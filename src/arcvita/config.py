from __future__ import annotations

from pathlib import Path

import yaml


def load_config(path: str | Path = "config.yaml") -> dict:
    p = Path(path)
    return yaml.safe_load(p.read_text(encoding="utf-8"))


def load_seed(path: str | Path = "data/seed_persons.yaml") -> list[dict]:
    p = Path(path)
    data = yaml.safe_load(p.read_text(encoding="utf-8"))
    return data.get("persons", [])
