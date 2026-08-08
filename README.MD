# 🌙 Luna

<p align="center">
  <img src="docs/luna-demo.gif" alt="Luna comentando por voz uma notícia do radar RSS" width="380">
</p>

Imagine uma Alexa que:

- conhece seus jogos
- acompanha sua agenda
- conversa naturalmente
- lembra de conversas antigas
- controla seu computador

...mas cujo cérebro roda no seu próprio PC.

**Essa é a Luna** — uma amiga de IA que ouve por voz (push-to-talk), responde falando, tem
interface web, integra com Telegram e toma iniciativa por conta própria (proativo). Fala em
PT-BR caloroso, e o **núcleo de IA — pensar (LLM), ouvir (STT) e falar (TTS) — roda 100%
local**, na sua própria máquina.

> 🛠️ **Quer instalar do zero?** O passo a passo completo (TurboLLM, modelos, chaves, tudo)
> está no **[`INSTALACAO.md`](INSTALACAO.md)**. Este README aqui é o mapa da *arquitetura*.

## 🎙️ Ouça a Luna

A própria Luna se apresentando, na voz dela (Kokoro TTS, pt-BR) — **clique no ▶ pra ouvir**:

https://github.com/user-attachments/assets/dec2ef52-8a6b-41c9-97ad-27f86b9adad6

Projeto de hobby. A persona tem prompt curto de propósito — o modelo define o tom
naturalmente. O nome do usuário (e tudo mais que é pessoal) fica no `.env`, fora do código.

## 🔒 O que roda local × o que usa API

O **núcleo** (pensar, ouvir, falar) é 100% local — o raciocínio e a sua voz não dependem de
nuvem. As **ferramentas** ligam pra serviços externos só quando você as aciona:

| 🖥️ Roda 100% no seu PC | ☁️ Usa API externa (ao acionar a ferramenta) |
|------------------------|-----------------------------------------------|
| LLM / raciocínio (Gemma-4-12B) | Ver tela / analisar imagem → Gemini (Google) |
| Transcrição de voz (Faster-Whisper) | Gerar imagem → Hugging Face |
| Síntese de voz (Kokoro) | Agenda → Google · E-mail → Gmail |
| Memória (perfil, episódica, ChromaDB) | Música → Spotify · Jogos → Steam / OverFast |
| Persona e camada proativa | Clima, pesquisa web, animes, GIFs, Telegram |

> 💡 Este README também serve de **contexto para a LLM**: dá pra colar ele inteiro
> num chat com a Claude/ChatGPT pra ela entender o projeto de cara.

---

## 🖥️ Hardware

| Peça | Detalhe |
|------|---------|
| GPU  | AMD RX 9060 XT 16GB (RDNA4, gfx1200) |
| CPU  | Ryzen 5 5600 |
| RAM  | 32GB |
| OS   | Windows 11 |

Atualmente, somente pra rodar a luna ele consome 9gb ram e 8gb gpu

Inferência acelerada por **ROCm** (via TurboLLM) — **não** Vulkan (Vulkan é lento nessa AMD).

---

## 🧠 Stack de IA

**STT (voz → texto)** — Faster-Whisper `small`, CPU, int8.
Push-to-talk: `Ctrl+Alt+F8` (segura pra gravar, solta pra enviar). O mesmo motor
transcreve os áudios que chegam pelo Telegram.

**TTS (texto → voz)** — **Kokoro-82M**, pt-BR (`lang_code='p'`), rodando local na CPU
via `sounddevice`. Escolhido pela prosódia natural de `?` e `!` (entonação de pergunta
e exclamação) e por ser leve (RTF ~0.3). Vozes disponíveis (só o timbre muda; a
pronúncia é sempre pt-BR):

| Voz | Timbre | |
|-----|--------|-|
| `jf_alpha`  | feminina, japonesa lendo pt-BR (charme de sotaque) | **padrão** |
| `af_bella`  | feminina, americana | |
| `af_nicole` | feminina, americana, tom mais sussurrado | |

Velocidade padrão **0.9x**. *(O Supertonic ficou como plano B arquivado em
`G:\Projetos\TTS_teste`, fácil de retomar se sair um sucessor melhor.)*

**LLM — MODO MONO (um modelo faz TUDO):**
- **Modelo:** Gemma-4-12B QAT (Q4_0) — faz o roteamento de ferramentas **E** gera a persona.
- **Servidor:** TurboLLM (OpenAI-compatível em `http://127.0.0.1:6996/v1`).
- **Engine:** llama.cpp ROCm — ~32 tok/s de geração na RX 9060 XT.
- Não existe roteador separado: `gerar_resposta` faz **2 chamadas ao mesmo modelo** —
  uma pra decidir a ferramenta, outra pra escrever a resposta.
- **`THINK_OFF` (crítico):** o Gemma-4-12B é um modelo "thinking". Se deixar ele
  raciocinar, ele gasta o orçamento de tokens pensando e devolve resposta vazia. Por
  isso toda chamada passa `extra_body={"chat_template_kwargs": {"enable_thinking": False}}`.
- **Nome com espaços** (`"gemma 4 12b it qat"`): é o único formato que o gateway do
  TurboLLM casa na biblioteca pra auto-carregar (JIT). Com hífens dá 503.
- **JIT + idle-unload:** o TurboLLM carrega na 1ª chamada (~6s a frio) e descarrega
  sozinho quando fica ocioso (libera VRAM) — recarrega na próxima fala.

A memória tem **3 camadas com papéis distintos** (pra não confundir o modelo):

- **Perfil** (`perfil.md` no Obsidian) — a **identidade**: quem o usuário é (trabalho,
  família, gostos). Estável, o usuário edita. Sempre no contexto.
- **Memória episódica** (`Luna/Memoria.md` no Obsidian) — **o que anda acontecendo**:
  eventos datados, assuntos em aberto, humor. A Luna **propõe** (extração no ocioso via o
  próprio 12B) e o usuário **confirma** numa caixa no web antes de salvar (o gate de
  confirmação é o anti-alucinação). Entram no prompt em **2 fatias**: os **~15 mais
  recentes** (continuidade; recência resolve conflito, o novo vence o velho) **+ lembranças
  antigas que casam com o assunto da conversa** (recall semântico — embedding multilíngue
  `paraphrase-multilingual-MiniLM-L12-v2` no CPU, ~470MB baixado na 1ª vez; piso alto pra só
  puxar quando o tema casa de verdade). **Curadoria esfria/esquenta**: evento com mais de ~45
  dias sem uso *esfria* e sai dos recentes (vai pro `Luna/Memoria_arquivo.md`, mantendo o
  `Memoria.md` enxuto), mas continua no recall — se o assunto volta à tona, *esquenta* e
  retorna pro ativo. **Retomada proativa**: a Luna puxa sozinha um assunto em aberto ("e aí,
  conseguiu consertar o PC?") — no máx 2x/dia (1ª uns minutos depois de ligar, 2ª ~6h depois),
  só fato registrado (o 12B escolhe qual é pendência, nunca inventa). **Hábitos de jogo**: ela
  comenta padrões *medidos* ("anda jogando bem mais Hollow Knight", "faz tempo que não abre
  Deadlock") a partir do que a Steam reporta ter sido jogado nas últimas 2 semanas — número
  real, nunca inventado; discreto (no máx 1x/dia). Fila de pendentes + lixo em
  `modelos/memoria_pendente.json`.
- **Conversas** (ChromaDB local) — **recall literal** das últimas 30 conversas, por busca
  semântica. Embedding all-MiniLM-L6-v2 (CPU, ~80MB), `LIMIAR_DISTANCIA=1.3`.

---

## 📓 O lado Obsidian (vault "semeado" sozinho)

Aponte `OBSIDIAN_VAULT` (no `.env`) pro seu vault e a Luna **cria o que falta na 1ª vez**
(nunca sobrescreve o que já existe):

| Arquivo | Pra que serve |
|---------|---------------|
| `Luna/perfil.md` | quem você é — o núcleo que ela carrega em toda conversa |
| `Luna/Memoria.md` | memória episódica (ela propõe, você confirma no painel web) |
| `Luna/animes.md` | lista de animes pro aviso de episódio novo (formato `- Nome \| apelido`) |
| `Luna/radar_rss.md` | feeds RSS que ela acompanha |
| `Luna/RastrearPromocoes.md` | canais do Telegram (`@`) + palavras-chave dos produtos que você caça |
| `.obsidian/snippets/luna-novidades.css` | deixa as notas **Novidades** e **Promoções** em colunas |

Ela também **escreve** em `Luna/Inbox/` (anotações que você pede), em `Novidades.md`
(o radar RSS, janela rolante de 72h) e em `Promocoes.md` (o radar de promoções, janela de 7 dias
— as fotos dos produtos ficam em `Luna/promo_imgs/` e somem junto com o card). Nenhuma das duas
cresce sem fim.

> 💡 **Pra ativar o layout bonito das Novidades:** Obsidian → *Configurações → Aparência →
> Snippets de CSS* → recarregar e ligar o **luna-novidades**. Aí cada notícia vira um card
> (capa + fonte + resumo) e eles se organizam em colunas conforme a largura da janela.

---

## 🔄 Fluxo principal (`main.py` → `loop_voz`)

1. **OUVIR** → `ouvir.py`: PTT (`Ctrl+Alt+F8`), grava áudio, Whisper transcreve.
2. **INTERCEPTA** → `main.py`: palavras-chave disparam ações sem passar pela LLM (ver abaixo).
3. **PENSAR** → `pensar.py`: o Gemma decide a ferramenta (chamada 1, thinking off) →
   executa → o mesmo modelo escreve a resposta com persona (chamada 2, thinking off).
4. **FALAR** → `falar.py`: limpa markdown/artefatos → Kokoro sintetiza → `sounddevice` toca.

**3 canais, 2 dimensões** — cada entrada define o *estilo* (curto pra voz, desenvolvido pra
texto) e a *presença* (se ela pode ou não sugerir algo que dependa do PC):

| Canal | Estilo | TTS | Presença |
|-------|--------|-----|----------|
| 🎙️ Voz (PTT) | conciso (1–3 frases) | fala | no PC |
| ⌨️ Texto no web | pode desenvolver | **só texto** | no PC |
| 📱 Telegram | pode desenvolver | só texto | **provavelmente fora** |

No Telegram o contexto situacional para de reportar o estado do PC (senão ela via "programa em
uso: firefox" e concluía que você estava sentado na máquina) e passa a evitar qualquer sugestão
que dependa do computador. Voz e texto do web **compartilham o mesmo histórico** — é uma conversa
só (`presenca_pc` viaja por `ContextVar`, thread-safe entre os canais).

**Interface:** Flask + WebSocket (`servidor.py`) em `localhost:5000`, aberta como janela
nativa via `pywebview` (Edge WebView2). System tray (`pystray`): Abrir / Ver logs / Fechar.

**Servidor de LLM:** o TurboLLM sobe sozinho no login (via `iniciar_turbollm.vbs` em
`shell:startup`, janela oculta). No boot, `garantir_modelo_turbollm()` dispara um warm-up
que carrega o 12B (JIT); se o TurboLLM estiver desligado, a Luna avisa. Rodar manual: `turbollm` no cmd.

---

## 📁 Estrutura de arquivos

```
main.py                — entry point, loop de voz, texto do web, interceptadores
servidor.py            — WebSocket/Flask: estado da interface, histórico, config, arquivos
iniciar_turbollm.vbs   — lançador do TurboLLM no login
setup_telegram_promo.py— login único do Telethon (gera a sessão do radar de promoções)
modulos/
  pensar.py            — motor de inferência: tool calling + persona (mono 12B) + ChromaDB
  falar.py             — TTS Kokoro + limpeza de texto (limpar_texto_para_voz)
  ouvir.py             — STT Faster-Whisper + PTT (também transcreve áudio do Telegram)
  habilidades.py       — todas as integrações externas (APIs, Spotify, etc.)
  proativa.py          — thread autônoma: tarefas de background + extração de memória (ocioso)
  telegram_bot.py      — bot do Telegram (texto + mensagens de voz)
  radar_promo.py       — lê canais de promoção do Telegram (Telethon, como o próprio usuário)
  tom.py               — lê o TOM da voz (SER acústico) e colore a persona — só no canal de voz
  memoria.py           — ChromaDB + fila da memória episódica + JSON (estado, vistos)
  obsidian.py          — vault: perfil.md, Memoria.md (episódica), notas, radares, animes
modelos/
  estado_luna.json     — estado situacional em tempo real (jogo ativo, programa, sessão)
  estado_proativo.json — persistência das rotinas diárias (bom_dia, etc.)
  chromadb/            — banco de conversas
templates/
  Index.html           — interface web (GIF, histórico, config, drag & drop, métricas)
Atalhos/
  Luna.vbs             — launcher silencioso   |   Luna.bat — launcher com terminal (debug)
```

---

## 🧰 Ferramentas (tool calling)

| Ferramenta | O que faz |
|-----------|-----------|
| `resumir_youtube`      | baixa a transcrição (aba ativa ou URL) e a persona resume |
| `resumir_site`         | faz fetch de qualquer URL e a persona resume |
| `adicionar_agenda`     | adiciona evento no Google Calendar |
| `ler_agenda_google`    | lista eventos dos próximos 30 dias |
| `controlar_spotify`    | tocar / pausar / próxima (spotipy + OAuth) |
| `pesquisar_web`        | DuckDuckGo, lê o conteúdo dos primeiros resultados |
| `checar_emails`        | IMAP Gmail, retorna remetente + assunto dos não lidos |
| `controlar_navegador`  | controla o Firefox via extensão WebSocket |
| `analisar_aba_atual`   | lê e resume a aba ativa do Firefox |
| `ver_tela`             | screenshot → Gemini descreve (e envia a foto no Telegram) |
| `desenhar_imagem`      | gera imagem via Hugging Face (FLUX.1-schnell) |
| `obter_clima`          | previsão do tempo via Open-Meteo (sem chave) |
| `alternar_mute`        | muta/desmuta o volume do sistema (pycaw) |
| `consultar_overwatch`  | rank, winrate, KDA e main via OverFast API |
| `consultar_jogo_steam` | preço, desconto, gênero e Metacritic de um jogo |
| `duvida_do_jogo`       | responde dúvida sobre o jogo que você está jogando AGORA (dicas, mecânicas) |
| `listar_processos_pesados` | os processos que mais consomem RAM/CPU no momento |
| `ler_obsidian`         | acha e lê uma nota do vault |
| `salvar_obsidian`      | guarda uma anotação em Luna/Inbox (inclui fotos do Telegram) |
| `listar_capacidades`   | lista o que a Luna consegue fazer (auto-gerada do código) |

*Fora do catálogo do roteador:* `ler_selecionado` (interceptador "traduz isso").
*Desativado:* `enviar_whatsapp` (pywhatkit instável).

> 🧹 **Removidas (ago/2026):** `abrir_programa` e `matar_processo`. Eram herança da fase
> "Jarvis" e não tinham uso real — pior, o `abrir_programa` disparava sozinho quando o assunto
> apenas *mencionava* abrir um programa. **Ferramenta morta não é neutra:** cada uma no catálogo
> é mais uma chance do roteador errar. O `matar_processo` ainda era arriscado (podia derrubar o
> SQL do trabalho). O que sobrou de útil virou aviso proativo (ver "guarda de recursos" abaixo).

---

## ⌨️ Interceptadores e atalhos

**Palavras-chave que agem sem passar pela LLM** (`main.py`): "veja minha agenda",
"um print" / "olha minha tela", "modo jogo/reunião/hibernação", "luna pausa",
"próxima música", "muta"/"desmuta", "traduz isso".

**Atalhos globais** (padrões — dá pra trocar na config web, seção ⌨ Teclas:
clica no campo e aperta a combinação nova; vale na hora, sem reiniciar):

| Tecla (padrão) | Ação |
|-------|------|
| `Ctrl+Alt+F8` | PTT: segura pra gravar, solta pra enviar |
| `Ctrl+F9`     | interrompe a fala imediatamente |
| `Ctrl+F7`     | toggle Modo Suspenso (bloqueia proativa e respostas) |

---

## 🌐 Interface web

Acesso: `http://localhost:5000` (janela nativa via pywebview).

A tela é dividida em duas zonas: **saída** em cima (tudo que é da Luna) e **entrada** embaixo
(tudo que é seu) — as duas formas de falar com ela, microfone e teclado, ficam juntas.

- Fala da Luna e do usuário em tempo real (efeito máquina de escrever); o status dela
  ("o que está fazendo agora") fica no próprio cabeçalho da caixa.
- **Caixa de texto:** digite e aperte Enter pra conversar **sem falar** — ela responde só por
  escrito (sem TTS), com a liberdade de tamanho do Telegram. Mesmo histórico da voz.
- GIF animado via Giphy (termo extraído da resposta: `[gif:termo]`), com botão de repetir fala (▶️).
- **Painel de pensamento** colapsável — o raio-X da 1ª chamada: ferramenta usada, **argumentos
  enviados** e o retorno; quando nenhuma ferramenta roda, mostra o que o roteador gerou (e é
  descartado). Serve pra diagnosticar acionamento errado sem caçar no log. Mais métricas de tok/s.
- Histórico da sessão e drag & drop de arquivos (`.txt/.md/.py/.js/.json/.pdf`…) pro prompt.
- **Configurações (engrenagem):** toggle do Proativo e de cada tarefa proativa (jogos, emails,
  agenda, pausa, clima, bom_dia, steam, navegador, radar RSS, promoções, animes, mortes no LoL…),
  seleção de voz (Alpha/Bella/Nicole) e velocidade do TTS.

---

## 🤖 Módulo proativo (`proativa.py`)

Thread separada, loop a cada 30s.

**Camada 1 — sempre ativa** (ignora suspensão e AFK): monitora jogos.
- Detecta abertura/fechamento via `psutil`. Ao fechar: consulta stats da partida (OverFast,
  LCU do LoL via lockfile, deadlock-api).
- **Overwatch — anti-repetição:** recitar rank+winrate de *carreira* fazia ela falar sempre a
  mesma coisa (carreira não muda). Ao **abrir**, sorteia UM ângulo (cutucar um herói, comparar
  os roles, um marco, ou zoeira sem número) e nunca repete o anterior; ao **fechar**, tira um
  *delta da sessão* (snapshot na abertura vs no fim) e comenta **o que rolou hoje**.
- **Steam:** ao abrir/fechar um jogo da Steam, comenta conquistas e tempo de sessão.
  Idle games (ex: Task Bar Hero) são ignorados.
- **Guarda de recursos:** ao abrir um jogo, se algum processo não-essencial passa de ~3GB de RAM
  (somado por nome — navegador se espalha em vários), ela **avisa** no briefing. Só avisa: nunca
  mata, nunca oferece matar, e ignora sistema, a própria Luna, Steam, SQL Server e o navegador.

**Camada 2 — ativa se não suspenso, AFK ≤ 5 min e sem jogo aberto:**

| Tarefa | Frequência | Silêncio |
|--------|-----------|----------|
| `checar_emails`      | 12h  | 18h–9h |
| `checar_agenda`      | 60min (avisa se evento em < 30min) | — |
| `lembrete_pausa`     | 150min | — |
| `monitorar_clima`    | 20min (fala só se começou a chover) | — |
| `steam_wishlist`     | 24h (alerta se desconto ≥ 50%) | — |
| `bom_dia`            | 1x/dia (agenda + emails matinais) | fora de 8h–11h |
| `autoconhecimento`   | ~4h (comenta algo real sobre o próprio funcionamento) | 0h–8h |
| `radar_rss`          | 30min (feeds do vault, com teaser da 1ª novidade) | 0h–7h |
| **`radar_promocoes`**| 30min (canais do Telegram via Telethon → card em `Promocoes.md`) | 0h–7h |
| **`avisar_animes`**  | 2h (avisa episódio que saiu nas últimas 72h — fonte AniList) | 0h–9h |
| `retomar_assunto`    | ≤2x/dia (puxa pendência em aberto; não repete o mesmo assunto por 21 dias) | — |
| `contexto_navegador` | Firefox em foco na mesma URL há 10+ min (YouTube → oferece resumo; artigo → comenta o tema) | — |

**Carência de boot (120s):** nos primeiros minutos o modelo ainda esquenta e várias tarefas
querem falar juntas — a fala ficava *starved* (ela detectava e até escrevia a nota, mas a voz
nunca saía). Agora os proativos de fala esperam o boot assentar.

**Anúncio atômico:** as tarefas que escrevem arquivo + dão teaser de voz (radar RSS, promoções,
animes) só marcam como "avisado" e gravam o card **depois que a fala sai de verdade**. Se a fala
for engolida, elas **re-tentam** no ciclo seguinte em vez de sumir caladas.

**Suspensão automática:** após 3 falas proativas sem resposta → suspende.
Reseta com qualquer fala do usuário ou abertura de jogo.

---

## 🔑 APIs e chaves (`.env`)

Copie `.env.example` para `.env` e preencha. **Nunca** commite o `.env` real nem
`modelos/credentials.json`.

| Chave | Pra quê |
|-------|---------|
| `USUARIO_NOME`   | seu nome — como a Luna te chama (privacidade: fora do código) |
| `GEMINI_API_KEY` | visão (`ver_tela`, análise de imagem) — não é usado na persona |
| `HF_TOKEN`       | geração de imagem (FLUX.1-schnell) — precisa da permissão "Inference Providers" |
| `GIPHY_API_KEY`  | GIFs na interface web (opcional) |
| `SPOTIPY_*`      | Spotify (client id/secret/redirect) |
| `EMAIL_USUARIO` / `EMAIL_SENHA` | Gmail IMAP (senha de app de 16 letras) |
| `OW_BATTLETAG`   | BattleTag do Overwatch (ex: `SeuNome-1234`) |
| `STEAM_API_KEY` / `STEAM_ID` | wishlist + jogos da Steam |
| `TELEGRAM_TOKEN` / `TELEGRAM_CHAT_ID` | bot do Telegram |
| `TELEGRAM_API_ID` / `TELEGRAM_API_HASH` | radar de promoções (API de cliente, em my.telegram.org) |
| `OBSIDIAN_VAULT` | caminho do vault que a Luna lê (opcional) |
| `CLIMA_LAT` / `CLIMA_LON` | localização pra previsão do tempo |

Google Calendar usa OAuth2 (`token.json` + `credentials.json` em `modelos/`, locais).
O radar de promoções faz um **login único** (`python setup_telegram_promo.py`) que gera
`modelos/luna_promo.session` — é credencial da sua conta, fica no `.gitignore`.

> 📖 Passo a passo de instalação (TurboLLM, modelos, cada chave e onde pegar):
> **[`INSTALACAO.md`](INSTALACAO.md)**.

---

## 🎭 Persona (`pensar.py`)

Tom de **amiga próxima**: calorosa, direta, bem-humorada, com humor afiado (sarcasmo,
ironia, deadpan) — sempre do lado de quem gosta do usuário, nunca cruel. A Luna é
amiga/parceira, **nunca** namorada ou esposa (modelos pequenos tendem a "virar esposa"
se o papel não for explícito — o prompt deixa o limite claro; detalhes pessoais, como
o nome da esposa, vêm do `perfil.md` privado do Obsidian, não do código).

Regras do prompt: 1ª pessoa sempre, 1 a 4 frases, datas em linguagem falada
("29 de julho às duas da tarde", nunca formato cru), não inventar fatos, proibido prometer
ação futura, sem emojis/markdown, e termina com `[gif:termo]` em inglês (meme/cultura
internet). Não cumprimenta ("boa noite" etc.) mais de uma vez a cada 6h — um rastreador de
saudação segura isso, já que o prompt sozinho não sabe o que é "primeiro contato".
O nome do usuário entra no prompt via `USUARIO_NOME` (.env); o resto do código fala
só "o usuário".

**Ousadia / imprevisibilidade (ago/2026).** A queixa era que ela ficara *previsível* — não por
falta de memória (isso ela tem), mas por sempre reagir do mesmo jeito. A regra **SURPREENDA**
pede que ela fuja do óbvio: pegue um ângulo de canto, vire o quadro, varie o registro e **crave
a posição** em vez de ficar em cima do muro. A surpresa vem do **ângulo e da entrega** — nunca de
inventar fato nem de narrar o que ele está fazendo (isso vira "narradora", o oposto do que se
quer). `temperature` da persona subiu de 0.65 → **0.8**. Dois freios: em momento sensível
(cansaço, estresse, saúde) ela **acolhe primeiro** e a zoeira fica pra outra hora; e pergunta é
fecho **ocasional**, nunca padrão (o "devolver a bola" tinha virado tique — 9 de 10 respostas
terminavam em "?").

**Camada de tom (`tom.py`, só na voz).** Um modelo acústico (SER) lê a *energia* da fala,
mantém uma baseline móvel do normal do usuário e, só quando o tom desvia, injeta uma dica
**sutil** que colore o COMO ela responde. Nunca vira o assunto nem é comentada em voz alta.

**Presença.** Voz e texto do web = ele está no PC; Telegram = provavelmente fora — nesse caso
ela não sugere nada que dependa do computador (ver "Fluxo principal").

O proativo usa `REGRA_PERSONA` (em `proativa.py`) com o mesmo tom.

---

## ⚡ Configurações rápidas (topo de `pensar.py`)

```python
BASE_LOCAL     = "http://127.0.0.1:6996/v1"   # TurboLLM (OpenAI-compatível)
MODELO_PERSONA = "gemma 4 12b it qat"         # ESPAÇOS (JIT do TurboLLM)
THINK_OFF      = {"chat_template_kwargs": {"enable_thinking": False}}  # em TODA chamada
ATIVAR_MEMORIA_PERMANENTE = False   # legado — substituído pela memória episódica
```

Trocar de modelo: mudar `BASE_LOCAL` e `MODELO_PERSONA`. Se o novo modelo não for
"thinking", o `THINK_OFF` é inofensivo.

---

## ⚠️ Limitações / pendências

- O TurboLLM precisa estar rodando (sobe no login; manual: `turbollm`). 1ª resposta após
  ocioso demora ~6s (recarga JIT).
- A extração da memória episódica ainda propõe algum ruído (ex: trivia técnica de uma
  conversa) — por isso ela **pede sua confirmação** antes de salvar; nada entra sozinho.
  A memória permanente antiga (`ATIVAR_MEMORIA_PERMANENTE`) virou legado: ela extraía em
  tempo real e alucinava, problema que o gate de confirmação resolveu.
- LCU API do LoL só funciona com o cliente rodando; extensão Firefox necessária pras
  ferramentas de navegador; `pdfplumber` opcional (PDF no drag & drop).

---

*Novidades e histórico de mudanças: veja [`PATCHNOTES.md`](PATCHNOTES.md).*
