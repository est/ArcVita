"""load_classical stage — pure function (inputs,cfg)->(outputs,diagnostics).

按姓名从 extracted 古籍读取 classical 补丁.
"""
from __future__ import annotations

from typing import Any


def load_classical(seed_meta: dict[str, dict], cfg: dict) -> tuple[dict[str, dict], dict[str, Any]]:
    classical_map: dict[str, dict] = {}
    diagnostics: dict[str, Any] = {"total": len(seed_meta), "found": 0}
    try:
        from arcvita.sources.classical import fetch_classical_for_name
    except Exception:
        diagnostics["error"] = "classical source not available"
        return classical_map, diagnostics

    for qid, meta in seed_meta.items():
        name = meta.get("name_zh", "")
        if not name:
            continue
        try:
            cpatch = fetch_classical_for_name(name)
            if cpatch:
                classical_map[qid] = cpatch
        except Exception:
            continue
    diagnostics["found"] = len(classical_map)
    return classical_map, diagnostics


def run(inputs: dict, cfg: dict) -> tuple[dict, dict]:
    seed_meta = inputs.get("seed_meta", {})
    classical_map, diag = load_classical(seed_meta, cfg)
    return {"classical_map": classical_map}, diag
