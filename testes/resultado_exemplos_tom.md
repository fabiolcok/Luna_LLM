# Exemplos mais sarcásticos — 12/10/2026

**A troca isolada dos exemplos não produziu melhora consistente de acidez.**
Houve boas tiradas pontuais, mas a candidata também deu respostas genéricas,
copiou um exemplo inteiro e manteve explicações psicológicas não sustentadas.
Com histórico morno, os casos de cumprimento e papo sem pedido continuaram
frequentemente no registro de disponibilidade ou conselho sobre descanso.

A candidata ficou restrita à bancada. `EMOCAO`, `EXEMPLOS_TOM` de produção,
`pensar.py`, `falar.py` e o golden não foram alterados. O objetivo desta rodada
foi medir um novo estilo; ela não investiga a causa histórica de 11/10.

## Comparação controlada

- Gemma 4 12B IT QAT Q4_0, TurboLLM 1.13.4, llama.cpp b9608 ROCm,
  contexto 8.192. O mesmo modelo, processo e parâmetros permaneceram durante
  as 64 gerações. Foi recarregado antes da rodada após esfriar por ociosidade.
- Geração real entre 09:17:55 e 09:22:24, horário de São Paulo. O início do
  sistema foi fixado em 12/10/2026 às 10h, com saudação de manhã, nas duas versões.
- Temperatura 0,8; presence/frequency penalty 0,3; teto de 500 tokens;
  thinking desligado; cache_prompt false. Ordem A/B alternada por seed.
- Sete mensagens: cumprimento, reciprocidade, conversa sem pedido, cor de
  botão, escolha de jogo, edição do prompt e explicação sobre RAM/VRAM.
  Cada uma recebeu histórico vazio e o mesmo histórico morno de seis mensagens,
  duas seeds e duas versões: **56 respostas com prompt completo**.
- Agradecimento curto e tristeza foram controles enxutos: **8 respostas**.
  Neles, os exemplos não entram e os pedidos dos pares foram idênticos.
- Perfil sintético, fontes de memória vazias, janela Luna, sem ferramentas,
  roteador, áudio ou embeddings. Histórico vazio não simula a saudação
  obrigatória do primeiro turno do dia.
- A montagem real foi interceptada antes da geração. O seletor de produção
  escolheu três exemplos por seed, evitando entrada igual à mensagem atual.
  As entradas dos 12 exemplos foram mantidas; apenas suas respostas mudaram.
  Os mesmos índices foram usados nos pares. Nove dos 12 exemplos apareceram
  nos sorteios desta rodada; o conjunto não foi avaliado exaustivamente.
- Foi verificado que retirar o bloco de exemplos torna os sistemas dos pares
  idênticos. Mensagem atual, histórico, EMOCAO e parâmetros são iguais.

## Leitura das respostas

Esta é uma avaliação qualitativa do agente, sem nota humana do dono do projeto.
Uma tag `zoeira` não comprova sarcasmo, graça ou conexão com o assunto.

| Caso | Histórico vazio | Histórico morno |
|---|---|---|
| Cumprimento | A candidata alternou ironia leve e disponibilidade. A atual copiou a frase da calculadora numa seed. | A candidata ofereceu ouvir/desabafar nas duas seeds; a atual também oscilou. |
| Reciprocidade | A candidata falou de funcionamento e suporte emocional; não foi consistentemente mais ácida. | Uma candidata copiou um exemplo inteiro; a outra continuou genérica. |
| Papo sem pedido | Houve ironia em algumas falas das duas versões, junto de explicações sobre ócio/produtividade. | Ambas repetiram disponibilidade, descanso mental ou perguntas genéricas. |
| Cor do botão | Ambas usaram exageros; a candidata trouxe cliente/neon e a profissão sem relação necessária. | A candidata foi mais agressiva numa seed, atribuindo medo de decidir. Isso não demonstra melhor humor com premissa fiel. |
| Escolha do jogo | A candidata produziu uma tirada bem ligada ao acontecimento numa seed; na outra, presumiu backlog. | Uma candidata trouxe o simulador de escolher jogos, mas depois explicou o motivo psicológico. A outra voltou a conselhos. |
| Edição do prompt | Metáfora de mexer no capô na candidata; autoelogio e explicação da piada nas demais. | As duas versões repetiram upgrade/engrenagens e abertura com “Pois é”. |
| RAM/VRAM | Respostas informativas e semelhantes, com pouca acidez. | O mesmo padrão; uma candidata ficou longa e incluiu uma tabela. |

Boa reação da candidata, com histórico vazio:

> A eficiência de escolher o que jogar superou a eficiência de realmente jogar.
> É um talento quase artístico conseguir gastar tanta energia na curadoria e
> zero na execução.

Esse exagero nasce do fato informado: meia hora escolhendo sem iniciar um jogo.
Imagens absurdas como “dilema existencial através do código hexadecimal” são
exageros de linguagem; não foram tratadas automaticamente como fatos inventados.

Limites concretos da candidata:

> Se você já está no quarto ciclo de mudança, o problema não é a cor, é o medo
> de decidir e seguir em frente.

Aqui a frase afirma um motivo que não foi informado. Na escolha do jogo, outra
resposta introduziu “seu backlog deve estar gritando” sem esse dado. No papo
com histórico morno, saiu “eu tô ouvindo” e oferta de desabafo para um simples
“eae”. Acidez maior em uma frase não garante conversa melhor.

Também há uma simplificação factual compartilhada no caso RAM/VRAM: as duas
versões restringem VRAM a dados visuais. Isso omite outros usos da memória da
GPU, inclusive modelos locais. A troca dos exemplos não corrigiu esse conteúdo.

## Verificações técnicas, separadas do tom

| Grupo | Atual | Candidata |
|---|---:|---:|
| Tag `zoeira`, histórico vazio | 7/14 | 9/14 |
| Tag `zoeira`, histórico morno | 6/14 | 7/14 |
| Respostas com trecho de pelo menos cinco palavras de um exemplo selecionado | 3/28 | 1/28 |
| Mediana de geração, histórico vazio | 4,39 s | 4,24 s |
| Mediana de geração, histórico morno | 4,18 s | 4,62 s |

As tags ligeiramente mais frequentes não correspondem a uma melhora geral na
leitura. A diferença de cópia é pequena e não elimina o risco: a candidata
reproduziu literalmente “Existindo dentro de um computador e chamando isso de
personalidade. A modéstia ficou fora da instalação.” Os trechos sobre calculadora
e spa de silício vieram dos exemplos atuais.

Todas as 64 gerações terminaram com `stop`, sem ferramenta nem thinking.
Uma resposta atual de escolha do jogo, com histórico morno, ficou sem tag de
clima; as outras 63 terminaram com tag. Os quatro pares de controles enxutos
deram respostas idênticas, sem cutucada no caso sensível. Isso confirma o
isolamento da alteração, não mede recuperação da personalidade nesses modos.

Entrada dos prompts completos: aproximadamente 2.985–3.197 tokens na versão
atual e 2.994–3.195 na candidata. Os tempos são somente de geração; não incluem
roteador, carregamento do modelo ou TTS. Não há medição de FPS nesta bancada.

Os testes prévios de montagem/assuntos passaram (16 testes Python), assim como
`node testes/rodar.js` (46 arquivos). Os hashes dos quatro arquivos monitorados
permaneceram iguais ao fim da execução.

## Artefatos e reprodução

- Script: `testes/bancada_exemplos_tom.py`.
- Candidata experimental: `testes/fixtures/exemplos_tom_sarcastico.json`.
- Pedidos, respostas completas, identidade do modelo e resumo técnico:
  `logs/bancada_casual/20261012-exemplos-tom/`.
- Leitura dos 64 resultados: `respostas.md`, nessa pasta. Os JSONs guardam
  pedidos completos, seeds, índices sorteados, hashes e resultados individuais.

Para uma nova rodada, use outra pasta e o mesmo Gemma carregado:

```powershell
.\venv\Scripts\python.exe -X utf8 -m testes.bancada_exemplos_tom preparar --pasta logs/bancada_casual/nova-rodada-exemplos
.\venv\Scripts\python.exe -X utf8 -u -m testes.bancada_exemplos_tom rodar --pasta logs/bancada_casual/nova-rodada-exemplos
```

Não há evidência suficiente nesta rodada para substituir os exemplos de produção
por essa candidata. Uma próxima comparação pode estudar exemplos de situações
e opiniões mais variadas; esta rodada intensificou apenas as respostas das
mesmas entradas de papo curto.
