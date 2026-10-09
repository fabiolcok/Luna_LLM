# Gemma 3 12B Heretic Thinking — bancada da Luna

Rodada concluída em **27/09/2026**, após retomar o trabalho interrompido pela queda
de energia. Foram **40 respostas medidas na rodada final**: 28 na comparação geral
e 12 no proativo atual de Dark Souls. As quatro respostas anteriores à queda
ficaram preservadas e não entram neste placar.

**Não houve ganho convincente de criatividade ou coerência sobre o registro do
Gemma 4.** Algumas falas ficaram mais coloquiais, mas o modelo acrescentou fatos
inexistentes e perdeu o acontecimento atual. A geração também foi mais lenta.
Esta conclusão vale para a versão modificada carregada, não para todo Gemma 3.

## Identificação e condições

Arquivo confirmado em `/props`:
`gemma-3-12b-it-vl-GPT-5.1-High-Heretic-Uncensored-Thinking.i1-Q4_K_M.gguf`.

É uma versão de [DavidAU](https://huggingface.co/DavidAU/gemma-3-12b-it-vl-GPT-5.1-High-Heretic-Uncensored-Thinking),
quantizada por [mradermacher](https://huggingface.co/mradermacher/gemma-3-12b-it-vl-GPT-5.1-High-Heretic-Uncensored-Thinking-i1-GGUF),
com treinamento adicional sobre uma variante Heretic. Não é o checkpoint oficial
Gemma 3 12B IT sem modificações.

- TurboLLM 1.13.4, llama.cpp b9608 ROCm, contexto 8192, um slot.
- Depois da reinicialização, o comando passou a incluir K/V `q8_0`. Por isso,
  foi iniciada uma rodada nova; a tentativa interrompida não foi misturada.
- Thinking solicitado como desligado; nenhum texto de raciocínio separado,
  truncamento ou token de cache registrado nas 40 respostas finais.
- Comparação geral: mesmo snapshot de 14 cenários, duas repetições, seeds 1932/1933
  e `top_k=20`. Aquecimento excluído do placar.
- Dark Souls: mesmos eventos, seeds e data/hora dos testes de Llama e Lexi,
  com `top_k=40` enviado por chamada. O padrão global do Gemma 3 permanece 64.
- Nenhuma ferramenta foi executada, voz emitida ou conversa pessoal salva.
  Não houve alteração de prompts ou de configurações de produção.

### Compatibilidade de histórico

O template recusou mensagens que não alternam usuário/assistente, com HTTP 400.
A bancada direta parou no cenário de referência vaga antes da queda de energia.

Na rodada final foi usada a adaptação já existente na Luna
(`adaptar_mensagens_alternadas`), apenas após o erro específico. Quatro chamadas
precisaram dela: referência vaga e desabafo com pedido antigo, nas duas rodadas.
As quatro responderam após a adaptação. Erro original e pedido adaptado estão no
JSON; os tempos dessas chamadas incluem a tentativa rejeitada.

Assim, o snapshot-base é o mesmo, mas essas quatro requisições efetivas têm
histórico formatado de maneira diferente. Isso limita a comparação estrita entre
modelos e representa o tratamento que o código atual da Luna já oferece.

## Chat, formato e tempo

| Medida | Gemma 3 Heretic Q4_K_M / KV Q8 | Gemma 4 12B QAT, registro de 20/09 |
|---|---:|---:|
| Geração mediana | 30,98 tokens/s | 40,18 tokens/s |
| Tempo mediano, prompt completo | 6,12 s | 4,98 s |
| Primeira saída, prompt completo | 2,90 s | 2,58 s |
| Tempo mediano, proativo | 3,11 s | 3,08 s |
| Tag de clima válida nas falas | 15/20 | 20/20 |
| Roteamento correto | 4/8 | 8/8 |

O Gemma 4 não foi recarregado nesta rodada. Ele usou geração especulativa MTP,
enquanto o Gemma 3 não registrou tokens draft; o cache K/V e as quantizações também
diferem. Os tempos comparam essas configurações concretas, não isolam a arquitetura.
São chamadas separadas, sem TTS, ferramentas, FPS ou duração do turno completo.

No roteador, o Gemma 3 levou mediana de 0,97 s, mas **não executou corretamente os
pedidos explícitos**: música virou `SEM_FERRAMENTA`; gameplay saiu como texto
`duvida_do_jogo`, sem chamada estruturada. Os quatro acertos foram os comentários
que realmente não pediam ferramenta. Portanto, a baixa latência não representa
melhora de execução de ações.

### Leitura manual das falas

- **Placar inventado:** a fixture só informava janela e jogo, mas ele afirmou
  “O placar atual de Overwatch é 4 a 1 para a equipe inimiga”. Na segunda rodada
  admitiu não ter acesso ao placar.
- **Número alterado:** a notícia fornecia 400 horas de conteúdo; uma resposta
  transformou isso em “Quase 500 horas pra zerar o jogo”.
- **Conta incoerente:** para dez horas de Overwatch, propôs trinta partidas de
  vinte minutos e concluiu “mais de doze horas”.
- **Conversa:** houve respostas compreensíveis e coloquiais sobre a utilidade
  de abrir programas. No cenário do script, porém, predominou a oferta de ajuda
  técnica e consolo; isso não demonstrou mais humor ou presença.
- **Formato:** retornou `[clima:curiosa]`, fora da lista, omitiu outras tags e
  usou emojis em falas destinadas à voz.
- **Pontos positivos:** respondeu 1966 nas duas perguntas sobre o filme e admitiu
  que a referência vaga não tinha nome conhecido. Uma fala sobre Hollow Knight
  usou corretamente 42 horas e três semanas.

Os checks automáticos ficaram em **9/28 sem alertas**, segmentados:
prompt completo 3/10; cotidiano 0/2; referência vaga 0/2; proativo 2/6; roteador 4/8.
Isso não é nota de qualidade: a referência vaga foi semanticamente admitida nas
duas vezes, mas esbarrou em expressões exigidas/proibidas. Por outro lado, o placar
“4 a 1” passou porque o check antigo só barrava alguns exemplos de placar.
A conclusão considera a leitura das respostas, não apenas essa contagem.

## Dark Souls

Doze falas em **3,06–4,66 s**, mediana **3,47 s**. Dez retornaram tag de clima
válida. Não numerou mortes ou tentativas.

Na primeira sequência, reconheceu mortes, a derrota de Taurus Demon e a fogueira
de Undead Parish. Ainda acrescentou narrativas e propriedades não fornecidas,
como um suposto “modo fantasma” que deixaria a personagem mais resistente.

Na segunda, começou a presumir que o personagem já estava na fogueira. Quando o
evento foi **Taurus Demon derrotado**, respondeu “Que beleza ter chegado à fogueira
do Taurus Demon!”. Depois, mortes continuaram rendendo comentários de chegada à
fogueira e marcações no mapa, que não constavam dos dados.

Houve menos repetição literal de uma única metáfora do que nos testes dos Llama,
mas a distinção entre os acontecimentos ainda falhou. O exagero de “virou
churrasquinho” não é tratado como defeito por si só; trocar o evento confirmado e
afirmar fatos não observados é outro problema.

## Memória de GPU observada

Uma leitura do contador Windows `GPUProcessMemory.DedicatedUsage` do processo
9184, durante a rodada após a reinicialização, registrou **8.266.719.232 bytes =
7,70 GiB dedicados**, além de aproximadamente **112 MiB compartilhados**.

Antes da queda, uma amostra do processo 9248 indicou 8,15 GiB dedicados. O comando
anterior não explicitava o tipo do cache K/V; o atual usa Q8. São duas amostras
pontuais em condições diferentes, não máximos nem comparação controlada.

Não há medição equivalente do Gemma 4 nesta sessão. Portanto, não foi demonstrado
quanto este modelo economiza em relação a ele, nem se reduz quedas durante o jogo.

## Sobre “mais parâmetros de texto”

O [relatório técnico do Gemma 3](https://storage.googleapis.com/deepmind-media/gemma/Gemma3Report.pdf)
separa, no 12B, 1.012 milhões de parâmetros de embeddings, 10.759 milhões fora dos
embeddings e 417 milhões no encoder visual. O componente de linguagem soma
aproximadamente **11,77 bilhões**, com o encoder visual separado.

O [model card oficial do Gemma 4](https://ai.google.dev/gemma/docs/core/model_card_4)
descreve o 12B como **Unified**, com 11,95 bilhões de parâmetros e sem encoders
dedicados de visão/áudio: entradas multimodais passam por projeções leves para
um transformer compartilhado.

Minha interpretação desses dados: não dá para concluir que o Gemma 3 reserva mais
capacidade para texto simplesmente porque o Gemma 4 também aceita imagem e áudio.
Tampouco a contagem, sozinha, prevê criatividade. Este teste ainda mistura
treinamento adicional, quantização, template e cache, então não isola “Gemma 3
oficial versus Gemma 4 oficial”.

## Evidências locais

- [Respostas gerais](../logs/bancada_modelos/20260927-225656-gemma3-heretic-q4km-kvq8.md)
  e [métricas/retries](../logs/bancada_modelos/20260927-225656-gemma3-heretic-q4km-kvq8.json).
- [Comparação com o Gemma 4](../logs/bancada_modelos/comparacao-gemma4-gemma3-heretic-20260927.md).
- [Falas de Dark Souls](../logs/dark_souls/gemma3-heretic-kvq8-20260927-225912.md)
  e [requisições completas](../logs/dark_souls/gemma3-heretic-kvq8-20260927-225912.json).
- [Amostra de GPU com KV Q8](../logs/bancada_modelos/gemma3-heretic-gpu-kvq8-20260927.json).
- Tentativa anterior preservada: `logs/bancada_modelos/20260927-223422-gemma3-12b-heretic-q4km.json`.

Arquivos de logs são locais e ignorados pelo Git. Os 39 arquivos de testes Node
passaram antes da interrupção; os arquivos de produção usados na bancada não mudaram.
