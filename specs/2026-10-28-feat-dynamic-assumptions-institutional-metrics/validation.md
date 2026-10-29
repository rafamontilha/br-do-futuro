# Validation — Dynamic Assumptions & Institutional Metrics

## Automated

- [ ] `pytest tests/` passa com PostgreSQL real sem testes pulados
- [ ] `go test ./...` e `go vet ./...` no diretório `services/api` passam sem avisos ou erros
- [ ] `npm run build` e typecheck no diretório `web/` passam limpos sem erros
- [ ] `python3 scripts/smoke.py` valida com sucesso a API local e os novos endpoints
- [ ] Novos testes cobrem:
  - Validação de premissas numéricas com valores limite e rejeição de entradas inválidas
  - Cálculo de fingerprint determinístico SHA-256
  - Ciclo de vida assíncrono: solicitação na outbox → execução pelo worker → persistência do resultado
  - Consulta do catálogo institucional de competências e relacionamento com indicadores

### Key assertions
| Behaviour | Test type | Expected result |
|---|---|---|
| Premissas dinâmicas válidas | Unit (Python) | Trajetória da dívida calculada com precisão `Decimal` esperada |
| Premissas com $g \le -100\%$ ou não numéricas | Unit (Python / Go) | Erro `ValueError` / HTTP 400 Bad Request |
| Despacho assíncrono de simulação | Integration (Go / DB) | Retorno HTTP 202 Accepted com `simulation_id` e status `pending` |
| Processamento assíncrono pelo Worker | Integration (Python / DB) | Worker processa outbox e atualiza `dynamic_simulations` para `completed` |
| Consulta de atores institucionais | Integration (Go) | Retorno HTTP 200 contendo os 7 atores canônicos e suas esferas |

## Manual walkthrough

1. Iniciar o ambiente completo via Docker Compose (`docker compose up -d --build`).
2. Acessar a interface web no navegador (`http://localhost:3000`).
3. Navegar até o painel de **Simulações Fiscais Dinâmicas**.
4. Ajustar os sliders de taxa de juros ($i_t$), crescimento do PIB ($g_t$) e resultado primário ($p_t$).
5. Clicar no botão **"Simular Trajetória"**.
6. Observar o estado de carregamento/processamento assíncrono e a renderização subsequente da curva comparativa da dívida bruta/PIB.
7. Verificar se o aviso metodológico em destaque está visível: *"Simulação contábil condicional; não constitui previsão oficial nem aconselhamento."*
8. Inspecionar o card de **Competências Institucionais** do indicador de dívida e verificar a distinção clara entre proponente (Executivo), aprovador (Legislativo) e fiscalizador (TCU).

### Edge cases
- [ ] **Empty state:** Antes de disparar qualquer simulação customizada, a UI exibe os cenários canônicos padrão com convite claro à experimentação.
- [ ] **Valores extremos / Inviáveis:** Inserir juros excessivos ou crescimento nulo; a interface e a API validam limites sem travar o worker ou a interface.
- [ ] **Falha no worker / Timeout:** Se o worker demorar a processar, a interface exibe feedback adequado de processamento sem travar a navegação.

## Tone check (if user-facing copy exists)

- [ ] Textos e avisos seguem estritamente a neutralidade e o rigor exigidos em `specs/mission.md`.
- [ ] Nenhum juízo de valor ou aconselhamento financeiro/político presente na interface.
- [ ] Rótulo explícito de status `projected` / `hypothesis` em todos os resultados simulados.
- [ ] Nenhum texto de placeholder (`Lorem Ipsum` ou `TODO`) remanescente na UI.

## Definition of done

- [ ] Todas as verificações automatizadas passam (`pytest`, `go test`, `go vet`, `npm run build`).
- [ ] Manual walkthrough executado localmente com sucesso.
- [ ] Descrição de PR referencia o diretório de especificação `specs/2026-10-28-feat-dynamic-assumptions-institutional-metrics/`.
- [ ] Código versionado na branch `feat/dynamic-assumptions-institutional-metrics` pronto para revisão técnica independente.
