"""
SQLite setup. Plain sqlite3 (stdlib) is used on purpose here rather than an
ORM - the schema is small and stable, and it keeps the app easy for anyone
on the team to read and modify later.
"""
import sqlite3
from pathlib import Path
from contextlib import contextmanager

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "eod.db"

# The 7 pages currently live. Add more here (or later via SQL / an admin
# screen) - the app reads pages from the table, not from this list, so this
# only matters the first time the database is created.
DEFAULT_PAGES = [
    "Golden Adventure",
    "Lucky Penny",
    "Sapphire",
    "Lightning Slots",
    "Fishable",
    "Loot",
    "Jazzy Danny's",
]


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def db_cursor():
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with db_cursor() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                salt TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'staff',
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS pages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                active INTEGER NOT NULL DEFAULT 1
            );

            CREATE TABLE IF NOT EXISTS eod_reports (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                page_id INTEGER NOT NULL REFERENCES pages(id),
                user_id INTEGER NOT NULL REFERENCES users(id),
                report_date TEXT NOT NULL,

                redeem_processed_count INTEGER NOT NULL,
                redeem_paid_count INTEGER NOT NULL,
                redeem_pending_count INTEGER NOT NULL,

                redeem_paid_amount REAL NOT NULL DEFAULT 0,
                redeem_pending_amount REAL NOT NULL DEFAULT 0,
                grand_total_deposit REAL NOT NULL DEFAULT 0,

                screenshot_path TEXT,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS deposit_breakdown (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                eod_id INTEGER NOT NULL REFERENCES eod_reports(id) ON DELETE CASCADE,
                method TEXT NOT NULL,
                amount REAL NOT NULL
            );

            CREATE TABLE IF NOT EXISTS redeem_breakdown (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                eod_id INTEGER NOT NULL REFERENCES eod_reports(id) ON DELETE CASCADE,
                method TEXT NOT NULL,
                amount REAL NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_eod_page_date ON eod_reports(page_id, report_date);
            """
        )
        # Seed default pages if the table is empty (first run only).
        existing = conn.execute("SELECT COUNT(*) AS c FROM pages").fetchone()["c"]
        if existing == 0:
            conn.executemany(
                "INSERT INTO pages (name) VALUES (?)",
                [(p,) for p in DEFAULT_PAGES],
            )
