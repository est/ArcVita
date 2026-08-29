"""Pydantic 强校验的 Config（Phase A）.

- Config 模型包含 wikidata / sources / paths / languages
- 全部 Path 相对 config.yaml 所在目录 resolve
- 兼容旧 config.yaml（缺字段自动补默认值）
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field, field_validator


class WikidataConfig(BaseModel):
    endpoint: str = "https://query.wikidata.org/sparql"
    api: str = "https://www.wikidata.org/w/api.php"
    wikipedia_api: str = "https://zh.wikipedia.org/w/api.php"
    user_agent: str = "ArcVita/0.1 (biography research; local)"
    batch_size: int = Field(default=3, ge=1, le=50)
    qps: float = Field(default=0.5, ge=0, le=5)
    timeout: int = Field(default=30, ge=1, le=300)
    retries: int = Field(default=5, ge=0, le=10)


class SourcesConfig(BaseModel):
    enabled: list[str] = Field(default_factory=list)
    cache: bool = True
    qps: float = Field(default=0.5, ge=0, le=5)

    @field_validator("enabled", mode="before")
    @classmethod
    def _coerce_enabled(cls, v: Any) -> list[str]:
        if v is None:
            return []
        if isinstance(v, list):
            return [str(x) for x in v]
        return [str(v)]


class PathsConfig(BaseModel):
    seed: Path = Field(default=Path("data/seed_persons.yaml"))
    raw_dir: Path = Field(default=Path("data/raw"))
    persons_yaml: Path = Field(default=Path("data/processed/persons.yaml"))
    events_yaml: Path = Field(default=Path("data/processed/events.yaml"))
    endeavors_yaml: Path = Field(default=Path("data/processed/endeavors.yaml"))
    highlights_yaml: Path = Field(default=Path("data/processed/highlights.yaml"))
    timelines_dir: Path = Field(default=Path("data/processed/timelines"))
    db: Path = Field(default=Path("data/biography.db"))

    # 允许额外路径（兼容未来扩展），但不强制校验


class LanguagesConfig(BaseModel):
    primary: str = "zh"
    fallback: str = "en"


class Config(BaseModel):
    wikidata: WikidataConfig = Field(default_factory=WikidataConfig)
    sources: SourcesConfig = Field(default_factory=SourcesConfig)
    paths: PathsConfig = Field(default_factory=PathsConfig)
    languages: LanguagesConfig = Field(default_factory=LanguagesConfig)

    # 内部：config 文件所在目录，用于 resolve
    _config_dir: Path | None = None

    def resolve_paths(self, base_dir: Path | str | None = None) -> Config:
        """把所有相对路径相对于 base_dir（默认 config.yaml 所在目录）解析为绝对路径."""
        base = Path(base_dir) if base_dir else (self._config_dir or Path.cwd())
        # 确保 base 是目录
        if base.is_file():
            base = base.parent
        for field_name in ("seed", "raw_dir", "persons_yaml", "events_yaml", "endeavors_yaml", "highlights_yaml", "timelines_dir", "db"):
            p: Path = getattr(self.paths, field_name)
            if not p.is_absolute():
                setattr(self.paths, field_name, (base / p).resolve())
            else:
                setattr(self.paths, field_name, p.resolve())
        return self

    def model_dump_paths_as_str(self) -> dict:
        """用于兼容旧代码：paths 转为 str 字典."""
        d = self.model_dump()
        # paths 转 str
        for k, v in d.get("paths", {}).items():
            d["paths"][k] = str(v)
        return d


def load_config(path: str | Path = "config.yaml") -> Config:
    """加载并校验 config.yaml，返回 Config 实例.

    兼容旧版：缺字段自动补默认值；paths 自动相对 config 所在目录 resolve.
    同时保持对旧调用方的兼容：返回对象支持 dict-like 访问（__getitem__）.
    """
    p = Path(path)
    if not p.exists():
        # 允许传入相对路径，从 cwd 查找；若不存在则用默认 Config
        cfg_dict: dict[str, Any] = {}
        config_dir = p.parent.resolve() if p.parent != Path("") else Path.cwd()
    else:
        raw = p.read_text(encoding="utf-8")
        cfg_dict = yaml.safe_load(raw) or {}
        config_dir = p.resolve().parent

    # Pydantic 校验（缺字段走默认值）
    cfg = Config.model_validate(cfg_dict)
    cfg._config_dir = config_dir
    cfg.resolve_paths(config_dir)

    # 为兼容旧 pipeline 代码（cfg["paths"] dict 访问），给 Config 加上 __getitem__ 代理
    # 这里不改类定义，直接 monkey patch 实例
    # 将 paths 转为字符串供旧代码使用时，仍保留 Path 对象在 .paths 上
    return cfg


# 兼容旧代码的 dict 访问：Config 支持 cfg["paths"] 等
def _config_getitem(self: Config, key: str) -> Any:  # type: ignore
    if key == "wikidata":
        return self.wikidata.model_dump()
    if key == "sources":
        return self.sources.model_dump()
    if key == "paths":
        # 旧代码期望 str 路径，保持为字符串
        return {k: str(v) for k, v in self.paths.model_dump().items()}
    if key == "languages":
        return self.languages.model_dump()
    # 兼容直接 dict get
    if hasattr(self, key):
        return getattr(self, key)
    raise KeyError(key)


# 动态为 Config 添加 __getitem__ 与 get
Config.__getitem__ = _config_getitem  # type: ignore[attr-defined]

_orig_get = Config.get if hasattr(Config, "get") else None  # type: ignore


def _config_get(self: Config, key: str, default: Any = None) -> Any:  # type: ignore
    try:
        return self[key]  # type: ignore[index]
    except KeyError:
        return default


Config.get = _config_get  # type: ignore[attr-defined]


def load_seed(path: str | Path = "data/seed_persons.yaml") -> list[dict]:
    p = Path(path)
    data = yaml.safe_load(p.read_text(encoding="utf-8"))
    return data.get("persons", [])
