# Integração opcional de voz Discord — 03/11/2026

Implementada como saída de voz dentro da Luna, com dependências separadas.
Inicialização manual, token e canal via .env; nenhuma biblioteca Discord é
importada antes de conectar. Bot sem intents de mensagens, conectado self_deaf.
Kokoro usa uma trava para síntese compartilhada e produz PCM 48 kHz estéreo.
Envio manual não toca na placa de som local. Comentários marcados como de jogo
podem ser transmitidos automaticamente quando o usuário ativa a opção.

## Evidência local

- 22 testes passaram: ponte simulada, segmentação, volume e catálogo de vozes.
- Após acrescentar teste da conversão real PCM, 14 testes focados passaram
  (incluem os seis da ponte, streaming e volume).
- 47 arquivos da suite JavaScript passaram antes e depois da interface.
- Edge/Playwright com API simulada: painel, conectar, compartilhar por ID,
  opção de jogos e sair passaram; captura inspecionada em
  `agents/tmp/piloto-web/discord-painel.png`.
- Casos cobertos: dependência/configuração opcional, fila limitada, rejeição de
  envio desconectado, bloqueio de proativo pessoal, conexão self_deaf, tamanho dos
  quadros, fechamento do cliente e descarte da fila em falha sem expor token.

## Validação real em 04/11/2026

O usuário configurou seu bot e confirmou áudio no canal após ajustar a dependência
davey para a série 0.1, compatível com discord.py 2.7.1. Com davey 0.2 o sinal PCM
era normal, mas a sessão DAVE permanecia sem criptografia pronta, gerando silêncio.
O requirements preserva a combinação compatível; a ponte aguarda a negociação.

Envio manual tem acompanhamento individual junto ao botão. Comentários automáticos
tocam também no PC; envio manual continua restrito ao Discord. O agente validou os
fluxos com conexão simulada e não iniciou a Luna nem transmitiu áudio no canal.
