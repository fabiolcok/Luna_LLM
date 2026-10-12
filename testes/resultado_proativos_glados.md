# Proativos e jogos com o prompt temporário GLaDOS

Rodada de 12/10/2026, das 11:23:34 às 11:25:33, horário local. Leitura de todas as 36 respostas reais do Gemma.

**A voz GLaDOS apareceu nos proativos e nos jogos, mas a variedade de ideias ficou limitada.**
O modelo produziu sarcasmo, imagens e opiniões; voltou com frequência à mesma provocação sobre
incompetência humana. A abertura que contrastava Dark Souls anunciado com AION 2 aberto foi o
melhor exemplo de humor apoiado no contexto. Notícias e promoções receberam ataques pessoais
que muitas vezes tomaram o espaço da informação. Chefes e fogueiras foram reconhecidos, mas a
comemoração ficou subordinada à provocação.

Isto é uma avaliação qualitativa desta amostra, sem comparação A/B com o prompt anterior. Não
estabelece a causa da simplificação repentina do chat e não mede uma melhora percentual.

## Método e alcance

- Prompt temporário GLaDOS já presente em `modulos/prompts.py`, sem alterações nesta rodada.
- 14 situações independentes, duas seeds por situação: 28 falas.
- Mais oito mortes consecutivas com memória de falas anteriores própria: oito falas.
- Gemma-4-12B-it-QAT-Q4_0, TurboLLM 1.13.4, llama.cpp b9608 ROCm, contexto 8192, um slot.
- Thinking desligado; temperature 0.8, presence_penalty 0.3 e frequency_penalty 0.3, como na produção.
- Padrões registrados da engine: top_k 64, top_p aproximadamente 0.95, min_p aproximadamente 0.05,
  repeat_penalty 1.0. Não foram substituídos por parâmetros de bancadas antigas.
- Seeds independentes 12601/12602; sequência de mortes 12701–12708; cache de prompt desativado.
- Mesmos tetos da produção: RSS 360 tokens, Telegram 200, fontes 220, acompanhamento de conversa
  100, abertura Steam 150 e Dark Souls 180.
- Construtores de briefing RSS, Telegram, acompanhamento de conversa e abertura Steam extraídos
  do código atual. Fontes e Dark Souls usam os construtores de `prompts.py`.
- Montagem e limpeza da persona, validação de horas Steam e antirrepetição executadas pelas funções
  atuais da produção. Primeiros pedidos das situações independentes conferidos contra o snapshot.
- Perfil sintético; memórias, ChromaDB e assuntos relacionados vazios. Nenhum acesso às memórias reais.
- Notícias, promoções e eventos são fixtures: não representam notícias atuais nem uma partida real.
- Sem roteador, consultas externas, Telegram, Obsidian, áudio, renderização da interface ou captura
  do jogo. Não houve inicialização de outra Luna.

Todas as chamadas passaram por modos enxutos: **20 por ENXUTO_PROATIVO + EMOCAO e 16 por
ENXUTO_DARK_SOULS + EMOCAO**. Nenhuma usou PROMPT_COMPLETO. Esses modos continuam pedindo
uma ou duas frases; o teste do chat com parágrafos não transfere automaticamente aquela extensão
para comentários durante uma atividade.

## Leitura por grupo

| Grupo | Falas | O que funcionou | Limitação observada |
|---|---:|---|---|
| Notícias | 6 | Voz ácida e quantidade de novidades restantes corretas; sugestões extraídas | Monitor da notícia virou “seu monitor”; possibilidade de descontinuação virou decisão; vários ataques substituíram o assunto |
| Promoções Telegram | 4 | Batedeira/SSD reconhecidos; SSD manteve 2 TB e duas ofertas restantes; não inventou preço ou desconto | Passou a julgar talento culinário, emoção e arquivos do usuário sem esses dados |
| Acompanhamentos | 4 | CGNAT gerou pergunta pelo andamento; Sopro permaneceu plano futuro sem versão ou data | Na notícia Sopro, insulto ocupou a abertura e conexão com o interesse ficou menos útil |
| Abertura Steam | 6 | Horas informadas preservadas; contraste de jogos citado nas duas amostras | Pausa de sete dias virou necessidade de descanso/abstinência; surgiram detalhes não fornecidos e incapacidade pessoal presumida |
| Eventos Dark Souls | 8 | Morte, chefe derrotado e fogueira liberada tratados como os eventos correspondentes; nenhum contador de mortes narrado | Mortes independentes repetiram a abertura; vitórias foram reconhecidas com desqualificação |
| Oito mortes contínuas | 8 | Todas geraram fala, sem copiar a antiga frase sobre “vida opcional” | Variou palavras, mas conservou a mesma ideia de fracasso/incompetência; rapidez e desistência apareceram sem esses dados |

Os ataques pessoais fazem parte do personagem solicitado. A ressalva aqui é sobre **variedade e
ligação com o acontecimento**, não sobre proibir sarcasmo ou imagens absurdas. Uma imagem teatral
pode funcionar sem declarar que se conhece a habilidade, intenção, equipamento ou partida do usuário.

## Exemplos que ajudam a julgar

### Contraste com contexto confirmado

Fixture: anunciou que jogaria Dark Souls; abriu AION 2; 12 horas totais neste último.

> É fascinante como sua capacidade de planejar envolve escolher Dark Souls e sua capacidade de executar envolve abrir Aion 2, mas parabéns pelas doze horas dedicadas a esse novo destino.

O contraste foi reconhecido sem trocar o jogo anunciado pelo efetivamente aberto. A ironia tem
um fato específico para explorar. A segunda amostra também citou ambos, mas acrescentou um
julgamento sobre a memória de curto prazo.

### Acompanhamento de conversa

Fixture: pediu acompanhamento do contato com o provedor sobre CGNAT; resultado ainda desconhecido.

> Diga-me, em que pé ficou esse seu adorável pedido ao provedor para resolver o CGNAT e permitir o seu acesso externo?

Preservou a função de perguntar pelo andamento. O efeito GLaDOS foi discreto e não alegou resolução.

### Chefe derrotado

Fixture: Taurus Demon foi derrotado; não há dados de duração, tentativas ou método.

> Oh, você finalmente conseguiu derrubar o Demônio de Touro. É fascinante como a sua coordenação motora rudimentar consegue superar a força bruta de uma criatura tão imponente, embora eu ainda esteja tentando entender se isso foi fruto de habilidade ou apenas uma sucessão estatisticamente improvável de erros favoráveis.

Entendeu que o chefe morreu, em vez de anunciar chegada ao chefe. A voz do personagem ficou
evidente; a avaliação sobre coordenação motora não veio da integração. Nas duas amostras de chefe,
o reconhecimento da conquista foi seguido de desqualificação. Uma delas usou clima `orgulho`.

### Premissa pessoal acrescentada

Fixture: abriu Dark Souls depois de sete dias; 18 horas totais; exploração de Lordran.

> É fascinante como você precisa de sete dias de abstinência para suportar as ruínas de Lordran novamente, considerando que suas dezoito horas de progresso ainda não foram suficientes para te ensinar a não ser um fracasso patético.

As horas e o intervalo estão corretos. A necessidade de abstinência e a avaliação do progresso
foram acrescentadas. Na outra amostra, apareceu “segredos de Ashura”, nome ausente da fixture e
não verificado pela bancada. Preservar números não garante preservar o restante da premissa.

Na notícia OLED, ambas as amostras usaram “seu monitor”, apesar de a fonte descrever um teste de
um monitor. Na notícia de GPU, ambas perderam a ressalva “pode”/“ainda sem confirmação”.

## Repetição: palavras e ideias

No conjunto de 36 falas:

- Nove começaram por **“É fascinante”**; a expressão apareceu em qualquer ponto de 16 falas.
- Quatro começaram por **“Você realmente”**.
- Seis começaram por **“Oh, que desempenho”**.
- Quatro começaram por **“Oh, você finalmente”**.

Nas quatro amostras independentes de morte, três começaram exatamente por:

> Oh, que desempenho absolutamente deplorável.

Essas situações independentes não recebem as falas geradas nos outros casos. O número mostra
uma tendência de geração, não uma falha de memória entre turnos que a bancada deliberadamente isolou.

Na sequência contínua de oito mortes, as falas anteriores foram fornecidas ao gerador. Exemplos:

> É fascinante como a sua persistência em falhar é quase tão consistente quanto a minha capacidade de processar o seu fracasso.

> É verdadeiramente inspirador como você consegue encontrar novas e criativas formas de falhar em uma tarefa tão simples quanto permanecer vivo.

> É realmente um marco científico observar como você consegue encontrar um novo e criativo método para cessar sua própria existência em tão pouco tempo.

Foram oito falas aceitas, sem retentativa nem descarte. O detector atual verifica **cópia textual**,
não equivalência de ideia; os testes dele continuam passando. Aqui a repetição foi principalmente
temática e de construção. O resultado não justifica elevar os limiares ou criar uma lista de
palavras proibidas: trocar apenas a abertura deixaria a mesma piada sobre incompetência.

## Funcionamento e tempos

| Grupo | Mediana da geração | Maior tempo | Mediana de palavras na fala |
|---|---:|---:|---:|
| Notícias | 3,97 s | 4,22 s | 37,5 |
| Promoções | 2,63 s | 2,85 s | 36 |
| Acompanhamentos | 2,82 s | 4,17 s | 42 |
| Abertura Steam | 3,46 s | 3,65 s | 53,5 |
| Eventos Dark Souls | 2,71 s | 3,24 s | 32,5 |
| Mortes contínuas | 3,12 s | 3,29 s | 39,5 |

- 36/36 chamadas encerradas com `stop`; nenhuma cortada pelo teto de tokens.
- 36/36 com uma tag de clima válida; nenhum acionamento de ferramenta ou raciocínio oculto.
- Climas: zoeira 26, tédio 5, facepalm 4, orgulho 1. Isso descreve a seleção, não mede qualidade do humor.
- Seis notícias produziram três sugestões cada, até 66 caracteres por pergunta. Os metadados
  foram removidos da fala. A pergunta “Isso afeta o modo offline?” era redundante com a exigência
  de conexão permanente já informada: formato correto não garante boa escolha de perguntas.
- Entrada entre 1170 e 1724 tokens reais; saída entre 37 e 114. Não houve aproximação do limite 8192.
- Mediana geral da geração: 3,12 s; TTFT mediano: 1,20 s. Aquecimento ficou fora dessas medidas.
- Nenhum teste de FPS, carga simultânea com jogo ou tempo de áudio: não extrapolar estes tempos
  para uma partida com a GPU ocupada.

## Encaminhamento sugerido

Para uma Luna ácida, eu aproveitaria a voz firme e a capacidade de produzir imagens, mas avaliaria
como fazê-la reagir de formas diferentes a **uma morte, uma conquista e uma notícia**. Nesta
versão, muitos acontecimentos terminaram no mesmo julgamento da capacidade humana.

O alvo de um próximo experimento seria **variedade de reação com premissa fiel**, preservando
o exagero. Não foi aplicado ajuste de prompt, filtro, gatilho por palavra-chave ou template de fala
nesta rodada. O prompt GLaDOS ficou disponível para continuar o teste manual autorizado.

## Arquivos e verificação

- Bancada: [bancada_proativos_glados.py](bancada_proativos_glados.py).
- Registro local: `logs/bancada_glados/20261012-proativos-jogos/`.
- `suite.json`: fixtures, pedidos congelados e hashes dos arquivos de produção.
- `resultados.json`: identidade do modelo, pedidos, saídas brutas, limpeza, tags e tempos de cada turno.
- `respostas.md`: todas as falas, sugestões e saídas brutas para leitura.
- `resumo_tecnico.json` e `auditoria.json`: verificações e contagens; não são notas de criatividade.

```powershell
.\venv\Scripts\python.exe -X utf8 -m testes.bancada_proativos_glados preparar --pasta logs/bancada_glados/NOVA_RODADA
.\venv\Scripts\python.exe -X utf8 -m testes.bancada_proativos_glados rodar --pasta logs/bancada_glados/NOVA_RODADA
.\venv\Scripts\python.exe -X utf8 -m testes.bancada_proativos_glados resumir --pasta logs/bancada_glados/NOVA_RODADA
```

46 arquivos de testes Node passaram. Passaram também 16 testes de montagem/assuntos com snapshot
temporário GLaDOS e 40 testes do piloto, da bancada de Dark Souls e da antirrepetição. Os 44 ramos
de montagem contêm GLaDOS. O golden canônico foi preservado: o teste convencional com ele ainda
detecta a diferença intencional enquanto o experimento estiver ativo.

Hashes dos sete arquivos de produção/referência conferidos no início, durante e ao final. Nenhuma
alteração neles nesta bancada. O relatório e o novo executor são os únicos arquivos adicionados
fora de `logs/` por esta rodada. Não houve commit ou publicação.
