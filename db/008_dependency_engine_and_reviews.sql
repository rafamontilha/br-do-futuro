-- Brasil do Futuro - Fase 1: Motor de Dependências e Recálculo Seletivo; Workflow de Revisão Humana
-- Migração 008: Grafo de dependências (DAG), planos de recálculo e workflow de revisão humana

-- 1. Nós do Grafo de Dependências (DAG)
CREATE TABLE IF NOT EXISTS dependency_graph_nodes (
    id text PRIMARY KEY,
    node_type text NOT NULL CHECK (node_type IN ('indicator', 'model', 'scenario', 'guidance_target', 'policy_proposal')),
    canonical_name text NOT NULL,
    domain_id integer,
    description text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT clock_timestamp()
);

CREATE INDEX IF NOT EXISTS dependency_graph_nodes_type ON dependency_graph_nodes(node_type);

-- 2. Arestas do Grafo de Dependências (DAG)
CREATE TABLE IF NOT EXISTS dependency_graph_edges (
    id text PRIMARY KEY,
    source_node_id text NOT NULL REFERENCES dependency_graph_nodes(id) ON DELETE CASCADE,
    target_node_id text NOT NULL REFERENCES dependency_graph_nodes(id) ON DELETE CASCADE,
    relationship_type text NOT NULL CHECK (relationship_type IN ('direct_input', 'accounting_identity', 'behavioral_elasticity', 'target_benchmark')),
    materiality_rule text NOT NULL CHECK (materiality_rule IN ('delta_absolute', 'target_breach', 'elasticity_shock', 'composite')),
    threshold_value numeric(16,6) NOT NULL,
    created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    UNIQUE (source_node_id, target_node_id)
);

CREATE INDEX IF NOT EXISTS dependency_graph_edges_source ON dependency_graph_edges(source_node_id);
CREATE INDEX IF NOT EXISTS dependency_graph_edges_target ON dependency_graph_edges(target_node_id);

-- 3. Aprimoramento da tabela de alertas para workflow de revisão humana
ALTER TABLE alert ADD COLUMN IF NOT EXISTS reviewed_by text;
ALTER TABLE alert ADD COLUMN IF NOT EXISTS review_justification text;
ALTER TABLE alert ADD COLUMN IF NOT EXISTS reviewed_at timestamptz;

-- 4. Planos de Recálculo Seletivo gerados pelo motor
CREATE TABLE IF NOT EXISTS recalculation_plan (
    id text PRIMARY KEY,
    event_id uuid REFERENCES outbox(id),
    trigger_indicator_id text NOT NULL,
    affected_nodes jsonb NOT NULL,
    rationale text NOT NULL,
    status text NOT NULL DEFAULT 'executed' CHECK (status IN ('planned', 'executed', 'skipped', 'failed')),
    created_at timestamptz NOT NULL DEFAULT clock_timestamp()
);

CREATE INDEX IF NOT EXISTS recalculation_plan_trigger ON recalculation_plan(trigger_indicator_id);
CREATE INDEX IF NOT EXISTS recalculation_plan_created ON recalculation_plan(created_at DESC);

-- 5. Sementes canônicas dos nós do DAG
INSERT INTO dependency_graph_nodes (id, node_type, canonical_name, domain_id, description)
VALUES
    -- Indicadores P0
    ('indicator:br.debt.gross_pct_gdp', 'indicator', 'Dívida Bruta (% PIB)', 5, 'Dívida Bruta do Governo Geral em proporção do PIB (BCB/STN)'),
    ('indicator:br.ipca.12m', 'indicator', 'IPCA 12 Meses', 2, 'Inflação oficial acumulada em 12 meses medida pelo IBGE'),
    ('indicator:br.selic.target_annual', 'indicator', 'Taxa Selic Meta', 3, 'Meta da taxa de juros básica definida pelo Copom/BCB'),
    ('indicator:br.gdp.quarterly_yoy', 'indicator', 'PIB Trimestral (YoY)', 1, 'Crescimento real interanual do Produto Interno Bruto (IBGE)'),
    ('indicator:br.fx.usd_brl.ptax', 'indicator', 'Câmbio USD/BRL (PTAX)', 4, 'Taxa de câmbio comercial de fechamento PTAX (BCB)'),
    ('indicator:br.labor.unemployment_rate', 'indicator', 'Taxa de Desocupação', 6, 'Taxa de desocupação da força de trabalho medida pela PNAD Contínua (IBGE)'),

    -- Modelos Analíticos
    ('model:fiscal_path_v1', 'model', 'Identidade Fiscal v1', 5, 'Modelo canônico da evolução da dívida/PIB por identidade contábil'),

    -- Cenários Fiscais
    ('scenario:continuity', 'scenario', 'Cenário Continuidade', 5, 'Trajetória inercial fiscal sem alterações nas regras orçamentárias vigentes'),
    ('scenario:alternative', 'scenario', 'Cenário Alternativo', 5, 'Trajetória com ajuste fiscal estrutural de +1,0 p.p. no primário'),
    ('scenario:adverse', 'scenario', 'Cenário Adverso', 5, 'Trajetória de estresse com juros elevados, baixo crescimento e déficit'),
    ('scenario:dynamic_simulations', 'scenario', 'Simulações Dinâmicas', 5, 'Mecanismo de simulação de premissas interativas do usuário'),

    -- Metas Oficiais e Compromissos do Guidance
    ('guidance_target:debt_stabilization', 'guidance_target', 'Estabilização da Dívida', 5, 'Compromisso institucional de estabilização da Dívida/PIB até 2030'),
    ('guidance_target:inflation_target_cmn', 'guidance_target', 'Meta Contínua de Inflação', 2, 'Meta oficial do CMN de 3,00% a.a. com intervalo de tolerância de +/- 1,5 p.p.'),
    ('guidance_target:selic_neutral_band', 'guidance_target', 'Banda Neutra de Juros', 3, 'Faixa referencial de equilíbrio neutro de taxa de juros real')
ON CONFLICT (id) DO UPDATE SET
    canonical_name = EXCLUDED.canonical_name,
    domain_id = EXCLUDED.domain_id,
    description = EXCLUDED.description;

-- 6. Sementes canônicas das arestas do DAG com regras de materialidade e limiares
INSERT INTO dependency_graph_edges (id, source_node_id, target_node_id, relationship_type, materiality_rule, threshold_value)
VALUES
    -- Dívida alimenta diretamente o modelo fiscal e os cenários
    ('edge:debt->fiscal_model', 'indicator:br.debt.gross_pct_gdp', 'model:fiscal_path_v1', 'direct_input', 'delta_absolute', 0.500000),
    ('edge:fiscal_model->continuity', 'model:fiscal_path_v1', 'scenario:continuity', 'accounting_identity', 'delta_absolute', 0.500000),
    ('edge:fiscal_model->alternative', 'model:fiscal_path_v1', 'scenario:alternative', 'accounting_identity', 'delta_absolute', 0.500000),
    ('edge:fiscal_model->adverse', 'model:fiscal_path_v1', 'scenario:adverse', 'accounting_identity', 'delta_absolute', 0.500000),
    ('edge:debt->dynamic_sim', 'indicator:br.debt.gross_pct_gdp', 'scenario:dynamic_simulations', 'direct_input', 'delta_absolute', 0.500000),

    -- Selic e PIB influenciam o modelo fiscal por elasticidade e identidade
    ('edge:selic->fiscal_model', 'indicator:br.selic.target_annual', 'model:fiscal_path_v1', 'behavioral_elasticity', 'delta_absolute', 0.250000),
    ('edge:gdp->fiscal_model', 'indicator:br.gdp.quarterly_yoy', 'model:fiscal_path_v1', 'direct_input', 'delta_absolute', 0.500000),

    -- Cenário de continuidade é confrontado com a meta de estabilização da dívida
    ('edge:continuity->debt_target', 'scenario:continuity', 'guidance_target:debt_stabilization', 'target_benchmark', 'target_breach', 0.500000),

    -- Inflação e Selic são confrontados com suas respectivas metas institucionais
    ('edge:ipca->cmn_target', 'indicator:br.ipca.12m', 'guidance_target:inflation_target_cmn', 'target_benchmark', 'composite', 0.250000),
    ('edge:selic->neutral_band', 'indicator:br.selic.target_annual', 'guidance_target:selic_neutral_band', 'target_benchmark', 'delta_absolute', 0.250000)
ON CONFLICT (source_node_id, target_node_id) DO UPDATE SET
    relationship_type = EXCLUDED.relationship_type,
    materiality_rule = EXCLUDED.materiality_rule,
    threshold_value = EXCLUDED.threshold_value;

-- 7. Permissões de Leitura e Escrita Controlada
DO $$ BEGIN
    IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname='bdf_reader') THEN
        GRANT SELECT ON dependency_graph_nodes TO bdf_reader;
        GRANT SELECT ON dependency_graph_edges TO bdf_reader;
        GRANT SELECT, INSERT ON recalculation_plan TO bdf_reader;
        GRANT SELECT, UPDATE (review_status, reviewed_by, review_justification, reviewed_at) ON alert TO bdf_reader;
    END IF;
END $$;
