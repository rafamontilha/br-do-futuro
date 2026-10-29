"""
tests/test_audit_integrity.py

Testes unitários e de integração para validação da trilha imutável de auditoria
(decision_audit_log) e encadeamento criptográfico SHA-256 no Brasil do Futuro (Incremento 04).
"""

import hashlib
import json
from pathlib import Path
from typing import Any

import psycopg
import pytest

GENESIS_PREV_LOG_HASH = "0" * 64
GENESIS_PAYLOAD = {"status": "initialized", "version": "v1.4"}
GENESIS_PAYLOAD_HASH = "fa57e04f83fac28110ef3c82f4141d85eaf5858788cf7b6dbbc9f85ff91f0a9a"

ALLOWED_ACTOR_ROLES = frozenset({"producer", "reviewer", "publisher", "system"})
UNAUTHORIZED_ROLES = [
    "admin",
    "guest",
    "hacker",
    "root",
    "superuser",
    "anonymous",
    "audit_editor",
    "",
]


def compute_payload_hash(payload: Any) -> str:
    """Calcula deterministamente o hash SHA-256 de um payload canônico de auditoria."""
    canonical_json = json.dumps(payload, sort_keys=True)
    return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()


def validate_actor_role(role: str) -> bool:
    """Valida se o papel do ator está dentro dos papéis canônicos permitidos."""
    if not isinstance(role, str) or role not in ALLOWED_ACTOR_ROLES:
        raise ValueError(
            f"Unauthorized actor role '{role}'. Allowed roles: {sorted(ALLOWED_ACTOR_ROLES)}"
        )
    return True


def verify_audit_chain(records: list[dict[str, Any]], raise_on_error: bool = True) -> bool:
    """
    Valida a integridade da cadeia de auditoria de decisões.
    - Registro gênese (índice 0): prev_log_hash DEVE ser 64 zeros ('0' * 64).
    - Registros subsequentes (índice N): prev_log_hash DEVE ser igual a payload_hash do registro N-1.
    - Em cada registro: payload_hash DEVE corresponder a compute_payload_hash(new_state).
    - Em cada registro: actor_role DEVE ser um dos papéis permitidos.
    """
    if not records:
        return True

    for i, record in enumerate(records):
        # Validação do papel
        role = record.get("actor_role")
        if role not in ALLOWED_ACTOR_ROLES:
            msg = f"Record at index {i} ({record.get('id')}) has unauthorized actor_role: '{role}'"
            if raise_on_error:
                raise AssertionError(msg)
            return False

        # Validação de integridade do payload atual
        new_state = record.get("new_state")
        expected_payload_hash = compute_payload_hash(new_state)
        actual_payload_hash = record.get("payload_hash")
        if actual_payload_hash != expected_payload_hash:
            msg = (
                f"Payload hash mismatch at index {i} ({record.get('id')}): "
                f"expected {expected_payload_hash}, found {actual_payload_hash}"
            )
            if raise_on_error:
                raise AssertionError(msg)
            return False

        # Validação do encadeamento com o registro anterior
        actual_prev_hash = record.get("prev_log_hash")
        if i == 0:
            if actual_prev_hash != GENESIS_PREV_LOG_HASH:
                msg = (
                    f"Genesis record at index 0 must have prev_log_hash equal to 64 zeros, "
                    f"found {actual_prev_hash}"
                )
                if raise_on_error:
                    raise AssertionError(msg)
                return False
        else:
            expected_prev_hash = records[i - 1].get("payload_hash")
            if actual_prev_hash != expected_prev_hash:
                msg = (
                    f"Chain broken at index {i} ({record.get('id')}): "
                    f"prev_log_hash {actual_prev_hash} does not match predecessor payload_hash {expected_prev_hash}"
                )
                if raise_on_error:
                    raise AssertionError(msg)
                return False

    return True


# ==============================================================================
# 1. Testes de Cálculo Determinístico de SHA-256
# ==============================================================================

def test_deterministic_sha256_canonical_genesis_payload():
    """Valida que o cálculo de SHA-256 para o payload gênese produz o hash exato da migração 005."""
    computed = compute_payload_hash(GENESIS_PAYLOAD)
    assert computed == GENESIS_PAYLOAD_HASH
    assert len(computed) == 64
    assert all(c in "0123456789abcdef" for c in computed)


def test_sha256_key_order_invariance():
    """Valida que a ordenação de chaves garante determismo independente da ordem de inserção do dict."""
    payload_a = {"status": "calibrated", "parameter": "debt_anchor", "value": 75.5}
    payload_b = {"value": 75.5, "parameter": "debt_anchor", "status": "calibrated"}
    payload_c = {"parameter": "debt_anchor", "value": 75.5, "status": "calibrated"}

    hash_a = compute_payload_hash(payload_a)
    hash_b = compute_payload_hash(payload_b)
    hash_c = compute_payload_hash(payload_c)

    assert hash_a == hash_b == hash_c


def test_sha256_nested_structures_determinism():
    """Valida determinismo em payloads aninhados contendo tipos diversos (listas, floats, booleans, nulls)."""
    complex_payload = {
        "calibration_id": "calib-20261029-01",
        "parameters": {
            "interest_rate": 0.105,
            "primary_surplus_target": 0.015,
            "growth_rate": 0.022,
        },
        "flags": [True, False, True],
        "metadata": {
            "notes": "Parâmetros pós-revisão metodológica",
            "reviewer": "user-reviewer-01",
            "deprecated_field": None,
        },
    }

    hash1 = compute_payload_hash(complex_payload)
    hash2 = compute_payload_hash(complex_payload)
    assert hash1 == hash2

    # Pequena modificação em campo aninhado produz hash diferente (efeito avalanche)
    modified_payload = json.loads(json.dumps(complex_payload))
    modified_payload["parameters"]["interest_rate"] = 0.106
    hash_modified = compute_payload_hash(modified_payload)

    assert hash1 != hash_modified


def test_sha256_avalanche_effect():
    """Valida efeito avalanche: alteração mínima altera drasticamente o hash."""
    base = {"action": "approve_calibration", "entity_id": "calib-001"}
    tampered = {"action": "approve_calibration", "entity_id": "calib-002"}

    h_base = compute_payload_hash(base)
    h_tampered = compute_payload_hash(tampered)

    assert h_base != h_tampered
    # Não deve haver prefixo comum longo
    common_prefix_len = 0
    for a, b in zip(h_base, h_tampered):
        if a == b:
            common_prefix_len += 1
        else:
            break
    assert common_prefix_len < 10


# ==============================================================================
# 2. Testes de Validação da Cadeia de Hashes Encadeados
# ==============================================================================

def test_genesis_record_prev_log_hash_is_64_zeros():
    """Valida que o registro gênese possui prev_log_hash estritamente igual a 64 zeros."""
    assert GENESIS_PREV_LOG_HASH == "0" * 64
    assert len(GENESIS_PREV_LOG_HASH) == 64


def test_sequential_audit_chain_links():
    """Valida uma cadeia sequencial íntegra de múltiplos registros encadeados."""
    rec0 = {
        "id": "audit-genesis-0000",
        "actor_role": "system",
        "action": "initialize_audit_ledger",
        "new_state": GENESIS_PAYLOAD,
        "payload_hash": compute_payload_hash(GENESIS_PAYLOAD),
        "prev_log_hash": GENESIS_PREV_LOG_HASH,
    }

    state1 = {"status": "ingested", "series": "br.ipca.monthly", "vintage": "2026-10"}
    rec1 = {
        "id": "audit-dec-20261029-001",
        "actor_role": "producer",
        "action": "ingest_vintage",
        "new_state": state1,
        "payload_hash": compute_payload_hash(state1),
        "prev_log_hash": rec0["payload_hash"],
    }

    state2 = {"status": "approved", "calibration": "fiscal-2026-v2"}
    rec2 = {
        "id": "audit-dec-20261029-002",
        "actor_role": "reviewer",
        "action": "approve_calibration",
        "new_state": state2,
        "payload_hash": compute_payload_hash(state2),
        "prev_log_hash": rec1["payload_hash"],
    }

    state3 = {"status": "published", "guidance": "comm-debt-stabilization-2030"}
    rec3 = {
        "id": "audit-dec-20261029-003",
        "actor_role": "publisher",
        "action": "publish_guidance",
        "new_state": state3,
        "payload_hash": compute_payload_hash(state3),
        "prev_log_hash": rec2["payload_hash"],
    }

    chain = [rec0, rec1, rec2, rec3]

    # Verifica cada elo diretamente
    assert rec0["prev_log_hash"] == "0" * 64
    assert rec1["prev_log_hash"] == rec0["payload_hash"]
    assert rec2["prev_log_hash"] == rec1["payload_hash"]
    assert rec3["prev_log_hash"] == rec2["payload_hash"]

    # Validação completa da cadeia
    assert verify_audit_chain(chain, raise_on_error=True) is True
    assert verify_audit_chain(chain, raise_on_error=False) is True


# ==============================================================================
# 3. Testes de Detecção de Adulteração (Tampering)
# ==============================================================================

@pytest.fixture
def sample_valid_chain():
    """Fixture que retorna uma cópia de cadeia de 3 registros válida."""
    rec0 = {
        "id": "audit-genesis-0000",
        "actor_role": "system",
        "new_state": {"genesis": True},
        "payload_hash": compute_payload_hash({"genesis": True}),
        "prev_log_hash": GENESIS_PREV_LOG_HASH,
    }
    rec1 = {
        "id": "audit-001",
        "actor_role": "producer",
        "new_state": {"spending_approved_brl": 500_000_000},
        "payload_hash": compute_payload_hash({"spending_approved_brl": 500_000_000}),
        "prev_log_hash": rec0["payload_hash"],
    }
    rec2 = {
        "id": "audit-002",
        "actor_role": "reviewer",
        "new_state": {"reviewed": True},
        "payload_hash": compute_payload_hash({"reviewed": True}),
        "prev_log_hash": rec1["payload_hash"],
    }
    return [rec0, rec1, rec2]


def test_tampering_retroactive_payload_modification_fails(sample_valid_chain):
    """Adulteração de payload intermediário (new_state) é detectada imediatamente."""
    chain = sample_valid_chain
    # Atacante altera retroativamente o valor de gasto aprovado sem conseguir falsificar o hash
    chain[1]["new_state"] = {"spending_approved_brl": 999_999_999}

    assert verify_audit_chain(chain, raise_on_error=False) is False
    with pytest.raises(AssertionError, match="Payload hash mismatch at index 1"):
        verify_audit_chain(chain, raise_on_error=True)


def test_tampering_payload_hash_altered_breaks_chain(sample_valid_chain):
    """Se o atacante recalcular o payload_hash do registro N, quebra o encadeamento no registro N+1."""
    chain = sample_valid_chain
    forged_state = {"spending_approved_brl": 999_999_999}
    chain[1]["new_state"] = forged_state
    chain[1]["payload_hash"] = compute_payload_hash(forged_state)  # atualizou o próprio hash

    # O registro 2 ainda aponta para o payload_hash anterior -> cadeia quebrada
    assert verify_audit_chain(chain, raise_on_error=False) is False
    with pytest.raises(AssertionError, match="Chain broken at index 2"):
        verify_audit_chain(chain, raise_on_error=True)


def test_tampering_prev_log_hash_modification_fails(sample_valid_chain):
    """Adulteração de prev_log_hash em registro subsequente falha a verificação."""
    chain = sample_valid_chain
    chain[2]["prev_log_hash"] = "deadbeef" * 8

    assert verify_audit_chain(chain, raise_on_error=False) is False
    with pytest.raises(AssertionError, match="Chain broken at index 2"):
        verify_audit_chain(chain, raise_on_error=True)


def test_tampering_genesis_prev_log_hash_fails(sample_valid_chain):
    """Adulteração de prev_log_hash no registro gênese falha a verificação."""
    chain = sample_valid_chain
    chain[0]["prev_log_hash"] = "1" * 64

    assert verify_audit_chain(chain, raise_on_error=False) is False
    with pytest.raises(AssertionError, match="Genesis record at index 0 must have prev_log_hash equal to 64 zeros"):
        verify_audit_chain(chain, raise_on_error=True)


def test_tampering_reordering_records_breaks_chain(sample_valid_chain):
    """Reordenação de registros quebra o encadeamento cronológico."""
    chain = [sample_valid_chain[0], sample_valid_chain[2], sample_valid_chain[1]]

    assert verify_audit_chain(chain, raise_on_error=False) is False
    with pytest.raises(AssertionError, match="Chain broken at index 1"):
        verify_audit_chain(chain, raise_on_error=True)


def test_tampering_deleting_intermediate_record_breaks_chain(sample_valid_chain):
    """Exclusão de registro intermediário quebra a continuidade da cadeia."""
    chain = [sample_valid_chain[0], sample_valid_chain[2]]

    assert verify_audit_chain(chain, raise_on_error=False) is False
    with pytest.raises(AssertionError, match="Chain broken at index 1"):
        verify_audit_chain(chain, raise_on_error=True)


# ==============================================================================
# 4. Testes de Papéis Permitidos e Rejeição de Não Autorizados
# ==============================================================================

@pytest.mark.parametrize("role", ["producer", "reviewer", "publisher", "system"])
def test_allowed_roles_accepted(role):
    """Valida que todos os papéis canônicos de governança são aceitos."""
    assert validate_actor_role(role) is True


@pytest.mark.parametrize("role", UNAUTHORIZED_ROLES)
def test_unauthorized_roles_rejected(role):
    """Valida que papéis não autorizados (ex: admin, guest, hacker) são estritamente rejeitados."""
    with pytest.raises(ValueError, match="Unauthorized actor role"):
        validate_actor_role(role)


def test_chain_with_unauthorized_role_rejected(sample_valid_chain):
    """Valida que registro com papel não autorizado reprova a cadeia de auditoria."""
    chain = sample_valid_chain
    chain[1]["actor_role"] = "hacker"

    assert verify_audit_chain(chain, raise_on_error=False) is False
    with pytest.raises(AssertionError, match="has unauthorized actor_role: 'hacker'"):
        verify_audit_chain(chain, raise_on_error=True)


def test_migration_005_sql_schema_enforces_roles():
    """Valida estaticamente que a migração 005_audit_logs_and_security.sql contém a restrição de papéis."""
    sql_path = Path("db/005_audit_logs_and_security.sql")
    assert sql_path.exists(), "db/005_audit_logs_and_security.sql must exist"
    content = sql_path.read_text(encoding="utf-8")

    # Verifica CHECK constraint na tabela decision_audit_log
    assert "CREATE TABLE IF NOT EXISTS decision_audit_log" in content
    assert "CHECK (actor_role IN ('producer', 'reviewer', 'publisher', 'system'))" in content

    # Verifica CHECK constraint na tabela system_api_keys
    assert "CREATE TABLE IF NOT EXISTS system_api_keys" in content
    assert "CHECK (role IN ('producer', 'reviewer', 'publisher'))" in content


# ==============================================================================
# 5. Testes de Integração com PostgreSQL (usando o fixture db de conftest.py)
# ==============================================================================

def test_database_genesis_record_exists_and_valid(db):
    """Valida que o registro gênese é inserido no banco com os valores canônicos exatos."""
    with psycopg.connect(db) as conn:
        row = conn.execute("""
            SELECT id, actor_id, actor_role, action, entity_type, entity_id,
                   new_state, payload_hash, prev_log_hash
            FROM decision_audit_log
            WHERE id = 'audit-genesis-0000'
        """).fetchone()

        assert row is not None, "Registro gênese 'audit-genesis-0000' deve existir no banco de dados"
        audit_id, actor_id, role, action, entity_type, entity_id, new_state, p_hash, prev_hash = row

        assert role == "system"
        assert action == "initialize_audit_ledger"
        assert prev_hash == GENESIS_PREV_LOG_HASH, "prev_log_hash do gênese deve ser 64 zeros"
        assert p_hash == GENESIS_PAYLOAD_HASH
        assert compute_payload_hash(new_state) == p_hash


def test_database_insert_chained_records_and_verify(db):
    """Testa a inserção sequencial de registros de auditoria no PostgreSQL e a verificação da cadeia."""
    with psycopg.connect(db) as conn:
        # Recupera o registro gênese
        genesis_hash = conn.execute("""
            SELECT payload_hash FROM decision_audit_log WHERE id = 'audit-genesis-0000'
        """).fetchone()[0]

        # Inserção do Registro 1: Produtor
        state1 = {"dataset": "ibge-ipca", "vintage_id": "vintage-202610", "records_count": 120}
        hash1 = compute_payload_hash(state1)
        conn.execute("""
            INSERT INTO decision_audit_log (
                id, actor_id, actor_role, action, entity_type, entity_id,
                justification, new_state, payload_hash, prev_log_hash
            ) VALUES (
                'audit-test-001', 'user-producer-01', 'producer', 'ingest_data',
                'vintage', 'vintage-202610', 'Ingestão periódica oficial de inflação',
                %s::jsonb, %s, %s
            )
        """, (json.dumps(state1), hash1, genesis_hash))

        # Inserção do Registro 2: Revisor
        state2 = {"target_proposal": "prop-tax-reform-neutrality", "calibrated_debt_anchor": 75.0}
        hash2 = compute_payload_hash(state2)
        conn.execute("""
            INSERT INTO decision_audit_log (
                id, actor_id, actor_role, action, entity_type, entity_id,
                justification, new_state, payload_hash, prev_log_hash
            ) VALUES (
                'audit-test-002', 'user-reviewer-01', 'reviewer', 'approve_calibration',
                'public_proposal', 'prop-tax-reform-neutrality', 'Homologação metodológica de âncora fiscal',
                %s::jsonb, %s, %s
            )
        """, (json.dumps(state2), hash2, hash1))

        # Inserção do Registro 3: Publicador
        state3 = {"commitment_id": "comm-debt-stabilization-2030", "status": "proposed_target"}
        hash3 = compute_payload_hash(state3)
        conn.execute("""
            INSERT INTO decision_audit_log (
                id, actor_id, actor_role, action, entity_type, entity_id,
                justification, new_state, payload_hash, prev_log_hash
            ) VALUES (
                'audit-test-003', 'user-publisher-01', 'publisher', 'publish_guidance',
                'guidance_commitment', 'comm-debt-stabilization-2030', 'Publicação de meta após duplo parecer',
                %s::jsonb, %s, %s
            )
        """, (json.dumps(state3), hash3, hash2))

        # Consulta e validação de todos os registros em ordem cronológica
        rows = conn.execute("""
            SELECT id, actor_role, new_state, payload_hash, prev_log_hash
            FROM decision_audit_log
            ORDER BY created_at ASC, id ASC
        """).fetchall()

        chain = [
            {
                "id": r[0],
                "actor_role": r[1],
                "new_state": r[2],
                "payload_hash": r[3],
                "prev_log_hash": r[4],
            }
            for r in rows
        ]

        assert len(chain) == 4
        assert verify_audit_chain(chain, raise_on_error=True) is True


def test_database_primary_key_uniqueness_enforced(db):
    """Valida que o PostgreSQL rejeita duplicidade de chave primária (id) na tabela decision_audit_log."""
    with psycopg.connect(db) as conn:
        state = {"test": "duplicate_key"}
        h = compute_payload_hash(state)

        # Tentativa de reinserir o id 'audit-genesis-0000'
        with pytest.raises(psycopg.errors.UniqueViolation):
            conn.execute("""
                INSERT INTO decision_audit_log (
                    id, actor_id, actor_role, action, entity_type, entity_id,
                    justification, new_state, payload_hash, prev_log_hash
                ) VALUES (
                    'audit-genesis-0000', 'hacker', 'system', 'override_genesis',
                    'system', 'bdf-foundation', 'Ataque de sobrescrita de gênese',
                    %s::jsonb, %s, %s
                )
            """, (json.dumps(state), h, GENESIS_PREV_LOG_HASH))


def test_database_role_check_constraint_enforced(db):
    """Valida que o PostgreSQL rejeita papéis não autorizados via restrição CHECK."""
    with psycopg.connect(db) as conn:
        state = {"test": "invalid_role"}
        h = compute_payload_hash(state)

        for invalid_role in ["admin", "guest", "hacker"]:
            with pytest.raises(psycopg.errors.CheckViolation):
                conn.execute("""
                    INSERT INTO decision_audit_log (
                        id, actor_id, actor_role, action, entity_type, entity_id,
                        justification, new_state, payload_hash, prev_log_hash
                    ) VALUES (
                        %s, 'intruder', %s, 'unauthorized_action',
                        'system', 'sec-breach', 'Tentativa de burlar papéis',
                        %s::jsonb, %s, %s
                    )
                """, (f"audit-invalid-role-{invalid_role}", invalid_role, json.dumps(state), h, GENESIS_PREV_LOG_HASH))
            conn.rollback()
