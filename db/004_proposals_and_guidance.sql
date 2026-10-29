-- Brasil do Futuro - Incremento 03: Método, Propostas Públicas e Guidance Contracts
-- Migração 004 (executada automaticamente pelo runner bdf migrate)

CREATE TABLE IF NOT EXISTS public_proposals (
    id text PRIMARY KEY,
    title text NOT NULL,
    policy_axis text NOT NULL CHECK (policy_axis IN ('fiscal_quality', 'infrastructure_investment', 'tax_productivity', 'human_capital', 'state_efficiency')),
    status text NOT NULL CHECK (status IN ('hypothesis_under_review', 'calibrated', 'ready_for_peer_review')),
    problem_statement text NOT NULL,
    causal_mechanism text NOT NULL,
    cost_estimate_annual_brl numeric(14,2) NOT NULL,
    cost_pct_gdp numeric(5,2),
    funding_source text NOT NULL,
    institutional_competence text NOT NULL CHECK (institutional_competence IN ('executive_decree', 'ordinary_law', 'supplementary_law', 'constitutional_amendment')),
    responsible_actors jsonb NOT NULL DEFAULT '[]'::jsonb,
    counterfactual_summary text NOT NULL,
    empirical_evidence text NOT NULL,
    target_indicator_id text,
    created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    updated_at timestamptz NOT NULL DEFAULT clock_timestamp()
);

CREATE INDEX IF NOT EXISTS public_proposals_axis ON public_proposals(policy_axis);
CREATE INDEX IF NOT EXISTS public_proposals_status ON public_proposals(status);

CREATE TABLE IF NOT EXISTS guidance_commitments (
    id text PRIMARY KEY,
    proposal_id text REFERENCES public_proposals(id),
    indicator_id text NOT NULL,
    name text NOT NULL,
    horizon_year integer NOT NULL,
    status text NOT NULL CHECK (status IN ('experimental_hypothesis', 'proposed_target', 'under_evaluation')),
    baseline_period text NOT NULL,
    baseline_value numeric(12,4) NOT NULL,
    target_value numeric(12,4) NOT NULL,
    forecast_value numeric(12,4),
    actual_latest_value numeric(12,4),
    unit text NOT NULL,
    variance_explanation text,
    review_policy text NOT NULL DEFAULT 'annual' CHECK (review_policy IN ('annual', 'quarterly')),
    human_review_required boolean NOT NULL DEFAULT true,
    created_at timestamptz NOT NULL DEFAULT clock_timestamp(),
    updated_at timestamptz NOT NULL DEFAULT clock_timestamp()
);

CREATE INDEX IF NOT EXISTS guidance_commitments_indicator ON guidance_commitments(indicator_id);
CREATE INDEX IF NOT EXISTS guidance_commitments_horizon ON guidance_commitments(horizon_year);

CREATE TABLE IF NOT EXISTS fiscal_calibrations (
    id text PRIMARY KEY,
    scenario_id text NOT NULL,
    proposal_id text REFERENCES public_proposals(id),
    elasticity_revenue_gdp numeric(6,3) NOT NULL,
    real_interest_rate_spread numeric(6,3) NOT NULL,
    primary_balance_shift_pct_gdp numeric(6,3) NOT NULL,
    notes text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT clock_timestamp()
);

CREATE INDEX IF NOT EXISTS fiscal_calibrations_scenario ON fiscal_calibrations(scenario_id);

-- Carga inicial das 3 propostas canônicas do Policy Lab
INSERT INTO public_proposals (
    id, title, policy_axis, status, problem_statement, causal_mechanism,
    cost_estimate_annual_brl, cost_pct_gdp, funding_source, institutional_competence,
    responsible_actors, counterfactual_summary, empirical_evidence, target_indicator_id
)
VALUES
    (
        'prop-fiscal-mandatory-spending',
        'Revisão e Eficiência do Gasto Obrigatório e Previdenciário',
        'fiscal_quality',
        'hypothesis_under_review',
        'O crescimento inercial de despesas obrigatórias e indexações automáticas comprime o espaço para investimentos públicos essenciais e pressiona a sustentabilidade da dívida pública.',
        'A desindexação seletiva de benefícios, convergência de regras de aposentadoria e revisão periódica de programas sociais reduzem despesas primárias recorrentes em até 1,2% do PIB ao ano, desacelerando a dinâmica da dívida sem prejudicar o piso de proteção social aos mais vulneráveis.',
        -45.00,
        -0.40,
        'Revisão e focalização de programas sociais, contenção de reajustes automáticos acima do ganho de produtividade e redução de fraudes cadastrais.',
        'constitutional_amendment',
        '["Poder Executivo Federal (Ministério da Fazenda / MPO)", "Congresso Nacional (Câmara dos Deputados e Senado Federal)"]'::jsonb,
        'Sem a revisão estrutural, a rigidez orçamentária atinge 95% das despesas primárias da União, paralisando serviços públicos e elevando a dívida bruta para além de 85% do PIB até 2030.',
        'Evidências empíricas de consolidações fiscais baseadas em corte de despesas correntes (Alesina & Ardagna, 2013; Relatórios de Acompanhamento Fiscal da IFI/Senado 2024-2026).',
        'br.debt.gross_pct_gdp'
    ),
    (
        'prop-infra-investment-acceleration',
        'Aceleração do Investimento em Infraestrutura via Parcerias e Desregulamentação',
        'infrastructure_investment',
        'hypothesis_under_review',
        'A taxa de investimento no Brasil (FBCF em torno de 16-17% do PIB) é historicamente insuficiente para sustentar crescimento do PIB potencial acima de 2,5% ao ano.',
        'A expansão de garantias federais para debêntures de infraestrutura, desregulamentação ambiental transparente e reforço de segurança jurídica nas concessões elevam a FBCF privada em 1,5 p.p. do PIB em 4 anos, gerando ganhos de produtividade logística e crescimento potencial adicional de 0,5% a.a.',
        12.00,
        0.10,
        'Fundo Garantidor de Infraestrutura (FGI), receitas de outorgas de concessões anteriores e atração de investimento direto no país (IDP).',
        'ordinary_law',
        '["Ministério dos Transportes", "Ministério de Portos e Aeroportos", "Agências Reguladoras (ANTT, ANTAQ, ANAC)", "BNDES"]'::jsonb,
        'Estagnação do investimento logístico, gargalos de escoamento da safra agrícola, aumento contínuo do custo de frete e perda de competitividade externa.',
        'Estudos IPEA/CNI sobre retorno social da infraestrutura e multiplicador de longo prazo do investimento privado (Ferreira & Malliagaros, 1998; Frischtak, 2022).',
        'br.investment.gfcf_pct_gdp'
    ),
    (
        'prop-tax-reform-neutrality',
        'Transição Tributária para o IBS/CBS com Neutralidade de Carga e Fim da Cumulatividade',
        'tax_productivity',
        'hypothesis_under_review',
        'O sistema de tributação sobre o consumo no Brasil gera o maior contencioso tributário do mundo (mais de 70% do PIB) e severa distorção na alocação de fatores produtivos.',
        'A unificação em IVA dual (IBS e CBS) de base ampla com crédito financeiro amplo e neutralidade de carga elimina a cumulatividade de resíduos tributários, desonera investimentos e exportações, e eleva a produtividade total dos fatores (PTF) em até 10% no ciclo decenal.',
        0.00,
        0.00,
        'Compensação de alíquotas com base no modelo de alíquota de referência calculado pelo Comitê Gestor do IBS e Receita Federal do Brasil.',
        'supplementary_law',
        '["Congresso Nacional", "Comitê Gestor do IBS", "Secretaria Especial da Receita Federal do Brasil"]'::jsonb,
        'Manutenção da guerra fiscal interestadual, insegurança jurídica crônica para novas plantas industriais e desindustrialização precoce.',
        'Simulações de equilíbrio geral computável IPEA/UFMG (Appy et al., 2020; Pires, 2023) estimando incremento de 12% a 20% no PIB potencial em 15 anos.',
        'br.ipca.12m'
    )
ON CONFLICT (id) DO NOTHING;

-- Carga inicial dos 3 compromissos canônicos de Guidance 2027–2030
INSERT INTO guidance_commitments (
    id, proposal_id, indicator_id, name, horizon_year, status,
    baseline_period, baseline_value, target_value, forecast_value,
    actual_latest_value, unit, variance_explanation, review_policy, human_review_required
)
VALUES
    (
        'comm-debt-stabilization-2030',
        'prop-fiscal-mandatory-spending',
        'br.debt.gross_pct_gdp',
        'Estabilização da Dívida Bruta do Governo Geral até 2030',
        2030,
        'experimental_hypothesis',
        '2025-12',
        77.8000,
        75.0000,
        81.4000,
        NULL,
        '% do PIB',
        'Divergência entre o cenário de continuidade (dívida em alta devido a juros reais elevados) e a meta experimental de estabilização fundamentada nas propostas do Policy Lab.',
        'annual',
        true
    ),
    (
        'comm-inflation-convergence-2030',
        'prop-tax-reform-neutrality',
        'br.ipca.12m',
        'Convergência da Inflação Anual (IPCA 12m) ao Centro da Meta',
        2030,
        'experimental_hypothesis',
        '2025-12',
        4.1000,
        3.0000,
        3.8000,
        NULL,
        '% a.a.',
        'Meta contínua de 3,00% com intervalo de tolerância de 1,50 p.p. fixada pelo CMN para o IPCA acumulado em 12 meses; modelo projeta pressão residual no curto prazo.',
        'annual',
        true
    ),
    (
        'comm-investment-rate-2030',
        'prop-infra-investment-acceleration',
        'br.investment.gfcf_pct_gdp',
        'Elevação da Taxa de Investimento (FBCF) para 20% do PIB',
        2030,
        'experimental_hypothesis',
        '2025-12',
        16.5000,
        20.0000,
        17.2000,
        NULL,
        '% do PIB',
        'Meta experimental condicionada à segurança jurídica de concessões e atração de capital privado de longo prazo.',
        'annual',
        true
    )
ON CONFLICT (id) DO NOTHING;

-- Carga inicial de calibrações de parâmetros fiscais
INSERT INTO fiscal_calibrations (
    id, scenario_id, proposal_id, elasticity_revenue_gdp,
    real_interest_rate_spread, primary_balance_shift_pct_gdp, notes
)
VALUES
    (
        'calib-baseline-continuation',
        'baseline',
        NULL,
        1.050,
        6.200,
        0.000,
        'Cenário fiscal de continuidade inercial sem aprovação de novas reformas estruturais.'
    ),
    (
        'calib-mandatory-spending-package',
        'optimistic',
        'prop-fiscal-mandatory-spending',
        1.080,
        4.800,
        1.200,
        'Calibração com contenção de gastos obrigatórios gerando melhora estrutural de 1,2% do PIB no resultado primário e queda no prêmio de risco.'
    ),
    (
        'calib-infra-investment-boost',
        'optimistic',
        'prop-infra-investment-acceleration',
        1.150,
        5.100,
        0.300,
        'Aceleração do investimento logístico elevando a elasticidade de arrecadação por ganho de produtividade.'
    ),
    (
        'calib-tax-reform-efficiency',
        'baseline',
        'prop-tax-reform-neutrality',
        1.100,
        5.500,
        0.100,
        'Neutralidade da carga tributária no curto prazo com ganho gradual de eficiência alocativa a partir do 3º ano.'
    )
ON CONFLICT (id) DO NOTHING;

-- Permissões de leitura e auditoria para bdf_reader
GRANT SELECT, INSERT, UPDATE ON public_proposals TO bdf_reader;
GRANT SELECT, INSERT, UPDATE ON guidance_commitments TO bdf_reader;
GRANT SELECT, INSERT, UPDATE ON fiscal_calibrations TO bdf_reader;
