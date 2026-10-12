# Fontes pela conversa, interesses no radar e leitura das respostas

Implementação de 10/10/2026, inspirada em ações na conversa e preferências explícitas.
Reiniciar a Luna e atualizar a página para usar os novos comandos Python.

## Cadastro conversando

Exemplo: “Acompanhe este projeto e me avise quando tiver suporte a PT-BR: https://example.org/releases.atom”.
O link deste exemplo é fictício: substitua pela fonte real.

- A Luna prepara um cartão com assunto, mudança de interesse e até três links.
- Interesse e situação devem vir literalmente do pedido; campos não sustentados ficam vazios.
- É possível editar o cartão, confirmar ou descartar. Só **Confirmar acompanhamento** cadastra
  o monitor e inicia a primeira leitura. O cadastro manual continua disponível.
- Rascunhos são locais, duram sete dias e sobrevivem ao reinício. Edições ainda não enviadas
  sobrevivem à reconexão da página aberta; recarregar a página restaura o rascunho original.
- Reenviar a confirmação após uma queda não cria outro monitor. Pedidos repetidos reutilizam
  o rascunho ou o acompanhamento igual. O piloto Sopro/PT-BR já cadastrado também é reutilizado.
- Este piloto de cadastro conversa funciona no chat Web. Voz e Telegram conservam seus caminhos.

A primeira consulta continua silenciosa; consultas posteriores seguem o monitor existente,
a cada seis horas enquanto a Luna está aberta, com proatividade e acompanhamento habilitados.
Fontes públicas sem login: RSS/Atom e changelogs são preferíveis; páginas dependentes de
JavaScript podem não fornecer conteúdo útil. Nenhum site é consultado para preparar o rascunho.

## Interesse nas notícias

Na notícia, abra **Afinar radar**, informe palavras como “OLED” e escolha mais ou menos desse
assunto. A preferência afeta o sorteio do próximo destaque quando as palavras aparecem no
título ou resumo. Não classifica assuntos semanticamente nem aprende por treinamento.

O peso sobe ou cai por cinco para cada preferência correspondente, limitado entre 1/25 e 25.
Todas as notícias coletadas continuam na nota; menos interesse não é um bloqueio. Sem
preferências, o sorteio anterior é preservado. Repetir o clique substitui a preferência.
É possível removê-la em **Configurações → Proatividade → Conversa & interesses → Interesses
do radar de novidades**. Limite de vinte interesses, salvos localmente e fora do prompt.
Avaliações boa/ruim continuam avaliando a resposta da Luna, separadamente.

Na apresentação de 10/10, a fonte fica no cabeçalho do cartão e o link **Ver todas** aparece
à direita de **Abrir notícia**, dentro do cartão, sem uma contagem adicional solta.
As perguntas ficam recolhidas em
**Continuar assunto**, ao lado de **Afinar radar**. Mensagens antigas sem cartão e promoções
conservam o link da nota depois da fala.

## Ouvir respostas

O botão ▷ no canto da resposta lê o texto daquele turno com Kokoro, voz/velocidade atuais e
volume que pode mudar durante a reprodução. Usa o texto do histórico do servidor: o navegador
não fornece um texto diferente. Markdown é limpo pelo caminho de fala já existente; dados
dos cartões e links não são anexados ao áudio. Não cria nova mensagem, memória ou chamada LLM.

O play da barra é um atalho para o botão da **última resposta**. Ambos compartilham a leitura,
o estado e o cancelamento. A barra também funciona para uma resposta escrita que nunca teve
áudio; não depende mais do último WAV gerado, que podia pertencer a uma fala antiga.

O botão vira ■ durante a fila, geração e reprodução e pode parar essa leitura. Uma mensagem
nova cancela a leitura atual ou pendente; o áudio de texto antigo não deve atrasar a conversa.
O cancelamento libera a fila sem esperar pela síntese do trecho em andamento; esse áudio é
descartado quando o Kokoro termina. A leitura usa o fluxo de frases já existente, em vez de
gerar o áudio inteiro antes de começar. Não interfere no descarregamento do LLM por inatividade.

## Verificação

- Testes da interface antes/depois: **45 arquivos Node**.
- Testes Python: **92 testes**, mais **10 da montagem dos prompts**, todos passando.
  Cobrem cadastro/consulta, reenvio após falha de gravação, expiração, duplicação,
  literalidade, preferências, cartões, fila de texto, prioridade, cancelamento e limpeza de voz.
- Golden: os **39 cenários anteriores foram preservados**, acrescentando apenas a montagem
  específica de confirmação do rascunho. A ferramenta nova só entra no pedido Web apropriado.
- Prévia com componentes reais em 900 e 420 px, sem excesso de largura. Arquivos ignorados
  pelo Git em `logs/bancada_web/20261010-fontes-interesses-voz/preview.html`.
- Cartão de notícia compacto conferido em 900 e 420 px, com os dois controles recolhidos
  e abertos, sem corte horizontal. Miniatura simulada apenas para medir o espaço na prévia:
  `logs/bancada_web/20261010-cartao-noticia-limpo/preview.html`.

## Bancada Gemma 4 12B

`python -X utf8 -m testes.bancada_fontes_conversa`: quatro pedidos, duas seeds no roteador
e uma confirmação persona por caso; mesmo modelo e engine, sem consultar sites, criar
acompanhamentos reais ou reproduzir áudio. Temperatura zero no roteador: as duas seeds
não equivalem a duas observações independentes.

Primeira rodada: **8/8 chamadas da ferramenta**, mas o pedido sem interesse ganhou um objetivo
genérico inventado. O modelo também colocou URLs em campos que não eram fontes. A confirmação
tinha três respostas claras e uma abertura ambígua (“o projeto já está na lista”).

Correção: interesse/contexto literais, sem URL; falta de interesse explicitada no retorno;
contrato de confirmação redigido como um rascunho normal, sem apresentá-lo como falha.
Segunda rodada: **8/8 chamadas válidas**, interesse literal nos seis pedidos com critério
e vazio nos dois sem critério. **4/4 confirmações** descreveram o rascunho e condicionaram
o monitoramento à confirmação. Um assunto ainda veio com URL; o Python usa o domínio como
nome provisório nesse caso, editável no cartão.

Resultados: `logs/bancada_web/20261010-fontes-interesses-voz-v2/resultados.json`.
Isso valida estes casos, não toda a linguagem natural. O som no dispositivo real e a utilidade
das preferências ainda precisam da avaliação do usuário. Kokoro não foi trocado nem comparado
novamente; foram verificados a entrega do texto, sua limpeza e o cancelamento sem áudio real.

## Adiado

“O que aconteceu enquanto estava fora”: estudar uma apresentação agrupada dos avisos já
coletados. Nenhum novo processamento durante jogos foi implementado nesta etapa.
