from __future__ import annotations

import json
import pathlib
import sqlite3
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data/processed"
SITE = ROOT / "site"
DB = ROOT / "data/biography.db"


def load_yaml(p: pathlib.Path):
    return yaml.safe_load(p.read_text(encoding="utf-8")) if p.exists() else []


def main():
    persons = load_yaml(PROCESSED / "persons.yaml") or []
    events = load_yaml(PROCESSED / "events.yaml") or []
    endeavors = load_yaml(PROCESSED / "endeavors.yaml") or []
    highlights = load_yaml(PROCESSED / "highlights.yaml") or []

    SITE.mkdir(parents=True, exist_ok=True)
    data_dir = SITE / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    # JSONL: one line per event ordered by date (lexicographic ~ timeline, BCE handled by minus sign)
    # 前端直接按行加载，无限滚动
    def date_key(e):
        d = e.get("date") or "9999"
        # BCE: -YYYY -> sort before CE
        return d

    events_sorted = sorted(events, key=date_key)
    # persons lookup
    pmap = {p["qid"]: p for p in persons}

    # Build timeline.jsonl: each line is a compact event with person + endeavor + highlight flag
    tl_path = data_dir / "timeline.jsonl"
    with tl_path.open("w", encoding="utf-8") as f:
        for e in events_sorted:
            p = pmap.get(e["person_qid"], {})
            f.write(
                json.dumps(
                    {
                        "date": e.get("date"),
                        "place": e.get("place_name"),
                        "title": e.get("title_zh"),
                        "type": e.get("event_type"),
                        "is_highlight": bool(e.get("is_highlight")),
                        "highlight_type": e.get("highlight_type"),
                        "highlight_note": e.get("highlight_note"),
                        "person_qid": e.get("person_qid"),
                        "person": p.get("name_zh"),
                        "archetype": p.get("archetype"),
                        "era": p.get("era"),
                        "endeavor_id": e.get("endeavor_id"),
                        "description": e.get("description_zh"),
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )

    # endeavors.jsonl: 成事儿周期，便于前端按人物展开
    ed_path = data_dir / "endeavors.jsonl"
    with ed_path.open("w", encoding="utf-8") as f:
        for ed in sorted(endeavors, key=lambda x: (x.get("person_qid", ""), x.get("start_date") or "9999")):
            f.write(json.dumps(ed, ensure_ascii=False) + "\n")

    # highlights.json: 名场面聚合
    (data_dir / "highlights.json").write_text(json.dumps(highlights, ensure_ascii=False, indent=2), encoding="utf-8")
    # persons.json: 轻量人物索引
    persons_lite = [
        {
            "qid": p["qid"],
            "name_zh": p["name_zh"],
            "era": p.get("era"),
            "archetype": p.get("archetype"),
            "role": p.get("role"),
            "dilemmas": p.get("dilemmas", []),
            "summary_zh": p.get("summary_zh"),
        }
        for p in persons
    ]
    (data_dir / "persons.json").write_text(json.dumps(persons_lite, ensure_ascii=False, indent=2), encoding="utf-8")

    # manifest for infinite loader: chunks of timeline.jsonl
    CHUNK = 60
    chunks = []
    lines = tl_path.read_text(encoding="utf-8").splitlines()
    for i in range(0, len(lines), CHUNK):
        chunk_path = data_dir / f"chunks/timeline.{i//CHUNK:03d}.json"
        chunk_path.parent.mkdir(parents=True, exist_ok=True)
        chunk = [json.loads(l) for l in lines[i : i + CHUNK]]
        chunk_path.write_text(json.dumps(chunk, ensure_ascii=False, indent=2), encoding="utf-8")
        chunks.append(f"data/chunks/timeline.{i//CHUNK:03d}.json")
    (data_dir / "manifest.json").write_text(
        json.dumps({"total_events": len(lines), "chunk_size": CHUNK, "chunks": chunks, "total_persons": len(persons), "highlights": len(highlights)}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    # Copy raw YAML as artifacts too
    for name in ("persons.yaml", "events.yaml", "endeavors.yaml", "highlights.yaml"):
        src = PROCESSED / name
        if src.exists():
            (data_dir / name).write_bytes(src.read_bytes())

    print(f"site built: {len(events)} events -> {tl_path} + {len(chunks)} chunks")
    print(f"highlights: {len(highlights)}, persons: {len(persons)}")
    return {"events": len(events), "chunks": len(chunks), "highlights": len(highlights)}


if __name__ == "__main__":
    main()
