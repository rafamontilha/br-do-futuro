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
- Antes de PR: pytest com PostgreSQL, Go tests/vet, build e typecheck web, diff --check.
- Não versionar segredos, dumps de dados coletados, caches ou dependências instaladas.
