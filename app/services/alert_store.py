"""SQLite-backed alert queue for the hosted web app."""

import sqlite3
from datetime import datetime, timezone


def _get_connection(db_file):
    """Open a SQLite connection with rows returned like dictionaries."""
    connection = sqlite3.connect(db_file)
    connection.row_factory = sqlite3.Row
    return connection


def init_alert_store(db_file) -> None:
    """Create the alert queue table on first startup."""
    with _get_connection(db_file) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS queued_alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_email TEXT NOT NULL,
                ip_address TEXT NOT NULL,
                attempt_timestamp TEXT NOT NULL,
                created_at TEXT NOT NULL,
                brute_force INTEGER NOT NULL DEFAULT 0,
                failure_count INTEGER NOT NULL DEFAULT 1,
                status TEXT NOT NULL DEFAULT 'pending',
                sent_at TEXT
            )
            """
        )
        connection.commit()


def queue_alert(
    db_file,
    user_email: str,
    ip_address: str,
    attempt_timestamp,
    brute_force: bool,
    failure_count: int,
) -> None:
    """Store a pending alert for the local notifier service."""
    created_at = datetime.now(timezone.utc).isoformat()
    with _get_connection(db_file) as connection:
        connection.execute(
            """
            INSERT INTO queued_alerts (
                user_email,
                ip_address,
                attempt_timestamp,
                created_at,
                brute_force,
                failure_count,
                status
            )
            VALUES (?, ?, ?, ?, ?, ?, 'pending')
            """,
            (
                user_email,
                ip_address,
                attempt_timestamp.isoformat(),
                created_at,
                int(brute_force),
                failure_count,
            ),
        )
        connection.commit()


def fetch_pending_alerts(db_file, limit: int):
    """Fetch a batch of unsent alerts for the local notifier."""
    with _get_connection(db_file) as connection:
        rows = connection.execute(
            """
            SELECT
                id,
                user_email,
                ip_address,
                attempt_timestamp,
                created_at,
                brute_force,
                failure_count
            FROM queued_alerts
            WHERE status = 'pending'
            ORDER BY id ASC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()

    return [
        {
            "id": row["id"],
            "user_email": row["user_email"],
            "ip_address": row["ip_address"],
            "attempt_timestamp": row["attempt_timestamp"],
            "created_at": row["created_at"],
            "brute_force": bool(row["brute_force"]),
            "failure_count": row["failure_count"],
        }
        for row in rows
    ]


def mark_alert_sent(db_file, alert_id: int, sent_at) -> None:
    """Mark an alert as delivered so the local notifier does not resend it."""
    with _get_connection(db_file) as connection:
        connection.execute(
            """
            UPDATE queued_alerts
            SET status = 'sent',
                sent_at = ?
            WHERE id = ?
            """,
            (sent_at.isoformat(), alert_id),
        )
        connection.commit()
