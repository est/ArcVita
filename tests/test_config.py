"""Config 强校验：pydantic 模型、路径相对 resolve、旧 yaml 兼容."""
import pathlib
import tempfile

import pytest
import yaml

from arcvita.config import Config, load_config


def test_load_config_default():
    cfg = load_config("config.yaml")
    assert isinstance(cfg, Config)
    # paths 应被 resolve 为绝对路径
    assert cfg.paths.seed.is_absolute()
    assert cfg.paths.db.is_absolute()
    # 兼容 dict 访问
    assert "seed" in cfg["paths"]
    assert cfg.get("wikidata") is not None
    assert cfg["wikidata"]["batch_size"] == 3


def test_paths_relative_to_config_dir():
    with tempfile.TemporaryDirectory() as td:
        td_path = pathlib.Path(td)
        cfg_path = td_path / "config.yaml"
        # 写一个使用相对路径的最小 config
        minimal = {
            "paths": {
                "seed": "data/seed_persons.yaml",
                "raw_dir": "data/raw",
                "db": "data/biography.db",
            },
            "wikidata": {"batch_size": 5},
        }
        cfg_path.write_text(yaml.safe_dump(minimal), encoding="utf-8")
        cfg = load_config(cfg_path)
        # seed 应相对于 cfg 所在目录 resolve
        expected_seed = (td_path / "data/seed_persons.yaml").resolve()
        assert cfg.paths.seed == expected_seed
        assert cfg.wikidata.batch_size == 5
        # 未显式配置的应走默认值
        assert cfg.paths.persons_yaml.is_absolute()
        assert cfg.sources.enabled == []


def test_old_config_compat_missing_fields():
    with tempfile.TemporaryDirectory() as td:
        td_path = pathlib.Path(td)
        cfg_path = td_path / "config.yaml"
        # 旧 config 可能只有 wikidata.endpoint
        old = {"wikidata": {"endpoint": "https://example.org/sparql"}}
        cfg_path.write_text(yaml.safe_dump(old), encoding="utf-8")
        cfg = load_config(cfg_path)
        assert cfg.wikidata.endpoint == "https://example.org/sparql"
        # 其他字段补默认
        assert cfg.wikidata.batch_size == 3
        assert cfg.languages.primary == "zh"
        assert cfg.paths.seed.is_absolute()


def test_config_validation_error_on_bad_qps():
    with tempfile.TemporaryDirectory() as td:
        td_path = pathlib.Path(td)
        cfg_path = td_path / "config.yaml"
        bad = {"sources": {"qps": "慢"}}
        cfg_path.write_text(yaml.safe_dump(bad), encoding="utf-8")
        with pytest.raises(Exception):
            load_config(cfg_path)


def test_config_sources_enabled_coercion():
    cfg = Config.model_validate({"sources": {"enabled": None}})
    assert cfg.sources.enabled == []
    cfg2 = Config.model_validate({"sources": {"enabled": ["wikipedia"]}})
    assert cfg2.sources.enabled == ["wikipedia"]


def test_config_languages_defaults():
    cfg = Config()
    assert cfg.languages.primary == "zh"
    assert cfg.languages.fallback == "en"
    assert cfg.wikidata.qps == 0.5
    assert cfg.sources.cache is True
