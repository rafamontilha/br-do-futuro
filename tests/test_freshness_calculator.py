from datetime import datetime, timezone, timedelta
from decimal import Decimal
import pytest

from bdf.freshness import calculate_freshness, execute_outbox_replay, record_source_failure, record_source_success


def test_calculate_freshness_within_window():
    expected = datetime(2026, 10, 10, 9, 0, tzinfo=timezone.utc)
    current = datetime(2026, 10, 10, 11, 0, tzinfo=timezone.utc)  # 2h after expected, tolerance is 4h

    is_stale, delay = calculate_freshness(expected, tolerance_window_hours=4, current_time=current)
    assert not is_stale
    assert delay == Decimal("0.00")


def test_calculate_freshness_exceeded_window():
    expected = datetime(2026, 10, 10, 9, 0, tzinfo=timezone.utc)
    # 7 hours after expected -> 3 hours past 4h tolerance window
    current = datetime(2026, 10, 10, 16, 0, tzinfo=timezone.utc)

    is_stale, delay = calculate_freshness(expected, tolerance_window_hours=4, current_time=current)
    assert is_stale
    assert delay == Decimal("3.00")


def test_replay_without_reason_raises_error():
    class DummyConn:
        pass
    with pytest.raises(ValueError, match="reason is required"):
        execute_outbox_replay(DummyConn(), reason="   ")


def test_freshness_and_circuit_breaker_db(db):
    import psycopg
    from bdf.freshness import refresh_source_schedules

    with psycopg.connect(db) as conn:
        # Initial schedule check
        schedules = conn.execute("SELECT indicator_id, consecutive_failures, circuit_open FROM source_schedules").fetchall()
        assert len(schedules) >= 3

        # Simulate failures for IPCA
        res1 = record_source_failure(conn, "br.ipca.monthly", "Timeout 1", failure_threshold=3)
        assert res1["consecutive_failures"] == 1
        assert not res1["circuit_open"]

        res2 = record_source_failure(conn, "br.ipca.monthly", "Timeout 2", failure_threshold=3)
        assert res2["consecutive_failures"] == 2
        assert not res2["circuit_open"]

        res3 = record_source_failure(conn, "br.ipca.monthly", "503 Service Unavailable", failure_threshold=3)
        assert res3["consecutive_failures"] == 3
        assert res3["circuit_open"]  # Circuit is now open!

        # Success resets failure counter and closes circuit
        res_ok = record_source_success(conn, "br.ipca.monthly")
        assert res_ok["consecutive_failures"] == 0
        assert not res_ok["circuit_open"]
        assert res_ok["last_successful_at"] is not None

        # Replay outbox execution
        conn.execute("INSERT INTO outbox (id, event_type, payload, status) VALUES (%s, %s, %s, 'processed')",
                     ("11111111-1111-1111-1111-111111111111", "EconomicIndicatorUpdated", '{"indicator_id": "br.ipca.monthly"}'))
        replay_res = execute_outbox_replay(conn, reason="Auditoria e reprocessamento operacional")
        assert replay_res["status"] == "completed"
        assert replay_res["events_replayed_count"] == 1

        # Outbox item status returned to pending
        outbox_row = conn.execute("SELECT status FROM outbox WHERE id='11111111-1111-1111-1111-111111111111'").fetchone()
        assert outbox_row[0] == "pending"

        # Check outbox_replay_audit
        audit_row = conn.execute("SELECT reason, status FROM outbox_replay_audit WHERE id=%s", (replay_res["replay_id"],)).fetchone()
        assert audit_row[0] == "Auditoria e reprocessamento operacional"
        assert audit_row[1] == "completed"
