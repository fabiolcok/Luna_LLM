# 🌙 Luna — Notas de Atualização

Diário de novidades da Luna, em linguagem de gente. Sempre que uma ideia
sai do papel, ela vira uma linha aqui (em vez de só sumir da lista de ideias).
Mais recente no topo.

Legenda: ✨ novo · 🔧 melhorado · 🐛 corrigido

---

## 21/08/2026

- 🗣️ 🔧 **A voz começou a responder sem esperar o texto inteiro.** No modo Web por voz, a
  persona entrega frases completas ao sintetizador enquanto continua gerando a resposta. O botão
  de parar também interrompe a geração e mantém no chat o trecho já recebido, marcado como
  interrompido.

- 🎮 🐛 **Comentários sobre um jogo não viram mais pedidos de tutorial.** A consulta de gameplay
  agora exige uma prova literal na mensagem atual; o histórico ajuda a identificar o jogo e
  sustenta continuações curtas, mas não transforma progresso ou opinião em pergunta inventada.

- 💬 ✨ **A conversa Web ficou mais viva e confortável de ler.** A resposta textual da Luna
  agora aparece em streaming com o antigo efeito de braille, balões suaves ancorados no rodapé
  e rolagem que respeita quem voltou para ler mensagens anteriores. O texto ganhou cores menos
  luminosas, Markdown seguro, cópia e controles compactos; o nome técnico da ferramenta ficou
  disponível apenas no hover do mascote para ajudar no diagnóstico sem poluir a conversa.

- 🌘 🔧 **Falas espontâneas agora explicam de onde vieram.** Cada balão iniciado pela própria
  Luna mostra discretamente a tarefa proativa responsável, como `radar_rss` ou `checar_agenda`.
  Ferramentas pedidas pelo usuário continuam fora do rótulo para não transformar o chat em log.

- 🔎 🔧 **O tamanho da conversa agora se adapta ao monitor.** Um controle nas configurações
  permite reduzir ou ampliar o texto e guarda a preferência neste PC. Os nomes “VOCÊ” e “LUNA”
  também ganharam mais destaque para separar melhor quem está falando.

## 20/08/2026

- 💬 🔧 **O modo web agora tem uma conversa de verdade.** Os turnos aparecem numa área
  principal com rolagem, seleção e cópia, sem esconder o papo numa gaveta lateral. Respostas e
  notas também renderizam parágrafos, listas, links, código e tabelas Markdown de forma segura.
  O antigo “Pensamento” virou “Detalhes” dentro da fala mais recente e levou as métricas junto.

## 18/08/2026

- 🧠 🔧 **O thinking agora pertence à persona, não ao roteador.** Quando ativado no
  seletor de modelo, a resposta final recebe espaço para raciocinar sem atrasar nem confundir a
  escolha de ferramentas. O limite maior é apenas um teto; as respostas continuam orientadas a ser curtas.

- 🪞 🔧 **O autoconhecimento deixou de interromper e passou a responder com código real.**
  A observação aleatória sobre horas ligada, voz e quantidade de ferramentas saiu dos proativos.
  Quando perguntada sobre o próprio funcionamento, a Luna agora consulta trechos atuais e seguros
  da implementação, sem abrir configurações, dados pessoais ou caminhos arbitrários.

## 17/08/2026

- 🎮 ✨ **A rotina de jogos agora entende o que você conta sobre cada jogo.** Declarações
  explícitas de que zerou, abandonou ou está jogando e opiniões ditas na conversa ficam no histórico
  local daquele título. A Luna não deduz gosto por horas jogadas e só recebe esse contexto quando
  o próprio jogo estiver envolvido.

- 📝 🐛 **Anotações no Obsidian ficaram mais limpas.** Pedidos com `título:` e
  `conteúdo:` salvam somente a nota de verdade, sem levar junto a introdução nem o comando.
  Quando o pedido é “boa ideia, deixa anotado”, a Luna usa a fala anterior da conversa e também
  registra corretamente se o pedido veio do web, da voz ou do Telegram.

- 🧪 🔧 **Os testes ganharam uma revisão completa em um comando.** O runner completo
  valida interface e backend juntos, mantendo o teste rápido da presença separado para o dia a dia.

- ☑️ ✨ **A Luna agora conclui tarefas no Obsidian com confirmação.** Pedidos para marcar uma
  checkbox como feita ou uma conta como paga localizam a linha exata e aguardam um “sim” por
  botão, texto, voz ou Telegram antes de trocar `[ ]` por `[x]`. Ambiguidades, decisões vencidas
  e notas alteradas durante a espera são recusadas sem mexer no arquivo.

- ✅ ✨ **“O que tenho pendente?” agora olha nos lugares certos.** A consulta reúne tarefas
  abertas do Obsidian, compromissos futuros da agenda e acompanhamentos esperando desfecho,
  mantendo cada categoria separada. Quando o pedido cita contas ou outro assunto específico,
  a busca fica restrita à nota relacionada e ignora checkboxes já concluídas.

- 💬 🔧 **Textos maiores ganharam espaço para respirar.** Respostas desenvolvidas no web e no
  Telegram passam a separar ideias em parágrafos curtos. A caixa de escrita do web também aceita
  várias linhas com `Shift+Enter` e cresce até um limite sem deformar a interface.

- 🌅 ✨ **“O que tem pra mim hoje?” virou um briefing de verdade.** A Luna reúne clima, agenda,
  animes, acompanhamentos, novidades e promoções, escolhe poucos destaques e termina abrindo
  espaço para continuar a conversa. Consultar o resumo não consome os avisos automáticos.

- 🎮 ✨ **A rotina dos jogos começou a ganhar memória própria.** Aberturas, fechamentos e tempo
  observado ficam registrados apenas neste PC. Em alguns marcos de uso, a reação ao abrir um
  jogo pode considerar essa convivência sem criar uma segunda fala nem entupir o modelo de dados.

## 14/08/2026

- 🧟 🐛 **A guarda de recursos reconhece o Python da própria Luna.** O processo `python3.12`
  entrou na lista branca e não será mais anunciado como consumidor externo ao abrir um jogo.

- 🌒 🔧 **O proativo agora percebe o clima em que está entrando.** As duas últimas falas reais
  ajudam a evitar uma interrupção deslocada e permitem continuidade quando houver relação direta,
  sem entregar o histórico inteiro nem deixar a rotina autônoma abandonar a própria tarefa.

- ⚡ 🔧 **O roteador parou de conversar escondido.** Quando nenhuma ferramenta é necessária,
  a primeira chamada agora devolve apenas um marcador curto, com orçamento próprio, em vez de
  gastar a geração escrevendo uma resposta que seria descartada. Saudações simples também ficam
  leves e presentes, sem puxar backlog, trabalho ou memória sem relação.

- 🪐 🐛 **As órbitas não carregam mais o embalo para outras animações.** Ao sair do fidget
  para digitar, usar uma ferramenta ou abrir o radar proativo, as bolinhas zeram a rotação e
  a força centrífuga antes de assumir a formação própria do novo estado.

## 13/08/2026

- 🖱️ ✨ **A órbita virou um fidget.** Com o cursor sobre a Luna em repouso, a rodinha do mouse
  dá embalo às bolinhas: movimentos seguidos acumulam velocidade, a direção pode ser invertida
  e o giro desacelera sozinho sem roubar o scroll do restante da página. Em alta velocidade,
  as bolinhas ficam brancas e deixam pequenas caudas luminosas de cometa. O primeiro giro já
  clareia a órbita, mas alcançar o efeito máximo agora exige bem mais embalo; a força centrífuga
  também afasta o anel depois que ele ganha embalo, mantendo o raio normal nas velocidades baixas.

- 🪟 🔧 **A janela principal lembra onde ficou.** Ao mover ou redimensionar o modo web, a
  posição e o tamanho ficam salvos apenas neste PC e são restaurados na próxima abertura.

- ⌨️ ✨ **Responder por texto ganhou movimento próprio.** Quando não usa voz, a Luna leva as
  quatro bolinhas grandes suavemente até a base, pisca cada uma em branco num ritmo irregular
  e acompanha a escrita com o rosto, antes de voltar ao repouso.

- 📊 ✨ **As ferramentas agora deixam um placar local.** Cada uso registra sucesso ou erro,
  duração e canal; quando uma resposta recebe 👍 ou 👎, a nota também entra na conta daquela
  ferramenta. O resumo fica em `logs/uso_ferramentas_resumo.json`, sem salvar argumentos nem
  retornos das integrações.

- 🎌 ✨ **Agora dá para perguntar pelos animes.** Além do aviso automático, a Luna consulta
  a pedido os episódios recentes da lista `animes.md` ou um anime citado, incluindo o próximo
  episódio quando houver previsão, sem consumir nem silenciar o alerta proativo. A apresentação
  também fica presa aos dados encontrados, evitando a persona transformar um resultado válido
  em um falso erro de consulta.

- 🌙 🔧 **O widget ficou mais ajustável e atento.** No clique direito dá para alternar se ele
  fica sempre no topo e escolher tamanho pequeno, normal ou grande; tudo fica lembrado neste
  PC. A Luna também percebe o cursor se aproximando fora da janelinha transparente, e o gesto
  de arrastar ficou menos propenso a virar um cutucão acidental.

- 💬 🐛 **Texto digitado voltou a aparecer no CMD.** A resposta do modo web continuava na
  interface, mas o terminal só imprimia falas que passavam pelo TTS. Agora respostas digitadas
  ganham um banner próprio no diagnóstico, sem começar a tocar áudio por conta disso.

- 🧠 🔧 **Trocar o cérebro não exige mais editar Python.** O modelo local pode ser escolhido
  por `MODELO_LLM` no `.env`, e `MODELO_THINKING` decide se o raciocínio fica ligado,
  desligado ou por conta do próprio modelo. O Gemma continua sendo o padrão quando ambos
  ficam como vieram, e o diagnóstico mostra a escolha realmente carregada. Com o `.env`
  vazio, a configuração web lista a biblioteca do TurboLLM e troca o modelo na hora; a opção
  fica salva só naquele PC e pode voltar ao Gemma pelo item padrão.

- 🧊 🐛 **Modelo frio não exige mais abrir o TurboLLM na mão.** Se o prazo de ociosidade
  descarregar o modelo, a Luna agora pede o carregamento pela API do próprio TurboLLM, espera
  ele ficar pronto e repete a solicitação uma vez. Outros erros 503 continuam visíveis em vez
  de entrarem num ciclo de tentativas.

- 🌙 ✨ **A Luna pode sair da janela e ficar na área de trabalho.** Um botão destaca o mascote
  como widget transparente, sempre visível e arrastável. O clique direito oferece o caminho de
  volta, e a posição escolhida fica guardada para a próxima vez.

- 🎭 🔧 **O widget continua sendo a mesma Luna.** Estados, ferramentas, expressões, interações
  e acontecimentos visuais acompanham o mascote que estiver aparecendo, sem reiniciar os
  relógios ao alternar entre a janela e a área de trabalho. O laboratório também controla a
  cópia visível, e o tamanho agora é consistente nos dois modos.

---

## 11/08/2026

- 🤝 ✨ **Ela pode acompanhar como uma situação terminou.** Quando existe um desfecho concreto
  pela frente, a Luna pode oferecer perguntar depois. Ela só guarda o acompanhamento após
  confirmação por botão, texto ou voz, e isso fica separado da agenda e da memória. Quando chega
  a hora, pergunta naturalmente como ficou e permite resolver, adiar ou esquecer o assunto.

- 🎭 🐛 **O mascote parou de ficar eternamente "ouvindo".** Enquanto aguardava o atalho de voz,
  a interface mostrava a animação de escuta como se o microfone estivesse gravando. Agora ela
  repousa enquanto espera, fica atenta ao pressionar o PTT, pensa ao processar e volta ao idle
  depois de falar. Os comandos rápidos, como pausar ou avançar a música, também fecham esse
  ciclo corretamente. O CMD mostra cada transição visual para facilitar o diagnóstico.

- 👂 🔧 **Ouvir agora parece ouvir.** Em vez de apenas girar um pouco mais rápido que o idle,
  a periferia se recolhe, as 12 partículas pequenas ficam discretas, as quatro grandes pulsam
  como sensores e os arcos respiram como uma membrana. Fica fácil distinguir escuta de repouso.

- 🎮 🔧 **O modo jogo ficou mais vivo e ganhou identidade própria.** A cabeça usa violeta
  elétrico estável — o verde continua sendo a assinatura da música —, os quatro pixels principais
  ficaram maiores e a órbita alterna trechos lentos e rápidos. A expressão concentrada `ᓀ‸ᓂ`
  também deixou de piscar.

- 📡 ✨ **Novidades agora aparecem no radar.** Enquanto RSS, promoções ou animes são
  preparados, uma linha de sonar varre a cabeça com rastro luminoso. As partículas ficam no
  escuro e as quatro principais acendem em branco quando a varredura alcança cada uma. A cara
  `⇀‸↼` acompanha o radar e a animação sai quando ela começa a falar.

- 💭 🔧 **Pensar e falar ganharam mais movimento.** O pensamento agora usa `◐_◑` e
  pisca brevemente durante o processamento. Na fala, o rosto faz uma microarticulação vertical
  rápida e curta, sem virar a dança mais ampla do modo música.

- 😌 🐛 **Olho fechado não pisca duas vezes.** A cara `ᗒᗜᗕ` já representa olhos
  fechados, mas o mecanismo de piscada ainda a transformava brevemente em `-ᗜ-`. Ela entrou
  na curadoria das expressões que não piscam.

- 🪶 🐛 **O próprio modelo deixou de ser acusado de gastar memória.** O aviso de recursos ao
  abrir um jogo ignorava os inicializadores da Luna, mas não o executável real `llama-server`.
  Como o 12B sempre ocupa muita RAM por definição, ele entrou na lista branca; outros programas
  realmente pesados continuam aparecendo no aviso.

---

## 10/08/2026

- 🙂 🔧 **As caras dela foram limpas.** Passei uma peneira: caiu quem tinha "olho" que não lia
  como olho (acento solto, três curvas sem rosto), e cada cara ganhou uma decisão explícita de
  **piscar ou não**. A regra que apareceu sozinha: olho que já está fechado ou franzido não tem
  o que fechar — piscar ali vira um tremeliqueLe sem leitura.
  - 👄 *E a boca?* Tentei dar uma boca separada pra ela — primeiro desenhada em vetor, depois em
    2-3 quadros de caractere. **Não ficou boa em nenhuma das duas** e voltei atrás: o rosto
    continua sendo o kaomoji inteiro. Ficou a limpeza das caras, que veio junto, e o `°ᯅ°` do
    medo funcionando direito de novo.

- 🪐 ✨ **Ela agora tem problemas.** De vez em quando **acontece alguma coisa com ela** na
  interface — e some quando você resolve. Cada uma pede um jeito diferente de mexer com ela, e
  descobrir qual é metade da graça. Não vou contar. 👀
  - Se você **ignorar** por tempo demais, tem consequência. Essa também não vou contar.

- 🔧 **Ritmo.** As coisas acontecem **bem mais espaçadas** e não se amontoam mais: existe um
  intervalo mínimo entre elas e um teto de quantas podem estar rolando junto. Antes, dois minutos
  fora e você voltava pra uma bagunça.

- 🐛 **O modo suspenso pedia GIF ao Giphy.** Sobrou de quando a reação era GIF: toda vez que ela
  suspendia, aparecia uma imagem aleatória embaixo dela. Era o último chamador vivo — saiu.

- 🐛 **Instalar em outra máquina não funcionava.** Meu irmão foi rodar a Luna na casa dele e
  descobriu três coisas de uma vez:
  - Os **atalhos** tinham o caminho da minha máquina cravado. Em qualquer outro lugar o `cd`
    falhava, o ambiente virtual não era ativado e o erro que aparecia (`No module named
    'webview'`) não tinha nada a ver com a causa. Agora eles se localizam sozinhos e avisam
    direito quando falta o `venv`.
  - O **`.env.example`** derrubava a Luna: um `int()` no `TELEGRAM_CHAT_ID` estourava com o
    texto de exemplo, na importação. Uma feature *opcional* matando o app inteiro. Agora
    placeholder e vazio são a mesma coisa — não configurado.
  - O **nome do modelo** era exigido exato. Nem toda versão do TurboLLM deixa batizar o modelo,
    e aí ele precisava carregar na mão toda vez. Agora a Luna **descobre** qual id o servidor
    expõe; se não achar, ela **lista o que tem** em vez de só reclamar.

---

## 09/08/2026

- 🌙 ✨ **A Luna ganhou um rosto.** O GIF do Giphy saiu e no lugar dela existe uma **presença**
  no topo da tela: uma cabeça que respira, um rosto no meio dela, três arcos girando e dezesseis
  bolinhas em órbita. Não é enfeite — é o **estado dela em tempo real**. Ela fica de um jeito
  quando está ouvindo, de outro pensando, de outro falando. E dorme quando você some.
  - **Ela pisca.** Parece bobo, mas era o que faltava: personagem que não pisca parece morto.
  - **Ela te olha.** O rosto acompanha o mouse pela tela. E quando você não está mexendo em
    nada, ela **divaga sozinha** — dá uma espiada pra um lado, segura, volta.
  - **Ela responde ao toque.** Não vou dizer como. 🙂
- 🎨 ✨ **Ela mostra o que está fazendo.** Cada ferramenta muda a cor e o comportamento da
  periferia — mas nunca o rosto nem a cabeça, que são a identidade dela:
  - 🎵 **Spotify:** fica verde, as bolinhas viram um equalizador e ela **balança a cabeça** no ritmo.
  - 🔍 **Pesquisa na web:** azul claro, com ondas de radar saindo dela e as bolinhas piscando em sequência.
  - 👁️ **Ver a tela:** branco, com uma linha de **scanner** varrendo a cabeça.
  - 🎬 **Resumir vídeo/site:** vermelho, e o anel "engole" o conteúdo.
  - 🎮 **Jogando:** um **controle orbita ela e passa por trás da cabeça**, aparece uma barra de
    vida, as bolinhas viram **pixels quadrados** e a cara fica concentrada (`◺_◿`).
- 🌌 ✨ **A tela dela muda com a hora do dia** — e, de vez em quando, acontece alguma coisa que
  ninguém pediu. Ficam por sua conta descobrir. (Tem umas quantas.)
- 🥺 ✨ **Ela sente sua falta.** Se você sumir por um bom tempo e voltar, dá pra perceber.
- 🔡 🔧 **O texto aparece diferente.** A Luna e você agora "materializam" a fala a partir de um
  ruído em braile que vai se resolvendo da esquerda pra direita, no lugar da máquina de escrever.
- 🖥️ 🔧 **A tela parou de pular.** Antes, cada linha que a Luna escrevia reposicionava a página
  inteira (o conteúdo era centralizado verticalmente). Agora fica ancorado no topo.
- 🐛 **Correções que saíram no caminho:** o roteador engolia a tag do rosto antes da hora; sobrava
  pedaço de carinha na fala (e o TTS lia "japanese symbol"); as bolinhas entravam dentro da
  cabeça em alguns estados; e um erro de JavaScript no carregamento chegou a **derrubar a
  interface inteira** por alguns minutos.

> 💡 **Como o rosto é escolhido:** o modelo só diz o *clima* da fala (`[clima:zoeira]`,
> `[clima:carinho]`…) e o Python escolhe a carinha, revezando entre as do grupo. Deixar o
> modelo desenhar dava carinha quebrada, formato inconsistente e sempre as mesmas três.
> Escolher uma palavra ele faz bem — desenhar, não.

## 08/08/2026

- ⌨️ ✨ **Agora dá pra DIGITAR pra ela no modo web.** Apareceu uma caixa de texto embaixo do
  bloco "Você": escreve, aperta Enter, e ela responde **só por escrito** (sem falar em voz alta),
  com a mesma liberdade de tamanho que ela tem no Telegram. É a mesma conversa da voz — dá pra
  falar uma coisa e digitar a próxima sem perder o fio. Bom pra quando você não quer (ou não pode)
  falar em voz alta.
- 📍 ✨ **Ela sabe se você está no PC ou fora.** Voz e caixa de texto = você está na máquina;
  Telegram = você provavelmente está no celular, longe do PC. Antes ela sugeria "vai revisar o
  sistema no PC?" com você **na rua** — porque o contexto dela olhava o programa aberto no
  computador e concluía que você estava sentado lá. Agora, quando você fala pelo Telegram, ela
  para de olhar o estado do PC e só sugere coisa que dá pra fazer no celular.
- 🎭 🔧 **A Luna ficou menos previsível.** Ela tinha virado meio "disco riscado": mesma estrutura,
  mesmo tipo de resposta, e — o que você mesmo pegou no log — **9 de 10 respostas terminavam com
  pergunta**. Agora ela foge do óbvio (pega ângulos que você não vê vir, varia o registro, crava
  a posição em vez de ficar em cima do muro) e **deixa a fala pousar** em vez de devolver a bola
  toda vez. Com um freio importante: quando você está pra baixo (cansaço, estresse, saúde), ela
  **acolhe primeiro** — a ousadia fica pra outra hora.
- 🎮 🔧 **O briefing de Overwatch parou de repetir a mesma coisa.** Ele recitava o rank e o winrate
  de **carreira** toda vez — e carreira não muda, então era sempre "Silver support, 51%, se
  esforça". Agora, ao **abrir**, ela sorteia um ângulo diferente (cutuca um herói específico,
  compara seus roles, comenta um marco, ou só solta uma zoeira sem número) e nunca repete o
  anterior. E ao **fechar**, ela comenta **a sessão de hoje** (quantas partidas, vitórias, qual
  herói você mais jogou) em vez da carreira.
- 🌅 🐛 **As falas proativas pararam de sumir caladas.** Tinha um problema silencioso: no primeiro
  minuto depois de ligar, o modelo ainda está esquentando e várias tarefas querem falar ao mesmo
  tempo — a fala era engolida. Pior: em alguns casos a Luna **escrevia a novidade na nota e
  marcava como avisada**, mas a voz nunca saía (você via o card no Obsidian sem ter ouvido nada).
  Agora ela espera o boot assentar e, se a fala não sair, **tenta de novo** em vez de desistir
  em silêncio.
- 🎌 🐛 **Aviso de anime mais confiável.** Ela só checava a cada 6h *e* só quando você estava
  presente e fora de jogo — na prática, poucas checagens por dia. Além disso, só avisava de
  episódio que saiu nas últimas 24h, então bastava um dia de PC desligado pra perder. Agora
  checa a cada 2h e lembra por 3 dias.
- 🌚 🐛 **Ela parou de perguntar a mesma coisa todo dia.** A lista de assuntos já retomados
  zerava à meia-noite, então um projeto em andamento virava "pendência nova" todo santo dia
  (*"e aí, como tá o LUNA_LLM?"*, diariamente). Agora ela lembra do que já perguntou por 3
  semanas, e aprendeu a diferença entre uma **pendência com fim** ("consertou o PC?") e uma
  **atividade contínua** (um projeto, um jogo) — dessa última ela não fica cobrando desfecho.
- 🗣️ 🐛 **Ela parou de ler markdown em voz alta.** Quando ia contar as novidades, às vezes
  despejava o arquivo cru — "cssclasses, novidades-grid, colchete exclamação tip..." — porque a
  proteção contra isso procurava um formato de data antigo e tinha parado de funcionar em
  silêncio. Agora ela reconhece essas notas pelo formato do card e **conta conversando**.
- 🧟 ✨ **Um toque quando algo está comendo memória.** Ao abrir um jogo, se algum programa
  estiver consumindo muita RAM, ela avisa — **só avisa**. Nunca fecha nada, nunca oferece fechar,
  e ignora o que é do sistema, o banco de dados do trabalho e o navegador (que é onde você
  trabalha).
- 🧹 🔧 **Faxina de ferramentas.** Saíram o "abrir programa" e o "matar processo" — heranças da
  época de tentar fazer um Jarvis, que você nunca usava e que ainda por cima **atrapalhavam**:
  o "abrir programa" disparava sozinho quando você só *mencionava* abrir alguma coisa. Menos
  ferramenta morta = ela acerta mais na hora de decidir o que usar.
- 🖥️ 🔧 **A tela do web foi reorganizada.** Ficou dividida em duas zonas: em cima tudo que é da
  Luna (resposta, status dela, pensamento, métricas), embaixo tudo que é seu (o que você disse,
  microfone, caixa de texto). Antes as duas formas de falar com ela — mic e teclado — ficavam em
  cantos opostos da tela.
- 🔍 🔧 **A caixa "Pensamento" virou um raio-X.** Além da ferramenta usada, agora mostra os
  **argumentos** que ela mandou e, quando nenhuma ferramenta é acionada, o que o roteador
  "pensou" antes de ficar quieto. Serve pra entender por que ela às vezes faz algo inesperado —
  sem precisar caçar no log.
- 📖 ✨ **Guia de instalação do zero** ([`INSTALACAO.md`](INSTALACAO.md)): passo a passo pra
  alguém (ou você, depois de formatar) botar a Luna pra rodar — TurboLLM, modelos, cada chave de
  API e onde pegar, extensão do Firefox, e os erros comuns.

## 03/08/2026

- 🛒 ✨ **A Luna agora caça promoções pra você no Telegram.** Em vez de raspar Kabum/Terabyte
  (que vivem bloqueando isso e davam manutenção sem fim), ela lê os **canais de promoção**
  que você segue — como se fosse você olhando. Você entra nos canais, e numa nota do Obsidian
  (`RastrearPromocoes.md`) lista os **@ dos canais** + as **palavras-chave** dos produtos que
  te interessam. Quando cai uma oferta que bate, ela **te avisa na voz** e monta um **card**
  numa página `Promocoes.md` — com **foto do produto**, preço e link. Casa por palavra (ignora
  acento/maiúscula), **semeia canal novo em silêncio** (não despeja o histórico todo na 1ª vez)
  e **limpa promoção velha depois de 7 dias** pra não encher o HD. Liga/desliga no toggle
  **"Promoções (Telegram)"**. (Precisa de um login único no Telegram — instruções no `.env.example`.)
- 🎙️ ✨ **Ela começou a perceber o TOM da tua voz.** Um modelo de emoção acústica lê a **energia**
  da tua fala e, quando você soa mais **pra baixo/cansado** ou mais **animado** que o teu normal,
  ela ajusta sutilmente o **jeito** de responder — sem nunca virar o assunto pra "como você tá"
  (colore o *como*, não o *quê*). Só na voz, e ela aprende teu "normal" sozinha (recalibra a cada
  dia). É uma camada fininha, que vai afinando com o uso.

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
