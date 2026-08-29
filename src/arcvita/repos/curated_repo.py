"""Curated 数据加载（单一真源）.

从 data/curated/classical/*.yaml 加载 CuratedBundle，
暴露 load_curated(repo_root) 与 get(qid)，带 mtime 缓存.

每个 yaml 结构:
  person: {name_zh, name_en, birth_date, death_date, birth_place, ...}
  endeavors / endavors: [...]
  events: [...]
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass
class CuratedBundle:
    qid: str  # 若原文件无 qid，则用 name_zh 或文件名派生
    name_zh: str
    person: dict[str, Any] = field(default_factory=dict)
    endeavors: list[dict] = field(default_factory=list)
    events: list[dict] = field(default_factory=list)
    source_file: Path | None = None


# mtime 缓存
_cache: dict[str, dict] = {}
_cache_mtime: dict[str, float] = {}
_cache_bundles: dict[str, CuratedBundle] = {}


def _scan_yaml_files(repo_root: Path) -> list[Path]:
    # 支持 flat + recursive pre_qin
    files: list[Path] = []
    for p in repo_root.rglob("*.yaml"):
        if p.is_file():
            files.append(p)
    for p in repo_root.rglob("*.yml"):
        if p.is_file():
            files.append(p)
    return sorted(files)


def load_curated(repo_root: str | Path = "data/curated/classical") -> dict[str, CuratedBundle]:
    """加载全部 CuratedBundle，带 mtime 缓存.

    参数:
        repo_root: 目录路径，默认为项目相对路径 data/curated/classical.
                 若为相对路径，则相对 cwd 解析；若绝对则直接使用.

    返回:
        dict[qid/name_zh -> CuratedBundle]; 兼容 get 两种键.
    """
    root = Path(repo_root)
    # 若相对路径，尝试相对 cwd；若不存在则尝试相对项目根（向上查找 config.yaml）
    if not root.is_absolute() and not root.exists():
        # 尝试从当前工作目录向上找项目根
        proj = Path.cwd()
        cand = proj / repo_root
        if cand.exists():
            root = cand
    # 计算最新 mtime
    files = _scan_yaml_files(root) if root.exists() else []
    latest_mtime = 0.0
    for f in files:
        try:
            latest_mtime = max(latest_mtime, f.stat().st_mtime)
        except OSError:
            continue
    cache_key = str(root.resolve()) if root.exists() else str(root)
    # 若缓存有效则直接返回
    if cache_key in _cache_bundles and _cache_mtime.get(cache_key) == latest_mtime and _cache.get(cache_key):
        # 返回合并后的 dict（包含 alias）
        return _cache[cache_key]  # type: ignore

    bundles: dict[str, CuratedBundle] = {}
    for f in files:
        try:
            data = yaml.safe_load(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        if not isinstance(data, dict):
            continue
        person = data.get("person", {}) if isinstance(data.get("person"), dict) else {}
        name_zh = person.get("name_zh") or f.stem
        qid = person.get("qid") or person.get("id") or name_zh
        # 规范 qid: 若为 guji- 风格或 Qxxx，保留；否则用 name_zh
        if not qid:
            qid = f.stem
        # endeavors 兼容拼写
        endeavors = data.get("endeavors") or data.get("endavors") or []
        if not isinstance(endeavors, list):
            # 某些文件 places 为字符串，需容错
            endeavors = []
        events = data.get("events") or []
        if not isinstance(events, list):
            events = []

        bundle = CuratedBundle(
            qid=str(qid),
            name_zh=str(name_zh),
            person=person,
            endeavors=endeavors,
            events=events,
            source_file=f,
        )
        # 主键 qid
        bundles[str(qid)] = bundle
        # 别名 name_zh（若不同）
        if str(name_zh) != str(qid):
            bundles[str(name_zh)] = bundle
        # 同时以文件 stem 为别名
        if f.stem not in bundles:
            bundles[f.stem] = bundle

    # 更新缓存
    _cache[cache_key] = bundles
    _cache_mtime[cache_key] = latest_mtime
    # 也保存 bundles 引用
    _cache_bundles[cache_key] = bundles
    return bundles


def get(qid: str, repo_root: str | Path = "data/curated/classical") -> CuratedBundle | None:
    """按 qid 或 name_zh 获取单个 Bundle."""
    bundles = load_curated(repo_root)
    # 直接命中
    if qid in bundles:
        return bundles[qid]
    # 尝试按 name_zh 去掉前后空格
    qid_stripped = qid.strip()
    if qid_stripped in bundles:
        return bundles[qid_stripped]
    return None


def clear_cache() -> None:
    """清空缓存（测试用）."""
    _cache.clear()
    _cache_mtime.clear()
    _cache_bundles.clear()


__all__ = ["CuratedBundle", "load_curated", "get", "clear_cache"]
