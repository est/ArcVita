"""Wikipedia 中文条目适配器（SourceAdapter 实现）

- REST summary: https://zh.wikipedia.org/api/rest_v1/page/summary/{title}
- Action API: action=query prop=extracts|revisions (exintro + explaintext + revisions)
- 解析首段与“作品/成语出处”关键词句，做名场面候选
- 接入 CacheStore 双探与共享 httpx_retry
"""
from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import quote

import httpx

from arcvita.models import Event
from arcvita.sources.base import CacheStore, FetchContext, FetchPatch, httpx_retry

WIKI_REST_SUMMARY = "https://zh.wikipedia.org/api/rest_v1/page/summary/{title}"
WIKI_API = "https://zh.wikipedia.org/w/api.php"
WIKIDATA_API = "https://www.wikidata.org/w/api.php"

# 关键词 -> highlight_type 映射
KEYWORD_MAP: dict[str, str] = {
    "代表作": "代表作",
    "代表作品": "代表作",
    "作品": "代表作",
    "著有": "代表作",
    "创作": "代表作",
    "撰写": "代表作",
    "编著": "代表作",
    "名作": "代表作",
    "成语": "成语",
    "典故": "成语",
    "出处": "成语",
    "出自": "成语",
    "名言": "名言",
    "名句": "名言",
    "发明": "发明",
    "创造": "发明",
    "研制": "发明",
    "战役": "战役",
    "战争": "战役",
    "会战": "战役",
    "改革": "制度",
    "制度": "制度",
    "变法": "制度",
    "演讲": "演讲",
    "演说": "演讲",
    "奖项": "奖项",
    "获奖": "奖项",
    "诺贝尔": "奖项",
    "远航": "远航",
    "航海": "远航",
    "决策": "决策",
}

# 用于切句的标点
_SENT_SPLIT_RE = re.compile(r"[。！？；\n]+")
_HIGHLIGHT_RE = re.compile("|".join(map(re.escape, KEYWORD_MAP.keys())))


# ---------------------------------------------------------------------------
# 基础解析（保持独立可单测）
# ---------------------------------------------------------------------------

def parse_first_para(extract: str) -> str:
    """取首段（按换行/空行切），截 800 字内。"""
    if not extract:
        return ""
    para = extract.strip().split("\n")[0].strip()
    para = re.sub(r"\s+", " ", para)
    if len(para) > 800:
        para = para[:800] + "…"
    return para


def extract_highlight_candidates(text: str, max_candidates: int = 8) -> list[dict]:
    """解析“作品/成语出处”关键词句，做名场面候选。"""
    if not text:
        return []
    sentences = [s.strip() for s in _SENT_SPLIT_RE.split(text) if s.strip()]
    candidates: list[dict] = []
    seen: set[str] = set()
    for sent in sentences:
        m = _HIGHLIGHT_RE.search(sent)
        if not m:
            continue
        keyword = m.group(0)
        if sent in seen:
            continue
        seen.add(sent)
        if len(sent) < 8 or len(sent) > 300:
            continue
        htype = KEYWORD_MAP.get(keyword, "代表作")
        candidates.append(
            {
                "sentence": sent,
                "keyword": keyword,
                "highlight_type": htype,
                "is_highlight_candidate": True,
            }
        )
        if len(candidates) >= max_candidates:
            break
    return candidates


# ---------------------------------------------------------------------------
# 内部 HTTP 拉取（共享退避）
# ---------------------------------------------------------------------------

def resolve_zhwiki_title(qid: str, client: httpx.Client, cache: CacheStore | None = None) -> str | None:
    """通过 Wikidata sitelinks 解析 zhwiki 标题，带缓存辅助。"""
    if cache:
        cached = cache.read(qid, "wikipedia")
        if cached and cached.get("zhwiki_title"):
            return cached["zhwiki_title"]
    r = httpx_retry(
        client,
        WIKIDATA_API,
        params={
            "action": "wbgetentities",
            "ids": qid,
            "props": "sitelinks",
            "format": "json",
        },
    )
    if r is None:
        return None
    try:
        data = r.json()
        ent = data.get("entities", {}).get(qid, {})
        title = ent.get("sitelinks", {}).get("zhwiki", {}).get("title")
        return title
    except Exception:
        return None


def fetch_rest_summary(title: str, client: httpx.Client) -> dict | None:
    url = WIKI_REST_SUMMARY.format(title=quote(title, safe=""))
    r = httpx_retry(client, url, headers={"Accept": "application/json"})
    if r is None:
        return None
    try:
        j = r.json()
        return {
            "title": j.get("title"),
            "displaytitle": j.get("displaytitle"),
            "extract": j.get("extract"),
            "extract_html": j.get("extract_html"),
            "originalimage": j.get("originalimage", {}).get("source"),
            "content_urls": j.get("content_urls", {}),
        }
    except Exception:
        return None


def fetch_extracts_revisions(title: str, client: httpx.Client) -> dict | None:
    """action=query prop=extracts|revisions 做中文条目拉取。"""
    r = httpx_retry(
        client,
        WIKI_API,
        params={
            "action": "query",
            "prop": "extracts|revisions",
            "titles": title,
            "exintro": "1",
            "explaintext": "1",
            "rvprop": "ids|timestamp|user|comment",
            "rvlimit": "5",
            "format": "json",
        },
    )
    if r is None:
        return None
    try:
        data = r.json()
        pages = data.get("query", {}).get("pages", {})
        for page in pages.values():
            if "missing" in page:
                return None
            return {
                "pageid": page.get("pageid"),
                "title": page.get("title"),
                "extract": page.get("extract", ""),
                "revisions": page.get("revisions", []),
            }
        return None
    except Exception:
        return None


# ---------------------------------------------------------------------------
# 保留旧签名兼容（委托新实现）
# ---------------------------------------------------------------------------

def fetch_wikipedia_for_qid(
    qid: str,
    client: httpx.Client,
    cache_dir: Path | str = "data/raw",
    title_hint: str | None = None,
) -> dict:
    """拉取中文条目：REST summary + extracts|revisions，返回可合并补丁。

    保持旧签名；内部使用 CacheStore 双探与共享退避，避免硬编码重复。
    """
    cache = CacheStore(cache_dir)
    ctx = FetchContext(client=client, cache=cache, title_hint=title_hint)
    adapter = WikipediaAdapter()
    patch = adapter.fetch(qid, ctx)
    if patch is None:
        return {"qid": qid, "zhwiki_title": None, "error": "no zhwiki title", "highlight_candidates": []}
    raw = patch.get("raw", {})
    # 还原旧返回结构以兼容 pipeline 已落盘读取
    raw.setdefault("qid", qid)
    return raw


# ---------------------------------------------------------------------------
# Adapter
# ---------------------------------------------------------------------------

class WikipediaAdapter:
    """Wikipedia 适配器 — id=wikipedia，实现 SourceAdapter。"""

    id: str = "wikipedia"

    def fetch(self, qid: str, ctx: FetchContext) -> FetchPatch | None:
        cache = ctx.cache if ctx else CacheStore("data/raw")
        client = ctx.client if ctx else None
        title_hint = ctx.title_hint if ctx else None
        if client is None:
            # 离线降级：仅尝试缓存
            cached = cache.read(qid, "wikipedia")
            if cached:
                return self._to_patch(qid, cached)
            return None

        # 1. 解析标题
        title = title_hint or resolve_zhwiki_title(qid, client, cache=cache)
        if not title:
            cached = cache.read(qid, "wikipedia")
            if cached:
                return self._to_patch(qid, cached)
            return None

        result: dict = {"qid": qid, "zhwiki_title": title, "source_urls": [f"https://zh.wikipedia.org/wiki/{quote(title)}"]}

        # 2. REST summary
        rest = fetch_rest_summary(title, client)
        if rest and rest.get("extract"):
            result["rest_extract"] = rest["extract"]
            result["rest_summary"] = rest
        else:
            result["rest_extract"] = None

        # 3. extracts|revisions
        ext = fetch_extracts_revisions(title, client)
        if ext:
            result["extract"] = ext.get("extract", "")
            result["revisions"] = ext.get("revisions", [])
            result["pageid"] = ext.get("pageid")
        else:
            cached = cache.read(qid, "wikipedia")
            if cached:
                return self._to_patch(qid, cached)
            result["extract"] = result.get("rest_extract") or ""
            result["revisions"] = []

        # 4. 首段 + 候选
        full_text = result.get("extract") or result.get("rest_extract") or ""
        result["first_para"] = parse_first_para(full_text)
        candidates = extract_highlight_candidates(full_text)
        if not candidates and result.get("rest_extract"):
            candidates = extract_highlight_candidates(result["rest_extract"])
        result["highlight_candidates"] = candidates
        result["cached"] = False

        # 5. 写缓存
        cache.write(qid, "wikipedia", result)
        return self._to_patch(qid, result)

    def _to_patch(self, qid: str, raw: dict) -> FetchPatch:
        """将原始 wikipedia result 转为 FetchPatch（wikipedia highlight → Event）。"""
        if raw.get("error"):
            return {"source": "wikipedia", "person_patch": {}, "events": [], "source_urls": [], "raw": raw}
        # summary 仅作 person_patch 备选（交由 Aggregator 按白名单决定是否采用）
        person_patch: dict = {}
        if raw.get("first_para"):
            person_patch["summary_zh"] = raw["first_para"]
        # highlight_candidates -> Event 补丁
        events: list[Event] = []
        for idx, cand in enumerate(raw.get("highlight_candidates", [])[:5], 1):
            sent = cand.get("sentence", "")
            htype = cand.get("highlight_type", "代表作")
            events.append(
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
                    sources=raw.get("source_urls", [f"https://zh.wikipedia.org/wiki/{qid}"]),
                    status="needs_review",
                    needs_review_reason="Wikipedia 候选，需人工核验时间/出处",
                )
            )
        return {
            "source": "wikipedia",
            "person_patch": person_patch,
            "events": events,
            "source_urls": raw.get("source_urls", []),
            "raw": raw,
        }

# 用于旧导入兼容：openalex_wb.WikidataAdapter 等可通过此类获取
__all__ = ["WikipediaAdapter", "fetch_wikipedia_for_qid", "parse_first_para", "extract_highlight_candidates", "resolve_zhwiki_title"]
