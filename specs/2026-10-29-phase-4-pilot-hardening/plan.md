# Plan — Pilot Hardening & Operational Resilience (Incremento 04)

## Task groups

### 1. Data layer
1.1. Criar migração SQL `db/005_audit_logs_and_security.sql` definindo a tabela `decision_audit_log` (com constraints de integridade, campos para payload_hash, prev_log_hash, índices por `entity_type`, `created_at` e `actor_role`) e tabela `system_api_keys` com vinculação a papéis (`producer`, `reviewer`, `publisher`).
1.2. Inserir sementes iniciais com chaves de API/atores canônicos de teste para os três papéis e um registro gênese de auditoria (`audit-genesis-0000`).
1.3. Desenvolver script de resiliência e validação `scripts/backup_restore_test.sh` que executa `pg_dump`, simula restauração em banco temporário, checa a integridade das tabelas e calcula checksums dos dados.

### 2. Go API: Security Middleware, Pagination & Observability
2.1. Implementar middleware de autenticação e RBAC em `services/api/auth.go`:
   - Extração de credenciais via `Authorization: Bearer <token>` ou cabeçalhos de contexto de teste `X-Actor-Role` e `X-Actor-Id`.
   - Validação dos papéis `producer`, `reviewer` e `publisher`.
   - Retorno padronizado de HTTP 401 para requisições não autenticadas em rotas protegidas e HTTP 403 para permissões insuficientes.
2.2. Implementar middleware de Rate Limiting em `services/api/ratelimit.go`:
   - Algoritmo Token Bucket / Sliding Window in-memory indexado por IP / Actor ID.
   - Headers informativos `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `Retry-After`.
   - Retorno de HTTP 429 Too Many Requests quando a cota configurada for excedida.
2.3. Implementar helper de paginação e aplicar nos endpoints de listagem existentes:
   - Suporte a `limit` (default 50, max 200) e `offset` ou `cursor`.
   - Atualizar `/v1/observations`, `/v1/proposals`, `/v1/alerts` para retornar metadados de paginação padronizados em `meta.pagination`.
2.4. Implementar endpoints de Auditoria de Decisões e Observabilidade em `services/api/main.go`:
   - `GET /v1/admin/audit/decisions`: listagem paginada da trilha de auditoria com filtro por ator e tipo de entidade (requer papel `reviewer` ou `publisher`).
   - `POST /v1/admin/audit/decisions`: registro de nova decisão auditável com cálculo automático de SHA-256 e validação de cadeia de hash (requer papel `reviewer` ou `publisher`).
   - `GET /v1/observability/metrics`: sumário consolidado dos quatro planos de observabilidade (Plataforma, Dados, Modelos, Decisões) com indicadores de SLO.

### 3. Components / UI
3.1. Criar componente `<ObservabilityPlanesPanel>` em `web/app/components/ObservabilityPlanesPanel.tsx` apresentando a saúde dos 4 planos (Plataforma, Dados, Modelos, Decisões) com status visual (verde, amarelo, vermelho) e métricas de SLO.
3.2. Criar componente `<DecisionAuditTrailModal>` em `web/app/components/DecisionAuditTrailModal.tsx` para exibição e conferência da cadeia imutável de decisões de governança, indicando ator, justificativa e hash de integridade.
3.3. Criar componente `<RoleSwitcherBadge>` em `web/app/components/RoleSwitcherBadge.tsx` permitindo ao usuário alternar interativamente entre a visão de `Público`, `Produtor`, `Revisor` e `Publicador` para demonstrar o controle de acesso e auditoria.
3.4. Integrar o painel de observabilidade e a barra de governança na página principal em `web/app/page.tsx`.

### 4. Navigation / integration
4.1. Atualizar especificação OpenAPI em `docs/openapi.yaml` documentando o esquema de autenticação (SecuritySchemes), os novos endpoints `/v1/admin/audit/decisions`, `/v1/observability/metrics` e os parâmetros de paginação e rate limiting.
4.2. Atualizar script de fumaça `scripts/smoke.py` com testes de:
   - Rejeição não autenticada (401) e autorização por papel (403 vs 200/201).
   - Verificação de rate limiting (disparo rápido gerando 429 e cabeçalho `Retry-After`).
   - Paginação com `limit`, `offset` e `has_more`.
   - Consulta e integridade dos endpoints de auditoria e métricas dos 4 planos.

### 5. Tests & Verification (Otimização de Custo com Subagentes)
5.1. Invocar subagente com modelo `flash` para gerar casos de teste unitários Python em `tests/test_audit_integrity.py` validando integridade de hash SHA-256 e encadeamento da cadeia de auditoria.
5.2. Invocar subagente com modelo `flash` para testes de schema de métricas em `tests/test_observability_metrics.py`.
5.3. Implementar testes de integração Go em `services/api/main_test.go` cobrindo o middleware RBAC, rate limiting, endpoints de auditoria e paginação.
5.4. Executar verificação determinística completa do ecossistema: `pytest`, `go test ./...`, `go vet ./...`, `npm run build` e typecheck do Next.js.
