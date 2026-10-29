"""Append-only captures and per-period revisions, committed with an outbox."""
import hashlib
import json
import logging
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from uuid import uuid4

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb
from opentelemetry import trace

from .catalog import INDICATORS

LOG = logging.getLogger(__name__)
TRACER = trace.get_tracer("brasil-do-futuro.ingestion")


def validate(body, indicator):
    try:
        rows = json.loads(body)
    except Exception as exc:
        raise ValueError("Invalid JSON payload") from exc
    if not isinstance(rows, list) or not rows:
        raise ValueError("Expected a non-empty array")

    # If first element has D2C or resultados, it is an IBGE response (SIDRA or Agregados)
    if isinstance(rows[0], dict) and ("D2C" in rows[0] or "resultados" in rows[0]):
        from .sources.ibge import parse_ibge_ipca
        return parse_ibge_ipca(body)

    result, seen = [], set()
    for row in rows:
        if not isinstance(row, dict) or set(row) != {"data", "valor"}:
            raise ValueError("Unexpected SGS schema")
        day = datetime.strptime(row["data"], "%d/%m/%Y").date()
        if day > datetime.now(timezone.utc).date():
            raise ValueError("Future observation is not an actual")
        if indicator["frequency"] == "monthly" and day.day != 1:
            raise ValueError("Monthly reference must start on day 1")
        if day in seen:
            raise ValueError("Duplicate reference period")
        if not isinstance(row["valor"], str):
            raise ValueError("SGS values must be strings")
        value = Decimal(row["valor"])
        if not value.is_finite():
            raise ValueError("Non-finite observation")
        seen.add(day)
        result.append((day, value))
    return sorted(result)


def ingest(dsn, indicator_id, body, source_uri, mode="fixture", published_at=None):
    if mode not in ("fixture", "source"):
        raise ValueError("Unknown data mode")
    indicator = INDICATORS[indicator_id]
    now = datetime.now(timezone.utc)
    # SGS reference date is NOT a publication timestamp. Never infer publication.
    if published_at is not None:
        if published_at.tzinfo is None or published_at > now:
            raise ValueError("Publication timestamp must be timezone-aware and not in the future")
    digest = hashlib.sha256(body).hexdigest()
    run_id, vintage_id = uuid4(), uuid4()
    error = None
    try:
        rows = validate(body, indicator)
    except (ValueError, TypeError, KeyError, InvalidOperation, UnicodeDecodeError) as exc:
        rows, error = [], str(exc)
    with TRACER.start_as_current_span("ingest") as span:
        span.set_attribute("indicator.id", indicator_id)
        span.set_attribute("correlation.id", str(run_id))
        with psycopg.connect(dsn, row_factory=dict_row) as conn:
            # Serialize ingestion per series+mode, including concurrent first captures.
            conn.execute("SELECT pg_advisory_xact_lock(hashtextextended(%s,0))", (indicator_id + mode,))
            conn.execute("INSERT INTO raw_capture(id,body) VALUES (%s,%s) ON CONFLICT DO NOTHING", (digest, body))
            changes = []
            for day, value in rows:
                old = conn.execute("""SELECT o.* FROM observation o JOIN vintage v ON v.id=o.vintage_id
                    WHERE indicator_id=%s AND reference_period=%s AND mode=%s
                    ORDER BY v.known_at DESC LIMIT 1""", (indicator_id, day, mode)).fetchone()
                if old is None or old["value"] != value:
                    changes.append((day, value, old))
            status = "quarantined" if error else ("accepted" if changes else "unchanged")
            conn.execute("""INSERT INTO ingestion_run VALUES (%s,%s,%s,%s,%s,%s,%s,%s)""",
                         (run_id, indicator_id, now, source_uri, digest, mode, status, error))
            if changes:
                methodology_ver = indicator["methodology_version"]
                if "ibge" in source_uri.lower() or "sidra" in source_uri.lower():
                    methodology_ver = "ibge-sidra-contract-v1"
                conn.execute("""INSERT INTO vintage(id,run_id,published_at,methodology_version,quality_status)
                    VALUES (%s,%s,%s,%s,%s)""", (vintage_id, run_id, published_at,
                    methodology_ver, "synthetic" if mode == "fixture" else "provisional"))
            for day, value, old in changes:
                obs_id, event_id = uuid4(), uuid4()
                conn.execute("INSERT INTO observation VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
                    (obs_id, indicator_id, day, value, indicator["unit"], vintage_id, old["id"] if old else None, mode))
                payload = dict(event_id=str(event_id), event_version=1, indicator_id=indicator_id,
                    reference_period=day.isoformat(), vintage_id=str(vintage_id), observation_id=str(obs_id),
                    source_hash=digest, provenance_ref=str(run_id), correlation_id=str(run_id), mode=mode)
                event_type = "HistoricalSeriesRevised" if old else "EconomicIndicatorUpdated"
                conn.execute("INSERT INTO outbox(id,event_type,payload) VALUES (%s,%s,%s)",
                             (event_id, event_type, Jsonb(payload)))
            if error:
                event_id = uuid4()
                conn.execute("INSERT INTO outbox(id,event_type,payload) VALUES (%s,%s,%s)",
                    (event_id, "DataQualityFailed", Jsonb(dict(event_version=1, indicator_id=indicator_id,
                     correlation_id=str(run_id), source_hash=digest, mode=mode, reason=error))))
        result = dict(run_id=str(run_id), status=status, changes=len(changes), source_hash=digest, error=error)
        LOG.info(json.dumps(dict(event="ingestion_finished", **result)))
        return result


def observations(dsn, indicator_id, as_of=None, mode="fixture"):
    # Knowledge-time filtering prevents a current capture from leaking into past backtests.
    with psycopg.connect(dsn, row_factory=dict_row) as conn:
        return conn.execute("""SELECT DISTINCT ON (o.reference_period) o.*,v.known_at,v.published_at,
            v.quality_status FROM observation o JOIN vintage v ON o.vintage_id=v.id
            WHERE o.indicator_id=%s AND o.mode=%s AND v.known_at <= COALESCE(%s,clock_timestamp())
            ORDER BY o.reference_period,v.known_at DESC""", (indicator_id, mode, as_of)).fetchall()
