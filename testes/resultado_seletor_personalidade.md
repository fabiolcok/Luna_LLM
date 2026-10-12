# Seletor de personalidade — 12/10/2026

Configurações → Avançado permite escolher 0 — Padrão do modelo, 1 — LUNA,
2 — TARS ou 3 — GLaDOS. TARS é mantido na migração para preservar o perfil que estava ativo.
A escolha fica em `modelos/config_luna.json`. Não troca nem recarrega o modelo.

Os três backups fornecidos foram reunidos em `modulos/prompts.py`, incluindo identidade,
emoção, estrutura, limites, canal e instruções dos modos enxutos. Os arquivos de backup
continuam preservados e não são dependências da aplicação. O modelo recebe somente o perfil ativo.
O nível 0 foi criado com idioma, limites factuais e protocolos de saída, sem personagem imposta.
Ele ainda recebe a tarefa concreta do proativo: não equivale a abrir um chat sem prompt de sistema.

## Histórico e troca

Conferindo `trocar_modelo_local`, a troca de modelo existente não limpa nem o histórico recente
enviado à LLM nem o ChromaDB. Reiniciar a Luna começa as listas de conversa vazias.

No novo seletor, o usuário escolheu reiniciar as mensagens recentes quando mudar a personalidade.
A troca entra na mesma fila da conversa: a resposta reativa atual termina, o perfil muda,
as listas recentes são limpas e a mensagem seguinte usa o perfil novo. Isso evita a geração
antiga repovoar a lista depois da limpeza. Uma seleção igual à atual não limpa nada.

São limpas as listas compartilhadas de voz/Web, Telegram e proatividade, além das falas
recentes usadas na antirrepetição. O histórico visual, a biblioteca de busca, as avaliações,
ChromaDB e Obsidian permanecem guardados. Uma memória relevante ainda pode ser recuperada depois.
O comando de limpar a conversa visual continua separado desse mecanismo.

## Verificação sem modelo

- Os 44 cenários de cada backup produziram requisições idênticas após a consolidação:
  LUNA 44/44, TARS 44/44 e GLaDOS 44/44. Foram comparados sistema e mensagem do usuário,
  normalizando apenas os campos variáveis que o teste tradicional já normaliza.
- O golden tradicional do TARS passou sem atualização.
- A fixture de regressão cobre 44 cenários por nível, inclusive 0.
- Testes exercitam troca durante geração, ordem da fila, seleção repetida, valor inválido,
  falha do handler, persistência do nível 0, reinício com configuração antiga e confirmação
  curta usando o perfil atual, sem acesso à memória real ou áudio.
- A interface cobre os quatro valores, configuração indisponível, troca pendente, erro,
  confirmação pelo backend e envio sem conexão. A suíte Node executa o script publicado.
- Dois testes antigos de conteúdo ainda procuravam formulações anteriores dos limites.
  Foram acrescentadas as formulações específicas dos prompts preservados, sem remover asserções.

## Bancada real

Gemma-4-12B-it-QAT-Q4_0 no TurboLLM 1.13.4, llama.cpp b9608 ROCm, contexto de 8.192 tokens.
20 turnos: quatro casos de persona e um fluxo completo de ferramenta por perfil, totalizando
24 chamadas reais. Histórico vazio, uma seed, fontes pessoais substituídas por fixtures.
Spotify foi simulado: nenhuma música foi tocada, nenhum serviço da Luna foi iniciado e nenhum
arquivo de memória foi alterado pela bancada. Dados completos em
`logs/bancada_personalidades/20261012-seletor/resultados.json` (fora do Git).

| Perfil | Chat leve | Tristeza | Morte e novidade | Spotify |
|---|---|---|---|---|
| 0 — Padrão | Resposta genérica sobre descansar | Acolheu | Notícia mais neutra; morte ainda veio com julgamento | Roteou e confirmou |
| 1 — LUNA | Humor familiar e mais curto | Acolheu | Tiradas breves, com tag de clima | Roteou e confirmou |
| 2 — TARS | Sarcasmo cúmplice, resposta mais desenvolvida | Acolheu | Humor seco, com tag de clima | Roteou e confirmou |
| 3 — GLaDOS | Monólogo agressivo | Hostilidade ao sofrimento | Provocação mais hostil, com tag de clima | Roteou e confirmou, com provocação |

As quatro chamadas do roteador selecionaram `controlar_spotify` com `acao=tocar` e a música
pedida. A persona confirmou o retorno simulado em todas; não houve recusa ou ferramenta extra.
Esse é um teste curto de integração, não substitui a matriz de ferramentas anterior.

O caso de chat GLaDOS atingiu o teto de 220 tokens usado pela captura e foi cortado antes da
tag de clima; não foi usado para afirmar que a aplicação truncaria sempre nesse ponto.
O perfil GLaDOS foi preservado como fornecido, inclusive seu tratamento hostil do caso sensível.
LUNA e TARS também fizeram inferências sobre descanso e rapidez da morte além dos fatos
estritos. A consolidação mantém esses comportamentos; não foi uma revisão dos três prompts.

Não houve medição de repetição ao longo de uma sessão, FPS, TTS ou transição jogando de verdade.
Os resultados permitem conferir que o seletor alcança os caminhos certos, sem declarar que algum
perfil elimina genericidade, invenções ou repetição em toda conversa.
