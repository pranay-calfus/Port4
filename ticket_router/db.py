"""SQLite persistence for routed tickets and teams.

Plain sqlite3 (stdlib, no new dependency), one connection per call - this is
a low-traffic Streamlit app, not a service under concurrent write load, so
there's no need for a pooled/long-lived connection. Every function accepts an
optional `db_path` override (falling back to `config.TICKET_DB_PATH`) purely
so tests can point at an isolated temp file instead of the real database.
"""

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime

from ticket_router.config import config
from ticket_router.models import ASSIGNED_TEAMS, AssignedTeam, Priority


def _resolve_path(db_path: str | None) -> str:
    return db_path or config.TICKET_DB_PATH


@contextmanager
def _connect(db_path: str | None) -> Iterator[sqlite3.Connection]:
    # timeout=10 makes a connection that finds the database briefly locked
    # by another writer retry for up to 10s instead of raising
    # "database is locked" immediately - Streamlit reruns the whole script
    # on every interaction, across every open tab/session, so two of these
    # short-lived connections legitimately can overlap. WAL journal mode
    # additionally lets readers proceed without blocking on a writer at
    # all, which is the standard fix for SQLite-under-a-web-app lock
    # contention.
    conn = sqlite3.connect(_resolve_path(db_path), timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db(db_path: str | None = None) -> None:
    """Creates the `teams` and `tickets` tables if they don't already exist,
    and seeds `teams` from ASSIGNED_TEAMS. Called on every app start/rerun
    (so it can self-heal if the database file is ever reset while the
    server keeps running), so this all has to be safe to repeat.

    The seeding insert only runs when the teams table isn't already fully
    seeded - once it is (true for every rerun after the very first), this
    function does nothing but two no-op `CREATE TABLE IF NOT EXISTS` checks
    and a `SELECT`, no write transaction, which matters because every rerun
    across every open tab/session calls this. Still uses `INSERT OR IGNORE`
    rather than a bare INSERT for the rare case where two sessions both see
    an unseeded table and race to seed it.
    """
    with _connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS teams (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS tickets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                message TEXT NOT NULL,
                category TEXT NOT NULL,
                ai_priority TEXT NOT NULL,
                final_priority TEXT NOT NULL,
                ai_assigned_team TEXT NOT NULL,
                assigned_team TEXT NOT NULL,
                reasoning TEXT NOT NULL,
                confidence REAL NOT NULL,
                model_used TEXT,
                status TEXT NOT NULL DEFAULT 'Pending',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        existing = conn.execute("SELECT COUNT(*) FROM teams").fetchone()[0]
        if existing < len(ASSIGNED_TEAMS):
            conn.executemany(
                "INSERT OR IGNORE INTO teams (name) VALUES (?)",
                [(team,) for team in ASSIGNED_TEAMS],
            )


def add_ticket(
    message: str,
    category: str,
    ai_priority: Priority,
    final_priority: Priority,
    assigned_team: AssignedTeam,
    reasoning: str,
    confidence: float,
    model_used: str | None,
    db_path: str | None = None,
) -> int:
    """Inserts a newly-routed ticket. `ai_priority` is the model's suggestion;
    `final_priority` is whatever the submitter actually chose (the two may
    differ). `status` starts "Pending" - see set_status(). Returns the new
    ticket's id.
    """
    now = datetime.now(UTC).isoformat()
    with _connect(db_path) as conn:
        cursor = conn.execute(
            """
            INSERT INTO tickets (
                message, category, ai_priority, final_priority,
                ai_assigned_team, assigned_team, reasoning, confidence,
                model_used, status, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'Pending', ?, ?)
            """,
            (
                message,
                category,
                ai_priority,
                final_priority,
                assigned_team,
                assigned_team,
                reasoning,
                confidence,
                model_used,
                now,
                now,
            ),
        )
        return cursor.lastrowid


def _touch(conn: sqlite3.Connection, ticket_id: int, column: str, value: str) -> None:
    conn.execute(
        f"UPDATE tickets SET {column} = ?, updated_at = ? WHERE id = ?",
        (value, datetime.now(UTC).isoformat(), ticket_id),
    )


def set_final_priority(ticket_id: int, priority: Priority, db_path: str | None = None) -> None:
    with _connect(db_path) as conn:
        _touch(conn, ticket_id, "final_priority", priority)


def reassign_team(ticket_id: int, new_team: AssignedTeam, db_path: str | None = None) -> None:
    with _connect(db_path) as conn:
        _touch(conn, ticket_id, "assigned_team", new_team)


def set_status(ticket_id: int, status: str, db_path: str | None = None) -> None:
    with _connect(db_path) as conn:
        _touch(conn, ticket_id, "status", status)


def list_teams(db_path: str | None = None) -> list[str]:
    with _connect(db_path) as conn:
        rows = conn.execute("SELECT name FROM teams ORDER BY name").fetchall()
        return [row["name"] for row in rows]


def list_tickets_for_team(team: str, db_path: str | None = None) -> list[dict]:
    """Returns all tickets currently assigned to `team`, sorted by priority
    (High, then Medium, then Low), most recently created first within each
    priority.
    """
    with _connect(db_path) as conn:
        rows = conn.execute(
            """
            SELECT * FROM tickets
            WHERE assigned_team = ?
            ORDER BY
                CASE final_priority WHEN 'High' THEN 0 WHEN 'Medium' THEN 1 WHEN 'Low' THEN 2 END,
                created_at DESC
            """,
            (team,),
        ).fetchall()
        return [dict(row) for row in rows]


def list_all_tickets(db_path: str | None = None) -> list[dict]:
    """Returns every ticket across all teams - Pending first (needs
    attention), then by priority (High to Low), then most recently created.
    """
    with _connect(db_path) as conn:
        rows = conn.execute(
            """
            SELECT * FROM tickets
            ORDER BY
                CASE status WHEN 'Pending' THEN 0 ELSE 1 END,
                CASE final_priority WHEN 'High' THEN 0 WHEN 'Medium' THEN 1 WHEN 'Low' THEN 2 END,
                created_at DESC
            """
        ).fetchall()
        return [dict(row) for row in rows]


def count_by_status(team: str, db_path: str | None = None) -> dict[str, int]:
    with _connect(db_path) as conn:
        rows = conn.execute(
            "SELECT status, COUNT(*) AS n FROM tickets WHERE assigned_team = ? GROUP BY status",
            (team,),
        ).fetchall()
        counts = {"Pending": 0, "Closed": 0}
        counts.update({row["status"]: row["n"] for row in rows})
        return counts


def pending_counts_by_team(db_path: str | None = None) -> dict[str, int]:
    """Returns {team: pending_ticket_count} in one query, for the admin
    dashboard's team-picker labels. Teams with no pending tickets are
    simply absent - callers should default missing teams to 0.
    """
    with _connect(db_path) as conn:
        rows = conn.execute(
            "SELECT assigned_team, COUNT(*) AS n FROM tickets "
            "WHERE status = 'Pending' GROUP BY assigned_team"
        ).fetchall()
        return {row["assigned_team"]: row["n"] for row in rows}


def delete_ticket(ticket_id: int, db_path: str | None = None) -> None:
    with _connect(db_path) as conn:
        conn.execute("DELETE FROM tickets WHERE id = ?", (ticket_id,))
