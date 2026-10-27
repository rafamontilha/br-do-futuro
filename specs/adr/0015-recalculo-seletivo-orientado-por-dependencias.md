# ADR 0015 — Recálculo seletivo orientado por dependências

**Status:** proposed | **Versão:** Constituição V1.3 | **Data:** 2026-10-26

## Contexto

Equilibrar latência, custo, estabilidade e transparência.

## Decisão

Usar DAG/grafo de dados, modelos, cenários e guidance para recalcular só partes afetadas, com auditoria de execução completa disponível.

## Consequências e controles

Mudanças de metodologia podem invalidar cache e exigir recálculo integral.

## Revisão

A mudança exige registro de alternativa, justificativa, impacto nas dependências e referência a um ADR substituto quando houver.
