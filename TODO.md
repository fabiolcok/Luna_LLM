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

- [ ] **Encolher o prompt da persona, regra por regra.** Hoje: **8.498 caracteres (~2.400
      tokens), 17 regras, 59 proibições contra 13 permissões** — muito para um 12B, que tende a
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

- [ ] **`proativo_sem_relacao` inventa consequência técnica.** Falha na bancada desde antes de
      qualquer mudança recente: dado um número (600W), ela conclui o que o dado não diz — "vai
      precisar de tomada exclusiva pra não derrubar o disjuntor". É o ponto fraco mais
      persistente que apareceu.

- [ ] **Muleta de abertura.** ~20% das respostas abrem com "Pois é", "Nossa", "Eita", "Putz". A
      persona manda cortar o "Pois é" explicitamente e ele aparece assim mesmo, em todas as
      rodadas medidas. A bancada não mede isso — um cenário que reprove abertura-muleta
      resolveria.

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
