from __future__ import annotations

import json
import sqlite3
from pathlib import Path

DB = Path("data/biography.db")

DILEMMA_MAP: dict[str, list[str]] = {
    "被流放": ["Q316452", "Q334053", "Q8023", "Q517", "Q19837"],
    "被贬": ["Q316452", "Q334053", "Q23114"],
    "被误解": ["Q4604", "Q23114", "Q937", "Q935"],
    "众叛亲离": ["Q517", "Q1048", "Q352"],
    "从零开始": ["Q720", "Q19837", "Q334642", "Q184080"],
    "技术瓶颈": ["Q193533", "Q935", "Q7186", "Q334642", "Q937"],
    "至暗时刻": ["Q8016", "Q8023", "Q1001", "Q37230"],
    "怀才不遇": ["Q4604", "Q7074", "Q762", "Q913"],
    "过度扩张": ["Q162427", "Q517", "Q720", "Q352"],
    "转型阵痛": ["Q37230", "Q316452", "Q23114", "Q19837"],
}


def find_by_dilemma(keyword: str, public_only: bool = True) -> list[dict]:
    qids = DILEMMA_MAP.get(keyword, [])
    if not qids:
        qids = [k for k, v in DILEMMA_MAP.items() if keyword in k for _ in v]
        qids = DILEMMA_MAP.get(keyword, [])
    if not qids:
        return []
    placeholders = ",".join("?" for _ in qids)
    vis_filter = "AND visibility='public'" if public_only else ""
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    cur = con.cursor()
    cur.execute(f"SELECT * FROM persons WHERE qid IN ({placeholders}) {vis_filter}", qids)
    rows = [dict(r) for r in cur.fetchall()]
    con.close()
    # sort by qid order
    order = {q: i for i, q in enumerate(qids)}
    rows.sort(key=lambda r: order.get(r["qid"], 999))
    return rows


def find_by_place(place: str, public_only: bool = True) -> list[dict]:
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    cur = con.cursor()
    # search endeavors places and events place_name
    like = f"%{place}%"
    if public_only:
        cur.execute(
            """SELECT DISTINCT p.* FROM persons p
               JOIN endeavors e ON e.person_qid=p.qid
               WHERE e.places LIKE ? AND p.visibility='public'""",
            (like,),
        )
        a = [dict(r) for r in cur.fetchall()]
        cur.execute(
            """SELECT DISTINCT p.* FROM persons p
               JOIN events ev ON ev.person_qid=p.qid
               WHERE ev.place_name LIKE ? AND p.visibility='public'""",
            (like,),
        )
        b = [dict(r) for r in cur.fetchall()]
    else:
        cur.execute("SELECT DISTINCT p.* FROM persons p JOIN endeavors e ON e.person_qid=p.qid WHERE e.places LIKE ?", (like,))
        a = [dict(r) for r in cur.fetchall()]
        cur.execute("SELECT DISTINCT p.* FROM persons p JOIN events ev ON ev.person_qid=p.qid WHERE ev.place_name LIKE ?", (like,))
        b = [dict(r) for r in cur.fetchall()]
    con.close()
    seen: dict[str, dict] = {}
    for r in a + b:
        seen[r["qid"]] = r
    return list(seen.values())


def timeline(qid: str) -> list[dict]:
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    cur = con.cursor()
    cur.execute("SELECT * FROM events WHERE person_qid=? ORDER BY date", (qid,))
    rows = [dict(r) for r in cur.fetchall()]
    con.close()
    return rows


def endeavors_for(qid: str) -> list[dict]:
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    cur = con.cursor()
    cur.execute("SELECT * FROM endeavors WHERE person_qid=? ORDER BY start_date", (qid,))
    rows = [dict(r) for r in cur.fetchall()]
    con.close()
    for r in rows:
        for k in ("places", "phases", "event_ids", "highlight_event_ids"):
            try:
                r[k] = json.loads(r[k]) if r[k] else []
            except Exception:
                r[k] = []
    return rows


def highlights_for(qid: str | None = None, highlight_type: str | None = None) -> list[dict]:
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    cur = con.cursor()
    q = "SELECT * FROM events WHERE is_highlight=1"
    args: list = []
    if qid:
        q += " AND person_qid=?"
        args.append(qid)
    if highlight_type:
        q += " AND highlight_type=?"
        args.append(highlight_type)
    q += " ORDER BY date"
    cur.execute(q, args)
    rows = [dict(r) for r in cur.fetchall()]
    con.close()
    return rows


def chengshi_persons(public_only: bool = True) -> list[dict]:
    vis = "WHERE visibility='public'" if public_only else ""
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    cur = con.cursor()
    cur.execute(f"SELECT * FROM persons {vis} ORDER BY qid")
    rows = [dict(r) for r in cur.fetchall()]
    # 优先返回有成事儿原型的
    cur.execute(f"SELECT person_qid, COUNT(*) as c FROM endeavors {('JOIN persons p ON p.qid=person_qid ' + vis) if public_only else ''} GROUP BY person_qid")
    cnt = {r["person_qid"]: r["c"] for r in cur.fetchall()}
    con.close()
    rows.sort(key=lambda r: (-(1 if r.get("archetype") else 0), -cnt.get(r["qid"], 0)))
    return rows
