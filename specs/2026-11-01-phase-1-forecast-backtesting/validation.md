# Validation — Phase 1: Backtesting de Forecasts por Vintage e Horizonte

## Automated

- [ ] `./scripts/verify.sh` passa (pytest com PostgreSQL `bdf_test`, `go test ./...`,
      `go vet ./...`, `npm run build`, `npm run typecheck`, `git diff --check`).
- [ ] `pytest tests/test_backtesting.py` passa sem novas falhas na suíte existente.
- [ ] `python scripts/smoke.py` valida `GET /v1/backtests`.
- [ ] Novos testes cobrem: métricas, horizonte, garantia ex-ante, revisão de vintage,
      benchmarks sem vazamento, idempotência, filtros e `as_of` da API.

### Key assertions

| Behaviour | Test type | Expected result |
|-----------|-----------|-----------------|
| `mae`/`rmse`/`bias` com pares conhecidos | unit (Python) | valores exatos esperados |
| `compute_horizon` mensal/anual | unit (Python) | horizonte correto em períodos nativos |
| Snapshot com `forecast_origin_at >= known_at` do realizado | unit (Python) | par descartado; não entra nas métricas |
| Snapshot `reconstructed` | unit (Python) | nunca agregado com `ex_ante` |
| Série revisada (2 vintages) | integration (Python) | `first_release` usa a 1ª vintage, `latest` a mais recente `<= as_of` |
| Benchmark random walk | unit (Python) | usa só observações com `known_at <= origin_at` |
| `run_backtest` executado 2× com mesmas entradas | integration (Python) | um único `backtest_run` |
| `UPDATE`/`DELETE` em `forecast_snapshot` | integration (SQL) | exceção `append-only evidence` |
| Worker com `dict_row` | integration (Python) | captura e backtest funcionam sem depender de `row_factory` implícito |
| `GET /v1/backtests?as_of=` anterior ao run | integration (Go) | run não retornado |
| `GET /v1/backtests?target=foo` | integration (Go) | 400 Bad Request |
| `GET /v1/backtests` sem runs | integration (Go) | 200 com lista vazia e `experimental: true` |

## Manual walkthrough

1. Subir os serviços (`docker compose up -d`) com o banco migrado até `009`.
2. Executar `python -m bdf.backtesting --mode fixture --as-of <agora>`.
3. Consultar `GET /v1/backtests?mode=fixture` e conferir `run_id`, `code_version`, `as_of`
   e `experimental: true`.
4. Abrir `http://localhost:3000`, plano "Modelos & Cenários" do painel de observabilidade.
5. Conferir a tabela por indicador × horizonte, a alternância `first_release`/`latest`
   e os badges "Experimental" e "Fixture".
6. Reexecutar o comando do passo 2 e confirmar que nenhum run duplicado foi criado.

### Edge cases

- [ ] **Sem snapshots ex-ante:** painel mostra estado vazio explicativo, sem erro.
- [ ] **Amostra insuficiente:** exibe "Amostra insuficiente" em vez de métricas.
- [ ] **Indicador sem intervalo:** cobertura exibida como "n/d", não 0%.
- [ ] **Indicador diário (câmbio):** sazonal ingênuo não é aplicado.
- [ ] **Falha de banco na captura:** erro explícito/logado; nenhum dado estático substitui o resultado.

## Tone check (`specs/mission.md`)

- [ ] Textos descrevem métricas de erro sem afirmar qualidade/superioridade do modelo.
- [ ] Dados `fixture` nunca rotulados como oficiais ou como desempenho real.
- [ ] Nenhuma recomendação ou Guidance publicado automaticamente a partir dos resultados.

## Definition of done

- [ ] Todos os checks automatizados passam.
- [ ] Walkthrough manual concluído sem comportamento inesperado (evidência humana).
- [ ] Questões abertas de `requirements.md` respondidas ou registradas como pendência.
- [ ] PR referencia `specs/2026-11-01-phase-1-forecast-backtesting/`.
- [ ] Roadmap atualizado indicando a entrega parcial do item 4 (backtesting), com alertas
      por calendário ainda pendentes.

## Evidência técnica — grupo 2 (2026-11-02)

- `./scripts/verify.sh`: **aprovado**, exit code 0; **168 testes Python** em
  PostgreSQL dedicado `bdf_test` (3,45 s), testes e vet Go, build e typecheck web,
  `git diff --check`.
- `tests/test_forecast_snapshots.py`: **15 testes aprovados**; conexões `dict_row`
  e `tuple_row`, horizontes nativos, classificação fixture/reconstructed e source/ex_ante,
  benchmarks sem revisão posterior à origem, isolamento de modos, replay idempotente,
  rollback do worker por erro de captura e atomicidade da captura de trajetórias.
- O teste em modo source usa payload sintético para exercitar o contrato; não constitui
  evidência de captura oficial nem validação econômica.
- O registro anterior dizia que dois testes haviam sido escritos após a primeira
  execução. O comando que os gravaria foi rejeitado antes da execução. Eles foram
  efetivamente adicionados e validados nesta retomada.
- O relógio do PostgreSQL é usado como origem nos testes para evitar divergência entre
  o relógio do host e o do banco. Origens futuras continuam rejeitadas.
- Grupos 3–6 e walkthrough humano da feature continuam pendentes. Esta evidência
  técnica não conclui o gate 0→1 nem aprovação metodológica.

## Revisão da PR #9 — horizonte na origem (2026-11-02)

- Finding P2 confirmado: publicações acumuladas antes do processamento tornam o período
  base do cenário diferente do último período conhecido em `scenario_run.created_at`.
- Correção: manter o alvo ancorado na base do cenário e calcular o horizonte contra
  a última observação do mesmo indicador/modo com `known_at <= forecast_origin_at`.
  Alvos com horizonte zero ou negativo são excluídos com contador explícito.
- Regressão parametrizada com conexão `dict_row`: base fevereiro/2025 e publicação
  setembro/2025 resultam em horizonte 5 para fevereiro/2026; publicações fevereiro e
  março/2026 excluem o primeiro alvo. Benchmarks mantêm o mesmo horizonte; outro modo
  e publicações posteriores à origem não alteram o resultado no replay.
- `./scripts/verify.sh`: aprovado, exit code 0; **171 testes Python** (18 de snapshots),
  testes/vet Go, build/typecheck web e `git diff --check`.

## Segunda revisão da PR #9 — bootstrap Compose (2026-11-02)

- Finding P1 confirmado: o serviço `db` montava somente 001–008; o worker atualizado
  depende de `forecast_snapshot` e falharia no fluxo documentado com banco novo.
- Incluído mount somente leitura da 009 após a 008. Runbook documenta aplicação
  aditiva em volumes existentes, que não executam novamente os scripts de init.
- Regressão `test_compose_initializes_all_migrations_in_order_read_only`: verifica
  paridade dos arquivos versionados, ordem, destinos de init e acesso somente leitura.
- `./scripts/verify.sh`: aprovado, exit code 0; **172 testes Python**, testes/vet Go,
  build/typecheck web e `git diff --check`. Nenhum volume foi excluído/recriado;
  não foi executado um novo bootstrap Docker ponta a ponta nesta revisão.
