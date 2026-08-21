from __future__ import annotations

import sqlite3
from pathlib import Path

from arcvita.models import Endeavor, Event, Person


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
        source_urls TEXT, status TEXT, needs_review_reason TEXT
    );
    CREATE TABLE endeavors (
        id TEXT PRIMARY KEY,
        person_qid TEXT,
        title_zh TEXT, domain TEXT,
        start_date TEXT, end_date TEXT,
        places TEXT, place_qids TEXT,
        status TEXT, description_zh TEXT, outcome TEXT, lesson TEXT,
        event_ids TEXT, sources TEXT, review_status TEXT,
        FOREIGN KEY(person_qid) REFERENCES persons(qid)
    );
    CREATE TABLE events (
        id TEXT PRIMARY KEY,
        person_qid TEXT,
        endeavor_id TEXT,
        date TEXT, date_precision TEXT,
        place_name TEXT, place_qid TEXT, place_coord TEXT,
        event_type TEXT, title_zh TEXT, description_zh TEXT,
        first_person_quote TEXT, sources TEXT, status TEXT, needs_review_reason TEXT,
        FOREIGN KEY(person_qid) REFERENCES persons(qid)
    );
    CREATE INDEX idx_events_person_date ON events(person_qid, date);
    CREATE INDEX idx_events_endeavor ON events(endeavor_id);
    CREATE INDEX idx_endeavors_person ON endeavors(person_qid);
    """
    )
    import json

    for p in persons:
        cur.execute(
            "INSERT INTO persons VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                p.qid,
                p.name_zh,
                p.name_en,
                p.birth_date,
                p.death_date,
                p.birth_place,
                p.death_place,
                json.dumps(p.occupations, ensure_ascii=False),
                json.dumps(p.domains, ensure_ascii=False),
                p.era,
                p.role,
                p.sensitivity,
                p.visibility,
                p.lesson,
                p.summary_zh,
                p.summary_first_person,
                json.dumps(p.source_urls, ensure_ascii=False),
                p.status,
                p.needs_review_reason,
            ),
        )
    for e in endeavors:
        cur.execute(
            "INSERT INTO endeavors VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                e.id,
                e.person_qid,
                e.title_zh,
                e.domain,
                e.start_date,
                e.end_date,
                json.dumps(e.places, ensure_ascii=False),
                json.dumps(e.place_qids, ensure_ascii=False),
                e.status,
                e.description_zh,
                e.outcome,
                e.lesson,
                json.dumps(e.event_ids, ensure_ascii=False),
                json.dumps(e.sources, ensure_ascii=False),
                e.review_status,
            ),
        )
    for ev in events:
        cur.execute(
            "INSERT INTO events VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                ev.id,
                ev.person_qid,
                ev.endeavor_id,
                ev.date,
                ev.date_precision,
                ev.place_name,
                ev.place_qid,
                json.dumps(ev.place_coord, ensure_ascii=False) if ev.place_coord else None,
                ev.event_type,
                ev.title_zh,
                ev.description_zh,
                ev.first_person_quote,
                json.dumps(ev.sources, ensure_ascii=False),
                ev.status,
                ev.needs_review_reason,
            ),
        )
    cur.executescript(
        """
    CREATE VIEW timeline AS
    SELECT e.person_qid, p.name_zh as person_name, e.date, e.place_name, e.title_zh, e.event_type, e.endeavor_id
    FROM events e JOIN persons p ON p.qid=e.person_qid
    ORDER BY e.person_qid, e.date;
    CREATE VIEW public_persons AS SELECT * FROM persons WHERE visibility='public';
    """
    )
    con.commit()
    con.close()
