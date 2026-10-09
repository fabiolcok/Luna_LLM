# Stheno v3.2 8B Q6_K — bancada da Luna

Concluída em **28/09/2026**, com **50 respostas medidas**: 28 na comparação geral,
12 no proativo atual de Dark Souls e 10 em uma conversa contínua exploratória.

**O Stheno ficou rápido, mas não mostrou a melhora de companhia que procurávamos
com os prompts avaliados.** Na conversa, lembrou um apelido e reconheceu uma
vitória relatada explicitamente. Porém, explicou brincadeiras, fez perguntas
genéricas e perdeu o acontecimento atual no proativo. Não recomendo substituir
o modelo atual da Luna por ele com base nesta rodada.

## Condições e interrupção

- GGUF confirmado em `/props`: `L3-8B-Stheno-v3.2-Q6_K.gguf`.
- TurboLLM 1.13.4, llama.cpp **b9608 ROCm**, contexto 8192, um slot, GPU RX 9060 XT.
- A primeira tentativa, em 27/09, salvou oito respostas e parou quando a engine
  deixou de estar disponível durante o cenário de filme. A causa da parada não
  foi determinada; isso não foi classificado como falha de qualidade do Stheno.
- Na retomada, o PID mudou de 8708 para 14392. Modelo, engine, contexto e padrões
  de amostragem foram conferidos iguais. O JSON final preserva as oito respostas,
  identifica o processo de cada resposta e acrescenta as vinte que faltavam.
  O arquivo incompleto original continua preservado.
- Aquecimentos ficaram fora do placar. Os 28 hashes dos pedidos foram conferidos
  contra o snapshot; não há duplicação de cenário/rodada.
- Nenhuma das 50 respostas registrou corte por limite de tokens, cache de prompt
  ou conteúdo de raciocínio separado. Thinking foi solicitado desligado.
- Foram usadas fixtures e chamadas isoladas: sem executar ferramentas, TTS,
  salvar conversa pessoal ou alterar prompts/configuração global da Luna.

## Comparação geral

Mesmo snapshot de 14 cenários, duas repetições, seeds 1932/1933. Persona usa
temperatura 0,8 e penalidades de presença/frequência 0,3; roteador usa os parâmetros
congelados de seu cenário. `top_k=20` foi aplicado apenas às requisições.

| Ramo | Checks Stheno | TTFT mediano | Total mediano |
|---|---:|---:|---:|
| PROMPT_COMPLETO | 4/10 | 3,25 s | 5,07 s |
| ENXUTO_COTIDIANO | 0/2 | 0,88 s | 1,99 s |
| ENXUTO_REFERENCIA_SEM_NOME | 1/2 | 0,53 s | 1,42 s |
| ENXUTO_PROATIVO | 4/6 | 1,30 s | 2,47 s |
| ROTEADOR | 4/8 | 0,63 s | 0,84 s |

**13/28 sem alertas não é nota de criatividade.** Há falsos negativos e problemas
que os checks não cobrem: a referência vaga foi admitida nas duas respostas,
mas uma não usou as expressões esperadas; já a abertura de Hollow Knight alterou
a data nas duas repetições e passou nos checks de uma delas.

| Medida | Stheno Q6_K | Llama 3.1 Q6_K | Gemma 3 Heretic Q4_K_M | Gemma 4 QAT |
|---|---:|---:|---:|---:|
| Geração mediana | 41,04 tok/s | 40,45 tok/s | 30,98 tok/s | 40,18 tok/s |
| Total mediano, prompt completo | 5,07 s | 4,68 s | 6,12 s | 4,98 s |
| Total mediano, proativo | 2,47 s | 2,18 s | 3,11 s | 3,08 s |
| Tag de clima válida na persona | 12/20 | 13/20 | 15/20 | 20/20 |
| Roteamento correto | 4/8 | 4/8 | 4/8 | 8/8 |

Os outros modelos não foram recarregados: são registros anteriores, de 20 e 27/09.
O Gemma 4 usou MTP; o Gemma 3 usou cache K/V Q8 e adaptação de histórico em quatro
chamadas. Templates, tokenizadores e quantizações também diferem. Esses números
comparam configurações concretas, não isolam arquitetura ou garantem desempenho
durante um jogo. Os tempos excluem ferramentas e voz.

### Leitura das respostas

- **Ferramentas:** acertou os quatro comentários que pediam `SEM_FERRAMENTA`.
  Nos dois pedidos explícitos de música também devolveu `SEM_FERRAMENTA`.
  Nas duas perguntas de gameplay respondeu em texto, sem chamada estruturada.
  A mediana curta do roteador não representa ações executadas mais depressa.
- **Humor:** no script de dez linhas, “catástrofe de produtividade” trouxe uma
  provocação ligada ao relato. Na notícia de 400 horas, porém, predominou uma
  reação genérica: “400h de jogo, hein? Isso é uma viagem, cara!”.
- **Dado alterado:** as três semanas desde a última sessão de Hollow Knight
  viraram “nem sequer uma semana” nas duas repetições.
- **Conhecimento e invenção:** respondeu 1968 para Três Homens em Conflito nas
  duas vezes; em uma, ainda o chamou de primeiro longa do gênero spaghetti western.
- **Placar sem acesso:** numa resposta admitiu não ter o placar, mas inventou
  disponibilidade de cinco partidas salvas; noutra afirmou estar vendo o jogo
  e informou 3x2 para o time do usuário.
- **Formato:** omitiu tags ou escreveu valores como `curiosidade` e `fest`,
  fora da lista da Luna. Também deixou uma instrução entre colchetes ao final
  da explicação sobre o placar.

## Dark Souls com o prompt atual

Duas sequências independentes de seis eventos: morte, morte, chefe, morte,
fogueira e morte. Mesmos eventos, seeds, instante fixo, fontes e amostragem
padrão do teste anterior do Llama (`top_k=40`). O primeiro pedido é idêntico;
depois os históricos divergem conforme as próprias falas de cada modelo.

As 12 respostas levaram **2,53–4,08 s**, mediana **2,99 s**; sete tiveram tag de
clima válida. Não numerou mortes ou tentativas e não ultrapassou o TTL antes do TTS.

- Na primeira sequência, repetiu “rei dos suicídios” e “missão secreta”, apesar
  da antirrepetição. Quando **Taurus Demon foi derrotado**, continuou comentando
  o quanto o usuário era profissional em morrer. A fogueira também virou morte.
- Na segunda, inventou um cemitério e manteve o assunto nas falas seguintes.
  Não reconheceu a vitória sobre Taurus Demon; ao receber a fogueira de Undead
  Parish, falou de cadáveres e acrescentou Sulyvahn, que não estava no contexto.

O defeito é perder o evento confirmado e repetir a mesma ideia. A presença de
hipérboles, por si só, não foi considerada um problema. O teste não mede o detector
em jogo, entrega de áudio, FPS ou engasgos.

## Conversa contínua: dez turnos

Experimento adicional, separado do placar acima, com o sistema completo e o
invólucro da mensagem do snapshot da Luna. Cada turno recebe o histórico das
respostas anteriores; as tags de clima são retiradas desse histórico.

Usei os valores sugeridos no [model card do autor](https://huggingface.co/Sao10K/L3-8B-Stheno-v3.2):
temperatura **1,17**, `min_p=0,075`, `top_k=50` e repetição **1,1**.
Presença/frequência ficaram em zero; `top_p` permaneceu no padrão 0,95 da engine.
São ajustes apenas por chamada. Este não é um A/B de amostragem: também mudaram
os cenários e a estrutura da conversa.

O diálogo começou com uma queda após ler um aviso, criou o apelido “Fiscal de
Escada”, relatou vitória sobre o Demônio Touro, fez uma piada de frigideira e mudou
para um sanduíche. No final, pediu recuperação do apelido e uma brincadeira com o aviso.

**Pontos positivos:**
- Recuperou corretamente “Fiscal de Escada” no nono turno.
- Reconheceu a vitória quando ela foi contada explicitamente no diálogo.
- Entendeu que trocar a espada por frigideira era brincadeira e que a espada continuava.

**Limitações observadas:**
- Explicou a piada em terceira pessoa: “O usuário mudou de armamento e brincou...”.
  Depois perguntou qual teria sido o propósito da brincadeira.
- Repetiu perguntas genéricas sobre planos e próximos objetivos.
- Mesmo depois da mudança para o lanche, voltou à “maratona no Dark Souls”
  sem que isso tivesse sido informado.
- No encerramento, recuperou o aviso e o apelido, mas a resposta continuou explicativa.

Mediana **5,87 s**, faixa **3,99–8,18 s**, máximo de 4605 tokens de entrada.
Duas respostas tiveram tag no formato e vocabulário exatos; uma terceira usou
`[clima: zoeira]`, com espaço. Este ensaio não valida memória persistente ou a
seleção automática dos diferentes modos da Luna.

## GPU e validação

Amostra pontual do processo 14392: **7,08 GiB de memória dedicada** e cerca de
121 MiB compartilhados. Não representa pico nem comparação controlada com os
outros modelos. A engine reconheceu a RX 9060 XT e carregou o backend HIP.

Os **39 arquivos de testes Node** e **13 testes Python da infraestrutura das
bancadas** passaram. Nenhum arquivo de produção foi alterado nesta rodada.

## Evidências e reprodução

- [Comparação geral completa](../logs/bancada_modelos/20260928-185838-stheno-v32-8b-q6-retomada.md)
  e [JSON com retomada e PID por resposta](../logs/bancada_modelos/20260928-185838-stheno-v32-8b-q6-retomada.json).
- [Dark Souls: respostas](../logs/dark_souls/stheno-v32-8b-20260928-190104.md)
  e [pedidos/tempos](../logs/dark_souls/stheno-v32-8b-20260928-190104.json).
- [Conversa de dez turnos](../logs/bancada_modelos/20260928-190158-stheno-conversa-autor.md)
  e [requisições completas](../logs/bancada_modelos/20260928-190158-stheno-conversa-autor.json).
- [Comparação com os modelos anteriores](../logs/bancada_modelos/comparacao-stheno-20260928.md).
- [Amostra de GPU](../logs/bancada_modelos/stheno-gpu-20260928.json).
- Tentativa parcial preservada: `logs/bancada_modelos/20260927-234621-stheno-v32-8b-q6.json`.

Snapshot: `logs/bancada_modelos/suite-bonsai-gemma.json`, SHA256
`542b1a61ee0ec544e21e7e77fccf4141f741a88e3583418c7386068911df89e3`.
Os arquivos em `logs/` são locais e ignorados pelo Git.

```powershell
.\venv\Scripts\python.exe -X utf8 -m testes.bancada_modelos --rotulo stheno-v32-8b-q6 --esperado L3-8B-Stheno-v3.2-Q6_K --suite logs/bancada_modelos/suite-bonsai-gemma.json --top-k 20
.\venv\Scripts\python.exe -X utf8 -m logs.bancada_modelos.avaliar_dark_souls_stheno
.\venv\Scripts\python.exe -X utf8 -m logs.bancada_modelos.avaliar_conversa_stheno
```
