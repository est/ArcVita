from __future__ import annotations

import re

DATE_RE = re.compile(r"^(-?\d{1,4})(?:-(\d{2})(?:-(\d{2}))?)?")
YANK_RE = re.compile(r"约|前|公元前|公元")

def clean(s: str | None) -> str | None:
    if not s:
        return None
    s = s.strip()
    if not s or s == "?" or s == "—":
        return None
    # 长词优先，避免 "公元前" 被 "前" 拆开
    s = s.replace("公元前", "-").replace("公元", "").replace("约", "").replace("前", "-")
    s = s.replace("--", "-")
    s = s.lstrip("+").strip()
    if "T" in s:
        s = s.split("T")[0]
    s = s.rstrip("Z").strip()
    return s or None


def _norm_year(y: str) -> str:
    """Strip leading zeros but keep sign: '-0551' -> '-551', '0005' -> '5'."""
    if y.startswith("-"):
        core = y[1:].lstrip("0") or "0"
        return f"-{core}"
    return y.lstrip("0") or "0"


def parse_iso(s: str | None) -> tuple[str | None, str | None]:
    """Return (iso, precision) where iso is YYYY or YYYY-MM or YYYY-MM-DD, BCE retains leading -."""
    c = clean(s)
    if not c:
        return None, None
    m = DATE_RE.match(c)
    if not m:
        # try extract first yearish token
        m2 = re.search(r"(-?\d{1,4})", c)
        if not m2:
            return None, None
        return _norm_year(m2.group(1)), "year"
    y, mo, d = m.group(1), m.group(2), m.group(3)
    y = _norm_year(y)
    if d and mo:
        return f"{y}-{mo}-{d}", "day"
    if mo:
        return f"{y}-{mo}", "month"
    return y, "year"


def parse_wikidata_date(s: str) -> tuple[str | None, str | None]:
    return parse_iso(s)


# 别名: 任务描述中的 parse_wikidate（无 a）亦兼容
def parse_wikidate(s: str | None) -> tuple[str | None, str | None]:
    return parse_iso(s)


def year_of(iso: str | None) -> int | None:
    if not iso:
        return None
    c = clean(iso)
    if not c:
        return None
    m = re.match(r"^(-?\d+)", c)
    if not m:
        return None
    try:
        return int(m.group(1))
    except ValueError:
        return None


def coerce_precision(iso: str | None) -> str | None:
    _, prec = parse_iso(iso)
    return prec


def in_range(ev_date: str | None, start: str | None, end: str | None) -> bool:
    ey = year_of(ev_date)
    sy = year_of(start)
    ey2 = year_of(end)
    if ey is None or sy is None or ey2 is None:
        return False
    return sy <= ey <= ey2


def sort_key(iso: str | None) -> str:
    """Sortable key: unknown dates sort last."""
    if not iso:
        return "9999"
    return iso
