# 🌙 Luna — Notas de Atualização

Diário de novidades da Luna, em linguagem de gente. Sempre que uma ideia
sai do papel, ela vira uma linha aqui (em vez de só sumir da lista de ideias).
Mais recente no topo.

Legenda: ✨ novo · 🔧 melhorado · 🐛 corrigido

---

## 01/08/2026

- 🐛 **A "retomar assuntos" parou de cutucar o modelo à toa.** Quando você não tinha nenhum
  assunto em aberto pra ela puxar, ela ficava perguntando pro modelo "tem pendência?" a cada
  ~30 segundos — mantendo ele aceso sem motivo e enchendo o log. Agora ela só re-checa de
  tempos em tempos. (Saiu de uma caçada de bug e tanto.)
- 🔧 **O log do terminal ficou bem mais legível.** Cada linha agora mostra a **hora**
  ([HH:MM:SS]), e as tarefas de fundo que consultam o modelo aparecem com **rótulo** (ex:
  "Retomar: checando pendência", "Memória: extraindo fatos"). Dá pra saber na hora o que a
  Luna tá fazendo por baixo — e se aparecer uma consulta sem rótulo, é bandeira pra investigar.

## 31/07/2026

- 🎮 ✨ **Ela te zoa (com carinho) quando você morre no LoL.** Durante a partida, ao tomar uma
  morte, a Luna comenta **na voz** — mas lendo o jogo de verdade: **quem te matou**, o **placar**
  dos times e o **matchup** da sua rota. E escolhe o tom pelos dados: **cutuca** quando você deu
  mole com o time ganhando (*"tá com 6 abates e ainda foi dar show pro Lee Sin?"*), ou **apoia
  como parceira de duo** quando tá osso de verdade (*"Kayle contra Zed no early é sofrimento,
  segura até teus itens"*). Ela até sabe que **suporte não farma** — não te cobra CS de support.
  Com juízo: fala só em **algumas** mortes (não em todas) e no máximo **3 por partida**, pra não
  encher. Usa a API **oficial** da Riot (a mesma dos overlays tipo Blitz) — **zero risco de ban**.
  Dá pra desligar no toggle **"LoL: comentar mortes"**. E ela sai **rápido** (o modelo fica quente
  durante a partida, pra não travar na hora da fala).
- 🔧 **A config de tarefas ficou organizada.** Os toggles das tarefas proativas — que eram uma
  lista corrida enorme e fácil de se perder — agora estão em **3 grupos**: 🎮 Jogos, ⏰ Rotina &
  avisos, e 💬 Conversa & interesses.

## 30/07/2026

- 🔧 **A Luna ficou bem mais afiada e menos "assistente genérica".** Um pacote de ajustes de
  personalidade, guiado pelo que apareceu no log real:
  - **Acabou o "carimbo".** Antes, quando você desabafava ou decidia algo, ela respondia com
    fórmula de biscoito da sorte (*"faz sentido, às vezes a gente..."*). Agora ela traz um
    **ângulo específico** do teu caso, nunca eco vazio.
  - **Ela discorda de verdade** e tem opinião própria — não concorda com tudo só pra agradar.
  - **Chega de saudação-recheio** (*"tô aqui, o que manda?"*): toda fala vem com um gancho real.
  - **Menos muleta:** ela abusava do *"Pois é"* pra abrir tudo — agora **varia** as aberturas.
- 🔧 **Ela sabe onde está falando e ajusta o tamanho.** No **Telegram**, quando o assunto é
  profundo, ela **desenvolve** o raciocínio; na **voz**, ela é **concisa** (pra você não ouvir um
  textão no áudio). Papo casual continua curto nos dois.
- 🔧 **"Olha minha tela" virou reação, não relatório.** Em vez de listar o que está aberto
  (*"vi que você está com X e Y..."*), ela **repara numa coisa e reage/cutuca**.
- 🐛 **Ela parou de negar que enxerga a tela.** Às vezes dizia que "não conseguia ver" mesmo
  tendo a ferramenta — corrigido (e o motor de visão passou a receber a instrução certa).

## 26/07/2026

- 🎮 **Ela entende melhor COMO você joga.** Ao **abrir** um jogo na Steam, agora ela sabe suas
  horas **totais** e as das **últimas 2 semanas** — e se você tá voltando a um jogo parado, ela
  comenta *"faz X que você não abria isso"*. Ao **fechar**, ela cita as conquistas que você
  destravou **pelo nome** (no máx duas + "e mais tantas", pra não metralhar), avisa quando você
  **platina** o jogo, e comemora quando você **cruza um marco** de horas (100, 200, 300…). E o
  melhor: se você **não** pegou conquista nenhuma, ela nem toca no assunto (chega de "nenhuma
  conquista nova pra você").
- 🔧 **Os GIFs pararam de ser genéricos.** Antes ela inventava o termo do GIF e às vezes caía
  num vídeo qualquer de "pessoa sentada numa pedra". Agora ela escolhe uma **reação** de uma
  lista curada (deboche, choque, cansaço, música, leitura…) e a gente traduz pro meme certo —
  bem mais na cara do momento.
- 🔧 **Ela não te metralha mais quando liga.** No boot, várias falas proativas (bom dia,
  retomar assunto, hábitos, novidades) saíam todas de uma vez. Agora sai **uma de cada vez**,
  com um respiro **variável** (1 a 2,5 min) entre elas — dá pra acompanhar sem susto.
- 🐛 **Novidades.md voltou pras colunas.** Um bug fazia o estilo se perder (as notícias viravam
  uma por linha, e o cabeçalho de configuração se duplicava no meio da nota). Agora elas
  **agrupam por dia** e fluem em colunas de novo.

## 25/07/2026

- ✨ **Ela lembra pelo ASSUNTO, não só pelo que é recente.** Antes a Luna só puxava as
  lembranças mais novas (por data). Agora, quando você toca num tema, ela resgata a lembrança
  antiga que combina — mesmo de meses atrás. Você fala "tava pensando em comprar um instrumento
  musical" e ela lembra que **você queria aprender violão**. (Por baixo: um modelo de linguagem
  multilíngue que entende português de verdade, com um freio alto — ela só puxa quando o
  assunto casa mesmo, pra nunca trazer a lembrança errada.)
- ✨ **A memória se organiza sozinha (esfria e esquenta).** Evento antigo que ninguém toca há
  mais de ~45 dias **esfria** e sai da lista principal (vai pro `Luna/Memoria_arquivo.md`),
  deixando o `Memoria.md` enxuto. Mas não some: se o assunto **volta à tona**, a lembrança
  **esquenta** e retorna sozinha. Nada é apagado — só sai da frente.
- ✨ **Ela retoma assunto em aberto por conta própria.** Se você tinha uma pendência ("vou
  tentar consertar o ventilador"), ela puxa depois: *"e aí, conseguiu resolver o ventilador?"*.
  Com juízo: **no máximo 2x por dia** (uma logo depois de ligar a Luna, outra uma boa folga
  depois), e **só coisa que você realmente falou** — ela nunca inventa uma pendência. Dá pra
  desligar no toggle **"Retomar assuntos"** (⚙ → Tarefas proativas).
- ✨ **Ela repara nos teus hábitos de jogo.** Sem te espionar nada: usa só o que a **Steam**
  já registra de tempo jogado nas últimas 2 semanas, e comenta um padrão de vez em quando —
  *"você anda jogando bem mais Hollow Knight"* ou *"faz um tempo que não abre o Deadlock"*.
  É sempre **número real** (nunca inventa), e **discreto** (no máx 1x por dia). Toggle
  **"Hábitos de jogo"** na config, e precisa da Steam configurada.

## 22/07/2026

- ✨ **Ela te ajuda COM o jogo, não só comenta.** Jogando e com uma dúvida, é só perguntar
  natural ("como faço pra fazer o trem andar?") que ela **saca sozinha** que é do jogo aberto,
  pesquisa na web escopado nele e te responde. Tem um freio esperto: se a busca não achar
  nada específico daquele jogo (comum em jogo obscuro/sem wiki), ela é **honesta** que não
  achou — nunca te dá dica de um jogo parecido achando que é o teu.
- 🔧 **"Olha minha tela" agora sabe qual jogo você tá jogando.** Quando ela analisa um print
  com um jogo aberto, avisa ao motor de visão qual é o jogo — aí ele reconhece a tela e
  responde bem mais certeiro.
- 🐛 **Trocar voz, velocidade e ligar/desligar o proativo pela config voltou a funcionar.**
  Um bug (introduzido junto com as teclas configuráveis) fazia esses ajustes serem ignorados
  no modo web — o botão do proativo ficava preso. Consertado.
- 🔧 **Menos "metralhada".** Quando você pede as novidades, ela agora **conta** conversando em
  vez de colar a nota crua. E consertos das suas avaliações 👎: não salva mais comentário
  casual como anotação, não "fala o roteiro" das falas automáticas, e não trava mais o
  contexto quando a conversa fica longa.
- 🔧 **Patch notes acessível pela config** (botão no rodapé do painel).

## 18/07/2026

- ✨ **Memória episódica — a Luna passou a lembrar do que anda acontecendo.** Além do
  perfil (quem você é) e das conversas (ChromaDB), agora tem uma camada nova: eventos
  datados, assuntos em aberto, humor da semana. Quando você sai do PC, ela **revisa as
  conversas sozinha e propõe lembranças**; um **badge roxo (pulsante)** acende no ⚙ e você
  **confirma ou descarta** cada uma numa caixa (🧠 Memória), podendo **editar** o texto
  antes de guardar. Nada é salvo sem sua aprovação (é o anti-alucinação). O que você guarda
  vai pro Obsidian (`Luna/Memoria.md`) e a Luna usa nas próximas conversas — com **o fato
  mais recente vencendo** o antigo quando conflitam. Tem botão **"Processar agora"** pra
  forçar, **lixo de 7 dias** pra desfazer descarte, e dá pra desligar a extração automática.
- 🔧 **Config web mais limpa** — saiu a seção "Comportamento" (o Proativo já tem botão na
  tela principal; a memória permanente antiga foi substituída pela episódica). Emojis novos
  nos títulos e painel um pouco mais largo.
- 🐛 **Bug do `modo_memoria`** — quando o modelo respondia um JSON direto (sem ferramenta),
  o texto estava sendo descartado. Consertado — era o que travava a extração de fatos.

## 17/07/2026

- ✨ **Config web virou central da Luna.** Painel novo com: **Oficina da fala**
  (digite e ouça na hora + dicionário de pronúncia editável que vale sem
  reiniciar), **atalhos** pra abrir avaliações/vistos/log/.env no PC, painel de
  **chaves** (mostra ✓/✗ de cada uma do .env, sem expor valor) e botão **📜**
  na tela principal que abre estas notas de atualização bonitinhas.
- 🐛 **Aviso de anime agora dispara de verdade quando o episódio SAI.** A lógica
  antiga olhava "vai sair hoje" e só tinha uma frestinha antes do episódio ir ao
  ar — quando ele saía, o AniList já pulava pro próximo e a Luna ficava muda
  (o ep 15 da 4ª temporada do Slime passou batido por isso). Agora ela detecta o
  último episódio que **já foi ao ar** (últimas 24h) e avisa que está no ar pra
  assistir.

## 13/07/2026

- ✨ **Novidades (radar) agora tem interruptor.** Igual aos animes: dá pra
  desligar o aviso de novidades na tela de config — útil pra ela não te cortar
  no meio de uma ligação. (De quebra, o botão dos **animes** que não estava
  respondendo ao clique foi consertado.)
- 🔧 **Ela fala mais sobre o jogo da Steam que você abre.** Além de horas e
  conquistas, agora puxa um detalhe específico — a história/premissa (extraída
  da descrição da loja), um prêmio ou um modo de jogo. Funciona pra qualquer
  jogo: se a página é magra, cai na descrição curta; se é gigante, não enrola.
- 🐛 **GIF do modo de espera saiu da mesmice.** O termo "desligando" só tinha
  2 GIFs no Giphy (sempre os mesmos); virou "sleeping", que tem centenas.
- 🔧 **Descrições da Steam vêm em português do Brasil** (antes vinham de
  Portugal, com "tu/conseguires").

## 12/07/2026

- ✨ **Aviso de lançamento de animes!** Você lista seus animes numa nota do
  Obsidian (`Luna/animes.md`) e a Luna avisa no dia em que sai episódio novo
  (fonte: AniList). Dá pra pôr apelido pra ela não tagarelar títulos gigantes:
  `- Nome enorme do anime | apelido`.
- 🔧 **"Boa noite" parou de aparecer em toda resposta** — agora é um por dia,
  o resto da conversa vai direto ao ponto.
- 🐛 **Promoção da wishlist não some mais.** Um bug fazia o aviso de promoção
  morrer se a Luna estivesse ocupada na hora; agora ele insiste até sair.

## 11/07/2026

- ✨ **Primeira novidade do radar vem com teaser.** Em vez de só "tem 3 novidades",
  a Luna já dá um resuminho de uma delas e avisa que tem mais na nota Novidades.
- 🔧 **Idle games não atrapalham mais.** Jogos que ficam sempre abertos (ex: Task
  Bar Hero) não disparam o comentário nem o "não perturbe".
- 🔧 **Botão do Proativo mais claro.** Quando desligado, agora fica 🔴 "Proativo
  DESLIGADO" em vermelho — fim do "cliquei sem querer e não percebi".
- 🔧 **"Troca de música" agora funciona de verdade.** A Luna toca a música com o
  álbum na fila (sempre tem próxima, sempre do artista certo), confere o que
  realmente ficou tocando antes de confirmar, e foi proibida de escolher sempre
  Blinding Lights quando a escolha é livre.
- 🔧 **Honestidade reforçada** (vinda das suas avaliações 👎): ela não alega mais
  ações que não fez ("já marquei o IPTU" sem conseguir editar notas), não promete
  "vou fazer", e cita os fatos exatos das ferramentas.
- 🔧 **Follow-up do proativo**: quando ela avisa algo por conta própria ("tem 2
  novidades no radar"), agora dá pra perguntar "quais são?" que ela sabe do que
  se trata.
- ✨ **Mensagem de voz no Telegram!** Agora dá pra mandar áudio pra Luna — ela
  transcreve local (Whisper, o mesmo ouvido do PC), mostra o que entendeu
  (🎤 "...") e responde normal. Áudio de +2min ela pede um mais curto.
- ✨ **Luna com humor mais afiado.** Sarcasmo, ironia e alfinetadas carinhosas
  entraram na personalidade — sempre do lado de quem gosta, nunca cruel.
- 🔧 **Agenda e emails agora são apresentados pela Luna de verdade** — ela conta
  os compromissos conversando ("quarta, 29 de julho às duas da tarde"), em vez de
  cuspir o texto cru da ferramenta com datas em formato de robô.
- 🔧 **Confirmação de foto salva no Obsidian com a voz dela** (web e Telegram) —
  antes era uma frase pronta sorteada pelo código.
- 🔧 **Proativo dos jogos alinhado ao humor novo** — fim do "analista frio";
  na Steam ela fala "2 horas e 12 minutos" em vez de "132 minutos".
- 🔧 **Autoconhecimento atualizado** — ela agora sabe da própria voz nova
  (Kokoro) e das tarefas proativas que estão ligadas.

## 09/07/2026

- ✨ **Voz nova!** A Luna trocou o motor de voz (do Supertonic pro **Kokoro**).
  Agora fala em pt-BR com a voz **Alpha** (aquele charme de "japonesa falando
  português") e com entonação natural de pergunta e exclamação. Dá pra trocar
  entre **Alpha, Bella e Nicole** na tela de configuração do modo web.
- 🐛 **Chega de "boa noite" em toda resposta.** Ela só te cumprimenta no começo
  da conversa ou quando ela mesma te chama (proativo). No meio do papo, responde
  direto.

## 08/07/2026

- ✨ **A Luna comenta seus jogos da Steam.** Quando você abre um jogo, ela fala
  algo (horas jogadas, conquistas); quando fecha, comenta a sessão (tempo jogado
  e conquistas novas daquela sessão).
- ✨ **Botão de repetir fala (▶️)** no modo web — clica e ela toca de novo a
  última coisa que falou, sem precisar gerar tudo outra vez.
- 🔧 **GIFs mais divertidos.** O filtro foi aberto pra trazer meme/anime/reação
  de verdade, no lugar de gente aleatória andando ou dando joinha.
- 🔧 **Ela pode falar um pouco mais** — respostas de até 4 frases quando o
  assunto pede.
- 🔧 **Imagens do "Novidades" (Obsidian) viraram miniatura** — parou de poluir a
  leitura das notícias.

## 07/07/2026

- 🔧 **Dicionário de pronúncia** — um jeito fácil de corrigir palavras que a voz
  fala errado (é só cadastrar a palavra e a grafia certa).
- 🐛 **Radar de RSS** — agora ele dá a volta na lista de feeds e mostra novidades
  de todos, não só de um.

## 06/07/2026

- ✨ **Letreiro de dicas** no modo web — mostra exemplos de comando embaixo do
  "Aguardando".
- ✨ **Dica no GIF** — passando o mouse no GIF, você vê o termo que a Luna usou
  pra buscar ele.

## 05/07/2026

- 🔧 **Luna ~5x mais rápida (modo mono).** Passou a usar um único modelo
  (Gemma-4-12B, no TurboLLM) pra tudo: decidir qual ferramenta usar E conversar.

## 01/07/2026

- 🔧 **Salvar nota no Obsidian ficou mais honesto** — a confirmação comenta o
  assunto de verdade, sem inventar nada.

## 30/06/2026

- ✨ **Autoconhecimento** — no proativo, a Luna comenta fatos reais sobre ela
  mesma (o próprio estado/configuração).

---

*Pra adicionar uma novidade nova: é só copiar o formato acima (data no topo,
✨/🔧/🐛 + uma frase). Ou pede pro Claude gerar a partir dos últimos commits.*
