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

- [ ] **Introspecção nível 3 — ela ler o próprio código.** Via `inspect.getsource`, pra responder
      "como você faz X?" olhando a função de verdade. O desenho já foi discutido; parou por
      prioridade, não por dúvida.
- [ ] **Barge-in.** Interromper a fala dela falando por cima, em vez de esperar terminar.
- [ ] **Radar de encomendas.** Mesma ideia do radar de promoções, para rastreio de pedidos.
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
