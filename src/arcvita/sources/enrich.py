"""统一入口 enrich_person(qid, client)  — 协议化改写

优先级: curated > classical > wikidata > wikipedia
仅对白名单字段补空，curated 永远优先；wikipedia highlight → Event，wikidata sig/pos → Event
保持 enrich_person 兼容签名：thin wrapper 委托 Aggregator
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import httpx

from arcvita.curated import OFFLINE
from arcvita.models import Event
from arcvita.sources.base import CacheStore, FetchContext, FetchPatch
from arcvita.sources.classical import ClassicalAdapter
from arcvita.sources.openalex_wb import WikidataAdapter
from arcvita.sources.wikipedia import WikipediaAdapter

# 仅补空字段白名单
FILL_IF_EMPTY: set[str] = {
    "birth_date",
    "death_date",
    "birth_place",
    "death_place",
    "summary_zh",
    "summary_first_person",
    "lesson",
    "era",
    "archetype",
}

# 适配器显式合并优先级（数值越小越高）
_PRIORITY: dict[str, int] = {"curated": 0, "classical": 1, "wikidata": 2, "wikipedia": 3}


# ---------------------------------------------------------------------------
# Curated Adapter（离线真源，内联于 enrich 避免循环依赖 pipeline）
# ---------------------------------------------------------------------------

class CuratedAdapter:
    id: str = "curated"

    def fetch(self, qid: str, ctx: FetchContext) -> FetchPatch | None:
        base = OFFLINE.get(qid)
        if not base:
            return None
        person_patch = {
            "name_zh": base.get("name_zh"),
            "name_en": base.get("name_en"),
            "birth_date": base.get("birth_date"),
            "death_date": base.get("death_date"),
            "birth_place": base.get("birth_place"),
            "summary_zh": base.get("summary_zh"),
            "summary_first_person": base.get("summary_first_person"),
            "lesson": base.get("lesson"),
            "era": base.get("era"),
            "archetype": base.get("archetype"),
            # occupations 保留但不入白名单（pipeline 另作合并去重）
            "occupations": base.get("occupations", []),
        }
        # 去掉空值（保留白名单判空由 Aggregator 处理）
        return {
            "source": "curated",
            "person_patch": person_patch,
            "events": [],
            "source_urls": [f"https://www.wikidata.org/wiki/{qid}"],
            "raw": {"source": "curated", "found": True, "person_patch": person_patch},
        }


# ---------------------------------------------------------------------------
# Aggregator
# ---------------------------------------------------------------------------

class Aggregator:
    """多源聚合器：按 curated > classical > wikidata > wikipedia 显式合并。"""

    def __init__(self, adapters: list[Any] | None = None, ctx: FetchContext | None = None) -> None:
        if adapters is None:
            adapters = [CuratedAdapter(), ClassicalAdapter(), WikidataAdapter(), WikipediaAdapter()]
        # 按优先级排序，保证 curated 永远先行
        self.adapters = sorted(adapters, key=lambda a: _PRIORITY.get(getattr(a, "id", ""), 99))
        self.ctx = ctx

    def aggregate(self, qid: str, title_hint: str | None = None) -> dict[str, Any]:
        """聚合补丁 -> MergedPatch

        返回:
          {
            person_patch: {merged 按白名单仅补空},
            events: [Event... 去重后],
            source_urls: [去重后],
            summary_zh: 便捷摘要,
            raw_patches: {id: raw}
          }
        """
        # 若调用方通过 title_hint 传入而 ctx 不含，则临时注入
        ctx = self.ctx
        if title_hint and ctx and not ctx.title_hint:
            # 浅复制避免污染外层
            from dataclasses import replace  # type: ignore

            try:
                ctx = replace(ctx, title_hint=title_hint)  # type: ignore[arg-type]
            except Exception:
                ctx = FetchContext(client=ctx.client, cache=ctx.cache, qps=ctx.qps, title_hint=title_hint)

        merged_person: dict[str, Any] = {}
        merged_events: list[Event] = []
        merged_urls: list[str] = []
        raw_patches: dict[str, Any] = {}
        seen_titles: set[str] = set()

        for adapter in self.adapters:
            a_ctx = ctx
            # wikipedia 需 title_hint
            if getattr(adapter, "id", "") == "wikipedia" and title_hint and a_ctx and not a_ctx.title_hint:
                from dataclasses import replace as _replace

                try:
                    a_ctx = _replace(a_ctx, title_hint=title_hint)  # type: ignore[arg-type]
                except Exception:
                    pass
            try:
                patch = adapter.fetch(qid, a_ctx)  # type: ignore[arg-type]
            except Exception:
                continue
            if not patch:
                continue
            raw_patches[getattr(adapter, "id", "unknown")] = patch.get("raw", patch)

            # person_patch 合并：仅白名单且空字段才补
            pp: dict[str, Any] = patch.get("person_patch") or {}
            # 兼顾 patch 顶层直接带 summary_zh（wikipedia）
            if patch.get("summary_zh") and "summary_zh" not in pp:
                pp = dict(pp)
                pp["summary_zh"] = patch["summary_zh"]
            for k in FILL_IF_EMPTY:
                if k not in pp or pp[k] is None:
                    continue
                v = pp[k]
                if isinstance(v, str) and not v.strip():
                    continue
                if isinstance(v, list) and len(v) == 0:
                    continue
                if k not in merged_person or not merged_person.get(k):
                    # 检查现有是否空
                    cur = merged_person.get(k)
                    if cur is None or (isinstance(cur, str) and not cur.strip()) or (isinstance(cur, list) and len(cur) == 0):
                        merged_person[k] = v
                # 已有非空则保持 curated 优先，不覆盖

            # occupations 特殊：pipeline 现有逻辑为追加去重，这里聚合也合并去重但不算白名单覆盖
            # 若 curated 无 occupations 且下层有，则补
            if "occupations" in pp and pp["occupations"]:
                if not merged_person.get("occupations"):
                    # 仅当空时取第一个非空
                    cur_oc = merged_person.get("occupations")
                    if not cur_oc:
                        merged_person["occupations"] = list(pp["occupations"])
                else:
                    # 合并去重（curated 优先保留顺序）
                    existing = set(merged_person.get("occupations", []))
                    for oc in pp["occupations"]:
                        if oc not in existing:
                            merged_person["occupations"].append(oc)

            # source_urls 去重保序
            for u in patch.get("source_urls", []) or []:
                if u and u not in merged_urls:
                    merged_urls.append(u)

            # events 去重（按标题）
            for ev in patch.get("events", []) or []:
                title = getattr(ev, "title_zh", None)
                if title is None and isinstance(ev, dict):
                    title = ev.get("title_zh")
                if not title:
                    continue
                if title in seen_titles:
                    continue
                seen_titles.add(title)
                merged_events.append(ev)

        return {
            "person_patch": merged_person,
            "events": merged_events,
            "source_urls": merged_urls,
            "summary_zh": merged_person.get("summary_zh"),
            "raw_patches": raw_patches,
        }


def _split_events_by_source(events: list[Event]) -> tuple[list[Event], list[Event]]:
    """按事件 id 前缀粗分 wikipedia / wikidata，供旧 pipeline 兼容字段使用。"""
    wiki: list[Event] = []
    wd: list[Event] = []
    for ev in events:
        eid = getattr(ev, "id", "")
        if "wiki" in eid:
            wiki.append(ev)
        else:
            wd.append(ev)
    return wiki, wd


# ---------------------------------------------------------------------------
# 兼容包装：enrich_person 保持旧签名，委托 Aggregator
# ---------------------------------------------------------------------------

def enrich_person(
    qid: str,
    client: httpx.Client | None = None,
    cache_dir: Path | str = "data/raw",
    enabled_sources: list[str] | None = None,
    title_hint: str | None = None,
) -> dict[str, Any]:
    """统一入口：按 enabled_sources 顺序尝试，返回补丁（兼容旧 pipeline）。

    enabled_sources 默认 ["curated", "wikipedia", "wikidata"]，
    可通过 config.yaml sources.enabled 覆盖（如 ["curated"] 即纯离线）。
    classical 隐含：若 enabled_sources 含 curated/classical 则纳入，否则仅按 enabled 过滤。
    """
    if enabled_sources is None:
        enabled_sources = ["curated", "wikipedia", "wikidata"]

    cdir = Path(cache_dir)
    cache = CacheStore(cdir)

    # 支持旧 id 拼写兼容
    id_map = {"openalex_wb": "wikidata", "openalex": "wikidata", "classical": "classical", "wikidata": "wikidata", "wikipedia": "wikipedia", "curated": "curated"}
    normalized = [id_map.get(s, s) for s in enabled_sources]

    # 构建 adapters 过滤集合
    all_adapters: dict[str, Any] = {
        "curated": CuratedAdapter(),
        "classical": ClassicalAdapter(),
        "wikidata": WikidataAdapter(),
        "wikipedia": WikipediaAdapter(),
    }
    adapters: list[Any] = [all_adapters[s] for s in normalized if s in all_adapters]
    # 若调用方未显式包含 classical 但需要古籍补全且为 guji- qid，可自动纳入
    if qid.startswith("guji-") and "classical" not in normalized and "classical" in all_adapters:
        # guji 人物必须补 classical，否则为空
        adapters.append(all_adapters["classical"])
        adapters = sorted(adapters, key=lambda a: _PRIORITY.get(getattr(a, "id", ""), 99))

    own_client = False
    active_client = client
    if active_client is None and any(s in normalized for s in ("wikipedia", "wikidata")):
        active_client = httpx.Client(headers={"User-Agent": "ArcVita/0.1 (biography research; local)"}, timeout=30)
        own_client = True

    try:
        ctx = FetchContext(client=active_client, cache=cache, qps=0.5, title_hint=title_hint)
        aggregator = Aggregator(adapters=adapters, ctx=ctx)
        merged = aggregator.aggregate(qid, title_hint=title_hint)

        # 还原旧结构以兼容 pipeline 的 patch 读写
        person_patch = merged.get("person_patch", {})
        events = merged.get("events", [])
        wiki_events, wd_events = _split_events_by_source(events)
        raw_patches = merged.get("raw_patches", {})

        # 旧 pipeline 还从 labels / cached 等字段取细节，wrapper 中 raw 已含
        result: dict[str, Any] = {
            "qid": qid,
            "curated": raw_patches.get("curated"),
            "wikipedia": raw_patches.get("wikipedia"),
            "wikidata": raw_patches.get("wikidata"),
            "classical": raw_patches.get("classical"),
            "patch": {
                "person_patch": person_patch,
                "summary_zh": person_patch.get("summary_zh"),
                "extra_source_urls": merged.get("source_urls", []),
                "events_from_wiki": wiki_events,
                "events_from_wikidata": wd_events,
                "events": events,
            },
        }
        # 保持与旧实现相同的键：若 wikipedia/raw 含 first_para 等，也回填到 patch 顶层供调试
        # 额外写入 raw 透传
        result["merged"] = merged
        return result
    finally:
        if own_client and active_client is not None:
            active_client.close()


def build_enrich_patch_as_endeavors_events(
    qid: str,
    patch: dict[str, Any],
) -> tuple[list[Any], list[Event]]:
    """将 patch 转为可落盘的 Endeavor/Event 列表（可选辅助）。"""
    events: list[Event] = []
    events.extend(patch.get("events_from_wiki", []))
    events.extend(patch.get("events_from_wikidata", []))
    # 兼容新 merged 结构
    if not events and patch.get("events"):
        events.extend(patch.get("events", []))
    return [], events
