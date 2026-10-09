# Bonsai PQ2 × Gemma — bancada da Luna

## Rodada de 20/09/2026

**Comparação concluída: nesta configuração da Luna, eu manteria o Gemma 12B.** Foram
14 cenários, duas repetições por modelo, 56 chamadas medidas. O Gemma acertou mais
contratos de roteamento/formato e respondeu mais rápido. Os dois ainda inventaram
premissas para fazer humor; isso aparece na leitura manual, mesmo quando o check passa.

As duas rodadas usaram as mesmas mensagens e schemas congelados, sem ajustar o
prompt entre modelos. Os arquivos de resultados preservam os alertas originais.

Modelo confirmado pelo caminho em `/props`: `Ternary-Bonsai-2-27B-PQ2_0.gguf`.
Engine: `llama-prism-b10709-9a9394a-bin-win-hip-radeon-x64 (9a9394a)`.
Gemma: `gemma-4-12B-it-QAT-Q4_0.gguf`, no engine `llama.cpp b9608 (rocm)`.
Ambos: TurboLLM 1.13.4; contexto 8192; um slot. A identificação não depende do nome `Hf`
mostrado pela biblioteca, que pode confundir quantizações diferentes.

- Thinking desligado; nenhum texto de raciocínio retornado.
- Persona: temperatura 0,8, penalidades 0,3 e teto de 300 tokens; roteador: temperatura
  zero e teto de 256. Duas seeds, 1932 e 1933.
- Cache de prompt desativado por chamada; zero tokens de cache nos 56 resultados.
- Aquecimento fora do placar. Nenhuma resposta cortada pelo teto de tokens.
- Bonsai usou top_k 20 por padrão. Gemma tinha 64, então a bancada enviou `top_k=20`
  somente nas suas chamadas. `/slots` confirmou 20 em uso e `/props` continuou com
  64 como padrão; nenhuma configuração global do Turbo foi alterada. Ambos usaram
  top_p aproximadamente 0,95, min_p aproximadamente 0,05 e repeat_penalty 1.
- O engine do Gemma usou geração especulativa: `/slots` informou `none,draft-mtp`,
  e os resultados contêm contagens de tokens draft. O Bonsai não registrou drafts.
  Os tempos comparam os conjuntos **modelo + engine/configuração**, não isolam
  velocidade intrínseca dos modelos. Engines e templates também são diferentes.
- Nenhuma ferramenta executada, nenhuma conversa salva. A preparação isola o
  carregamento automático de `pensar.py`, os bancos de memória e o TTS.

## Tempos e triagem automática

| Ramo | Checks Bonsai | Checks Gemma | Total mediano Bonsai | Total mediano Gemma |
|---|---:|---:|---:|---:|
| PROMPT_COMPLETO | 5/10 | 8/10 | 9,61 s | 4,98 s |
| ENXUTO_COTIDIANO | 2/2 | 2/2 | 3,01 s | 1,94 s |
| ENXUTO_REFERENCIA_SEM_NOME | 0/2 | 2/2 | 2,08 s | 0,91 s |
| ENXUTO_PROATIVO | 4/6 | 3/6 | 4,86 s | 3,08 s |
| ROTEADOR | 6/8 | 8/8 | 11,82 s | 3,60 s |

| Primeira saída (TTFT mediano) | Bonsai | Gemma |
|---|---:|---:|
| PROMPT_COMPLETO | 6,90 s | 2,58 s |
| ENXUTO_PROATIVO | 2,85 s | 1,12 s |
| ROTEADOR | 10,36 s | 3,33 s |

Geração mediana: **29,92 tokens/s no Bonsai e 40,18 no Gemma**, considerando todas
as chamadas. No prompt completo, as medianas foram 29,83 e 35,06 tokens/s; boa parte
do ganho de espera veio da leitura inicial do prompt. TTFT mede a primeira saída de
texto ou tool call. Esses tempos são de chamadas isoladas: um turno reativo que passa
por roteador e persona soma as duas etapas, além de ferramenta, interface e eventual TTS.
Não são tempos de conversa completa nem medição de desempenho durante um jogo.

Os totais de **17/28 no Bonsai e 23/28 no Gemma não são notas de qualidade**. Exemplos abaixo mostram
problemas que os checks de palavras não detectam. A referência vaga foi corretamente
admitida pelo Bonsai nas duas respostas; seu 0/2 veio da ausência da tag de clima.
No Gemma, ambas as respostas admitiram a referência vaga e trouxeram a tag.

O contrato de emoção ficou em **14/20 no Bonsai e 20/20 no Gemma**. Todas as falas
proativas dos dois modelos incluíram tag válida. Acertar a tag não prova que a emoção
ou a piada ficou boa; prova que o front recebeu um valor previsto pelo contrato.

## Leitura das respostas do Bonsai

1. **Dados e idioma:** no radar de um jogo com **400 horas**, a primeira resposta saiu
   inteira em inglês e começou com “Forty hours”. A segunda preservou o número, mas
   excedeu o limite de caracteres do cenário.
2. **Continuidade factual:** sobre *Três Homens em Conflito*, respondeu 1966 nas duas
   rodadas. Na primeira, acrescentou outro título, *Once Upon a Time in the West*, e
   uma história que não estava no contexto. O check de ano sozinho não flagrou isso.
   A segunda resposta foi direta e ficou no filme solicitado.
3. **Roteamento:** “Hoje foi puxado”, com um pedido antigo de música no histórico,
   gerou `controlar_spotify` nas duas rodadas. A bancada apenas registrou a intenção;
   nenhuma música foi tocada. As perguntas explícitas de gameplay e música escolheram
   as ferramentas esperadas, com argumentos válidos nas duas rodadas.
4. **Emoção:** faltou `[clima:...]` em **6 das 20 respostas de persona**. Não foi
   truncamento. Todas as seis falas proativas incluíram uma tag válida.
5. **Naturalidade:** apareceram “eu vixo”, “teuçando” e “uma noiva nova no backlog”.
   Na abertura de Hollow Knight, a segunda fala terminou com “só porque você apertou
   a J”, sem contexto para essa tecla. Minha leitura é de perda de sentido, não de
   excesso de personalidade. Exagero teatral, por si só, não é defeito.
6. **Sinais bons:** a segunda resposta sobre gosto próprio foi coerente com a persona;
   as duas referências vagas foram admitidas sem inventar um nome; o modelo não
   inventou números para o placar desconhecido. Ainda assim, a primeira resposta sobre
   placar prometeu uma consulta que a fixture não garantia, e a segunda falou da “tela”
   mesmo tendo recebido apenas sinais de janela/jogo.

## Leitura das respostas do Gemma

1. **Roteamento melhor neste recorte:** ignorou o pedido antigo de música quando a
   mensagem atual era “Hoje foi puxado”, nas duas rodadas. Respondeu `SEM_FERRAMENTA`
   nos comentários e escolheu as ferramentas/argumentos esperados nos pedidos
   explícitos. Isso cobre quatro cenários, não todas as 26 ferramentas disponíveis.
2. **Ainda inventa números para a piada:** o usuário disse apenas “Passei o domingo
   inteiro tentando fazer um script de 10 linhas funcionar”. A primeira resposta
   transformou isso em “dez horas de vida”; a segunda introduziu “dezessete linhas”.
   Ambas passaram nos checks antigos. O problema é acrescentar dado, não exagerar.
3. **Atribui gosto sem base:** ao falar do próprio gosto, disse “o seu lado de grind
   infinito e gacha” e “o seu gosto por jogos que exigem aquele grind infinito”.
   O perfil sintético não dizia que o usuário gosta disso. O padrão apareceu nas
   duas rodadas, apesar dos checks aprovarem a presença dos gêneros da persona.
4. **Abertura de jogo mais ligada ao tema, na minha leitura:** “as 42 horas acumuladas
   mostram que você não é só um turista perdido no Reino de Hallownest” conecta o
   exagero ao jogo e ao dado recebido. Ficou mais compreensível que a referência do
   Bonsai a “apertou a J”. Ainda são só duas amostras por modelo.
5. **Placar desconhecido:** não inventou placar nas duas rodadas. Na segunda,
   explicou que os dados não mostram o conteúdo ou progresso do jogo. Na primeira,
   falou da janela “não mostrando detalhes”, formulação menos precisa para uma
   fixture que só entregava o título da janela e a detecção do jogo.

## Alertas que precisam de leitura humana

- No radar, o Gemma escreveu **“Quatrocentos horas”**. O número 400 foi preservado,
  mas houve erro de concordância. O check buscava somente `400` ou `quatrocentas`,
  então sinalizou ausência do número. Esse alerta não equivale à troca de 400 por
  40 feita pelo Bonsai. Na segunda rodada, o Gemma preservou 400 e passou 14
  caracteres do limite de 300; isso também não mede, sozinho, qualidade de humor.
- No filme, a fixture esperava 1966, ano catalogado pelo
  [BFI](https://www.bfi.org.uk/film/48f84a16-0530-544f-b591-0d564249dd43/the-good-the-bad-and-the-ugly).
  O Gemma respondeu 1967 duas vezes, que corresponde ao lançamento nos EUA, conforme
  o [AFI](https://fest.afi.com/2017/cinemas-legacy-2017/the-good-the-bad-and-the-ugly-il-buono-il-brutto-il-cattivo/).
  Faltou qualificar a data, e o enunciado não especificava país. Não trato essas duas
  respostas como invenção inequívoca. Os alertas brutos foram mantidos para preservar
  o mesmo critério nos dois modelos.
- O outro alerta do Gemma foi a expressão “tempo livre” no cenário de Overwatch.
  É uma proibição lexical herdada da bancada antiga, não uma avaliação semântica
  completa da frase. Por esses motivos, o 3/6 contra 4/6 no proativo não demonstra
  que o Bonsai teve humor melhor.

**Decisão sugerida:** manter o Gemma na Luna por enquanto. Neste teste ele trouxe
melhor roteamento, formato mais consistente e menor espera. A prioridade de qualidade
que ficou evidente é impedir números, hábitos e preferências inventados para sustentar
a piada, preservando o exagero. Não alteramos os prompts de produção nesta comparação.
A amostra pequena e as diferenças de engine impedem generalizar para qualquer uso dos modelos.

## Reproduzir a comparação

Snapshot local: `logs/bancada_modelos/suite.json`.
SHA256: `542b1a61ee0ec544e21e7e77fccf4141f741a88e3583418c7386068911df89e3`.

[Respostas completas do Bonsai](../logs/bancada_modelos/20260920-205057-bonsai-pq2.md)
e [JSON com métricas](../logs/bancada_modelos/20260920-205057-bonsai-pq2.json) ficam
localmente em `logs/`, ignorado pelo Git. O snapshot duplicado
`suite-bonsai-gemma.json` guarda a mesma entrada desta comparação.

[Respostas completas do Gemma](../logs/bancada_modelos/20260920-230239-gemma.md),
[JSON com métricas](../logs/bancada_modelos/20260920-230239-gemma.json),
[verificação de parâmetros](../logs/bancada_modelos/verificacao-gemma-20260920.json)
e [relatório conjunto](../logs/bancada_modelos/comparacao.md) também estão salvos.

Depois de carregar o Gemma no TurboLLM, mantendo contexto 8192 e thinking desligado:

```powershell
.\venv\Scripts\python.exe -X utf8 testes\bancada_modelos.py --rotulo gemma --esperado gemma --top-k 20
```

Não preparar outro snapshot entre as rodadas. O script recusa o modelo errado e
interrompe se GGUF, processo ou configuração mudarem durante a medição. Os resultados
novos terão outro nome com data/hora. Para juntar os relatórios:

```powershell
.\venv\Scripts\python.exe -X utf8 testes\bancada_modelos.py --comparar logs\bancada_modelos\20260920-205057-bonsai-pq2.json logs\bancada_modelos\20260920-230239-gemma.json
```

Validação da bancada: 10 testes Python e 38 arquivos de testes JavaScript passaram.
