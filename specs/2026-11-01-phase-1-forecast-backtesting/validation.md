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
