# Economic Baseline & Indicator Catalog — V1.3

**Status:** especificação do baseline, **não** snapshot de valores verificados.  
**Data de configuração:** 2026-10-26. Os números concretos exigem ingestão e validação das respectivas fontes.

## Política de baseline

Definir base 2026 para o Guidance 2027–2030, mas manter séries históricas preferencialmente desde 2000, quando disponíveis e comparáveis. O ano-base não é sinônimo da última observação: registrar dado mais recente por frequência e vintage. O baseline inicial só recebe status `verified` depois de reconciliação com fonte, unidade, período e metodologia. Nunca preencher lacuna com valor lembrado de conversas anteriores.

## Domínios do Observatório Econômico Nacional

| # | Domínio | Indicadores e desagregações prioritárias | Fonte inicial candidata |
|---|---|---|---|
| 01 | Crescimento e PIB | PIB real/nominal/per capita, PIB potencial, produtividade, hiato do produto | IBGE, Ipea, BCB |
| 02 | Inflação e preços | IPCA, IPCA-15, INPC, núcleos, administrados, IGP-M | IBGE, BCB, FGV |
| 03 | Juros e crédito | Selic meta/efetiva, juros reais, spreads, crédito, concessões, inadimplência | BCB |
| 04 | Famílias e consumo | endividamento, comprometimento de renda, renda real, consumo, confiança | BCB, IBGE, CNC |
| 05 | Investimento e capital | FBCF, taxa de investimento, investimento público e privado, investimento direto no país (IDP), fluxos | IBGE, BCB, Tesouro |
| 06 | Câmbio e setor externo | USD/BRL, EUR/BRL, câmbio real efetivo, reservas, conta corrente | BCB |
| 07 | Comércio exterior | exportações/importações FOB, saldo, NCM, país, empresa quando permitido, novos mercados, concentração, tecnologia | MDIC/Comex Stat |
| 08 | Mercado financeiro | Ibovespa e índices setoriais, retorno nominal/real, volume, capitalização, fluxos por tipo de investidor | B3, CVM |
| 09 | Trabalho | PNAD Contínua, desemprego, ocupação, informalidade, subutilização, rendimento, emprego formal | IBGE, MTE |
| 10 | Demografia e sociedade | Censo, população, envelhecimento, escolaridade, pobreza, desigualdade, mobilidade | IBGE, INEP, Ipea |
| 11 | Setores produtivos | agropecuária, indústria extrativa e transformação, construção, comércio, serviços, tecnologia; valor adicionado, produção, emprego | IBGE e fontes setoriais |
| 12 | Contas públicas | dívida bruta/líquida, primário/nominal, receita, despesa, juros, subsídios, investimentos | Tesouro, BCB, SIOP |

## Setores e classificação

PIB pelas óticas da produção (valor adicionado por atividades + impostos líquidos), despesa e renda conforme disponibilidade. Construção é atividade da indústria na ótica de produção, não setor somado outra vez. Acompanhar em cada atividade: crescimento real, participação no PIB/VA, produtividade, emprego, rendimento, investimento, exportação e capacidade. Antecedentes: PIM-PF, PMC, PMS, levantamentos de safra, crédito e indicadores imobiliários quando metodologicamente compatíveis.

## Mercados externos

Mapear produto NCM ↔ destino/origem ↔ período, volume, valor, preço implícito e concentração. Identificar entrada de novo mercado somente com critério de recorrência e relevância definidos. Distinguir crescimento do preço internacional de aumento de volume, especialmente commodities; comparar moedas e deflatores adequados.

## Fluxos da bolsa

Separar variação de preços, participação no volume e fluxo líquido de investidores estrangeiros/nacionais. Influência causal só após modelo de identificação e controles (juros, câmbio, notícias, lucros, composição e liquidez); não inferir causalidade de simples coincidência temporal.

## Esquema mínimo para cada série

```yaml
indicator_id: br.ipca.12m
name: IPCA acumulado em 12 meses
unit: percent
frequency: monthly
source: IBGE
source_series_id: TO_BE_VALIDATED
reference_period: YYYY-MM
value: null # preencher apenas por captura verificada
published_at: null
collected_at: null
vintage_id: null
adjustment: non-seasonally-adjusted
methodology_version: null
quality_status: unavailable # verified | provisional | unavailable
source_uri: null
license: TO_BE_VALIDATED
```

Outros campos: cobertura geográfica, dimensões, ajuste sazonal, moeda, base de preços, referência de classificação, tipo estoque/fluxo, calendário esperado, latência máxima, revisão e sucessor metodológico.

## Classes de atualização (por origem)

- **Mercado diário/intradiário:** câmbio e bolsa conforme publicação/licença; marcar horários e fechamento.
- **Mensal:** inflação, emprego PNAD móvel, crédito, produção e comércio; respeitar calendário real.
- **Trimestral:** PIB, FBCF, PNAD e outras séries conforme metodologia.
- **Anual:** indicadores estruturais, contas e avaliações consolidadas.
- **Decenal/episódica:** Censo; não classificar como vencido fora de seu ciclo.

A frequência efetiva de cada série é definida no catálogo da origem, nunca imposta por esta classificação genérica.

## Contrato de acompanhamento

Para todo indicador ligado ao guidance: `baseline`, `target`, `forecast`, `actual`, `variance`, `context`, `attribution_assessment`, `opportunity`, `as_of` e `vintage`. O cálculo do desvio deve mostrar unidade e direção desejada; comparar índices e percentuais com cuidado (p.p. versus %).

## Critérios de aceite do primeiro baseline

1. Fonte primária e identificador exato documentados.
2. Última observação capturada e validada, com data e timezone.
3. 10+ anos históricos quando possível, ou limitação explícita.
4. Revisões e quebras de série documentadas.
5. Fórmulas e transformações reproduzíveis.
6. Comparabilidade intergovernos testada; não atribuir mérito sem controle de fatores externos.

## URLs de partida (não substituem seleção de série)

- IBGE SIDRA: https://sidra.ibge.gov.br/
- BCB dados abertos: https://dadosabertos.bcb.gov.br/
- Tesouro: https://www.tesourotransparente.gov.br/
- IpeaData: http://www.ipeadata.gov.br/
- MDIC Comex Stat: https://comexstat.mdic.gov.br/
- B3: https://www.b3.com.br/
- CVM: https://dados.cvm.gov.br/
- MTE: https://www.gov.br/trabalho-e-emprego/

URLs são referências para integração futura; disponibilidade, termos de uso e endpoints específicos precisam ser confirmados na implantação.
