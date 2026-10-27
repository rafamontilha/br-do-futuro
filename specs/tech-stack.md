# Tech Stack & Reference Architecture — Brasil do Futuro (V1.3)

**Status:** arquitetura-alvo proposta, implementação ainda não comprovada.

## Visão de camadas

```text
Experience & Decision
  Guidance | Observatório | Simulador | Alertas | Relatórios | API
                      ↕
Economic Intelligence
  Scenario Engine | Policy Evaluation | Forecast/Backtesting
  Opportunity Detection | AI Research Agents | Impact Analysis
                      ↕
Automation & Event Orchestration
  Source Schedules | Change Detection | Event Bus | Dependency Graph
  Selective Recalculation | Workflow | Human Review
                      ↕
Economic Data & Knowledge
  Indicator Catalog | Historical Time Series | Vintage Registry
  Provenance/Evidence Ledger | Scenario Registry | Model Registry
                      ↕
Source Integration
  IBGE | BCB | Tesouro | Ipea | MDIC | B3 | CVM | MTE | Outras
--------------------------------------------------------------
Cross-cutting: Security | Governance | Platform/Data/Model/Decision
Observability | Cost | Lineage | Audit | Backup & Recovery
```

## Princípio de funcionamento

Uma nova publicação oficial ou revisão histórica ativa ingestão e validação. Só após aceitação dos contratos de dados ela gera `EconomicIndicatorUpdated` ou `HistoricalSeriesRevised`. O grafo de dependências encontra métricas derivadas, modelos, cenários, guidance e relatórios afetados. Uma política de materialidade decide entre atualizar dados, recalcular silenciosamente, criar alerta ou requerer revisão humana. O pipeline mantém histórico de inputs, código, premissas, outputs e aprovações.

## Componentes e responsabilidades

| Componente | Contrato principal | Garantia esperada |
|---|---|---|
| Source Registry / Scheduler | origem, API, versão, calendário, janela e custo | não presumir atualização fora do calendário |
| Ingestion Connectors | captura idempotente, paginação, retries, checksum | reproduzir a captura original |
| Data Contract & Quality | schema, unidade, frequência, outliers, consistência | quarentena de dados inválidos |
| Historical Time Series | observação, período, vintage, publicação e coleta | nunca sobrescrever fatos históricos |
| Indicator Catalog | IDs canônicos, derivação, interpretação, fonte | sem métricas ambíguas |
| Evidence Ledger | proveniência, transformações e artefatos | trilha de auditoria verificável |
| Economic Event Bus | evento versionado após validação | entrega ao menos uma vez + consumidores idempotentes |
| Dependency Graph | arestas dados → modelos → cenários → metas | análise de impacto explicável |
| Scenario Engine | parâmetros, choques, bandas, versões e resultados | execução reprodutível |
| Forecast & Backtesting | métricas por horizonte e vintage | separar ex-ante de ex-post |
| Policy Impact Evaluation | desenho causal, contrafactual, limites | registrar incerteza e identificação |
| Opportunity Intelligence | sinal, hipótese, impacto, evidência, confiança | não promover sugestão a fato |
| Alert & Review Workflow | severidade, proprietário, SLA, evidência, decisão | aprovação auditável para mudanças materiais |
| Experience & Public API | consultas com data/vintage/método | indicar atualização e proveniência |

## Fluxo automatizado de evento

1. Registrar calendário de divulgação e estratégia (API, arquivo, scraping apenas quando autorizado).
2. Verificar atualização com `etag`, checksum, versão ou comparação de período; aceitar revisão retroativa.
3. Armazenar payload bruto e metadados de captura sem alteração.
4. Validar contratos, classificações, sazonalidade, unidade, lacunas e mudanças metodológicas.
5. Persistir uma **nova vintage** e emitir evento somente após commit consistente.
6. Consultar grafo de dependências e produzir plano de recálculo seletivo com justificativa.
7. Executar cenários afetados de forma determinística quando possível; registrar versões de modelo, dados e parâmetros.
8. Comparar outputs novos versus anteriores; pontuar impacto, sensibilidade, risco e materialidade.
9. Atualizar visualizações de observação automaticamente; solicitar aprovação humana para recomendações materiais e versões oficiais do Guidance.
10. Publicar evidência, alerta (quando cabível), trilha de decisão e métricas de ciclo.

### Eventos de referência

```json
{
  "event_type": "EconomicIndicatorUpdated",
  "event_version": 1,
  "event_id": "uuid",
  "indicator_id": "br.ipca.12m",
  "reference_period": "YYYY-MM",
  "vintage_id": "source-published-at:hash",
  "published_at": "ISO-8601",
  "ingested_at": "ISO-8601",
  "data_quality_status": "verified",
  "provenance_ref": "evidence-id",
  "correlation_id": "uuid"
}
```

Outros eventos: `HistoricalSeriesRevised`, `DataQualityFailed`, `ScenarioRecalculationRequested`, `ScenarioRecalculated`, `ScenarioImpactDetected`, `MaterialReviewRequired`, `GuidanceRevisionPublished`, `OpportunityIdentified`.

## Observabilidade obrigatória: quatro planos

**Plataforma:** SLI de disponibilidade, taxa de erros, latência p95, filas, retries, execução de jobs, latência de ingestão, saturação, custo por execução, recuperação e segurança. Instrumentação de métricas, logs estruturados, traces e correlation IDs.

**Dados:** freshness *relativa à próxima publicação esperada*, completude por série/período, drift de esquema, anomalias, revisões, proveniência, confiabilidade da origem, cobertura de calendário e qualidade de contratos. Censo e cotação diária exigem SLOs diferentes.

**Modelos:** erro de previsão por horizonte/vintage (MAE, RMSE e métricas apropriadas), viés, cobertura dos intervalos, mudanças de distribuição, sensibilidade, estabilidade, degradação e resultado de backtests comparados a benchmarks simples.

**Decisões:** número de cenários afetados, tempo publicação → observação → análise → decisão, alertas úteis/falsos positivos, oportunidades verificadas, frequência de revisão humana, adoção e resultados posteriores das recomendações. Atribuição causal permanece questão metodológica separada.

### SLOs candidatos para piloto (a validar)

- ≥ 99% das execuções prioritárias concluídas dentro da janela de fonte definida.
- 100% dos indicadores públicos com fonte, unidade, período, vintage e metodologia.
- 100% dos cenários publicados com dependências, versão de modelo e parâmetros.
- 100% dos modelos preditivos publicados com avaliação ex-ante/backtest documentado.
- Disponibilidade, RTO/RPO, tempo de detecção e latência máximos serão definidos após medir cargas, criticidade e custos reais.

## Segurança, risco e continuidade

OIDC para identidade; RBAC/ABAC para ações; separação entre produtor, revisor e publicador; secret manager; criptografia em trânsito e repouso; logs de auditoria imutáveis; least privilege; backup testado; classificação e minimização de dados pessoais (LGPD); rate limiting e controle de custos. Conteúdo de terceiros/LLM não executa instruções operacionais sem autorização. Resultados de agentes são material de apoio, sujeitos à verificação de fontes.

## Stack candidata e momento de adoção

| Capacidade | Opção inicial | Evolução condicionada |
|---|---|---|
| Integração | Python, requests, Pandas/Polars | conectores gerenciados conforme escala |
| API e serviços | Go + OpenAPI | serviços separados quando necessário |
| Web | Next.js/React | acessibilidade e internacionalização |
| Persistência | PostgreSQL + objetos versionados | TimescaleDB se séries justificarem |
| Orquestração | agendador simples + jobs auditados | Dagster ou Prefect |
| Eventos | outbox transacional + fila simples | NATS JetStream; Kafka se volume exigir |
| Dependências | tabelas relacionais e DAG | grafo dedicado só se necessário |
| Econometria | Python: statsmodels, scipy | modelos especializados com validação |
| Model tracking | artefatos/metadata versionados | MLflow |
| Qualidade / lineage | testes declarativos e manifestos | Soda/Great Expectations, OpenLineage |
| Instrumentação | OpenTelemetry | padrão para integração |
| Observabilidade | Prometheus/Grafana + logs | Loki, Tempo, Alertmanager |
| Model monitoring | backtests próprios | Evidently se conveniente |
| Infraestrutura | Docker e pipeline CI | cloud/Kubernetes com necessidade demonstrada |

A tabela contém **candidatos**, não afirma implementação, contratos vigentes ou homologação.

## Operação e FinOps

Todo job tem owner, frequência, calendário, idempotency key, custo estimado, prioridade, políticas de retry/dead-letter, modo replay e runbook. Recalcular somente nós materialmente afetados, com cache por hashes de dados, código e premissas; permitir *full recomputation* de auditoria. Alertas precisam de deduplicação, supressão por janelas, escalonamento, incidentes e retrospectivas.

## Critérios de saída da primeira implantação

Pipeline ponta a ponta para 3–5 indicadores: detecção de publicação, vintage, avaliação de qualidade, evento, dependência, recálculo seletivo, alerta, aprovação, atualização de painel, trilha auditável e teste de replay. Nenhum painel pode rotular dados locais antigos como “mais recentes” sem verificar a fonte no momento apropriado.

## ADRs relacionados

0003, 0004, 0005, 0006, 0008, 0009, 0010, 0011, 0012, 0013, 0014, 0015 e 0016.
