from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from arcvita.models import Endeavor, Event, Person


def _j(v) -> str:
    return json.dumps(v, ensure_ascii=False)


def build_db(path: Path, persons: list[Person], events: list[Event], endeavors: list[Endeavor]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        path.unlink()
    con = sqlite3.connect(path)
    cur = con.cursor()
    cur.executescript(
        """
    CREATE TABLE persons (
        qid TEXT PRIMARY KEY,
        name_zh TEXT, name_en TEXT,
        birth_date TEXT, death_date TEXT,
        birth_place TEXT, death_place TEXT,
        occupations TEXT, domains TEXT,
        era TEXT,
        role TEXT, sensitivity TEXT, visibility TEXT,
        lesson TEXT, summary_zh TEXT, summary_first_person TEXT,
        archetype TEXT,
        dilemmas TEXT, keywords TEXT,
        source_urls TEXT, status TEXT, needs_review_reason TEXT
    );
    CREATE TABLE endeavors (
        id TEXT PRIMARY KEY,
        person_qid TEXT,
        title_zh TEXT, domain TEXT,
        start_date TEXT, end_date TEXT,
        places TEXT, place_qids TEXT,
        status TEXT, description_zh TEXT, outcome TEXT, lesson TEXT,
        phases TEXT,
        dilemmas TEXT, keywords TEXT,
        event_ids TEXT, highlight_event_ids TEXT,
        sources TEXT, review_status TEXT,
        FOREIGN KEY(person_qid) REFERENCES persons(qid)
    );
    CREATE TABLE events (
        id TEXT PRIMARY KEY,
        person_qid TEXT,
        endeavor_id TEXT,
        date TEXT, date_precision TEXT,
        place_name TEXT, place_qid TEXT, place_coord TEXT,
        event_type TEXT, title_zh TEXT, description_zh TEXT,
        first_person_quote TEXT,
        is_highlight INTEGER, highlight_type TEXT, highlight_note TEXT,
        sources TEXT, status TEXT, needs_review_reason TEXT,
        FOREIGN KEY(person_qid) REFERENCES persons(qid)
    );
    CREATE INDEX idx_events_person_date ON events(person_qid, date);
    CREATE INDEX idx_events_endeavor ON events(endeavor_id);
    CREATE INDEX idx_events_highlight ON events(is_highlight);
    CREATE INDEX idx_endeavors_person ON endeavors(person_qid);
    """
    )
    for p in persons:
        cur.execute(
            "INSERT INTO persons VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                p.qid,
                p.name_zh,
                p.name_en,
                p.birth_date,
                p.death_date,
                p.birth_place,
                p.death_place,
                _j(p.occupations),
                _j(p.domains),
                p.era,
                p.role,
                p.sensitivity,
                p.visibility,
                p.lesson,
                p.summary_zh,
                p.summary_first_person,
                p.archetype,
                _j(p.dilemmas),
                _j(p.keywords),
                _j(p.source_urls),
                p.status,
                p.needs_review_reason,
            ),
        )
    for e in endeavors:
        cur.execute(
            "INSERT INTO endeavors VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                e.id,
                e.person_qid,
                e.title_zh,
                e.domain,
                e.start_date,
                e.end_date,
                _j(e.places),
                _j(e.place_qids),
                e.status,
                e.description_zh,
                e.outcome,
                e.lesson,
                _j([ph.model_dump() if hasattr(ph, "model_dump") else ph for ph in e.phases]),
                _j(e.dilemmas),
                _j(e.keywords),
                _j(e.event_ids),
                _j(e.highlight_event_ids),
                _j(e.sources),
                e.review_status,
            ),
        )
    for ev in events:
        cur.execute(
            "INSERT INTO events VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                ev.id,
                ev.person_qid,
                ev.endeavor_id,
                ev.date,
                ev.date_precision,
                ev.place_name,
                ev.place_qid,
                _j(ev.place_coord) if ev.place_coord else None,
                ev.event_type,
                ev.title_zh,
                ev.description_zh,
                ev.first_person_quote,
                1 if ev.is_highlight else 0,
                ev.highlight_type,
                ev.highlight_note,
                _j(ev.sources),
                ev.status,
                ev.needs_review_reason,
            ),
        )
    cur.executescript(
        """
    CREATE VIEW timeline AS
    SELECT e.person_qid, p.name_zh as person_name, e.date, e.place_name, e.title_zh, e.event_type, e.is_highlight, e.highlight_type, e.endeavor_id
    FROM events e JOIN persons p ON p.qid=e.person_qid
    ORDER BY e.person_qid, e.date;
    CREATE VIEW highlights AS
    SELECT e.*, p.name_zh as person_name FROM events e JOIN persons p ON p.qid=e.person_qid WHERE e.is_highlight=1 ORDER BY e.date;
    CREATE VIEW public_persons AS SELECT * FROM persons WHERE visibility='public';
    CREATE VIEW endeavor_timeline AS
    SELECT en.person_qid, en.title_zh as endeavor, en.start_date, en.end_date, en.places, en.phases, en.outcome FROM endeavors en ORDER BY en.person_qid, en.start_date;
    """
    )
    con.commit()
    con.close()
