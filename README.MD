# 🌙 Luna

Assistente pessoal de IA **100% local**, rodando em Python no Windows 11. Uma amiga
próxima que fala em PT-BR caloroso: ouve por voz (push-to-talk), responde falando,
tem interface web, integra com Telegram e faz coisas por conta própria (proativo).

Projeto de hobby. A persona tem prompt curto de propósito — o modelo define o tom
naturalmente. O nome do usuário (e tudo mais que é pessoal) fica no `.env`, fora do código.

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

**Memória de conversas** — ChromaDB local, busca semântica por relevância.
Embedding: all-MiniLM-L6-v2 (CPU, ~80MB), `LIMIAR_DISTANCIA=1.3`.

**Memória permanente** (fatos sobre o usuário) — `modelos/memoria_permanente.json`
(+ `perfil.md` no Obsidian é o núcleo). `ATIVAR_MEMORIA_PERMANENTE = False` (desativado
— requer um LLM que extraia fatos sem alucinar).

---

## 🔄 Fluxo principal (`main.py` → `loop_voz`)

1. **OUVIR** → `ouvir.py`: PTT (`Ctrl+Alt+F8`), grava áudio, Whisper transcreve.
2. **INTERCEPTA** → `main.py`: palavras-chave disparam ações sem passar pela LLM (ver abaixo).
3. **PENSAR** → `pensar.py`: o Gemma decide a ferramenta (chamada 1, thinking off) →
   executa → o mesmo modelo escreve a resposta com persona (chamada 2, thinking off).
4. **FALAR** → `falar.py`: limpa markdown/artefatos → Kokoro sintetiza → `sounddevice` toca.

**Interface:** Flask + WebSocket (`servidor.py`) em `localhost:5000`, aberta como janela
nativa via `pywebview` (Edge WebView2). System tray (`pystray`): Abrir / Ver logs / Fechar.

**Servidor de LLM:** o TurboLLM sobe sozinho no login (via `iniciar_turbollm.vbs` em
`shell:startup`, janela oculta). No boot, `garantir_modelo_turbollm()` dispara um warm-up
que carrega o 12B (JIT); se o TurboLLM estiver desligado, a Luna avisa. Rodar manual: `turbollm` no cmd.

---

## 📁 Estrutura de arquivos

```
main.py                — entry point, loop de voz, interceptadores de palavras-chave
servidor.py            — WebSocket/Flask: estado da interface, histórico, config, arquivos
iniciar_turbollm.vbs   — lançador do TurboLLM no login
modulos/
  pensar.py            — motor de inferência: tool calling + persona (mono 12B) + ChromaDB
  falar.py             — TTS Kokoro + limpeza de texto (limpar_texto_para_voz)
  ouvir.py             — STT Faster-Whisper + PTT (também transcreve áudio do Telegram)
  habilidades.py       — todas as integrações externas (APIs, Spotify, etc.)
  proativa.py          — thread autônoma com tarefas de background
  telegram_bot.py      — bot do Telegram (texto + mensagens de voz)
  memoria.py           — ChromaDB + JSON (estado_luna, estado_proativo, vistos)
  obsidian.py          — leitura/escrita do vault (perfil.md, notas, radar RSS, animes)
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
| `abrir_programa`       | abre jogos ou aplicativos por nome |
| `obter_clima`          | previsão do tempo via Open-Meteo (sem chave) |
| `alternar_mute`        | muta/desmuta o volume do sistema (pycaw) |
| `consultar_overwatch`  | rank, winrate, KDA e main via OverFast API |
| `consultar_jogo_steam` | preço, desconto, gênero e Metacritic de um jogo |
| `ler_obsidian`         | acha e lê uma nota do vault |
| `salvar_obsidian`      | guarda uma anotação em Luna/Inbox (inclui fotos do Telegram) |
| `listar_capacidades`   | lista o que a Luna consegue fazer (auto-gerada do código) |

*Fora do catálogo do roteador:* `ler_selecionado` (interceptador "traduz isso").
*Desativado:* `enviar_whatsapp` (pywhatkit instável).

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

- Fala da Luna e do usuário em tempo real (efeito máquina de escrever).
- GIF animado via Giphy (termo extraído da resposta: `[gif:termo]`), com botão de repetir fala (▶️).
- Painel de pensamento colapsável (ferramenta usada + resultado) e métricas de tok/s.
- Histórico da sessão e drag & drop de arquivos (`.txt/.md/.py/.js/.json/.pdf`…) pro prompt.
- **Configurações (engrenagem):** toggle do Proativo e de cada tarefa proativa
  (jogos, emails, agenda, pausa, clima, bom_dia, steam, navegador, radar, animes),
  seleção de voz (Alpha/Bella/Nicole) e velocidade do TTS.

---

## 🤖 Módulo proativo (`proativa.py`)

Thread separada, loop a cada 30s.

**Camada 1 — sempre ativa** (ignora suspensão e AFK): monitora jogos.
- Detecta abertura/fechamento via `psutil`. Ao abrir Overwatch/Deadlock: briefing com
  dados reais (rank/winrate). Ao fechar: consulta stats da partida (OverFast, LCU do
  LoL via lockfile, deadlock-api).
- **Steam:** ao abrir/fechar um jogo da Steam, comenta conquistas e tempo de sessão.
  Idle games (ex: Task Bar Hero) são ignorados.

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
| **`avisar_animes`**  | ~4x/dia (avisa no dia em que sai episódio novo — fonte AniList) | 0h–9h |
| `contexto_navegador` | Firefox em foco na mesma URL há 10+ min (YouTube → oferece resumo; artigo → comenta o tema) | — |

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
| `OBSIDIAN_VAULT` | caminho do vault que a Luna lê (opcional) |
| `CLIMA_LAT` / `CLIMA_LON` | localização pra previsão do tempo |

Google Calendar usa OAuth2 (`token.json` + `credentials.json` em `modelos/`, locais).

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

O proativo usa `REGRA_PERSONA` (em `proativa.py`) com o mesmo tom.

---

## ⚡ Configurações rápidas (topo de `pensar.py`)

```python
BASE_LOCAL     = "http://127.0.0.1:6996/v1"   # TurboLLM (OpenAI-compatível)
MODELO_PERSONA = "gemma 4 12b it qat"         # ESPAÇOS (JIT do TurboLLM)
THINK_OFF      = {"chat_template_kwargs": {"enable_thinking": False}}  # em TODA chamada
ATIVAR_MEMORIA_PERMANENTE = False
```

Trocar de modelo: mudar `BASE_LOCAL` e `MODELO_PERSONA`. Se o novo modelo não for
"thinking", o `THINK_OFF` é inofensivo.

---

## ⚠️ Limitações / pendências

- O TurboLLM precisa estar rodando (sobe no login; manual: `turbollm`). 1ª resposta após
  ocioso demora ~6s (recarga JIT).
- O TurboLLM detecta a VRAM da RX 9060 XT errado (4,3 GB em vez de 16) → não segura 2
  modelos ao mesmo tempo. Daí o desenho MONO.
- `ATIVAR_MEMORIA_PERMANENTE` desativado (requer modelo que extraia fatos sem alucinar).
- LCU API do LoL só funciona com o cliente rodando; extensão Firefox necessária pras
  ferramentas de navegador; `pdfplumber` opcional (PDF no drag & drop).

---

*Novidades e histórico de mudanças: veja [`PATCHNOTES.md`](PATCHNOTES.md).*
