# Validation — Phase 1: Motor de Dependências e Recálculo Seletivo; Workflow de Revisão Humana para Impactos Materiais

## Automated

- [x] `pytest tests/test_dependency_engine.py` e testes de regressão do worker executam com sucesso (121 testes passam).
- [x] `go test -v ./...` e `go vet ./...` no diretório `services/api` executam sem falhas.
- [x] `npm run build` e `npm run typecheck` no diretório `web` concluem sem erros de tipagem TypeScript ou de lint.
- [x] `git diff --check` não acusa espaços em branco espúrios ou inconsistências de formatação.
- [x] `python scripts/smoke.py` valida as rotas `/v1/dependencies`, `/v1/alerts` e a operação de revisão.

### Key assertions

| Behaviour | Test type | Expected result |
|-----------|-----------|-----------------|
| `GET /v1/dependencies` | integration (Go) | Retorna status 200 com array de nós (nodes) e arestas (edges) do DAG macroeconômico |
| Resolução de DAG do Worker | unit / integration (Python) | Atualização de indicador dispara recálculo somente dos cenários dependentes, gerando `recalculation_plan` |
| Regra de Materialidade ($\Delta \ge 0,5$ p.p.) | unit (Python) | Cria alerta de severidade `material`, atribuição ao `Independent Reviewer` e bloqueio de publicação |
| Regra de Ruptura de Meta (`target_breach`) | unit (Python) | Identifica quando a trajetória cruza a tolerância da meta oficial e emite `MaterialReviewRequired` |
| `POST /v1/alerts/{id}/review` com chave inválida/produtor | integration (Go) | Retorna 403 Forbidden ("role unauthorized: reviewer or publisher required") |
| `POST /v1/alerts/{id}/review` com justificativa curta | integration (Go) | Retorna 400 Bad Request exigindo justificativa com $\ge 15$ caracteres |
| `POST /v1/alerts/{id}/review` com chave de reviewer | integration (Go) | Retorna 200 OK, atualiza `review_status` para `approved` e insere registro na cadeia de `decision_audit_log` |
| Encadeamento de Hash do Audit Log | integration (Python / Go) | Garante que `prev_log_hash` do novo registro de auditoria é estritamente igual ao hash do registro anterior |

## Manual walkthrough

1. Iniciar os serviços com Docker Compose (`docker compose up -d`) ou localmente com PostgreSQL ativo.
2. Acessar `http://localhost:3000` e navegar até a seção "Revisão humana" no Observatório.
3. Clicar no botão **"Grafo de Dependências"** e inspecionar a visualização do DAG:
   - Verificar as conexões partindo dos indicadores P0 até os cenários e metas do Guidance.
   - Observar a anotação dos limiares de materialidade em cada aresta.
4. Identificar na lista um alerta pendente de revisão ("Impacto material: X p.p. — Aguardando revisão humana").
5. Clicar no botão **"Revisar Alerta"**:
   - Inspecionar a evidência completa exibida no modal (indicador afetado, delta percentual, meta violada, SLA de 48h).
   - Tentar submeter aprovação com justificativa em branco ou menor que 15 caracteres e constatar a validação imediata.
   - Selecionar o papel `Revisor Metodológico Independente` (ou inserir chave de reviewer).
   - Preencher justificativa técnica fundamentada (ex.: "Revisão metodológica concluída; desvio consistente com choque exógeno de commodities").
   - Submeter a aprovação.
6. Constatar a atualização imediata do card do alerta para "Aprovado por Revisor Independente" com badge verde e registro do carimbo temporal.
7. Abrir o modal **"Trilha de Auditoria"** na barra superior e verificar a inclusão do novo evento de auditoria com hash SHA-256 encadeado e justificativa gravada.

### Edge cases

- [ ] **Tentativa de aprovação por produtor de dados:** Chave com papel `producer` não pode autorizar liberação de alerta de impacto material.
- [ ] **Alerta já revisado:** Tentativa de revisar novamente um alerta com status `approved` ou `rejected` deve retornar conflito (409 Conflict) ou supersedes explícito.
- [ ] **Grafo com nós desconectados:** Indicadores P0 sem modelos dependentes vinculados não devem gerar planos vazios com erro nem travar o worker.

## Tone check (specs/mission.md)

- [ ] Todas as justificativas e textos de alerta são puramente técnicos, descritivos e baseados em grandezas objetivas.
- [ ] O visualizador do DAG e os cards de alerta explicam as limitações metodológicas ("Hipótese fiscal ilustrativa").
- [ ] Nenhuma menção a julgamentos políticos ou partisanismos.

## Definition of done

- [ ] Todos os testes automatizados (pytest, go test, npm build, smoke.py) passam com 100% de sucesso.
- [ ] Migração `db/008_dependency_engine_and_reviews.sql` executada e testada no banco `bdf_test`.
- [ ] Walkthrough manual completo demonstrando a identificação do impacto, aprovação/rejeição e registro na auditoria.
- [ ] Documentação e roadmap atualizados conforme as diretrizes do projeto.
