# Brasil do Futuro — Constituição V1.3

**Status:** proposta constitucional para ratificação  
**Data:** 2026-10-26  
**Horizonte:** baseline histórico e Guidance 2027–2030, com visão até 2035.

O Brasil do Futuro é um projeto independente de inteligência econômica e avaliação de políticas públicas. Transforma observações econômicas e séries históricas em diagnósticos, simulações, compromissos verificáveis, avaliação de resultados e identificação de oportunidades de crescimento sustentável.

## Como navegar

- [`specs/mission.md`](specs/mission.md): missão, princípios, North Star e limites.
- [`specs/tech-stack.md`](specs/tech-stack.md): arquitetura, dados, automação, segurança e observabilidade.
- [`specs/roadmap.md`](specs/roadmap.md): entrega incremental 0 → 1 → 10 → 100, critérios de passagem.
- [`specs/domain-model.md`](specs/domain-model.md): domínios, capacidades, entidades, eventos e contratos.
- [`specs/methodology.md`](specs/methodology.md): método científico, histórico, simulações e causalidade.
- [`specs/economic-baseline.md`](specs/economic-baseline.md): catálogo inicial de indicadores, fontes e regras de baseline.
- [`specs/governance.md`](specs/governance.md): governança editorial, institucional, técnica e de dados.
- [`specs/guidance-2027-2030.md`](specs/guidance-2027-2030.md): ciclo de compromissos e prestação de contas.
- [`specs/adr/`](specs/adr/): ADRs 0001–0016.

## Regras de interpretação

1. **Constituição não é dado conjuntural.** Indicadores concretos precisam ser carregados de fontes oficiais com carimbo de data, não presumidos a partir deste repositório.
2. **Planejamento não é endosso governamental.** O Guidance aqui descrito é um instrumento experimental e independente, não compromisso formal do Estado brasileiro.
3. **Previsão não é fato.** Separar observação, estimativa, cenário hipotético, proposta, meta e avaliação causal.
4. **Revisões preservam história.** Nunca sobrescrever silenciosamente um dado ou guidance publicado.
5. **Crescimento com qualidade.** Avaliar crescimento econômico junto com sustentabilidade fiscal, produtividade, distribuição, bem-estar e impactos ambientais.

## Estrutura de trabalho sugerida

```
brasil-do-futuro/
  README.md
  specs/
    mission.md
    tech-stack.md
    roadmap.md
    domain-model.md
    methodology.md
    economic-baseline.md
    governance.md
    guidance-2027-2030.md
    adr/
      0001-*.md ... 0016-*.md
```

**Escopo desta versão:** constituição e contratos conceituais; não inclui integrações implementadas, coleta de dados realizada ou modelo econométrico calibrado.

## Implementação — piloto da fase 0

A constituição acima é preservada como recebida. A implementação inicial é um
**demonstrador técnico**, não aprovação metodológica nem conclusão do gate 0→1.

### Subir localmente

Requisito: Docker com Compose. As portas são expostas somente em localhost.
Credenciais no Compose são exclusivas do desenvolvimento local.

```sh
docker compose up -d --build
# Carregar exemplos explicitamente sintéticos:
docker compose run --rm ingestion ingest br.debt.gross_pct_gdp fixtures/debt-initial.json
docker compose run --rm ingestion ingest br.ipca.monthly fixtures/ipca.json
docker compose run --rm ingestion ingest br.selic.daily fixtures/selic.json
docker compose run --rm ingestion worker
# Exercitar revisão histórica, recálculo e alerta:
docker compose run --rm ingestion ingest br.debt.gross_pct_gdp fixtures/debt-revised.json
docker compose run --rm ingestion worker
```

- Painel: http://localhost:13000/?mode=fixture (demonstração sintética).
- Capturas de fontes: http://localhost:13000/?mode=source (vazio até capturar).
- API: http://localhost:18080/v1/indicators.
- Saúde: http://localhost:18080/healthz.
- Contrato: [`docs/openapi.yaml`](docs/openapi.yaml).

### Capturar uma janela da origem

```sh
docker compose run --rm ingestion fetch br.selic.daily --start 2025-01-02 --end 2025-01-10
docker compose run --rm ingestion worker
```

O conector usa HTTPS, timeout e retries limitados. Divida históricos em janelas
não superiores a 3650 dias. Toda captura real recebe `provisional`: confirmação
de contrato não substitui validação econômica, licença e calendário. SGS não
informa a data de publicação nesse payload; `published_at` fica nulo, sem confundir
período de referência com data de divulgação. Falhas de fonte são logadas e não
substituem observações anteriores nem certificam freshness.

### Validar

```sh
uv venv --python 3.12
uv pip install -r requirements.lock
# Banco descartável exclusivamente para testes; não apontar ao banco do piloto.
docker compose exec db createdb -U bdf bdf_test
TEST_DATABASE_URL=postgres://bdf:local-development-only@localhost:55432/bdf_test .venv/bin/pytest -q
(cd services/api && go test ./... && go vet ./...)
(cd web && npm ci && npm run build && npm run typecheck)
```

Sem `TEST_DATABASE_URL`, somente os testes unitários rodam; integrações ficam
explicitamente skipped. O CI sempre disponibiliza PostgreSQL e executa ambos.

### Operação e limites

- [`docs/execution-plan.md`](docs/execution-plan.md): escopo entregue, próximos incrementos e gates.
- [`docs/model-routing.md`](docs/model-routing.md): uso de Astra, Sol, Luna e Terra.
- [`docs/runbook.md`](docs/runbook.md): replay, falhas e limitações de operação.
- [`docs/source-register.md`](docs/source-register.md): seleção de séries e validações pendentes.

Não há endpoint de aprovação/publicação, credenciais de produção nem job periódico
habilitado. Recomendações e Guidance não são publicados automaticamente. Grafana,
exportação OTLP, calibração econômica, backtests, recuperação e aprovação metodológica
continuam no backlog. A API usa um usuário PostgreSQL de leitura.
