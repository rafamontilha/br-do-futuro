import argparse
import json
import logging
import os
from datetime import date, datetime
from pathlib import Path

import psycopg
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import ConsoleSpanExporter, SimpleSpanProcessor

from .catalog import INDICATORS, catalog
from .pipeline import ingest
from .worker import drain


def main():
    parser = argparse.ArgumentParser(description="Brasil do Futuro — foundation pilot")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("migrate")
    sub.add_parser("catalog")
    sub.add_parser("worker")
    fixture = sub.add_parser("ingest")
    fixture.add_argument("indicator", choices=INDICATORS)
    fixture.add_argument("file", type=Path)
    fetch = sub.add_parser("fetch")
    fetch.add_argument("indicator", choices=INDICATORS)
    fetch.add_argument("--start", required=True, type=date.fromisoformat)
    fetch.add_argument("--end", required=True, type=date.fromisoformat)
    fetch.add_argument("--source", choices=["ibge", "bcb"], default=None)
    replay = sub.add_parser("replay")
    replay.add_argument("--reason", required=True)
    replay.add_argument("--indicator", choices=INDICATORS, default=None)
    replay.add_argument("--event-type", default=None)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    provider = TracerProvider()
    if os.getenv("BDF_TRACE_CONSOLE") == "1":
        provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))
    trace.set_tracer_provider(provider)
    if args.command == "catalog":
        print(json.dumps(catalog(), ensure_ascii=False, indent=2))
        return
    dsn = os.environ["DATABASE_URL"]
    if args.command == "migrate":
        with psycopg.connect(dsn) as conn:
            for migration in sorted(Path("db").glob("*.sql")):
                conn.execute(migration.read_text())
    elif args.command == "worker":
        print(json.dumps(drain(dsn)))
    elif args.command == "ingest":
        result = ingest(dsn, args.indicator, args.file.read_bytes(), "fixture:" + args.file.name)
        print(json.dumps(result))
        if result["status"] == "quarantined":
            raise SystemExit(2)
    elif args.command == "replay":
        from .freshness import execute_outbox_replay
        with psycopg.connect(dsn) as conn:
            result = execute_outbox_replay(
                conn,
                reason=args.reason,
                triggered_by="cli-operator",
                filter_indicator_id=args.indicator,
                filter_event_type=args.event_type,
            )
            print(json.dumps(result))
    elif args.command == "fetch":
        if args.start > args.end or (args.end - args.start).days > 3650 or args.end > date.today():
            parser.error("Use a past interval no longer than 3650 days; split larger histories")
        session = requests.Session()
        session.mount("https://", HTTPAdapter(max_retries=Retry(total=3, backoff_factor=1,
                      status_forcelist=[429, 500, 502, 503, 504], allowed_methods=["GET"])))
        use_ibge = (args.source == "ibge") or (args.indicator == "br.ipca.monthly" and args.source != "bcb")
        if use_ibge and args.indicator == "br.ipca.monthly":
            from .sources.ibge import fetch_ipca
            # Calculate periods format for SIDRA (YYYYMM-YYYYMM)
            start_p = args.start.strftime("%Y%m")
            end_p = args.end.strftime("%Y%m")
            period_arg = f"{start_p}-{end_p}" if start_p != end_p else start_p
            try:
                content, url = fetch_ipca(periods=period_arg, session=session)
            except requests.RequestException:
                logging.error(json.dumps(dict(event="source_unavailable", indicator_id=args.indicator,
                                              source="IBGE_SIDRA", checked_at=datetime.now().astimezone().isoformat())))
                raise SystemExit(1)
            result = ingest(dsn, args.indicator, content, url, mode="source")
        else:
            uri = INDICATORS[args.indicator]["source_uri"]
            try:
                response = session.get(uri, params=dict(formato="json", dataInicial=args.start.strftime("%d/%m/%Y"),
                                       dataFinal=args.end.strftime("%d/%m/%Y")), timeout=(10, 60))
                response.raise_for_status()
            except requests.RequestException:
                logging.error(json.dumps(dict(event="source_unavailable", indicator_id=args.indicator,
                                              source="BCB_SGS", checked_at=datetime.now().astimezone().isoformat())))
                raise SystemExit(1)
            result = ingest(dsn, args.indicator, response.content, response.url, mode="source")
        print(json.dumps(result))
        if result["status"] == "quarantined":
            raise SystemExit(2)


if __name__ == "__main__":
    main()
