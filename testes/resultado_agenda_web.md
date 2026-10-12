# Agenda visual na conversa — 09/10/2026

Ao consultar a agenda, a resposta da Luna vem acompanhada de um cartão com os eventos
confirmados pelo Google Calendar: data em cada bloco, horário inicial/final, dia inteiro,
local quando disponível e link para abrir o evento. O cartão também aparece ao criar
um compromisso, nos avisos de compromissos próximos e no bom dia.

Os dados visuais são montados em Python, separados da fala e preservados no histórico
da Web. Não é preciso adotar o OpenUI ou fazer outra chamada à LLM. A interface usa
os componentes e recursos locais da Luna. Comparações interativas ficaram na fila do TODO.

Revisão visual de 10/10: data e horário passaram para a primeira linha dentro do bloco
de cada compromisso. O intervalo longo no cabeçalho foi substituído por “Próximos 30 dias”
na consulta padrão; agenda de hoje e criação não repetem esse subtítulo. A origem Calendar
fica na mesma linha do título. Testes de cartões atualizados para conferir esse layout.

## Ajustes necessários no caminho da agenda

- O leitor continua devolvendo texto compatível com os consumidores existentes, mas
  transporta os eventos em metadados. O chat preserva esses metadados ao limpar a resposta.
- Datas com horário são convertidas para o fuso local da máquina da Luna. Eventos de
  dia inteiro preservam a data; o término exclusivo do Google é tratado corretamente.
- A consulta de 30 dias passa a usar UTC com fuso explícito. Antes, colar `Z` no relógio
  local deslocava a janela da consulta.
- O aviso proativo deixa de tentar extrair ISO de linhas com `|`: o leitor já escrevia
  datas por extenso com `—`, e os avisos não encontravam os compromissos. Agora usa os
  eventos estruturados e mostra apenas os que estão próximos.
- O bom dia filtra os eventos do dia atual; antes recebia a lista inteira de 30 dias
  sob o rótulo “agenda para hoje”.
- Só a persona da agenda no chat recebe a indicação de que os dados estão no cartão,
  com referência de hoje/amanhã e horários exatos. Os prompts anteriores de voz, Telegram,
  Dark Souls, notícias e conversa comum foram preservados.

## Validação

`node testes/rodar.js`: **45 arquivos passaram**, antes e depois da alteração na interface.
Cobertura nova no teste de cartões: agrupamento, ordenação, dia inteiro, término exclusivo,
virada de dia, local, links, ausência de eventos, limite e metadados inválidos.

**41 testes Python passaram**: agenda, cartões, briefing, pendências, recebimento Web,
sugestões de novidades e saída Web. Google Calendar simulado; nenhuma leitura ou criação
na conta real. O fluxo roteador → ferramenta → persona → legenda foi exercitado, incluindo
preservação dos cartões no chat/voz e isolamento do Telegram.

Montagem do prompt: **10 testes passaram, 39 cenários**. Os 34 cenários anteriores mantêm
os mesmos bytes; foram acrescentados cinco de agenda. O golden foi atualizado e conferido.
Os espaços finais em `Conversas anteriores: ` são parte do prompt original congelado.

Prévia inspecionada no Edge em 900 px e 420 px, sem transbordamento horizontal na largura
menor. Arquivo local: `logs/bancada_web/20261009-agenda-v2/preview.html`.

### Bancada com o Gemma 4 12B QAT

Três rodadas de sete gerações, com eventos fictícios: controle Web, consulta Web,
pergunta por período, agenda vazia, criação confirmada, voz e Telegram. Engine ROCm;
thinking desligado. Nenhuma execução de ferramenta no modelo real.

Nas duas primeiras rodadas, a pergunta “amanhã depois das 18h” recebeu uma resposta
incorreta de agenda vazia, mesmo havendo uma consulta às 19h. Repetir uma regra genérica
de conferência não resolveu. Acrescentar hoje/amanhã e as datas ISO confirmadas à
instrução desse caminho corrigiu o caso na terceira rodada:

> Você tem uma consulta marcada para amanhã, sábado, às 19h. Fora isso, não tem nada
> registrado depois das 18h.

A rodada final terminou as sete respostas sem cortes. No chat, a agenda vazia e a criação
foram respondidas corretamente. Consulta geral: 3.191 tokens de entrada no controle e
3.459 com o cartão/referência, **+268 tokens** para três eventos; 4,11 s e 4,19 s nesta
amostra. Isso não representa um aumento em todos os turnos da Luna.

Registros completos em `logs/bancada_web/20261009-agenda[-v2|-v3]/`. O placar acima
separa Web alterada dos controles de voz/Telegram; diferenças nestes últimos são variação
da geração. A amostra é pequena: não prova que o Gemma acertará toda pergunta sobre datas.
Os horários do cartão vêm diretamente do Calendar e não dependem dessa interpretação.

## Uso e limites

Reinicie a Luna e atualize a página. Peça **“Como está minha agenda?”**. Ao pedir a criação
de um compromisso, o cartão aparece após a confirmação da ferramenta, com o evento criado.
Os avisos dependem de as tarefas de agenda/bom dia já estarem ativadas.

A conexão Google precisa estar configurada. A consulta atual continua sendo a agenda
principal nos próximos 30 dias; o cartão mostra até 50 eventos e sinaliza quando houver
mais. Não busca páginas adicionais nem filtra automaticamente o cartão pela pergunta:
o período exibido é identificado no próprio cartão. Cada mensagem guarda uma fotografia
da consulta; alterações posteriores no Calendar exigem nova consulta.

Briefing/pendências mantêm seus consumidores de texto existentes. Na voz, a apresentação
oral continua pelo caminho atual, e o cartão acompanha a legenda na Web. A bancada não
valida qualidade por escuta nem substitui o teste com os compromissos reais.
