# Pendências

Lista curta de experimentos que ainda precisam de validação humana antes de virarem decisão
definitiva. Itens daqui não estão automaticamente aprovados para commit.

## Em teste

- [ ] **Validar limpeza do `salvar_obsidian`.** Mensagens com `título:`/`conteúdo:` não devem
      guardar introdução nem comando; reação curta como “boa ideia, deixa anotado” deve salvar
      a fala anterior da conversa. A origem precisa distinguir web, Telegram e voz.

- [ ] **Validar contexto recente nas falas proativas.**
  - Implementação atual: o proativo recebe as duas últimas mensagens reais
    (`usuário → Luna`), limitadas a 350 caracteres cada.
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

- [ ] **Estender o bloco EMOÇÃO aos modos enxutos ácidos.** O proativo foi o primeiro. Os
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

---

## Como manter este arquivo

Duas IAs trabalham neste repositório (Claude Code e Codex) — este arquivo é o que evita as duas
proporem a mesma coisa ou reabrirem algo já descartado.

- Ideia nova que o usuário aprovou mas não começou → **Ideias combinadas**
- Coisa em uso esperando julgamento dele → **Em teste**
- "Não" com motivo → **Decidido NÃO fazer**, com o porquê. O motivo importa mais que o item.
