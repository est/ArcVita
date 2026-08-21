from __future__ import annotations

import json
import time
from pathlib import Path

import httpx
import yaml

from arcvita.config import load_config, load_seed
from arcvita.models import Endeavor, Event, Person
from arcvita.curated import enrich_offline
from arcvita.wikidata import (
    build_events_for_person,
    curated_endeavors_for,
    fetch_labels_and_summaries,
    fetch_persons_batch,
    fetch_persons_via_api,
)

USER_AGENT = "ArcVita/0.1 (biography research; local)"


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

    persons: list[Person] = []
    events: list[Event] = []
    endeavors: list[Endeavor] = []

    offline_map = enrich_offline(seed_meta)

    def _person_from_offline(qid: str, off: dict) -> Person:
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
            summary_zh=off.get("summary_zh"),
            summary_first_person=off.get("summary_first_person"),
            lesson=off.get("lesson"),
            source_urls=[f"https://www.wikidata.org/wiki/{qid}"],
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
                    # fill summary_first_person / lesson from curated
                    if off.get("summary_first_person"):
                        p.summary_first_person = off["summary_first_person"]
                    if off.get("lesson"):
                        p.lesson = off["lesson"]
                    if off.get("era"):
                        p.era = off["era"]
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
                            sources=[f"https://www.wikidata.org/wiki/{p.qid}"],
                            status="ai_filled",
                        )
                    )
                sig = sig_map.get(p.qid, [])
                pos = pos_map.get(p.qid, [])
                api_evs = build_events_for_person(p.qid, sig, pos)
                # merge: offline first, then api dedup by title
                seen_titles = {e.title_zh for e in off_evs}
                evs = list(off_evs)
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

    return {"persons": len(persons), "events": len(events), "endeavors": len(endeavors)}
