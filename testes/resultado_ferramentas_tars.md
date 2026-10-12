# Ferramentas com TARS — 12/10/2026

## Resultado

**O TARS não impediu nenhuma ação nesta amostra.** Os 54 pedidos com ferramenta
chegaram ao despacho esperado, e os seis comentários ficaram sem ferramenta.
Nome da música, artista, conteúdo da nota, URLs, título e horário da reunião
foram preservados nos argumentos. A ação simulada aconteceu antes da persona.

O contrato completo do roteador passou em 58/60 turnos. Os dois desvios ocorreram
no comentário sobre música com o antigo histórico GLaDOS: respondeu com sarcasmo
em vez de `SEM_FERRAMENTA`. Esse texto foi descartado pelo Python, que chamou
a persona normalmente. Com histórico vazio ou TARS, o contrato passou em 40/40.

Na apresentação, a persona manteve bastante sarcasmo e voltou ao botão do
histórico até em tarefas sem relação com design. O fluxo de ferramenta está
funcional nesta bancada; a cumplicidade e a relevância do humor precisam de
calibração. A consulta de agenda também recebeu provocações que atrapalham a
neutralidade antes desejada para esse uso.

## Método

Dez situações × três históricos × duas seeds (12801/12802): 60 turnos e
**120 chamadas reais**, com roteador e persona. São 20 turnos por histórico.

- Histórico vazio.
- Histórico GLaDOS: mesmas quatro mensagens da bancada anterior, extraídas de
  respostas reais do smoke a entradas sintéticas.
- Histórico TARS: quatro mensagens extraídas do piloto TARS, a partir de `eae`
  e do relato sobre passar meia hora escolhendo a cor de um botão. São falas
  reais de bancada; não são memórias pessoais nem exemplos inseridos na produção.

Gemma 4 12B IT QAT Q4_0, TurboLLM 1.13.4, llama.cpp b9608 ROCm, contexto 8192,
um slot. Thinking desligado; roteador com temperatura zero e teto 256; persona
com temperatura 0,8 e teto 500. Cache de prompt desligado. Relógio sintético
fixado em 12/10 às 17h; compromisso sintético em 13/10 às 14h.

As 60 chamadas de persona usaram o prompt completo web. Todas as ferramentas
foram substituídas por fixtures, inclusive caminhos especiais de notas e fontes.
Uma ferramenta inesperada abortaria o turno. Nenhuma música, evento, nota,
abertura de navegador ou acompanhamento foi realmente executado/cadastrado.

Os hashes dos 19 arquivos de referência e a identidade do modelo foram
conferidos. Nenhum arquivo de produção mudou durante a rodada. Os pedidos
do roteador foram conferidos contra o snapshot preparado.

## Resultado por situação

| Situação | Turnos | Decisão | Apresentação |
|---|---:|---|---|
| Tocar música | 6 | 6/6 controlar_spotify, ação tocar | Confirmou Metamorfose Ambulante, de Raul Seixas; frequentemente retomou o botão |
| Pausar música | 6 | 6/6 controlar_spotify, ação pausar | Confirmou pausa; parte das falas trouxe provocação pessoal |
| Consultar agenda | 6 | 6/6 ler_agenda_google | Preservou reunião, dia e horário; nem sempre ficou neutra |
| Criar reunião | 6 | 6/6 adicionar_agenda | Título e data/hora corretos; confirmou criação do retorno simulado |
| Anotar café | 6 | 6/6 salvar_obsidian | Conteúdo comprar café preservado; confirmou registro |
| Abrir Firefox | 6 | 6/6 controlar_navegador | URL exata; confirmou abertura |
| Resumir artigo | 6 | 6/6 resumir_site | Preservou 200 → 150 MB, ausência de testes e ausência de PT-BR; acrescentou julgamentos/intenção |
| Preparar fonte | 6 | 6/6 preparar_acompanhamento_fontes | Assunto e interesse corretos; explicou que a consulta só começa após confirmar |
| Spotify desconectado | 6 | 6/6 controlar_spotify | As seis respostas informaram a falha; nenhuma anunciou reprodução |
| Comentário sobre música | 6 | 6/6 sem ferramenta | Persona respondeu; dois desvios textuais do roteador com histórico GLaDOS |

## O roteador e o histórico

| Histórico | Decisão de ferramenta | Contrato completo |
|---|---:|---:|
| Vazio | 20/20 | 20/20 |
| GLaDOS | 20/20 | 18/20 |
| TARS | 20/20 | 20/20 |

Os 40 pedidos do roteador com histórico vazio/GLaDOS são exatamente iguais
aos registrados na rodada GLaDOS anterior. O sistema do roteador não recebe
IDENTIDADE/EMOCAO TARS. Assim, o mesmo desvio não demonstra que o prompt TARS
estragou o roteador: ele já estava presente com aquela entrada e aquele histórico.

Nas duas seeds com histórico GLaDOS, o roteador repetiu o mesmo texto de 170
tokens, contra seis tokens para `SEM_FERRAMENTA`. O turno completo levou 14,82
e 15,04 segundos nesses dois casos. Com histórico TARS, levou 8,67 e 9,00 segundos.
Isso é geração desperdiçada pelo roteador; o parágrafo dele não foi usado como
retorno técnico. Repetir seeds em temperatura zero não equivale a amostras
estatisticamente independentes.

## Onde a persona funcionou e onde passou do ponto

### Falha sem inventar sucesso

> Não consegui tocar a música porque o seu Spotify está desconectado.

Essa foi a resposta nas seis combinações de seed e histórico. Apresentou o
problema técnico com clareza, sem transformar indisponibilidade em recusa da IA.

### Confirmação pendente preservada

> Como você ainda não confirmou o acompanhamento, os dados ainda não estão ativos.

As seis respostas mantiveram o estado de rascunho e pediram o clique de confirmação.
Isso é a fronteira entre preparar o cartão e começar uma consulta recorrente.

### Resumo com suposição sobre intenção

O artigo só dizia que ainda não havia testes de velocidade. Uma resposta acrescentou:

> como de costume, eles também não têm a mínima ideia (ou interesse) em mostrar os testes de velocidade por enquanto.

Conhecimento, interesse e hábito dos responsáveis não estavam no artigo. Outras
falas chamaram a atualização de medíocre ou os arquivos de inúteis. São opiniões
e provocações sem argumento adicional, que podem enfraquecer o resumo.

### Piada antiga fora do assunto

Pedidos de música, agenda e café retomaram repetidamente a indecisão sobre a cor
do botão. Os históricos TARS e GLaDOS contêm esse fato, mas repeti-lo em toda
resposta não torna a conversa mais presente. Uma consulta de agenda virou:

> o resto do seu calendário parece estar tão vazio quanto a sua capacidade de decidir a cor de um botão.

Essa formulação também ocorreu com histórico TARS. Trocar a referência da
personagem não garante que toda fala adquira cumplicidade automaticamente.

## Validação e alcance

Todas as 60 chamadas de persona terminaram com `stop`. O roteador teve 54
`tool_calls` e seis `stop`, sem truncamento ou reasoning. Sem erro de execução
da bancada e sem despachos indevidos. Maior entrada: 4558 tokens no roteador,
2508 na persona; nenhuma chegou ao contexto de 8192. Mediana por turno: 7,32 s,
incluindo roteador e persona, sem TTS nem jogo disputando a GPU.

Os 46 arquivos Node passaram, os dez testes da captura/validação de modelos
passaram e os executores compilaram. A leitura manual complementa a triagem:
schema correto não mede humor, fidelidade da confirmação ou pertinência.

Os executores antigos receberam parâmetros opcionais de personagem/histórico
e títulos corretos para os relatórios. Os cenários, seeds, retornos e caminhos
de produção foram reutilizados; a rodada anterior permaneceu em sua pasta.

Resultados completos: `logs/bancada_tars/20261012-integracoes/ferramentas/resultados.json`.
Saídas brutas/argumentos: `respostas.md`. Alertas: `triagem.json`.
Auditoria conjunta: `logs/bancada_tars/20261012-integracoes/auditoria.json`.
Executor: `python -X utf8 -m testes.bancada_tars_integracoes ferramentas`.

Este teste valida o fluxo com retornos simulados. Autenticação e disponibilidade
dos serviços externos, TTS, interface, FPS e partidas reais ficaram fora da rodada.
