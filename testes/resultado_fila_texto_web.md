# Recebimento e espera do texto na web

Data: 2026-10-09.

## Diagnóstico

No log persistido, a primeira mensagem desse episódio foi recebida às 09:43:48
e começou a ser atendida às 09:43:59. As demais foram recebidas entre 09:43:51
e 09:43:55, mas o terminal só as mostrava quando cada execução começava.
A confirmação limpava a caixa antes de existir qualquer balão para essa entrada.

O relato começa às 09:43:11. O registro disponível não explica sozinho o tempo
anterior ao recebimento das 09:43:48; portanto, não atribuímos os 30–40 segundos
inteiros à geração do modelo ou a uma conexão travada.

Dois atrasos adicionais existiam no código: uma espera visual de 4–9 segundos
depois de publicar cada resposta digitada e envios de WebSocket feitos sob as
travas de clientes/execução. Um navegador que deixasse de receber podia segurar
outros clientes e a reserva da conversa. Esse segundo cenário foi simulado no teste.

## Correção

- Entradas aceitas aparecem imediatamente na conversa com “recebida · aguardando
  resposta”. A fila não altera o usuário associado à geração em andamento.
- Cada entrada recebe um identificador. O início, o streaming e a resposta final
  ocupam o mesmo lugar; responder à primeira não remove as seguintes.
- Reconexão e recarga recuperam os textos ainda pendentes, junto com o histórico.
- Cada conexão tem um envio independente, ordenado e limitado a 128 eventos.
  Uma conexão travada não segura a reserva do usuário nem outra janela; excesso
  de eventos encerra a conexão para o cliente reconectar.
- A pausa visual foi retirada do handler de texto. O log agora separa o instante
  de recebimento do início da execução e informa os segundos de espera na fila.

Essas mudanças não fazem chamadas extras à LLM nem alteram o descarregamento por
ociosidade. Uma inferência já em andamento ainda pode precisar liberar a engine;
essa espera fica visível. A fila existe na memória do processo, não sobrevive a
fechar a Luna e não reenvia automaticamente mensagens sem confirmação.

## Validação

`node testes/rodar.js`: 44 arquivos passaram antes da mudança e 45 depois,
incluindo entradas sucessivas, streaming, resposta anterior à confirmação,
reconexão e preservação de resposta interrompida.

Na rodada completa de Python foram executados 325 testes. Três fixtures que
extraem funções por AST precisaram receber o novo contexto de mensagem web;
nenhuma asserção foi removida. Após esse ajuste, os 80 testes dos módulos
afetados passaram, incluindo as três fixtures, o transporte WebSocket real,
associação de resposta, proatividade ocupada, conexão lenta e fila de saída cheia.

A validação usou servidor de teste em porta temporária. A instância da Luna em
uso não foi reiniciada. O episódio de 30–40 segundos ainda requer observação
no uso real após reiniciar a Luna com esta versão.
