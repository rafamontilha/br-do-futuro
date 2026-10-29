# Plan — Method & Product: Public Proposals, Fiscal Calibration & Guidance Contracts (Incremento 03)

## Task groups

### 1. Data layer
1.1. Criar migração SQL `db/004_proposals_and_guidance.sql` com as tabelas `public_proposals`, `guidance_commitments` e `fiscal_calibrations`, incluindo constraints de chaves estrangeiras com `economic_indicators`, enumerações de status e índices por `policy_axis` e `horizon_year`.
1.2. Inserir sementes canônicas estruturadas para as 3 propostas públicas fundamentais:
   - `prop-fiscal-mandatory-spending` (Revisão do Gasto Obrigatório e Previdência)
   - `prop-infra-investment-acceleration` (Aceleração do Investimento em Infraestrutura via PPI)
   - `prop-tax-reform-neutrality` (Simplificação Tributária, Neutralidade e Fim da Cumulatividade)
   com dados reais de custo estimado, fontes de financiamento, competências legais e referências de evidências.
1.3. Inserir sementes dos compromissos canônicos de Guidance 2027–2030 vinculados aos indicadores da base (`br.debt.gross_pct_gdp`, `br.ipca.monthly`, taxa de investimento), associando valores de baseline histórico auditado e metas com status `experimental_hypothesis`.
1.4. Inserir sementes de calibração de parâmetros fiscais (`fiscal_calibrations`) relacionando cenários base, otimista e adverso às hipóteses das propostas públicas.

### 2. Components / UI
2.1. Criar componente `<PolicyLabPortfolio>` em `web/app/components/PolicyLabPortfolio.tsx` renderizando a carteira de propostas públicas em cards responsivos com visualização do custo anual, fonte de financiamento e badge distintivo de competência institucional (Executivo vs Legislativo).
2.2. Criar componente `<ProposalDetailModal>` em `web/app/components/ProposalDetailModal.tsx` com tabs detalhando o mecanismo causal, contrafactual, evidências empíricas e riscos associados.
2.3. Criar componente `<GuidanceCommitmentsMatrix>` em `web/app/components/GuidanceCommitmentsMatrix.tsx` exibindo a matriz de compromissos 2027–2030 com colunas explícitas para Baseline, Meta Proposta, Projeção (Forecast) e Realizado (Actual), além do badge de status metodológico `Hipotética / Em Avaliação`.
2.4. Criar componente `<GovernanceDisclaimerAlert>` em `web/app/components/GovernanceDisclaimerAlert.tsx` destacando a neutralidade institucional, limites de competência constitucional e a regra de não vinculação estatal.

### 3. Page & route
3.1. Adicionar endpoints no serviço Go (`services/api/main.go`):
   - `GET /api/v1/proposals`: listagem de propostas com suporte a filtro por `axis` e `status`.
   - `GET /api/v1/proposals/{id}`: busca detalhada de proposta única com mecanismo causal e referências.
   - `GET /api/v1/guidance/commitments`: listagem de compromissos com união e dados de observação mais recente.
   - `GET /api/v1/scenarios/calibrations`: lista de parâmetros fiscais calibrados vinculados aos cenários.
3.2. Integrar as seções **Policy Lab — Propostas Públicas** e **Guidance Brasil (2027–2030)** na página principal do dashboard em `web/app/page.tsx` com carregamento assíncrono e tratamento de estados de erro/vazio.

### 4. Navigation / integration
4.1. Atualizar especificação OpenAPI em `docs/openapi.yaml` documentando os novos endpoints `/api/v1/proposals`, `/api/v1/proposals/{id}`, `/api/v1/guidance/commitments` e `/api/v1/scenarios/calibrations` com seus schemas JSON estruturados.
4.2. Atualizar script de fumaça `scripts/smoke.py` para validar a disponibilidade e conformidade de resposta das rotas de propostas e do Guidance.

### 5. Tests
5.1. Implementar testes de integração da API Go em `services/api/main_test.go` cobrindo:
   - `GET /api/v1/proposals` retornando as 3 propostas canônicas cadastradas com HTTP 200.
   - `GET /api/v1/proposals/prop-fiscal-mandatory-spending` com validação dos campos obrigatórios (mecanismo causal, custo, competência).
   - `GET /api/v1/proposals/inexistente` retornando HTTP 404 Not Found.
   - `GET /api/v1/guidance/commitments` retornando os compromissos plurianuais com separação dos 4 quadrantes.
5.2. Implementar teste unitário em Python `tests/test_policy_proposals_integrity.py` validando os contratos de dados das propostas, checagem de consistência de unidades (% do PIB e R$ bi) e integridade dos status de governança.
5.3. Executar validação completa do pipeline: `go test ./...`, `go vet ./...`, `npm run build` e typecheck do Next.js.
