"""link stage — (inputs,cfg)->(outputs,diagnostics).

用 core.dates.in_range 替代 naive int比较，对无日期 endeavor 标记 needs_review.
"""
from __future__ import annotations

from typing import Any

from arcvita.core.dates import in_range
from arcvita.models import Endeavor, Event


def link_stage(
    events: list[Event],
    endeavors: list[Endeavor],
    cfg: dict | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    diagnostics: dict[str, Any] = {"linked": 0, "needs_review": [], "unlinked_events": 0}
    # mark endeavors without dates as needs_review
    for ed in endeavors:
        if not ed.start_date or not ed.end_date:
            # mark as needs_review (preserve original ai_filled else -> needs_review)
            if ed.review_status != "needs_review":
                ed.review_status = "needs_review"
            diagnostics["needs_review"].append(ed.id)
        else:
            # also validate date parsing; if in_range fails due to unparsable, mark
            from arcvita.core.dates import year_of

            if year_of(ed.start_date) is None or year_of(ed.end_date) is None:
                ed.review_status = "needs_review"
                diagnostics["needs_review"].append(ed.id)

    # group endeavors by person for faster lookup
    ed_by_person: dict[str, list[Endeavor]] = {}
    for ed in endeavors:
        ed_by_person.setdefault(ed.person_qid, []).append(ed)

    for ev in events:
        if ev.endeavor_id:
            continue
        if not ev.date:
            diagnostics["unlinked_events"] += 1
            continue
        person_eds = ed_by_person.get(ev.person_qid, [])
        linked = False
        for ed in person_eds:
            if not ed.start_date or not ed.end_date:
                continue
            try:
                if in_range(ev.date, ed.start_date, ed.end_date):
                    ev.endeavor_id = ed.id
                    ed.event_ids.append(ev.id)
                    diagnostics["linked"] += 1
                    linked = True
                    break
            except Exception:
                continue
        if not linked:
            diagnostics["unlinked_events"] += 1

    return {"events": events, "endeavors": endeavors}, diagnostics


def run(inputs: dict, cfg: dict) -> tuple[dict, dict]:
    events: list[Event] = inputs.get("events", [])
    endeavors: list[Endeavor] = inputs.get("endeavors", [])
    return link_stage(events, endeavors, cfg)
