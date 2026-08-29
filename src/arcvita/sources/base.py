"""统一 SourceAdapter 协议、CacheStore、RateLimit 与 httpx 共享退避

- CacheStore 支持双探：新 cache_dir 与旧 data/raw 双路径兼容
- FetchContext 携带 client / cache / qps
- httpx_retry 为共享指数退避（429/403 直接降级返回 None）
- SourceAdapter Protocol 供 wikipedia / wikidata / classical 实现
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

import httpx

USER_AGENT = "ArcVita/0.1 (biography research; local)"


# ---------------------------------------------------------------------------
# 共享退避
# ---------------------------------------------------------------------------

def httpx_retry(
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
        sleep = min(base * (2**attempt), 8)
        # 轻微 jitter
        sleep += attempt * 0.15
        time.sleep(sleep)
    return None


# Backwards compat alias for older adapter imports
request_with_backoff = httpx_retry  # alias
_get_with_backoff = httpx_retry  # alias


# ---------------------------------------------------------------------------
# CacheStore 双探
# ---------------------------------------------------------------------------

class CacheStore:
    """文件缓存，兼容旧 data/raw/<qid>.<source>.json 与新路径双探。

    read: 优先读 cache_dir/<qid>.<source>.json；未命中则回探旧 data/raw/<qid>.<source>.json
         兼容不带 source 的旧 bare <qid>.json（wikidata 早期）
    write: 始终写 cache_dir/<qid>.<source>.json
    """

    def __init__(self, cache_dir: Path | str = "data/raw") -> None:
        self.cache_dir = Path(cache_dir)
        # 旧路径固定为项目根下的 data/raw（相对 cwd）
        self.legacy_dir = Path("data/raw")

    def _candidate_paths(self, qid: str, source: str) -> list[Path]:
        """按探查优先级返回候选路径（先新后旧，先带 source 后 bare）。"""
        names = [f"{qid}.{source}.json", f"{qid}.json"]
        paths: list[Path] = []
        for n in names:
            paths.append(self.cache_dir / n)
        # legacy 双探：若 cache_dir 已是 legacy_dir 则不再重复
        if self.cache_dir.resolve() != self.legacy_dir.resolve():
            for n in names:
                paths.append(self.legacy_dir / n)
        return paths

    def _key_path(self, qid: str, source: str) -> Path:
        """写路径（始终新目录带 source 后缀）。"""
        return self.cache_dir / f"{qid}.{source}.json"

    def read(self, qid: str, source: str) -> dict[str, Any] | None:
        for p in self._candidate_paths(qid, source):
            if p.exists():
                try:
                    return json.loads(p.read_text(encoding="utf-8"))
                except Exception:
                    continue
        return None

    def write(self, qid: str, source: str, data: dict[str, Any]) -> None:
        try:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            p = self._key_path(qid, source)
            p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception:
            pass

    # 兼容部分旧调用：read/write 带 cache_dir 参数的全局函数风格
    def read_cache(self, qid: str, source: str) -> dict | None:  # alias
        return self.read(qid, source)

    def write_cache(self, qid: str, source: str, data: dict) -> None:  # alias
        self.write(qid, source, data)


# ---------------------------------------------------------------------------
# FetchContext & Patch 类型
# ---------------------------------------------------------------------------

@dataclass
class FetchContext:
    client: httpx.Client | None = None
    cache: CacheStore = field(default_factory=lambda: CacheStore("data/raw"))
    qps: float = 0.5
    title_hint: str | None = None


# FetchPatch：适配器返回的标准化补丁
# 约定 keys: source(str), person_patch(dict), events(list[Event]), source_urls(list[str]), raw(dict)
FetchPatch = dict[str, Any]
MergedPatch = dict[str, Any]


# ---------------------------------------------------------------------------
# SourceAdapter Protocol
# ---------------------------------------------------------------------------

@runtime_checkable
class SourceAdapter(Protocol):
    @property
    def id(self) -> str:  # noqa: D401
        ...

    def fetch(self, qid: str, ctx: FetchContext) -> FetchPatch | None:
        """按 qid 拉取补丁；失败/无数据返回 None，调用方可降级到空补丁。"""
        ...


# ---------------------------------------------------------------------------
# RateLimit 辅助（极简）
# ---------------------------------------------------------------------------

class RateLimiter:
    """按 qps 休眠的简易限流器；qps <=0 表示不限。"""

    def __init__(self, qps: float = 0.5) -> None:
        self.qps = qps
        self._last = 0.0

    def wait(self) -> None:
        if not self.qps or self.qps <= 0:
            return
        interval = 1.0 / self.qps
        now = time.time()
        elapsed = now - self._last
        if elapsed < interval:
            time.sleep(interval - elapsed)
        self._last = time.time()
