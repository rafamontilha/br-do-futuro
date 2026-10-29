# Plan — Dynamic Assumptions & Institutional Metrics

## Task groups

### 1. Data layer
1.1. Criar migração SQL `db/002_dynamic_and_institutional.sql` com tabelas `institutional_actors`, `indicator_institutional_roles` e `dynamic_simulations`.
1.2. Criar carga de dados canônica inicial dos 7 atores institucionais (`EXEC`, `LEG`, `JUD`, `BCB`, `TCU`, `SUB`, `SOC`) e vinculação inicial aos 3 indicadores existentes (`br.debt.gross_pct_gdp`, `br.ipca.monthly`, `br.selic.daily`).
1.3. Atualizar `ingestion/bdf/scenario.py` para desacoplar premissas fixas e suportar cálculo arbitrário de `fiscal_path` a partir de premissas dinâmicas com validação de limites.
1.4. Estender o worker Python em `ingestion/bdf/worker.py` para consumir eventos do tipo `DynamicSimulationRequested` da outbox, executar o cálculo fiscal e persistir o resultado com status `completed` em `dynamic_simulations`.

### 2. Components / UI
2.1. Criar componente `<FiscalAssumptionsForm>` em `web/app/components/FiscalAssumptionsForm.tsx` com sliders e inputs numéricos controlados para juros nominais, crescimento, resultado primário e ajuste estoque-fluxo.
2.2. Criar componente `<SimulationTrajectoryChart>` em `web/app/components/SimulationTrajectoryChart.tsx` renderizando a comparação visual entre os três cenários canônicos e a simulação dinâmica.
2.3. Criar componente `<InstitutionalBadge>` e `<InstitutionalMatrix>` em `web/app/components/InstitutionalMatrix.tsx` exibindo os atores institucionais, competências e base legal.
2.4. Adicionar banners de explicabilidade metodológica fixa com texto aprovado de não-previsão oficial.

### 3. Page & route
3.1. Adicionar endpoint `POST /api/v1/simulations/fiscal` no serviço Go (`services/api/main.go`) para validar input, gerar hash das premissas, registrar solicitação assíncrona na outbox e retornar status `pending` com `simulation_id`.
3.2. Adicionar endpoint `GET /api/v1/simulations/fiscal/{id}` no serviço Go para consulta do status e resultados da simulação.
3.3. Adicionar endpoint `GET /api/v1/institutions` no serviço Go para expor o catálogo de atores e papéis institucionais.
3.4. Integrar a interface do simulador na página principal `web/app/page.tsx` com polling/refetch do status da simulação assíncrona.

### 4. Navigation / integration
4.1. Atualizar especificação OpenAPI em `docs/openapi.yaml` documentando os novos endpoints, schemas de request e response.
4.2. Atualizar script de fumaça `scripts/smoke.py` com testes para requisição de simulação dinâmica, processamento pelo worker e recuperação via API.

### 5. Tests
5.1. Implementar testes unitários em `tests/test_dynamic_simulation.py` para o motor de cenários com premissas dinâmicas, valores limítrofes e cálculo de fingerprint SHA-256.
5.2. Implementar testes de integração em `tests/test_worker_dynamic.py` para o fluxo de outbox → worker → gravação de resultado de simulação.
5.3. Implementar testes unitários e de integração em Go em `services/api/main_test.go` cobrindo validação de payloads inválidos e recuperação de atores institucionais.
5.4. Executar verificação completa local: `pytest`, `go test ./...`, `go vet ./...`, `npm run build` e typecheck do Next.js.
