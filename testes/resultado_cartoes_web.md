# Piloto de cartões na conversa web

Data: 2026-10-09.

## Promoções do Telegram

O radar de promoções também envia um cartão antes da fala, com o produto
rastreado, o canal e o link da mensagem. Quando o radar baixou uma foto para
`Luna/promo_imgs` no Obsidian, a web reaproveita esse mesmo arquivo e centraliza
a imagem. A rota serve somente JPGs dessa pasta; não abre outras notas ou caminhos
do vault. O link da promoção não aparece duplicado e a nota completa continua
depois da fala. Canal sem link público conserva o cartão sem inventar um link.

Não há download nem chamada adicional à LLM para o cartão. Promoção sem foto,
download que falhou ou imagem já removida mantém produto, canal e links sem
ícone de imagem quebrada. O comportamento vale para os próximos avisos; os
metadados de cartões não são reconstruídos para falas antigas.

Validação: os 45 arquivos de testes da web e 44 testes Python relacionados
passaram. Uma foto já existente no cache real também foi servida com HTTP 200
e `image/jpeg`, sem iniciar outra instância da Luna.

## Resultado

Novidades dos feeds agora trazem um cartão com o título original, a fonte e o
link da matéria antes do comentário da Luna. No ajuste de 10/10, o link da nota completa
fica dentro do cartão da notícia, à direita, como **Ver todas**. Promoções conservam a
nota depois da fala; o link individual não aparece duplicado.

Nas miniaturas das notícias, o ajuste de 10/10 acrescenta um fundo difuso com as cores da
própria imagem, cantos suaves e fade curto nas extremidades. O centro permanece nítido,
com proporção preservada e altura máxima de 180 px. O efeito é CSS estático: não gera uma
imagem nova, não usa LLM e não anima o desfoque. O fundo é ativado apenas depois da carga
da miniatura, preservando a leitura lazy; imagem que falha também remove a área vazia.

Conferência desse efeito: 45 arquivos de testes Web passando; prévia no Edge em 900 e 420 px,
sem corte horizontal, com miniaturas horizontais, quadradas e verticais mantendo a proporção.
Prévia isolada, com imagens vetoriais de teste: `logs/bancada_web/20261010-miniatura-difusa/preview.html`.

Retornos combinados, novidades do Sopro e acompanhamentos de fontes recebem
cartões depois do comentário, com assunto, situação e próximo passo. O botão
**Ver acompanhamento** abre a seção correspondente do painel existente. Fontes
e Sopro também permitem **Pausar/Retomar**; os retornos de conversa usam os
controles que já existem no painel.

Situação, próximo passo e pausa seguem o estado atual enviado pelo servidor,
inclusive em mensagens antigas. O trecho da fonte continua sendo a evidência
daquela atualização. Um plano anunciado não vira algo disponível por ter sido
lido. Os botões ficam indisponíveis até receber o estado inicial ou após perder
a conexão; um acompanhamento removido aparece como não ativo.

## Custo e alcance

O piloto usa componentes nativos da interface e metadados das ferramentas.
Não instala OpenUI nem adiciona uma chamada ao modelo. Os prompts, sua montagem
e o golden mantêm exatamente os hashes da cópia anterior ao piloto.

Os cartões viajam no histórico web separados do texto. Títulos, evidências e
ações não entram na legenda, no texto do áudio ou no histórico de mensagens
enviado ao LLM. Os textos externos usam `textContent`; links dos cartões são
HTTP(S), com o protocolo Obsidian restrito ao link da nota já existente.

O escopo inicial são as falas proativas de novidades e acompanhamentos. Respostas
comuns continuam usando o Markdown da web. Mensagens antigas sem os novos dados
continuam mostrando seus links; não são transformadas retroativamente em cartões.
Os acompanhamentos continuam exigindo a confirmação/cadastro que já tinham.

## Validação

- Antes: 43 arquivos da suíte de interface passaram.
- Depois: 44 arquivos passaram em `node testes/rodar.js`, incluindo carga do script
  completo, renderização dos cartões, links antigos, cópia da fala e reconexão.
- 71 testes Python passaram: cartões, acompanhamentos de conversa, fontes, Sopro,
  links de novidades, interrupção do radar e recebimento de mensagens web.
- Os oito testes de montagem do prompt passaram, sem atualizar o golden.
- No navegador de teste, quatro cartões renderizados pelo código real não
  causaram overflow em 390 ou 760 pixels. Oito verificações de interação passaram:
  pausa, retomada, painel, desconexão, reconexão, retomada do Sopro, controles de
  conversa e espera por um plano ainda não disponível.
- Os testes das tarefas confirmaram metadados e a mesma quantidade de gerações.
  O teste do servidor confirmou texto limpo e metadados separados após serializar
  o evento/histórico em JSON.

Dois testes isolados de WebSocket de fontes/Sopro foram ajustados para encerrar
com `ConnectionClosed`, como a desconexão normal do servidor. Antes, o esgotamento
do mock levantava `StopIteration` e a extração isolada não incluía a classe da
exceção tratada. As asserções existentes foram preservadas.

Não foi iniciada outra instância da Luna, nem feito teste de fala ao vivo nesta
rodada. A qualidade dos comentários continua dependendo do modelo e dos prompts
existentes; este piloto valida a apresentação e os controles.

## Experimentar

Abra [a prévia interativa](../logs/bancada_web/20261009-cartoes/preview.html).
Ela usa o renderizador e os estilos reais com exemplos identificados como
demonstração. Pausa e reconexão alteram somente essa página. Não são notícias
reais nem resultados novos da bancada do modelo.

Para usar na aplicação, reinicie a Luna e recarregue o modo web. Os cartões
aparecem nas próximas falas proativas desses modos. O painel atual continua
sendo o lugar para cadastrar fontes e confirmar os retornos combinados.

Artefatos locais, ignorados pelo Git:

- `logs/bancada_web/20261009-cartoes/preview.html` e capturas `preview-390.png`,
  `preview-760.png`.
- `layout.json`, `interacoes.json` e `prompt_inalterado.json`.
- Cópias anteriores e hashes em `antes/` e `hashes_antes.json`.

Comandos de regressão:

```powershell
node testes/rodar.js
.\venv\Scripts\python.exe -X utf8 -m unittest testes.testa_cartoes_web testes.testa_acompanhamento_sopro testes.testa_acompanhamento_fontes testes.testa_acompanhamentos testes.testa_links_novidades testes.testa_radar_interrupcao testes.testa_recebimento_web
.\venv\Scripts\python.exe -X utf8 -m unittest testes.testa_prompt_montagem
```

## Miniaturas das novidades — 2026-10-09

O cartão agora reaproveita a URL de imagem do mesmo item selecionado para o
Obsidian (`destaque[4]`). Não faz nova busca, geração ou extração da página.
A imagem é opcional, carregada pelo navegador quando o cartão estiver próximo
da área visível. A URL permanece nos metadados, fora da fala e do prompt.

URLs inválidas são ignoradas. Se o servidor da imagem falhar, o elemento é
removido e título, fonte e link continuam disponíveis. As dimensões ficam
limitadas a 320 × 180 pixels, adaptando a largura a janelas menores.

Validação desta extensão: 44 arquivos de interface e 14 testes Python de cartões,
radar e links passaram. A regressão do radar compara a URL entregue ao Obsidian
com a do cartão e verifica uma única geração, sem incluir essa URL no pedido ao
modelo. Os hashes de `prompts.py`, `pensar.py` e do golden continuam iguais aos
anteriores à extensão.

O navegador de teste carregou uma miniatura servida por um HTTP local temporário
e recebeu 404 para outra. Em 390 e 760 pixels, a primeira apareceu sem overflow;
a segunda desapareceu, preservando o cartão. As interações anteriores também
passaram. As capturas usam imagem e notícias sintéticas:
[390 pixels](../logs/bancada_web/20261009-miniaturas/preview-390.png) e
[760 pixels](../logs/bancada_web/20261009-miniaturas/preview-760.png).

Reinicie a Luna e recarregue a web para aplicar. As próximas novidades terão
miniatura quando o feed fornecer uma imagem acessível. O histórico anterior
sem essa URL continua com texto.
