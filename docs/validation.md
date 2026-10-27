# Evidências de validação — 2026-10-27

## Ambiente local

- 19 testes Python passaram com PostgreSQL 17 real, sem testes de integração pulados.
- `go test ./...` e `go vet ./...` passaram.
- Next.js: build de produção e TypeScript passaram.
- Imagens Docker de ingestão, API e web construídas.
- Capturas históricas públicas SGS: Selic (7 pontos, 02–10/01/2025), IPCA (3 pontos,
  jan–mar/2025), dívida (3 pontos, jan–mar/2025). Contrato aceito; qualidade permanece
  `provisional`. Nenhuma dessas janelas constitui validação do baseline ou atualidade.
- Worker processou 13 eventos dessas capturas sem falhas.
- Demonstrador sintético: ingestão inicial de três séries, revisão da dívida, três
  cenários recalculados e três alertas materiais pendentes de revisão humana.

## O que os testes demonstram

Validação de estrutura e finitude; rejeição de datas futuras/períodos duplicados;
segregação fonte/fixture; ingestão concorrente idempotente; vintages preservadas;
reconstrução por conhecimento temporal; revisão de período antigo sem recálculo
inútil do cenário corrente; reversão A→B→A sem perda de história; replay sem duplicar
outputs; quarentena sem observações; falhas de consumidor → retries → dead-letter.

## O que ainda não demonstram

Revisão histórica real da fonte, qualidade de inferência econômica, causalidade,
calibração, backtests, revisão de licenças e calendários, autorização editorial,
segurança de produção, recuperação de desastre e SLOs sob carga.

## Verificação integrada

`scripts/smoke.py` passou contra a API Docker: saúde, 12 domínios, seis pontos
sintéticos correntes, três cenários, três alertas, 13 pontos reais provisórios,
`as_of` anterior vazio, modo inválido 400, data sem timezone 400 e escrita 405.
No navegador, o painel renderizou valores, unidades legíveis, cenários e alertas;
a expansão de proveniência mostrou vintage, hash e origem fixture.
