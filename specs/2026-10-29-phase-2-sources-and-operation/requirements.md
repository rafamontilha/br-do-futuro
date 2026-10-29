# Requirements — Sources, Freshness & Operational Replay (Incremento 02)

## Scope

**In scope:**
- **Conector Primário IBGE/SIDRA:** Implementação de conector direto para o IPCA (`br.ipca.monthly`) via API SIDRA do IBGE (Tabela 1737 / Série 2265 ou API Agregados), validando contrato de dados primário, preservando raw payload bytea SHA-256 e mantendo BCB SGS como conector secundário de fallback/auditoria comparativa.
- **Tabela de Agendamentos e Calendário Oficial (`source_schedules`):** Modelagem de calendário de divulgação oficial (frequência, dia/hora esperada de publicação, janela de tolerância e fuso horário).
- **Métricas de Freshness Persistidas:** Registro e cálculo contínuo de freshness com base no calendário oficial (`is_stale`, `next_expected_at`, `delay_hours`, `last_successful_ingestion_at`, `slo_status`).
- **Mecanismo de Replay Operacional de Outbox:** Ordenação rigorosa por timestamp/versão, controle de concorrência com idempotência, e capacidade de replay seletivo ou em lote para reprocessamento de eventos com falhas ou recálculo retrospectivo de cenários.
- **Circuit Breaker & Backoff no Worker:** Tratamento de falhas transitórias com backoff exponencial decorrelacionado e registro estruturado de metadados de erro (`failure_reason`, `retry_count`, `circuit_open`).
- **API Go de Saúde Operacional & Replay:** Endpoints `GET /api/v1/health/sources` (status de freshness e SLA de cada série) e `POST /api/v1/admin/outbox/replay` (disparo auditável de reprocessamento com `replay_reason`).
- **Painel de Saúde Operacional & Freshness (Next.js):** Seção no dashboard exibindo status de coleta, conformidade com calendário de divulgação, defasagem em horas e acionamento de replay com confirmação auditada.

**Out of scope:**
- Coleta de dados via web scraping não autorizado ou parse de HTML não documentado.
- Reconstrução de vintages históricas anteriores à implantação do sistema que não existam nas fontes oficiais.
- Expansão de novos indicadores além do núcleo P0 demonstrador já estabelecido.
- Automação não supervisionada de publicação de relatórios ou alteração de metas institucionais.
- Integração com sistemas de filas distribuídas de terceiros (Kafka, RabbitMQ) ou orquestradores pesados externos (Airflow gerenciado), preservando a simplicidade do modelo outbox relacional com PostgreSQL.

### Data / fields

#### Tabela `source_schedules`
| Field | Type | Required | Notes |
|---|---|---|---|
| `id` | `UUID` | Sim | Identificador único do agendamento (PK) |
| `indicator_id` | `VARCHAR(64)` | Sim | FK para `economic_indicators.id` |
| `primary_source` | `VARCHAR(32)` | Sim | Nome da fonte primária (ex: `IBGE_SIDRA`) |
| `fallback_source` | `VARCHAR(32)` | Não | Nome da fonte de contingência (ex: `BCB_SGS`) |
| `cron_expression` | `VARCHAR(64)` | Sim | Expressão cron de agendamento de verificação |
| `expected_release_day_offset` | `INTEGER` | Sim | Dias após término do período de referência para divulgação esperada |
| `expected_release_time` | `TIME` | Sim | Horário de Brasília esperado da divulgação |
| `tolerance_window_hours` | `INTEGER` | Sim | Janela de tolerância antes de marcar como atrasado (`is_stale`) |
| `last_checked_at` | `TIMESTAMPTZ` | Não | Timestamp da última verificação da fonte |
| `last_successful_at` | `TIMESTAMPTZ` | Não | Timestamp do último sucesso de ingestão |
| `next_expected_at` | `TIMESTAMPTZ` | Sim | Próxima divulgação oficial calculada |
| `is_stale` | `BOOLEAN` | Sim | Indicador se o dado ultrapassou a janela de tolerância |
| `current_delay_hours` | `NUMERIC(8,2)`| Sim | Horas de atraso em relação ao momento esperado |
| `consecutive_failures` | `INTEGER` | Sim | Contador de falhas consecutivas para circuit breaker |
| `circuit_open` | `BOOLEAN` | Sim | Se o circuit breaker está aberto impedindo chamadas automáticas |
| `metadata` | `JSONB` | Sim | Metadados de configuração e documentação da fonte |
| `created_at` | `TIMESTAMPTZ` | Sim | Data de criação do registro |
| `updated_at` | `TIMESTAMPTZ` | Sim | Data da última atualização de status |

#### Tabela `outbox_replay_audit`
| Field | Type | Required | Notes |
|---|---|---|---|
| `id` | `UUID` | Sim | Identificador único do replay (PK) |
| `triggered_by` | `VARCHAR(64)` | Sim | Identidade do operador ou sistema solicitante |
| `filter_event_type` | `VARCHAR(64)` | Não | Tipo de evento filtrado para replay (ou `ALL`) |
| `filter_indicator_id` | `VARCHAR(64)` | Não | Indicador filtrado para replay |
| `events_replayed_count` | `INTEGER` | Sim | Quantidade de eventos reprocessados |
| `reason` | `TEXT` | Sim | Justificativa do replay operacional para auditoria |
| `status` | `VARCHAR(32)` | Sim | `pending`, `running`, `completed`, `failed` |
| `created_at` | `TIMESTAMPTZ` | Sim | Data e hora do acionamento |
| `completed_at` | `TIMESTAMPTZ` | Não | Data e hora da conclusão |

## Decisions

| Decision | Choice | Rationale |
|---|---|---|
| **Estratégia de Fonte do IPCA** | Primária: IBGE/SIDRA API; Secundária: BCB/SGS API | O IBGE é o produtor oficial do IPCA. Usar a fonte primária elimina atrasos de redistribuição pelo BCB e garante adesão ao calendário oficial, mantendo o SGS como backup auditável. |
| **Persistência de Freshness** | Tabela dedicada `source_schedules` com gatilhos/worker de atualização | Permite consultas ultrarrápidas de observabilidade pela API Go sem scan contínuo em tabelas de séries e observações brutas. |
| **Tratamento de Falhas e Tolerância** | Circuit Breaker em software + backoff exponencial | Evita sobrecarregar APIs governamentais durante períodos de indisponibilidade ou manutenção oficial. |
| **Garantia de Replay da Outbox** | Replay via status transition (`failed` ou `processed` -> `replay_pending`) com locking seletivo | Preserva a integridade relacional do PostgreSQL e garante consumo idempotente por meio do deduplication hash já existente. |
| **Interface e Acessibilidade** | Componente `<SourceFreshnessPanel>` e modal de confirmação de Replay | Permite que operadores e pesquisadores auditem visualmente a atualidade das fontes e o cumprimento de SLOs sem depender de logs de terminal. |

## Context

- **Tone:** Estritamente neutro, técnico e focado na verificação de fatos e cumprimento de contratos de dados (conforme `specs/mission.md`).
- **Stack constraints:** Python 3.12+ para ingestão e workers assíncronos, PostgreSQL 16 para armazenamento transacional/ledger, Go 1.22+ para serviço de leitura e despacho de replay de alta performance, Next.js (App Router) + Tailwind CSS para apresentação web.
- **Existing patterns to follow:**
  - Migrações SQL numeradas sequencialmente em `db/` (`003_source_schedules_and_replay.sql`).
  - Hash SHA-256 do payload bruto e idempotência via `bytea` append-only.
  - Endpoints REST Go com validação de payload, CORS, JSON estruturado e testes com `net/http/httptest`.
  - Tratamento de incerteza e separação clara entre dados oficiais e projeções sintéticas.
- **Open questions:**
  - Janela de tolerância recomendada para o IPCA no dia de divulgação (sugerido: 4 horas após horário oficial previsto das 09:00).
  - Necessidade de autenticação OIDC completa para a rota de replay ou token de serviço operacional pré-compartilhado na Fase 0 (adotar token operacional de cabeçalho `X-BDF-Operator-Token` nesta etapa).
