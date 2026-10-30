# Validation — Phase 1: Painéis de Realizado vs. Baseline, Forecast, Target e Cenário de Continuidade

## Automated

- [ ] `pytest tests/test_trajectories.py` e testes de contratos passam sem erros.
- [ ] `go test -v ./...` e `go vet ./...` no diretório `services/api` executam com sucesso.
- [ ] `npm run build` no diretório `web` conclui sem erros de tipagem TypeScript ou de lint.
- [ ] `git diff --check` não acusa espaços em branco espúrios ou problemas de formatação.
- [ ] `python scripts/smoke.py` valida as rotas `/v1/trajectories` e a consistência das 5 curvas.

### Key assertions

| Behaviour | Test type | Expected result |
|-----------|-----------|-----------------|
| `GET /v1/trajectories?indicator_id=br.ipca.12m` | integration (Go) | Retorna status 200, metadados do IPCA e lista ordenada de períodos com as 5 trajetórias |
| Filtro temporal `as_of` | integration (Go) | Oculta ou marca como indisponíveis realizações e revisões posteriores ao corte temporal fornecido |
| Bandas de incerteza do forecast | unit (Python / Go) | Garante que `forecast_lower <= forecast_value <= forecast_upper` para todos os pontos com projeção |
| Indicador inexistente | integration (Go) | Retorna status 404 Not Found com mensagem padronizada |
| Fallback para fixtures | integration (Next.js / API) | Interface renderiza trajetórias herméticas quando o backend está em modo de fixture |

## Manual walkthrough

1. Iniciar os serviços com `docker compose up -d` ou executar localmente a API Go (`PORT=8080 go run main.go`) e a interface Next.js (`npm run dev`).
2. Acessar `http://localhost:3000` e navegar até a seção "Observatório Econômico — Trajetórias Macroeconômicas".
3. Alternar entre os 6 indicadores P0 (IPCA, Selic, Dívida/PIB, PIB Trimestral, Câmbio PTAX, Desemprego) e verificar a transição das curvas.
4. Passar o cursor sobre os pontos do gráfico vetorial e inspecionar os valores pontuais de Realizado, Baseline, Forecast, Target e Continuidade no tooltip.
5. Conferir a presença visual dos badges "Oficial", "Meta CMN / LDO", "Ilustrativo / Não-oficial" e "Cenário Inercial".
6. Abrir a tabela colapsável de desvios e verificar o cálculo correto do delta entre a meta/projeção e o realizado nos períodos passados.
7. Simular a alteração da data de corte `as_of` e observar a contração da curva de realizado no passado.

### Edge cases

- [ ] **Período futuro sem realizado:** Pontos posteriores à data de publicação oficial devem manter `actual_value = null`, exibindo apenas as curvas de projeção e meta sem quebra visual no gráfico.
- [ ] **Indicador sem meta oficial estipulada:** Exemplo do Câmbio PTAX em regime de câmbio flutuante, onde `target_value = null` — a curva de target não deve ser renderizada, exibindo badge indicando ausência de meta formal.
- [ ] **Falha ou indisponibilidade da API:** O componente da interface deve exibir estado de erro elegante com fallback transparente para fixtures demonstradoras.

## Tone check (specs/mission.md)

- [ ] Todas as projeções e estimativas futuras são rotuladas explicitamente como "Ilustrativas / Em calibração".
- [ ] A terminologia de desvio evita juízos políticos ou morais ("positivo", "negativo", "fracasso", "sucesso"), atendo-se a "acima da meta", "abaixo da projeção" e magnitude percentual.
- [ ] Metadados de proveniência (fonte e data da última coleta) estão visíveis e clicáveis.

## Definition of done

- [ ] Todos os testes automatizados (pytest, go test, npm build) passam com 100% de sucesso.
- [ ] Walkthrough manual executado confirmando renderização responsiva em desktop e mobile.
- [ ] Migração de banco de dados `db/007_trajectory_comparisons.sql` testada no ambiente isolado `bdf_test`.
- [ ] Pull Request aberto e referenciando os documentos vinculantes desta especificação (`requirements.md`, `plan.md`, `validation.md`).
- [ ] Itens do Roadmap correspondentes atualizados.
