"""Orchestrator — reads config, batches, delegates to stages, writes outputs.

Signature: def run_pipeline(config_path, limit, qids, out_dir: Path|None)->dict
保留原 pipeline 行 为 thin shim.
"""
from __future__ import annotations

import time
from pathlib import Path
from typing import Any

import httpx

from arcvita.config import load_config, load_seed

USER_AGENT = "ArcVita/0.1 (biography research; local)"


def run_pipeline(
    config_path: str = "config.yaml",
    limit: int | None = None,
    qids: list[str] | None = None,
    out_dir: Path | None = None,
) -> dict:
    cfg = load_config(config_path)
    paths = cfg.get("paths", {})
    wikicfg = cfg.get("wikidata", {}) if isinstance(cfg.get("wikidata"), dict) else {}
    batch_size = int(wikicfg.get("batch_size", 8))
    seed = load_seed(paths.get("seed", "data/seed_persons.yaml"))
    if qids:
        seed = [s for s in seed if s["qid"] in qids]
    if limit:
        seed = seed[:limit]

    # resolve raw_dir for orchestrator (used for enrich cache)
    if out_dir is not None:
        raw_dir = Path(out_dir) / "raw"
    else:
        raw_dir = Path(paths.get("raw_dir", "data/raw"))
    raw_dir.mkdir(parents=True, exist_ok=True)

    seed_meta = {s["qid"]: s for s in seed}
    all_qids = [s["qid"] for s in seed]

    sources_cfg = cfg.get("sources", {}) if isinstance(cfg.get("sources"), dict) else {}
    sources_enabled: list[str] = list(sources_cfg.get("enabled") or [])
    sources_qps = float(sources_cfg.get("qps", wikicfg.get("qps", 0.5) or 0.5))

    # ---- stages: load_offline / load_classical (pure) ----
    from arcvita.pipeline.stages.load_classical import run as run_load_classical
    from arcvita.pipeline.stages.load_offline import run as run_load_offline

    off_out, off_diag = run_load_offline({"seed_meta": seed_meta}, cfg)
    offline_map = off_out["offline_map"]

    cla_out, cla_diag = run_load_classical({"seed_meta": seed_meta}, cfg)
    classical_map = cla_out["classical_map"]

    persons: list[Any] = []
    events: list[Any] = []
    endeavors: list[Any] = []

    # collect raw batches for deferred write
    raw_batches: list[dict] = []

    # batch loop
    from arcvita.pipeline.stages.build_domain import run as run_build_domain
    from arcvita.pipeline.stages.fetch_sources import run as run_fetch_sources

    with httpx.Client(headers={"User-Agent": USER_AGENT}, timeout=30) as client:
        for i in range(0, len(all_qids), batch_size):
            batch = all_qids[i : i + batch_size]
            batch_idx = i // batch_size + 1
            print(f"[{batch_idx}] fetching batch {batch}")

            fetch_inputs = {
                "batch_qids": batch,
                "client": client,
                "offline_map": offline_map,
                "seed_meta": seed_meta,
            }
            fetch_out, fetch_diag = run_fetch_sources(fetch_inputs, cfg)
            batch_persons = fetch_out["batch_persons"]
            sig_map = fetch_out["sig_map"]
            pos_map = fetch_out["pos_map"]
            label_map = fetch_out["label_map"]
            mode = fetch_diag.get("mode", "")
            if mode == "offline-first":
                print("  offline-first (no network)")
            elif mode == "fallback-offline":
                print(f"  fallback offline due to {fetch_diag.get('error')}")

            # defer raw dump
            raw_batches.append({"batch_id": batch_idx, "qids": batch, "label_map": label_map})

            # build_domain per batch
            build_inputs = {
                "batch_persons": batch_persons,
                "sig_map": sig_map,
                "pos_map": pos_map,
                "label_map": label_map,
                "seed_meta": seed_meta,
                "offline_map": offline_map,
                "classical_map": classical_map,
                "client": client,
                "raw_dir": raw_dir,
            }
            build_out, build_diag = run_build_domain(build_inputs, cfg)
            batch_persons_built: list[Any] = build_out["persons"]
            batch_events: list[Any] = build_out["events"]
            batch_endeavors: list[Any] = build_out["endeavors"]

            # per-batch link (could also be global; we do per-batch then global re-link)
            from arcvita.pipeline.stages.link import run as run_link

            link_out, link_diag = run_link(
                {"events": batch_events, "endeavors": batch_endeavors}, cfg
            )
            # link mutates, collect
            # need to ensure unlinked counts tracked
            # events_out from link are already linked
            persons.extend(batch_persons_built)
            # link stage returns mutated lists; collect
            events.extend(link_out["events"])
            endeavors.extend(link_out["endeavors"])

            # throttle
            if sources_enabled and sources_qps and sources_qps > 0:
                time.sleep(max(0.2, 1.0 / sources_qps))
            else:
                time.sleep(0.5)

    # global re-link to ensure cross-batch consistency (no-op if already linked per batch, but handles edge)
    # We have already linked per batch using per-batch endeavors; global step would double-link if not careful.
    # So skip global relink; per-batch is correct for person-scoped link.

    # ---- write stage (only side effects) ----
    from arcvita.pipeline.stages.write import run as run_write

    write_inputs = {
        "persons": persons,
        "events": events,
        "endeavors": endeavors,
        "out_dir": out_dir,
        "raw_batches": raw_batches,
    }
    _, write_diag = run_write(write_inputs, cfg)

    result: dict[str, Any] = {
        "persons": len(persons),
        "events": len(events),
        "endeavors": len(endeavors),
        "diagnostics": {
            "offline": off_diag,
            "classical": cla_diag,
            "write": write_diag,
        },
    }
    # provide raw count for backward compatible keys
    return result
