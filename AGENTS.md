# Brasil do Futuro — execução

Leia `specs/mission.md`, `specs/tech-stack.md`, `specs/roadmap.md` e os documentos
vinculantes afetados antes de alterar comportamento. A constituição e os ADRs estão
como propostas; não marque ratificação, validação econômica ou aprovação humana
como concluídas automaticamente.

- Continue a fase 0 conforme `docs/execution-plan.md`; não declare gates sem evidências.
- Preserve raw payloads, vintages, revisões, unidades e conhecimento temporal.
- Nunca apresente fixtures como dados oficiais, ou captura antiga como última da origem.
- Não use Selic diária como juros efetivos anuais da dívida.
- Não publique recomendações/Guidance automaticamente.
- Use `docs/model-routing.md` para escolha de modelos; não iniciar quatro revisões redundantes.
- Testes de integração podem limpar apenas o banco dedicado `bdf_test`.
- Conexões SQL compartilhadas: nunca assumir `row_factory`; usar `conn.cursor(row_factory=...)` explícito ou extração polimórfica.
- Proibição de fallbacks silenciosos: não capturar erros de banco para mascarar com dados estáticos em produção.
- Paridade de testes: testar componentes com a mesma configuração de conexão usada pelos daemons em runtime (ex.: `dict_row`).
- Antes de PR: executar `./scripts/verify.sh` (pytest com PostgreSQL, Go tests/vet, build e typecheck web, diff --check).
- Consulte `docs/development-cycle.md` para as diretrizes completas de engenharia e ciclo de vida.
- Não versionar segredos, dumps de dados coletados, caches ou dependências instaladas.
