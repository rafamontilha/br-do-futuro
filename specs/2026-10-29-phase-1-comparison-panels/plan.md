# Plan — Phase 1: Painéis de Realizado vs. Baseline, Forecast, Target e Cenário de Continuidade

## Summary

Construir os painéis comparativos multi-perspectiva de trajetórias macroeconômicas para o núcleo P0, permitindo confrontar a série histórica realizada com o baseline, forecasts (com bandas de incerteza), metas oficiais declaradas (targets) e projeções de continuidade inercial. O trabalho abrange desde a persistência relacional em PostgreSQL, passando pelo endpoint Go unificado com filtro bitemporal `as_of`, até a interface Next.js com gráfico vetorial responsivo, tabela analítica de desvios e rotulagem de rigor metodológico.

## Architecture / Design

```text
[ Dados Oficiais / Vintages ]   [ Modelos / Calibrações ]   [ Metas Institucionais (CMN/LDO) ]
              │                            │                               │
              ▼                            ▼                               ▼
[ PostgreSQL: db/007_trajectory_comparisons.sql ]
   - indicator_trajectories (actual, baseline, forecast, target, continuity)
   - Bandas de incerteza (forecast_lower, forecast_upper)
   - Corte temporal e bitemporalidade (as_of, vintage_date)
              │
              ▼
[ Go API Service: services/api/ ]
   - GET /v1/trajectories?indicator_id={id}&as_of={iso_date}
   - Alinhamento de séries por período e agregação temporal
   - Testes unitários e de integração em main_test.go
              │
              ▼
[ Next.js Web App: web/app/components/MacroTrajectoryPanel.tsx ]
   - Seletor de indicador P0 (6 séries canônicas)
   - Visualização vetorial SVG com curvas sobrepostas e bandas de incerteza
   - Badges de integridade: 'Oficial', 'Meta CMN/LDO', 'Ilustrativo / Não-oficial'
   - Tabela de desvios absolutos e relativos por período
```

## Task Groups

### 1. Data Layer & Database Migrations
1.1. Criar migração SQL `db/007_trajectory_comparisons.sql` com a estrutura da tabela `indicator_trajectories` vinculada por chave estrangeira à tabela `indicators`.
1.2. Implementar colunas para `actual_value`, `baseline_value`, `forecast_value`, `forecast_lower`, `forecast_upper`, `target_value`, `continuity_value`, `calibration_status` e `as_of_valid_until`.
1.3. Popular dados herméticos de referência/fixtures em `fixtures/trajectories.json` para os 6 indicadores P0 (períodos 2022 a 2030).
1.4. Inserir script ou seed inicial para carregar as trajetórias de teste no banco `bdf` e `bdf_test`.

### 2. Go API Backend
2.1. Definir tipos Go para `TrajectoryPoint`, `TrajectoryResponse` e metadados de incerteza em `services/api/repository.go`.
2.2. Implementar método no repositório `GetTrajectories(ctx, indicatorID, asOf)` respeitando isolamento temporal e ordenação por período.
2.3. Registrar rota `GET /v1/trajectories` em `services/api/main.go` com tratamento de parâmetros de consulta e headers CORS/JSON.
2.4. Adicionar testes de unidade e integração em `services/api/main_test.go` verificando alinhamento de curvas, dados ausentes e respeito a cortes bitemporais `as_of`.

### 3. Frontend Web (Next.js & TypeScript)
3.1. Criar componente `web/app/components/MacroTrajectoryPanel.tsx` com interface interativa.
3.2. Implementar gráfico vetorial SVG responsivo renderizando curvas estilizadas para Realizado (sólida preta/escura), Target (tracejada verde), Baseline (pontilhada cinza), Forecast (linha azul com área de incerteza sombreada) e Continuidade (linha laranja/âmbar).
3.3. Adicionar badges semânticos de proveniência com alertas de que forecasts são ilustrativos/em calibração.
3.4. Implementar tabela colapsável de desvios calculando a distância entre Realizado e Target/Forecast por ano/período.
3.5. Integrar o novo painel em `web/app/page.tsx` dentro da seção de inteligência econômica e do Observatório.

### 4. Ingestão & Verificação End-to-End
4.1. Atualizar testes Python (`tests/test_trajectories.py`) validando os schemas Pydantic de trajetórias e coerência dos dados de fixture.
4.2. Atualizar o script `scripts/smoke.py` para consultar `/v1/trajectories` e verificar a integridade das 5 curvas.
4.3. Executar suíte completa: `pytest`, `go test ./...`, `go vet ./...` e `npm run build`.
