from __future__ import annotations

from pathlib import Path

from arcvita.models import Endeavor, Event, Person


def write_report(persons: list[Person], events: list[Event], endeavors: list[Endeavor], path: Path) -> None:
    total = len(events)
    with_date = sum(1 for e in events if e.date)
    with_place = sum(1 for e in events if e.place_name)
    highlights = [e for e in events if e.is_highlight]
    needs = [e for e in events if e.status == "needs_review"]
    path.parent.mkdir(parents=True, exist_ok=True)
    by_qid_events: dict[str, list[Event]] = {}
    by_qid_eds: dict[str, list[Endeavor]] = {}
    for e in events:
        by_qid_events.setdefault(e.person_qid, []).append(e)
    for ed in endeavors:
        by_qid_eds.setdefault(ed.person_qid, []).append(ed)
    lines = [
        "# ArcVita 采集报告",
        "",
        f"- 人物: {len(persons)}",
        f"- 事业(成事儿周期): {len(endeavors)}",
        f"- 事件: {total}（有时间 {with_date}/{total}，有地点 {with_place}/{total}）",
        f"- 名场面: {len(highlights)}（成语/代表作/演讲/发明等）",
        f"- 完整率: 时间 {with_date/total*100:.1f}% / 地点 {with_place/total*100:.1f}%" if total else "- 完整率: 0",
        "",
        "## 人物一览（成事儿精选）",
        "| QID | 姓名 | 原型 | 事业数 | 事件数 | 名场面 | 角色 |",
        "|---|---|---|---|---|---|---|",
    ]
    for p in persons:
        ec = len(by_qid_events.get(p.qid, []))
        edc = len(by_qid_eds.get(p.qid, []))
        hc = len([e for e in by_qid_events.get(p.qid, []) if e.is_highlight])
        lines.append(f"| {p.qid} | {p.name_zh} | {p.archetype or '—'} | {edc} | {ec} | {hc} | {p.role} |")
    # 名场面总表
    lines += ["", "## 名场面总表（成语/代表作/发明/演讲）", "| 日期 | 人物 | 类型 | 标题 | 释义 |", "|---|---|---|---|---|"]
    pmap = {p.qid: p.name_zh for p in persons}
    for e in sorted(highlights, key=lambda x: x.date or "9999")[:30]:
        lines.append(f"| {e.date or '?'} | {pmap.get(e.person_qid,'?')} | {e.highlight_type or ''} | {e.title_zh} | {e.highlight_note or e.description_zh or ''} |")
    if len(highlights) > 30:
        lines.append(f"| … | 还有 {len(highlights)-30} | | | |")
    # 成事儿周期示例
    lines += ["", "## 成事儿周期示例（从开头到结束）"]
    # 优先展示有 phases 的
    shown = 0
    for p in persons:
        if shown >= 6:
            break
        eds = by_qid_eds.get(p.qid, [])
        # 只展示带 phases 的，体现周期感
        eds = [ed for ed in eds if ed.phases] or eds[:1]
        if not eds:
            continue
        shown += 1
        lines.append(f"### {p.name_zh} ({p.qid}) · {p.archetype or ''}")
        for ed in eds:
            lines.append(f"- **{ed.title_zh}** {ed.start_date or '?'} → {ed.end_date or '?'} · {', '.join(ed.places) if ed.places else '地点待补'}")
            if ed.description_zh:
                lines.append(f"  > {ed.description_zh}")
            if ed.phases:
                lines.append("  - 阶段:")
                for ph in ed.phases:
                    hl = f" 名场面: {ph.highlight}" if ph.highlight else ""
                    lines.append(f"    - {ph.name}: {ph.start_date or ''}~{ph.end_date or ''} {ph.place or ''}{hl}")
            if ed.outcome:
                lines.append(f"  - 结果: {ed.outcome}")
            if ed.lesson:
                lines.append(f"  - 启发: {ed.lesson}")
        evs = sorted(by_qid_events.get(p.qid, []), key=lambda x: x.date or "9999")
        lines.append(f"  - 时间线 {len(evs)} 条（★为名场面）:")
        for ev in evs:
            star = "★" if ev.is_highlight else "·"
            lines.append(f"    - {star} {ev.date or '??'} · {ev.place_name or '—'} · {ev.title_zh} ({ev.event_type}) {('/' + ev.highlight_type) if ev.is_highlight and ev.highlight_type else ''}")
        lines.append("")
    lines += ["", "## 待补清单 needs_review", f"- {len(needs)} 条事件缺时间/地点或需AI查证"]
    for e in needs[:20]:
        lines.append(f"- {e.person_qid} {e.id} {e.title_zh} 缺{e.needs_review_reason or '信息'}")
    if len(needs) > 20:
        lines.append(f"- … 还有 {len(needs)-20} 条")
    lines += [
        "",
        "## 使用",
        "- YAML 真源: data/processed/persons.yaml / events.yaml / endeavors.yaml / highlights.yaml",
        "- 单人可查阅: data/processed/timelines/<QID>.md",
        "- SQLite: data/biography.db（可重建，视图 timeline/highlights/endeavor_timeline/public_persons）",
        "- 检索: `from arcvita.query import find_by_dilemma, find_by_place, highlights_for`",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")
