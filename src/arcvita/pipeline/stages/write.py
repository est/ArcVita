"""write stage — side-effect stage. (inputs,cfg)->(outputs,diagnostics).

只在此阶段写盘: YAML + SQLite + report + timelines/highlights.
调用 store.build_db / render.build_* 需参数化路径.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from arcvita.models import Endeavor, Event, Person


def _dump_yaml(path: Path, items: list[Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = [it.model_dump(exclude_none=False) if hasattr(it, "model_dump") else it for it in items]
    path.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False, width=100), encoding="utf-8")


def write_stage(
    persons: list[Person],
    events: list[Event],
    endeavors: list[Endeavor],
    cfg: dict,
    out_dir: Path | None = None,
    raw_batches: list[dict] | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    paths = cfg.get("paths", {})
    # resolve paths: if out_dir is given, redirect there
    if out_dir is not None:
        out = Path(out_dir)
        out.mkdir(parents=True, exist_ok=True)
        persons_yaml = out / "persons.yaml"
        events_yaml = out / "events.yaml"
        endeavors_yaml = out / "endeavors.yaml"
        db_path = out / "biography.db"
        report_path = out / "_report.md"
        highlights_yaml = out / "highlights.yaml"
        timelines_dir = out / "timelines"
        raw_dir = out / "raw"
    else:
        persons_yaml = Path(paths.get("persons_yaml", "data/processed/persons.yaml"))
        events_yaml = Path(paths.get("events_yaml", "data/processed/events.yaml"))
        endeavors_yaml = Path(paths.get("endeavors_yaml", "data/processed/endeavors.yaml"))
        db_path = Path(paths.get("db", "data/biography.db"))
        highlights_yaml = Path(paths.get("highlights_yaml", "data/processed/highlights.yaml"))
        timelines_dir = Path(paths.get("timelines_dir", "data/processed/timelines"))
        raw_dir = Path(paths.get("raw_dir", "data/raw"))
        report_path = Path("data/processed/_report.md")

    diagnostics: dict[str, Any] = {}

    persons_yaml.parent.mkdir(parents=True, exist_ok=True)
    events_yaml.parent.mkdir(parents=True, exist_ok=True)

    _dump_yaml(persons_yaml, persons)
    _dump_yaml(events_yaml, events)
    _dump_yaml(endeavors_yaml, endeavors)
    diagnostics["yaml_written"] = {
        "persons": str(persons_yaml),
        "events": str(events_yaml),
        "endeavors": str(endeavors_yaml),
    }

    # write raw batches if provided (during orchestrator)
    if raw_batches:
        raw_dir.mkdir(parents=True, exist_ok=True)
        for entry in raw_batches:
            bid = entry.get("batch_id", 0)
            qids = entry.get("qids", [])
            label_map = entry.get("label_map", {})
            import json

            (raw_dir / f"batch_{bid}.json").write_text(
                json.dumps({"qids": qids, "label_map": label_map}, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

    # SQLite build (parameterized)
    from arcvita.store import build_db

    build_db(db_path, persons, events, endeavors)
    diagnostics["db"] = str(db_path)

    # report
    from arcvita.report import write_report

    write_report(persons, events, endeavors, report_path)
    diagnostics["report"] = str(report_path)

    # render: highlights + timelines parameterized
    try:
        from arcvita.render import build_highlights, build_timelines

        # build_highlights/build_timelines now accept optional paths; fallback to defaults if not provided
        # we call with explicit paths to keep out_dir isolated
        highlights_count = build_highlights(db_path=db_path, out_path=highlights_yaml)
        timelines_count = build_timelines(db_path=db_path, out_dir=timelines_dir)
        diagnostics["highlights"] = highlights_count
        diagnostics["timelines"] = timelines_count
    except Exception as e:
        diagnostics["render_error"] = str(e)

    return {"ok": True}, diagnostics


def run(inputs: dict, cfg: dict) -> tuple[dict, dict]:
    persons = inputs.get("persons", [])
    events = inputs.get("events", [])
    endeavors = inputs.get("endeavors", [])
    out_dir = inputs.get("out_dir")
    if isinstance(out_dir, str):
        out_dir = Path(out_dir) if out_dir else None
    raw_batches = inputs.get("raw_batches")
    return write_stage(persons, events, endeavors, cfg, out_dir=out_dir, raw_batches=raw_batches)
