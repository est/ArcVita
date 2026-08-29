from __future__ import annotations

import json
import sqlite3
import yaml
from pathlib import Path

DB = Path("data/biography.db")


def _db():
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    return con


def build_highlights():
    con = _db()
    cur = con.cursor()
    cur.execute("SELECT * FROM events WHERE is_highlight=1 ORDER BY date")
    rows = [dict(r) for r in cur.fetchall()]
    con.close()
    out = []
    for r in rows:
        out.append(
            {
                "person_qid": r["person_qid"],
                "date": r["date"],
                "place_name": r["place_name"],
                "highlight_type": r["highlight_type"],
                "title_zh": r["title_zh"],
                "highlight_note": r["highlight_note"],
                "endeavor_id": r["endeavor_id"],
                "sources": json.loads(r["sources"]) if r["sources"] else [],
            }
        )
    # 合并历史背景事件（王表/朝代更替/社会变革等）
    ctx_path = Path("data/processed/historical_contexts.yaml")
    if ctx_path.exists():
        ctx = yaml.safe_load(ctx_path.read_text(encoding="utf-8")) or []
        for c in ctx:
            c["is_highlight"] = True
            if "person_qid" not in c:
                c["person_qid"] = "_context"
            out.append(c)
    p = Path("data/processed/highlights.yaml")
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(yaml.safe_dump(out, allow_unicode=True, sort_keys=False, width=100), encoding="utf-8")
    return len(out)


def build_timelines():
    con = _db()
    cur = con.cursor()
    cur.execute("SELECT qid, name_zh, era, archetype, summary_zh FROM persons ORDER BY qid")
    persons = [dict(r) for r in cur.fetchall()]
    outdir = Path("data/processed/timelines")
    outdir.mkdir(parents=True, exist_ok=True)
    for p in persons:
        qid = p["qid"]
        cur.execute("SELECT * FROM endeavors WHERE person_qid=? ORDER BY start_date", (qid,))
        eds = [dict(r) for r in cur.fetchall()]
        for e in eds:
            for k in ("places", "phases", "event_ids", "highlight_event_ids"):
                try:
                    e[k] = json.loads(e[k]) if e[k] else []
                except Exception:
                    e[k] = []
        cur.execute("SELECT * FROM events WHERE person_qid=? ORDER BY date", (qid,))
        evs = [dict(r) for r in cur.fetchall()]
        # markdown
        lines = [f"# {p['name_zh']} · {p['era'] or ''} {('· ' + p['archetype']) if p['archetype'] else ''}".strip(), ""]
        if p.get("summary_zh"):
            lines += [p["summary_zh"], ""]
        lines += ["## 成事儿周期", ""]
        if not eds:
            lines += ["（暂无事业数据，待补）", ""]
        for e in eds:
            lines += [
                f"### {e['title_zh']} — {e['domain'] or ''} · `{e['start_date'] or '?'} → {e['end_date'] or '?'}跨度: {e['start_date'] or '?'}～{e['end_date'] or '?'} · 地点: {', '.join(e['places']) if e['places'] else '—'}`".replace("跨度:", " ").strip(),
                "",
            ]
            if e.get("description_zh"):
                lines.append(f"> {e['description_zh']}")
                lines.append("")
            if e.get("outcome"):
                lines.append(f"- 结果: {e['outcome']}")
            if e.get("lesson"):
                lines.append(f"- 启发: {e['lesson']}")
            if e.get("phases"):
                lines.append("- 周期分解:")
                lines.append("  | 阶段 | 时间 | 地点 | 名场面 |")
                lines.append("  |---|---|---|---|")
                for ph in e["phases"]:
                    lines.append(
                        f"  | {ph.get('name','')} | {ph.get('start_date','') or ''}~{ph.get('end_date','') or ''} | {ph.get('place','') or ''} | {ph.get('highlight','') or ''} |"
                    )
            # highlight events in this endeavor
            hes = [ev for ev in evs if ev["endeavor_id"] == e["id"] and ev["is_highlight"]]
            if hes:
                lines.append("- 本周期名场面:")
                for he in hes:
                    lines.append(f"  - {he['date'] or '?'} · {he['place_name'] or '—'} · {he['highlight_type'] or ''} · **{he['title_zh']}** {('— ' + he['highlight_note']) if he['highlight_note'] else ''}")
            lines.append("")
        lines += ["## 名场面时间轴", ""]
        hes_all = [ev for ev in evs if ev["is_highlight"]]
        if hes_all:
            lines.append("| 日期 | 地点 | 类型 | 标题 | 释义 |")
            lines.append("|---|---|---|---|---|")
            for he in hes_all:
                lines.append(f"| {he['date'] or '?'} | {he['place_name'] or '—'} | {he['highlight_type'] or ''} | {he['title_zh']} | {he['highlight_note'] or ''} |")
            lines.append("")
        else:
            lines.append("（暂无名场面，待多源补齐）")
            lines.append("")
        lines += ["## 完整时间线（人物-时间-地点）", ""]
        lines.append("| 日期 | 地点 | 类型 | 标题 | 归属事业 |")
        lines.append("|---|---|---|---|---|")
        ed_title = {e["id"]: e["title_zh"] for e in eds}
        for ev in evs:
            lines.append(f"| {ev['date'] or '?'} | {ev['place_name'] or '—'} | {ev['event_type']} | {ev['title_zh']} | {ed_title.get(ev['endeavor_id'] or '', '')} |")
        lines.append("")
        (outdir / f"{qid}.md").write_text("\n".join(lines), encoding="utf-8")
    con.close()
    return len(persons)
