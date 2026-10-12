# Mudança de tom em 11/10/2026

## Calibração rejeitada e revertida

O ajuste posterior usou gatilhos por palavras-chave e três assuntos fixos.
O usuário rejeitou essa abordagem e pediu a volta ao estado anterior.
Os gatilhos, assuntos e instruções adicionais foram retirados. O resultado
4/4 em convites específicos não demonstrava recuperação da conversa natural;
destacá-lo como sucesso exagerou o alcance do experimento. A causa da mudança
súbita continua desconhecida. O [relatório](resultado_conversa_completa.md)
fica apenas como registro do experimento descartado.

## Após o reinício das 20:20: tom continua irregular

O log confirma nova inicialização às 20:20:52, após a restauração do EMOCAO
original. A chamada das 20:21 usa sistema com 11.263 caracteres, perfil com 507
e histórico vazio. Para `ta complicado...`, a resposta foi de acolhimento,
ligando a fala ao trecho do perfil sobre estar "só vivendo".

Foi executado um controle de quatro respostas: duas seeds pareadas, com o
perfil atual e retirando somente seu texto da mensagem `system`. A montagem
usou o EMOCAO original, demais fontes vazias e a mesma mensagem sem histórico.
Modelo, engine e configuração permaneceram iguais durante as chamadas.

- Com perfil, houve referências a estar "sobrevivendo" ao dia e à rotina de
  suporte. Sem perfil, essas referências deram lugar a suposições genéricas
  sobre frustração ou acúmulo de problemas.
- As quatro respostas permaneceram no registro de acolhimento. Retirar o
  perfil não recuperou a acidez nesse caso; portanto, ele não explica sozinho
  esse comportamento. Também não torna as respostas plenamente fiéis: as
  duas variantes presumiram problemas que não estavam na mensagem.

Um controle adicional manteve o prompt completo e o perfil atual, mas usou
uma situação leve explícita: `Passei quarenta minutos escolhendo um jogo e
perdi a vontade de jogar.` Nas duas seeds, apareceram imagens como transformar
o lazer em "um segundo trabalho de curadoria" ou "ergonomia mental". O humor
não ficou inteiramente ausente, porém continuou misturado a explicação e
suposições sobre motivos. Ambas abriram com "O clássico" e uma referência à
paralisia de análise; não foram tratadas como prova de criatividade recuperada.

`ta complicado...` pode ser interpretado pelo modelo como assunto pesado,
para o qual o EMOCAO manda acolher sem cutucar. Isso é uma hipótese compatível
com as respostas, não um diagnóstico do que o usuário sentia. Nenhum gatilho
Python de modo sensível foi acionado: a captura confirmou PROMPT_COMPLETO.
O resultado não identifica a causa histórica da mudança súbita de tom.

As seis respostas terminaram com `stop`, sem ferramenta ou raciocínio oculto.
Snapshots em `logs/diagnostico_tom_20261011/apos_restauracao_perfil.json` e
`apos_restauracao_controle.json`. Nenhuma regra de produção foi modificada.

## Teste das 20:10: EMOCAO entrou na montagem

O usuário substituiu temporariamente o bloco por
`- HUMOR E ACIDEZ (o seu registro) Literalmente Glados` e reiniciou a Luna.
O log registra inicialização às 20:09:21 e respostas ainda genéricas às 20:10.

A captura isolada de `_reescrever_como_luna`, interceptando a chamada antes de
enviar ao modelo, confirmou que a mensagem `system` contém o EMOCAO integral.
Com a mesma mensagem, histórico e fontes sintéticas, trocar o bloco alterou
somente esse trecho: as demais mensagens e os parâmetros permaneceram iguais.

| Medida | Original | Substituição |
|---|---:|---:|
| Caracteres do EMOCAO | 1.853 | 53 |
| Sistema do proativo registrado no log | 4.078 | 2.278 |

As duas diferenças são exatamente **1.800 caracteres**. A redução observada no
processo real corresponde à substituição feita pelo usuário; a hipótese de o
EMOCAO não carregar não é sustentada por esse teste. O pedido histórico completo
das 20:10 não está salvo: a captura é uma verificação da montagem atual, e o log
do proativo é a evidência complementar da versão carregada naquela sessão.

O arquivo já tinha o bloco original restaurado quando foi inspecionado, com
gravação às 20:13:02, posterior à inicialização do processo Python às 20:08:57.
O módulo é importado uma vez, sem recarga automática. Restaurar o arquivo exige
reiniciar a Luna para aplicar a versão restaurada naquele processo.

Carregar a instrução e seguir seu estilo são questões distintas. Esse teste não
identifica por que o modelo continuou genérico nem demonstra que outra posição
do bloco resolveria. Nenhuma alteração na persona ou na ordem dos blocos foi
aplicada nesta verificação. Medidas salvas em
`logs/diagnostico_tom_20261011/carregamento_emocao.json`.

## Novo achado: saudação recupera um assunto indevido

No teste das 19:45, após editar o perfil e limpar o ChromaDB novamente, o log
mostrou perfil de 507 caracteres, assuntos de 123 caracteres e histórico vazio.
Foi identificada uma falha concreta na recuperação de assuntos:

- Consulta: `Boa noite.`
- Assunto selecionado: `Compra de Notebook`.
- Estado: busca um notebook para plantões com foco em boa bateria ou baixo
  consumo de energia.
- Único termo coincidente: `boa`; pontuação 0,67, acima do piso 0,5.

Esse assunto vem de `modelos/assuntos_em_andamento.json`, independente do
ChromaDB e do perfil do Obsidian. Assim, limpar o índice não remove esse dado.
A frase sobre tranquilidade tinha outra origem: o perfil editado continha
“Nada, hoje estrou tranquilo”. Portanto, esse trecho da resposta tinha uma
fonte; não era evidência de uma conversa antiga que tivesse escapado da limpeza.

Correção aplicada em `modulos/assuntos.py`: retirar o cumprimento inicial
antes de pesquisar assuntos. Uma saudação pura retorna contexto vazio; uma
saudação seguida de pedido explícito continua pesquisando o conteúdo do pedido.

O teste reproduziu a seleção indevida antes da correção. Depois dela, a consulta
ao arquivo real retorna contexto vazio para `Boa noite.` e mantém a recuperação
para `Boa noite, e o notebook?`. Passaram 16 testes Python de assuntos e montagem
e os 46 arquivos do conjunto Node. O golden do prompt permaneceu igual.

Esse bug explica a entrada indevida de dados de notebook/plantão na chamada
das 19:45. Não demonstra que tenha causado o tom genérico das 17:16: ali o
log não mostrava o bloco de assuntos. A melhoria da personalidade ainda precisa
ser observada em uso; a correção não foi tratada como solução de todo o relato.

## Resultado da investigação

Foi confirmada uma quebra de continuidade após o reinício da Luna. Não foi
encontrada mudança no prompt comum ou troca de modelo que explique a passagem
repentina para respostas genéricas. A causa exata da escolha do tom na primeira
resposta das 17:16 permanece indeterminada: não há registro do pedido completo
e dos parâmetros efetivamente recebidos pelo engine naquela chamada.

A bancada de posição do EMOCAO mede um comportamento reproduzível, mas não
identifica a causa histórica desta mudança. Não é evidência suficiente para
adicionar uma regra de conversa casual como correção dessa ocorrência.

## Linha do tempo real

Horários locais de São Paulo, correlacionados com `logs/luna.log`, as respostas
completas em `logs/biblioteca_web.json` e `api_usage` do banco local do TurboLLM.
Os registros do TurboLLM estão em UTC; foi aplicada a diferença de três horas.

| Horário | Ocorrência | Entrada real da persona, em tokens |
|---|---|---:|
| 15:25:37 | Reinício da Luna | — |
| 15:28:14 | `ola` → “Boa tarde! Como é que tá esse ânimo hoje?” | 3.436 |
| 15:37:24 | `ta tenso.... plantao ainda` → comentário sobre a calmaria/caos do suporte | 3.562 |
| 15:59:27 | Notícia da GOG com zoeira sobre a biblioteca de jogos | — |
| 16:30:58 | Outro reinício da Luna | — |
| 17:16:17 | `opa` → “Boa tarde! No que eu posso te ajudar agora?” | 3.441 |
| 17:17:16 | `nada so conversando` → descanso antes da semana de plantão | 3.558 |
| 17:17:41 | `e o que faremos?` → oferta vaga de companhia | 3.631 |
| 17:54:00 | Outro reinício | — |
| 18:05:16 | `boa tarde` → pergunta sobre descanso após o plantão | 3.615 |
| 18:55:49 | `to pensando em comer algo` → conselho de alimentação ligado ao plantão | 3.735 |

Os dois primeiros cumprimentos de cada sessão tinham sistema com 11.373
caracteres e memória de 514 caracteres. Não houve aumento do tamanho do
sistema entre eles. A contagem real da requisição inteira também ficou próxima.

## O que foi conferido

- As 11 respostas reativas analisadas usaram a mesma chave de modelo: Gemma 4
  12B IT QAT Q4_0, arquivo de 6.975.878.560 bytes. Isso foi confirmado no banco
  do TurboLLM, e não deduzido apenas do nome exibido pela Luna.
- As bancadas salvas antes e depois registram a mesma engine b9608 ROCm,
  contexto 8.192, top-k 64, top-p aproximadamente 0,95, min-p aproximadamente
  0,05 e repeat penalty 1. Os processos mudaram. Esses snapshots não provam
  todos os parâmetros de cada chamada histórica; não apareceu evidência de
  alteração de configuração no intervalo.
- Nenhuma definição preexistente de `prompts.py` mudou em relação ao HEAD de
  09/10. As adições são funções e blocos condicionais de recursos da web.
- Dos 44 cenários do golden salvo antes da calibração da biblioteca, apenas
  `resposta_mensagem_web` difere do golden atual. Os cenários comuns permanecem
  idênticos. A referência a mensagem antiga depende de uma seleção explícita.
- Reconstrução de 11 mensagens reais, usando os mesmos dados de entrada no
  `pensar.py` do HEAD e no atual: **11 pedidos idênticos**, incluindo sistema,
  histórico, instruções e parâmetros. Data, janela e fontes foram controladas;
  isso compara as versões do código, não recupera os pedidos históricos reais.
- O perfil atual tem 514 caracteres e não é alterado desde 05/10 às 09:46.
  Contém “Foco da semana: semana de plantao.” Não diz que o plantão ainda vai
  começar. A palavra “chegando” foi interpretação da resposta das 17:17.

## O que o reinício muda

`main.py` inicializa `_historico_conversa = []`. O arquivo da busca de conversas
não repovoa essa lista. Assim, após o reinício das 16:30, a fala das 15:37 sobre
já estar de plantão saiu do histórico imediato. O perfil continuou disponível.

A abertura com tom de atendimento e as respostas seguintes passam a compor
o novo histórico e podem influenciar as próximas gerações. Essa é uma hipótese
para a continuidade do tom genérico, não uma causa demonstrada para a primeira
resposta. Também houve reinício às 15:25, antes da conversa considerada melhor:
reiniciar não implica, por si só, perder personalidade.

## Limite da conclusão

O TurboLLM está configurado com `captureBodies: false`; o log da Luna daquele
intervalo guarda tamanho, caminho de prompt e começo da resposta, mas não o
pedido integral. O diagnóstico das avaliações só é persistido quando avaliado,
e o arquivo de avaliações não contém essas interações de 11/10.

Portanto, não há base para afirmar que uma regra foi esquecida por posição,
que o contexto encheu, que a busca poluiu a chamada ou que um ajuste específico
de amostragem mudou naquele instante. O próximo dado necessário, se repetir,
é o pedido integral das duas situações, junto com os parâmetros do engine.

Nenhuma regra de personalidade foi alterada nesta investigação. Validação:
11 reconstruções equivalentes e `node testes/rodar.js`, 46 arquivos aprovados.
Evidência local filtrada em `logs/diagnostico_tom_20261011/`:
`comparacao_montagem.json` e `uso_turbollm.json`.
