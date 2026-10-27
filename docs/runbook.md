# Runbook local

## Ingestão e observabilidade

Execute os comandos do README. Cada execução registra raw hash, origem, momento de
captura, modo, status e erro. Captura inválida persiste em quarentena e emite
`DataQualityFailed`; nunca cria observações válidas. `BDF_TRACE_CONSOLE=1` imprime spans
OpenTelemetry locais. Não há collector, métricas Prometheus ou traces da API nesta fatia.

As credenciais declaradas são de desenvolvimento e os serviços só são publicados em
localhost. Não expor esse Compose à internet. A API tem somente SELECT; quem tem acesso
ao Docker/banco de desenvolvimento é operador de confiança. O papel dono do banco é
administrador; triggers append-only não substituem armazenamento WORM contra esse papel.

## Replay e recuperação de fila

O teste `test_revision_as_of_outbox_and_replay` marca eventos como pendentes e prova
que reprocessar não duplica outputs/alertas. O teste usa somente `bdf_test`.
Para falhas operacionais, inspecionar `outbox.last_error`, corrigir a causa e reencaminhar
**apenas os IDs afetados**, em transação e com registro de intervenção. Não reenfileirar
indiscriminadamente eventos antigos após novas capturas: replay operacional de histórico
fora de ordem ainda não tem um workflow auditado nesta versão.

Após três falhas, evento vira `dead_letter`; `bdf worker` retorna contagens. Não há daemon,
agendamento ou polling infinito. Um operador executa cada lote; backlog e dead-letter
ainda exigem consulta no banco. Falhas HTTP têm retries com backoff; worker terá backoff
persistido no próximo incremento. A CLI de fetch registra falha de origem no log, sem
persistir certificado de freshness. Painel sempre informa que a atualidade não foi verificada.

## Dados e modelo

Separação `mode=fixture|source` em todas as consultas e hashes. O modo padrão da API e
painel é `source`; exemplos sintéticos só aparecem ao escolhê-los explicitamente.
Os cenários são hipóteses contábeis com juros/crescimento/primário ilustrativos.
Limiar de 0,5 p.p. e SLA de 48h são configurações experimentais, não regras ratificadas.
Alertas permanecem `pending_human_review`; não existe ação de publicar/alterar Guidance.

## Limitações conhecidas

- `as_of` reconstitui o conhecimento capturado pelo sistema, não vintages anteriores à sua existência.
- O relógio `known_at` é atribuído dentro da transação, não um timestamp externo de publicação.
- Volumes pequenos; paginação e limites rígidos da API ainda pendentes.
- Banco registra conteúdo bruto; retenção, backup/restore e migração a objetos precisam validação.
- Calendários reais, fontes primárias completas, propostas públicas, backtesting e causalidade pendentes.
- CI valida funcionamento técnico; nenhum teste aprova metodologia econômica ou conteúdo público.
