"""Wikidata 智能降级适配器（沿用 Wikidata，增加指数退避+文件缓存）

- 基于 httpx 的指数退避 + 对 429/403 自动切缓存/离线，不再硬失败
- 缓存路径: data/raw/<qid>.json  (与 wikipedia 区分，用 <qid>.wikidata.json)
- 对外提供: fetch_wikidata_for_qid(qid, client, cache_dir) -> dict

此模块复用 arcvita.wikidata 的解析逻辑，但包裹“智能降级”。
"""
from __future__ import annotations

import json
import time
from pathlib import Path

import httpx

from arcvita.wikidata import fetch_labels_and_summaries, fetch_persons_via_api

WIKIDATA_API = "https://www.wikidata.org/w/api.php"
USER_AGENT = "ArcVita/0.1 (biography research; local)"


def _cache_path(cache_dir: Path, qid: str) -> Path:
    return cache_dir / f"{qid}.wikidata.json"


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


def _request_with_backoff(
    client: httpx.Client,
    url: str,
    params: dict,
    max_retries: int = 4,
    base: float = 1.0,
) -> httpx.Response | None:
    """指数退避；429/403 返回 None 让上层切缓存。"""
    for attempt in range(max_retries):
        try:
            r = client.get(url, params=params, headers={"User-Agent": USER_AGENT}, timeout=30)
            if r.status_code in (429, 403):
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
        sleep = min(base * (2**attempt), 10)
        # jitter
        sleep += attempt * 0.2
        time.sleep(sleep)
    return None


def fetch_wikidata_for_qid(
    qid: str,
    client: httpx.Client,
    cache_dir: Path | str = "data/raw",
) -> dict:
    """拉取 wikidata 人物卡 + 摘要，带指数退避与缓存。

    成功返回:
    {
      qid, person: Person.model_dump(), sig: [...], pos: [...],
      labels: {name_zh, summary_zh, zhwiki_title, zhwiki_url},
      source_urls: [...],
      cached: False
    }
    限流/失败时返回缓存（cached=True）或 {"qid":..., "error":..., "cached":...}
    """
    cdir = Path(cache_dir)

    # 先尝试线上（带退避），失败则切缓存
    try:
        persons, ev_map = fetch_persons_via_api([qid], client)
        sig = ev_map.get("sig", {}).get(qid, [])
        pos = ev_map.get("pos", {}).get(qid, [])

        # labels/summary 另一次请求（同样做退避检测）
        labels: dict = {}
        # 用带退避的探测去判断是否被限流；若被限流则 labels 保持空，整体仍算成功
        probe = _request_with_backoff(
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
            # 未被限流 -> 走正常 fetch_labels_and_summaries（其内部也会请求，但已验证通路正常）
            try:
                lm = fetch_labels_and_summaries([qid], client)
                labels = lm.get(qid, {})
            except Exception:
                labels = {}
        else:
            # 被限流 -> 尝试从缓存补 labels
            cached = _read_cache(cdir, qid)
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
        # 写缓存
        try:
            _write_cache(cdir, qid, result)
        except Exception:
            pass
        return result
    except Exception as e:
        # 网络异常 / 限流 -> 切缓存
        cached = _read_cache(cdir, qid)
        if cached:
            cached["cached"] = True
            return cached
        return {"qid": qid, "error": str(e), "cached": False, "person": None, "sig": [], "pos": [], "labels": {}}


def fetch_wikidata_batch_with_fallback(
    qids: list[str],
    client: httpx.Client,
    cache_dir: Path | str = "data/raw",
) -> dict[str, dict]:
    """批量拉取，逐个智能降级。"""
    out: dict[str, dict] = {}
    for q in qids:
        out[q] = fetch_wikidata_for_qid(q, client, cache_dir=cache_dir)
        time.sleep(0.2)
    return out
