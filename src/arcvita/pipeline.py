from __future__ import annotations

import json
import time
from pathlib import Path

import httpx
import yaml

from arcvita.config import load_config, load_seed
from arcvita.curated import enrich_offline
from arcvita.models import Endeavor, Event, Person
from arcvita.wikidata import (
    build_events_for_person,
    curated_endeavors_for,
    fetch_labels_and_summaries,
    fetch_persons_via_api,
)

USER_AGENT = "ArcVita/0.1 (biography research; local)"

# sources 可插拔接入（默认离线优先，不改现有 25 人产出）
try:
    from arcvita.sources.enrich import enrich_person as _enrich_person
except Exception:  # pragma: no cover
    _enrich_person = None  # type: ignore


def run_pipeline(config_path: str = "config.yaml", limit: int | None = None, qids: list[str] | None = None) -> dict:
    cfg = load_config(config_path)
    paths = cfg["paths"]
    wikicfg = cfg.get("wikidata", {})
    batch_size = wikicfg.get("batch_size", 8)
    seed = load_seed(paths["seed"])
    if qids:
        seed = [s for s in seed if s["qid"] in qids]
    if limit:
        seed = seed[:limit]

    raw_dir = Path(paths["raw_dir"])
    raw_dir.mkdir(parents=True, exist_ok=True)

    seed_meta = {s["qid"]: s for s in seed}
    all_qids = [s["qid"] for s in seed]

    # sources 配置：默认离线优先（enabled 为空则不联网），可插拔
    sources_cfg = cfg.get("sources", {}) if isinstance(cfg.get("sources"), dict) else {}
    sources_enabled: list[str] = list(sources_cfg.get("enabled") or [])
    # 兼容旧习惯：sources.enabled 为空 -> 纯离线；显式 ["wikipedia","wikidata"] 才联网
    sources_cache = bool(sources_cfg.get("cache", True))
    sources_qps = float(sources_cfg.get("qps", wikicfg.get("qps", 0.5) or 0.5))

    persons: list[Person] = []
    events: list[Event] = []
    endeavors: list[Endeavor] = []

    offline_map = enrich_offline(seed_meta)

    # 古籍提取数据：按姓名索引
    classical_map: dict[str, dict] = {}
    try:
        from arcvita.sources.classical import fetch_classical_for_name
        for qid, meta in seed_meta.items():
            name = meta.get("name_zh", "")
            if name:
                cpatch = fetch_classical_for_name(name)
                if cpatch:
                    classical_map[qid] = cpatch
    except Exception:
        pass

    def _person_from_offline(qid: str, off: dict) -> Person:
        source_url = f"https://www.wikidata.org/wiki/{qid}" if not qid.startswith("guji-") else f"https://daizhige.org/史藏/正史/史记.html"
        return Person(
            qid=qid,
            name_zh=off.get("name_zh") or seed_meta.get(qid, {}).get("name_zh", qid),
            name_en=off.get("name_en"),
            birth_date=off.get("birth_date"),
            death_date=off.get("death_date"),
            birth_place=off.get("birth_place"),
            death_place=off.get("death_place"),
            occupations=off.get("occupations", []),
            era=off.get("era"),
            archetype=off.get("archetype"),
            summary_zh=off.get("summary_zh"),
            summary_first_person=off.get("summary_first_person"),
            lesson=off.get("lesson"),
            dilemmas=off.get("dilemmas", []),
            source_urls=[source_url],
        )

    with httpx.Client(headers={"User-Agent": USER_AGENT}, timeout=30) as client:
        for i in range(0, len(all_qids), batch_size):
            batch = all_qids[i : i + batch_size]
            print(f"[{i//batch_size+1}] fetching batch {batch}")
            # offline-first: if every qid has curated offline, skip network entirely
            offline_covered = all(q in offline_map and offline_map[q].get("birth_date") for q in batch)
            if offline_covered:
                batch_persons = [_person_from_offline(q, offline_map[q]) for q in batch]
                sig_map: dict[str, list[dict]] = {q: [] for q in batch}
                pos_map: dict[str, list[dict]] = {q: [] for q in batch}
                label_map: dict[str, dict] = {q: {} for q in batch}
                print("  offline-first (no network)")
            else:
                try:
                    batch_persons, api_events = fetch_persons_via_api(batch, client)
                    sig_map = api_events["sig"]
                    pos_map = api_events["pos"]
                    label_map = {}
                    for p in batch_persons:
                        label_map[p.qid] = {"name_zh": p.name_zh, "name_en": p.name_en, "summary_zh": None}
                    try:
                        extra = fetch_labels_and_summaries(batch, client)
                        for qid, v in extra.items():
                            if v.get("summary_zh"):
                                label_map[qid]["summary_zh"] = v["summary_zh"]
                                label_map[qid]["zhwiki_url"] = v.get("zhwiki_url")
                    except Exception:
                        pass
                except Exception as e:
                    print(f"  API fetch failed: {e}, falling back to offline+curated")
                    batch_persons = []
                    for qid in batch:
                        off = offline_map.get(qid, {})
                        if off and off.get("birth_date"):
                            batch_persons.append(_person_from_offline(qid, off))
                        else:
                            # minimal from seed so no one is dropped
                            meta = seed_meta.get(qid, {})
                            batch_persons.append(
                                Person(
                                    qid=qid,
                                    name_zh=meta.get("name_zh", qid),
                                    birth_date=None,
                                    source_urls=[f"https://www.wikidata.org/wiki/{qid}"],
                                    status="needs_review",
                                    needs_review_reason="离线库未覆盖，需AI/线上补齐",
                                )
                            )
                    sig_map = {q: [] for q in batch}
                    pos_map = {q: [] for q in batch}
                    label_map = {q: {} for q in batch}

            # also raw dump for reproducibility
            (raw_dir / f"batch_{i//batch_size+1}.json").write_text(
                json.dumps({"qids": batch, "label_map": label_map}, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

            for p in batch_persons:
                extra = label_map.get(p.qid, {})
                if extra.get("name_zh") and extra["name_zh"] != p.name_zh:
                    # keep API label if more precise
                    pass
                if extra.get("summary_zh"):
                    p.summary_zh = extra["summary_zh"]
                if extra.get("zhwiki_url"):
                    p.source_urls.append(extra["zhwiki_url"])
                # offline enrich fallback for thin API results
                off = offline_map.get(p.qid)
                if off:
                    if not p.summary_zh and off.get("summary_zh"):
                        p.summary_zh = off["summary_zh"]
                    if not p.birth_place and off.get("birth_place"):
                        p.birth_place = off["birth_place"]
                    if off.get("summary_first_person"):
                        p.summary_first_person = off["summary_first_person"]
                    if off.get("lesson"):
                        p.lesson = off["lesson"]
                    if off.get("era"):
                        p.era = off["era"]
                    if off.get("archetype"):
                        p.archetype = off["archetype"]
                    if off.get("dilemmas"):
                        p.dilemmas = off["dilemmas"]
                    if off.get("keywords"):
                        p.keywords = off["keywords"]
                # 古籍提取数据补充（仅补空字段）
                cp = classical_map.get(p.qid)
                if cp:
                    pp = cp.get("person_patch", {})
                    for k in ("archetype", "dilemmas", "summary_first_person", "lesson"):
                        if not getattr(p, k, None) and pp.get(k):
                            setattr(p, k, pp[k])
                    if not p.birth_date and pp.get("birth_date"):
                        p.birth_date = pp["birth_date"]
                    if not p.death_date and pp.get("death_date"):
                        p.death_date = pp["death_date"]
                    if not p.birth_place and pp.get("birth_place"):
                        p.birth_place = pp["birth_place"]
                    if not p.era and pp.get("era"):
                        p.era = pp["era"]
                    for u in cp.get("source_urls", []):
                        if u and u not in p.source_urls:
                            p.source_urls.append(u)
                meta = seed_meta.get(p.qid, {})
                if meta.get("role"):
                    p.role = meta["role"]
                if meta.get("sensitivity"):
                    p.sensitivity = meta["sensitivity"]
                if meta.get("visibility"):
                    p.visibility = meta["visibility"]
                # keep curated era (don't clear)
                # curated endeavors for thick narrative (offline-first, merged with API-derived)
                api_eds = curated_endeavors_for(p.qid)
                # offline curated may have more; enrich_offline returns endeavors separately
                off_eds = offline_map.get(p.qid, {}).get("_endeavors", [])
                seen_titles = {e.title_zh for e in api_eds}
                merged_eds = list(api_eds)
                for oe in off_eds:
                    if oe.title_zh not in seen_titles:
                        merged_eds.append(oe)
                # 古籍提取的事业补充
                if cp and cp.get("endeavors_from_classical"):
                    for ce_raw in cp["endeavors_from_classical"]:
                        if ce_raw.get("title_zh") not in seen_titles:
                            try:
                                ce = Endeavor(
                                    id=f"{p.qid}-endeavor-{len(merged_eds)+1}",
                                    person_qid=p.qid,
                                    title_zh=ce_raw["title_zh"],
                                    domain=ce_raw.get("domain"),
                                    start_date=ce_raw.get("start_date"),
                                    end_date=ce_raw.get("end_date"),
                                    places=ce_raw.get("places", []),
                                    phases=ce_raw.get("phases", []),  # type: ignore
                                    description_zh=ce_raw.get("description_zh"),
                                    outcome=ce_raw.get("outcome"),
                                    lesson=ce_raw.get("lesson"),
                                    event_ids=[],
                                    sources=[f"https://daizhige.org/史藏/正史/史记.html"],
                                    review_status="ai_filled",
                                )
                                merged_eds.append(ce)
                                seen_titles.add(ce.title_zh)
                            except Exception:
                                pass
                for idx, e in enumerate(merged_eds, 1):
                    e.id = f"{p.qid}-endeavor-{idx}"
                eds = merged_eds
                endeavors.extend(eds)

                # events: offline events first, then wikidata-derived
                off_events_raw = offline_map.get(p.qid, {}).get("_events", [])
                off_evs: list[Event] = []
                for idx, oe in enumerate(off_events_raw, 1):
                    off_evs.append(
                        Event(
                            id=f"{p.qid}-event-{idx}",
                            person_qid=p.qid,
                            date=oe.get("date"),
                            date_precision="day" if oe.get("date") and len(oe["date"]) > 7 else "year",  # type: ignore
                            place_name=oe.get("place_name"),
                            event_type=oe.get("event_type", "经历"),
                            title_zh=oe.get("title_zh", ""),
                            description_zh=oe.get("description_zh"),
                            is_highlight=oe.get("is_highlight", False),
                            highlight_type=oe.get("highlight_type"),
                            highlight_note=oe.get("highlight_note"),
                            sources=[f"https://www.wikidata.org/wiki/{p.qid}"],
                            status="ai_filled",
                        )
                    )
                sig = sig_map.get(p.qid, [])
                pos = pos_map.get(p.qid, [])
                api_evs = build_events_for_person(p.qid, sig, pos)
                # merge: offline first, then classical, then api dedup by title
                seen_titles = {e.title_zh for e in off_evs}
                evs = list(off_evs)
                # 古籍提取事件补充
                if cp and cp.get("events_from_classical"):
                    for ce_raw in cp["events_from_classical"]:
                        if ce_raw.get("title_zh") and ce_raw["title_zh"] not in seen_titles:
                            try:
                                ce = Event(
                                    id=f"{p.qid}-event-{len(evs)+1}",
                                    person_qid=p.qid,
                                    date=ce_raw.get("date"),
                                    date_precision="day" if ce_raw.get("date") and len(ce_raw["date"]) > 7 else "year",  # type: ignore
                                    place_name=ce_raw.get("place_name"),
                                    event_type=ce_raw.get("event_type", "经历"),
                                    title_zh=ce_raw["title_zh"],
                                    description_zh=ce_raw.get("description_zh"),
                                    is_highlight=ce_raw.get("is_highlight", False),
                                    highlight_type=ce_raw.get("highlight_type"),
                                    highlight_note=ce_raw.get("highlight_note"),
                                    sources=[f"https://daizhige.org/史藏/正史/史记.html"],
                                    status="ai_filled",
                                )
                                evs.append(ce)
                                seen_titles.add(ce.title_zh)
                            except Exception:
                                pass
                for ae in api_evs:
                    if ae.title_zh not in seen_titles:
                        # re-id sequentially
                        ae.id = f"{p.qid}-event-{len(evs)+1}"
                        evs.append(ae)
                # if offline provided birth/death already, don't duplicate synthetic
                has_birth = any(e.event_type == "出生" for e in evs)
                has_death = any(e.event_type == "逝世" for e in evs)

                if p.birth_date and not has_birth:
                    evs.insert(
                        0,
                        Event(
                            id=f"{p.qid}-event-birth",
                            person_qid=p.qid,
                            date=p.birth_date,
                            date_precision="day" if len(p.birth_date) > 7 else "year",  # type: ignore
                            place_name=p.birth_place,
                            event_type="出生",
                            title_zh="出生",
                            description_zh=f"生于 {p.birth_place or '未知地点'}",
                            sources=[f"https://www.wikidata.org/wiki/{p.qid}"],
                            status="verified",
                        ),
                    )
                if p.death_date and not has_death:
                    evs.append(
                        Event(
                            id=f"{p.qid}-event-death",
                            person_qid=p.qid,
                            date=p.death_date,
                            date_precision="day" if len(p.death_date) > 7 else "year",  # type: ignore
                            place_name=getattr(p, "death_place", None),
                            event_type="逝世",
                            title_zh="逝世",
                            description_zh=f"卒于 {getattr(p, 'death_place', None) or '未知地点'}",
                            sources=[f"https://www.wikidata.org/wiki/{p.qid}"],
                            status="verified",
                        )
                    )

                # --- sources 可插拔 enrich（仅当 sources.enabled 非空时才联网） ---
                if sources_enabled and _enrich_person is not None:
                    try:
                        title_hint = label_map.get(p.qid, {}).get("zhwiki_title") if isinstance(label_map.get(p.qid), dict) else None
                        # 优先用 label_map 里的 zhwiki_title 传给 wikipedia，避免重复请求 sitelinks
                        enrich_res = _enrich_person(p.qid, client, cache_dir=raw_dir, enabled_sources=sources_enabled, title_hint=title_hint)
                        patch = enrich_res.get("patch", {})
                        # summary 仅在 curated 无时才补（保离线真源不被覆盖）
                        if not p.summary_zh and patch.get("summary_zh"):
                            p.summary_zh = patch["summary_zh"]
                        # person_patch 中的生卒地/职业等，仅在空字段时补
                        pp = patch.get("person_patch", {}) or {}
                        if pp:
                            if not p.birth_date and pp.get("birth_date"):
                                p.birth_date = pp["birth_date"]
                            if not p.death_date and pp.get("death_date"):
                                p.death_date = pp["death_date"]
                            if not p.birth_place and pp.get("birth_place"):
                                p.birth_place = pp["birth_place"]
                            if not getattr(p, "death_place", None) and pp.get("death_place"):
                                p.death_place = pp["death_place"]  # type: ignore
                            if pp.get("occupations"):
                                # 合并去重
                                existing = set(p.occupations or [])
                                for oc in pp["occupations"]:
                                    if oc not in existing:
                                        p.occupations.append(oc)
                        # source_urls 合并去重
                        for u in patch.get("extra_source_urls", []) or []:
                            if u and u not in p.source_urls:
                                p.source_urls.append(u)
                        # events 增量：wikipedia 名场面候选 + wikidata sig/pos（去重标题）
                        extra_evs: list[Event] = []
                        extra_evs.extend(patch.get("events_from_wiki", []) or [])
                        extra_evs.extend(patch.get("events_from_wikidata", []) or [])
                        if extra_evs:
                            seen_titles_local = {e.title_zh for e in evs}
                            for ae in extra_evs:
                                if ae.title_zh not in seen_titles_local:
                                    ae.id = f"{p.qid}-event-{len(evs)+1}"
                                    evs.append(ae)
                                    seen_titles_local.add(ae.title_zh)
                            # 若 wikidata 补上了 birth/death 而之前无，也会在上面 extra_evs 里；无需重复 synthetic
                        # 写 enrich 降级链路可追溯文件（不影响主落盘）
                        if sources_cache:
                            try:
                                (raw_dir / f"{p.qid}.enrich.json").write_text(
                                    json.dumps(
                                        {
                                            "qid": p.qid,
                                            "enabled": sources_enabled,
                                            "wikipedia": {k: v for k, v in (enrich_res.get("wikipedia") or {}).items() if k not in ("extract", "rest_summary")},
                                            "wikidata": {k: v for k, v in (enrich_res.get("wikidata") or {}).items() if k not in ("person",)},
                                            "patch_summary": patch.get("summary_zh"),
                                            "extra_urls": patch.get("extra_source_urls", [])[:3],
                                            "events_added": len(extra_evs),
                                        },
                                        ensure_ascii=False,
                                        indent=2,
                                    ),
                                    encoding="utf-8",
                                )
                            except Exception:
                                pass
                    except Exception as e:
                        print(f"  enrich skipped for {p.qid}: {e}")

                # naive link: distribute events into endeavors by date range overlap (if endeavor has dates)
                for ed in eds:
                    # placeholder: if event date within endeavor range, assign
                    for ev in evs:
                        if ev.endeavor_id:
                            continue
                        if not ev.date or not ed.start_date or not ed.end_date:
                            continue
                        try:
                            # compare year only for BCE/CE simplicity
                            ey = int(ev.date.lstrip("-").split("-")[0])
                            sy = int(ed.start_date.lstrip("-").split("-")[0])
                            en = int(ed.end_date.lstrip("-").split("-")[0])
                            if sy <= ey <= en:
                                ev.endeavor_id = ed.id
                                ed.event_ids.append(ev.id)
                        except Exception:
                            continue
                events.extend(evs)
                # status: verified if we have dates+sources
                p.status = "ai_filled" if not p.summary_zh else "needs_review"
                if not p.birth_date:
                    p.needs_review_reason = "缺生卒年/地点，需补"
                persons.append(p)

            # 按配置限流（离线时 0.5s；sources 启用时按 sources.qps）
            if sources_enabled and sources_qps and sources_qps > 0:
                time.sleep(max(0.2, 1.0 / sources_qps))
            else:
                time.sleep(0.5)

    # write YAML (primary) + SQLite
    persons_yaml = Path(paths["persons_yaml"])
    events_yaml = Path(paths["events_yaml"])
    endeavors_yaml = Path(paths["endeavors_yaml"])
    persons_yaml.parent.mkdir(parents=True, exist_ok=True)
    events_yaml.parent.mkdir(parents=True, exist_ok=True)

    def dump_yaml(path: Path, items: list):
        data = [it.model_dump(exclude_none=False) for it in items]
        # block style, no quotes hell
        path.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False, width=100), encoding="utf-8")

    dump_yaml(persons_yaml, persons)
    dump_yaml(events_yaml, events)
    dump_yaml(endeavors_yaml, endeavors)

    # SQLite build
    from arcvita.store import build_db

    build_db(Path(paths["db"]), persons, events, endeavors)

    # report
    from arcvita.report import write_report

    write_report(persons, events, endeavors, Path("data/processed/_report.md"))

    # render: 成事儿周期可查阅形态 + 名场面总表
    try:
        from arcvita.render import build_highlights, build_timelines

        build_highlights()
        build_timelines()
    except Exception as e:
        print(f"render skipped: {e}")

    return {"persons": len(persons), "events": len(events), "endeavors": len(endeavors)}
