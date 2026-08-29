"""E2E pipeline with _tmp isolation: --limit 2 --out _tmp/e2e"""
from __future__ import annotations

import sqlite3
from pathlib import Path

import yaml

from arcvita.pipeline import run_pipeline


def test_pipeline_e2e_tmp_isolation(tmp_path: Path):
    # Use project _tmp/e2e isolation -- respect constraint: only write _tmp
    out = Path("_tmp/e2e")
    # clean
    if out.exists():
        import shutil
        shutil.rmtree(out)
    out.mkdir(parents=True, exist_ok=True)

    res = run_pipeline(limit=2, out_dir=out)
    assert res["persons"] == 2
    assert res["events"] >= 2
    assert (out / "persons.yaml").exists()
    assert (out / "events.yaml").exists()
    assert (out / "endeavors.yaml").exists()
    assert (out / "highlights.yaml").exists()
    assert (out / "biography.db").exists()
    assert (out / "_report.md").exists()

    persons = yaml.safe_load((out / "persons.yaml").read_text(encoding="utf-8"))
    assert isinstance(persons, list) and len(persons) == 2
    for p in persons:
        assert "qid" in p and "name_zh" in p

    highlights = yaml.safe_load((out / "highlights.yaml").read_text(encoding="utf-8"))
    assert isinstance(highlights, list)

    # SQLite checks
    con = sqlite3.connect(out / "biography.db")
    cur = con.cursor()
    cur.execute("SELECT count(*) FROM persons")
    assert cur.fetchone()[0] == 2
    cur.execute("SELECT count(*) FROM events")
    assert cur.fetchone()[0] >= 2
    cur.execute("SELECT count(*) FROM endeavors")
    # endeavors may be 0..n
    assert cur.fetchone()[0] >= 0
    con.close()

    # timelines
    assert (out / "timelines").exists()
    mds = list((out / "timelines").glob("*.md"))
    assert len(mds) == 2

    # ensure no external write leakage: data/processed still exists separately
    # but out isolation is verified by out path


def test_pipeline_cli_out(tmp_path: Path):
    """CLI --out path also works via subprocess."""
    import subprocess
    import sys

    out = Path("_tmp/e2e_cli")
    if out.exists():
        import shutil
        shutil.rmtree(out)
    out.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(
        [sys.executable, "-m", "arcvita.cli", "--limit", "2", "--out", str(out)],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
    assert (out / "persons.yaml").exists()
    assert (out / "biography.db").exists()
