# Pendências

Lista curta de experimentos que ainda precisam de validação humana antes de virarem decisão
definitiva. Itens daqui não estão automaticamente aprovados para commit.

## Em teste

- [ ] **HAL 9000 no lugar do perfil LUNA.** Implementado em 16/10: nível 1 com
      registro calmo, preciso e impassível, incluindo modos enxutos e proativos.
      O nome da assistente continua Luna nos quatro perfis; corrigida a identidade
      do GLaDOS e do padrão do modelo. TARS preservado. Identidade conferida em
      quatro respostas reais; avaliar naturalidade e humor no uso, sem tomar a
      amostra pequena como aprovação definitiva. [Bancada](testes/resultado_hal9000.md).

- [ ] **Responder a mensagens, biblioteca do radar, busca e imagens ampliadas.** Implementados
      em 11/10: controles discretos acima da conversa, seleção de referência sem apagar o
      rascunho, consultas locais sem LLM e biblioteca com lidas/não lidas. Histórico salvo
      limitado a 1.000 turnos; 300 notícias/promoções, incluindo as notas atuais do Obsidian.
      Validar no uso após reiniciar a Luna. [Bancada e uso](testes/resultado_consulta_web.md).

- [ ] **Cadastro de fontes pela conversa, interesses no radar e leitura das respostas.**
      Implementados em 10/10: pedido com link prepara um cartão editável; somente o clique
      confirma o monitor. Interesse e situação usam trechos literais, sem objetivo inventado.
      “Afinar radar” salva palavras para mais/menos destaque sem mudar as avaliações ou
      apagar notícias da nota. Botão de ouvir em cada resposta usa Kokoro, volume atual e
      cede a uma conversa nova, sem chamar a LLM. Validar após reiniciar a Luna.
      [Bancada e uso](testes/resultado_fontes_interesses_voz.md).
      Resumo do que aconteceu na ausência fica adiado: estudar agrupamento dos avisos
      já coletados, sem novas gerações ou captura de tela durante jogos.

- [ ] **Agenda visual na conversa.** Implementada em 09/10: compromissos do Google Calendar
      agrupados por dia, horários, dia inteiro, local e link para abrir o evento. Aparece
      ao consultar/criar compromissos e nos avisos proativos da agenda. Cartão montado
      pelo Python, sem chamada extra à LLM. Validar com a agenda real após reiniciar.
      Bancada e limites em [resultado_agenda_web.md](testes/resultado_agenda_web.md).

- [ ] **Acompanhamentos com fontes cadastradas.** Implementado em 07/10: assunto, interesse,
      situação opcional e até três links no painel Web. Primeira leitura silenciosa, consulta
      a cada 6h, análise de conteúdo novo com evidência literal e avisos respeitando conversa
      e jogos. RSS/Atom, HTML e texto; pause/retome/edite e confira as fontes no painel.
      Validar relevância, fontes escolhidas e naturalidade no uso real. A memória e o
      contexto de todos os turnos não recebem a lista de cadastros. Guia e bancada em
      [resultado_acompanhamento_fontes.md](testes/resultado_acompanhamento_fontes.md).

- [ ] **Piloto de acompanhamento Sopro/PT-BR.** Implementado em 05/10: painel Web com situação
      editável, pausa, encerramento, consulta manual e adiamento de convites. Consulta documentação,
      releases do GitHub e card do modelo no Hugging Face a cada 6h enquanto a Luna está aberta.
      Primeira leitura silenciosa; versões e PT-PT sozinhos não geram convite. Menção nova vira
      evidência com link, sem concluir que o sotaque foi resolvido. Usa o proativo existente,
      com prioridade da conversa e silêncio durante jogos. Validar utilidade e naturalidade
      no uso real; manter Kokoro até aprovação por escuta. Guia e limites em
      [resultado_acompanhamento_sopro.md](testes/resultado_acompanhamento_sopro.md).

- [ ] **Piloto no Dark Souls Remastered.** Mortes, chefes e fogueiras integrados em 23/09.
      Leitura real validada; transições, expiração, troca de save e prioridade cobertas por
      testes. Na primeira sessão, a fala de morte saiu; a vitória sobre Taurus Demon
      foi detectada e gerou 69 tokens em 12,3 s, mas não foi falada. O usuário permaneceu
      no jogo; o log antigo não informa a causa. Diagnóstico de descarte e controle Web
      adicionados em 24/09. Validar a próxima vitória com esses registros e continuar
      avaliando humor, frequência, latência e FPS/engasgos.
      Comparação de thinking em 24/09: 16 gerações; ligado manteve a repetição, teve
      mediana de 58,7 s e 3/8 respostas vazias por limite de tokens. Desligado: 2,9 s,
      8/8 falas, com dois erros de contagem. Produção mantida sem thinking. Resultado
      e limites em `testes/resultado_dark_souls_thinking.md`.
      Guia em `integracoes/dark_souls/README.md`.
      DS1 PTDE, DS2 e DS3 ainda não estão integrados ao piloto.

- [ ] **Contexto do momento (item 1).** Implementado em 20/09: janela atual, jogos com fonte
      e validade, última fala recente e isolamento do Telegram. Reaproveita os monitores,
      sem nova chamada LLM ou captura de tela. Teto de 800 caracteres; +146 caracteres no
      cenário neutro do prompt completo. Validar no uso real após abrir/fechar jogos, alternar
      janelas e retomar conversa depois de uma pausa. A detecção não revela placar ou ações
      dentro do jogo. Bancada e limites em `testes/resultado_momento.md`.

- [ ] **Avaliações V2 no uso real.** Web permite categorias e comentário opcional nos dois votos.
      O alvo fica preso à resposta, mesmo se o radar falar enquanto o motivo é escrito. Registros
      novos incluem trechos de contexto, caminho de prompt, modelo e origem; o relatório
      `testes/resumo_avaliacoes.py` consolida as revisões sem duplicar o voto. Categorias servem
      para escolher casos de regressão e comparar mudanças; não alteram a personalidade sozinhas.
  - Bancada de continuidade de 19/09: 20 respostas, sem ganho nos checks ao acrescentar um
    lembrete de referência ou retirar a conversa da notícia. Com título presente, ela ainda
    inventou anos; com ano fornecido, acertou o ano, mas uma resposta inventou o gênero.
    Prompts preservados. Resultado e limites em `testes/resultado_continuidade.md`.

- [ ] **Retomar Pocket TTS somente quando houver uma boa voz feminina PT-BR.** A bancada
      `testes/bancada_tts.py` confirmou streaming muito rápido, mas ainda não justifica trocar o
      Kokoro. O `portuguese_24l` soa melhor que o modelo leve, porém roda perto ou abaixo de tempo
      real e varia volume, duração e encerramento entre gerações; temperatura `0.5` foi a menos
      problemática. A amostra da Keila manteve sotaque brasileiro, mas saiu muito baixa; vozes
      estrangeiras do catálogo Kyutai tiveram volume melhor e sotaque ruim em português. Próximo
      teste: procurar uma referência feminina brasileira, conversacional, limpa, com 15–30 segundos
      e licença CC0 ou CC BY; comparar no 24l/t0.5 com normalização, sem integrar antes da aprovação.

- [ ] **Validar assuntos em andamento.** Projetos confirmados na curadoria ficam em estado local,
      separados de memória e acompanhamento. Confirmar no uso real se a Luna retoma o ponto certo
      quando o tema volta, atualiza o mesmo fio e não transforma assunto em tarefa ou cobrança.

- [ ] **Validar limpeza do `salvar_obsidian`.** Mensagens com `título:`/`conteúdo:` não devem
      guardar introdução nem comando; reação curta como “boa ideia, deixa anotado” deve salvar
      a fala anterior da conversa. A origem precisa distinguir web, Telegram e voz.

- [ ] **Validar contexto recente nas falas proativas.**
  - Implementação atual: o proativo recebe as duas últimas mensagens reais
    (`usuário → Luna`), limitadas a 350 caracteres cada e, desde 20/09, com até 15 minutos.
  - Confirmar se isso melhora continuidade e sensibilidade sem fazer o 12B abandonar a tarefa,
    ressuscitar assunto encerrado ou forçar referência pessoal.
  - Primeiro teste real: o usuário anunciou que jogaria The Last of Us Parte II Remastered e
    abriu Hollow Knight: Silksong. O proativo manteve a tarefa, mas não percebeu o contraste.
  - Experimento atual: somente a abertura de jogo tem um detector estreito em Python. Ele compara
    um anúncio explícito de "vou jogar/abrir A" com o jogo B realmente aberto e entrega os dois
    fatos estruturados ao 12B. Menção solta e mudança de ideia declarada não viram cobrança.
  - A bancada produziu uma reação aprovada ao contraste The Last of Us/Silksong. Confirmar no uso
    real se isso continua raro e certeiro, sem recorrer automaticamente a Steam/backlog.
  - Contexto sem relação direta não vira ponte: jantar não deve ser misturado com promoção,
    radar ou notícia só porque os eventos aconteceram perto no tempo.
  - Se frequentemente faltar uma conexão importante, experimentar quatro mensagens
    (`usuário → Luna → usuário → Luna`) mantendo os mesmos limites.
  - Não há validação manual objetiva para uma fala isolada. Manter as duas mensagens atuais e
    só reabrir o ajuste se aparecer um caso concreto de assunto ignorado ou conexão forçada.

---

## Ideias combinadas, ainda não começadas

Nada aqui está aprovado pra sair fazendo — são conversas que chegaram a um desenho, mas
esperam a vez. Confirme com o usuário antes de pegar uma.

### Luna (Python)

- [ ] **Companhia no Cities: Skylines II (Steam).** Combinado em 16/09/2026: o usuário ainda
      vai baixar o jogo e testar a Luna apenas por conversa/voz, sem integração. Primeiro
      observar FPS, engasgos e conforto enquanto ela gera e fala; já houve queda no Overwatch.
      Depois avaliar um mod que exporte eventos para um arquivo local lido pela Luna, dando
      contexto real às respostas e a comentários ocasionais, sem narrar tudo nem inventar fatos.
      Candidato pesquisado: https://github.com/iRecycled/CS2_Events — o autor documenta eventos
      de construção, impostos, orçamento e empréstimos; compatibilidade com a versão instalada
      ainda não foi validada. Não foi encontrada API HTTP/webhook oficial pronta para isso.
      Possível primeiro protótipo: construção de edifício, mudança de imposto e empréstimo;
      medir coleta com geração desligada antes de ativar falas. Coleta leve não elimina o custo
      do LLM na GPU. Retomar após o teste manual; nenhuma integração implementada nesta etapa.

- [ ] **Ela falar duas vezes seguidas em algumas interações.** Combinado em 13/10/2026: em vez
      do bate e volta de sempre, às vezes ela manda uma segunda mensagem curta logo depois.
      Desenho conversado: roleta em Python (cerca de 1 a cada 5 respostas), só em papo leve —
      prompt completo, sem ferramenta, fora dos modos enxutos e nunca em assunto sensível ou
      cansaço. A segunda chamada pede para ACRESCENTAR algo sem repetir e tem uma saída
      (`SEM_CONTINUACAO`) para quando não houver nada que valha: sem ela o modelo sempre
      preenche com repetição ou palpite. Na web chega como outra bolha, depois de um
      "digitando…" curto. Medir antes de ligar (quantas vezes usa a saída, repete ou inventa),
      com histórico morno, como em `testes/resultado_tom_generico.md`.
- [ ] **Botão no avatar para desligar o modo jogo na hora** (LoL, Dark Souls), sem mexer na
      intensidade do proativo. Combinado em 12/10/2026, para depois.
- [ ] **Barge-in.** Interromper a fala dela falando por cima, em vez de esperar terminar.
- [ ] **Radar de encomendas.** Mesma ideia do radar de promoções, para rastreio de pedidos.
- [ ] **Luz ambiente da Luna.** Testar a integração com uma lâmpada RGB Positivo em um bocal ou
      abajur atrás da mesa, usando luz indireta na parede como extensão discreta do mascote.
      Primeiro reaproveitar temporariamente uma das duas lâmpadas existentes; só montar algo
      definitivo se a automação for agradável no uso real. Começar com comandos explícitos de
      ligar, desligar, brilho e cor. Depois avaliar estados curtos como ouvindo, pensando, radar
      e alerta, sem transformar cada interação em espetáculo nem depender da Alexa como ponte.
- [ ] **Modo de datas comemorativas.** Em aniversário do usuário, Natal, Ano-Novo e outras
      datas selecionadas, adaptar por tempo limitado o jeito de falar e a aparência/animação do
      mascote. O aniversário deve vir de configuração pessoal (`.env` ou painel Web), nunca ficar
      gravado no código público. Definir uma curadoria pequena de datas e comportamentos para não
      transformar toda resposta do dia em bordão temático nem depender da LLM acertar a data.
- [ ] **Modo manutenção com agente de programação externo.** Ideia futura para debug: a Luna
      detecta ou recebe um erro, pede confirmação e prepara um pacote seguro com log recente,
      estado do Git e módulo provável para Codex, Claude Code, Pi ou OpenCode investigar. Começar
      apenas gerando o diagnóstico; qualquer edição, teste, commit ou push continua dependendo de
      autorização humana. Não priorizar agora: antes, investir em deixá-la mais viva nas interações.

### Presença (front — `templates/Index.html`)

> Combine antes de mexer neste arquivo: são ~4100 linhas com CSS, HTML e todo o JS juntos, e é
> onde dois agentes colidem. Rode `node testes/rodar.js` antes e depois.

- [ ] **Mais animação no modo Web.** Pedido em 13/10/2026: deixar a interface mais fluida —
      por exemplo, a caixa de resposta entrando e crescendo de forma suave enquanto ela digita,
      com os efeitos do anime.js (aqui é a v3.2.2; ver AGENTS.md). Incluir as bolhas de
      status no chat: "pensando…", "falando…" e "digitando…", vindas dos mesmos estados
      visuais que já movem o rosto, e que somem quando a resposta termina. Respeitar
      `prefers-reduced-motion`.

- [ ] **Comparações interativas na conversa.** Na fila por escolha do usuário em 09/10.
      Explorar cartões para comparar opções quando surgir uma dúvida que justifique isso.
      Conversas simples continuam sendo o uso principal; aguardar um caso concreto.

- [ ] **Um evento novo que se resolva por ESPERA.** Os que existem hoje pedem gestos ativos; falta
      um cujo desfecho seja não fazer nada por um tempo. Chegou a ser cogitado, sem fechar o
      desenho — o difícil é a espera não virar tédio.
- [ ] **Devolver algum movimento à cara de medo.** Ela ficou totalmente estática quando o rosto
      voltou a ser kaomoji inteiro. Um tremor leve no `#rosto-txt` via CSS na classe `.medo`
      resolveria sem reabrir a discussão da boca.
---

### Persona (`modulos/pensar.py`)

- [x] **Separar os prompts por eixo.** Feito: todo o TEXTO saiu do `pensar.py` para o
      `modulos/prompts.py`, organizado em identidade / emoção / conduta / forma / saída, mais os
      12 modos enxutos e o núcleo curto. O `pensar.py` ficou só com a LÓGICA (quem escolhe qual
      prompt, em que ordem testa os gatilhos). **A ORDEM das regras dentro do prompt continua
      exatamente a de antes** — reagrupar por eixo muda comportamento num 12B e é experimento de
      bancada, não arrumação. Rede nova: `testes/testa_prompt_montagem.py` monta o prompt de 22
      ramos e compara byte a byte com um golden.

- [x] **Reagrupar o prompt por eixo.** Feito e medido. As 18 constantes de bullet viraram 5
      blocos (identidade, emoção, estrutura, limites, saída) — granularidade por regra era
      papelada: `NAO_E_NAMORADA` tinha 42 caracteres e ganhava nome próprio e linha na
      composição. Fundir obrigou a reordenar (a identidade estava espalhada nas posições 1, 2, 4,
      11 e 12). **Bancada: 37/39 antes, 37/39 depois** nos turnos que usam a persona.
      `AUTONOMIA NÃO É BIRRA` ficou em EMOÇÃO, não em LIMITES: por conteúdo é limite, mas é a
      guarda de `TENHA OPINIÃO` e guarda longe não segura neste modelo.

- [x] **Trocar o prompt inteiro x trocar só o bloco de emoção.** Testado nos dois extremos da
      escala, e a resposta é a mesma nos dois: **o modo enxuto fica.**
  - `momento_sensivel` (o lado compreensivo): 15/15 nos dois, e **0/3 nos dois** no cenário com
    memória pertinente — dar perfil, memória e ChromaDB NÃO fez ela usar. 8x mais prompt por
    empate. O mecanismo (`persona(emocao)`) ficou pronto e desligado, ver `prompts.py`.
  - `aviso_cotidiano` (o lado ácido): prompt completo **piorou** o grounding, 12/12 → 9/12. As
    falhas foram justamente o que o enxuto previne: "mais um", "dessa vez" e um "backlog
    infinito que você só olha e não joga" puxado do nada.
  - Devolver as travas ao prompt completo recuperou só parte (10/12). Uma delas — a proibição
    LITERAL de "dessa vez" — foi desobedecida mesmo estando escrita, porque no prompt completo
    ela fica a 10.000 caracteres do começo. **É a quarta medição do mesmo princípio: instrução
    perto vence instrução longe.**
  - **O que funcionou** foi o contrário do experimento: copiar para o modo enxuto a UMA regra do
    prompt completo que ele não herdava. O `ENXUTO_COTIDIANO` não tinha o freio anti-pergunta, e
    o resultado eram **11 de 12 respostas terminando em "?", 10 delas no molde "vai ser X ou Y?"**.
    Com 200 caracteres de freio: grounding 11/12, "?" caiu para 6/12 e o molde para 5/12.

- [x] **O proativo passa a usar o bloco EMOÇÃO da persona.** Era o único turno que NUNCA via a
      persona: mexer no humor dela não mudava uma vírgula do que ela fala sozinha quando um jogo
      abre ou o radar acha algo. Agora o `nucleo_enxuto` aceita um bloco do prompt central, e o
      proativo recebe o `EMOCAO` — 2.208 → 4.147 caracteres, ainda 2,5x menor que o completo.
      Medido em 5 cenários x3: **14/15 antes, 13/15 depois** (a diferença é 1, dentro do ruído) e
      o tom mudou de "é uma mistura bem aleatória" para "sua caixa de entrada tá pedindo socorro
      entre o boleto do Nubank e o convite pra assembleia". Foram criados 4 cenários proativos —
      os 3 que existiam mediam só GROUNDING, nenhum media se ela tem atitude.

- [ ] **Acidez no lugar de argumento.** Achado num teste real: para "vou usar PHP nesse projeto
      novo" ela respondeu com uma piada sobre paciência que serviria igual para Rust, Go ou
      COBOL — não tem opinião sobre PHP. O `LIMITES` pede o contrário: "se a ideia dele é furada,
      contraponha com ARGUMENTO de verdade, não só com uma piada por cima". É diferente do que a
      gente vinha atacando: não é falta de humor, é humor ocupando o lugar do argumento. Medível
      com um cenário que dê uma decisão técnica concreta e cobre algo que só se aplique ÀQUELA
      escolha. (O dono do projeto notou que a resposta boa dela ali veio de um gancho da conversa
      anterior, não da opinião — confirma a leitura.)

- [ ] **Estender o bloco EMOÇÃO aos modos enxutos ácidos — mas testar a hipótese barata antes.**
      CONTRAPONTO medido no uso real: o `ENXUTO_CANSACO` está marcado `sem humor` e tem **262
      caracteres**, e produziu *"desliga essa máquina e vai deitar antes que seu cérebro peça
      asilo político"* — aprovado pelo dono do projeto. O prompt dele diz "uma mordida carinhosa
      sobre ele descansar ou **o cérebro pedir arrego**": ela pegou a semente concreta e variou.
      Ou seja, 262 chars de instrução ESPECÍFICA bateram os 1.938 do bloco genérico. Antes de
      empurrar o `EMOCAO` para os quatro modos ácidos, tentar o mais barato: dar a cada um uma
      semente concreta do mesmo tipo e medir. Pode ser que o que falte não seja mais prompt de
      humor, e sim um exemplo do que zoar naquele momento.

- [ ] **(se a semente não bastar) Estender o bloco EMOÇÃO aos modos ácidos.** O proativo foi o primeiro. Os
      candidatos naturais são `COTIDIANO`, `ZOEIRA_BACKLOG`, `CONTRADICAO` e `COMPRA_DE_JOGO` —
      todos pedem acidez e nenhum recebe o bloco que a define. **NÃO estender aos de acolhimento**
      (`SENSIVEL`, `CANSACO`, `CORRECAO`): lá o bloco ácido briga com a instrução, e já foi medido
      que o registro compreensivo não ganha nada com prompt maior. Medir um de cada vez.

- [ ] **Auditar o que mais falta nos outros 11 modos enxutos.** JÁ RENDEU DUAS: o freio
      anti-pergunta (no cotidiano) e o freio de abertura (no núcleo, valeu para os 12). O método
      que funcionou não é rodar experimento por modo — é olhar o LOG. `logs/bancada_persona.jsonl`
      já tem mais de mil respostas: agrupar por modo enxuto e procurar o padrão que se repete
      custa nada e aponta direto para a regra que falta. Dois falsos alarmes já apareceram assim e
      valem lembrar: `COMPRA_DE_JOGO` fecha com "?" em 100% das respostas e `SAUDACAO` em 94% —
      **os dois por design**, o prompt manda. Padrão repetido nem sempre é defeito.
  - Ainda sem cobertura de cenário: `agradecimento_curto`, `zoeira_backlog` e `compra_de_jogo`
    têm um cenário cada; `contradicao_proativa_jogo` e o proativo em geral, quase nada.
  - O que a auditoria estática mostrou e a empírica NÃO confirmou: "não prometa ação futura"
    falta em todos os 12 modos e apareceu em **0%** das mil respostas. Não é buraco, é regra que
    o núcleo não precisa.

- [ ] ~~**A trava nominal de Steam/backlog saiu do prompt completo.**~~ RESOLVIDO no mesmo dia: a
      medição do cotidiano fez ela dizer "descansa desse backlog infinito que você só olha e não
      joga" com o prompt completo. A meia-frase voltou para `NADA DE CARIMBO`, como estava
      previsto aqui, e o backlog não apareceu mais nas rodadas seguintes. Prova de que nomear o
      viés segura melhor que a regra genérica.

- [ ] **Proibido curto casa dentro de palavra — já custou duas falhas fantasma.** `"iso"` (para
      pegar data em formato ISO) reprovava "sorriso"; `"tas a "` (português de Portugal)
      reprovava "certas áreas". As duas apareceram numa medição real e quase fizeram uma mudança
      neutra parecer regressão. Corrigido com fronteira de palavra **só no início** — muitos
      proibidos são prefixos de propósito ("trabalh", "produtiv"), e exigir fronteira no fim
      quebraria todos. Ao escrever proibido novo com menos de 6 letras, teste antes se ele casa
      dentro de alguma palavra comum.

- [ ] **O ruído da bancada é de ±6 pontos em 102 — leia o placar sabendo disso.** Medido sem
      querer: duas rodadas completas seguidas, com o prompt dos cenários reativos **byte a byte
      idêntico** (o golden prova), deram 97/102 e 91/102. As 6 falhas de diferença estavam todas
      em cenários que a mudança não tocava, e cada uma era uma falha isolada em três rodadas.
      Conclusão prática: diferença de até ~6 pontos no total NÃO é sinal. Para decidir qualquer
      coisa, olhe **só os cenários que a mudança toca** — foi assim que o experimento do proativo
      ficou claro (0 falhas proativas antes e depois, enquanto o total "caía" 6).

- [ ] **Metade da bancada não mede a persona.** Dos 34 cenários, **21 caem num `modo_enxuto`**,
      que SUBSTITUI o prompt inteiro — a persona não entra. Medir uma mudança na persona contra o
      placar total engana: ao reagrupar os prompts, o total caiu de 76/81 para 74/81 e a queda
      inteira estava nesses 14, cujo prompt é byte a byte o mesmo. A bancada já reporta os dois
      números separados. Falta o outro lado: **os 14 modos enxutos praticamente não têm cenário
      próprio bem coberto**, e é neles que moram as falhas antigas (`proativo_sem_relacao`,
      `mudanca_de_ideia_normal`). Antes de mexer num modo enxuto, conferir a cobertura dele.

- [ ] **`zoeira_backlog` é capturado pelo `aviso_cotidiano`.** Achado ao montar o golden: qualquer
      frase que COMECE com "vou comprar" cai no modo cotidiano, que vem antes na cadeia de `elif`.
      Ou seja, "vou comprar mais um jogo com o backlog lotado" — a formulação mais natural — nunca
      chega na zoeira liberada. Só acende quando a frase começa de outro jeito ("quero comprar...",
      "meu backlog tá lotado e..."). Decidir se troca a ordem dos dois `elif` ou se o cotidiano
      passa a excluir menção a backlog. Mexer na ordem tem efeito colateral: o `compra_jogo_sem_
      contexto` também depende dela.

- [ ] **Encolher o prompt da persona, regra por regra.** Hoje: **8.880 caracteres (~2.400
      tokens), 16 regras + a abertura**, e o prompt MONTADO chega a ~10.300 caracteres com
      perfil, memórias e ajustes do turno (medido pelo golden). Já saíram 544 chars com o
      `CONTRADIÇÃO CONCRETA`, sem custo medido — muito para um 12B, que tende a
      perder as regras do meio. A parte fácil já foi feita: fundir os dois bullets de humor, que
      repetiam as mesmas quatro regras (−923 chars, e o placar da bancada subiu de 92% pra 98%).
      O que sobra é o difícil — **toda regra ali existe porque um comportamento ruim aconteceu**,
      então cortar no olho reabre bug antigo. Método: remover UMA e medir 3 rodadas.
  - **Pré-requisito:** ampliar a bancada antes. Várias regras não têm cenário nenhum cobrindo
    (não falar como português, não prometer ação futura, não usar markdown). Sem cobertura,
    cortar é aposta, não medição.
  - Aprendizado que vale carregar: **instrução perto vence instrução longe**. Três vezes a mesma
    história — regra forte no topo, proteção dela num bullet distante, o modelo obedecendo só a
    de perto. Colar a guarda junto da instrução resolveu nas três.
  - Contraexemplo útil: tentei remover o bullet "não invente fatos" achando que era repetição
    pura. O placar caiu 8 pontos. Provar que era ruído custaria mais rodadas do que os 80 chars
    valiam. Nem toda duplicata aparente é duplicata.

- [ ] **`proativo_sem_relacao` inventa consequência técnica.** Dado um número (600W), ela conclui
      o que o dado não diz — "vai precisar de tomada exclusiva pra não derrubar o disjuntor".
      Segue sendo o ponto fraco mais persistente. **Mas um terço do problema era o teste:** das 30
      falhas no log, 9 eram a palavra "jogo" reprovando "600 watts só pra rodar um jogo" — uso
      natural do dado, não conexão forçada com o jantar. O proibido foi removido; "backlog" e
      "steam", que são a muleta de verdade, ficaram. O que sobra de real é "tomada" (12 falhas).

- [x] **Muleta de abertura.** RESOLVIDO. A causa não era a persona ser ignorada — era o modo
      enxuto não herdar a regra. Medido em **875 respostas de modo enxuto contra 294 de prompt
      completo**: 22% das enxutas abriam com poxa/nossa/putz/eita/puxa, contra **0%** das
      completas. E as duas listas de proibidos do código — o bullet `VARIE o começo` e o
      `anti_rep` do `user_msg` — **paravam em 'Ih'**, logo antes das cinco que mais apareciam.
      Duas correções: as listas foram completadas, e o núcleo enxuto ganhou a parte POSITIVA que
      só o prompt completo tinha ("vá direto ao ponto, reaja ao que ele disse ou comece pela
      informação") — a lista de proibidos sozinha já chegava lá pelo `anti_rep` e não bastava.
      Resultado em 5 modos x3: abertura-muleta **13/15 → 0/15**, aberturas distintas 7/15 → 11/15,
      checks inalterados em 14/15. Custo: 173 caracteres no núcleo.

- [ ] **`mudanca_de_ideia_normal` parece ter falso positivo.** O cenário reprova a palavra
      "drama", mas ela está descrevendo o *gênero* do jogo abandonado, não inventando drama sobre
      o usuário. Falhou por isso em várias rodadas. Confirmar antes de mexer.

---

## Decidido NÃO fazer

Está aqui pra ninguém propor de novo. Se quiser reabrir algum, pergunte antes — cada um foi
testado ou discutido até dar num "não".

- **Boca separada dos olhos.** Tentado duas vezes no mesmo dia: primeiro vetorial (um `<path>` de
  curvatura/abertura/largura), depois glifo de 2-3 quadros com bancada de teste. Nenhuma das duas
  ficou melhor que o kaomoji inteiro, e a primeira custava 128 linhas de maquinaria. Revertido.
  Sobrou de bom: a curadoria das caras e a lista `NAO_PISCA`.
- **Bocejo.** Existia, exigia ~2 min de sossego absoluto e nunca chegou a ser visto rodando.
  Removido junto com as caras `˘ o ˘` e `- ○ -`.
- **GIF do Giphy como reação.** Na gaveta desde que a presença nasceu — reagia a uma *categoria*,
  nunca ao que ela tinha dito, e só existia no web. O código continua dormente no repositório
  (ver o comentário "GIF NA GAVETA" no `pensar.py`); pra voltar, basta o prompt emitir `[gif:]`.
- **Chuva de verdade usando dados do clima na presença.** "Não sei se encaixa, é uma lua."
- **Cara de esforço enquanto o TurboLLM carrega o modelo.** Avaliado e adiado — "não por agora".
- **Qwen3-TTS.** Avaliado a fundo contra o Kokoro. Voz boa e clonagem funcionando, mas o pico de
  8GB de VRAM e a ausência de streaming mataram. Kokoro fica.

- **KittenTTS 2 como substituto do Kokoro.** Testado em CPU em 03/10/2026, com seis
  amostras em português, duas com emoção. Após ouvir, o usuário preferiu o Kokoro
  (“kokoro tá melhor ainda”). A versão Python levou 55–68 s por frase, contra 3–5 s
  do Kokoro. Manter a voz atual; a versão C++ não foi medida.
  [Relatório e avaliação](testes/resultado_kitten2.md).


---

## Como manter este arquivo

Duas IAs trabalham neste repositório (Claude Code e Codex) — este arquivo é o que evita as duas
proporem a mesma coisa ou reabrirem algo já descartado.

- Ideia nova que o usuário aprovou mas não começou → **Ideias combinadas**
- Coisa em uso esperando julgamento dele → **Em teste**
- "Não" com motivo → **Decidido NÃO fazer**, com o porquê. O motivo importa mais que o item.
