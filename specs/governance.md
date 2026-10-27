# Governance — Brasil do Futuro (V1.3)

## Mandato e independência

O Brasil do Futuro é independente e não representa o Governo Federal nem autoridades monetárias, instituições fiscalizadoras ou entidades estatísticas. Avaliações e contrapropostas aplicam critérios iguais independentemente de alinhamento político. Financiamento, colaboradores, conflitos de interesse, metodologia e mudanças editoriais deverão ser transparentes.

## Instâncias de governança (papéis, não pessoas nomeadas)

| Papel | Responsabilidades |
|---|---|
| Constitutional Steward | integridade dos princípios, evolução de versões e ADRs |
| Economic Research Lead | coerência teórica, carteira analítica, limitações |
| Data Steward | catálogo, proveniência, contratos, quality e histórico |
| Model Owner | calibração, teste, backtesting, monitoramento de drift |
| Platform/SRE Owner | ingestão, SLO, segurança, incidentes, custo |
| Independent Reviewer | revisão econômica, metodológica e editorial de material crítico |
| Publication Owner | versão, escopo, mensagens, correções públicas |
| Compliance/Privacy Reviewer | licença, dados pessoais, segurança e riscos legais |

Um mesmo indivíduo pode exercer múltiplas funções na fase inicial, mas uma publicação material exige pelo menos uma revisão crítica documentada independente da autoria sempre que viável; exceções devem ser declaradas.

## Competências institucionais monitoradas

- Executivo: propostas, gestão e execução dentro de sua competência.
- Legislativo: legislação, aprovação e fiscalização do orçamento.
- Judiciário: controle jurisdicional nos casos de sua competência, sem função ordinária de gestão econômica.
- Banco Central: funções definidas em lei, com autonomia aplicável.
- TCU e órgãos de controle: fiscalização e auditoria.
- Estados e municípios: competências próprias e execução federativa.
- Sociedade civil: monitoramento, debate e contestação.

Um mapa institucional por política distingue proponente, aprovador, executor, financiador, fiscalizador e beneficiário. Não confundir esfera federal com responsabilidade exclusiva do Executivo.

## Direitos de decisão

| Tipo | Automação permitida | Revisão requerida |
|---|---|---|
| Captura/validação de dado | sim | incidentes/exceções |
| Atualização de painel factual verificado | sim | amostragem e auditoria |
| Recálculo técnico e sinal de desvio | sim | materialidade e riscos |
| Alerta operativo | sim | pós-triagem conforme severidade |
| Mudança de hipótese causal | não automaticamente | revisão metodológica |
| Recomendação pública material | não publicar automaticamente | responsável e revisor |
| Mudança de target ou Guidance oficial do projeto | não | registro e aprovação formal |
| Mudança constitucional/ADR | não | proposta, revisão, ratificação |

## Registro de decisões

Cada aprovação contém identificador, autor, revisor, data, escopo, dados/vintage, modelo e versão, alternativas, risco, conflitos de interesse, objeções, conclusão e link ao artefato. Uma atualização nunca apaga uma publicação anterior.

## Política de alertas e incidentes

- **Crítico:** perda de integridade, pipeline prioritário indisponível ou publicação não reprodutível; bloquear propagação quando necessário.
- **Material:** desvio significativo de guidance, revisão relevante de cenário ou mudança de risco; revisão humana proporcional.
- **Oportunidade:** sinal econômico ainda hipotético; abrir estudo, não afirmar política vencedora.

Alertas possuem owner, SLA, deduplicação, rastreamento e análise de falsos positivos. Incidentes graves exigem postmortem e ação de prevenção.

## Segurança e privacidade

Aplicar minimização e finalidade de dados, bases legais apropriadas quando houver dados pessoais, segregação de privilégios, revisão de integrações, backup e controle de custos. Não publicar microdados identificáveis. Conteúdo de fontes e IA é dado não confiável até verificação.

## Auditoria e contestação

Disponibilizar método, fontes e limitações; permitir questionamentos documentados e histórico de erratas. Uma correção retifica a visão atual, mas preserva o que foi originalmente publicado e a explicação da mudança.

## Política de mudanças

- Constituição: versionamento semântico e nota de emenda.
- ADR: histórico de status (proposed, accepted, superseded, rejected) com substituto identificado.
- Indicador: mudança de definição cria versão e política de ponte entre séries.
- Modelo: mudança exige regressão/backtest e confronto com benchmark.
- Guidance: revisão anual ou extraordinária justificada, sem reescrever metas originais.

## KPIs de governança

Cobertura de proveniência, tempo de remediação, qualidade dos alertas, incidentes recorrentes, resultados reproduzíveis, revisões independentes, publicações corrigidas, tempo entre publicação oficial e atualização e desempenho dos modelos. O desempenho institucional de governo é distinto do desempenho operacional da plataforma.
