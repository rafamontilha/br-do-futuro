-- Brasil do Futuro - Incremento de Premissas Dinâmicas e Métricas Institucionais
-- Migração 002

CREATE TABLE IF NOT EXISTS institutional_actors (
    actor_id text PRIMARY KEY,
    name text NOT NULL,
    sphere text NOT NULL CHECK (sphere IN ('federal', 'subnational', 'independent', 'civil_society')),
    legal_framework text NOT NULL,
    description text NOT NULL
);

CREATE TABLE IF NOT EXISTS indicator_institutional_roles (
    indicator_id text NOT NULL,
    actor_id text NOT NULL REFERENCES institutional_actors(actor_id),
    role text NOT NULL CHECK (role IN ('proposer', 'approver', 'executor', 'funder', 'auditor', 'beneficiary')),
    notes text,
    PRIMARY KEY (indicator_id, actor_id, role)
);

CREATE TABLE IF NOT EXISTS dynamic_simulations (
    simulation_id text PRIMARY KEY,
    base_debt_pct numeric NOT NULL,
    assumptions jsonb NOT NULL,
    status text NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'completed', 'failed')),
    results jsonb,
    error text,
    requested_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    completed_at timestamptz
);

-- Carga inicial dos 7 atores institucionais constitucionais
INSERT INTO institutional_actors (actor_id, name, sphere, legal_framework, description)
VALUES
    ('EXEC', 'Poder Executivo Federal', 'federal', 'Art. 84 e 165 da CF/88', 'Formulação e execução de políticas públicas, gestão orçamentária e administração financeira da União.'),
    ('LEG', 'Poder Legislativo (Congresso Nacional)', 'federal', 'Art. 48, 49 e 166 da CF/88', 'Aprovação de leis orçamentárias (PPA, LDO, LOA), reformas tributárias e fiscalização financeira.'),
    ('JUD', 'Poder Judiciário', 'federal', 'Art. 92 e 100 da CF/88', 'Controle jurisdicional e de constitucionalidade das normas fiscais e ordenação de precatórios.'),
    ('BCB', 'Banco Central do Brasil', 'independent', 'Lei Complementar nº 179/2021', 'Execução da política monetária, controle da inflação conforme meta, regulação financeira e estabilidade cambial.'),
    ('TCU', 'Tribunal de Contas da União', 'independent', 'Art. 70 a 73 da CF/88', 'Controle externo e fiscalização contábil, financeira, orçamentária, operacional e patrimonial da União.'),
    ('SUB', 'Entes Subnacionais (Estados e Municípios)', 'subnational', 'Art. 18, 157-159 da CF/88 e LRF (LC 101/2000)', 'Execução descentralizada de serviços essenciais e cumprimento de metas e limites fiscais federativos.'),
    ('SOC', 'Sociedade Civil e Setor Produtivo', 'civil_society', 'Art. 1º, parágrafo único da CF/88', 'Participação social, debate público, produção econômica e destinatária final das políticas públicas.')
ON CONFLICT (actor_id) DO NOTHING;

-- Mapeamento inicial de competências para os 3 indicadores prioritários
INSERT INTO indicator_institutional_roles (indicator_id, actor_id, role, notes)
VALUES
    ('br.debt.gross_pct_gdp', 'EXEC', 'executor', 'Administração e refinanciamento da dívida pública pelo Tesouro Nacional.'),
    ('br.debt.gross_pct_gdp', 'LEG', 'approver', 'Fixação de limites de dívida pública pelo Senado Federal e aprovação orçamentária.'),
    ('br.debt.gross_pct_gdp', 'BCB', 'auditor', 'Cálculo metodológico e publicação das estatísticas oficiais da dívida líquida e bruta.'),
    ('br.debt.gross_pct_gdp', 'TCU', 'auditor', 'Auditoria anual da conformidade da dívida com a Lei de Responsabilidade Fiscal.'),
    ('br.ipca.monthly', 'EXEC', 'proposer', 'Definição da meta contínua de inflação pelo Conselho Monetário Nacional (CMN).'),
    ('br.ipca.monthly', 'BCB', 'executor', 'Condução da política de juros pelo Copom para convergência da inflação à meta.'),
    ('br.ipca.monthly', 'SOC', 'beneficiary', 'Preservação do poder de compra e previsibilidade das relações econômicas.'),
    ('br.selic.daily', 'BCB', 'executor', 'Fixação da taxa meta pelo Copom e operações compromissadas diárias no mercado aberto.'),
    ('br.selic.daily', 'SOC', 'beneficiary', 'Parâmetro de taxa livre de risco, custo de crédito e remuneração da poupança.')
ON CONFLICT (indicator_id, actor_id, role) DO NOTHING;

-- Permissões para bdf_reader
GRANT SELECT, INSERT, UPDATE ON dynamic_simulations TO bdf_reader;
GRANT SELECT, INSERT ON outbox TO bdf_reader;
GRANT SELECT ON institutional_actors, indicator_institutional_roles TO bdf_reader;
