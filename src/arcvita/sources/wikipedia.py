"""Wikipedia 中文条目适配器

- REST summary: https://zh.wikipedia.org/api/rest_v1/page/summary/{title}
- Action API: action=query prop=extracts|revisions (exintro + explaintext + revisions)
- 解析首段与“作品/成语出处”关键词句，做名场面候选
"""
from __future__ import annotations

import json
import re
import time
from pathlib import Path
from urllib.parse import quote

import httpx

WIKI_REST_SUMMARY = "https://zh.wikipedia.org/api/rest_v1/page/summary/{title}"
WIKI_API = "https://zh.wikipedia.org/w/api.php"
WIKIDATA_API = "https://www.wikidata.org/w/api.php"
USER_AGENT = "ArcVita/0.1 (biography research; local)"

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


def _cache_path(cache_dir: Path, qid: str) -> Path:
    return cache_dir / f"{qid}.wikipedia.json"


def _read_cache(cache_dir: Path, qid: str) -> dict | None:
    p = _cache_path(cache_dir, qid)
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            return None
    return None


def _write_cache(cache_dir: Path, qid: str, data: dict) -> None:
    cache_dir.mkdir(parents=True, exist_ok=True)
    p = _cache_path(cache_dir, qid)
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _get_with_backoff(
    client: httpx.Client,
    url: str,
    params: dict | None = None,
    headers: dict | None = None,
    max_retries: int = 3,
    base: float = 1.0,
    timeout: int = 30,
) -> httpx.Response | None:
    """指数退避请求，429/403 直接返回 None 让上层切缓存。"""
    h = {"User-Agent": USER_AGENT}
    if headers:
        h.update(headers)
    for attempt in range(max_retries):
        try:
            r = client.get(url, params=params, headers=h, timeout=timeout)
            if r.status_code in (429, 403):
                # 限流/拒绝 -> 不再硬重试，直接让上层降级
                return None
            r.raise_for_status()
            return r
        except httpx.HTTPStatusError as e:
            if e.response.status_code in (429, 403):
                return None
            if attempt == max_retries - 1:
                return None
        except Exception:
            if attempt == max_retries - 1:
                return None
        # 指数退避
        sleep = min(base * (2**attempt), 8)
        time.sleep(sleep)
    return None


def resolve_zhwiki_title(qid: str, client: httpx.Client, cache_dir: Path | None = None) -> str | None:
    """通过 Wikidata sitelinks 解析 zhwiki 标题，带缓存辅助。"""
    # 先看 wikipedia 缓存里是否已有标题
    if cache_dir:
        cached = _read_cache(cache_dir, qid)
        if cached and cached.get("zhwiki_title"):
            return cached["zhwiki_title"]
    r = _get_with_backoff(
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
    r = _get_with_backoff(client, url, headers={"Accept": "application/json"})
    if r is None:
        return None
    try:
        j = r.json()
        return {
            "title": j.get("title"),
            "displaytitle": j.get("displaytitle"),
            "extract": j.get("extract"),  # 首段纯文本
            "extract_html": j.get("extract_html"),
            "originalimage": j.get("originalimage", {}).get("source"),
            "content_urls": j.get("content_urls", {}),
        }
    except Exception:
        return None


def fetch_extracts_revisions(title: str, client: httpx.Client) -> dict | None:
    """action=query prop=extracts|revisions 做中文条目拉取。"""
    r = _get_with_backoff(
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


def parse_first_para(extract: str) -> str:
    """取首段（按换行/空行切），截 800 字内。"""
    if not extract:
        return ""
    # extracts 已是纯文本，取首段
    para = extract.strip().split("\n")[0].strip()
    # 去掉多余空白
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
        # 过滤过短/过长句
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


def fetch_wikipedia_for_qid(
    qid: str,
    client: httpx.Client,
    cache_dir: Path | str = "data/raw",
    title_hint: str | None = None,
) -> dict:
    """拉取中文条目：REST summary + extracts|revisions，返回可合并补丁。

    返回结构:
    {
      qid, zhwiki_title, rest_summary, extracts, first_para,
      highlight_candidates: [...],
      source_urls: [...],
      cached: bool
    }
    失败不抛异常，返回 {"qid":..., "error": "...", "cached": ...} 并尽量带缓存。
    """
    cdir = Path(cache_dir)
    # 1. 解析标题
    title = title_hint or resolve_zhwiki_title(qid, client, cache_dir=cdir)
    if not title:
        # 无 zhwiki 标题 -> 尝试读缓存
        cached = _read_cache(cdir, qid)
        if cached:
            cached["cached"] = True
            return cached
        return {"qid": qid, "zhwiki_title": None, "error": "no zhwiki title", "highlight_candidates": []}

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
        # 429/403 降级到缓存
        cached = _read_cache(cdir, qid)
        if cached:
            cached["cached"] = True
            return cached
        result["extract"] = result.get("rest_extract") or ""
        result["revisions"] = []

    # 4. 首段 + 候选
    full_text = result.get("extract") or result.get("rest_extract") or ""
    result["first_para"] = parse_first_para(full_text)
    # 候选：优先用 extract 全文，其次 rest_extract
    candidates = extract_highlight_candidates(full_text)
    # 若全文未命中，尝试用 rest_extract 补充
    if not candidates and result.get("rest_extract"):
        candidates = extract_highlight_candidates(result["rest_extract"])
    result["highlight_candidates"] = candidates
    result["cached"] = False

    # 5. 写缓存（成功才写，避免覆盖有效缓存为错误）
    try:
        _write_cache(cdir, qid, result)
    except Exception:
        pass

    return result
