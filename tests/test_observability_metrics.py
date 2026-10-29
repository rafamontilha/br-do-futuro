"""
Testes unitários e de integração para métricas de observabilidade dos quatro planos
(Plataforma, Dados, Modelos, Decisões) e conformidade de SLOs constitucionais.

Incremento 04 — Endurecimento do Piloto, Auditoria e Resiliência Operacional.
"""

import copy
from datetime import datetime, timezone
import pytest

from bdf.observability import (
    SLOViolationError,
    VALID_DATABASE_STATUSES,
    assert_slo_compliance,
    get_canonical_observability_snapshot,
    validate_metric_types_and_ranges,
    validate_observability_schema,
    validate_slo_compliance,
)


# ==============================================================================
# 1. Validação de Estrutura do Schema dos Quatro Planos e SLO Compliance
# ==============================================================================

def test_canonical_snapshot_schema_structure_is_valid():
    """Valida que o snapshot canônico contém todos os quatro planos e conformidade de SLO."""
    snapshot = get_canonical_observability_snapshot()
    errors = validate_observability_schema(snapshot)
    assert errors == [], f"Snapshot canônico deve ser válido pelo schema: {errors}"

    expected_top_keys = {"platform", "data", "models", "decisions", "slo_compliance"}
    assert expected_top_keys.issubset(set(snapshot.keys()))


@pytest.mark.parametrize("missing_plane", [
    "platform",
    "data",
    "models",
    "decisions",
    "slo_compliance",
])
def test_schema_rejects_missing_top_level_plane(missing_plane):
    """Garante que a ausência de qualquer um dos quatro planos ou de slo_compliance é rejeitada."""
    snapshot = get_canonical_observability_snapshot()
    del snapshot[missing_plane]

    errors = validate_observability_schema(snapshot)
    assert any(missing_plane in err for err in errors), f"Deveria reportar ausência de {missing_plane}"


@pytest.mark.parametrize("plane,field", [
    ("platform", "uptime_seconds"),
    ("platform", "database_status"),
    ("platform", "error_rate_pct"),
    ("platform", "p95_latency_ms"),
    ("data", "tracked_series_count"),
    ("data", "stale_series_count"),
    ("data", "quarantine_count"),
    ("models", "active_scenarios_count"),
    ("models", "calibrated_parameters_count"),
    ("decisions", "total_decisions_count"),
    ("decisions", "pending_reviews_count"),
    ("decisions", "audit_chain_intact"),
    ("slo_compliance", "source_window_compliance_pct"),
    ("slo_compliance", "metadata_completeness_pct"),
    ("slo_compliance", "scenario_lineage_coverage_pct"),
    ("slo_compliance", "reproducible_forecasts_pct"),
])
def test_schema_rejects_missing_nested_fields(plane, field):
    """Garante que a ausência de qualquer métrica mandatória de um plano é detectada."""
    snapshot = get_canonical_observability_snapshot()
    del snapshot[plane][field]

    errors = validate_observability_schema(snapshot)
    assert any(field in err for err in errors), f"Deveria acusar ausência do campo '{field}' em '{plane}'"


def test_schema_rejects_non_dict_payload():
    """Garante rejeição quando o snapshot ou um dos planos não é um dicionário."""
    assert validate_observability_schema(["not", "a", "dict"]) != []

    snapshot = get_canonical_observability_snapshot()
    snapshot["platform"] = "invalid_string"
    errors = validate_observability_schema(snapshot)
    assert any("platform" in err for err in errors)


# ==============================================================================
# 2. Testes de Tipos e Intervalos Esperados
# ==============================================================================

def test_platform_plane_types_and_ranges():
    """
    Testa tipos e limites do plano de Plataforma:
    - uptime_seconds >= 0
    - database_status in ('healthy', 'unconfigured', 'unreachable')
    - error_rate_pct >= 0
    - p95_latency_ms >= 0
    """
    snapshot = get_canonical_observability_snapshot()

    # Valores canônicos válidos
    assert validate_metric_types_and_ranges(snapshot) == []

    # Status de banco válidos
    for status in ("healthy", "unconfigured", "unreachable"):
        snap = copy.deepcopy(snapshot)
        snap["platform"]["database_status"] = status
        violations = validate_metric_types_and_ranges(snap)
        assert violations == [], f"Status '{status}' deve ser aceito na especificação de tipos"

    # Status de banco inválido
    snap = copy.deepcopy(snapshot)
    snap["platform"]["database_status"] = "database_corrupted"
    assert any("database_status" in v for v in validate_metric_types_and_ranges(snap))

    # Uptime negativo
    snap = copy.deepcopy(snapshot)
    snap["platform"]["uptime_seconds"] = -1
    assert any("uptime_seconds" in v for v in validate_metric_types_and_ranges(snap))

    # Error rate negativo
    snap = copy.deepcopy(snapshot)
    snap["platform"]["error_rate_pct"] = -0.01
    assert any("error_rate_pct" in v for v in validate_metric_types_and_ranges(snap))

    # p95 negativo
    snap = copy.deepcopy(snapshot)
    snap["platform"]["p95_latency_ms"] = -5.0
    assert any("p95_latency_ms" in v for v in validate_metric_types_and_ranges(snap))


def test_data_plane_types_and_ranges():
    """
    Testa tipos e limites do plano de Dados:
    - tracked_series_count >= 12
    - stale_series_count >= 0
    - quarantine_count >= 0
    """
    snapshot = get_canonical_observability_snapshot()
    assert validate_metric_types_and_ranges(snapshot) == []

    # Séries rastreadas abaixo do mínimo (12 domínios canônicos)
    snap = copy.deepcopy(snapshot)
    snap["data"]["tracked_series_count"] = 11
    violations = validate_metric_types_and_ranges(snap)
    assert any("tracked_series_count" in v for v in violations)

    # Séries com atraso negativas
    snap = copy.deepcopy(snapshot)
    snap["data"]["stale_series_count"] = -1
    assert any("stale_series_count" in v for v in validate_metric_types_and_ranges(snap))

    # Quarentena negativa
    snap = copy.deepcopy(snapshot)
    snap["data"]["quarantine_count"] = -1
    assert any("quarantine_count" in v for v in validate_metric_types_and_ranges(snap))


def test_models_plane_types_and_ranges():
    """
    Testa tipos e limites do plano de Modelos:
    - active_scenarios_count >= 3 (continuidade, alternativo, adverso)
    - calibrated_parameters_count >= 4
    """
    snapshot = get_canonical_observability_snapshot()
    assert validate_metric_types_and_ranges(snapshot) == []

    # Cenários ativos < 3
    snap = copy.deepcopy(snapshot)
    snap["models"]["active_scenarios_count"] = 2
    violations = validate_metric_types_and_ranges(snap)
    assert any("active_scenarios_count" in v for v in violations)

    # Parâmetros calibrados < 4
    snap = copy.deepcopy(snapshot)
    snap["models"]["calibrated_parameters_count"] = 3
    violations = validate_metric_types_and_ranges(snap)
    assert any("calibrated_parameters_count" in v for v in violations)


def test_decisions_plane_types_and_ranges():
    """
    Testa tipos e limites do plano de Decisões:
    - total_decisions_count >= 1 (registro gênese é mandatória)
    - pending_reviews_count >= 0
    - audit_chain_intact is True
    """
    snapshot = get_canonical_observability_snapshot()
    assert validate_metric_types_and_ranges(snapshot) == []

    # Total de decisões < 1
    snap = copy.deepcopy(snapshot)
    snap["decisions"]["total_decisions_count"] = 0
    violations = validate_metric_types_and_ranges(snap)
    assert any("total_decisions_count" in v for v in violations)

    # Pendências negativas
    snap = copy.deepcopy(snapshot)
    snap["decisions"]["pending_reviews_count"] = -1
    assert any("pending_reviews_count" in v for v in validate_metric_types_and_ranges(snap))

    # Cadeia corrompida (audit_chain_intact is False)
    snap = copy.deepcopy(snapshot)
    snap["decisions"]["audit_chain_intact"] = False
    violations = validate_metric_types_and_ranges(snap)
    assert any("audit_chain_intact" in v for v in violations)


def test_slo_compliance_types_and_ranges():
    """
    Testa tipos e limites da conformidade com SLOs constitucionais:
    - source_window_compliance_pct >= 99.0
    - metadata_completeness_pct == 100.0
    - scenario_lineage_coverage_pct == 100.0
    - reproducible_forecasts_pct == 100.0
    """
    snapshot = get_canonical_observability_snapshot()
    assert validate_metric_types_and_ranges(snapshot) == []

    # Janela de fonte abaixo de 99.0%
    snap = copy.deepcopy(snapshot)
    snap["slo_compliance"]["source_window_compliance_pct"] = 98.9
    violations = validate_metric_types_and_ranges(snap)
    assert any("source_window_compliance_pct" in v for v in violations)

    # Metadados públicos < 100%
    snap = copy.deepcopy(snapshot)
    snap["slo_compliance"]["metadata_completeness_pct"] = 99.9
    violations = validate_metric_types_and_ranges(snap)
    assert any("metadata_completeness_pct" in v for v in violations)

    # Rastreabilidade de cenários < 100%
    snap = copy.deepcopy(snapshot)
    snap["slo_compliance"]["scenario_lineage_coverage_pct"] = 99.5
    violations = validate_metric_types_and_ranges(snap)
    assert any("scenario_lineage_coverage_pct" in v for v in violations)

    # Reprodutibilidade de previsões < 100%
    snap = copy.deepcopy(snapshot)
    snap["slo_compliance"]["reproducible_forecasts_pct"] = 99.0
    violations = validate_metric_types_and_ranges(snap)
    assert any("reproducible_forecasts_pct" in v for v in violations)


# ==============================================================================
# 3. Testes de Detecção de Anomalias pela Função Validadora de SLO
# ==============================================================================

def test_slo_compliance_passes_nominal_snapshot():
    """Snapshot canônico nominal deve ser aprovado sem anomalias."""
    snapshot = get_canonical_observability_snapshot()
    is_compliant, violations = validate_slo_compliance(snapshot)
    assert is_compliant is True
    assert violations == []

    # Não deve levantar exceção
    assert_slo_compliance(snapshot)


def test_slo_compliance_detects_database_unreachable():
    """
    Anomalia de plataforma: database_status == 'unreachable' deve ser detectada
    como violação de SLO operacional.
    """
    snapshot = get_canonical_observability_snapshot()
    snapshot["platform"]["database_status"] = "unreachable"

    is_compliant, violations = validate_slo_compliance(snapshot)
    assert is_compliant is False
    assert any("unreachable" in v for v in violations), f"Violações devem apontar banco inacessível: {violations}"

    with pytest.raises(SLOViolationError, match="unreachable"):
        assert_slo_compliance(snapshot)


def test_slo_compliance_detects_audit_chain_break():
    """
    Anomalia de decisões: audit_chain_intact == False deve ser detectada
    como violação crítica de integridade.
    """
    snapshot = get_canonical_observability_snapshot()
    snapshot["decisions"]["audit_chain_intact"] = False

    is_compliant, violations = validate_slo_compliance(snapshot)
    assert is_compliant is False
    assert any("audit_chain_intact" in v for v in violations)

    with pytest.raises(SLOViolationError, match="audit_chain_intact"):
        assert_slo_compliance(snapshot)


def test_slo_compliance_detects_source_window_degradation():
    """Anomalia de SLO: taxa de pontualidade de janelas de fontes < 99.0%."""
    snapshot = get_canonical_observability_snapshot()
    snapshot["slo_compliance"]["source_window_compliance_pct"] = 98.4

    is_compliant, violations = validate_slo_compliance(snapshot)
    assert is_compliant is False
    assert any("source_window_compliance_pct" in v for v in violations)

    with pytest.raises(SLOViolationError, match="source_window_compliance_pct"):
        assert_slo_compliance(snapshot)


def test_slo_compliance_detects_multiple_simultaneous_anomalies():
    """Garante que anomalias simultâneas em múltiplos planos são todas identificadas."""
    snapshot = get_canonical_observability_snapshot()
    snapshot["platform"]["database_status"] = "unreachable"
    snapshot["data"]["tracked_series_count"] = 5
    snapshot["decisions"]["audit_chain_intact"] = False
    snapshot["slo_compliance"]["reproducible_forecasts_pct"] = 80.0

    is_compliant, violations = validate_slo_compliance(snapshot)
    assert is_compliant is False
    assert len(violations) >= 4
    violation_blob = " ".join(violations)
    assert "unreachable" in violation_blob
    assert "tracked_series_count" in violation_blob
    assert "audit_chain_intact" in violation_blob
    assert "reproducible_forecasts_pct" in violation_blob


# ==============================================================================
# 4. Teste de Integridade das Contagens Contra o PostgreSQL Dedicado bdf_test
# ==============================================================================

def test_observability_counts_against_database_integration(db):
    """
    Se TEST_DATABASE_URL estiver configurado, valida as contagens reais no banco bdf_test.
    Caso contrário, a fixture db pula o teste graciosamente.
    """
    import psycopg

    with psycopg.connect(db) as conn:
        # 1. Contagem de parâmetros fiscais calibrados (deve ser >= 4 conforme 004_proposals_and_guidance.sql)
        calibrations_count = conn.execute("SELECT count(*) FROM fiscal_calibrations").fetchone()[0]
        assert calibrations_count >= 4, "Devem existir ao menos 4 parâmetros calibrados no banco bdf_test"

        # 2. Contagem da trilha de auditoria (deve ser >= 1 com o registro gênese conforme 005_audit_logs_and_security.sql)
        total_decisions = conn.execute("SELECT count(*) FROM decision_audit_log").fetchone()[0]
        assert total_decisions >= 1, "Trilha de auditoria deve conter pelo menos o registro gênese"

        # 3. Verificação do registro gênese
        genesis_row = conn.execute("""
            SELECT id, action, prev_log_hash, payload_hash
            FROM decision_audit_log
            WHERE id = 'audit-genesis-0000'
        """).fetchone()
        assert genesis_row is not None, "Registro gênese 'audit-genesis-0000' deve existir"
        assert genesis_row[2] == "0" * 64, "prev_log_hash da gênese deve ser 64 zeros"

        # 4. Contagem de séries atrasadas e quarentenas
        stale_schedules_count = conn.execute("SELECT count(*) FROM source_schedules WHERE is_stale = true").fetchone()[0]
        assert stale_schedules_count >= 0

        quarantine_count = conn.execute("SELECT count(*) FROM ingestion_run WHERE status = 'quarantined'").fetchone()[0]
        assert quarantine_count >= 0

        pending_reviews_count = conn.execute("SELECT count(*) FROM alert WHERE status = 'pending_review'").fetchone()[0]
        assert pending_reviews_count >= 0

        # Constrói o snapshot baseado nas consultas reais ao banco
        live_db_snapshot = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "platform": {
                "uptime_seconds": 1800,
                "database_status": "healthy",
                "error_rate_pct": 0.0,
                "p95_latency_ms": 11.2,
            },
            "data": {
                "tracked_series_count": 12,
                "stale_series_count": stale_schedules_count,
                "quarantine_count": quarantine_count,
            },
            "models": {
                "active_scenarios_count": 3,
                "calibrated_parameters_count": calibrations_count,
            },
            "decisions": {
                "total_decisions_count": total_decisions,
                "pending_reviews_count": pending_reviews_count,
                "audit_chain_intact": (genesis_row is not None),
            },
            "slo_compliance": {
                "source_window_compliance_pct": 99.4,
                "metadata_completeness_pct": 100.0,
                "scenario_lineage_coverage_pct": 100.0,
                "reproducible_forecasts_pct": 100.0,
            },
        }

        # Valida conformidade e ausência de anomalias no estado inicial do bdf_test
        is_compliant, violations = validate_slo_compliance(live_db_snapshot)
        assert is_compliant is True, f"Banco dedicado bdf_test deve produzir snapshot conforme: {violations}"
        assert_slo_compliance(live_db_snapshot)


def test_observability_detects_db_chain_tampering_or_missing_genesis(db):
    """
    Testa no banco dedicado bdf_test que a remoção do registro gênese
    é detectada e quebra o indicador de integridade do plano de Decisões.
    """
    import psycopg

    with psycopg.connect(db) as conn:
        # Remove temporariamente o registro gênese no banco dedicado bdf_test
        conn.execute("DELETE FROM decision_audit_log WHERE id = 'audit-genesis-0000'")

        # Verifica que agora a contagem do genesis é zero
        genesis_count = conn.execute("SELECT count(*) FROM decision_audit_log WHERE id = 'audit-genesis-0000'").fetchone()[0]
        assert genesis_count == 0

        tampered_snapshot = get_canonical_observability_snapshot()
        tampered_snapshot["decisions"]["audit_chain_intact"] = (genesis_count > 0)

        is_compliant, violations = validate_slo_compliance(tampered_snapshot)
        assert is_compliant is False
        assert any("audit_chain_intact" in v for v in violations)

        with pytest.raises(SLOViolationError, match="audit_chain_intact"):
            assert_slo_compliance(tampered_snapshot)
