# Roadmap — Brasil do Futuro (V1.3)

**Status:** plano hipotético condicionado a financiamento, capacidade de execução e validação de valor.  
**Evolução:** 0 → 1 → 10 → 100. O número é maturidade relativa, não contagem de usuários.

## 0 — Economic Intelligence Foundation (2026)

**Objetivo:** tornar auditável a primeira leitura da economia e testar a infraestrutura de atualização contínua.

- Ratificar missão, domínio, metodologia, governança e ADRs 0001–0016.
- Catálogo inicial dos 12 domínios com responsáveis, fontes, licenças e periodicidades.
- Baseline histórico: preferir 2000 em diante quando séries comparáveis estiverem disponíveis; documentar quebras e lacunas.
- Selecionar de 3 a 5 indicadores para pipeline demonstrador, incluindo um revisável, um mensal e um diário.
- Criar ingestão idempotente, contratos, registros de vintage, eventos, observabilidade e replay.
- Construir primeiro cenário fiscal com premissas explícitas e uma carteira de pelo menos três propostas públicas analisadas.
- Guidance 2027–2030 experimental, com metas **ilustrativas** até validação e sem vinculação institucional.

**Gate 0→1:** três propostas com custo, mecanismo, competência e cenários; dados rastreáveis; uma revisão histórica reproduzível; eventos → cenário → alerta demonstrados; aprovação metodológica documentada.

## 1 — Assisted Economic Decisioning (2027)

- Expandir integrações para PIB, inflação, juros, câmbio, fiscal, mercado de trabalho, investimento, crédito e comércio exterior. [Núcleo P0 integrado e catalogado]
- Painéis de realizado vs. baseline, forecast, target e cenário de continuidade. [Entregue na PR #7 — branch phase-1-comparison-panels]
- Motor de dependências e recálculo seletivo; workflow de revisão humana para impactos materiais. [Entregue na branch phase-1-dependency-engine]
- Backtesting de forecasts por vintage e horizonte; mecanismo de alertas por calendário e materialidade.
- Revisões trimestrais de cenário; primeira revisão anual do Guidance.
- Publicar relatório de desempenho do próprio modelo operacional e erro de previsões.

**Gate 1→10:** cobertura estável do núcleo P0; observabilidade ponta a ponta; governança de mudanças; testes de recuperação; relatórios reproduzíveis e avaliação independente dos principais métodos.

## 10 — National Policy Intelligence (2028–2030)

- Cobertura dos 12 domínios econômicos e desagregações setoriais/regionais compatíveis com fontes.
- Acompanhamento de medidas aprovadas, execução orçamentária, responsáveis e efeitos observados.
- Avaliação longitudinal de políticas; experimentos naturais e estratégias contrafactuais quando identificáveis.
- Mapa de abertura de mercados produto-destino e sinais setoriais de investimento.
- Comparação entre mandatos sem distorções de base, sazonalidade e mudanças de metodologia.
- APIs abertas, dashboards acessíveis e explicações de incerteza para público não técnico.

**Gate 10→100:** resultados revisados por pares especialistas, confiança pública, evidências de utilidade e melhoria consistente de acurácia e processo.

## 100 — Adaptive National Development Intelligence (2031–2035, visão)

- Inteligência econômica adaptativa com cenários intersetoriais e regionais.
- Recomendações fundamentadas em evidências, revisáveis, com memória entre mandatos.
- Participação pública e mecanismos de contestação de análises.
- Avaliar se a adoção do sistema melhorou a qualidade e transparência das decisões, sem atribuição causal gratuita.

## Sequência transversal de capacidades

| Frente | Fundação | 2027 | 2028–2030 | Longo prazo |
|---|---|---|---|---|
| Catálogo e fontes | P0 definido | P0 coberto | 12 domínios | expansão comparativa |
| Histórico e vintage | MVP auditável | revisões automatizadas | série multi-mandato | inteligência longitudinal |
| Simulação | modelo fiscal simples | cenários integrados | intersetorial | adaptativo |
| Observabilidade | platform+data | +model+decision | otimização contínua | garantia independente |
| Impact engine | 3–5 séries | DAG e impacto seletivo | ampla cobertura | escala federada |
| Guidance | proposta experimental | revisão anual | comparação 2027–2030 | ciclos de governo |

## Backlog inicial priorizado

1. Definir identidade dos indicadores e calendário esperado de publicação.
2. Verificar direitos de acesso e licenças, endpoints, cobertura histórica e limites.
3. Implementar armazenamento bruto versionado, transformação e registro de vintage.
4. Instrumentar pipelines com OpenTelemetry, logs estruturados e SLOs de dados.
5. Emitir eventos de atualização/revisão; testar idempotência e falhas.
6. Definir dependências e regra de materialidade; implementar recálculo seletivo.
7. Construir visualização baseline–forecast–target–actual–opportunity.
8. Adicionar backtesting e revisão humana para recomendações.
9. Publicar primeiro relatório de cenário com limitações explícitas.
10. Auditar cobertura, falsas detecções, custo e progresso contra os gates.

## Anti-goals

Não iniciar com arquitetura distribuída complexa; não prometer atualização em tempo real de séries anuais; não fixar metas numéricas de economia sem baseline validado; não automatizar posicionamentos públicos sem revisão; não declarar impacto causal apenas porque uma política antecedeu uma melhora.

## Risco e mitigação

- Fontes instáveis ou revisadas → contratos, vintage, monitoramento e fallback documentado.
- Correlação espúria → protocolo causal, sensibilidade e revisão por especialistas.
- Custos de processamento → cache e recálculo seletivo.
- Captura político-partidária → metodologia invariável, transparência e contestação.
- Dados não comparáveis → metadados de ruptura e séries encadeadas apenas quando justificadas.
- Alerta em excesso → limiares por domínio, análise de precisão, deduplicação.
