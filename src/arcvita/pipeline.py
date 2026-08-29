"""Thin shim — preserves `python -m arcvita.cli` and legacy imports.

Actual implementation lives in arcvita.pipeline.orchestrator + stages/*.
This file re-exports run_pipeline for backward compatibility.
"""
from __future__ import annotations

from arcvita.pipeline.orchestrator import run_pipeline

__all__ = ["run_pipeline"]
