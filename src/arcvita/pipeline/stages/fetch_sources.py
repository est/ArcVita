"""fetch_sources stage — (inputs,cfg)->(outputs,diagnostics).

按 sources.enabled 决定是否联网，聚合 wikidata/wikipedia 数据。
纯函数: 不写盘，只返回 batch_persons / sig_map / pos_map / label_map。
raw 持久化由 orchestrator/write 负责。
"""
from __future__ import annotations

from typing import Any

import httpx

from arcvita.models import Person

USER_AGENT = "ArcVita/0.1 (biography research; local)"


def _person_from_offline(qid: str, off: dict, seed_meta: dict) -> Person:
    source_url = (
        f"https://www.wikidata.org/wiki/{qid}"
        if not qid.startswith("guji-")
        else "https://daizhige.org/史藏/正史/史记.html"
    )
    return Person(
        qid=qid,
        name_zh=off.get("name_zh") or seed_meta.get(qid, {}).get("name_zh", qid),
        name_en=off.get("name_en"),
        birth_date=off.get("birth_date"),
        death_date=off.get("death_date"),
        birth_place=off.get("birth_place"),
        death_place=off.get("death_place"),
        occupations=off.get("occupations", []),
        era=off.get("era"),
        archetype=off.get("archetype"),
        summary_zh=off.get("summary_zh"),
        summary_first_person=off.get("summary_first_person"),
        lesson=off.get("lesson"),
        dilemmas=off.get("dilemmas", []),
        source_urls=[source_url],
    )


def fetch_sources(
    batch_qids: list[str],
    client: httpx.Client | None,
    cfg: dict,
    offline_map: dict[str, dict],
    seed_meta: dict[str, dict],
) -> tuple[dict[str, Any], dict[str, Any]]:
    """direct helper used by run()."""
    cfg.get("sources", {}) if isinstance(cfg.get("sources"), dict) else {}
    # Note: caller orchestrator already ensures client exists if needed
    offline_covered = all(
        q in offline_map and offline_map[q].get("birth_date") for q in batch_qids
    )
    diagnostics: dict[str, Any] = {"offline_covered": offline_covered, "batch_size": len(batch_qids)}
    sig_map: dict[str, list[dict]] = {q: [] for q in batch_qids}
    pos_map: dict[str, list[dict]] = {q: [] for q in batch_qids}
    label_map: dict[str, dict] = {q: {} for q in batch_qids}
    batch_persons: list[Person] = []

    if offline_covered:
        batch_persons = [
            _person_from_offline(q, offline_map[q], seed_meta) for q in batch_qids
        ]
        diagnostics["mode"] = "offline-first"
        return (
            {
                "batch_persons": batch_persons,
                "sig_map": sig_map,
                "pos_map": pos_map,
                "label_map": label_map,
            },
            diagnostics,
        )

    # try network
    try:
        from arcvita.wikidata import fetch_labels_and_summaries, fetch_persons_via_api

        if client is None:
            # create ephemeral client
            with httpx.Client(headers={"User-Agent": USER_AGENT}, timeout=30) as tmp:
                batch_persons, api_events = fetch_persons_via_api(batch_qids, tmp)
                sig_map = api_events["sig"]
                pos_map = api_events["pos"]
                for p in batch_persons:
                    label_map[p.qid] = {
                        "name_zh": p.name_zh,
                        "name_en": p.name_en,
                        "summary_zh": None,
                    }
                try:
                    extra = fetch_labels_and_summaries(batch_qids, tmp)
                    for qid, v in extra.items():
                        if v.get("summary_zh"):
                            label_map[qid]["summary_zh"] = v["summary_zh"]
                            label_map[qid]["zhwiki_url"] = v.get("zhwiki_url")
                            if v.get("zhwiki_title"):
                                label_map[qid]["zhwiki_title"] = v.get("zhwiki_title")
                except Exception:
                    pass
        else:
            batch_persons, api_events = fetch_persons_via_api(batch_qids, client)
            sig_map = api_events["sig"]
            pos_map = api_events["pos"]
            for p in batch_persons:
                label_map[p.qid] = {"name_zh": p.name_zh, "name_en": p.name_en, "summary_zh": None}
            try:
                extra = fetch_labels_and_summaries(batch_qids, client)
                for qid, v in extra.items():
                    if v.get("summary_zh"):
                        label_map[qid]["summary_zh"] = v["summary_zh"]
                        label_map[qid]["zhwiki_url"] = v.get("zhwiki_url")
                        if v.get("zhwiki_title"):
                            label_map[qid]["zhwiki_title"] = v.get("zhwiki_title")
            except Exception:
                pass
        diagnostics["mode"] = "online"
    except Exception as e:
        diagnostics["mode"] = "fallback-offline"
        diagnostics["error"] = str(e)
        batch_persons = []
        for qid in batch_qids:
            off = offline_map.get(qid, {})
            if off and off.get("birth_date"):
                batch_persons.append(_person_from_offline(qid, off, seed_meta))
            else:
                meta = seed_meta.get(qid, {})
                batch_persons.append(
                    Person(
                        qid=qid,
                        name_zh=meta.get("name_zh", qid),
                        birth_date=None,
                        source_urls=[f"https://www.wikidata.org/wiki/{qid}"],
                        status="needs_review",
                        needs_review_reason="离线库未覆盖，需AI/线上补齐",
                    )
                )
        sig_map = {q: [] for q in batch_qids}
        pos_map = {q: [] for q in batch_qids}
        label_map = {q: {} for q in batch_qids}

    return (
        {
            "batch_persons": batch_persons,
            "sig_map": sig_map,
            "pos_map": pos_map,
            "label_map": label_map,
        },
        diagnostics,
    )


def run(inputs: dict, cfg: dict) -> tuple[dict, dict]:
    batch_qids: list[str] = inputs.get("batch_qids", [])
    client: httpx.Client | None = inputs.get("client")
    offline_map: dict = inputs.get("offline_map", {})
    seed_meta: dict = inputs.get("seed_meta", {})
    outputs, diag = fetch_sources(batch_qids, client, cfg, offline_map, seed_meta)
    # include raw batch representation for orchestrator to dump
    outputs["batch_qids"] = batch_qids
    return outputs, diag
