# Validation — Pilot Hardening & Operational Resilience (Incremento 04)

## Automated

- [x] `pytest tests/` passa com os testes de integridade da cadeia de auditoria e métricas dos 4 planos
- [x] `go test ./...` e `go vet ./...` no diretório `services/api` passam sem avisos ou erros
- [x] `npm run build` e typecheck no diretório `web/` passam limpos sem erros
- [ ] `python3 scripts/smoke.py` valida com sucesso a API local, RBAC (401/403/200), rate limiting (429), paginação e os novos endpoints
- [x] `bash scripts/backup_restore_test.sh` completa com êxito a rotina de dump, restore em banco de teste e verificação de integridade
- [x] Novos testes cobrem:
  - Rejeição de requisições sem autenticação em rotas administrativas (HTTP 401)
  - Bloqueio de ação de `producer` em endpoints que exigem `reviewer` ou `publisher` (HTTP 403)
  - Ativação do rate limiting com resposta HTTP 429 e cabeçalho `Retry-After`
  - Paginação consistente com retorno de metadados (`limit`, `offset`, `total`, `has_more`)
  - Integridade da cadeia de hashes encadeados na tabela `decision_audit_log`
  - Resposta consistente e completa do endpoint `/v1/observability/metrics` cobrindo os 4 planos

### Key assertions
| Behaviour | Test type | Expected result |
|---|---|---|
| Acesso não autenticado a rotas admin | Integration (Go) | `POST /v1/admin/audit/decisions` sem credencial retorna HTTP 401 Unauthorized |
| Controle de Acesso RBAC insuficiente | Integration (Go) | `POST /v1/admin/audit/decisions` com papel `producer` retorna HTTP 403 Forbidden |
| Registro de Decisão Autorizado | Integration (Go) | `POST /v1/admin/audit/decisions` com papel `reviewer` ou `publisher` retorna HTTP 201 Created |
| Integridade da Trilha de Auditoria | Unit (Python) | Modificação retroativa de registro quebra a verificação SHA-256 de `prev_log_hash` |
| Rate Limiting Excedido | Integration (Go) | Rajada de requisições excedendo a cota retorna HTTP 429 com `Retry-After` |
| Paginação de Observações e Alertas | Integration (Go) | `GET /v1/observations?limit=2&offset=0` retorna exatamente 2 itens e `has_more: true` |
| Telemetria dos Quatro Planos | Integration (Go) | `GET /v1/observability/metrics` retorna HTTP 200 com blocos `platform`, `data`, `models` e `decisions` |
| Resiliência de Backup e Restauração | Script (Bash/Postgres) | Dump e restore em `bdf_test` restaura 100% dos dados com contagens idênticas |

---

## Manual walkthrough

1. Iniciar o ambiente completo com as novas migrações (`docker compose up -d --build`).
2. Acessar a aplicação no navegador em `http://localhost:3000`.
3. Inspecionar a nova barra superior de governança:
   - Localizar o `<RoleSwitcherBadge>` indicando o papel ativo atual (padrão: `Visitante / Público`).
   - Clicar para alternar para o papel `Revisor` e depois `Publicador`.
4. Rolar até a seção **Observabilidade e Saúde Operacional (Quatro Planos)**:
   - Confirmar a exibição dos 4 quadrantes:
     1. *Plataforma:* Uptime, status da base de dados e taxa de erro.
     2. *Dados:* Frescor relativo ao calendário oficial, contagem de séries e integridade de contratos.
     3. *Modelos:* Estabilidade de cenários e parâmetros calibrados ativos.
     4. *Decisões:* Total de decisões registradas, alertas sob revisão e integridade da trilha imutável.
5. Clicar no botão **"Inspecionar Trilha de Auditoria de Decisões"**:
   - Abrir o modal `<DecisionAuditTrailModal>`.
   - Verificar os registros cronológicos com ator, papel, ação realizada, justificativa e hash criptográfico.
   - Confirmar que usuários com papel `Visitante` ou `Produtor` visualizam a trilha em modo somente-leitura.
6. Testar o rate limiting e paginação:
   - Verificar na listagem de observações a navegação suave por páginas.

### Edge cases
- [ ] **Token ou credencial malformada:** Retorna HTTP 401 com mensagem JSON estruturada e explicativa.
- [ ] **Rajada de tráfego rápido:** Bloqueia temporariamente apenas o cliente causador (HTTP 429), liberando após o período de janela deslizante sem afetar outros usuários.
- [ ] **Inserção concorrente na auditoria:** Preserva a consistência sequencial de hash com lock transacional no último registro.
- [ ] **Página além do limite (`offset > total`):** Retorna array vazio `[]` e `has_more: false` sem gerar erro de servidor.

---

## Tone check (if user-facing copy exists)

- [x] Toda a cópia segue o padrão neutro, institucional e auditável estabelecido em `specs/mission.md`.
- [x] Termos técnicos de governança e segurança são apresentados com clareza (ex.: papéis e responsabilidades explicitados).
- [x] Nenhum texto provisório ou placeholder (`TODO`, `Lorem Ipsum`) permanece na interface.

---

## Definition of done

- [ ] Todas as verificações automatizadas passam (`pytest`, `go test`, `go vet`, `npm run build`, `smoke.py`, `backup_restore_test.sh`).
- [ ] Manual walkthrough executado localmente com sucesso.
- [ ] Descrição de PR referencia o diretório de especificação `specs/2026-10-29-phase-4-pilot-hardening/`.
- [ ] Roadmap e execution plan atualizados refletindo o progresso do Incremento 04.
- [ ] Código versionado na branch `phase-4-pilot-hardening` pronto para revisão técnica independente.
