# Validation — Method & Product: Public Proposals, Fiscal Calibration & Guidance Contracts (Incremento 03)

## Automated

- [x] `pytest tests/` passa com testes de integridade de propostas e governança
- [x] `go test ./...` e `go vet ./...` no diretório `services/api` passam sem avisos ou erros
- [x] `npm run build` e typecheck no diretório `web/` passam limpos sem erros
- [ ] `python3 scripts/smoke.py` valida com sucesso a API local e os novos endpoints de propostas e compromissos
- [x] Novos testes cobrem:
  - Integridade estrutural das 3 propostas canônicas (mecanismo causal, financiamento, atores responsáveis e competência)
  - Validação da proibição de marcação automática de validação econômica ou ratificação de metas
  - Consulta e serialização dos endpoints `GET /api/v1/proposals` e `GET /api/v1/guidance/commitments`
  - Rejeição de requisição com identificador de proposta inexistente (HTTP 404)

### Key assertions
| Behaviour | Test type | Expected result |
|---|---|---|
| Consulta de Propostas do Policy Lab | Integration (Go) | `GET /api/v1/proposals` retorna HTTP 200 com array contendo as 3 propostas canônicas |
| Detalhe de Proposta Única | Integration (Go) | `GET /api/v1/proposals/prop-fiscal-mandatory-spending` retorna HTTP 200 com mecanismo causal completo e competência |
| Proposta Inexistente | Integration (Go) | `GET /api/v1/proposals/nao-existe` retorna HTTP 404 Not Found |
| Consulta de Matriz de Guidance | Integration (Go) | `GET /api/v1/guidance/commitments` retorna HTTP 200 com compromissos separando `baseline`, `target`, `forecast` e `actual` |
| Integridade de Dados de Políticas | Unit (Python) | Propostas possuem valores numéricos válidos para custo, fontes de financiamento preenchidas e referências de evidência |
| Verificação de Governança | Unit (Python) | Nenhuma proposta ou meta de guidance possui status `validated` ou `ratified` automaticamente |

---

## Manual walkthrough

1. Iniciar o ambiente completo com as migrações aplicadas (`docker compose up -d --build`).
2. Acessar o dashboard no navegador (`http://localhost:3000`).
3. Rolar até a nova seção **Policy Lab — Carteira de Propostas Públicas**:
   - Confirmar a renderização dos 3 cards de propostas canônicas:
     1. Revisão do Gasto Obrigatório e Previdência
     2. Aceleração do Investimento em Infraestrutura
     3. Simplificação Tributária e Produtividade
   - Verificar a exibição do impacto fiscal anual (R$ bilhões / % PIB), fonte de financiamento e o badge de competência (ex.: "Poder Legislativo — PEC" ou "Poder Executivo — Decreto").
4. Clicar no botão **"Ver Detalhes e Mecanismo Causal"** de uma proposta:
   - Inspecionar a hipótese causal, o cenário contrafactual e as evidências empíricas citadas.
5. Rolar até a seção **Guidance Brasil (2027–2030)**:
   - Analisar a matriz de compromissos com as 4 colunas essenciais:
     - Baseline (período base e valor)
     - Meta Proposta (com badge explícito `Hipotética / Em Avaliação`)
     - Projeção do Modelo (Forecast)
     - Realizado Oficial (Actual)
   - Confirmar a presença visível do **Disclaimer de Governança e Neutralidade**, alertando sobre a natureza experimental e independente do projeto.

### Edge cases
- [ ] **Proposta sem vínculo direto a indicador único:** A proposta continua navegável e exibe seu mecanismo causal, mesmo sem um target indicator cadastrado.
- [ ] **Compromisso de Guidance sem dado realizado divulgado ainda:** A coluna `Realizado (Actual)` exibe estado neutro ("Aguardando divulgação oficial da fonte") sem quebrar a tabela.
- [ ] **Visualização em telas pequenas (Mobile):** Os cards do Policy Lab se reorganizam verticalmente e a tabela de Guidance ativa scroll horizontal suave sem truncar números ou rótulos.

---

## Tone check (if user-facing copy exists)

- [x] Toda a cópia segue estritamente o tom neutro, técnico e apartidário estabelecido em `specs/mission.md`.
- [x] Nenhuma proposta é atribuída a partidos políticos ou apresentada como promessa governamental oficial.
- [x] Todos os números são acompanhados de suas respectivas unidades (R$ bilhões, % do PIB, p.p.).
- [x] Nenhum texto provisório ou placeholder (`Lorem Ipsum` ou `TODO`) permanece na interface.

---

## Definition of done

- [ ] Todas as verificações automatizadas passam (`pytest`, `go test`, `go vet`, `npm run build`, `smoke.py`).
- [ ] Manual walkthrough executado localmente com sucesso.
- [ ] Descrição de PR referencia o diretório de especificação `specs/2026-10-29-phase-3-method-and-product/`.
- [ ] Roadmap e execution plan atualizados refletindo o progresso do Incremento 03.
- [ ] Código versionado na branch `phase-3-method-and-product` pronto para revisão técnica independente.
