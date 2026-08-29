from __future__ import annotations

import re

MODERN_RE = re.compile(r"(.+?)[\(（]今(.+?)[\)）]")
PAREN_RE = re.compile(r"[\(（].*?[\)）]")

def normalize_place(raw: str | None) -> dict | None:
    """Split '长安(今陕西西安)' -> {name:长安, modern:陕西西安, raw} ; return None for empty."""
    if not raw or not raw.strip():
        return None
    raw = raw.strip()
    m = MODERN_RE.search(raw)
    if m:
        return {"name": m.group(1).strip(), "modern": m.group(2).strip(), "raw": raw}
    # no modern annotation
    name = PAREN_RE.sub("", raw).strip() or raw
    return {"name": name, "raw": raw, "modern": None}

def place_display(raw: str | None) -> str:
    if not raw:
        return "—"
    n = normalize_place(raw)
    if not n:
        return raw
    if n.get("modern"):
        return f"{n['name']}({n['modern']})"
    return n["name"]

def places_equal(a: str | None, b: str | None) -> bool:
    if not a or not b:
        return False
    na = normalize_place(a)
    nb = normalize_place(b)
    return (na or {}).get("name") == (nb or {}).get("name")
