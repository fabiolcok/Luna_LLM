# Dark Souls — reação à morte sem contagem

Validação de 26/09/2026. O proativo deixa de receber `mortes_sessao` e `incremento`
no briefing e o total de mortes no bloco MOMENTO. O prompt orienta a não numerar
mortes ou tentativas, inclusive quando uma fala anterior menciona números.
O detector, os intervalos e a prioridade dos eventos permanecem iguais.

## Verificação automática

- 49 testes do piloto, MOMENTO, execuções e bancada passaram.
- O teste do pedido completo varia os contadores internos de 1/1 para 9876/4321:
  as mensagens enviadas ao modelo ficam idênticas, para morte, chefe e fogueira.
- A leitura de morte continua gerando evento; o jogo continua reconhecido sem
  eventos recentes. O contexto reativo Web/voz mantém a informação anterior.
- Os cinco testes de montagem preservam o golden. Os 39 arquivos de testes Node passaram.

## Bancada com modelo

Modelo selecionado: Mistral NeMo 12B Abliterated Q4_K_M, TurboLLM 1.13.4,
llama.cpp b9608 ROCm. Thinking desligado, quatro mortes e um chefe, sem áudio
ou execução de ferramentas. Todas as chamadas usam `ENXUTO_PROATIVO + EMOCAO`.

Na rodada final, as quatro mortes produziram fala **sem contagem** (2,9–3,4 s).
A quarta também recebeu uma fala antiga sobre a “décima morte” na antirrepetição.
O teste de chefe citou Taurus Demon sem total de mortes (3,7 s), mas não deixou
clara a vitória. A qualidade continua limitada: repetiu “Ai, morreu de novo!”
e analogias de escalada, mesmo recebendo as falas recentes para não repetir.
O ajuste trata a contagem; estes resultados não demonstram melhora de criatividade.

Na primeira redação experimental, uma ordem genérica para reagir à morte também
estava presente em eventos de chefe. Foi retirada antes da rodada final. Numa
comparação adicional, com mesmo histórico e seed, o prompt anterior disse
“138 mortes só nessa sessão”; o ajustado reconheceu a derrota de Taurus Demon
sem contar mortes. Ainda inventou velocidade/estratégia e retornou duas tags de
clima: questões de qualidade fora do ajuste de contagem.

Registros locais, ignorados pelo Git:

- `logs/dark_souls/sem-contagem-20260926-173855.json` — rodada final completa.
- `logs/dark_souls/comparacao-chefe-sem-contagem.json` — comparação com o prompt anterior.

Não mede FPS, entrega de voz ou comportamento durante uma sessão real.
