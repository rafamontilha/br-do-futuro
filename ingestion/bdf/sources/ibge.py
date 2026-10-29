"""IBGE SIDRA and Agregados API connector for IPCA."""
import json
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

SIDRA_BASE_URL = "https://apisidra.ibge.gov.br/values/t/1737/v/2265"
AGREGADOS_BASE_URL = "https://servicodados.ibge.gov.br/api/v3/agregados/1737"


class IBGEContractError(ValueError):
    """Raised when an IBGE payload violates the data contract."""
    pass


def parse_ibge_sidra(body: bytes | str, frequency: str = "monthly") -> list[tuple[date, Decimal]]:
    """Parse and validate observations from IBGE SIDRA or Agregados API.

    frequency can be 'monthly' (YYYYMM) or 'quarterly' (YYYY0Q).
    Returns a sorted list of (reference_period, Decimal(value)) tuples where
    reference_period is date(YYYY, MM, 1).
    """
    if isinstance(body, bytes):
        try:
            raw_text = body.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise IBGEContractError("Invalid UTF-8 payload from IBGE") from exc
    else:
        raw_text = body

    try:
        data = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise IBGEContractError("Invalid JSON from IBGE") from exc

    if not isinstance(data, list) or not data:
        raise IBGEContractError("Expected non-empty array from IBGE")

    now_date = datetime.now(timezone.utc).date()
    results: list[tuple[date, Decimal]] = []
    seen_periods: set[date] = set()

    # Case A: SIDRA Values endpoint (data[0] is header metadata with keys "NC", "V", "D2C", etc.)
    if isinstance(data[0], dict) and "D2C" in data[0] and "V" in data[0]:
        rows = data[1:]  # skip header row
        if not rows:
            raise IBGEContractError("SIDRA table has no data rows")

        for row in rows:
            if not isinstance(row, dict):
                raise IBGEContractError("Malformed SIDRA row")
            period_code = row.get("D2C")  # e.g. "202501"
            val_str = row.get("V")

            if not period_code or len(period_code) != 6 or not period_code.isdigit():
                raise IBGEContractError(f"Invalid SIDRA period format: {period_code}")

            year = int(period_code[:4])
            code_suffix = int(period_code[4:6])

            if frequency == "quarterly":
                if code_suffix < 1 or code_suffix > 4:
                    raise IBGEContractError(f"Invalid quarter in period: {period_code}")
                month = (code_suffix - 1) * 3 + 1
            else:
                month = code_suffix
                if month < 1 or month > 12:
                    raise IBGEContractError(f"Invalid month in period: {period_code}")

            day = date(year, month, 1)
            if day > now_date:
                raise IBGEContractError("Future observation is not an actual")

            if day in seen_periods:
                raise IBGEContractError(f"Duplicate reference period: {day}")

            if val_str in ("...", "-", None):
                raise IBGEContractError(f"Missing or withheld observation for {day}")

            try:
                val = Decimal(str(val_str))
            except (InvalidOperation, TypeError) as exc:
                raise IBGEContractError(f"Invalid numeric value in SIDRA: {val_str}") from exc

            if not val.is_finite():
                raise IBGEContractError("Non-finite observation")

            seen_periods.add(day)
            results.append((day, val))

    # Case B: ServicoDados Agregados v3 endpoint
    elif isinstance(data[0], dict) and "resultados" in data[0]:
        try:
            resultados = data[0]["resultados"]
            if not resultados or "series" not in resultados[0] or not resultados[0]["series"]:
                raise IBGEContractError("Agregados structure missing series")
            serie = resultados[0]["series"][0].get("serie", {})
        except (KeyError, IndexError, TypeError) as exc:
            raise IBGEContractError("Unexpected Agregados schema") from exc

        if not serie:
            raise IBGEContractError("No observations found in Agregados series")

        for period_code, val_str in serie.items():
            if not period_code or len(period_code) != 6 or not period_code.isdigit():
                raise IBGEContractError(f"Invalid Agregados period: {period_code}")

            year = int(period_code[:4])
            code_suffix = int(period_code[4:6])

            if frequency == "quarterly":
                if code_suffix < 1 or code_suffix > 4:
                    raise IBGEContractError(f"Invalid quarter in period: {period_code}")
                month = (code_suffix - 1) * 3 + 1
            else:
                month = code_suffix
                if month < 1 or month > 12:
                    raise IBGEContractError(f"Invalid month in period: {period_code}")

            day = date(year, month, 1)
            if day > now_date:
                raise IBGEContractError("Future observation is not an actual")

            if day in seen_periods:
                raise IBGEContractError(f"Duplicate reference period: {day}")

            if val_str in ("...", "-", None):
                raise IBGEContractError(f"Missing observation for {day}")

            try:
                val = Decimal(str(val_str))
            except (InvalidOperation, TypeError) as exc:
                raise IBGEContractError(f"Invalid numeric value: {val_str}") from exc

            if not val.is_finite():
                raise IBGEContractError("Non-finite observation")

            seen_periods.add(day)
            results.append((day, val))
    else:
        raise IBGEContractError("Unrecognized IBGE response schema")

    return sorted(results)


def parse_ibge_ipca(body: bytes | str) -> list[tuple[date, Decimal]]:
    """Parse and validate IPCA observations from IBGE SIDRA or Agregados API."""
    return parse_ibge_sidra(body, frequency="monthly")


def fetch_ipca(periods: str = "last 12", session: requests.Session | None = None) -> tuple[bytes, str]:
    """Fetch IPCA monthly variations from IBGE SIDRA API."""
    if session is None:
        session = requests.Session()
        session.mount("https://", HTTPAdapter(max_retries=Retry(
            total=3, backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET"]
        )))

    url = f"{SIDRA_BASE_URL}/p/{periods}/n1/1"
    response = session.get(url, timeout=(10, 60))
    response.raise_for_status()
    return response.content, response.url


def fetch_sidra_gdp(periods: str = "last 4", session: requests.Session | None = None) -> tuple[bytes, str]:
    """Fetch quarterly GDP variations from IBGE SIDRA API (Table 5932)."""
    if session is None:
        session = requests.Session()
        session.mount("https://", HTTPAdapter(max_retries=Retry(
            total=3, backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET"]
        )))

    url = f"https://apisidra.ibge.gov.br/values/t/5932/v/6561/p/{periods}/c11255/90707/n1/1"
    response = session.get(url, timeout=(10, 60))
    response.raise_for_status()
    return response.content, response.url


def fetch_sidra_unemployment(periods: str = "last 4", session: requests.Session | None = None) -> tuple[bytes, str]:
    """Fetch unemployment rate from IBGE SIDRA API (PNAD Contínua Table 4099)."""
    if session is None:
        session = requests.Session()
        session.mount("https://", HTTPAdapter(max_retries=Retry(
            total=3, backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET"]
        )))

    url = f"https://apisidra.ibge.gov.br/values/t/4099/v/4099/p/{periods}/n1/1"
    response = session.get(url, timeout=(10, 60))
    response.raise_for_status()
    return response.content, response.url
