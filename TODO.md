# Pendências

Lista curta de experimentos que ainda precisam de validação humana antes de virarem decisão
definitiva. Itens daqui não estão automaticamente aprovados para commit.

## Em teste

- [ ] **Validar contexto recente nas falas proativas.**
  - Implementação atual, ainda local: o proativo recebe as duas últimas mensagens reais
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
  - Antes de commitar, pedir a avaliação do usuário sobre os testes cotidianos.
