#!/usr/bin/env bash
set -euo pipefail

# Brasil do Futuro — Script de Verificação Pré-PR Unificado
# Executa todos os gates obrigatórios definidos em AGENTS.md e no ciclo de desenvolvimento.

echo "==> 1. Verificando formatação e espaços em branco residuais (git diff --check)..."
git diff --check

echo "==> 2. Executando testes Python com PostgreSQL (bdf_test)..."
export TEST_DATABASE_URL="${TEST_DATABASE_URL:-postgres://bdf:local-development-only@127.0.0.1:55432/bdf_test}"
.venv/bin/pytest tests/

echo "==> 3. Executando testes e análise estática Go (services/api)..."
(cd services/api && go test -count=1 -v ./... && go vet ./...)

echo "==> 4. Executando compilação e verificação de tipos Web (web)..."
(cd web && npm run build && npm run typecheck)

echo "==> [OK] Todos os gates de verificação pré-PR foram aprovados com sucesso!"
