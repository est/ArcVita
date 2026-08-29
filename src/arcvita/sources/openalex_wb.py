"""Wikidata 智能降级适配器（沿用 openalex_wb 名称，id 规范为 wikidata）

- 基于 httpx_retry 共享退避 + CacheStore 双探
- 对外提供: fetch_wikidata_for_qid(qid, client, cache_dir) -> dict 兼容签名
- 暴露 WikidataAdapter(id="wikidata") 实现 SourceAdapter
"""
from __future__ import annotations

import time
from pathlib import Path

import httpx

from arcvita.models import Event
from arcvita.sources.base import CacheStore, FetchContext, FetchPatch, httpx_retry
from arcvita.wikidata import (
    build_events_for_person,
    fetch_labels_and_summaries,
    fetch_persons_via_api,
)

WIKIDATA_API = "https://www.wikidata.org/w/api.php"


# ---------------------------------------------------------------------------
# 兼容旧签名：fetch_wikidata_for_qid
# ---------------------------------------------------------------------------

def fetch_wikidata_for_qid(
    qid: str,
    client: httpx.Client,
    cache_dir: Path | str = "data/raw",
) -> dict:
    """拉取 wikidata 人物卡 + 摘要，带退避与缓存；兼容旧调用。"""
    cache = CacheStore(cache_dir)
    ctx = FetchContext(client=client, cache=cache)
    adapter = WikidataAdapter()
    patch = adapter.fetch(qid, ctx)
    if patch is None:
        # offline cache miss 情况
        return {"qid": qid, "error": "no data", "cached": False, "person": None, "sig": [], "pos": [], "labels": {}}
    raw = patch.get("raw", {})
    raw.setdefault("qid", qid)
    return raw


def fetch_wikidata_batch_with_fallback(
    qids: list[str],
    client: httpx.Client,
    cache_dir: Path | str = "data/raw",
) -> dict[str, dict]:
    """批量拉取，逐个智能降级（兼容旧签名）。"""
    out: dict[str, dict] = {}
    cache = CacheStore(cache_dir)
    for q in qids:
        ctx = FetchContext(client=client, cache=cache)
        patch = WikidataAdapter().fetch(q, ctx)
        out[q] = patch.get("raw", {}) if patch else {"qid": q, "error": "no data"}
        time.sleep(0.2)
    return out


# ---------------------------------------------------------------------------
# Adapter
# ---------------------------------------------------------------------------

class WikidataAdapter:
    """Wikidata 适配器 — 文件仍为 openalex_wb.py 但 id 规范为 wikidata。"""

    id: str = "wikidata"

    def fetch(self, qid: str, ctx: FetchContext) -> FetchPatch | None:
        cache = ctx.cache if ctx else CacheStore("data/raw")
        client = ctx.client if ctx else None

        # 无 client 时仅缓存
        if client is None:
            cached = cache.read(qid, "wikidata")
            if cached:
                return self._to_patch(qid, cached)
            return None

        # 先尝试线上（带退避），失败则切缓存
        try:
            persons, ev_map = fetch_persons_via_api([qid], client)
            sig = ev_map.get("sig", {}).get(qid, [])
            pos = ev_map.get("pos", {}).get(qid, [])

            labels: dict = {}
            probe = httpx_retry(
                client,
                WIKIDATA_API,
                params={
                    "action": "wbgetentities",
                    "ids": qid,
                    "props": "labels|sitelinks",
                    "languages": "zh|en",
                    "languagefallback": "1",
                    "format": "json",
                },
            )
            if probe is not None:
                try:
                    lm = fetch_labels_and_summaries([qid], client)
                    labels = lm.get(qid, {})
                except Exception:
                    labels = {}
            else:
                cached = cache.read(qid, "wikidata")
                if cached and cached.get("labels"):
                    labels = cached["labels"]

            person = persons[0] if persons else None
            result: dict = {
                "qid": qid,
                "person": person.model_dump() if person else None,
                "sig": sig,
                "pos": pos,
                "labels": labels,
                "source_urls": [f"https://www.wikidata.org/wiki/{qid}"],
                "cached": False,
            }
            cache.write(qid, "wikidata", result)
            return self._to_patch(qid, result)
        except Exception as e:
            cached = cache.read(qid, "wikidata")
            if cached:
                # 标记 cached 返回 patch
                patch = self._to_patch(qid, cached)
                if patch:
                    patch["raw"]["cached"] = True
                return patch
            # 无缓存则返回错误 raw 但仍构造 patch=None 让上层跳过或返回空
            result = {"qid": qid, "error": str(e), "cached": False, "person": None, "sig": [], "pos": [], "labels": {}}
            return self._to_patch(qid, result)

    def _to_patch(self, qid: str, raw: dict) -> FetchPatch | None:
        if raw.get("error") and not raw.get("person"):
            # 错误但无 person，仍返回空 events 以便上层跳过
            return {"source": "wikidata", "person_patch": {}, "events": [], "source_urls": [], "raw": raw}
        pp = raw.get("person") or {}
        person_patch: dict = {}
        for k in ("name_zh", "name_en", "birth_date", "death_date", "birth_place", "death_place", "occupations"):
            if pp.get(k):
                person_patch[k] = pp[k]
        # summary 备选 via labels
        if raw.get("labels", {}).get("summary_zh"):
            person_patch["summary_zh"] = raw["labels"]["summary_zh"]
        # sig/pos -> Event (通过 wikidata.build_events_for_person)
        events: list[Event] = []
        try:
            sig = raw.get("sig", [])
            pos = raw.get("pos", [])
            events = build_events_for_person(qid, sig, pos)
        except Exception:
            events = []
        source_urls: list[str] = list(raw.get("source_urls", []))
        zhwiki_url = raw.get("labels", {}).get("zhwiki_url")
        if zhwiki_url and zhwiki_url not in source_urls:
            source_urls.append(zhwiki_url)
        return {
            "source": "wikidata",
            "person_patch": person_patch,
            "events": events,
            "source_urls": source_urls,
            "raw": raw,
        }


# alias 保持可从 openalex_wb 导入 WikidataAdapter / OpenAlexAdapter
OpenAlexAdapter = WikidataAdapter
