"""Thin shim kept for backwards compat — use arcvita.repos.curated_repo instead."""
from __future__ import annotations

import warnings

# Re-export legacy offline data (still the source of truth for pilot 25 until migration)
from arcvita._curated_legacy import (  # noqa: F401
    ENDEAVORS_OFFLINE,
    EVENTS_OFFLINE,
    OFFLINE,
    enrich_offline,
)

warnings.warn(
    "arcvita.curated is deprecated; use arcvita.repos.curated_repo (load_curated/get) instead. "
    "This shim will be removed in Phase E.",
    DeprecationWarning,
    stacklevel=2,
)

# Re-export new repo API for transitional callers
try:
    from arcvita.repos.curated_repo import (  # noqa: F401
        CuratedBundle,
        clear_cache,
        get,
        load_curated,
    )
except Exception:  # pragma: no cover
    pass

__all__ = [
    "OFFLINE",
    "ENDEAVORS_OFFLINE",
    "EVENTS_OFFLINE",
    "enrich_offline",
    "load_curated",
    "get",
    "CuratedBundle",
    "clear_cache",
]
