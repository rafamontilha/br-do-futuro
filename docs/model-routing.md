# Roteamento de modelos e economia de contexto

Data: 2026-10-27. Política operacional proposta para este projeto.
Não constitui medição de consumo, promessa de economia ou mudança automática do modelo da conversa.

| Modelo | Trabalho preferencial | Esforço inicial | Escalar quando |
|---|---|---|---|
| GPT-6.1 Sol | implementação de ponta a ponta, contratos, integração, testes, PRs | medium | duas tentativas fundamentadas falham ou aparece ambiguidade arquitetural |
| GPT-6 Astra | arquitetura difícil, invariantes temporais, identificação causal, revisão de riscos metodológicos | high, apenas no trecho crítico | exigir análise humana quando for decisão econômica/material |
| GPT-6 Luna | documentação a partir de evidências, triagem, ajustes repetitivos bem delimitados, catálogo | low/medium | houver comportamento transacional, decisões de domínio ou mudanças em múltiplas camadas |
| GPT-6.1 Terra | inspeção visual, operação de navegador, acessibilidade visual e correções locais de interface | medium | problema exigir redesenho arquitetural ou investigação de dados |

## Regras de execução

1. Sol como ponto de partida para desenvolvimento. Não chamar os quatro modelos para a mesma tarefa.
2. Enviar missão resumida, critérios de aceite, arquivos relevantes e resultado dos testes; evitar repetir toda a constituição.
3. Luna recebe tarefas pequenas com entrada e saída verificáveis. Não decide validade causal ou licença de dados.
4. Astra revisa o problema crítico e os invariantes, não reescreve mudanças rotineiras já verificadas.
5. Terra valida o resultado salvo/renderizado; não confundir sucesso de clique com sucesso do sistema.
6. Testes determinísticos e checksums comprovam propriedades mecânicas sem novas rodadas de LLM.
7. Registrar modelo, esforço, motivo de escalada, validação e consumo **quando disponibilizado**. Consumo não disponível fica `unknown`.
8. Reutilizar artefatos, resumir decisões e evitar duplicar trabalho. Paralelismo de agentes somente quando autorizado.
9. Avaliar custo por entrega aceita e retrabalho, não apenas quantidade de tokens.
10. Aprovação metodológica humana continua necessária independentemente do modelo.

## Aplicação ao roadmap

- Fundação e integrações: Sol; revisão pontual de bitemporalidade/outbox: Astra.
- Catálogo e documentação: Luna após contrato definido por Sol e validação humana de fontes.
- Painéis e inspeção responsiva: Terra, com regras de dados e aceitação já especificadas.
- Policy Lab, causalidade e comparação de cenários: Astra como apoio; especialista humano aprova.
- Manutenção de baixo risco: Luna; investigação que cruza serviços: Sol.

Fundamento: [guia oficial de seleção de modelos](https://developers.openai.com/api/docs/guides/model-selection),
consultado em 2026-10-27. A divisão acima é nossa aplicação prática dessa orientação.
Não usa preços de API para inferir consumo ou limites da assinatura Codex.
