from __future__ import annotations

import re
import time
from urllib.parse import quote

import httpx

from arcvita.models import Endeavor, Event, Person

WIKIDATA_SPARQL = "https://query.wikidata.org/sparql"
WIKIDATA_API = "https://www.wikidata.org/w/api.php"
ZH_WIKI_API = "https://zh.wikipedia.org/w/api.php"
USER_AGENT = "ArcVita/0.1 (biography research; local)"

DATE_RE = re.compile(r"^(\d{4})(?:-(\d{2})(?:-(\d{2}))?)?")  # kept for compat

# Delegated to core.dates (canonical)
try:
    from arcvita.core.dates import parse_iso as _parse_iso

    def parse_wikidata_date(s: str) -> tuple[str | None, str | None]:  # type: ignore[no-redef]
        return _parse_iso(s)

    # alias required by task spec
    parse_wikidate = parse_wikidata_date  # type: ignore
except Exception:  # pragma: no cover

    def parse_wikidata_date(s: str) -> tuple[str | None, str | None]:  # type: ignore[no-redef]
        if not s:
            return None, None
        s = s.strip().lstrip("+")
        if "T" in s:
            s = s.split("T")[0]
        m = DATE_RE.match(s)
        if not m:
            return None, None
        y, mo, d = m.group(1), m.group(2), m.group(3)
        if d and mo:
            return f"{y}-{mo}-{d}", "day"
        if mo:
            return f"{y}-{mo}", "month"
        return y, "year"

    parse_wikidate = parse_wikidata_date  # type: ignore


def sparql_query(client: httpx.Client, query: str, retries: int = 3) -> dict:
    for attempt in range(retries):
        try:
            r = client.get(
                WIKIDATA_SPARQL,
                params={"query": query, "format": "json"},
                headers={"User-Agent": USER_AGENT, "Accept": "application/sparql-results+json"},
                timeout=30,
            )
            r.raise_for_status()
            return r.json()
        except Exception:
            if attempt == retries - 1:
                raise
            time.sleep(2 * (attempt + 1))
    raise RuntimeError("sparql failed")


def _claim_time_to_date(claim) -> tuple[str | None, str | None]:
    try:
        v = claim["mainsnak"]["datavalue"]["value"]
        t = v.get("time", "")
        prec = v.get("precision", 11)
        # precision 11=day, 10=month, 9=year
        raw = t.lstrip("+").split("T")[0]
        # raw like 1643-01-04 or -0550-01-01
        if prec == 9:
            return raw[:4] if not raw.startswith("-") else "-" + raw[1:5], "year"
        if prec == 10:
            return raw[:7] if not raw.startswith("-") else "-" + raw[1:8], "month"
        return raw, "day"
    except Exception:
        return None, None


def _claim_entity_qid(claim) -> str | None:
    try:
        return claim["mainsnak"]["datavalue"]["value"]["id"]
    except Exception:
        return None


def fetch_persons_via_api(qids: list[str], client: httpx.Client) -> tuple[list[Person], dict[str, list[dict]]]:
    ids = "|".join(qids)
    r = client.get(
        WIKIDATA_API,
        params={
            "action": "wbgetentities",
            "ids": ids,
            "props": "labels|descriptions|sitelinks|claims",
            "languages": "zh|en",
            "languagefallback": "1",
            "format": "json",
        },
        headers={"User-Agent": USER_AGENT},
        timeout=30,
    )
    r.raise_for_status()
    data = r.json()
    # collect place qids for second round
    place_qids: set[str] = set()
    raw_entities = data.get("entities", {})
    for ent in raw_entities.values():
        for pid in ("P19", "P20", "P276"):
            for cl in ent.get("claims", {}).get(pid, []):
                q = _claim_entity_qid(cl)
                if q:
                    place_qids.add(q)
                for qv in (cl.get("qualifiers", {}).get("P276", []) or []):
                    q2 = qv.get("datavalue", {}).get("value", {}).get("id")
                    if q2:
                        place_qids.add(q2)
    place_labels: dict[str, str] = {}
    if place_qids:
        for chunk in [list(place_qids)[i : i + 50] for i in range(0, len(place_qids), 50)]:
            rr = client.get(
                WIKIDATA_API,
                params={
                    "action": "wbgetentities",
                    "ids": "|".join(chunk),
                    "props": "labels",
                    "languages": "zh|en",
                    "format": "json",
                },
                headers={"User-Agent": USER_AGENT},
                timeout=30,
            )
            rr.raise_for_status()
            for qid, ent in rr.json().get("entities", {}).items():
                lab = ent.get("labels", {}).get("zh", {}).get("value") or ent.get("labels", {}).get("en", {}).get("value")
                if lab:
                    place_labels[qid] = lab
            time.sleep(0.2)

    persons: list[Person] = []
    sig_events: dict[str, list[dict]] = {q: [] for q in qids}
    pos_events: dict[str, list[dict]] = {q: [] for q in qids}
    for qid, ent in raw_entities.items():
        labels = ent.get("labels", {})
        name_zh = labels.get("zh", {}).get("value") or labels.get("en", {}).get("value") or qid
        name_en = labels.get("en", {}).get("value")
        claims = ent.get("claims", {})
        # birth/death
        birth_date = None
        death_date = None
        if "P569" in claims:
            birth_date, _ = _claim_time_to_date(claims["P569"][0])
        if "P570" in claims:
            death_date, _ = _claim_time_to_date(claims["P570"][0])
        birth_place = None
        death_place = None
        if "P19" in claims:
            pq = _claim_entity_qid(claims["P19"][0])
            birth_place = place_labels.get(pq, pq) if pq else None
        if "P20" in claims:
            pq = _claim_entity_qid(claims["P20"][0])
            death_place = place_labels.get(pq, pq) if pq else None
        occupations: list[str] = []
        # P106 labels need second fetch - keep qids for now, fill via place_labels fallback
        for cl in claims.get("P106", [])[:5]:
            oq = _claim_entity_qid(cl)
            if oq:
                occupations.append(place_labels.get(oq, oq))
        # significant events P793 with qualifiers P585/P276
        for cl in claims.get("P793", []):
            try:
                ev_qid = _claim_entity_qid(cl)
                ev_label = place_labels.get(ev_qid, ev_qid) if ev_qid else ""
                quals = cl.get("qualifiers", {})
                date = None
                prec = None
                if "P585" in quals:
                    # qualifier snak value is time
                    v = quals["P585"][0].get("datavalue", {}).get("value", {})
                    t = v.get("time", "")
                    p = v.get("precision", 11)
                    raw = t.lstrip("+").split("T")[0] if t else ""
                    if raw:
                        if p == 9:
                            date = raw[:4] if not raw.startswith("-") else "-" + raw[1:5]
                            prec = "year"
                        elif p == 10:
                            date = raw[:7] if not raw.startswith("-") else "-" + raw[1:8]
                            prec = "month"
                        else:
                            date = raw
                            prec = "day"
                place = None
                pq = None
                if "P276" in quals:
                    pq = quals["P276"][0].get("datavalue", {}).get("value", {}).get("id")
                    place = place_labels.get(pq, pq) if pq else None
                sig_events[qid].append(
                    {"event_label": ev_label or ev_qid, "date": date, "date_precision": prec, "place_name": place, "place_qid": pq}
                )
            except Exception:
                continue
        # positions P39 and awards P166
        for cl in claims.get("P39", []):
            pq = _claim_entity_qid(cl)
            label = place_labels.get(pq, pq) if pq else ""
            quals = cl.get("qualifiers", {})
            date = None
            prec = None
            end_date = None
            if "P580" in quals:
                v = quals["P580"][0].get("datavalue", {}).get("value", {})
                t = v.get("time", "")
                if t:
                    raw = t.lstrip("+").split("T")[0]
                    date = raw[:4] if v.get("precision") == 9 else raw
                    prec = "year" if v.get("precision") == 9 else "day"
            if "P582" in quals:
                v = quals["P582"][0].get("datavalue", {}).get("value", {})
                t = v.get("time", "")
                if t:
                    end_date = t.lstrip("+").split("T")[0][:4]
            place = None
            place_q = None
            if "P276" in quals:
                place_q = quals["P276"][0].get("datavalue", {}).get("value", {}).get("id")
                place = place_labels.get(place_q, place_q) if place_q else None
            pos_events[qid].append({"event_label": label, "date": date, "date_precision": prec, "end_date": end_date, "place_name": place, "place_qid": place_q})
        for cl in claims.get("P166", [])[:10]:
            pq = _claim_entity_qid(cl)
            label = place_labels.get(pq, pq) if pq else ""
            quals = cl.get("qualifiers", {})
            date = None
            prec = None
            if "P585" in quals:
                v = quals["P585"][0].get("datavalue", {}).get("value", {})
                t = v.get("time", "")
                if t:
                    raw = t.lstrip("+").split("T")[0]
                    date = raw
                    prec = "day"
            pos_events[qid].append({"event_label": label, "date": date, "date_precision": prec, "place_name": None, "place_qid": None})
        persons.append(
            Person(
                qid=qid,
                name_zh=name_zh,
                name_en=name_en,
                birth_date=birth_date,
                death_date=death_date,
                birth_place=birth_place,
                death_place=death_place,
                occupations=occupations,
                source_urls=[f"https://www.wikidata.org/wiki/{qid}"],
            )
        )
    # stash for caller
    fetch_persons_via_api._sig = sig_events  # type: ignore
    fetch_persons_via_api._pos = pos_events  # type: ignore
    return persons, {"sig": sig_events, "pos": pos_events}


def fetch_persons_batch(qids: list[str], client: httpx.Client) -> list[Person]:
    values = " ".join(f"wd:{q}" for q in qids)
    query = f"""
SELECT ?person ?personLabel ?birthDate ?deathDate ?birthPlace ?birthPlaceLabel ?deathPlace ?deathPlaceLabel ?occupationLabel WHERE {{
  VALUES ?person {{ {values} }}
  OPTIONAL {{ ?person wdt:P569 ?birthDate. }}
  OPTIONAL {{ ?person wdt:P570 ?deathDate. }}
  OPTIONAL {{ ?person wdt:P19 ?birthPlace. }}
  OPTIONAL {{ ?person wdt:P20 ?deathPlace. }}
  OPTIONAL {{ ?person wdt:P106 ?occupation. }}
  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "zh,en". }}
}}
"""
    data = sparql_query(client, query)
    # Aggregate by person
    by_qid: dict[str, dict] = {q: {"occupations": set()} for q in qids}
    for b in data["results"]["bindings"]:
        uri = b["person"]["value"]
        qid = uri.rsplit("/", 1)[-1]
        rec = by_qid[qid]
        if "personLabel" in b:
            rec["name_zh"] = b["personLabel"]["value"]
        if "birthDate" in b:
            rec["birthDate_raw"] = b["birthDate"]["value"]
        if "deathDate" in b:
            rec["deathDate_raw"] = b["deathDate"]["value"]
        if "birthPlaceLabel" in b:
            rec["birthPlace"] = b["birthPlaceLabel"]["value"]
        if "deathPlaceLabel" in b:
            rec["deathPlace"] = b["deathPlaceLabel"]["value"]
        if "occupationLabel" in b:
            rec["occupations"].add(b["occupationLabel"]["value"])
    out: list[Person] = []
    for qid in qids:
        rec = by_qid[qid]
        birth_date, birth_prec = parse_wikidata_date(rec.get("birthDate_raw", ""))
        death_date, _ = parse_wikidata_date(rec.get("deathDate_raw", ""))
        out.append(
            Person(
                qid=qid,
                name_zh=rec.get("name_zh", qid),
                name_en=None,
                birth_date=birth_date,
                death_date=death_date,
                birth_place=rec.get("birthPlace"),
                death_place=rec.get("deathPlace"),
                occupations=sorted(rec["occupations"]),
                source_urls=[f"https://www.wikidata.org/wiki/{qid}"],
            )
        )
    return out


def fetch_labels_and_summaries(qids: list[str], client: httpx.Client) -> dict[str, dict]:
    # wbgetentities for zh/en labels + zhwiki sitelink + extract via zhwiki API
    result: dict[str, dict] = {q: {} for q in qids}
    # Wikidata API batch
    ids = "|".join(qids)
    r = client.get(
        WIKIDATA_API,
        params={
            "action": "wbgetentities",
            "ids": ids,
            "props": "labels|sitelinks",
            "languages": "zh|en",
            "languagefallback": "1",
            "format": "json",
        },
        headers={"User-Agent": USER_AGENT},
        timeout=30,
    )
    r.raise_for_status()
    data = r.json()
    for qid, ent in data.get("entities", {}).items():
        labels = ent.get("labels", {})
        result[qid]["name_zh"] = labels.get("zh", {}).get("value")
        result[qid]["name_en"] = labels.get("en", {}).get("value")
        sitelinks = ent.get("sitelinks", {})
        zh_title = sitelinks.get("zhwiki", {}).get("title")
        if zh_title:
            result[qid]["zhwiki_title"] = zh_title
    # Fetch zhwiki extracts for those with title (batch 5)
    titles = [v["zhwiki_title"] for v in result.values() if "zhwiki_title" in v]
    if titles:
        # zh.wikipedia extracts
        for i in range(0, len(titles), 5):
            chunk = titles[i : i + 5]
            rr = client.get(
                ZH_WIKI_API,
                params={
                    "action": "query",
                    "prop": "extracts",
                    "exintro": "1",
                    "explaintext": "1",
                    "titles": "|".join(chunk),
                    "format": "json",
                },
                headers={"User-Agent": USER_AGENT},
                timeout=30,
            )
            rr.raise_for_status()
            pages = rr.json().get("query", {}).get("pages", {})
            for page in pages.values():
                title = page.get("title")
                extract = page.get("extract", "")
                # map back by title
                for qid, v in result.items():
                    if v.get("zhwiki_title") == title:
                        # first sentence-ish, keep under 300 chars
                        s = extract.strip().replace("\n", " ")
                        if len(s) > 400:
                            s = s[:400] + "…"
                        v["summary_zh"] = s
                        v["zhwiki_url"] = f"https://zh.wikipedia.org/wiki/{quote(title)}"
    return result


def fetch_significant_events(qids: list[str], client: httpx.Client) -> dict[str, list[dict]]:
    values = " ".join(f"wd:{q}" for q in qids)
    query = f"""
SELECT ?person ?event ?eventLabel ?pointInTime ?place ?placeLabel ?coord WHERE {{
  VALUES ?person {{ {values} }}
  ?person p:P793 ?stmt.
  ?stmt ps:P793 ?event.
  OPTIONAL {{ ?stmt pq:P585 ?pointInTime. }}
  OPTIONAL {{ ?stmt pq:P276 ?place. OPTIONAL {{ ?place wdt:P625 ?coord. }} }}
  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "zh,en". }}
}}
ORDER BY ?person ?pointInTime
"""
    data = sparql_query(client, query)
    out: dict[str, list[dict]] = {q: [] for q in qids}
    for b in data["results"]["bindings"]:
        uri = b["person"]["value"]
        qid = uri.rsplit("/", 1)[-1]
        d_raw = b.get("pointInTime", {}).get("value", "")
        date, prec = parse_wikidata_date(d_raw) if d_raw else (None, None)
        place = b.get("placeLabel", {}).get("value")
        place_qid = None
        if "place" in b:
            place_qid = b["place"]["value"].rsplit("/", 1)[-1]
        coord = None
        if "coord" in b:
            # Point(lon lat)
            m = re.search(r"Point\s*\(\s*([-\d.]+)\s+([-\d.]+)\s*\)", b["coord"]["value"])
            if m:
                coord = [float(m.group(2)), float(m.group(1))]  # lat, lon
        out[qid].append(
            {
                "event_label": b.get("eventLabel", {}).get("value"),
                "event_qid": b.get("event", {}).get("value", "").rsplit("/", 1)[-1] if "event" in b else None,
                "date": date,
                "date_precision": prec,
                "place_name": place,
                "place_qid": place_qid,
                "coord": coord,
                "raw_date": d_raw,
            }
        )
    return out


def fetch_position_and_award_events(qids: list[str], client: httpx.Client) -> dict[str, list[dict]]:
    values = " ".join(f"wd:{q}" for q in qids)
    query = f"""
SELECT ?person ?posLabel ?start ?end ?placeLabel ?place ?awardLabel ?awardDate WHERE {{
  VALUES ?person {{ {values} }}
  {{
    ?person p:P39 ?stmt.
    ?stmt ps:P39 ?pos.
    OPTIONAL {{ ?stmt pq:P580 ?start. }}
    OPTIONAL {{ ?stmt pq:P582 ?end. }}
    OPTIONAL {{ ?stmt pq:P276 ?place. }}
  }} UNION {{
    ?person p:P166 ?stmt2.
    ?stmt2 ps:P166 ?award.
    OPTIONAL {{ ?stmt2 pq:P585 ?awardDate. }}
    BIND(?award AS ?pos)
  }}
  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "zh,en". }}
}}
"""
    data = sparql_query(client, query)
    out: dict[str, list[dict]] = {q: [] for q in qids}
    for b in data["results"]["bindings"]:
        qid = b["person"]["value"].rsplit("/", 1)[-1]
        label = b.get("posLabel", {}).get("value") or b.get("awardLabel", {}).get("value")
        if not label:
            continue
        # prefer start/awardDate
        raw = b.get("start", {}).get("value") or b.get("awardDate", {}).get("value") or ""
        date, prec = parse_wikidata_date(raw) if raw else (None, None)
        place = b.get("placeLabel", {}).get("value")
        place_qid = b.get("place", {}).get("value", "").rsplit("/", 1)[-1] if "place" in b else None
        raw_end = b.get("end", {}).get("value", "")
        end_date, _ = parse_wikidata_date(raw_end) if raw_end else (None, None)
        out[qid].append(
            {
                "event_label": label,
                "date": date,
                "date_precision": prec,
                "end_date": end_date,
                "place_name": place,
                "place_qid": place_qid,
                "raw_date": raw,
            }
        )
    return out


def build_events_for_person(qid: str, sig: list[dict], pos: list[dict]) -> list[Event]:
    events: list[Event] = []
    # Birth/death handled via Person; other events from sig+pos
    merged = sig + pos
    # Deduplicate by (label, date, place)
    seen: set[tuple] = set()
    for idx, m in enumerate(merged):
        label = (m.get("event_label") or "").strip()
        if not label:
            continue
        key = (label, m.get("date"), m.get("place_name"))
        if key in seen:
            continue
        seen.add(key)
        # Filter overly generic single-char noise
        if len(label) < 2:
            continue
        eid = f"{qid}-event-{len(events)+1}"
        # Heuristic event_type
        et = "经历"
        if any(k in label for k in ["战争", "战役", "远征", "革命"]):
            et = "战役"
        elif any(k in label for k in ["奖", "勋章", "诺贝尔"]):
            et = "获奖"
        elif any(k in label for k in ["任", "职位", "总统", "皇帝", "首相"]):
            et = "任职"
        elif any(k in label for k in ["迁", "流亡", "退位"]):
            et = "迁徙"
        events.append(
            Event(
                id=eid,
                person_qid=qid,
                date=m.get("date"),
                date_precision=m.get("date_precision"),  # type: ignore
                place_name=m.get("place_name"),
                place_qid=m.get("place_qid"),
                place_coord=m.get("coord"),
                event_type=et,
                title_zh=label,
                description_zh=None,
                sources=[f"https://www.wikidata.org/wiki/{qid}#P793"] if m in sig else [f"https://www.wikidata.org/wiki/{qid}"],
                status="needs_review" if not m.get("date") else "ai_filled",
                needs_review_reason=None if m.get("date") else "缺时间，需AI/人工补齐",
            )
        )
    return events


# Curated endeavors for pilot persons (thick narrative, 做事流)
CURATED_ENDEAVORS: dict[str, list[dict]] = {
    "Q935": [
        {
            "title_zh": "光学与颜色研究",
            "domain": "科学",
            "start_date": "1666",
            "end_date": "1672",
            "places": ["剑桥", "伦敦"],
            "description_zh": "躲避瘟疫回到伍尔斯索普，却在棱镜前看见白光的秘密；我把光拆开又合上，论文投向皇家学会，争议随之而来。此后每一次回望，都像在黑暗中点亮一束可控的光。",
            "outcome": "发表光学论文，奠定近代光学基础",
            "lesson": "在孤独的实验里坚持可重复的证据，比雄辩更有力。",
        },
        {
            "title_zh": "微积分与数学原理孕育",
            "domain": "科学",
            "start_date": "1665",
            "end_date": "1687",
            "places": ["剑桥"],
            "description_zh": "瘟疫年代的田野与书房，我与无穷小搏斗；多年后在哈雷的催促下把零散手稿压成《原理》，用几何的语言为世界立法。",
            "outcome": "《自然哲学的数学原理》出版",
            "lesson": "长期沉淀后的一次体系化交付，能改变一个时代的坐标系。",
        },
        {
            "title_zh": "万有引力与天体力学",
            "domain": "科学",
            "start_date": "1684",
            "end_date": "1687",
            "places": ["剑桥", "伦敦"],
            "description_zh": "从苹果的下落到月球的轨道，我试图让同一条定律贯穿天地；在与胡克的争执中学会用数学把直觉钉牢。",
            "outcome": "提出万有引力定律，统一天上地下力学",
            "lesson": "把不同尺度的现象纳入同一原理，是最难也最值得的做事方式。",
        },
        {
            "title_zh": "皇家造币厂与公共事务",
            "domain": "政治/公共",
            "start_date": "1696",
            "end_date": "1727",
            "places": ["伦敦"],
            "description_zh": "离开剑桥走进造币厂，我以同样的苛刻追查伪币、重铸货币；科学的严谨在世俗事务里同样锋利。",
            "outcome": "主持货币重铸，打击伪造",
            "lesson": "把专业精神迁移到新战场，同样能创造秩序。",
        },
    ],
    "Q4604": [
        {
            "title_zh": "周游列国与讲学",
            "domain": "文化/政治",
            "start_date": "-497",
            "end_date": "-484",
            "places": ["鲁", "卫", "陈", "蔡"],
            "description_zh": "我带着弟子在诸侯间辗转，屡遭冷遇却不改其志；在陈蔡之间断粮，仍弦歌不辍——道不行，吾辈当以身示范。",
            "outcome": "形成儒家学说雏形，弟子三千",
            "lesson": "在逆境中保持一致的言行，比一时的采纳更长久。",
        },
        {
            "title_zh": "整理六经",
            "domain": "文化",
            "start_date": "-484",
            "end_date": "-479",
            "places": ["鲁"],
            "description_zh": "归鲁后不再求仕，转而删诗书、定礼乐；我想为后世留下一套可依的文脉，让人在迷茫时有章可循。",
            "outcome": "《诗》《书》《礼》《乐》《易》《春秋》成型",
            "lesson": "做成一套可传承的体系，胜过做成一件事。",
        },
    ],
    "Q517": [
        {
            "title_zh": "意大利战役与崛起",
            "domain": "军事/政治",
            "start_date": "1796",
            "end_date": "1797",
            "places": ["意大利", "巴黎"],
            "description_zh": "以少胜多的急行军与心理战让我一战成名，也让我第一次相信意志可以改写地图；巴黎的掌声让我误以为掌声会永远持续。",
            "outcome": "控制北意大利，声望飙升",
            "lesson": "早期的胜利最容易让人高估自己的边界。",
        },
        {
            "title_zh": "称帝与法典",
            "domain": "政治",
            "start_date": "1804",
            "end_date": "1807",
            "places": ["巴黎"],
            "description_zh": "我把革命的成果装进《民法典》，试图用法律固定住动荡的法国；加冕的那一刻，荣光与孤独同时加身。",
            "outcome": "《拿破仑法典》颁布，影响欧洲大陆法系",
            "lesson": "制度化的成果比个人光环走得更远。",
        },
        {
            "title_zh": "远征俄国与衰落",
            "domain": "军事",
            "start_date": "1812",
            "end_date": "1815",
            "places": ["莫斯科", "莱比锡", "滑铁卢"],
            "description_zh": "莫斯科的大火与寒冬把补给线拉断，莱比锡与滑铁卢把同一个错误重复了两遍；当所有联盟都站到对面，个人的天才已无法弥补战略的透支。",
            "outcome": "帝国崩溃，流放圣赫勒拿",
            "lesson": "过度扩张会让每一次胜利都成为下一次失败的预付款。",
        },
    ],
    "Q36955": [  # placeholder, not used
    ],
    "Q8016": [
        {
            "title_zh": "二战领导与演讲",
            "domain": "政治/军事",
            "start_date": "1940",
            "end_date": "1945",
            "places": ["伦敦"],
            "description_zh": "敦刻尔克之后我对议会说我们将在海滩上战斗；在伦敦的废墟里，语言成了武器，让一个民族相信自己还能站着。",
            "outcome": "领导英国渡过二战，获诺贝尔文学奖",
            "lesson": "在至暗时刻，清晰的叙事本身就是领导力。",
        },
    ],
    "Q937": [
        {
            "title_zh": "相对论的孕育",
            "domain": "科学",
            "start_date": "1905",
            "end_date": "1915",
            "places": ["伯尔尼", "柏林"],
            "description_zh": "专利局的桌前，我在思想实验里追光；从狭义到广义，十年间把时空从背景变成了主角，孤独却笃定。",
            "outcome": "狭义与广义相对论",
            "lesson": "给自己一段不被打扰的深思期，答案会在尽头等你。",
        },
    ],
}


def curated_endeavors_for(qid: str) -> list[Endeavor]:
    raw = CURATED_ENDEAVORS.get(qid, [])
    out: list[Endeavor] = []
    for idx, r in enumerate(raw, 1):
        out.append(
            Endeavor(
                id=f"{qid}-endeavor-{idx}",
                person_qid=qid,
                title_zh=r["title_zh"],
                domain=r.get("domain"),
                start_date=r.get("start_date"),
                end_date=r.get("end_date"),
                places=r.get("places", []),
                description_zh=r.get("description_zh"),
                outcome=r.get("outcome"),
                lesson=r.get("lesson"),
                event_ids=[],
                sources=[f"https://www.wikidata.org/wiki/{qid}"],
                review_status="ai_filled",
            )
        )
    return out
