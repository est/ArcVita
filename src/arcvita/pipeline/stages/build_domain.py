"""build_domain stage — (inputs,cfg)->(outputs,diagnostics).

组装 Person / Endeavor / Event，含:
- _person_from_offline 融合
- label_map / offline / classical / seed meta 补全
- curated + offline + classical 的 endeavors/events 合并
- birth/death 合成事件
- sources可插拔 enrich (按 sources.enabled)
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from arcvita.models import Endeavor, Event, Person

try:
    from arcvita.sources.enrich import enrich_person as _enrich_person
except Exception:  # pragma: no cover
    _enrich_person = None  # type: ignore


def _coerce_phase(ph: Any) -> Any:
    return ph


def build_domain(
    batch_persons: list[Person],
    sig_map: dict[str, list[dict]],
    pos_map: dict[str, list[dict]],
    label_map: dict[str, dict],
    seed_meta: dict[str, dict],
    offline_map: dict[str, dict],
    classical_map: dict[str, dict],
    cfg: dict,
    client: Any | None = None,
    raw_dir: Path | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    from arcvita.wikidata import build_events_for_person, curated_endeavors_for

    sources_cfg = cfg.get("sources", {}) if isinstance(cfg.get("sources"), dict) else {}
    sources_enabled: list[str] = list(sources_cfg.get("enabled") or [])
    sources_cache = bool(sources_cfg.get("cache", True))

    persons_out: list[Person] = []
    events_out: list[Event] = []
    endeavors_out: list[Endeavor] = []
    diagnostics: dict[str, Any] = {
        "batch_persons_in": len(batch_persons),
        "sources_enabled": sources_enabled,
        "classical_found": 0,
    }

    for p in batch_persons:
        qid = p.qid
        extra = label_map.get(qid, {})
        # keep API label if needed (no-op as original)
        if extra.get("summary_zh"):
            p.summary_zh = extra["summary_zh"]
        if extra.get("zhwiki_url"):
            p.source_urls.append(extra["zhwiki_url"])
        # offline enrich fallback
        off = offline_map.get(qid)
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
            # preserve role/sensitivity/visibility if offline had
            if off.get("role"):
                p.role = off["role"]
            if off.get("sensitivity"):
                p.sensitivity = off["sensitivity"]
            if off.get("visibility"):
                p.visibility = off["visibility"]

        # classical supplement (only fill missing)
        cp = classical_map.get(qid)
        if cp:
            diagnostics["classical_found"] += 1
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
        meta = seed_meta.get(qid, {})
        if meta.get("role"):
            p.role = meta["role"]
        if meta.get("sensitivity"):
            p.sensitivity = meta["sensitivity"]
        if meta.get("visibility"):
            p.visibility = meta["visibility"]

        # curated endeavors merge
        api_eds = curated_endeavors_for(qid)
        off_eds = offline_map.get(qid, {}).get("_endeavors", [])
        seen_titles = {e.title_zh for e in api_eds}
        merged_eds = list(api_eds)
        for oe in off_eds:
            if oe.title_zh not in seen_titles:
                merged_eds.append(oe)
        if cp and cp.get("endeavors_from_classical"):
            for ce_raw in cp["endeavors_from_classical"]:
                if ce_raw.get("title_zh") not in seen_titles:
                    try:
                        ce = Endeavor(
                            id=f"{qid}-endeavor-{len(merged_eds)+1}",
                            person_qid=qid,
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
                            sources=["https://daizhige.org/史藏/正史/史记.html"],
                            review_status="ai_filled",
                        )
                        merged_eds.append(ce)
                        seen_titles.add(ce.title_zh)
                    except Exception:
                        pass
        for idx, e in enumerate(merged_eds, 1):
            e.id = f"{qid}-endeavor-{idx}"
        eds = merged_eds
        endeavors_out.extend(eds)

        # events: offline first, then classical, then api dedup
        off_events_raw = offline_map.get(qid, {}).get("_events", [])
        off_evs: list[Event] = []
        for idx, oe in enumerate(off_events_raw, 1):
            off_evs.append(
                Event(
                    id=f"{qid}-event-{idx}",
                    person_qid=qid,
                    date=oe.get("date"),
                    date_precision="day" if oe.get("date") and len(oe["date"]) > 7 else "year",  # type: ignore
                    place_name=oe.get("place_name"),
                    event_type=oe.get("event_type", "经历"),
                    title_zh=oe.get("title_zh", ""),
                    description_zh=oe.get("description_zh"),
                    is_highlight=oe.get("is_highlight", False),
                    highlight_type=oe.get("highlight_type"),
                    highlight_note=oe.get("highlight_note"),
                    sources=[f"https://www.wikidata.org/wiki/{qid}"],
                    status="ai_filled",
                )
            )
        sig = sig_map.get(qid, [])
        pos = pos_map.get(qid, [])
        api_evs = build_events_for_person(qid, sig, pos)
        seen_titles_ev = {e.title_zh for e in off_evs}
        evs = list(off_evs)
        if cp and cp.get("events_from_classical"):
            for ce_raw in cp["events_from_classical"]:
                if ce_raw.get("title_zh") and ce_raw["title_zh"] not in seen_titles_ev:
                    try:
                        ce = Event(
                            id=f"{qid}-event-{len(evs)+1}",
                            person_qid=qid,
                            date=ce_raw.get("date"),
                            date_precision="day" if ce_raw.get("date") and len(ce_raw["date"]) > 7 else "year",  # type: ignore
                            place_name=ce_raw.get("place_name"),
                            event_type=ce_raw.get("event_type", "经历"),
                            title_zh=ce_raw["title_zh"],
                            description_zh=ce_raw.get("description_zh"),
                            is_highlight=ce_raw.get("is_highlight", False),
                            highlight_type=ce_raw.get("highlight_type"),
                            highlight_note=ce_raw.get("highlight_note"),
                            sources=["https://daizhige.org/史藏/正史/史记.html"],
                            status="ai_filled",
                        )
                        evs.append(ce)
                        seen_titles_ev.add(ce.title_zh)
                    except Exception:
                        pass
        for ae in api_evs:
            if ae.title_zh not in seen_titles_ev:
                ae.id = f"{qid}-event-{len(evs)+1}"
                evs.append(ae)
                seen_titles_ev.add(ae.title_zh)
        has_birth = any(e.event_type == "出生" for e in evs)
        has_death = any(e.event_type == "逝世" for e in evs)
        if p.birth_date and not has_birth:
            evs.insert(
                0,
                Event(
                    id=f"{qid}-event-birth",
                    person_qid=qid,
                    date=p.birth_date,
                    date_precision="day" if len(p.birth_date) > 7 else "year",  # type: ignore
                    place_name=p.birth_place,
                    event_type="出生",
                    title_zh="出生",
                    description_zh=f"生于 {p.birth_place or '未知地点'}",
                    sources=[f"https://www.wikidata.org/wiki/{qid}"],
                    status="verified",
                ),
            )
        if p.death_date and not has_death:
            evs.append(
                Event(
                    id=f"{qid}-event-death",
                    person_qid=qid,
                    date=p.death_date,
                    date_precision="day" if len(p.death_date) > 7 else "year",  # type: ignore
                    place_name=getattr(p, "death_place", None),
                    event_type="逝世",
                    title_zh="逝世",
                    description_zh=f"卒于 {getattr(p, 'death_place', None) or '未知地点'}",
                    sources=[f"https://www.wikidata.org/wiki/{qid}"],
                    status="verified",
                ),
            )

        # sources enrich (only when enabled)
        if sources_enabled and _enrich_person is not None:
            try:
                title_hint = None
                lm = label_map.get(qid)
                if isinstance(lm, dict):
                    title_hint = lm.get("zhwiki_title")
                # need raw_dir for cache
                cache_dir = raw_dir if raw_dir is not None else Path("data/raw")
                enrich_res = _enrich_person(
                    qid, client, cache_dir=cache_dir, enabled_sources=sources_enabled, title_hint=title_hint
                )
                patch = enrich_res.get("patch", {})
                if not p.summary_zh and patch.get("summary_zh"):
                    p.summary_zh = patch["summary_zh"]
                pp2 = patch.get("person_patch", {}) or {}
                if pp2:
                    if not p.birth_date and pp2.get("birth_date"):
                        p.birth_date = pp2["birth_date"]
                    if not p.death_date and pp2.get("death_date"):
                        p.death_date = pp2["death_date"]
                    if not p.birth_place and pp2.get("birth_place"):
                        p.birth_place = pp2["birth_place"]
                    if not getattr(p, "death_place", None) and pp2.get("death_place"):
                        p.death_place = pp2["death_place"]  # type: ignore
                    if pp2.get("occupations"):
                        existing = set(p.occupations or [])
                        for oc in pp2["occupations"]:
                            if oc not in existing:
                                p.occupations.append(oc)
                for u in patch.get("extra_source_urls", []) or []:
                    if u and u not in p.source_urls:
                        p.source_urls.append(u)
                extra_evs: list[Event] = []
                extra_evs.extend(patch.get("events_from_wiki", []) or [])
                extra_evs.extend(patch.get("events_from_wikidata", []) or [])
                if extra_evs:
                    seen_local = {e.title_zh for e in evs}
                    for ae in extra_evs:
                        if ae.title_zh not in seen_local:
                            ae.id = f"{qid}-event-{len(evs)+1}"
                            evs.append(ae)
                            seen_local.add(ae.title_zh)
                if sources_cache and raw_dir is not None:
                    try:
                        (raw_dir / f"{qid}.enrich.json").write_text(
                            json.dumps(
                                {
                                    "qid": qid,
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
                diagnostics.setdefault("enrich_errors", []).append(f"{qid}:{e}")

        events_out.extend(evs)
        # status logic (preserve original)
        p.status = "ai_filled" if not p.summary_zh else "needs_review"
        if not p.birth_date:
            p.needs_review_reason = "缺生卒年/地点，需补"
        persons_out.append(p)

    diagnostics["persons_out"] = len(persons_out)
    diagnostics["events_out"] = len(events_out)
    diagnostics["endeavors_out"] = len(endeavors_out)
    return {"persons": persons_out, "events": events_out, "endeavors": endeavors_out}, diagnostics


def run(inputs: dict, cfg: dict) -> tuple[dict, dict]:
    return build_domain(
        batch_persons=inputs.get("batch_persons", []),
        sig_map=inputs.get("sig_map", {}),
        pos_map=inputs.get("pos_map", {}),
        label_map=inputs.get("label_map", {}),
        seed_meta=inputs.get("seed_meta", {}),
        offline_map=inputs.get("offline_map", {}),
        classical_map=inputs.get("classical_map", {}),
        cfg=cfg,
        client=inputs.get("client"),
        raw_dir=inputs.get("raw_dir"),
    )
