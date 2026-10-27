# Methodology — Evidências, Séries Históricas e Avaliação (V1.3)

## Hierarquia de afirmações

1. **Observado:** valor de origem com referência, data de publicação e vintage.
2. **Derivado:** cálculo reproduzível sobre observações, fórmula e versão.
3. **Estimado:** inferência com erro, incerteza e pressupostos.
4. **Projetado:** forecast ex-ante ou simulação condicional, com cenário.
5. **Hipótese:** mecanismo não demonstrado.
6. **Recomendação:** juízo normativo com critérios explícitos e revisão.

Não combinar categorias como se tivessem o mesmo grau de certeza.

## Fonte e atualização

Buscar fontes oficiais primárias sempre que disponíveis. Para cada série: identificador de origem, URL/API, licença, calendário de divulgação, timezone, lag esperado, período de referência, coleta, publicação, revisão e eventuais quebras de série. `latest` significa **última observação disponível na origem na hora da verificação**, não último arquivo local.

Caso não seja possível verificar a origem, registrar `source_unavailable` e data da última coleta bem-sucedida. Não apresentar valores antigos como atuais.

## Dados bitemporais e vintages

- **Tempo válido:** período econômico ao qual o valor se refere.
- **Tempo de conhecimento:** data de publicação, captura e versão válida no sistema.

Retornar `as_of` reconstrói a informação conhecida em uma data histórica. Uma publicação revisada produz nova vintage com motivo da revisão e link para a anterior. Também preservar payload bruto e código de transformação.

## Preparação de séries

- Documentar nominal vs. real, ajustado vs. não ajustado sazonalmente, acumulado de 12 meses vs. variação mensal, fluxo vs. estoque e valores de fim vs. média de período.
- Usar deflatores e base de preços consistentes, especialmente em séries de PIB, renda e investimento.
- Não interpolar lacunas automaticamente para publicação; imputações ficam marcadas.
- Registrar mudanças de classificação setorial, critérios do Censo/PNAD, nomenclatura de comércio e dados de balança.
- Construir série desde 2000 quando comparável; se não, usar o intervalo válido e explicitar a limitação.

## Simulação e cenários

Todo modelo exige: pergunta, horizonte, variáveis, equações, elasticidades, fonte, vintage, calibração, incerteza, limites e benchmark. Definir no mínimo cenário de continuidade, alternativo e adverso. Sensibilidade multi-parâmetro e análise de riscos substituem projeção pontual como única resposta.

Exemplo de identidade fiscal simplificada:

`d_t = [(1+i_t)/(1+g_t)] × d_(t-1) - p_t + a_t`

Em que `d` é dívida/PIB, `i` juros nominais efetivos, `g` crescimento nominal, `p` superávit primário/PIB e `a` ajuste estoque-fluxo. É relação contábil condicional; não equivale a previsão oficial sem calibração.

## Previsão e backtesting

- Calcular erro por vintage e horizonte de previsão, mantendo a informação de tempo real que teria sido conhecida na origem.
- Comparar com benchmarks ingênuos (persistência, sazonal, consenso público quando elegível).
- Acompanhar viés, MAE/RMSE, cobertura e largura de intervalos, calibração e degradação.
- Não selecionar apenas janelas favoráveis; publicar falhas e mudanças de modelo.

## Causalidade e políticas

Começar com teoria de mudança: inputs → atividades → outputs → outcomes → efeitos esperados. Comparar políticas com contrafactual defensável e identificar variáveis confundidoras, defasagens e efeitos distributivos. Considerar diferença-em-diferenças, séries temporais interrompidas, controles sintéticos e estudos de evento apenas quando pressupostos forem sustentáveis. Acompanhamento de preços ou fluxos da B3 não prova influência causal estrangeira sem identificação apropriada.

## Materialidade e oportunidades

Materialidade é função de magnitude histórica, persistência, probabilidade, incerteza, impacto sobre objetivos, criticidade e custo de ação. Limiares por série, com revisão e deduplicação. Uma oportunidade precisa: sinal, hipótese, baseline, cenário, impacto potencial, competência institucional, custo, riscos, evidência, confiança e teste para refutá-la.

Exemplo comércio: primeira exportação produto-destino não equivale a mercado consolidado; monitorar recorrência, diversificação, participação e margem de valor.

## Avaliação do modelo operacional

Monitorar tempos entre fonte, ingestão, cenário e decisão; precisão e utilidade dos alertas; taxa de revisão; acurácia; proporção das recomendações verificáveis; qualidade do contrafactual; custo por insight; mudanças de curso justificadas. Ser usado por gestores não prova impacto da ferramenta nas políticas — avaliar a contribuição com desenho de pesquisa específico.

## Validação e publicação

`draft` → `technical_review` → `methodological_review` → `approved` → `published`. Alertas de fatos observados podem ser automatizados sob regras; recomendações materiais e guidance publicado exigem revisão humana. Publicar nota de limitações, referências e log de mudanças em cada versão.
