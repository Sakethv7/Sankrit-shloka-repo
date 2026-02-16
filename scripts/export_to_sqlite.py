"""Export all digest, janam patri, and MLflow data into a single SQLite DB for dashboards/reports."""
from __future__ import annotations

import os
import sys
from pathlib import Path

import mlflow
from mlflow.tracking import MlflowClient

DASHBOARD_DATA = Path(__file__).resolve().parent.parent / "dashboard" / "data"
DB_PATH = DASHBOARD_DATA / "vedic_wisdom.db"
TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI", "sqlite:///mlflow.db")
EXPERIMENT_NAME = "vedic-wisdom-weekly"


def _get_conn():
    import sqlite3
    DASHBOARD_DATA.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(DB_PATH)


def init_schema(conn) -> None:
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS runs (
        run_id TEXT PRIMARY KEY,
        week_start TEXT NOT NULL,
        verse_id TEXT,
        verse_source TEXT,
        observances TEXT,
        observance_count INTEGER,
        search_latency_ms REAL,
        start_time TEXT
    );
    CREATE TABLE IF NOT EXISTS weeks (
        week_start TEXT PRIMARY KEY,
        week_end TEXT NOT NULL,
        exported_at TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS panchang_days (
        week_start TEXT NOT NULL,
        date TEXT NOT NULL,
        vaara TEXT,
        tithi TEXT,
        paksha TEXT,
        nakshatra TEXT,
        sunrise TEXT,
        PRIMARY KEY (week_start, date)
    );
    CREATE TABLE IF NOT EXISTS observances (
        week_start TEXT NOT NULL,
        date TEXT NOT NULL,
        name TEXT,
        deity TEXT,
        description TEXT
    );
    CREATE TABLE IF NOT EXISTS daily_verses (
        week_start TEXT NOT NULL,
        date TEXT NOT NULL,
        tithi TEXT,
        paksha TEXT,
        devanagari TEXT,
        transliteration TEXT,
        meaning TEXT,
        source TEXT
    );
    CREATE TABLE IF NOT EXISTS verse_of_week (
        week_start TEXT PRIMARY KEY,
        devanagari TEXT,
        transliteration TEXT,
        meaning TEXT,
        source TEXT
    );
    CREATE TABLE IF NOT EXISTS janam_patri (
        birth_date TEXT,
        birth_time TEXT,
        birth_place TEXT,
        janma_nakshatra TEXT,
        rashi TEXT,
        theme TEXT,
        updated_at TEXT
    );
    CREATE TABLE IF NOT EXISTS janam_patri_verses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        devanagari TEXT,
        transliteration TEXT,
        meaning TEXT,
        source TEXT,
        sort_order INTEGER
    );
    """)


def export_mlflow_runs(conn) -> int:
    mlflow.set_tracking_uri(TRACKING_URI)
    client = MlflowClient()
    exp = client.get_experiment_by_name(EXPERIMENT_NAME)
    if not exp:
        return 0
    runs = client.search_runs(experiment_ids=[exp.experiment_id], order_by=["start_time DESC"])
    cur = conn.cursor()
    cur.execute("DELETE FROM runs")
    for run in runs:
        p = run.data.params or {}
        m = run.data.metrics or {}
        cur.execute(
            "INSERT OR REPLACE INTO runs (run_id, week_start, verse_id, verse_source, observances, observance_count, search_latency_ms, start_time) VALUES (?,?,?,?,?,?,?,?)",
            (
                run.info.run_id,
                p.get("week", ""),
                p.get("verse_id", ""),
                p.get("verse_source", ""),
                p.get("observances", ""),
                int(m.get("observance_count", 0)),
                float(m.get("search_latency_ms", 0)),
                str(run.info.start_time) if run.info.start_time else None,
            ),
        )
    conn.commit()
    return len(runs)


def export_current_digest(conn) -> None:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from weekly_notification import build_digest, digest_to_dict

    digest, _ = build_digest()
    d = digest_to_dict(digest)
    cur = conn.cursor()
    from datetime import datetime
    now = datetime.utcnow().isoformat() + "Z"
    cur.execute("INSERT OR REPLACE INTO weeks (week_start, week_end, exported_at) VALUES (?,?,?)", (d["week_start"], d["week_end"], now))
    cur.execute("DELETE FROM panchang_days WHERE week_start = ?", (d["week_start"],))
    for p in d.get("panchang_days", []):
        cur.execute(
            "INSERT INTO panchang_days (week_start, date, vaara, tithi, paksha, nakshatra, sunrise) VALUES (?,?,?,?,?,?,?)",
            (d["week_start"], p["date"], p["vaara"], p["tithi"], p["paksha"], p["nakshatra"], p["sunrise"]),
        )
    cur.execute("DELETE FROM observances WHERE week_start = ?", (d["week_start"],))
    for o in d.get("observances", []):
        cur.execute("INSERT INTO observances (week_start, date, name, deity, description) VALUES (?,?,?,?,?)", (d["week_start"], o["date"], o["name"], o["deity"], o["description"]))
    cur.execute("DELETE FROM daily_verses WHERE week_start = ?", (d["week_start"],))
    for v in d.get("daily_verses", []):
        verse = v.get("verse") or {}
        cur.execute(
            "INSERT INTO daily_verses (week_start, date, tithi, paksha, devanagari, transliteration, meaning, source) VALUES (?,?,?,?,?,?,?,?)",
            (d["week_start"], v["date"], v["tithi"], v["paksha"], verse.get("devanagari"), verse.get("transliteration"), verse.get("meaning"), verse.get("source")),
        )
    vo = d.get("verse_of_week") or {}
    cur.execute("INSERT OR REPLACE INTO verse_of_week (week_start, devanagari, transliteration, meaning, source) VALUES (?,?,?,?,?)", (d["week_start"], vo.get("devanagari"), vo.get("transliteration"), vo.get("meaning"), vo.get("source")))
    conn.commit()


def export_janam_patri(conn) -> bool:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from janam_patri import run_to_dict
    from datetime import datetime

    root = Path(__file__).resolve().parent.parent
    data = run_to_dict(root / "config.yaml")
    if not data:
        return False
    cur = conn.cursor()
    now = datetime.utcnow().isoformat() + "Z"
    cur.execute("DELETE FROM janam_patri")
    cur.execute(
        "INSERT INTO janam_patri (birth_date, birth_time, birth_place, janma_nakshatra, rashi, theme, updated_at) VALUES (?,?,?,?,?,?,?)",
        (data["birth_date"], data["birth_time"], data.get("birth_place"), data["janma_nakshatra"], data["rashi"], data["theme"], now),
    )
    cur.execute("DELETE FROM janam_patri_verses")
    for i, v in enumerate(data.get("verses", [])):
        cur.execute("INSERT INTO janam_patri_verses (devanagari, transliteration, meaning, source, sort_order) VALUES (?,?,?,?,?)", (v["devanagari"], v["transliteration"], v["meaning"], v["source"], i))
    conn.commit()
    return True


def main() -> None:
    conn = _get_conn()
    init_schema(conn)
    n = export_mlflow_runs(conn)
    export_current_digest(conn)
    jp = export_janam_patri(conn)
    conn.close()
    print(f"SQLite: {DB_PATH}")
    print(f"  runs: {n} | current week panchang: written | janam_patri: {'yes' if jp else 'no'}")


if __name__ == "__main__":
    main()
