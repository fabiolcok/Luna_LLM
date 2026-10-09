# Llama 3.1 8B Q6_K — bancada da Luna

Rodada de **27/09/2026**. Foram **40 chamadas medidas**: 28 nos mesmos cenários
congelados usados com Gemma/Bonsai e 12 no proativo atual do Dark Souls.
Minha leitura: **não substitui o Gemma nesta configuração da Luna**. O Llama
respondeu sem erro de API, mas acionou ferramentas em comentários sem pedido,
omitiu tags de emoção e misturou acontecimentos do jogo. Não mostrou ganho de naturalidade.

## Modelo e condições

- Confirmado em `/props`: `Meta-Llama-3.1-8B-Instruct-Q6_K.gguf`.
- TurboLLM 1.13.4, llama.cpp b9608 ROCm, contexto 8192, um slot.
- Thinking desligado; nenhum texto de raciocínio, truncamento ou token de cache
  registrado nas 40 chamadas. O aquecimento da comparação ficou fora do placar.
- Os 14 cenários congelados foram repetidos duas vezes, com as mesmas mensagens,
  ferramentas, seeds e `top_k=20` usados na comparação anterior. O padrão do Llama
  permanece 40; o ajuste para 20 valeu apenas nessas requisições.
- O teste de Dark Souls usa o prompt atual, a antirrepetição da produção e o
  padrão de amostragem do Llama (`top_k=40`). São duas sequências independentes
  de quatro mortes, um chefe e uma fogueira, com teto de 180 tokens.
- Nenhuma ferramenta foi executada. Não houve voz, conversa salva, alteração de
  prompt de produção ou troca do modelo selecionado.

## Comparação com os registros do Gemma

O Gemma foi medido em **20/09**, não novamente nesta rodada. As entradas abaixo
são idênticas, mas os tempos comparam execuções em datas diferentes e modelos com
templates/tokenizadores diferentes. O Gemma usou geração especulativa MTP; o Llama
não registrou tokens draft. Não é uma medição isolada da arquitetura dos modelos.

| Ramo | Checks Llama | Checks Gemma | Total mediano Llama | Total mediano Gemma |
|---|---:|---:|---:|---:|
| PROMPT_COMPLETO | 7/10 | 8/10 | 4,68 s | 4,98 s |
| ENXUTO_COTIDIANO | 1/2 | 2/2 | 1,60 s | 1,94 s |
| ENXUTO_REFERENCIA_SEM_NOME | 2/2 | 2/2 | 1,31 s | 0,91 s |
| ENXUTO_PROATIVO | 2/6 | 3/6 | 2,18 s | 3,08 s |
| ROTEADOR | 4/8 | 8/8 | 6,53 s | 3,60 s |

**Checks não são notas de criatividade.** O Llama ficou em 16/28 sem alertas;
o Gemma em 23/28, com ressalvas dos checks antigos já registradas em
[resultado_modelos.md](resultado_modelos.md). A tag de clima válida apareceu em
13/20 respostas de persona do Llama, contra 20/20 do Gemma.

A geração mediana foi 40,45 tokens/s no Llama e 40,18 no Gemma. O Llama produziu
algumas falas mais curtas, mas a primeira saída no prompt completo demorou
3,34 s, contra 2,58 s no Gemma. No roteador foram 5,44 s contra 3,33 s.
Os tempos são por chamada, sem ferramentas, TTS ou o turno completo da Luna.

## Leitura manual

- **Roteador:** nas duas repetições de “Hoje foi puxado”, pediu `controlar_spotify`
  recuperando “Toca uma música” do histórico. Nas duas de “Voltei da partida, que
  surra”, pediu `duvida_do_jogo` apesar de não haver pergunta. Acertou as quatro
  chamadas de pedidos explícitos de música/gameplay, com argumentos válidos.
- **Personalidade:** para o domingo tentando fazer dez linhas de código funcionar,
  respondeu “Você deve ter ficado bem cansado depois disso”. Passou no check, mas
  trouxe pouca personalidade. Também repetiu a pergunta do usuário e devolveu
  perguntas genéricas em cenários de opinião e gosto próprio.
- **Premissa inventada:** na abertura de Hollow Knight, com apenas 42 horas e data
  da última sessão, escreveu “Você ainda está perseguindo aquele Silur o tempo todo,
  né? 42 horas jogadas e ainda não conseguiu derrotá-lo...”. O briefing não dizia
  inimigo atual nem que o jogo estava incompleto. Na outra repetição reduziu
  42 para “quase 40” e também supôs que o jogo não havia sido terminado.
- **Formato:** quatro das seis falas proativas ficaram sem tag de clima válida.
  No cenário de gosto próprio apareceu `[clima:fest]`, fora da lista prevista.
- **Pontos positivos:** admitiu a referência vaga sem inventar o nome do jogo,
  não inventou o placar de Overwatch e respondeu 1966 ao filme nas duas rodadas.
  Na notícia de 400 horas, a comparação com assistir à TV Globo foi um exagero
  compreensível ligado à notícia; o exagero em si não é o problema.

## Dark Souls com o prompt atual

As 12 chamadas produziram texto em **2,20–3,74 s**, mediana **2,95 s**, sem
numerar mortes ou tentativas. Sete retornaram uma tag de clima válida.

Na primeira sequência, a imagem de crateras e buracos se repetiu apesar da
antirrepetição. Ao receber **Taurus Demon derrotado**, continuou falando de buracos
e de um sistema de esgoto em Anor Londo, sem reconhecer a vitória.

Na segunda, um evento de morte virou “a fogueira de Anor Londo está livre agora”.
Depois de citar corretamente Taurus Demon derrotado, voltou a comemorar chefe e
fogueira em um evento de morte. O evento real de fogueira era **Undead Parish**;
mesmo assim, continuou mencionando Anor Londo. Uma fala deixou `Clima:festal` no texto.

O piloto detectou os tipos corretos na fixture. O problema observado foi a resposta
do modelo: falas anteriores ganharam peso sobre o acontecimento atual. Não contei
a metáfora de uma cratera, sozinha, como erro factual; misturar vitória/fogueira/morte
e afirmar locais não fornecidos são problemas distintos do humor exagerado.

Não houve teste dentro do jogo nem medição de FPS ou entrega de voz. A amostra
serve para avaliar este modelo com os prompts atuais, sem ajustes específicos para ele.

## Evidência e reprodução

- [Respostas e métricas da comparação](../logs/bancada_modelos/20260927-132140-llama31-8b-q6.json).
- [Respostas completas do Llama](../logs/bancada_modelos/20260927-132140-llama31-8b-q6.md).
- [Comparativo com Gemma](../logs/bancada_modelos/comparacao-gemma-llama31-20260927.md).
- [Falas de Dark Souls](../logs/dark_souls/llama31-8b-20260927-132412.md) e
  [pedidos completos](../logs/dark_souls/llama31-8b-20260927-132412.json).

Os registros em `logs/` ficam apenas localmente, ignorados pelo Git.
Snapshot de comparação: `logs/bancada_modelos/suite-bonsai-gemma.json`, SHA256
`542b1a61ee0ec544e21e7e77fccf4141f741a88e3583418c7386068911df89e3`.

```powershell
.\venv\Scripts\python.exe -X utf8 -m testes.bancada_modelos --rotulo llama31-8b-q6 --esperado Meta-Llama-3.1-8B-Instruct-Q6_K --suite logs/bancada_modelos/suite-bonsai-gemma.json --top-k 20
```

Verificação da infraestrutura: 13 testes Python da bancada e 39 arquivos de
testes Node passaram. Nenhum código de produção foi modificado nesta rodada.
