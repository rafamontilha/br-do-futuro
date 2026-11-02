# Ciclo de Desenvolvimento e Padrões de Engenharia — Brasil do Futuro

Este documento formaliza as práticas operacionais, padrões de engenharia e aprendizados incorporados ao ciclo de desenvolvimento do projeto.

---

## 1. Fluxo de Trabalho (Development Lifecycle)

1. **Especificação e Alinhamento:**
   - Antes de iniciar código, consultar `specs/mission.md`, `specs/roadmap.md` e a spec da respectiva fase em `specs/`.
   - Manter imutabilidade e não alterar propostas de governança/constituição sem aprovação humana.

2. **Implementação com Blindagem de Contratos:**
   - **PostgreSQL / Conexões Compartilhadas:** Funções que recebem conexões `conn` externas **nunca devem presumir o `row_factory` padrão**. Devem explicitar o cursor (`with conn.cursor(row_factory=tuple_row) as cur:`) ou desempacotar polimorficamente (`row["col"] if isinstance(row, dict) else row[idx]`).
   - **Proibição de Fallbacks Silenciosos:** Nunca capturar exceções de leitura de banco e reverter silenciosamente para dados estáticos/canônicos em memória sem emitir erro explícito. Fallbacks silenciosos mascaram quebras em produção e violam a separação estrita entre dados oficiais e fixtures.
   - **Bitemporalidade e Vintages:** Preservar `known_at`, `reference_period` e imutabilidade dos dados históricos.

3. **Paridade em Testes Automatizados:**
   - Testes de componentes invocados por workers e daemons de produção devem exercitar as conexões usando a mesma configuração do consumidor real (ex.: testar com `row_factory=dict_row` além do default).
   - Testes de integração devem limpar exclusivamente o banco isolado `bdf_test`.

4. **Verificação Pré-PR Unificada:**
   - Executar `./scripts/verify.sh` antes de abrir ou atualizar qualquer Pull Request. O script valida:
     - Ausência de quebras de formatação e trailing whitespace (`git diff --check`).
     - Testes Python com PostgreSQL 17 (`pytest tests/`).
     - Testes e análise estática Go (`go test ./...` e `go vet ./...`).
     - Compilação e verificação de tipos Next.js (`npm run build` e `npm run typecheck`).

5. **Revisões de IA (Codex) e Fechamento de Ciclo:**
   - Inspecionar ativamente os comentários e badges emitidos pelo Codex/CI nas PRs.
   - Para cada finding identificado, aplicar a correção correspondente e **obrigatoriamente adicionar teste de regressão automatizado** que reproduza o cenário problemático.
   - Reavaliar o PR via `@codex review` e registrar os aprendizados nos documentos vinculantes.

## 2. Horizonte de previsão e atraso de fila

O período base de um cenário determina seus alvos, mas o horizonte de backtesting
é medido contra o último período conhecido na origem registrada do forecast.
Com publicações acumuladas na fila, esses períodos podem diferir. Consultar somente
vintages do mesmo indicador/modo com `known_at <= forecast_origin_at`; excluir alvos
que não estejam à frente do último período conhecido. Replays preservam a origem e
não incorporam publicações posteriores. Testar fila acumulada, isolamento de modos,
alvos alcançados e correspondência dos horizontes dos benchmarks.
