"""统一入口 enrich_person(qid, client)

优先级: curated > wikipedia > wikidata(带缓存)
返回可合并的 Person/Endeavor/Event 补丁，供 pipeline 按需合并。
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import httpx

from arcvita.curated import OFFLINE
from arcvita.models import Endeavor, Event
from arcvita.sources.openalex_wb import fetch_wikidata_for_qid
from arcvita.sources.wikipedia import fetch_wikipedia_for_qid
from arcvita.wikidata import build_events_for_person


def _curated_patch(qid: str) -> dict[str, Any]:
    """curated 永远优先；不作网络请求。"""
    base = OFFLINE.get(qid)
    if not base:
        return {"source": "curated", "found": False}
    return {
        "source": "curated",
        "found": True,
        "person_patch": {
            "name_zh": base.get("name_zh"),
            "name_en": base.get("name_en"),
            "birth_date": base.get("birth_date"),
            "death_date": base.get("death_date"),
            "birth_place": base.get("birth_place"),
            # death_place curated 暂无，留 None
            "summary_zh": base.get("summary_zh"),
            "summary_first_person": base.get("summary_first_person"),
            "lesson": base.get("lesson"),
            "era": base.get("era"),
            "occupations": base.get("occupations", []),
        },
        "source_urls": [f"https://www.wikidata.org/wiki/{qid}"],
    }


def enrich_person(
    qid: str,
    client: httpx.Client | None = None,
    cache_dir: Path | str = "data/raw",
    enabled_sources: list[str] | None = None,
    title_hint: str | None = None,
) -> dict[str, Any]:
    """统一入口：按 enabled_sources 顺序尝试，返回补丁。

    enabled_sources 默认 ["curated", "wikipedia", "wikidata"]，
    可通过 config.yaml sources.enabled 覆盖（如 ["curated"] 即纯离线）。

    返回:
    {
      qid,
      curated: {...} | None,
      wikipedia: {...} | None,  # 含 first_para / highlight_candidates
      wikidata: {...} | None,   # 含 person/sig/pos/labels
      patch: {
        summary_zh?: str,
        summary_first_person?: str,
        extra_source_urls: [...],
        events_from_wiki: [Event...],  # wikipedia 候选转 Event（is_highlight=True）
        events_from_wikidata: [Event...],
        person_patch: {...}  # 合并后可直接用于 Person 补齐
      }
    }
    """
    if enabled_sources is None:
        enabled_sources = ["curated", "wikipedia", "wikidata"]

    cdir = Path(cache_dir)
    result: dict[str, Any] = {"qid": qid, "curated": None, "wikipedia": None, "wikidata": None, "patch": {}}

    # 1. curated（永远先看）
    if "curated" in enabled_sources:
        result["curated"] = _curated_patch(qid)

    # 需要 httpx client 时懒创建
    own_client = False
    if client is None and any(s in enabled_sources for s in ("wikipedia", "wikidata")):
        client = httpx.Client(headers={"User-Agent": "ArcVita/0.1 (biography research; local)"}, timeout=30)
        own_client = True

    try:
        # 2. wikipedia（中文条目 + 名场面候选）
        if "wikipedia" in enabled_sources and client is not None:
            try:
                w = fetch_wikipedia_for_qid(qid, client, cache_dir=cdir, title_hint=title_hint)
                result["wikipedia"] = w
            except Exception as e:
                result["wikipedia"] = {"qid": qid, "error": str(e), "highlight_candidates": []}

        # 3. wikidata（带缓存与指数退避）
        if "wikidata" in enabled_sources and client is not None:
            try:
                wb = fetch_wikidata_for_qid(qid, client, cache_dir=cdir)
                result["wikidata"] = wb
            except Exception as e:
                result["wikidata"] = {"qid": qid, "error": str(e), "person": None}
    finally:
        if own_client and client is not None:
            client.close()

    # ---- 合并为 patch ----
    patch: dict[str, Any] = {"extra_source_urls": []}
    events_from_wiki: list[Event] = []
    events_from_wikidata: list[Event] = []

    # wikipedia -> summary_zh 备选 + source_urls + highlight events
    w = result.get("wikipedia")
    if w and not w.get("error"):
        if w.get("first_para"):
            # 仅当 curated 无 summary 时才用 wikipedia 首段
            curated_summary = (result.get("curated") or {}).get("person_patch", {}).get("summary_zh")
            if not curated_summary:
                patch["summary_zh"] = w["first_para"]
        if w.get("source_urls"):
            patch["extra_source_urls"].extend(w["source_urls"])
        # highlight_candidates -> Event 补丁（is_highlight=True）
        for idx, cand in enumerate(w.get("highlight_candidates", [])[:5], 1):
            sent = cand.get("sentence", "")
            htype = cand.get("highlight_type", "代表作")
            events_from_wiki.append(
                Event(
                    id=f"{qid}-event-wiki-{idx}",
                    person_qid=qid,
                    date=None,
                    date_precision=None,
                    place_name=None,
                    event_type="名场面" if htype in ("成语", "代表作", "名言") else "经历",
                    title_zh=sent[:32] + ("…" if len(sent) > 32 else ""),
                    description_zh=sent,
                    is_highlight=True,
                    highlight_type=htype,  # type: ignore
                    highlight_note=f"Wikipedia 候选句（关键词: {cand.get('keyword')})",
                    sources=w.get("source_urls", [f"https://zh.wikipedia.org/wiki/{qid}"]),
                    status="needs_review",
                    needs_review_reason="Wikipedia 候选，需人工核验时间/出处",
                )
            )

    # wikidata -> person_patch + sig/pos events
    wb = result.get("wikidata")
    if wb and wb.get("person") and not wb.get("error"):
        pp = wb["person"]
        # 仅把可补字段塞进 patch（不覆盖 curated 已有）
        person_patch: dict[str, Any] = {}
        for k in ("name_zh", "name_en", "birth_date", "death_date", "birth_place", "death_place", "occupations"):
            if pp.get(k):
                person_patch[k] = pp[k]
        # labels 里的 zhwiki 摘要也可作 summary 备选
        if wb.get("labels", {}).get("summary_zh") and not patch.get("summary_zh"):
            # 仅当 curated+wiki 都无时才用
            curated_summary = (result.get("curated") or {}).get("person_patch", {}).get("summary_zh")
            if not curated_summary:
                patch["summary_zh"] = wb["labels"]["summary_zh"]
        if wb.get("labels", {}).get("zhwiki_url"):
            patch["extra_source_urls"].append(wb["labels"]["zhwiki_url"])
        patch["person_patch"] = person_patch

        # sig/pos -> Event
        try:
            sig = wb.get("sig", [])
            pos = wb.get("pos", [])
            evs = build_events_for_person(qid, sig, pos)
            events_from_wikidata = evs
        except Exception:
            events_from_wikidata = []
        patch["extra_source_urls"].extend(wb.get("source_urls", []))

    patch["events_from_wiki"] = events_from_wiki
    patch["events_from_wikidata"] = events_from_wikidata
    result["patch"] = patch
    return result


def build_enrich_patch_as_endeavors_events(
    qid: str,
    patch: dict[str, Any],
) -> tuple[list[Endeavor], list[Event]]:
    """将 patch 转为可落盘的 Endeavor/Event 列表（可选辅助）."""
    # 当前 wikipedia 候选与 wikidata sig/pos 已是 Event，直接返回即可；
    # Endeavor 的智能补齐留给后续（此处不凭空捏造）。
    events: list[Event] = []
    events.extend(patch.get("events_from_wiki", []))
    events.extend(patch.get("events_from_wikidata", []))
    return [], events
