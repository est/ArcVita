"""准入校验：确保 site 数据完整性"""
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parents[1]
SITE = ROOT / "site" / "data"
PROCESSED = ROOT / "data" / "processed"

def test_index_json_exists():
    assert (SITE / "index.json").exists(), "index.json not found"

def test_index_has_centuries():
    idx = json.load(open(SITE / "index.json"))
    assert "centuries" in idx, "no centuries key"
    assert len(idx["centuries"]) > 0, "no century groups"
    assert len(idx["persons"]) > 0, "no persons"

def test_century_files_are_valid_json():
    """每个世纪文件必须是有效的 JSON 数组，内含人物数据"""
    idx = json.load(open(SITE / "index.json"))
    errors = []
    all_persons = []
    for ck, info in idx["centuries"].items():
        fpath = SITE / f"{ck}.json"
        if not fpath.exists():
            errors.append(f"{ck}: file not found")
            continue
        try:
            data = json.loads(fpath.read_text(encoding="utf-8"))
            assert isinstance(data, list), f"{ck}: not a list"
            assert len(data) == info["count"], f"{ck}: count mismatch {len(data)} vs {info['count']}"
            for p in data:
                assert "qid" in p, f"{ck}: missing qid"
                assert "events" in p and isinstance(p["events"], list), f"{p.get('name_zh','?')}: events not list"
                assert "endeavors" in p and isinstance(p["endeavors"], list), f"{p.get('name_zh','?')}: endeavors not list"
            all_persons.extend(data)
        except json.JSONDecodeError as e:
            errors.append(f"{ck}: invalid JSON: {e}")
    # verify all persons are accounted for
    assert len(all_persons) == len(idx["persons"]), f"person count mismatch: {len(all_persons)} vs {len(idx['persons'])}"
    assert not errors, "errors:\n" + "\n".join(errors)

def test_timeline_jsonl_valid():
    tl = SITE / "timeline.jsonl"
    assert tl.exists(), "timeline.jsonl not found"
    lines = tl.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) > 0, "empty"
    for line in lines[:10]:
        d = json.loads(line)
        assert "date" in d and "person_qid" in d

def test_highlights_json_valid():
    hl = SITE / "highlights.json"
    data = json.loads(hl.read_text(encoding="utf-8"))
    assert isinstance(data, list) and len(data) > 0
    # should have both person and context highlights
    person_hl = [h for h in data if h.get("person_qid") != "_context"]
    context_hl = [h for h in data if h.get("person_qid") == "_context"]
    assert len(person_hl) > 0, "no person highlights"
    assert len(context_hl) > 0, "no historical context highlights"

def test_no_stale_year_dirs():
    """不应有旧的按年份目录结构"""
    for entry in SITE.iterdir():
        if entry.is_dir() and entry.name not in ("chunks",):
            # should not have directories with person YAML/JSON
            assert not any(entry.glob("*.yaml")), f"YAML in dir: {entry}"
            assert not any(entry.glob("*.json")), f"JSON in dir: {entry} (should be merged into century files)"

def test_processed_yamls_exist():
    for name in ("persons.yaml", "events.yaml", "highlights.yaml"):
        assert (PROCESSED / name).exists(), f"{name} not found"


def test_persons_no_duplicate_and_dates_parseable():
    import yaml
    from arcvita.core.dates import year_of

    persons = yaml.safe_load((PROCESSED / "persons.yaml").read_text(encoding="utf-8"))
    names = [p["name_zh"] for p in persons]
    assert len(names) == len(set(names)), f"duplicate name_zh: {[n for n in names if names.count(n) > 1]}"
    qids = [p["qid"] for p in persons]
    assert len(qids) == len(set(qids)), f"duplicate qid"
    # 合传已拆：不应再有复合日期含 "/"
    for p in persons:
        bd = p.get("birth_date") or ""
        dd = p.get("death_date") or ""
        assert "/" not in bd and "/" not in dd, f"composite date still present: {p['name_zh']} {bd}/{dd}"
        assert year_of(bd) is not None, f"birth_date unparsable: {p['name_zh']} {bd}"
    # 卫青/霍去病已拆为两条
    assert any(p["name_zh"] == "卫青" for p in persons), "卫青 missing after split"
    assert any(p["name_zh"] == "霍去病" for p in persons), "霍去病 missing after split"
    assert sum(1 for p in persons if p["name_zh"] == "秦始皇") == 1, "秦始皇 still duplicated"


def test_events_dates_parseable():
    import yaml
    from arcvita.core.dates import year_of

    events = yaml.safe_load((PROCESSED / "events.yaml").read_text(encoding="utf-8"))
    # 仅允许曹沫不详一条未知
    unknowns = [e for e in events if year_of(e.get("date")) is None]
    assert len(unknowns) <= 1, f"too many unparsable event dates: {unknowns[:5]}"
    for e in events:
        if year_of(e.get("date")) is None:
            assert e["person_qid"] == "guji-曹沫", f"unexpected unparsable: {e}"


def test_yaml_block_style():
    # 块式标准：无流式 [] {}、外层无双引号
    import re

    for name in ("persons.yaml", "events.yaml", "endeavors.yaml", "highlights.yaml"):
        text = (PROCESSED / name).read_text(encoding="utf-8")
        # 空流式 [] 应被 strip_empty 省略，若残留则为违规
        assert "[]\n" not in text and ": []" not in text, f"{name} contains flow []"
        assert "{}\n" not in text, f"{name} contains flow {{}}"
        # 外层双引号包裹的 value（块式应为 plain 或单引号）
        # 检测行末 ": \"...\"" 形式
        assert not re.search(r':\s+\"[^\"]*\"', text), f"{name} contains double-quoted scalar"
