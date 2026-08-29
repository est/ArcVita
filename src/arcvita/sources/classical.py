"""古籍传记适配器：从 extracted YAML 读取补丁（Adapter 形式）"""
from __future__ import annotations

import pathlib
from typing import Any

import yaml

from arcvita.models import Event
from arcvita.sources.base import FetchContext, FetchPatch

EXTRACTED_DIRS = [pathlib.Path("data/extracted/pre_qin"), pathlib.Path("data/extracted/qin_han"), pathlib.Path("data/extracted/king_tables")]
_curated_cache: dict[str, dict] = {}


def _load_all() -> None:
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


def _resolve_name_for_qid(qid: str) -> str | None:
    """按 qid 解析 name_zh：优先 guji- 前缀，其次 curated OFFLINE/seed 回落。"""
    if qid.startswith("guji-"):
        return qid[5:]
    # 尝试 curated OFFLINE 回落
    try:
        from arcvita.curated import OFFLINE

        if qid in OFFLINE:
            n = OFFLINE[qid].get("name_zh")
            if n:
                return n
    except Exception:
        pass
    # 尝试 seed
    try:
        from arcvita.config import load_seed

        for s in load_seed():
            if s.get("qid") == qid:
                return s.get("name_zh")
    except Exception:
        pass
    return None


def fetch_classical_for_name(name_zh: str) -> dict[str, Any] | None:
    """按姓名查找古籍提取数据，返回可合并的补丁（兼容旧 pipeline 调用）。"""
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
        "source_urls": ["https://daizhige.org/史藏/正史/史记.html"],
        "events_from_classical": data.get("events", []),
        "endeavors_from_classical": data.get("endeavors", []),
    }


# ---------------------------------------------------------------------------
# Adapter 实现
# ---------------------------------------------------------------------------

class ClassicalAdapter:
    """古籍 Adapter — id 规范为 classical，实现 SourceAdapter 协议。"""

    id: str = "classical"

    def fetch(self, qid: str, ctx: FetchContext) -> FetchPatch | None:
        name = _resolve_name_for_qid(qid)
        if not name:
            return None
        patch = fetch_classical_for_name(name)
        if not patch or not patch.get("found"):
            return None
        # 转为 FetchPatch 形态：person_patch + events(list[Event]) + source_urls
        person_patch = patch.get("person_patch", {})
        # events: dict -> Event
        raw_events = patch.get("events_from_classical", [])
        events: list[Event] = []
        for idx, ev in enumerate(raw_events, 1):
            try:
                events.append(
                    Event(
                        id=f"{qid}-event-classical-{idx}",
                        person_qid=qid,
                        date=ev.get("date"),
                        date_precision="day" if ev.get("date") and len(str(ev["date"])) > 7 else "year",  # type: ignore
                        place_name=ev.get("place_name"),
                        event_type=ev.get("event_type", "经历"),
                        title_zh=ev.get("title_zh", ""),
                        description_zh=ev.get("description_zh"),
                        is_highlight=bool(ev.get("is_highlight", False)),
                        highlight_type=ev.get("highlight_type"),
                        highlight_note=ev.get("highlight_note"),
                        sources=["https://daizhige.org/史藏/正史/史记.html"],
                        status="ai_filled",
                    )
                )
            except Exception:
                continue
        return {
            "source": "classical",
            "person_patch": person_patch,
            "events": events,
            "source_urls": patch.get("source_urls", []),
            "raw": patch,
            "events_from_classical": raw_events,
            "endeavors_from_classical": patch.get("endeavors_from_classical", []),
        }
