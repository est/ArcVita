"""合并 extracted YAML → curated → persons.yaml"""
from __future__ import annotations

import pathlib

import yaml

EXTRACTED_DIRS = [pathlib.Path("data/extracted/pre_qin"), pathlib.Path("data/extracted/qin_han"), pathlib.Path("data/extracted/king_tables")]
CURATED_DIR = pathlib.Path("data/curated/classical")


def load_extracted() -> list[dict]:
    """加载所有 extracted YAML"""
    results = []
    for d in EXTRACTED_DIRS:
        if not d.exists():
            continue
        for f in sorted(d.glob("*.yaml")):
            try:
                data = yaml.safe_load(f.read_text(encoding="utf-8"))
                if isinstance(data, dict) and "person" in data:
                    results.append(data)
                elif isinstance(data, list):
                    for item in data:
                        if isinstance(item, dict) and "person" in item:
                            results.append(item)
            except Exception as e:
                print(f"  skip {f.name}: {e}")
    return results


def validate_person(data: dict) -> list[str]:
    """校验人物数据完整性"""
    issues = []
    p = data.get("person", {})
    if not p.get("name_zh"):
        issues.append("缺 name_zh")
    if not p.get("birth_date") and not p.get("era"):
        issues.append("缺 birth_date 和 era")
    data.get("endeavors", [])
    evs = data.get("events", [])
    if len(evs) < 2:
        issues.append(f"events 仅 {len(evs)} 条，信息不足")
    if not any(ev.get("place_name") for ev in evs):
        issues.append("所有事件缺地点")
    return issues


def score_person(data: dict) -> float:
    """信息密度评分（高分优先）"""
    p = data.get("person", {})
    eds = data.get("endeavors", [])
    evs = data.get("events", [])
    hl = sum(1 for e in evs if e.get("is_highlight"))
    places = len(set(e.get("place_name") for e in evs if e.get("place_name")))
    has_fp = 1 if p.get("summary_first_person") else 0
    has_lesson = 1 if p.get("lesson") else 0
    phases = sum(len(ed.get("phases", [])) for ed in eds)
    return len(evs) * 1.0 + hl * 2.0 + places * 0.5 + has_fp + has_lesson + phases * 0.5


def merge_to_curated():
    """合并 extracted → curated 目录"""
    CURATED_DIR.mkdir(parents=True, exist_ok=True)
    extracted = load_extracted()
    print(f"loaded {len(extracted)} extracted persons")

    for data in extracted:
        p = data.get("person", {})
        name = p.get("name_zh", "unknown")
        issues = validate_person(data)
        data["_score"] = score_person(data)
        data["_issues"] = issues

        # Write to curated
        out = CURATED_DIR / f"{name}.yaml"
        out.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False, width=100), encoding="utf-8")

        status = "✓" if not issues else f"⚠ {', '.join(issues)}"
        print(f"  {name}: score={data['_score']:.1f} {status}")

    # Summary
    reviewed = [d for d in extracted if not d["_issues"]]
    needs_review = [d for d in extracted if d["_issues"]]
    print(f"\nreviewed: {len(reviewed)}, needs_review: {len(needs_review)}")
    for d in needs_review:
        p = d["person"]
        print(f"  {p.get('name_zh')}: {', '.join(d['_issues'])}")

    return extracted


def update_seed_and_pipeline(extracted: list[dict]):
    """将 merged 数据追加到 seed_persons.yaml 和 curated.py"""
    seed_path = pathlib.Path("data/seed_persons.yaml")
    seed = yaml.safe_load(seed_path.read_text(encoding="utf-8")) or {"persons": []}
    existing_qids = {p["qid"] for p in seed.get("persons", [])}

    for data in extracted:
        p = data.get("person", {})
        name = p.get("name_zh", "")
        qid = f"guji-{name}"
        if qid in existing_qids:
            continue
        seed["persons"].append({
            "name_zh": name,
            "qid": qid,
            "role": "模范",  # default
        })
        existing_qids.add(qid)

    seed_path.write_text(yaml.safe_dump(seed, allow_unicode=True, sort_keys=False, width=100), encoding="utf-8")
    print(f"seed updated: {len(seed['persons'])} persons")


if __name__ == "__main__":
    extracted = merge_to_curated()
    update_seed_and_pipeline(extracted)
