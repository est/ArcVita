"""准入校验：确保 site 数据完整性"""
import json, pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
SITE = ROOT / "site" / "data"
PROCESSED = ROOT / "data" / "processed"

def test_index_json_exists():
    assert (SITE / "index.json").exists(), "index.json not found"

def test_index_has_years():
    idx = json.load(open(SITE / "index.json"))
    assert len(idx["years"]) > 0, "no year directories"
    assert len(idx["persons"]) > 0, "no persons"

def test_person_files_are_json():
    idx = json.load(open(SITE / "index.json"))
    errors = []
    for p in idx["persons"]:
        fpath = SITE / p["year_dir"] / f"{p['name_zh']}.json"
        if not fpath.exists():
            errors.append(f"{p['name_zh']}: file not found at {fpath}")
            continue
        try:
            data = json.loads(fpath.read_text(encoding="utf-8"))
            assert "qid" in data
            assert "events" in data and isinstance(data["events"], list)
            assert "endeavors" in data and isinstance(data["endeavors"], list)
        except json.JSONDecodeError as e:
            errors.append(f"{p['name_zh']}: invalid JSON: {e}")
    assert not errors, f"errors:\n" + "\n".join(errors)

def test_timeline_jsonl_valid():
    tl = SITE / "timeline.jsonl"
    assert tl.exists(), "timeline.jsonl not found"
    lines = tl.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) > 0, "empty"
    for i, line in enumerate(lines[:10]):
        d = json.loads(line)
        assert "date" in d and "person_qid" in d

def test_highlights_json_valid():
    hl = SITE / "highlights.json"
    data = json.loads(hl.read_text(encoding="utf-8"))
    assert isinstance(data, list) and len(data) > 0

def test_no_yaml_in_year_dirs():
    idx = json.load(open(SITE / "index.json"))
    for p in idx["persons"]:
        yf = SITE / p["year_dir"] / f"{p['name_zh']}.yaml"
        assert not yf.exists(), f"YAML found: {yf} (should be JSON)"

def test_processed_yamls_exist():
    for name in ("persons.yaml", "events.yaml", "highlights.yaml"):
        assert (PROCESSED / name).exists(), f"{name} not found"
