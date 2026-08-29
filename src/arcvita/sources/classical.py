"""古籍传记适配器：从 extracted YAML 读取补丁"""
from __future__ import annotations
import yaml, pathlib
from typing import Any

EXTRACTED_DIRS = [pathlib.Path("data/extracted/pre_qin"), pathlib.Path("data/extracted/qin_han")]
_curated_cache: dict[str, dict] = {}


def _load_all():
    global _curated_cache
    if _curated_cache:
        return
    for d in EXTRACTED_DIRS:
        if not d.exists():
            continue
        for f in d.glob("*.yaml"):
            try:
                data = yaml.safe_load(f.read_text(encoding="utf-8"))
                if data and isinstance(data, dict) and "person" in data:
                    name = data["person"].get("name_zh", "")
                    if name:
                        _curated_cache[name] = data
            except Exception:
                continue


def fetch_classical_for_name(name_zh: str) -> dict[str, Any] | None:
    """按姓名查找古籍提取数据，返回可合并的补丁"""
    _load_all()
    data = _curated_cache.get(name_zh)
    if not data:
        return None
    p = data.get("person", {})
    return {
        "source": "classical",
        "found": True,
        "person_patch": {
            "name_zh": p.get("name_zh"),
            "name_en": p.get("name_en"),
            "birth_date": p.get("birth_date"),
            "death_date": p.get("death_date"),
            "birth_place": p.get("birth_place"),
            "era": p.get("era"),
            "archetype": p.get("archetype"),
            "dilemmas": p.get("dilemmas", []),
            "summary_zh": p.get("summary_zh"),
            "summary_first_person": p.get("summary_first_person"),
            "lesson": p.get("lesson"),
        },
        "source_urls": [f"https://daizhige.org/史藏/正史/史记.html"],
        "events_from_classical": data.get("events", []),
        "endeavors_from_classical": data.get("endeavors", []),
    }
