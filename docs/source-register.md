# Registro de fontes — piloto técnico

Não é um baseline. Licença, calendário exato, disponibilidade histórica e nomeação
individual de Data Steward estão pendentes. Frequência não é calendário de divulgação.

| Indicador canônico | Origem candidata | Unidade | Frequência | Limitação |
|---|---|---|---|---|
| br.ipca.monthly | SGS 433, IBGE redistribuído pelo BCB | variação % mensal | mensal | Preferir IBGE direto após validação do contrato; não é IPCA 12 meses |
| br.selic.daily | SGS 11, BCB | % ao dia | diária | Não é meta Selic nem juro efetivo anual da dívida |
| br.debt.gross_pct_gdp | SGS 13762, BCB | % PIB | mensal | Série revisável; verificar cobertura e quebras antes de comparação histórica |

Referências primárias para a diligência:
- [Catálogo SGS Selic](https://dadosabertos.bcb.gov.br/dataset/11-taxa-de-juros---selic).
- [Dados abertos do BCB](https://www.bcb.gov.br/acessoinformacao/dadosabertos).
- [IBGE SIDRA](https://sidra.ibge.gov.br/).
- [BCB, Relatório de Estabilidade Financeira, outubro 2019](https://www.bcb.gov.br/content/publicacoes/ref/201910/relestab201910-refpub.pdf), referência à série 13762; não substitui validação atual do catálogo.

## Contrato de captura

Endpoint: `https://api.bcb.gov.br/dados/serie/bcdata.sgs.{id}/dados`.
Parâmetros: `formato=json`, `dataInicial`, `dataFinal` (DD/MM/AAAA).
Payload esperado: lista de `{data, valor}`. A data é referência econômica, não publicação.
`published_at=null` quando a origem não a informa. `known_at` é o relógio do banco durante
a transação de ingestão; não usar uma coleta atual para afirmar o que se sabia em 2000.
Retenção bruta e hash permitem reproduzir normalização. Formato novo entra em quarentena.

O escopo inicial valida estrutura, duplicidade, finitude, frequência e datas futuras.
Validação de outliers econômicos, completude de calendários, revisão de metodologia,
remoção de pontos pela origem e eventos de republicação sem mudança de valor são pendentes.
Repetição de mesmos valores registra a captura, mas não cria nova observação nem evento.
