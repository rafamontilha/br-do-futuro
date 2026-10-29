# Validation — Phase 1: Expansão do Núcleo P0 (PIB, Câmbio PTAX, Desocupação PNAD Contínua)

## Automated

- [x] `pytest tests/` passa com os novos testes unitários e de integração dos conectores IBGE SIDRA e BCB PTAX.
- [x] `go test ./...` e `go vet ./...` no diretório `services/api` passam sem avisos ou erros.
- [x] `npm run build` e typecheck no diretório `web/` passam limpos sem erros.
- [x] `python3 scripts/smoke.py` valida com sucesso a presença e valores dos novos indicadores no catálogo e nas observações.
- [x] Validações de integridade e idempotência:
  - Reprocessamento das mesmas cargas brutas não duplica registros na tabela `indicator_observations`.
  - Payloads com valores inválidos (ex: variação de PIB nula ou ausência de campos essenciais) são desviados para `quarantine_records`.
  - Ancoragem temporal dos trimestres valida estritamente o formato `YYYY-MM-01` compatível com os 4 trimestres do ano civil.

### Key assertions

| Behaviour | Test type | Expected result |
|---|---|---|
| Ingestão PIB SIDRA (Tabela 5932) | Unit / Integration (Python) | Extrai período trimestral normalizado para `YYYY-MM-01`, persiste raw payload SHA-256 e gera observação com unidade `percent_yoy` |
| Ingestão Câmbio PTAX (Série 1) | Unit / Integration (Python) | Extrai cotação diária/fechamento com precisão decimal adequada e unidade `brl_per_usd` |
| Ingestão PNAD Contínua (Tabela 4099) | Unit / Integration (Python) | Extrai taxa de desocupação móvel com ancoragem no primeiro dia do período de referência e unidade `percent` |
| Quarentena de Payload Inválido | Unit (Python) | Resposta truncada ou fora de contrato é interceptada e registrada em `quarantine_records` sem propagação |
| Consulta de Indicadores na API Go | Integration (Go) | `GET /v1/indicators` retorna os 6 indicadores P0 cadastrados |
| Consulta Bitemporal (`as_of`) de PIB | Integration (Go) | `GET /v1/observations?indicator_id=IBGE_PIB_TRIMESTRAL_VAR&as_of=...` retorna observação válida respeitando a data de conhecimento |
| Renderização no Frontend | Integration (TypeScript/Next.js) | Componentes do Observatório renderizam os 6 indicadores com formatação numérica e badges adequadas |

---

## Manual walkthrough

1. Iniciar o ambiente completo com a nova migração (`docker compose up -d --build` ou banco local de desenvolvimento).
2. Executar o pipeline de ingestão para as novas séries:
   `python3 -m ingestion.bdf.pipeline --series IBGE_PIB_TRIMESTRAL_VAR,BCB_PTAX_USD_BRL,IBGE_PNADC_DESOCUPACAO --fixture-mode`
3. Acessar a aplicação no navegador em `http://localhost:3000`.
4. Verificar no Observatório Econômico Nacional os novos cartões de indicadores:
   - **PIB Trimestral (% a.a.)**: Confirmar a visualização dos trimestres históricos.
   - **Câmbio USD/BRL (PTAX)**: Confirmar a cotação em reais por dólar.
   - **Taxa de Desocupação (PNAD Contínua)**: Confirmar a taxa percentual de desemprego.
5. Inspecionar os metadados de proveniência de cada série clicando no indicador de fonte/vintage.
6. Acessar o endpoint `/v1/indicators` via cURL ou navegador e conferir a lista completa de 6 séries P0.

### Edge cases

- [ ] **Mudança de ano-base ou revisão de série pelo IBGE:** O conector deve registrar nova vintage com `knowledge_time` atualizado sem sobrescrever o registro histórico anterior (`supersedes_id` ou bitemporalidade).
- [ ] **Feriados e finais de semana na série cambial diária:** Não gerar registros fictícios para datas sem cotação de mercado oficial do BCB.
- [ ] **Tratamento de casas decimais em variações percentuais:** Preservar a exatidão com o tipo `NUMERIC(16,6)` evitando perda de precisão com ponto flutuante.

---

## Tone check (if user-facing copy exists)

- [ ] Terminologia técnica rigorosa e precisa (ex.: "PIB a preços de mercado - variação em relação ao mesmo trimestre do ano anterior").
- [ ] Sem juízo de valor subjetivo (evitar palavras como "excelente", "preocupante", "recorde" na visualização direta dos dados).
- [ ] Proveniência e autoria das fontes claramente identificadas (IBGE SIDRA e Banco Central do Brasil).

---

## Definition of done

- [ ] Todos os testes automatizados executam e passam com sucesso (`pytest`, `go test`, `go vet`, `npm run build`, `smoke.py`).
- [ ] Migração `006_expand_p0_indicators.sql` aplicada e documentada no catálogo.
- [ ] Conectores de ingestão com testes unitários e fixtures oficiais implementados.
- [ ] API Go e Frontend Next.js atualizados e validados.
- [ ] Walkthrough manual verificado localmente.
