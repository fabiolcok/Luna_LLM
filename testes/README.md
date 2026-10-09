# Testes da presença

```bash
node testes/rodar.js
```

Sem dependência. Só Node. ~2 segundos.

Para validar também o backend Python antes de fechar uma mudança maior:

```bash
node testes/rodar_tudo.js
```

Esse segundo comando roda primeiro a suíte rápida acima e depois todos os `testa_*.py` como
módulos. Ele procura o Python do `venv` e tem fallback para o launcher do sistema. As bancadas
que usam modelo real ficam de fora de propósito.

Regressão do radar RSS após interrupção de fala (sem rede, voz ou LLM):

```powershell
.\venv\Scripts\python.exe -X utf8 -m unittest testes.testa_radar_interrupcao testes.testa_execucoes
```

Cobre interrupção antes da apresentação, durante a síntese e durante o áudio,
preservação do intervalo e ausência de repetição ou duplicação da nota.

## Por que existem

O `templates/Index.html` tem ~4100 linhas com CSS, HTML e todo o JS da interface num arquivo só.
O erro mais comum ali — usar `let`/`const` antes da declaração — **derruba o script inteiro** e
a página abre em branco, sem mensagem nenhuma. `node --check` não vê: a sintaxe é válida.

Estes testes **extraem o `<script>` do HTML na hora e executam** com um DOM falso. Foi assim que
apareceram, entre outros: quatro quebras de zona morta, o cometão pulando pra origem do viewBox,
`classList.remove` variádico, config morta em três tabelas, e um `<svg>` sendo destruído sem
reconstrução.

## O que cada um cobre

| arquivo | assunto |
|---|---|
| `checa.js` | carga: o script roda até o fim sem `ReferenceError` |
| `testa_rosto.js` | as caras, a curadoria dos climas e quem pisca |
| `testa_eixos.js` | estado / atividade / emoção não se combinam no CSS |
| `testa_ritmo.js` | as histórias não se amontoam (espaçamento e teto) |
| `testa_sujeira.js` | fuligem: nasce, esfrega, some |
| `testa_medo.js` | chuva de asteroides: atrapalhar estica, com teto e período frio |
| `testa_invasao.js` | invasão: a frota ronda, fecha o cerco, debanda |
| `testa_desistir.js` | 3 histórias por tempo demais → vira de costas |
| `testa_cometao.js` | a martelada nunca perde a posição do cometão |
| `testa_prompt_montagem.py` | o prompt de sistema de cada ramo, byte a byte contra um golden |

## Escrevendo um teste novo

Copie o mais parecido e ajuste. O padrão é:

1. ler o `Index.html`, extrair o `<script>`
2. montar `global.document` e companhia com um DOM falso
3. `new Function(src + ';globalThis.__t = { ...o que você quer testar... }')()`
4. asserções com `diz(condição, 'frase que explica o que tem que valer')`

**Prefira asserção que descreve a regra, não o número.** `alt('T_T') < alt('ᵔ ᵕ ᵔ')` continua
valendo depois que alguém afinar os valores; `alt('T_T') === -0.22` vira manutenção.

Cada arquivo carrega o próprio DOM falso, e eles não são iguais — cada um precisa de uma
fidelidade diferente. Isso é proposital: já custou falha falsa três vezes o duble ser mais
pobre que o DOM de verdade (`classList` não-variádico, `className` fora de sincronia com
`classList`, `querySelector` inventando elemento em vez de devolver `null`).

## Vendo qual prompt montou uma fala

Cada turno imprime uma linha no terminal:

```
[🧩 Prompt: ENXUTO_COTIDIANO + sem humor · voz · 1959c≈489tok]
[🧩 Prompt: ENXUTO_PROATIVO + EMOCAO · texto · 4147c≈1036tok]
[🧩 Prompt: PROMPT_COMPLETO + EMOCAO · texto · 10536c≈2634tok · memória 1351c]
```

Sai no terminal e no `logs/luna.log`. Três informações, cada uma para uma pergunta:

- **o caminho** — `sem humor` significa que aquele turno caiu num modo enxuto que não recebe o
  bloco `EMOCAO`; aí mexer no `HUMOR E ACIDEZ` não vai adiantar nada, o problema é de arquitetura.
- **o tamanho** — para ver na hora se o prompt inchou, e quanto disso é MEMÓRIA (perfil,
  recentes, relacionada e ChromaDB), que é a parte que cresce sozinha. O detalhe bloco a
  bloco sai no `[📏]`, que só liga com `LUNA_DIAG_PROMPT=1` ou o arquivo
  `modelos/diag_prompt.flag` — é o que serve pra decidir o que cortar.
O modelo não entra na linha — ele já sai no boot e na troca. Mas fique de olho nele por outro
motivo: o seletor do painel só grava a escolha quando a troca dá certo. Se o TurboLLM não
carregar, o `config_luna.json` mantém o modelo anterior e a Luna sobe com ele no próximo
restart, sem avisar. Já custou uma sessão inteira de teste.

Serve para uma pergunta específica: quando ela sai mansa, foi o **caminho** ou o **modelo**?
`sem humor` significa que aquele turno caiu num modo enxuto que não recebe o bloco `EMOCAO` — aí
o problema é de arquitetura, não de prompt, e mexer no `HUMOR E ACIDEZ` não vai adiantar nada.

## Mexendo nos prompts

O texto dos prompts mora em `modulos/prompts.py`, separado por eixo. Toda mudança ali passa pelo
`testa_prompt_montagem.py`, que monta o prompt de 22 ramos diferentes (cada canal, cada modo
enxuto) e compara **byte a byte** com `prompt_golden.txt`.

- **Refatorou sem querer mudar nada?** O teste tem que passar sem tocar no golden. Se ele acusar,
  a refatoração não foi neutra.
- **Mudou o prompt de propósito?** Regrave o golden e leia o `git diff` dele — é ali que se vê
  o que realmente entrou e saiu:

```bash
.\venv\Scripts\python.exe -X utf8 -m testes.testa_prompt_montagem --atualizar
```

Ele não sobe modelo: o cliente é substituído por um dublê que só grava as mensagens. Comportamento
continua sendo assunto da bancada abaixo — este teste prova apenas que o TEXTO não mudou.

## Compatibilidade de histórico com Mistral NeMo

```powershell
.\venv\Scripts\python.exe -X utf8 -m unittest testes.testa_chat_alternado testes.testa_execucoes testes.testa_turbollm_recuperacao
```

Cobre proativos no início do recorte, mensagens consecutivas do mesmo autor,
preservação do histórico original e das ferramentas, retentativa limitada ao erro
400 de alternância e prioridade da conversa. Conteúdo multimodal e tool calls não
são convertidos em texto. Modelos que aceitam o histórico recebem o pedido original.
Validação com modelo real: [Mistral NeMo RPMax, 26/09](resultado_compat_mistral.md).

## Bancada da persona (modelo real)

### Comparar modelos no TurboLLM

`bancada_modelos.py` captura 14 chamadas reais: conversa, continuidade, limites do contexto
atual, proativo e roteador. As fontes pessoais são substituídas por fixtures. Ferramentas
são apenas propostas pelo modelo; nenhuma é executada. Não inicia a Luna nem grava conversas.

Prepare **uma vez**. O snapshot congela mensagens, ferramentas, parâmetros e checks para os
dois modelos, inclusive data/hora. Não altere `suite.json` entre as rodadas:

```powershell
.\venv\Scripts\python.exe -X utf8 testes\bancada_modelos.py --preparar
.\venv\Scripts\python.exe -X utf8 testes\bancada_modelos.py --rotulo bonsai-pq2 --esperado PQ2_0
```

Depois de trocar e carregar o Gemma manualmente no TurboLLM:

```powershell
.\venv\Scripts\python.exe -X utf8 testes\bancada_modelos.py --rotulo gemma --esperado gemma --top-k 20
```

O script verifica o caminho GGUF real em `/props` antes/depois de cada chamada; os nomes da
biblioteca podem ser iguais para quantizações diferentes. Ele não carrega nem troca modelos.
Por padrão são duas repetições, thinking desligado, seed base 1931 e cache de prompt desativado
por chamada. O aquecimento fica fora do placar. TTFT conta a primeira saída visível ou tool call;
tokens/tempos retornados pelo engine ficam no JSON. Contexto, engine e padrões de amostragem
também ficam registrados; engines/templates/tokenizadores diferentes impedem tratar tokens/s
como comparação pura de capacidade do modelo. As duas chamadas de um turno e TTS não são medidos
em conjunto: esta bancada mede componentes separados.

`--top-k 20` iguala esse parâmetro ao Bonsai desta comparação, cujo engine usou 20 por padrão;
o engine do Gemma estava em 64. O ajuste é registrado no resultado e vale somente para as
requisições da bancada. O snapshot e a configuração global do TurboLLM permanecem intactos.

Resultados JSON e relatórios completos ficam em `logs/bancada_modelos/` (ignorados pelo Git).
Para juntar as duas execuções, substitua os caminhos pelos JSON de resultado:

```powershell
.\venv\Scripts\python.exe -X utf8 testes\bancada_modelos.py --comparar logs\bancada_modelos\<bonsai>.json logs\bancada_modelos\<gemma>.json
```

Os checks cobrem contratos, palavras, dados esperados e schema dos argumentos. **Leia também
as falas**: exagero teatral é desejado; premissa inventada, piada sem ligação e tom de narradora
precisam de avaliação humana. O relatório separa `PROMPT_COMPLETO`, cada enxuto e `ROTEADOR`.
Passar nesses checks não significa ser engraçada ou estar pronta para substituir o Gemma.

Rodada do [Llama 3.1 8B Q6_K, em 27/09/2026](resultado_llama31_8b.md): comparação
com os registros do Gemma e teste separado do proativo atual do Dark Souls.
Na mesma data, o [Lexi Uncensored V2 Q6_K_L](resultado_lexi_v2.md) passou pelos
mesmos cenários, com comparação separada do Llama original.
A rodada do [Gemma 3 Heretic Thinking Q4_K_M](resultado_gemma3_heretic.md) inclui
compatibilidade de histórico, medição de GPU e retomada após queda de energia.

A rodada do [Stheno v3.2 8B Q6_K](resultado_stheno_v32.md), concluída em 28/09/2026,
traz comparação geral, Dark Souls e uma conversa exploratória de dez turnos.

A rodada do [Hermes 4 14B Q4_K_M](resultado_hermes4_14b.md), em 28/09/2026,

Piloto qualitativo: [Codex interpretando a Luna, sem inferencia isolada](resultado_piloto_codex.md).

A/B no Gemma: [avaliar 16 pares do proativo](resultado_reacao_proativa.md).
A variante de reação simples foi ativada apenas nos eventos do Dark Souls após a avaliação.
A bancada continua comparando o proativo original com essa variante, sem mudar a configuração.

```powershell
.\venv\Scripts\python.exe -X utf8 -m testes.bancada_reacao_proativa preparar --pasta logs/bancada_modelos/reacao-ab-nova
.\venv\Scripts\python.exe -X utf8 -m testes.bancada_reacao_proativa executar --pasta logs/bancada_modelos/reacao-ab-nova
```

O preparo nao chama o modelo. A execucao exige Gemma 4 12B QAT Q4_0 carregado;
confere modelo, PID e configuracao antes/depois de cada geracao. Grava cada resposta
imediatamente, nao retoma nem sobrescreve rodadas existentes. Os dados completos
e a chave X/Y ficam na pasta escolhida. Use uma pasta nova em cada rodada.
repete esses três testes e documenta uma cópia literal do histórico de antirrepetição.

### Executar a bancada original

```bash
.\venv\Scripts\python.exe -X utf8 testes\bancada_persona.py --repeticoes 3 --rotulo nome-do-experimento
```

Não sobe a Luna, voz, web ou Telegram, mas usa o TurboLLM e o modelo configurado. A bancada chama
a mesma função de persona da aplicação com perfil, memória, ChromaDB e estado do PC substituídos
por cenários controlados. As memórias irrelevantes são intencionais: medem se a Luna força conexão
pessoal. Checks objetivos rodam automaticamente; as respostas completas ficam em
`logs/bancada_persona.jsonl` (ignorado pelo Git) para comparar versões.

**Leia o placar certo.** Metade dos cenários (14 de 27) cai num `modo_enxuto`, que substitui o
prompt inteiro — a persona não entra neles. Por isso o resumo sai em dois números: mexeu na
persona, olhe só o primeiro. Já aconteceu de o total cair 2 pontos numa mudança cujo efeito real
foi zero, com a queda toda vinda de cenários cujo prompt não tinha mudado um byte.

## Mexendo num prompt: qual rede usar

| a pergunta | quem responde |
|---|---|
| o texto do prompt mudou? | `testa_prompt_montagem.py` (byte a byte, sem modelo) |
| a regra ainda existe em algum lugar? | `testa_persona_guardrails.py` (grupos de sinônimos) |
| ela responde melhor ou pior? | `bancada_persona.py` (modelo real, 3 rodadas) |

## Medindo uma mudança de prompt sozinho

Quatro passos. O único que exige atenção é o primeiro: **rode a baseline ANTES de editar**, senão
não há com o que comparar.

```bash
# 0. quais cenários a sua mudança toca? (não usa modelo, é instantâneo)
.\venv\Scripts\python.exe -X utf8 testes\comparar.py --caminhos

# 1. baseline, só nos cenários daquela linha
.\venv\Scripts\python.exe -X utf8 testes\bancada_persona.py -r 3 --rotulo antes --cenario a,b,c

# 2. edite o prompt

# 3. de novo, outro rótulo
.\venv\Scripts\python.exe -X utf8 testes\bancada_persona.py -r 3 --rotulo depois --cenario a,b,c

# 4. compare
.\venv\Scripts\python.exe -X utf8 testes\comparar.py antes depois
```

`comparar.py` sem argumento lista os rótulos que já existem no log, com o placar de cada um.

**O passo 0 é o que economiza tempo.** Mexeu no `EMOCAO`? Só os cenários de `PROMPT_COMPLETO`
sentem — rodar os 40 é desperdício, e os outros 21 só vão adicionar ruído ao seu placar.

**Três armadilhas que já custaram caro aqui:**

1. **O total engana.** O ruído é de ~6 pontos em 102. Uma vez o placar "caiu" de 97 para 91 e a
   regressão era zero: as 6 falhas estavam todas em cenários cujo prompt não tinha mudado um byte.
2. **Cortar não é só encolher.** Tirar os jogos favoritos do `IDENTIDADE` derrubou o
   `gosto_proprio` de 3/3 para 1/3 — e não por citar menos: ela passou a se esquivar com "não
   tenho um gosto pessoal". Meça antes de assumir que um trecho é enfeite.
3. **A bancada só pega o que tem cenário.** O vazamento da saudação existia há meses e passava
   batido porque o cenário de saudação não tinha histórico. Se o bug que você viu no uso real não
   reprova na bancada, o cenário está incompleto — conserte o cenário primeiro.

## Bancada dos acompanhamentos (modelo real)

```bash
.\venv\Scripts\python.exe -X utf8 testes\bancada_acompanhamentos.py
```

Confere se o roteador oferece acompanhamento para um desfecho concreto sem confundir agenda,
lembrete e conversa cotidiana. As ferramentas são substituídas por versões locais: não cria evento,
nota ou acompanhamento real e não sobe voz, web ou Telegram.

## Avaliações V2 e continuidade

O contexto transitório tem testes próprios:

```powershell
.\venv\Scripts\python.exe -X utf8 -m unittest testes.testa_momento
.\venv\Scripts\python.exe -X utf8 testes\bancada_momento.py --rotulo local --roteador
```

Os testes isolados conferem expiração, fechamento de jogo, erro da Steam, isolamento do
Telegram, limite do bloco e snapshot por execução. A bancada usa sinais simulados com o
modelo real; mesmo com `--roteador`, não executa ferramentas. Resultados de referência e
limites em `testes/resultado_momento.md`. Para reavaliar os checks sem gerar respostas novas,
use `--rotulo <rotulo-do-log> --reavaliar`.

O teste Web `testa_stream_web.js` aceita parâmetros adicionais depois do callback opcional;
o contrato de streaming continua sendo verificado. `testa_validacao_horas.py` recebe o
coordenador no dublê e confere o motivo do descarte, para não passar por uma exceção acidental.

```powershell
.\venv\Scripts\python.exe -X utf8 -m unittest testes.testa_avaliacoes
.\venv\Scripts\python.exe -X utf8 testes\resumo_avaliacoes.py
.\venv\Scripts\python.exe -X utf8 testes\bancada_continuidade.py --comparar --repeticoes 2
```

O teste isolado verifica alvo por ID, contexto por execução, revisões, compatibilidade com
registros antigos e expiração. `testa_avaliacoes.js`, incluído em `rodar.js`, executa o painel
Web e simula uma fala nova enquanto o motivo está sendo escrito, a seleção múltipla e a troca
entre motivos positivos e negativos. O teste Python também confere se todos os motivos
oferecidos pela interface são aceitos e salvos.

O relatório lê `logs/avaliacoes.jsonl` sem modificar o arquivo. Em V2, `avaliacao_id` agrupa
revisões do mesmo voto; contar linhas como votos duplicaria os complementos. Categorias são
múltiplas e não somam necessariamente o total. Os registros V1 não tinham identidade suficiente
para uma consolidação segura, então permanecem separados.

A bancada usa o modelo real, substitui fontes pessoais e não inicia Web, voz ou Telegram.
Seus casos são **reconstruções** inspiradas em duas avaliações antigas (filme confundido e
notícia misturada com conversa anterior), que não guardavam histórico suficiente para replay.
`--comparar` experimenta um lembrete de referência e a retirada de contexto alheio só nessa
execução; isso não modifica o comportamento da Luna. O placar separa prompt completo e enxuto.
Leia as respostas em `logs/bancada_continuidade.jsonl`: os checks conferem referência, não humor.

## Piloto Dark Souls Remastered

`testa_dark_souls.py` cobre referência inicial, mortes, chefes, fogueiras, troca de
personagem/NG, recarga de save, leituras transitórias, expiração, prioridade e cancelamento.
Não acessa o jogo, voz ou modelo.

```powershell
.\venv\Scripts\python.exe -X utf8 -m unittest testes.testa_dark_souls testes.testa_momento testes.testa_execucoes
.\venv\Scripts\python.exe -X utf8 -m testes.bancada_dark_souls --preparar
.\venv\Scripts\python.exe -X utf8 -m testes.bancada_dark_souls
```

A bancada usa três cenários sintéticos no ramo `ENXUTO_DARK_SOULS + EMOCAO`.
`--preparar` só captura os prompts; sem a opção, requer modelo já carregado no
TurboLLM. Não troca modelo, não emite áudio e não inicia a Luna. Leia as falas
para avaliar grounding e humor. [Guia e diagnóstico do coletor](../integracoes/dark_souls/README.md).

Para comparar thinking em uma sequência de mortes:

```powershell
.\venv\Scripts\python.exe -X utf8 -m unittest testes.testa_bancada_dark_souls_thinking
.\venv\Scripts\python.exe -X utf8 -m testes.bancada_dark_souls_thinking --preparar --mortes 2
.\venv\Scripts\python.exe -X utf8 -m testes.bancada_dark_souls_thinking --mortes 8
```

A comparação requer o Gemma 4 12B já carregado. Alterna a ordem ligado/desligado
entre eventos, mantém o mesmo seed por par e usa a montagem de prompt, limpeza de
voz e antirrepetição da produção. Cada sequência recebe suas próprias últimas falas
(três trechos de até 120 caracteres); por isso os históricos divergem após a primeira.
Perfil e eventos são sintéticos. O teto é o da Luna: 180 tokens sem thinking e 3000
com thinking, incluindo raciocínio. Não altera a configuração salva nem emite áudio.

JSON e Markdown em `logs/dark_souls/thinking-*.{json,md}` são atualizados após cada
resposta. Guardam identidade do modelo/engine, pedidos completos, falas, tempo,
volume de raciocínio e término por limite. Geração acima de 30 segundos já ultrapassa
a validade da morte antes do TTS; ficar abaixo não garante entrega durante o jogo.
As métricas não pontuam criatividade: leia a sequência inteira para avaliar repetição,
humor e invenção de fatos.
Resultado inicial: [comparação de thinking em 24/09](resultado_dark_souls_thinking.md).

## Bancada de TTS — Kokoro x Pocket TTS

O Pocket exige NumPy 2, enquanto a Luna usa NumPy 1.26. Por isso ele fica num ambiente virtual
separado e opcional — **não o instale no `venv` principal**:

```bash
py -3.12 -m venv .venv-tts
.\.venv-tts\Scripts\python.exe -m pip install -r testes\requirements_tts.txt
```

Depois gere os mesmos quatro textos nos dois motores:

```bash
.\venv\Scripts\python.exe -X utf8 testes\bancada_tts.py
```

Os WAVs e um `resultado_<motor>.json` para cada TTS ficam em `logs/bancada_tts/`. O relatório mede carga, preparo da
voz, tempo até o primeiro áudio, tempo total e RTF. Isso não troca o TTS da Luna nem inicia a
interface. Para comparar a prévia maior em português, use `--pocket-idioma portuguese_24l`;
para medir só um caso ou repetir, use `--caso curta --repeticoes 3`. A opção
`--pocket-temperatura 0.3` permite medir se valores menores deixam o Pocket mais consistente.
Cópias com o mesmo volume percebido podem ser criadas sem alterar os brutos com
`--normalizar-pasta <pasta>`; o alvo padrão (`0.049` RMS) veio da Nicole nesta bancada.


## KittenTTS 2 ? bancada isolada em CPU

Esta bancada gera WAVs com os mesmos quatro textos no KittenTTS 2 e no Kokoro.
O Kitten usa a voz Portuguese, normalizacao inglesa desligada e duas amostras
extras com emocao. Registra tempo ate o primeiro chunk, tempo total, duracao e RTF.
Nao inicia a Luna nem altera suas dependencias ou motor de voz.

Crie um ambiente separado e instale o PyTorch CPU antes das demais dependencias:

```powershell
.\venv\Scripts\python.exe -m venv logs/ambientes/kitten2
.\logs\ambientes\kitten2\Scripts\python.exe -m pip install torch==2.6.0 torchaudio==2.6.0 --index-url https://download.pytorch.org/whl/cpu
.\logs\ambientes\kitten2\Scripts\python.exe -m pip install -r testes/requirements_kitten2.txt
```

Execute cada motor em seu proprio ambiente, em sequencia:

```powershell
.\venv\Scripts\python.exe -X utf8 -m testes.bancada_kitten2 --motor kokoro --saida logs/bancada_tts/nova-comparacao
.\logs\ambientes\kitten2\Scripts\python.exe -X utf8 -m testes.bancada_kitten2 --motor kitten2 --saida logs/bancada_tts/nova-comparacao
```

Use um destino novo para preservar resultados. A opcao --modelo-local aponta
para um snapshot baixado e fixa a revisao dos pesos. --somente-estavel pula as
amostras com tags de emocao. O runtime testado e Python; a versao C++ tem kernels
CPU proprios e precisa de outra medicao.

[Resultado do primeiro teste](resultado_kitten2.md).

## Sopro — bancada e demo local em CPU

Ambiente opcional, separado da Luna. A versão fixada da bancada é Sopro 2.2.0.
Instale PyTorch CPU primeiro; não instale estes requisitos no venv principal:

```powershell
.\venv\Scripts\python.exe -m venv logs/ambientes/sopro
.\logs\ambientes\sopro\Scripts\python.exe -m pip install torch==2.6.0 torchaudio==2.6.0 --index-url https://download.pytorch.org/whl/cpu
.\logs\ambientes\sopro\Scripts\python.exe -m pip install -r testes/requirements_sopro.txt
```

Gere quatro frases nos modos completo e streaming, usando uma referência de 5–20 s:

```powershell
.\logs\ambientes\sopro\Scripts\python.exe -X utf8 -m testes.bancada_sopro --ref logs/bancada_tts/kitten2-20261003/amostras/kokoro_conquista_stable.wav --saida logs/bancada_tts/sopro-nova-rodada
```

Use um destino novo a cada rodada. Pode usar outro WAV com --ref; --modo offline
ou --modo stream limita a execução. --int8 é opcional e não foi medido no piloto.
O script fixa a revisão do modelo, mantém cache em logs/cache_sopro e registra
carga, preparo, aquecimento, latências e os WAVs. Não toca áudio.

Para experimentar textos pelo navegador, depois de baixar o modelo pela bancada:

```powershell
.\logs\ambientes\sopro\Scripts\python.exe -X utf8 -u -m testes.servir_sopro
```

Abra http://127.0.0.1:7860/. O idioma PT e a referência Nicole já ficam selecionados.
Digite o texto e clique em **Gerar fala**. Pode escolher outro áudio de referência;
a geração continua no Python CPU, sem ONNX/WebGPU. Feche com Ctrl+C no terminal.
Se já houver uma demo na porta 7860, use a existente ou --port 7861.

O launcher serve uma cópia da demo oficial em logs, sem o importmap de CDN.
A Luna não é iniciada nem tem sua configuração de voz alterada.

[Resultado do piloto](resultado_sopro.md).

Se a demo estiver rodando em segundo plano, encerre apenas o piloto com:

```powershell
.\logs\ambientes\sopro\Scripts\python.exe -X utf8 -m testes.servir_sopro --parar
```

Use --port também no encerramento se escolheu outra porta. A Luna continua funcionando.

Para iniciar a demo com outra referência já convertida para WAV:

```powershell
.\logs\ambientes\sopro\Scripts\python.exe -X utf8 -u -m testes.servir_sopro --ref <caminho-do-wav>
```

O nome mostrado na interface vem desse arquivo. Encerre a demo existente com
--parar antes de iniciar outra na mesma porta. A bancada de 04/10 também
incluiu uma rodada com gravação humana, mantendo os mesmos quatro textos.

## Piloto de acompanhamento Sopro/PT-BR

O painel **Acompanhando: Sopro** fica recolhido acima da entrada no modo web. O estado
é local (`modelos/acompanhamento_sopro.json`); o piloto consulta apenas fontes públicas
fixas, sem credenciais, dependências novas, captura de tela ou download de modelos.

Regressões sem rede, áudio ou LLM:

```powershell
.\venv\Scripts\python.exe -X utf8 -m unittest testes.testa_acompanhamento_sopro
node testes/rodar.js
```

Bancada de texto com anúncios fictícios e o ID do modelo escolhido no TurboLLM:

```powershell
.\venv\Scripts\python.exe -X utf8 -m testes.bancada_acompanhamento_sopro --modelo "ID do modelo no TurboLLM"
```

A bancada registra as respostas em `logs/bancada_acompanhamento_sopro/`. Leia se ela
preservou a diferença entre plano futuro, anúncio e melhoria realmente ouvida.
Ela não mede humor por um placar automático e não altera o estado do acompanhamento.
Guia: [resultado_acompanhamento_sopro.md](resultado_acompanhamento_sopro.md).

## EmbeddingGemma 2 — comparação de memória na CPU

A bancada usa exemplos sintéticos em português e não importa módulos da Luna.
Compara `all-MiniLM-L6-v2`, `paraphrase-multilingual-MiniLM-L12-v2` e
`google/embeddinggemma-2` em dois canais: fatos curtos e pares de conversa.
Crie um ambiente separado; não instale os requisitos no venv principal:

```powershell
.\venv\Scripts\python.exe -m venv logs/bancada_embeddings/venv
.\logs\bancada_embeddings\venv\Scripts\python.exe -m pip install -r testes/requirements_embeddings.txt
.\logs\bancada_embeddings\venv\Scripts\python.exe -X utf8 -u -m testes.bancada_embeddings
```

Os três modelos rodam em processos separados, na CPU, float32 e quatro threads.
O Gemma carrega apenas os parâmetros textuais. Os prefixos de consulta/documento
seguem o checkpoint oficial; 768d e 256d reutilizam a mesma inferência.
Os modelos podem ser baixados na primeira execução; o cache fica em `logs/`.

Cada canal tem 30 documentos e 40 consultas. Metade das consultas calibra o
filtro e a outra metade fica reservada para medir os resultados. O limiar
conservador é maior que todos os escores negativos da calibração. Ele é uma
referência experimental, não uma configuração pronta para a memória real.

Os JSONs registram revisões, versões, rankings completos, filtros, tempo e RAM.
O relatório Markdown resume os acertos antes do filtro e as memórias aceitas
depois dele. Use `--saida logs/bancada_embeddings/nova-rodada` para definir o
destino; resultados existentes não são sobrescritos.

Verificações dos critérios, sem carregar os modelos:

```powershell
.\venv\Scripts\python.exe -X utf8 -m unittest testes.testa_bancada_embeddings
```

[Resultado do piloto](resultado_embeddings.md).

## Adoção do EmbeddingGemma 2

Os caminhos reais usam um único embedder textual na CPU. Os pisos iniciais em
768 dimensões são 0,772 para memória, 0,75 para histórico e 0,77 para candidatos
de deduplicação. A similaridade recupera referências; o classificador continua
decidindo se o candidato repete um fato ou traz uma atualização.

Testes de migração, prefixos, filtros e memória fria:

```powershell
.\venv\Scripts\python.exe -X utf8 -m unittest testes.testa_embeddings testes.testa_memoria_dedup
```

Validação dos caminhos reais com dados sintéticos, sem ler notas privadas:

```powershell
.\venv\Scripts\python.exe -X utf8 -u -m testes.bancada_memoria_embeddinggemma
```

Essa rodada também exercita a cópia de uma coleção Chroma de 384 para 768
dimensões. As provas de repetição, atualização e assunto novo verificam quais
referências chegam à curadoria; não substituem a decisão do classificador.

Migração do histórico local sem iniciar a Luna:

```powershell
.\venv\Scripts\python.exe -X utf8 -m ferramentas.migrar_embeddings
```

O índice antigo fica preservado. IDs de origem já copiados ficam registrados
para não ressuscitar conversas removidas pelo limite de 30; falas adicionais
feitas pela instância antiga antes do reinício são sincronizadas.

## Apresentação das respostas na web

`bancada_formatacao_web.py` captura a chamada real da persona com dados sintéticos,
sem acessar notas pessoais ou executar ferramentas. Antes de mudar o prompt:

```powershell
.\venv\Scripts\python.exe -X utf8 -m testes.bancada_formatacao_web preparar --pasta logs/bancada_web/nova-rodada --variante antes
```

Depois da mudança, com o Gemma carregado no TurboLLM:

```powershell
.\venv\Scripts\python.exe -X utf8 -m testes.bancada_formatacao_web preparar --pasta logs/bancada_web/nova-rodada --variante depois
.\venv\Scripts\python.exe -X utf8 -m testes.bancada_formatacao_web rodar --pasta logs/bancada_web/nova-rodada
```

São 20 respostas: comparação, procedimento, código e explicação com duas seeds,
além de comentário leve e saudação com uma seed. Leia o resultado por ramo:
orientação visual entra no prompt completo da web; o núcleo enxuto da saudação
continua igual. O JSON é salvo a cada resposta para preservar o progresso.

Para o renderizador e a separação entre canais, rode `node testes/rodar.js` e
`python -m unittest testes.testa_prompt_montagem` usando o Python do venv.

[Resultado do piloto](resultado_formatacao_web.md).

## Cartões de novidades e acompanhamentos

`testa_cartoes_web.js` executa os componentes reais com dados sintéticos: links,
miniaturas opcionais e falha de carregamento,
cópia da fala, estado atual de mensagens antigas, pausa/retomada, painel e perda
de conexão. Integra `node testes/rodar.js`.

`testa_cartoes_web.py` verifica a separação entre metadados e texto no servidor,
a normalização dos cartões e a referência do acompanhamento de conversa. Rode
também os testes das tarefas que produzem esses dados:

```powershell
.\venv\Scripts\python.exe -X utf8 -m unittest testes.testa_cartoes_web testes.testa_acompanhamento_sopro testes.testa_acompanhamento_fontes testes.testa_acompanhamentos testes.testa_links_novidades testes.testa_radar_interrupcao testes.testa_recebimento_web
```

[Resultado e prévia do piloto](resultado_cartoes_web.md). A prévia usa exemplos
de demonstração e não acessa a instância da Luna nem o TurboLLM.
