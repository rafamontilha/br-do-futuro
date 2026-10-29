-- Brasil do Futuro - Incremento 04: Endurecimento do Piloto, Auditoria e Resiliência
-- Migração 005 (executada automaticamente pelo runner bdf migrate)

CREATE TABLE IF NOT EXISTS system_api_keys (
    id text PRIMARY KEY,
    token_hash text NOT NULL UNIQUE,
    actor_id text NOT NULL,
    actor_name text NOT NULL,
    role text NOT NULL CHECK (role IN ('producer', 'reviewer', 'publisher')),
    is_active boolean NOT NULL DEFAULT true,
    rate_limit_rpm integer NOT NULL DEFAULT 60,
    created_at timestamptz NOT NULL DEFAULT clock_timestamp()
);

CREATE INDEX IF NOT EXISTS system_api_keys_token_hash ON system_api_keys(token_hash);
CREATE INDEX IF NOT EXISTS system_api_keys_role ON system_api_keys(role);

CREATE TABLE IF NOT EXISTS decision_audit_log (
    id text PRIMARY KEY,
    event_id text,
    actor_id text NOT NULL,
    actor_role text NOT NULL CHECK (actor_role IN ('producer', 'reviewer', 'publisher', 'system')),
    action text NOT NULL,
    entity_type text NOT NULL,
    entity_id text NOT NULL,
    justification text NOT NULL,
    previous_state jsonb,
    new_state jsonb NOT NULL,
    payload_hash text NOT NULL,
    prev_log_hash text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT clock_timestamp()
);

CREATE INDEX IF NOT EXISTS decision_audit_log_entity ON decision_audit_log(entity_type, entity_id);
CREATE INDEX IF NOT EXISTS decision_audit_log_actor ON decision_audit_log(actor_id);
CREATE INDEX IF NOT EXISTS decision_audit_log_role ON decision_audit_log(actor_role);
CREATE INDEX IF NOT EXISTS decision_audit_log_created ON decision_audit_log(created_at DESC);

-- Sementes canônicas de chaves de API para os três papéis (tokens de teste/dev)
INSERT INTO system_api_keys (id, token_hash, actor_id, actor_name, role, rate_limit_rpm)
VALUES
    ('key-prod-001', '2470c2669c390531b6bfe0781205e36d74ac98a55d41a80f61dd5ee27068c897', 'user-producer-01', 'Produtor Oficial de Dados', 'producer', 120),
    ('key-rev-001', '2cc2b0d1020b54883366c2332c0fec8fc097c4238b7567d9151dc5c004d5c7fc', 'user-reviewer-01', 'Revisor Metodológico Independente', 'reviewer', 60),
    ('key-pub-001', '40575dc5f7fc7f160116b8f01aee216c6ba756c3cc7fa8fa26d5000d5d5ab777', 'user-publisher-01', 'Publicador de Políticas e Guidance', 'publisher', 30)
ON CONFLICT (id) DO NOTHING;

-- Registro gênese da trilha imutável de auditoria
INSERT INTO decision_audit_log (
    id, event_id, actor_id, actor_role, action, entity_type, entity_id,
    justification, previous_state, new_state, payload_hash, prev_log_hash
) VALUES (
    'audit-genesis-0000',
    NULL,
    'system-genesis',
    'system',
    'initialize_audit_ledger',
    'system',
    'bdf-foundation',
    'Gênese da trilha imutável de auditoria de decisões do Brasil do Futuro (Incremento 04)',
    NULL,
    '{"status": "initialized", "version": "v1.4"}'::jsonb,
    'af9fe7ed02660efdca8dfbcd16d0c9b300a92259e40671fd6b4ef18d7708975c',
    '0000000000000000000000000000000000000000000000000000000000000000'
) ON CONFLICT (id) DO NOTHING;

DO $$ BEGIN
    IF EXISTS (SELECT FROM pg_roles WHERE rolname = 'bdf_reader') THEN
        GRANT SELECT ON system_api_keys TO bdf_reader;
        GRANT SELECT, INSERT ON decision_audit_log TO bdf_reader;
    END IF;
END $$;
