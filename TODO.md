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
    Não ampliar isso como regra global. Próximo experimento possível: somente proativos de
    abertura verificam se a intenção imediatamente anterior citava outro item da mesma categoria.
  - Se frequentemente faltar uma conexão importante, experimentar quatro mensagens
    (`usuário → Luna → usuário → Luna`) mantendo os mesmos limites.
  - Antes de commitar, pedir a avaliação do usuário sobre os testes cotidianos.
