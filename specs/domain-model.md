# Domain Model — Brasil do Futuro (V1.3)

## Bounded contexts

1. **Economic Observation:** fontes, indicadores, observações, vintage e qualidade.
2. **Economic Context:** setores, regiões, mercados, choques e ciclos.
3. **Policy & Institutional Responsibility:** propostas, instrumentos, custos, competências e implementação.
4. **Scenario & Forecasting:** modelo, parâmetros, simulação, forecast, intervalo, benchmark e comparação.
5. **Guidance & Accountability:** compromisso, target, actual, revisão, avaliação e justificativa.
6. **Monitoring & Opportunity:** evento, dependência, materialidade, alerta, oportunidade, revisão humana.
7. **Audit & Governance:** evidência, decisão, aprovação, usuário, permissão, observabilidade e custo.

## Entidades canônicas

| Entidade | Identidade e atributos centrais |
|---|---|
| `DataSource` | id, mantenedor, endpoint, licença, calendário, disponibilidade |
| `Indicator` | id, nome, definição, unidade, frequência, cobertura, ajuste sazonal, fonte |
| `Observation` | indicator_id, reference_period, value, unit, geography, vintage_id |
| `Vintage` | published_at, ingested_at, source_hash, metodologia, supersedes |
| `IngestionRun` | source_id, started_at, status, retry, quality, trace_id |
| `EconomicSector` | classificação IBGE, parent_id, vigência, região |
| `Market` | produto (ex. NCM), país destino/origem, intervalo, comércio |
| `EconomicEvent` | event_type, event_id, payload_version, correlation_id, timestamp |
| `Policy` | hipótese, objetivo, instrumentos, custo, competência, cronograma |
| `PolicyExecution` | etapas, orçamento aprovado, empenhado, liquidado, pago, outputs |
| `Model` | id, versão, técnica, equações, validação, limitações |
| `Scenario` | id, horizonte, políticas, parâmetros, modelo, data-vintage |
| `Forecast` | indicador, período alvo, origin_date, horizonte, distribuição |
| `Commitment` | indicador, baseline, target, prazo, responsável, financiamento |
| `Actual` | observação vinculada ao compromisso e versão correspondente |
| `ScenarioImpact` | cenário, mudança de input, diferença de output, incerteza |
| `ModelDependency` | node_from, node_to, tipo, sensibilidade, criticidade |
| `Opportunity` | sinal, hipótese, setor/região, benefícios, riscos, evidência |
| `Alert` | severidade, limiar, causa, owner, estado, runbook, SLA |
| `ReviewDecision` | reviewer, timestamps, parecer, aprovação, artefato publicado |
| `Evidence` | origem, hash, método, código, limitações e referências |

## Relações principais

```text
DataSource -> IngestionRun -> Vintage -> Observation -> Indicator
Indicator --derives/feeds--> ModelDependency -> Model -> Scenario
Scenario -> Forecast -> ScenarioImpact -> Alert -> ReviewDecision
Indicator + Policy + Commitment -> Guidance
Actual -> Evaluation -> Opportunity -> Policy proposal
Policy -> PolicyExecution -> output/outcome -> Evaluation
EconomicSector + Market + Geography -> Indicator dimensions
```

`Observed` e `Projected` são estados distintos. `Actual` nunca é um forecast convertido automaticamente. `Opportunity` não é uma política aprovada.

## Taxonomia de relações econômicas

- **Identidade contábil:** transformação determinística (ex.: PIB e dívida conforme metodologia).
- **Relação econométrica estimada:** parâmetro com população, período, erro e sensibilidade.
- **Hipótese causal:** mecanismo proposto, condições de identificação e limitações.
- **Dependência operacional:** atualização de uma fonte exige validar artefato posterior.

Nunca transportar causalidade a partir de uma aresta operacional sem avaliação metodológica.

## Eventos de domínio

- `EconomicIndicatorUpdated`: novo ponto ou nova publicação válida.
- `HistoricalSeriesRevised`: mudança de valores de períodos já conhecidos.
- `DataQualityFailed`: violação de contrato em quarentena.
- `ScenarioRecalculationRequested`: grafo identifica candidato a recomputação.
- `ScenarioRecalculated`: output persistido com input hashes.
- `ScenarioImpactDetected`: diferenças quantificadas em um comparativo.
- `MaterialReviewRequired`: impacto supera regra de aprovação.
- `OpportunityIdentified`: hipótese de oportunidade com evidência e confiança.
- `GuidanceRevisionPublished`: nova versão pública; anterior preservada.

## Invariantes

1. Nenhuma observação sem `indicator_id`, período, fonte, unidade e vintage.
2. Mudança retroativa cria nova vintage, não `UPDATE` destrutivo.
3. Forecast tem data de origem e horizonte, mesmo que a referência seja futura.
4. Comparações exigem compatibilidade de unidade, frequência, cobertura e metodologia.
5. Cada resultado de cenário tem conjunto fechado de inputs e versão de modelo.
6. Publicação de recomendação material exige decisão humana registrada.
7. Revisão de Guidance mantém target original e justificativa da mudança.
8. Alertas têm ciclo de vida: novo, triado, atribuído, resolvido, descartado.

## Agregados e fronteiras transacionais

`IndicatorSeries` agrega observações/vintages; `ScenarioRun` agrega inputs/outputs; `GuidanceRelease` agrega compromissos/versionamento; `AlertCase` agrega evidências e decisões. Outbox transacional sincroniza persistência e emissão de eventos. Consumidores devem ser idempotentes.

## Interfaces mínimas de API (proposta)

- `GET /v1/indicators?domain=&frequency=`
- `GET /v1/indicators/{id}/observations?from=&to=&as_of=`
- `GET /v1/sources/{id}/freshness`
- `GET /v1/scenarios/{id}/runs?as_of=`
- `GET /v1/guidance/{period}/releases`
- `GET /v1/alerts?status=&severity=`
- `GET /v1/opportunities?sector=&period=`

Todo endpoint público precisa retornar versão da metodologia e referência temporal dos dados.
