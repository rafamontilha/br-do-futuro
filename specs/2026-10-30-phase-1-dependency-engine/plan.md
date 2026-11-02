# Plan — Phase 1: Motor de Dependências e Recálculo Seletivo; Workflow de Revisão Humana para Impactos Materiais

## Summary

Implementar o grafo formal de dependências econômicas (DAG) conectando as séries prioritárias P0 a modelos, cenários fiscais e metas institucionais, com capacidade de recálculo seletivo explicável e avaliação de materialidade em múltiplos níveis. Desenvolver o workflow completo de revisão humana para impactos materiais através da API Go (com autenticação por chave de API e registro na trilha imutável de auditoria) e de uma interface interativa no Observatório Econômico (Next.js), garantindo que nenhuma projeção com impacto material relevante seja publicada sem validação humana independente.

## Architecture / Design

```text
[ Atualização de Indicador P0 / Revisão Histórica ]
                       │
                       ▼
    [ PostgreSQL Outbox: EconomicIndicatorUpdated ]
                       │
                       ▼
       [ Python Worker: Dependency Engine ]
         1. Carrega DAG de Dependências (Nós & Arestas)
         2. Ordenação Topológica: Identifica Nós a Jusante
         3. Gera Plano de Recálculo Seletivo (Recalculation Plan)
         4. Executa Cenários Afetados com Hashes de Entrada
         5. Avalia Regra de Materialidade (Delta >= limiar OU Target Breach)
                       │
             ┌─────────┴─────────┐
             │                   │
    (Abaixo do Limiar)    (Impacto Material Detectado)
             │                   │
             ▼                   ▼
    Atualização Direta    Emite 'MaterialReviewRequired'
    Silenciosa no Banco   Cria Alerta (status='pending_human_review')
                          Bloqueia Publicação Material (SLA 48h)
                                 │
                                 ▼
                     [ Go API: services/api/ ]
                       - GET /v1/dependencies
                       - GET /v1/alerts?review_status=pending_human_review
                       - POST /v1/alerts/{id}/review (Auth: reviewer/publisher)
                                 │
                                 ▼
                     [ Trilha de Decisão Imutável ]
                       - Grava em decision_audit_log (Hash SHA-256 encadeado)
                       - Atualiza alert.review_status ('approved'/'rejected')
                                 │
                                 ▼
                     [ Next.js Web Application ]
                       - Painel de Revisão Humana Interativo
                       - Visualizador do DAG de Dependências
                       - Formulário de Justificativa e Ações de Aprovação
```

## Task Groups

### 1. Data Layer & Database Migrations
1.1. Criar migração SQL `db/008_dependency_engine_and_reviews.sql` definindo:
     - Tabela `dependency_graph_nodes` (id, node_type, canonical_name, description).
     - Tabela `dependency_graph_edges` (id, source_node_id, target_node_id, relationship_type, materiality_rule, threshold_value).
     - Atualização da tabela `alert` com colunas: `reviewed_by`, `review_justification`, `reviewed_at`, e constraints de integridade para `review_status`.
     - Tabela `recalculation_plan` (id, event_id, affected_nodes, rationale, created_at, execution_status).
1.2. Inserir sementes canônicas dos nós do DAG conectando os 6 indicadores P0 (`br.debt.gross_pct_gdp`, `br.ipca.12m`, `br.selic.target_annual`, `br.gdp.quarterly_yoy`, `br.fx.usd_brl.ptax`, `br.labor.unemployment_rate`) aos cenários fiscais (`continuity`, `alternative`, `adverse`), simulações dinâmicas e metas do Guidance 2027–2030.
1.3. Conceder permissões para o role `bdf_reader` e garantir execução idempotente em `bdf` e `bdf_test`.

### 2. Python Worker & Dependency Engine
2.1. Implementar módulo `ingestion/bdf/dependency_engine.py`:
     - Leitura e representação do DAG em memória a partir do banco de dados.
     - Algoritmo de busca e ordenação topológica para identificar caminhos de impacto a jusante a partir de um indicador alterado.
     - Geração do plano de recálculo seletivo com deduplicação de nós.
2.2. Implementar avaliador de regras de materialidade em `ingestion/bdf/materiality.py`:
     - Cálculo de $\Delta$ absoluto nas trajetórias do modelo.
     - Checagem de violação de metas oficiais cadastradas (`target breach`).
     - Emissão condicional de alerta de impacto material (`MaterialReviewRequired`) com SLA de 48h e bloqueio de publicação.
2.3. Integrar o `dependency_engine` ao processamento de eventos do `ingestion/bdf/worker.py` para substituir o dicionário estático anterior por resolução dinâmica de dependências.

### 3. Go API Backend
3.1. Criar `services/api/dependencies.go` implementando o repositório e o handler HTTP para `GET /v1/dependencies`:
     - Retorna os nós e arestas do DAG de dependências econômicas com metadados de materialidade.
3.2. Atualizar o handler de `GET /v1/alerts` em `services/api/main.go` para suportar filtros por `review_status` (`pending_human_review`, `approved`, `rejected`), severidade e limite de paginação.
3.3. Implementar handler `POST /v1/alerts/{id}/review` em `services/api/alerts_review.go`:
     - Validação de autorização via chave de API (requer papéis `reviewer` ou `publisher`).
     - Validação da ação (`approve`, `reject`) e exigência de justificativa técnica formal ($\ge 15$ caracteres).
     - Atualização atômica do status do alerta no banco e inserção na trilha imutável `decision_audit_log` com recálculo do encadeamento criptográfico de hash SHA-256.
3.4. Adicionar testes unitários e de integração em `services/api/main_test.go` cobrindo o fluxo de dependências, filtros de alerta e workflow de aprovação/rejeição com auditoria.

### 4. Frontend Web (Next.js & TypeScript)
4.1. Criar componente `web/app/components/DependencyGraphVisualizer.tsx`:
     - Visualização interativa e responsiva do DAG econômico com nós categorizados (Indicadores P0 em azul, Modelos/Cenários em roxo, Metas em verde) e conexões direcionadas com indicação de limiar.
4.2. Criar componente `web/app/components/HumanReviewWorkflowModal.tsx`:
     - Modal com lista de alertas pendentes, detalhes da evidência ($\Delta$ p.p., ruptura de meta, SLA de 48h em contagem regressiva).
     - Formulário para registrar decisão com seleção de ação (Aprovar / Rejeitar), campo de justificativa obrigatório e envio autenticado via chave de API selecionada no `RoleSwitcherBadge`.
4.3. Atualizar a seção de "Revisão humana" em `web/app/page.tsx`:
     - Exibição de cards informativos para cada alerta pendente e histórico recente de decisões com status ("Pendente de Revisão", "Aprovado por Revisor Independente", "Rejeitado").
     - Botão de ação para abrir o modal de revisão humana e botão para inspecionar o grafo de dependências.

### 5. Automated Tests & End-to-End Verification
5.1. Desenvolver testes Python em `tests/test_dependency_engine.py`:
     - Testes de ordenação topológica do DAG e cálculo seletivo.
     - Testes das regras de materialidade (variação acima do limiar e violação de meta).
     - Teste de idempotência e não recálculo de ramos independentes.
5.2. Atualizar `scripts/smoke.py` para validar os novos endpoints `/v1/dependencies` e `/v1/alerts/{id}/review`.
5.3. Executar suíte de validação completa: `pytest`, `go test ./...`, `go vet ./...` e `npm run build`.
