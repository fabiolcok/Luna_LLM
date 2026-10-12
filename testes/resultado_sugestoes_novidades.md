# Sugestões para continuar uma novidade — 09/10/2026

Implementado apenas no proativo `radar_rss`. A mesma geração produz o comentário e duas ou três
perguntas específicas para a notícia selecionada. Não há uma segunda chamada ao roteador para
montar os botões. O bloco comum `ENXUTO_PROATIVO` e a ordem de `EMOCAO` foram preservados.

## Comportamento

- As perguntas aparecem abaixo do comentário, somente na web. Não entram no áudio nem no
  texto de copiar a resposta. O resumo e as sugestões são metadados do cartão.
- Clicar envia a pergunta como uma mensagem de texto. O servidor resolve o id daquele turno,
  recupera título, fonte, URL e resumo da notícia e entrega essa referência à conversa.
  Uma notícia antiga não acaba referenciando a notícia mais recente.
- O rascunho na caixa de texto é preservado. O envio usa a mesma confirmação e fila das
  mensagens digitadas; conexão indisponível ou referência removida gera um aviso.
- Saída ausente, JSON inválido ou bloco cortado não impede o comentário: os botões são
  omitidos e o trecho de metadados é removido da fala. Há limite de três perguntas.
- As perguntas solicitam informação ou opinião. Uma pergunta não significa que a Luna já
  sabe a resposta: o resumo não é o artigo completo, e o fluxo normal pode consultar fontes.
- Promoções, Dark Souls e demais proativos mantêm seus prompts. Históricos anteriores não
  recebem sugestões retroativamente. Reiniciar a Luna e recarregar a web aplica a mudança
  às próximas novidades.

## Bancada com modelo real

Gemma 4 12B IT QAT Q4_0, TurboLLM 1.13.4, llama.cpp b9608 ROCm, contexto de 8192 tokens.
Sem voz, execução de ferramentas, leitura de memórias pessoais ou segunda instância da Luna.

Quatro notícias, duas seeds por notícia. ARC Raiders e OLED usam os relatos apresentados
pelo usuário; TTS e anúncio cooperativo são fixtures sintéticas. A montagem da tarefa RSS,
o núcleo e o pós-processamento são os da produção. Não foi simulado um diálogo contínuo,
nem o rodízio de abordagens e o histórico de falas recentes de uma sessão real.

A primeira rodada comparou oito pares com ordem alternada e cache de prompt desligado.
Todas as oito saídas do candidato tinham três perguntas válidas. A leitura manual encontrou
duas perguntas com intenção parecida e uma que repetia informação já dada pelo resumo.
O bloco recebeu uma instrução para evitar esses casos.

A rodada final executou oito novas chamadas do candidato e reaproveitou as oito chamadas
do controle, verificando que seus pedidos e a identidade do modelo eram idênticos. São
24 chamadas reais ao todo, não 32. A segunda rodada não é um novo A/B intercalado.

| Variante | Amostras | Perguntas válidas | Tokens de saída medianos | Total mediano |
|---|---:|---:|---:|---:|
| Controle, comentário sem botões | 8 | não se aplica | 69 | 3,26 s |
| Candidato final, comentário + botões | 8 | 8/8, três por notícia | 118 | 4,39 s |

O bloco acrescentou 197 tokens de entrada medidos nesta engine. O teto de saída RSS passou
de 220 para 360 para acomodar os metadados; isso é um limite, não consumo obrigatório.
Nenhuma amostra terminou cortada pelo teto.

Exemplos reais de sugestões da rodada final:

- ARC Raiders: “Como a IA vai diferenciar reflexos humanos de hacks?”
- OLED: “Como saber se o burn-in já afetou a minha unidade?” e
  “Existe alguma forma de mitigar esse desgaste no uso diário?”
- TTS sintético: “Já tem alguma amostra de áudio disponível?”

Os comentários continuaram coloquiais e com exageros. Esta amostra pequena não prova que
a qualidade da persona seja equivalente. Continuam aparecendo inferências sem suporte em
ambos os braços, como interpretar a falta de detalhes no resumo como falta de transparência
do estúdio, ou transformar “anunciou” em “lançou”. As sugestões também precisam de leitura
humana: validar JSON não valida a premissa da pergunta. Não foi feita uma calibração geral
da persona nesta mudança.

Arquivos locais, ignorados pelo Git:

- `logs/bancada_web/20261009-sugestoes-novidades/resultados.json`: rodada inicial.
- `logs/bancada_web/20261009-sugestoes-novidades-v2/resultados.json`: rodada final e pedidos.
- `logs/bancada_web/20261009-sugestoes-novidades-v2/amostras.md`: comentários e perguntas.
- `logs/bancada_web/20261009-sugestoes-novidades-v2/preview.html`: prévia usando CSS e
  componentes reais da interface. Seus cliques são demonstrações locais.

## Verificação

- `node testes/rodar.js`: 45 arquivos passaram, antes e depois da mudança de interface.
- 25 testes Python de sugestões, cartões, recebimento e links passaram.
- 118 testes Python de execução, interrupção, repetição, persona, promoções, avaliações,
  saída web e acompanhamentos passaram.
- Montagem de prompt: nove testes passaram; os 32 ramos anteriores continuam idênticos
  byte a byte. O golden ganhou somente dois cenários RSS, voz e texto.
- A bancada importa a persona com o boot desativado. A montagem foi verificada novamente
  desse modo para evitar inicializar Kokoro ou alterar o modelo durante os testes.
- Inspeção visual da prévia em Edge headless: perguntas abaixo do comentário, quebra em
  linhas conforme o espaço disponível, texto e links preservados.

Os testes da interface que verificavam a forma exata do `return` foram ajustados para o
transporte de sugestões, preservando as verificações de origem, clima e Markdown por canal.
O teste da fila passou a carregar também a função nova de criação das sugestões.

## Correção do clique que recusava continuar a conversa — 10/10/2026

As perguntas sobre RTX 5090 e GTA 6 exibiam “não consegui fazer isso agora” mesmo sem
pedir uma ação. O handler juntava a pergunta com a referência da notícia e a instrução
“consulte a fonte”. O guard `_parece_pedido_de_acao` examinava esse bloco inteiro e
detectava nossa própria instrução como um pedido do usuário. O roteador também recebia
uma instrução de responder, embora sua função seja decidir sobre ferramentas.

A pergunta literal agora permanece separada da referência, transportada pelo contexto
do clique. Só ela entra na checagem de ação, no histórico e no salvamento da conversa.
O roteador recebe um contrato específico para a notícia selecionada: devolve
`SEM_FERRAMENTA` para interpretação do resumo, ou chama `resumir_site` quando faltam
detalhes do artigo. Apenas a leitura está disponível nessa rota; a URL executada vem do
cartão validado pelo servidor, mesmo que o modelo omita ou invente outro link.

A persona recebe a referência em ambos os caminhos. O prompt distingue título/resumo
de conteúdo efetivamente obtido do artigo; falha na leitura não é apresentada como
leitura bem-sucedida. A proteção para um pedido real de pesquisa sem ferramenta continua
ativa. Chat comum, voz, Telegram e proativos mantêm os contratos anteriores.

### Validação

- 48 testes Python de sugestões, continuação, dúvidas de jogo, recebimento e cadastro
  de fontes passaram. Incluem as duas perguntas reportadas, artigo com URL omitida ou
  diferente, erro de leitura, ferramenta indevida e preservação do guard para ações reais.
- Dez testes de montagem passaram antes e depois. Os 40 ramos anteriores foram comparados
  e permanecem idênticos; o golden ganhou dois ramos de continuação, com resumo e com artigo.
  O teste do handler foi atualizado para exigir pergunta literal e referência separada.
- `node testes/rodar.js`: 45 arquivos passaram. Não houve alteração da interface nesta correção.
- Compilação dos arquivos Python alterados passou.

### Bancada do fluxo com Gemma

Rodada final: três perguntas, duas seeds por pergunta, roteador e persona reais da
produção. Gemma 4 12B IT QAT Q4_0, TurboLLM 1.13.4, llama.cpp b9608 ROCm, contexto 8192.
Os temas e duas perguntas vêm dos relatos; referências e artigos são fixtures sintéticas,
sem verificar os fatos das notícias originais. Não houve leitura de páginas na internet,
TTS, gravação de memória ou segunda instância da Luna.

| Pergunta | Decisão do roteador | Respostas sem o fallback indevido |
|---|---|---:|
| O que acontece com quem já planejou a 5090? | Conversar a partir do resumo | 2/2 |
| Por que o GTA 6 não está ajudando nas vendas? | Ler o artigo selecionado | 2/2 |
| Como fizeram esse teste? (OLED) | Ler o artigo selecionado | 2/2 |

Nos dois casos sem ferramenta, o roteador devolveu exatamente `SEM_FERRAMENTA` em seis
tokens. Nas quatro leituras, gerou somente a chamada de `resumir_site`, com a URL correta
(23–25 tokens). Todas as seis conversas chegaram à persona e preservaram a pergunta
literal no histórico. A soma mediana das duas gerações foi 9,70 s sem leitura e 5,91 s
com artigo simulado; esses tempos não incluem uma requisição real à fonte.

A leitura manual confirma o fluxo, não a precisão geral da persona. Ainda há inferências
sem suporte: uma resposta da 5090 introduziu uma 5080 “mais cara”, e uma do GTA 6 chamou
a hipótese do autor de “quase óbvia”. Esta correção não calibra toda a criatividade nem
garante que sites reais permitam a leitura. Na primeira rodada, um rótulo de fixture foi
interpretado como conteúdo do artigo; o rótulo foi removido e os seis casos foram refeitos.

Reprodução: `venv\Scripts\python.exe -X utf8 -m testes.bancada_continuar_novidade`, com o
Gemma já carregado. Pedidos, respostas e identidade do modelo ficam em
`logs/bancada_web/20261010-continuar-novidade/resultados.json`; a primeira rodada está em
`resultados-primeira-rodada.json`, e a comparação do golden em `prompt.diff` na mesma pasta.

Reiniciar a Luna e recarregar a página aplica a correção ao clique real.
