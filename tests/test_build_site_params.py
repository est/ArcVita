"""build_site parameterized with _tmp isolation"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.build_site import build_site  # noqa: E402


def test_build_site_params_tmp_isolation(tmp_path: Path):
    # prepare isolated processed_dir under _tmp
    processed = Path("_tmp/build_site_processed")
    site_data = Path("_tmp/build_site_out")
    # clean
    import shutil
    for p in (processed, site_data):
        if p.exists():
            shutil.rmtree(p)
        p.mkdir(parents=True, exist_ok=True)

    # minimal synthetic data
    persons = [
        {"qid": "Q1", "name_zh": "测试A", "birth_date": "1900-01-01", "era": "现代", "archetype": "测试型"},
        {"qid": "Q2", "name_zh": "测试B", "birth_date": "-500-01-01", "era": "春秋", "archetype": "测试型"},
    ]
    events = [
        {"person_qid": "Q1", "date": "1920-01-01", "place_name": "北京", "title_zh": "事件A", "event_type": "经历"},
        {"person_qid": "Q2", "date": "-480-01-01", "place_name": "曲阜", "title_zh": "事件B", "event_type": "经历"},
    ]
    endeavors = [
        {"person_qid": "Q1", "title_zh": "事业A", "start_date": "1920", "end_date": "1930", "places": ["北京"]},
    ]
    highlights = [
        {"person_qid": "Q1", "date": "1920-01-01", "title_zh": "高光A", "highlight_type": "代表作"},
    ]

    for name, data in [("persons.yaml", persons), ("events.yaml", events), ("endeavors.yaml", endeavors), ("highlights.yaml", highlights)]:
        (processed / name).write_text(yaml.safe_dump(data, allow_unicode=True), encoding="utf-8")

    res = build_site(processed, site_data)
    assert res["persons"] == 2
    assert (site_data / "index.json").exists()
    idx = json.loads((site_data / "index.json").read_text(encoding="utf-8"))
    # shape validation: centuries/persons/count consistent
    total = sum(v["count"] for v in idx["centuries"].values())
    assert total == len(idx["persons"]) == 2
    for ck, info in idx["centuries"].items():
        assert info["count"] == len(info["persons"])
        assert (site_data / f"{ck}.json").exists()
    # timeline/highlights exist
    assert (site_data / "timeline.jsonl").exists()
    assert (site_data / "highlights.json").exists()


def test_build_site_from_real_processed(tmp_path: Path):
    """Use real pipeline out as processed to ensure integration."""
    from arcvita.pipeline import run_pipeline

    out_proc = Path("_tmp/build_site_real_proc")
    out_site = Path("_tmp/build_site_real_site")
    import shutil
    for p in (out_proc, out_site):
        if p.exists():
            shutil.rmtree(p)
    out_proc.mkdir(parents=True, exist_ok=True)

    run_pipeline(limit=2, out_dir=out_proc)
    res = build_site(out_proc, out_site)
    assert res["persons"] == 2
    idx = json.loads((out_site / "index.json").read_text(encoding="utf-8"))
    assert "centuries" in idx and "persons" in idx
    assert sum(v["count"] for v in idx["centuries"].values()) == len(idx["persons"])
