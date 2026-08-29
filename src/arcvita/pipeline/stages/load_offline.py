"""load_offline stage — pure function (inputs,cfg)->(outputs,diagnostics).

加载 curated 离线库 (OFFLINE + ENDEAVORS_OFFLINE + EVENTS_OFFLINE) via enrich_offline.
"""
from __future__ import annotations

from typing import Any

from arcvita.curated import enrich_offline


def load_offline(seed_meta: dict[str, dict], cfg: dict) -> tuple[dict[str, dict], dict[str, Any]]:
    """direct helper: seed_meta -> offline_map."""
    offline_map = enrich_offline(seed_meta)
    diag = {
        "total_qids": len(seed_meta),
        "offline_covered": sum(1 for v in offline_map.values() if v.get("birth_date")),
        "offline_map_size": len(offline_map),
    }
    return offline_map, diag


def run(inputs: dict, cfg: dict) -> tuple[dict, dict]:
    """stage interface: (inputs,cfg)->(outputs,diagnostics).

    inputs must contain `seed_meta`.
    """
    seed_meta = inputs.get("seed_meta", {})
    offline_map, diag = load_offline(seed_meta, cfg)
    return {"offline_map": offline_map}, diag
