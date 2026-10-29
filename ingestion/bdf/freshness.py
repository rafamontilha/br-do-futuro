"""Source schedule freshness calculation, circuit breaker, and replay helpers."""
import math
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from uuid import uuid4
import psycopg
from psycopg.rows import dict_row


def calculate_freshness(
    next_expected_at: datetime,
    tolerance_window_hours: int = 4,
    current_time: datetime | None = None,
) -> tuple[bool, Decimal]:
    """Calculate whether a schedule is stale and how many hours it is delayed.

    Returns (is_stale, current_delay_hours).
    """
    if current_time is None:
        current_time = datetime.now(timezone.utc)

    # Ensure timezone awareness
    if next_expected_at.tzinfo is None:
        next_expected_at = next_expected_at.replace(tzinfo=timezone.utc)
    if current_time.tzinfo is None:
        current_time = current_time.replace(tzinfo=timezone.utc)

    tolerance = timedelta(hours=tolerance_window_hours)
    deadline = next_expected_at + tolerance

    if current_time > deadline:
        delay_seconds = (current_time - deadline).total_seconds()
        delay_hours = Decimal(str(round(delay_seconds / 3600.0, 2)))
        return True, delay_hours

    return False, Decimal("0.00")


def refresh_source_schedules(conn: psycopg.Connection, current_time: datetime | None = None) -> list[dict]:
    """Recompute is_stale and current_delay_hours for all records in source_schedules."""
    if current_time is None:
        current_time = datetime.now(timezone.utc)

    rows = conn.execute(
        "SELECT id, indicator_id, next_expected_at, tolerance_window_hours FROM source_schedules FOR UPDATE"
    ).fetchall()

    updated = []
    for r in rows:
        row = dict(r) if hasattr(r, "keys") else {
            "id": r[0],
            "indicator_id": r[1],
            "next_expected_at": r[2],
            "tolerance_window_hours": r[3],
        }
        is_stale, delay_hours = calculate_freshness(
            row["next_expected_at"],
            row["tolerance_window_hours"],
            current_time,
        )
        conn.execute(
            """UPDATE source_schedules
               SET is_stale = %s, current_delay_hours = %s, updated_at = clock_timestamp()
               WHERE id = %s""",
            (is_stale, delay_hours, row["id"]),
        )
        updated.append(dict(id=row["id"], indicator_id=row["indicator_id"], is_stale=is_stale, delay_hours=str(delay_hours)))

    return updated


def record_source_failure(
    conn: psycopg.Connection,
    indicator_id: str,
    error_message: str,
    failure_threshold: int = 3,
) -> dict:
    """Record a failure for a source schedule and open circuit if threshold is reached."""
    row = conn.execute(
        """UPDATE source_schedules
           SET consecutive_failures = consecutive_failures + 1,
               circuit_open = (consecutive_failures + 1 >= %s),
               last_checked_at = clock_timestamp(),
               updated_at = clock_timestamp(),
               metadata = jsonb_set(metadata, '{last_error}', to_jsonb(%s::text))
           WHERE indicator_id = %s
           RETURNING id, indicator_id, consecutive_failures, circuit_open""",
        (failure_threshold, error_message, indicator_id),
    ).fetchone()

    if not row:
        return {}
    if hasattr(row, "keys"):
        return dict(row)
    return {
        "id": row[0],
        "indicator_id": row[1],
        "consecutive_failures": row[2],
        "circuit_open": row[3],
    }


def record_source_success(conn: psycopg.Connection, indicator_id: str) -> dict:
    """Record a successful ingestion, resetting failures and closing circuit."""
    row = conn.execute(
        """UPDATE source_schedules
           SET consecutive_failures = 0,
               circuit_open = false,
               last_checked_at = clock_timestamp(),
               last_successful_at = clock_timestamp(),
               updated_at = clock_timestamp()
           WHERE indicator_id = %s
           RETURNING id, indicator_id, consecutive_failures, circuit_open, last_successful_at""",
        (indicator_id,),
    ).fetchone()

    if not row:
        return {}
    if hasattr(row, "keys"):
        return dict(row)
    return {
        "id": row[0],
        "indicator_id": row[1],
        "consecutive_failures": row[2],
        "circuit_open": row[3],
        "last_successful_at": row[4],
    }


def execute_outbox_replay(
    conn: psycopg.Connection,
    reason: str,
    triggered_by: str = "operator",
    filter_indicator_id: str | None = None,
    filter_event_type: str | None = None,
) -> dict:
    """Trigger a controlled replay of outbox events and record in outbox_replay_audit."""
    if not reason or not reason.strip():
        raise ValueError("Audit reason is required for operational replay")

    audit_id = f"replay-{uuid4()}"
    conn.execute(
        """INSERT INTO outbox_replay_audit (id, triggered_by, filter_event_type, filter_indicator_id, reason, status)
           VALUES (%s, %s, %s, %s, %s, 'running')""",
        (audit_id, triggered_by, filter_event_type, filter_indicator_id, reason.strip()),
    )

    query = """
        UPDATE outbox
        SET status = 'pending', processed_at = NULL
        WHERE status IN ('processed', 'dead_letter')
    """
    params: list = []

    if filter_event_type:
        query += " AND event_type = %s"
        params.append(filter_event_type)

    if filter_indicator_id:
        query += " AND payload->>'indicator_id' = %s"
        params.append(filter_indicator_id)

    res = conn.execute(query, params)
    replayed_count = res.rowcount

    conn.execute(
        """UPDATE outbox_replay_audit
           SET status = 'completed', events_replayed_count = %s, completed_at = clock_timestamp()
           WHERE id = %s""",
        (replayed_count, audit_id),
    )

    return {
        "replay_id": audit_id,
        "triggered_by": triggered_by,
        "events_replayed_count": replayed_count,
        "reason": reason.strip(),
        "status": "completed",
    }
