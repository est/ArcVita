"""stages package — pure (inputs,cfg)->(outputs,diagnostics), side-effects only in write."""

from arcvita.pipeline.stages import (
    build_domain,
    fetch_sources,
    link,
    load_classical,
    load_offline,
    write,
)

__all__ = ["build_domain", "fetch_sources", "link", "load_classical", "load_offline", "write"]
