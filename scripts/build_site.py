from __future__ import annotations

import json, pathlib, re
import yaml

ROOT = pathlib.Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data/processed"
SITE = ROOT / "site"


def load_yaml(p: pathlib.Path):
    return yaml.safe_load(p.read_text(encoding="utf-8")) if p.exists() else []


def parse_year(s):
    if not s:
        return None
    m = re.match(r"^(-?\d+)", s.replace("约", "").strip())
    return int(m.group(1)) if m else None


def year_dir(y):
    if y is None:
        return "unknown"
    return f"-{abs(y):04d}" if y < 0 else f"{y:04d}"


def main():
    persons = load_yaml(PROCESSED / "persons.yaml") or []
    events = load_yaml(PROCESSED / "events.yaml") or []
    endeavors = load_yaml(PROCESSED / "endeavors.yaml") or []
    highlights = load_yaml(PROCESSED / "highlights.yaml") or []

    SITE.mkdir(parents=True, exist_ok=True)
    data = SITE / "data"
    data.mkdir(parents=True, exist_ok=True)

    pmap = {p["qid"]: p for p in persons}

    # === timeline.jsonl (events sorted by date) ===
    events_sorted = sorted(events, key=lambda e: e.get("date") or "9999")
    tl = data / "timeline.jsonl"
    with tl.open("w", encoding="utf-8") as f:
        for e in events_sorted:
            p = pmap.get(e["person_qid"], {})
            f.write(json.dumps({
                "date": e.get("date"), "place": e.get("place_name"),
                "title": e.get("title_zh"), "type": e.get("event_type"),
                "is_highlight": bool(e.get("is_highlight")),
                "highlight_type": e.get("highlight_type"),
                "highlight_note": e.get("highlight_note"),
                "person_qid": e.get("person_qid"), "person": p.get("name_zh"),
                "archetype": p.get("archetype"), "era": p.get("era"),
                "description": e.get("description_zh"),
            }, ensure_ascii=False) + "\n")

    # === highlights.json ===
    (data / "highlights.json").write_text(
        json.dumps(sorted(highlights, key=lambda h: h.get("date") or "9999"), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    # === per-person JSON in year_dir ===
    index_years = {}
    for p in sorted(persons, key=lambda x: parse_year(x.get("birth_date")) or 9999):
        by = parse_year(p.get("birth_date"))
        d = year_dir(by)
        p_ys = sorted([e for e in events if e.get("person_qid") == p["qid"]], key=lambda e: e.get("date") or "9999")
        p_ed = sorted([e for e in endeavors if e.get("person_qid") == p["qid"]], key=lambda e: e.get("start_date") or "9999")
        p_hl = sorted([h for h in highlights if h.get("person_qid") == p["qid"]], key=lambda h: h.get("date") or "9999")
        person_data = {
            "qid": p["qid"], "name_zh": p["name_zh"], "name_en": p.get("name_en"),
            "era": p.get("era"), "archetype": p.get("archetype"), "role": p.get("role"),
            "dilemmas": p.get("dilemmas", []), "birth_date": p.get("birth_date"),
            "death_date": p.get("death_date"), "birth_place": p.get("birth_place"),
            "summary_zh": p.get("summary_zh"), "summary_first_person": p.get("summary_first_person"),
            "lesson": p.get("lesson"),
            "events": p_ys, "endeavors": p_ed, "highlights": p_hl,
        }
        out_dir = data / d
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / f"{p['name_zh']}.json").write_text(
            json.dumps(person_data, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        index_years.setdefault(d, []).append(p["name_zh"])

    # === index.json ===
    index = {
        "years": {d: {"count": len(ps), "persons": ps} for d, ps in sorted(index_years.items())},
        "persons": [
            {
                "qid": p["qid"], "name_zh": p["name_zh"], "era": p.get("era"),
                "archetype": p.get("archetype"), "role": p.get("role"),
                "birth_date": p.get("birth_date"), "death_date": p.get("death_date"),
                "summary_first_person": p.get("summary_first_person"),
                "year_dir": year_dir(parse_year(p.get("birth_date"))),
                "events_count": len([e for e in events if e.get("person_qid") == p["qid"]]),
                "highlights_count": len([h for h in highlights if h.get("person_qid") == p["qid"]]),
            }
            for p in sorted(persons, key=lambda x: parse_year(x.get("birth_date")) or 9999)
        ],
    }
    (data / "index.json").write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8")

    # === YAML copy (archive) ===
    for name in ("persons.yaml", "events.yaml", "endeavors.yaml", "highlights.yaml"):
        src = PROCESSED / name
        if src.exists():
            (data / name).write_bytes(src.read_bytes())

    print(f"built: {len(persons)} persons, {len(events)} events, {len(highlights)} highlights")
    for d in sorted(index_years.keys()):
        print(f"  {d}/: {', '.join(index_years[d])}")
    return {"persons": len(persons), "events": len(events), "highlights": len(highlights)}


if __name__ == "__main__":
    main()
