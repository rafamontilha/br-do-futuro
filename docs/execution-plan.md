# Execução incremental — Fundação 0

A autorização para implementar a constituição não altera seus status `proposed`.
Ratificação formal, responsáveis nominais e revisão metodológica devem ser registrados
por humanos. Nenhum gate está concluído por esta PR.

## Incremento 01 — infraestrutura auditável (esta PR)

- Catálogo estruturado com os 12 domínios e três séries candidatas.
- Python: contrato SGS, raw payload SHA-256, validação, quarentena, captura com retries.
- PostgreSQL: evidência append-only, supersedes por observação, conhecimento temporal,
  idempotência por valor/período e lock por série/modo, outbox transacional.
- Worker: recálculo só da dívida para três cenários condicionais, hash de inputs,
  deduplicação, alertas pendentes de revisão, retries e dead-letter após três falhas.
- Go: consultas de leitura e `as_of` com timezone; catálogo, observações, cenários e alertas.
- Next.js: separação de modos sintético/fonte, proveniência, hipóteses e estados vazios.
- Docker Compose e CI: integrações reais em PostgreSQL, Go, compilação e TypeScript.
- OpenTelemetry no pipeline/worker (spans locais opcionais), logs estruturados na ingestão.

O armazenamento bruto usa `bytea` append-only no PostgreSQL nesta fatia, evitando
consistência entre banco e object store. A migração para objetos versionados precisa
preservar hashes e ponteiros. Dependências são uma configuração pequena em código,
não um DAG genérico. Autorização de publicação não existe: o piloto é de leitura local.

## Incremento 02 — fontes e operação

Confirmar identidade, unidade, limites, direitos de uso, calendário oficial e histórico
de 10+ anos ou limitação por série. Trocar IPCA redistribuído pelo BCB pela fonte IBGE
quando o contrato primário estiver validado. Não reconstruir vintages antigas inexistentes.
Adicionar scheduler por calendário, freshness persistida, metadados de falhas,
backoff de worker, outbox com ordenação/replay operacional controlado, métricas e OTLP.

## Incremento 03 — método e produto

Calibrar cenário fiscal e benchmarks. Preparar três propostas com custo, financiamento,
mecanismo, competências, alternativas, evidências e refutação. Criar os contratos de
Guidance com baseline/target/forecast/actual separados. Não preencher metas com exemplos
sintéticos. Revisão metodológica independente e aprovação antes da publicação material.

## Incremento 04 — endurecimento do piloto

OIDC, papéis de produtor/revisor/publicador, auditoria de decisões, testes de backup/restore,
limites e paginação da API, observabilidade dos quatro planos, alertas e SLOs mensurados.
Somente depois definir implantação pública, orçamento e infraestrutura de produção.

## Gate 0→1 (estado atual)

| Critério | Estado |
|---|---|
| Três propostas públicas analisadas | Pendente; não há evidência suficiente nesta constituição |
| Dados econômicos rastreáveis e baseline validado | Estrutura implementada; validação econômica pendente |
| Revisão histórica reproduzível | Demonstrador sintético; revisão oficial ainda pendente |
| Eventos → cenário → alerta | Implementado para a identidade fiscal ilustrativa |
| Aprovação metodológica | Pendente de responsável humano |

O roadmap 2027–2035 permanece visão, não compromisso de concluir nesta primeira entrega.
