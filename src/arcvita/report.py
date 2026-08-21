from __future__ import annotations

from pathlib import Path

from arcvita.models import Endeavor, Event, Person


def write_report(persons: list[Person], events: list[Event], endeavors: list[Endeavor], path: Path) -> None:
    total = len(events)
    with_date = sum(1 for e in events if e.date)
    with_place = sum(1 for e in events if e.place_name)
    needs = [e for e in events if e.status == "needs_review"]
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# ArcVita 采集报告",
        "",
        f"- 人物: {len(persons)}",
        f"- 事业(做事流): {len(endeavors)}",
        f"- 事件: {total}（有时间 {with_date}/{total}，有地点 {with_place}/{total}）",
        f"- 完整率: 时间 {with_date/total*100:.1f}% / 地点 {with_place/total*100:.1f}%" if total else "- 完整率: 0",
        "",
        "## 人物一览",
        "| QID | 姓名 | 事业数 | 事件数 | 角色 | 可见性 |",
        "|---|---|---|---|---|---|",
    ]
    by_qid_events: dict[str, list[Event]] = {}
    by_qid_eds: dict[str, list[Endeavor]] = {}
    for e in events:
        by_qid_events.setdefault(e.person_qid, []).append(e)
    for ed in endeavors:
        by_qid_eds.setdefault(ed.person_qid, []).append(ed)
    for p in persons:
        ec = len(by_qid_events.get(p.qid, []))
        edc = len(by_qid_eds.get(p.qid, []))
        lines.append(f"| {p.qid} | {p.name_zh} | {edc} | {ec} | {p.role} | {p.visibility} |")
    lines += ["", "## 做事流示例（有始有终 + 地点）"]
    for p in persons[:5]:
        eds = by_qid_eds.get(p.qid, [])
        if not eds:
            continue
        lines.append(f"### {p.name_zh} ({p.qid})")
        for ed in eds:
            lines.append(f"- **{ed.title_zh}** {ed.start_date or '?'} → {ed.end_date or '?'} · {', '.join(ed.places) if ed.places else '地点待补'}")
            if ed.description_zh:
                lines.append(f"  > {ed.description_zh}")
            if ed.outcome:
                lines.append(f"  - 结果: {ed.outcome}")
            if ed.lesson:
                lines.append(f"  - 启发: {ed.lesson}")
        evs = sorted(by_qid_events.get(p.qid, []), key=lambda x: x.date or "9999")
        lines.append(f"  - 时间线 {len(evs)} 条，示例:")
        for ev in evs[:5]:
            lines.append(f"    - {ev.date or '??'} · {ev.place_name or '—'} · {ev.title_zh} ({ev.event_type})")
        lines.append("")
    lines += ["", "## 待补清单 needs_review", f"- {len(needs)} 条事件缺时间/地点或需AI查证"]
    for e in needs[:20]:
        lines.append(f"- {e.person_qid} {e.id} {e.title_zh} 缺{e.needs_review_reason or '信息'}")
    if len(needs) > 20:
        lines.append(f"- … 还有 {len(needs)-20} 条")
    lines += ["", "## 使用", "- YAML 真源: data/processed/persons.yaml / events.yaml / endeavors.yaml", "- SQLite: data/biography.db（可重建）", "- 公开视图: SELECT * FROM public_persons; SELECT * FROM timeline WHERE person_qid='Q935' ORDER BY date;"]
    path.write_text("\n".join(lines), encoding="utf-8")
