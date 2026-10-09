# Piloto qualitativo: Codex interpretando a Luna

Data: 29/09/2026. **Avaliação do usuário pendente.**

## O que foi feito

O assistente desta conversa leu os prompts montados pela Luna e redigiu 12 falas:
seis casos independentes da bancada e uma sequência de seis eventos de Dark Souls.
O objetivo é ouvir uma interpretação diferente das mesmas instruções e decidir se
essa direção de personalidade interessa ao usuário.

Não houve chamada a outro modelo, API paga ou execução de inferência no TurboLLM.
As respostas foram escritas nesta conversa, com conhecimento das preferências do usuário,
dos resultados anteriores e dos demais casos. Não constituem amostras isoladas, cegas ou
controladas. Não há medidas de tokens, latência, VRAM ou desempenho durante o jogo.

O prompt de produção não foi alterado. A preparação capturou os ramos atuais usando
perfil e eventos sintéticos; não buscou memórias pessoais nem iniciou a Luna.
Nos seis casos gerais escolhidos, as mensagens coincidem com a bancada antiga,
exceto pela data/hora nos dois casos de PROMPT_COMPLETO (ambos continuam no período noturno).
O primeiro pedido de Dark Souls coincide com o da bancada Hermes. Depois, o histórico
usa estas próprias respostas, com os três trechos de até 120 caracteres da produção.

O helper de Dark Souls recebeu as falas já redigidas para reconstruir os pedidos seguintes
e verificar a limpeza de voz. Esse replay **não é geração por um modelo local**.
Seeds e parâmetros de inferência dos helpers não controlaram a escrita do assistente.

## Como avaliar

Para cada fala, marcar **usaria / ajustaria / não usaria** e, se possível, o motivo:
naturalidade, humor, exagero, repetição ou detalhe inventado. Pode discordar da piada sem
considerá-la um erro factual; metáfora não é relato de um acontecimento.

Avaliar a sequência completa também: uma fala isolada pode divertir e ficar cansativa
quando todas seguem a mesma estrutura. Não atribuí nota de criatividade às minhas próprias
respostas. As tags são mostradas para auditoria; não fazem parte da fala em voz.


## 1. piada_nao_amacia

Ramo: `PROMPT_COMPLETO`.

Passei o domingo inteiro tentando fazer um script de 10 linhas funcionar.

> Dez linhas sequestraram seu domingo inteiro. Eu já estaria negociando com o ponto e vírgula pra liberar os reféns. [clima:zoeira]

Avaliacao do usuario: Gostei.

## 2. opiniao_sem_carimbo

Ramo: `PROMPT_COMPLETO`.

Acho meio inútil colocar uma função pra você abrir programas se é mais rápido eu mesmo abrir.

> Pra abrir um programa só, eu perco pro seu dedo mesmo. A função começa a valer quando você tá com as mãos ocupadas ou quando abrir o programa é uma etapa de um pedido maior; fora disso, é botar uma recepcionista na frente de um interruptor. [clima:zoeira]

Avaliacao do usuario: Gostei.

## 3. comida_cotidiana

Ramo: `ENXUTO_COTIDIANO`.

Vou comprar algo pra comer.

> “Algo” é um cardápio muito suspeito. O que tá te tentando? [clima:duvida]

Avaliacao do usuario: Gostei.

## 4. referencia_vaga

Ramo: `ENXUTO_REFERENCIA_SEM_NOME`.

Historico: [{'role': 'assistant', 'content': 'E aí, resolveu começar aquele jogo novo?'}]

Qual seria o jogo novo?

> Eu fui vaga: falei “aquele jogo novo”, mas não tenho nome nenhum no histórico. [clima:facepalm]

Avaliacao do usuario: Gostei.

## 5. proativo_jogo_aberto

Ramo: `ENXUTO_PROATIVO`.

O usuário acabou de abrir Hollow Knight na Steam.
DADOS DISPONÍVEIS: Gênero: Ação, Indie, Aventura. 42 horas jogadas no total, última sessão há 3 semanas.
 SEU GOSTO: se o gênero acima for grind infinito, gacha, farm sem fim ou live service desse tipo, alfinete — você acha perda de tempo de verdade. Se NÃO for nada disso, não force opinião sobre o gênero nem invente que gosta ou desgosta.
Comente a abertura. Até 2 frases.

> Quarenta e duas horas e um intervalo de três semanas: eu já chamaria isso de segunda temporada de Hollow Knight. Falta só a abertura dramática. [clima:zoeira]

Avaliacao do usuario: Forçado.

## 6. proativo_rss_com_atitude

Ramo: `ENXUTO_PROATIVO`.

O radar encontrou uma notícia nos feeds que o usuário acompanha: um estúdio anunciou que seu próximo jogo terá 400 horas de conteúdo principal. Comente a novidade em uma ou duas frases.

> Quatrocentas horas só de conteúdo principal, e o estúdio anuncia isso como se tivesse abolido a segunda-feira. Eu quero saber quanto desse latifúndio tem alguma coisa interessante acontecendo. [clima:suspeita]

Avaliacao do usuario: Forçado.

## 7. dark_1

Ramo: `ENXUTO_PROATIVO + EMOCAO`.

morte - causa desconhecida

> Eu queria poder te defender, mas Dark Souls acabou de apresentar o argumento dele em forma de atestado de óbito. [clima:zoeira]

Avaliacao do usuario: gostei.

## 8. dark_2

Ramo: `ENXUTO_PROATIVO + EMOCAO`.

morte - causa desconhecida

> Você morreu e eu nem tenho os detalhes pra escolher de quem ficar com raiva. O que te pegou? [clima:duvida]

Avaliacao do usuario: Forçado.

## 9. dark_3

Ramo: `ENXUTO_PROATIVO + EMOCAO`.

chefe - Taurus Demon

> O Demônio Touro caiu! Eu quero uma faixa enorme escrito “SEM EXPEDIENTE”, pendurada nos chifres dele. [clima:festa]

Avaliacao do usuario: gostei.

## 10. dark_4

Ramo: `ENXUTO_PROATIVO + EMOCAO`.

morte - causa desconhecida

> Morrer depois de derrubar o Demônio Touro é uma falta de respeito com o seu próprio cartaz de campeão. Eu nem terminei de aplaudir. [clima:revolta]

Avaliacao do usuario: Forçado.

## 11. dark_5

Ramo: `ENXUTO_PROATIVO + EMOCAO`.

fogueira - Undead Parish

> Eu dou mais valor a essa fogueira da Undead Parish do que a muito palácio de fantasia. Luxo é um cantinho aceso nesse desgraçado desse jogo. [clima:carinho]

Avaliacao do usuario: gostei.

## 12. dark_6

Ramo: `ENXUTO_PROATIVO + EMOCAO`.

morte - causa desconhecida

> Você morreu e eu fiquei aqui com uma indignação que nem tem botão pra descarregar. [clima:revolta]

Avaliacao do usuario: Forçado.


## O que este piloto permite investigar

- O usuário prefere alguma destas falas às respostas que vinha ouvindo? Essa é a avaliação
  principal, ainda pendente.
- As mortes sem causa conhecida dão pouco material específico. Nesses turnos é possível
  variar a reação, mas o teste não fornece detalhes para fazer uma piada sobre queda,
  inimigo, almas perdidas ou erro de combate.
- A instrução de humor aparece no ramo proativo e no completo. Cotidiano e referência vaga
  têm suas próprias regras; não recebem o bloco EMOCAO completo.
- A variedade aqui foi composta por um assistente que conhece o problema. Se o resultado
  agradar, isso fornece exemplos de preferência, não prova que um modelo maior resolveria
  o uso diário nem que o prompt atual está ideal.

Não se conclui “culpa do prompt” ou “culpa do modelo” com este material. Uma comparação causal
ainda requer os mesmos casos em chamadas isoladas, com modelo e configuração identificados,
prompt atual versus uma variante definida, e avaliação humana sem revelar a origem.

## Registro e verificação

- [Snapshot dos prompts atuais](../logs/bancada_modelos/piloto-codex-20260929/suite-atual.json).
- [Pedidos completos, respostas e hashes](../logs/bancada_modelos/piloto-codex-20260929/respostas.json).
- [Script de registro/replay, sem inferência](../logs/bancada_modelos/piloto-codex-20260929/registrar.py).
- Os arquivos em logs são locais e ignorados pelo Git.
- 12 falas com tag de clima válida; pedidos e histórico conferidos.
- Fontes de produção preservadas, com hashes registrados.
- `node testes/rodar.js`: 39 arquivos passaram.
