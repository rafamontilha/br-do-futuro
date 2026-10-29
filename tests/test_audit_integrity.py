"""
tests/test_audit_integrity.py

Testes unitários e de integração para validação da trilha imutável de auditoria
(decision_audit_log) e encadeamento criptográfico SHA-256 no Brasil do Futuro (Incremento 04).
"""

import copy
import hashlib
import json
from pathlib import Path
from typing import Any

import psycopg
import pytest

GENESIS_PREV_LOG_HASH = "0" * 64
GENESIS_RECORD = {
    "action": "initialize_audit_ledger",
    "actor_id": "system-genesis",
    "actor_role": "system",
    "entity_id": "bdf-foundation",
    "entity_type": "system",
    "event_id": None,
    "id": "audit-genesis-0000",
    "justification": "Gênese da trilha imutável de auditoria de decisões do Brasil do Futuro (Incremento 04)",
    "new_state": {"status": "initialized", "version": "v1.4"},
    "prev_log_hash": GENESIS_PREV_LOG_HASH,
    "previous_state": None,
}
GENESIS_PAYLOAD_HASH = "af9fe7ed02660efdca8dfbcd16d0c9b300a92259e40671fd6b4ef18d7708975c"

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


def compute_payload_hash(record_or_payload: Any) -> str:
    """Calcula deterministamente o hash SHA-256 de um registro canônico completo ou payload de auditoria."""
    if isinstance(record_or_payload, dict) and "action" in record_or_payload and "actor_role" in record_or_payload:
        canonical = {
            "action": record_or_payload.get("action"),
            "actor_id": record_or_payload.get("actor_id"),
            "actor_role": record_or_payload.get("actor_role"),
            "entity_id": record_or_payload.get("entity_id"),
            "entity_type": record_or_payload.get("entity_type"),
            "event_id": record_or_payload.get("event_id"),
            "id": record_or_payload.get("id"),
            "justification": record_or_payload.get("justification"),
            "new_state": record_or_payload.get("new_state"),
            "prev_log_hash": record_or_payload.get("prev_log_hash"),
            "previous_state": record_or_payload.get("previous_state"),
        }
        canonical_json = json.dumps(canonical, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()

    canonical_json = json.dumps(record_or_payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()


def make_valid_record(
    id: str,
    actor_role: str,
    action: str,
    new_state: Any,
    prev_log_hash: str,
    actor_id: str = "actor-01",
    entity_type: str = "proposal",
    entity_id: str = "entity-01",
    justification: str = "Justificativa padrão",
    event_id: str | None = None,
    previous_state: Any = None,
) -> dict[str, Any]:
    """Constrói um registro canônico válido com o hash calculado sobre todos os campos."""
    rec = {
        "action": action,
        "actor_id": actor_id,
        "actor_role": actor_role,
        "entity_id": entity_id,
        "entity_type": entity_type,
        "event_id": event_id,
        "id": id,
        "justification": justification,
        "new_state": new_state,
        "prev_log_hash": prev_log_hash,
        "previous_state": previous_state,
    }
    rec["payload_hash"] = compute_payload_hash(rec)
    return rec


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
    - Em cada registro: payload_hash DEVE corresponder a compute_payload_hash(record).
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

        # Validação de integridade do registro completo
        expected_payload_hash = compute_payload_hash(record)
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
    """Valida que o cálculo de SHA-256 para o registro canônico gênese completo produz o hash exato da migração 005."""
    computed = compute_payload_hash(GENESIS_RECORD)
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

    # Modificação em campo aninhado produz hash diferente (efeito avalanche)
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
    rec0 = copy.deepcopy(GENESIS_RECORD)
    rec0["payload_hash"] = compute_payload_hash(rec0)

    rec1 = make_valid_record(
        id="audit-dec-20261029-001",
        actor_role="producer",
        action="ingest_vintage",
        new_state={"status": "ingested", "series": "br.ipca.monthly", "vintage": "2026-10"},
        prev_log_hash=rec0["payload_hash"],
        actor_id="user-producer-01",
        entity_type="vintage",
        entity_id="vintage-2026-10",
        justification="Ingestão mensal oficial",
    )

    rec2 = make_valid_record(
        id="audit-dec-20261029-002",
        actor_role="reviewer",
        action="approve_calibration",
        new_state={"status": "approved", "calibration": "fiscal-2026-v2"},
        prev_log_hash=rec1["payload_hash"],
        actor_id="user-reviewer-01",
        entity_type="calibration",
        entity_id="fiscal-2026-v2",
        justification="Homologação técnica",
    )

    rec3 = make_valid_record(
        id="audit-dec-20261029-003",
        actor_role="publisher",
        action="publish_guidance",
        new_state={"status": "published", "guidance": "comm-debt-stabilization-2030"},
        prev_log_hash=rec2["payload_hash"],
        actor_id="user-publisher-01",
        entity_type="guidance",
        entity_id="comm-debt-stabilization-2030",
        justification="Publicação de meta",
    )

    chain = [rec0, rec1, rec2, rec3]

    assert rec0["prev_log_hash"] == "0" * 64
    assert rec1["prev_log_hash"] == rec0["payload_hash"]
    assert rec2["prev_log_hash"] == rec1["payload_hash"]
    assert rec3["prev_log_hash"] == rec2["payload_hash"]

    assert verify_audit_chain(chain, raise_on_error=True) is True
    assert verify_audit_chain(chain, raise_on_error=False) is True


# ==============================================================================
# 3. Testes de Detecção de Adulteração (Tampering)
# ==============================================================================

@pytest.fixture
def sample_valid_chain():
    """Fixture que retorna uma cópia de cadeia de 3 registros válida."""
    rec0 = copy.deepcopy(GENESIS_RECORD)
    rec0["payload_hash"] = compute_payload_hash(rec0)

    rec1 = make_valid_record(
        id="audit-001",
        actor_role="producer",
        action="ingest_vintage",
        new_state={"spending_approved_brl": 500_000_000},
        prev_log_hash=rec0["payload_hash"],
        actor_id="user-producer-01",
        justification="Autorização inicial de desembolso",
    )

    rec2 = make_valid_record(
        id="audit-002",
        actor_role="reviewer",
        action="approve_calibration",
        new_state={"reviewed": True},
        prev_log_hash=rec1["payload_hash"],
        actor_id="user-reviewer-01",
        justification="Parecer metodológico favorável",
    )
    return [rec0, rec1, rec2]


def test_tampering_retroactive_payload_modification_fails(sample_valid_chain):
    """Adulteração de payload intermediário (new_state) é detectada imediatamente."""
    chain = sample_valid_chain
    chain[1]["new_state"] = {"spending_approved_brl": 999_999_999}

    assert verify_audit_chain(chain, raise_on_error=False) is False
    with pytest.raises(AssertionError, match="Payload hash mismatch at index 1"):
        verify_audit_chain(chain, raise_on_error=True)


def test_tampering_retroactive_justification_modification_fails(sample_valid_chain):
    """Adulteração de justificativa técnica em registro é detectada pelo hash canônico."""
    chain = sample_valid_chain
    chain[1]["justification"] = "Justificativa adulterada sem autorização"

    assert verify_audit_chain(chain, raise_on_error=False) is False
    with pytest.raises(AssertionError, match="Payload hash mismatch at index 1"):
        verify_audit_chain(chain, raise_on_error=True)


def test_tampering_retroactive_actor_modification_fails(sample_valid_chain):
    """Adulteração de actor_id em registro é detectada pelo hash canônico."""
    chain = sample_valid_chain
    chain[1]["actor_id"] = "user-impersonator"

    assert verify_audit_chain(chain, raise_on_error=False) is False
    with pytest.raises(AssertionError, match="Payload hash mismatch at index 1"):
        verify_audit_chain(chain, raise_on_error=True)


def test_tampering_payload_hash_altered_breaks_chain(sample_valid_chain):
    """Se o atacante recalcular o payload_hash do registro N, quebra o encadeamento no registro N+1."""
    chain = sample_valid_chain
    chain[1]["new_state"] = {"spending_approved_brl": 999_999_999}
    chain[1]["payload_hash"] = compute_payload_hash(chain[1])

    # O registro 2 ainda aponta para o payload_hash anterior -> cadeia quebrada
    assert verify_audit_chain(chain, raise_on_error=False) is False
    with pytest.raises(AssertionError, match="Chain broken at index 2"):
        verify_audit_chain(chain, raise_on_error=True)


def test_tampering_prev_log_hash_modification_fails(sample_valid_chain):
    """Adulteração de prev_log_hash em registro subsequente falha a verificação."""
    chain = sample_valid_chain
    chain[2]["prev_log_hash"] = "deadbeef" * 8

    assert verify_audit_chain(chain, raise_on_error=False) is False
    with pytest.raises(AssertionError, match="Payload hash mismatch at index 2"):
        verify_audit_chain(chain, raise_on_error=True)


def test_tampering_genesis_prev_log_hash_fails(sample_valid_chain):
    """Adulteração de prev_log_hash no registro gênese falha a verificação."""
    chain = sample_valid_chain
    chain[0]["prev_log_hash"] = "1" * 64

    assert verify_audit_chain(chain, raise_on_error=False) is False
    with pytest.raises(AssertionError, match="Payload hash mismatch at index 0"):
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

    assert "CREATE TABLE IF NOT EXISTS decision_audit_log" in content
    assert "CHECK (actor_role IN ('producer', 'reviewer', 'publisher', 'system'))" in content
    assert "CREATE TABLE IF NOT EXISTS system_api_keys" in content
    assert "CHECK (role IN ('producer', 'reviewer', 'publisher'))" in content


# ==============================================================================
# 5. Testes de Integração com PostgreSQL (usando o fixture db de conftest.py)
# ==============================================================================

def test_database_genesis_record_exists_and_valid(db):
    """Valida que o registro gênese é inserido no banco com os valores canônicos exatos."""
    with psycopg.connect(db) as conn:
        row = conn.execute("""
            SELECT id, event_id, actor_id, actor_role, action, entity_type, entity_id,
                   justification, previous_state, new_state, payload_hash, prev_log_hash
            FROM decision_audit_log
            WHERE id = 'audit-genesis-0000'
        """).fetchone()

        assert row is not None, "Registro gênese 'audit-genesis-0000' deve existir no banco de dados"
        audit_id, event_id, actor_id, role, action, entity_type, entity_id, justification, prev_state, new_state, p_hash, prev_hash = row

        assert role == "system"
        assert action == "initialize_audit_ledger"
        assert prev_hash == GENESIS_PREV_LOG_HASH, "prev_log_hash do gênese deve ser 64 zeros"
        assert p_hash == GENESIS_PAYLOAD_HASH

        canonical = {
            "action": action,
            "actor_id": actor_id,
            "actor_role": role,
            "entity_id": entity_id,
            "entity_type": entity_type,
            "event_id": event_id,
            "id": audit_id,
            "justification": justification,
            "new_state": new_state,
            "prev_log_hash": prev_hash,
            "previous_state": prev_state,
        }
        assert compute_payload_hash(canonical) == p_hash


def test_database_insert_chained_records_and_verify(db):
    """Testa a inserção sequencial de registros de auditoria no PostgreSQL e a verificação da cadeia."""
    with psycopg.connect(db) as conn:
        genesis_hash = conn.execute("""
            SELECT payload_hash FROM decision_audit_log WHERE id = 'audit-genesis-0000'
        """).fetchone()[0]

        rec1 = {
            "action": "ingest_data",
            "actor_id": "user-producer-01",
            "actor_role": "producer",
            "entity_id": "vintage-202610",
            "entity_type": "vintage",
            "event_id": None,
            "id": "audit-test-001",
            "justification": "Ingestão periódica oficial de inflação",
            "new_state": {"dataset": "ibge-ipca", "vintage_id": "vintage-202610", "records_count": 120},
            "prev_log_hash": genesis_hash,
            "previous_state": None,
        }
        hash1 = compute_payload_hash(rec1)
        conn.execute("""
            INSERT INTO decision_audit_log (
                id, actor_id, actor_role, action, entity_type, entity_id,
                justification, new_state, payload_hash, prev_log_hash
            ) VALUES (
                %(id)s, %(actor_id)s, %(actor_role)s, %(action)s, %(entity_type)s, %(entity_id)s,
                %(justification)s, %(new_state)s::jsonb, %(payload_hash)s, %(prev_log_hash)s
            )
        """, {**rec1, "new_state": json.dumps(rec1["new_state"]), "payload_hash": hash1})

        rec2 = {
            "action": "approve_calibration",
            "actor_id": "user-reviewer-01",
            "actor_role": "reviewer",
            "entity_id": "prop-tax-reform-neutrality",
            "entity_type": "public_proposal",
            "event_id": None,
            "id": "audit-test-002",
            "justification": "Homologação metodológica de âncora fiscal",
            "new_state": {"target_proposal": "prop-tax-reform-neutrality", "calibrated_debt_anchor": 75.0},
            "prev_log_hash": hash1,
            "previous_state": None,
        }
        hash2 = compute_payload_hash(rec2)
        conn.execute("""
            INSERT INTO decision_audit_log (
                id, actor_id, actor_role, action, entity_type, entity_id,
                justification, new_state, payload_hash, prev_log_hash
            ) VALUES (
                %(id)s, %(actor_id)s, %(actor_role)s, %(action)s, %(entity_type)s, %(entity_id)s,
                %(justification)s, %(new_state)s::jsonb, %(payload_hash)s, %(prev_log_hash)s
            )
        """, {**rec2, "new_state": json.dumps(rec2["new_state"]), "payload_hash": hash2})

        rec3 = {
            "action": "publish_guidance",
            "actor_id": "user-publisher-01",
            "actor_role": "publisher",
            "entity_id": "comm-debt-stabilization-2030",
            "entity_type": "guidance_commitment",
            "event_id": None,
            "id": "audit-test-003",
            "justification": "Publicação de meta após duplo parecer",
            "new_state": {"commitment_id": "comm-debt-stabilization-2030", "status": "proposed_target"},
            "prev_log_hash": hash2,
            "previous_state": None,
        }
        hash3 = compute_payload_hash(rec3)
        conn.execute("""
            INSERT INTO decision_audit_log (
                id, actor_id, actor_role, action, entity_type, entity_id,
                justification, new_state, payload_hash, prev_log_hash
            ) VALUES (
                %(id)s, %(actor_id)s, %(actor_role)s, %(action)s, %(entity_type)s, %(entity_id)s,
                %(justification)s, %(new_state)s::jsonb, %(payload_hash)s, %(prev_log_hash)s
            )
        """, {**rec3, "new_state": json.dumps(rec3["new_state"]), "payload_hash": hash3})

        rows = conn.execute("""
            SELECT id, event_id, actor_id, actor_role, action, entity_type, entity_id,
                   justification, previous_state, new_state, payload_hash, prev_log_hash
            FROM decision_audit_log
            ORDER BY created_at ASC, id ASC
        """).fetchall()

        chain = [
            {
                "id": r[0],
                "event_id": r[1],
                "actor_id": r[2],
                "actor_role": r[3],
                "action": r[4],
                "entity_type": r[5],
                "entity_id": r[6],
                "justification": r[7],
                "previous_state": r[8],
                "new_state": r[9],
                "payload_hash": r[10],
                "prev_log_hash": r[11],
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
