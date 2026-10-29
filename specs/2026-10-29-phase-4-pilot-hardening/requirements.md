# Requirements — Pilot Hardening & Operational Resilience (Incremento 04)

## Scope

**In scope:**
- **Autenticação OIDC Simulada e Controle de Acesso Baseado em Papéis (RBAC):**
  - Implementação de autenticação via tokens JWT / cabeçalhos compatíveis com OIDC (`Authorization: Bearer <token>` ou `X-Actor-Role`, `X-Actor-Id`).
  - Três papéis estritos com separação de deveres:
    1. `producer`: ingestão, submissão de dados brutos e simulações preliminares.
    2. `reviewer`: análise técnica, anotação de divergências e parecer metodológico.
    3. `publisher`: autorização de publicação de versões oficiais, relatórios de governança e disparo de replays de alta criticidade.
  - Bloqueio com HTTP 401 (Unauthorized) para ausência de credenciais e HTTP 403 (Forbidden) para violação de privilégios.
- **Trilha Imutável de Auditoria de Decisões (`decision_audit_log`):**
  - Persistência estruturada no PostgreSQL de todas as decisões humanas e sistêmicas materiais (aprovação de calibrações, marcação de alertas revisados, requisições de replay operacional).
  - Encadeamento de integridade criptográfica com hash SHA-256 do registro atual combinando o hash do registro anterior (`prev_log_hash`), impedindo adulterações retroativas.
- **Paginação Padronizada e Rate Limiting na API Go:**
  - Middleware de limitação de taxa (Token Bucket / Sliding Window in-memory) por IP / Actor ID com quotas diferenciadas por papel e retorno de cabeçalhos RFC (`X-RateLimit-Limit`, `X-RateLimit-Remaining`, `Retry-After`) e HTTP 429 (Too Many Requests).
  - Paginação consistente (`limit`, `offset`, cursor temporal, `total_count`, `has_more`) nos endpoints de listagem volumosos: `/v1/observations`, `/v1/proposals`, `/v1/alerts` e `/v1/admin/audit/decisions`.
- **Observabilidade dos Quatro Planos e Métricas de SLOs:**
  - Endpoint consolidado `GET /v1/observability/metrics` expondo telemetria estruturada dos 4 planos canônicos:
    1. *Plataforma:* uptime, taxa de erro, latência p95, uso de pool do banco.
    2. *Dados:* freshness em relação ao calendário, completude de séries, contagem de quarentena.
    3. *Modelos:* estabilidade de parâmetros, desvio de cenários, registro de calibrações ativas.
    4. *Decisões:* tempo médio de revisão, volume de alertas pendentes vs. resolvidos, log de auditoria recente.
- **Resiliência Operacional e Teste de Backup/Restore:**
  - Script determinístico `scripts/backup_restore_test.sh` para validação automatizada de backup lógico (`pg_dump`), restauração em banco temporário e verificação de checksums e contagens de tabelas fundamentais.
- **Interface e Painel de Monitoramento (Next.js):**
  - Componente `<ObservabilityPlanesPanel>` renderizando a saúde e os SLOs dos 4 planos em tempo real.
  - Componente `<DecisionAuditTrailModal>` permitindo a inspeção pública e auditável das decisões registradas.
  - Simulador de identidade `<RoleSwitcherBadge>` para demonstração interativa de permissões (Produtor, Revisor, Publicador).

**Out of scope:**
- Integração com provedor IAM comercial de produção externo (ex.: Okta, Auth0 enterprise) sem necessidade comprovada nesta fase piloto.
- Infraestrutura de cluster multi-região ou Kubernetes em nuvem (mantém-se Docker Compose determinístico).
- Modificação das políticas de neutralidade econômica ou ratificação automática de metas sem intervenção humana.

---

### Data / fields

#### Tabela `decision_audit_log`
| Field | Type | Required | Notes |
|---|---|---|---|
| `id` | `VARCHAR(64)` | Sim | Identificador único do log (PK, ex: `audit-dec-20261029-001`) |
| `event_id` | `VARCHAR(64)` | Não | Vínculo com evento do outbox ou gatilho |
| `actor_id` | `VARCHAR(64)` | Sim | Identificador do ator/usuário (ex: `user-analyst-01`, `system-worker`) |
| `actor_role` | `VARCHAR(32)` | Sim | Papel do ator (`producer`, `reviewer`, `publisher`) |
| `action` | `VARCHAR(64)` | Sim | Tipo de ação executada (ex: `approve_calibration`, `resolve_alert`, `trigger_replay`) |
| `entity_type` | `VARCHAR(64)` | Sim | Entidade alvo (`fiscal_calibration`, `alert`, `guidance_commitment`, `outbox`) |
| `entity_id` | `VARCHAR(64)` | Sim | ID da entidade alvo |
| `justification` | `TEXT` | Sim | Justificativa técnica ou metodológica documentada |
| `previous_state` | `JSONB` | Não | Snapshot do estado anterior à decisão |
| `new_state` | `JSONB` | Sim | Snapshot do novo estado homologado |
| `payload_hash` | `VARCHAR(64)` | Sim | SHA-256 do payload da ação para integridade |
| `prev_log_hash` | `VARCHAR(64)` | Sim | SHA-256 do registro anterior na cadeia de auditoria |
| `created_at` | `TIMESTAMPTZ` | Sim | Timestamp UTC exato da decisão |

#### Estrutura de Resposta Paginaçāo (`PaginationMeta`)
| Field | Type | Required | Notes |
|---|---|---|---|
| `limit` | `INTEGER` | Sim | Limite solicitado (padrão: 50, máx: 200) |
| `offset` | `INTEGER` | Sim | Deslocamento atual |
| `total` | `INTEGER` | Sim | Total de registros correspondentes |
| `has_more` | `BOOLEAN` | Sim | Indica existência de páginas subsequentes |
| `next_cursor` | `VARCHAR(128)`| Não | Cursor temporal opcional para paginação estável |

#### Estrutura de Resposta dos Quatro Planos (`ObservabilitySnapshot`)
| Field | Type | Required | Notes |
|---|---|---|---|
| `platform` | `OBJECT` | Sim | Uptime, database_status, error_rate_pct, p95_latency_ms |
| `data` | `OBJECT` | Sim | tracked_series_count, stale_series_count, last_ingestion_at, quarantine_count |
| `models` | `OBJECT` | Sim | active_scenarios_count, calibrated_parameters_count, last_simulation_at |
| `decisions` | `OBJECT` | Sim | total_decisions_count, pending_reviews_count, audit_chain_intact |

---

## Decisions

| Decision | Choice | Rationale |
|---|---|---|
| **Estratégia de Autenticação e RBAC** | Mock OIDC JWT / Headers com Middleware Go | Oferece a segurança arquitetural necessária sem adicionar dependências externas complexas para a execução local, permitindo alternar papéis transparentemente na UI e validar o desacoplamento de responsabilidades. |
| **Integridade da Auditoria** | Log Append-Only no PostgreSQL com Encadeamento de Hashes SHA-256 | Assegura que nenhum ator, mesmo com privilégios de banco, possa alterar registros históricos sem quebrar a cadeia de verificação de integridade, cumprindo o princípio constitucional de rastreabilidade. |
| **Rate Limiting** | Token Bucket / Sliding Window in-memory no serviço Go | Suficiente para a escala do piloto, sem exigir Redis ou proxies adicionais no docker-compose, mantendo latência inferior a 1ms e bloqueando rajadas de tráfego abusivas. |
| **Paginação da API** | Paginação híbrida (Limit/Offset com suporte a Cursor temporal) | Compatível com requisições simples de UI e estável contra inserções concorrentes em streams temporais de observações e logs de auditoria. |
| **Observabilidade dos 4 Planos** | Coletor unificado no Go expondo `/v1/observability/metrics` + painel visual | Reúne métricas de Plataforma, Dados, Modelos e Decisões em um único payload estruturado, facilitando o consumo pelo dashboard Next.js e ferramentas externas de monitoramento. |
| **Estratégia de Modelos e Subagentes** | Roteamento econômico conforme `docs/model-routing.md` | Delegar tarefas repetitivas, geração de testes de schema, fixtures e validação preliminar para subagentes rápidos (Flash/Flash Lite), reservando a coordenação de integridade e contratos para o agente principal. |

---

## Context

- **Tone:** Rigor técnico, governança estrita, transparência em auditoria e observabilidade (conforme `specs/mission.md` e `specs/governance.md`).
- **Stack constraints:** Go 1.22+ para middleware de autenticação, rate-limiting e agregação de métricas; PostgreSQL 16 para trilha append-only; Python 3.12+ para testes de integridade e scripts de resiliência; Next.js 16 para interface responsiva.
- **Existing patterns to follow:**
  - Migrações SQL numeradas (`db/005_audit_logs_and_security.sql`).
  - IDs canônicos prefixados (`audit-dec-*`, `user-*`).
  - Respostas JSON padronizadas com envelope `{ "data": ..., "meta": ... }`.
  - Códigos de erro semânticos HTTP (400, 401, 403, 404, 429, 500).
- **Open questions:**
  - Configuração futura do provedor OIDC real quando o projeto for implantado em ambiente governamental ou acadêmico compartilhado.
