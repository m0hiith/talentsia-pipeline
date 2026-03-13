"""
SQLite database manager for the Talentsia pipeline.
Provides connection management, schema initialization, and query helpers.
"""

import sqlite3
import os
from pathlib import Path
from contextlib import contextmanager

DB_DIR = Path(__file__).parent
DB_PATH = DB_DIR / "talentsia.db"
SCHEMA_PATH = DB_DIR / "schema.sql"


def get_connection() -> sqlite3.Connection:
    """Get a SQLite connection with row factory enabled."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA busy_timeout=5000")
    return conn


@contextmanager
def get_db():
    """Context manager for database connections."""
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    """Initialize the database with the schema."""
    with get_db() as conn:
        schema_sql = SCHEMA_PATH.read_text()
        conn.executescript(schema_sql)
    print(f"✅ Database initialized at {DB_PATH}")


def query(sql: str, params: tuple = ()) -> list[dict]:
    """Execute a query and return results as list of dicts."""
    with get_db() as conn:
        cursor = conn.execute(sql, params)
        rows = cursor.fetchall()
        return [dict(row) for row in rows]


def execute(sql: str, params: tuple = ()) -> int:
    """Execute a statement and return lastrowid."""
    with get_db() as conn:
        cursor = conn.execute(sql, params)
        return cursor.lastrowid


def execute_many(sql: str, params_list: list[tuple]) -> None:
    """Execute a statement with multiple parameter sets."""
    with get_db() as conn:
        conn.executemany(sql, params_list)


def get_table_counts() -> dict:
    """Get row counts for all tables — useful for dashboard stats."""
    tables = ["stories", "scripts", "media", "reels", "publish_history", "agent_logs", "schedule_slots"]
    counts = {}
    with get_db() as conn:
        for table in tables:
            try:
                row = conn.execute(f"SELECT COUNT(*) as c FROM {table}").fetchone()
                counts[table] = dict(row)["c"]
            except Exception:
                counts[table] = 0
    return counts


def log_agent_run(agent_name: str, run_number: int, status: str,
                  duration: float, result_summary: str = None,
                  error_message: str = None) -> None:
    """Log an agent run to the agent_logs table."""
    import uuid
    with get_db() as conn:
        conn.execute(
            """INSERT INTO agent_logs (id, agent_name, run_number, status,
               duration_secs, result_summary, error_message)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                str(uuid.uuid4()),
                agent_name,
                run_number,
                status,
                duration,
                result_summary,
                error_message,
            ),
        )


# Auto-init on first import if DB doesn't exist
if not DB_PATH.exists():
    init_db()
