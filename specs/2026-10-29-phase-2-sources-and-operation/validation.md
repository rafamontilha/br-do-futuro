# Validation — Sources, Freshness & Operational Replay (Incremento 02)

## Automated

- [x] `pytest tests/` passa com PostgreSQL real sem testes pulados
- [x] `go test ./...` e `go vet ./...` no diretório `services/api` passam sem avisos ou erros
- [x] `npm run build` e typecheck no diretório `web/` passam limpos sem erros
- [ ] `python3 scripts/smoke.py` valida com sucesso a API local e os novos endpoints de saúde e replay
- [x] Novos testes cobrem:
  - Parse de payload real e sintético do conector IBGE/SIDRA com validação de unidade percentual
  - Cálculo de freshness (`is_stale`, `current_delay_hours`) relativo ao horário esperado oficial
  - Disparo e rejeição de replay de outbox por falta de justificativa auditável
  - Abertura de circuit breaker após 3 falhas consecutivas e fallback para BCB SGS quando configurado

### Key assertions
| Behaviour | Test type | Expected result |
|---|---|---|
| Ingestão IBGE SIDRA IPCA | Unit (Python) | Payload bruto parseado, SHA-256 gerado, registro append-only persistido |
| Cálculo de Freshness | Unit (Python) | Data corrente anterior à tolerância retorna `is_stale=False`; posterior retorna `is_stale=True` |
| Circuit Breaker | Unit (Python) | 3 falhas seguidas ativam `circuit_open=True` e acionam conector de fallback |
| Consulta de Saúde das Fontes | Integration (Go) | `GET /api/v1/health/sources` retorna HTTP 200 com array de agendamentos e status de SLA |
| Replay de Outbox sem Justificativa | Integration (Go) | `POST /api/v1/admin/outbox/replay` com `reason=""` retorna HTTP 400 Bad Request |
| Replay de Outbox com Justificativa | Integration (Go) | `POST /api/v1/admin/outbox/replay` retorna HTTP 202 Accepted com `replay_id` e auditoria gravada |

## Manual walkthrough

1. Iniciar o ambiente completo via Docker Compose (`docker compose up -d --build`).
2. Acessar a interface web no navegador (`http://localhost:3000`).
3. Navegar até a nova seção **Saúde Operacional & Freshness das Fontes**.
4. Inspecionar o card do indicador **IPCA (Mensal)**:
   - Verificar a exibição da fonte primária (`IBGE/SIDRA`) e secundária (`BCB/SGS`).
   - Conferir o horário da última coleta e a data da próxima divulgação oficial esperada.
   - Observar o indicador de SLA (`EM DIA` ou `ATENÇÃO`).
5. Clicar no botão **"Replay Operacional"** para abrir o modal de reprocessamento.
6. Tentar submeter o formulário sem preencher a justificativa; verificar se a interface impede a submissão e exige justificativa para auditoria.
7. Preencher a justificativa (ex: `"Teste de validação de replay operacional pós-ajuste de conector"`) e confirmar o disparo.
8. Observar a confirmação com o identificador de auditoria retornado e verificar a atualização do status na tela.

### Edge cases
- [ ] **Indisponibilidade temporária da API IBGE:** Se a API SIDRA falhar ou retornar timeout, o worker registra falha estruturada, preserva o estado de consistência e tenta a fonte de contingência (BCB).
- [ ] **Disparo concorrente de replay:** Dois disparos de replay simultâneos para o mesmo indicador não geram duplicação de eventos devido à cláusula `SKIP LOCKED` e deduplication hash na outbox.
- [ ] **Horário de divulgação em final de semana ou feriado:** O agendador computa dias úteis oficiais conforme o calendário nacional do IBGE/BCB.

## Tone check (if user-facing copy exists)

- [x] Textos e avisos seguem estritamente a neutralidade e o rigor exigidos em `specs/mission.md`.
- [x] A terminologia de status operacional é clara e objetiva (`Normal`, `Alerta de Latência`, `Degradado`, `Replay Auditado`).
- [x] Nenhum texto de placeholder (`Lorem Ipsum` ou `TODO`) remanescente na UI.

## Definition of done

- [ ] Todas as verificações automatizadas passam (`pytest`, `go test`, `go vet`, `npm run build`, `smoke.py`).
- [ ] Manual walkthrough executado localmente com sucesso.
- [ ] Descrição de PR referencia o diretório de especificação `specs/2026-10-29-phase-2-sources-and-operation/`.
- [ ] Código versionado na branch `phase-2-sources-and-operation` pronto para revisão técnica independente.
