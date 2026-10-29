# Plan — Sources, Freshness & Operational Replay (Incremento 02)

## Task groups

### 1. Data layer
1.1. Criar migração SQL `db/003_source_schedules_and_replay.sql` com as tabelas `source_schedules` e `outbox_replay_audit`, adicionando índices por `indicator_id`, `status` e `next_expected_at`.
1.2. Inserir sementes de agendamento canônico para os 3 indicadores prioritários (`br.ipca.monthly` via IBGE/SIDRA com fallback BCB, `br.selic.daily` via BCB, `br.debt.gross_pct_gdp` via BCB) com seus cronogramas e janelas de tolerância oficiais.
1.3. Implementar conector IBGE/SIDRA em `ingestion/bdf/sources/ibge.py` com suporte à API Agregados/SIDRA para o IPCA, extração do JSON bruto, cálculo de hash SHA-256 e conformidade com o contrato de dados de observação.
1.4. Estender o worker Python em `ingestion/bdf/worker.py` para calcular métricas de freshness (`is_stale`, `current_delay_hours`), gerenciar retries com backoff exponencial e implementar o circuit breaker.

### 2. Components / UI
2.1. Criar componente `<SourceFreshnessPanel>` em `web/app/components/SourceFreshnessPanel.tsx` exibindo cards para cada indicador com fonte primária, última coleta, próxima divulgação oficial e badge de status de SLA (`EM DIA`, `ATENÇÃO`, `ATRASADO`).
2.2. Criar componente `<OperationalReplayModal>` em `web/app/components/OperationalReplayModal.tsx` com formulário controlado para seleção de eventos/indicador, campo de justificativa obrigatório e confirmação de acionamento.
2.3. Criar componente `<CircuitBreakerBadge>` em `web/app/components/CircuitBreakerBadge.tsx` indicando o estado de prontidão dos conectores governamentais (`Normal`, `Alerta`, `Circuito Aberto`).

### 3. Page & route
3.1. Adicionar endpoint `GET /api/v1/health/sources` no serviço Go (`services/api/main.go`) retornando a lista de agendamentos, status de freshness, atraso em horas e estado do circuit breaker.
3.2. Adicionar endpoint `POST /api/v1/admin/outbox/replay` no serviço Go para registrar a solicitação em `outbox_replay_audit`, marcar eventos alvo com status `replay_pending` e emitir log estruturado de auditoria.
3.3. Adicionar endpoint `GET /api/v1/admin/outbox/replay/{id}` no serviço Go para acompanhar o progresso e o número de eventos reprocessados.
3.4. Integrar a seção de Saúde Operacional e o botão de Replay na interface principal em `web/app/page.tsx` com atualização periódica e feedback de erro/sucesso.

### 4. Navigation / integration
4.1. Atualizar especificação OpenAPI em `docs/openapi.yaml` documentando `/api/v1/health/sources` e `/api/v1/admin/outbox/replay` com schemas completos de entrada e saída.
4.2. Atualizar script de fumaça `scripts/smoke.py` com checagem de integridade dos agendamentos oficiais de fontes e simulação de replay operacional.

### 5. Tests
5.1. Implementar testes unitários em `tests/test_ibge_connector.py` validando o parse do payload da API SIDRA do IBGE, normalização de datas e validação de schema do IPCA.
5.2. Implementar testes unitários em `tests/test_freshness_calculator.py` cobrindo cálculo de dias úteis/horas de atraso, transição de estado de frescor e lógica do circuit breaker.
5.3. Implementar testes de integração em Go em `services/api/main_test.go` cobrindo o endpoint `GET /api/v1/health/sources` e a emissão de replay em `POST /api/v1/admin/outbox/replay` (incluindo rejeição quando justificativa for vazia).
5.4. Executar verificação completa local: `pytest`, `go test ./...`, `go vet ./...`, `npm run build` e typecheck do Next.js.
