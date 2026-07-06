[CONTEXTO DO PROJETO PARA A LLM]
Assistente pessoal de IA local chamada Luna, rodando em Python no Windows 11.
Desenvolvida pelo Fábio (projeto de hobby). Persona com prompt curto — o modelo
define o tom naturalmente. Amiga próxima, PT-BR caloroso.

================================================================================
1. HARDWARE
================================================================================
- GPU: AMD RX 9060 XT 16GB VRAM (RDNA4, gfx1200)
- CPU: Ryzen 5 5600
- RAM: 32GB
- OS:  Windows 11
- Inferência acelerada por ROCm (via TurboLLM) — NÃO Vulkan (Vulkan é lento nessa AMD).

================================================================================
2. STACK DE IA
================================================================================
STT (voz → texto):
  - Faster-Whisper "small", CPU, int8
  - PTT: Ctrl+Alt+F8 (segura para gravar, solta para enviar)

TTS (texto → voz):
  - Supertonic v1.2.1, PT-BR, voz "F1", velocidade 1.2x
  - Roda localmente via sounddevice
  - Tags de expressão inline que a persona pode usar: <laugh>, <sigh>, <breath>

LLM — MODO MONO (um modelo faz TUDO):
  - Modelo: Gemma-4-12B QAT (Q4_0) — faz o roteamento de ferramentas E gera a persona
  - Servidor: TurboLLM (OpenAI-compatível em http://127.0.0.1:6996/v1)
  - Engine: llama.cpp b9870 ROCm — ~32 tok/s de geração na RX 9060 XT
  - NÃO existe mais roteador separado (era o Nemotron 4B) nem MODO_DUAL_LLM:
    gerar_resposta faz 2 chamadas ao MESMO modelo — 1 pra decidir a ferramenta,
    1 pra escrever a resposta.
  - THINK_OFF (crítico): o Gemma-4-12B é um modelo "thinking". Se deixar ele
    raciocinar, gasta o orçamento de tokens pensando e devolve resposta VAZIA.
    Por isso toda chamada passa extra_body={"chat_template_kwargs":
    {"enable_thinking": False}} — desliga o raciocínio. (Ligar de volta só faz
    sentido pra debug do roteador; na persona volta a dar resposta vazia/lenta.)
  - Nome do modelo COM ESPAÇOS ("gemma 4 12b it qat"): é o único formato que o
    gateway do TurboLLM casa na biblioteca pra AUTO-CARREGAR (JIT). Com hífens dá 503.
  - JIT + idle-unload: o TurboLLM carrega o modelo na 1ª chamada da Luna (~6s a frio)
    e o descarrega sozinho quando fica ocioso (libera VRAM) — recarrega na próxima fala.

Memória de Conversas:
  - ChromaDB local — guarda as últimas conversas, busca semântica por relevância
  - Modelo de embedding: all-MiniLM-L6-v2 (CPU, ~80MB), LIMIAR_DISTANCIA=1.3

Memória Permanente (fatos sobre o usuário):
  - modelos/memoria_permanente.json  (+ perfil.md no Obsidian é o núcleo)
  - ATIVAR_MEMORIA_PERMANENTE = False (desativado — requer LLM que extraia fatos sem alucinar)

================================================================================
3. ARQUITETURA — FLUXO PRINCIPAL (main.py → loop_voz)
================================================================================
1. OUVIR    → ouvir.py: PTT (Ctrl+Alt+F8), grava áudio, Whisper transcreve
2. INTERCEP → main.py: palavras-chave ativam ações sem passar pela LLM (ver seção 6)
3. PENSAR   → pensar.py: o Gemma-4-12B decide a ferramenta (chamada 1, thinking off) →
             executa → o MESMO modelo gera a resposta com persona (chamada 2, thinking off)
4. FALAR    → falar.py: limpa markdown/artefatos → Supertonic sintetiza → sounddevice toca

Interface:
  - Flask + WebSocket (servidor.py) rodando em localhost:5000
  - pywebview abre a interface como janela nativa (Edge WebView2)
  - System tray (pystray): Abrir interface / Ver logs / Fechar Luna

Servidor de LLM (TurboLLM):
  - Sobe sozinho no login do Windows via Atalhos de inicialização (iniciar_turbollm.vbs
    na pasta shell:startup — janela oculta, --no-open). Usa caminho completo do node +
    turbollm global (npm i -g turbollm) pra não depender de PATH.
  - A Luna verifica no boot com garantir_modelo_turbollm(): se o 12B não estiver
    carregado, dispara um warm-up que o carrega (JIT); se o TurboLLM estiver desligado, avisa.
  - Rodar manualmente (se precisar): "turbollm" no cmd.

================================================================================
4. ESTRUTURA DE ARQUIVOS
================================================================================
main.py              — entry point, loop de voz, interceptadores de palavras-chave
servidor.py          — WebSocket/Flask: estado da interface, histórico, config, arquivos
iniciar_turbollm.vbs — lançador do TurboLLM no login (cópia também em shell:startup)
modulos/
  pensar.py          — motor de inferência: tool calling + persona (mono 12B) + ChromaDB
  falar.py           — TTS Supertonic + limpeza de texto (limpar_texto_para_voz)
  ouvir.py           — STT Faster-Whisper + PTT por teclado
  habilidades.py     — todas as integrações externas (APIs, Spotify, etc.)
  proativa.py        — thread autônoma com tarefas de background
  memoria.py         — ChromaDB + JSON (estado_luna, estado_proativo, vistos)
  obsidian.py        — leitura/escrita do vault (perfil.md, notas, radar RSS)
modelos/
  cores.py           — cores ANSI para o terminal
  log.py             — configuração do logging (arquivo + console)
  estado_luna.json   — estado situacional em tempo real (jogo ativo, programa, sessão)
  estado_proativo.json — persistência das rotinas diárias (bom_dia, etc.)
  chromadb/          — banco de conversas
  memoria_permanente.json — fatos permanentes sobre o usuário
templates/
  Index.html         — interface web (GIF, histórico, config, drag & drop, métricas)
Atalhos/
  Luna.vbs           — launcher silencioso (sem janela CMD)
  Luna.bat           — launcher com terminal visível (modo debug)
  Luna Log.lnk       — atalho direto para logs/luna.log

================================================================================
5. FERRAMENTAS DISPONÍVEIS (TOOL CALLING)
================================================================================
resumir_youtube      — baixa a transcrição (aba ativa ou URL) e a persona resume
resumir_site         — faz fetch de qualquer URL (Firefox ou clipboard) e a persona resume
adicionar_agenda     — adiciona evento no Google Calendar
ler_agenda_google    — lista eventos dos próximos 30 dias
controlar_spotify    — tocar / pausar / próxima (via spotipy + OAuth)
pesquisar_web        — DuckDuckGo, lê conteúdo dos primeiros resultados
checar_emails        — IMAP Gmail, retorna remetente + assunto dos não lidos
controlar_navegador  — controla Firefox via extensão WebSocket (abrir URL, etc.)
analisar_aba_atual   — lê e resume o conteúdo da aba ativa do Firefox
ver_tela             — screenshot → Gemini analisa e descreve (e envia a foto no Telegram)
desenhar_imagem      — gera imagem via Hugging Face (FLUX.1-schnell), abre no navegador e envia foto no Telegram
abrir_programa       — abre jogos ou aplicativos por nome
obter_clima          — previsão do tempo via Open-Meteo (sem chave)
alternar_mute        — muta/desmuta volume do sistema via pycaw
consultar_overwatch  — perfil, rank, winrate, KDA e herói main via OverFast API
consultar_jogo_steam — preço, desconto, descrição, gênero e Metacritic de um jogo na Steam
ler_obsidian         — acha e lê uma nota do vault (receita, lista, etc.)
salvar_obsidian      — guarda uma anotação em Luna/Inbox (inclui fotos do Telegram)
listar_capacidades   — retorna lista do que Luna consegue fazer (auto-gerada do código)

Fora do catálogo do roteador (existem como função, mas não são acionadas por chat):
  ler_selecionado    — usada só pelo interceptador de "traduz isso" (main.py)
  listar_processos_pesados, matar_processo — podadas para reduzir tool calling errado

Desativado (comentado no código):
  enviar_whatsapp    — pywhatkit (instável)

================================================================================
6. INTERCEPTADORES DE PALAVRAS-CHAVE (main.py)
================================================================================
Ativam ações diretamente sem passar pelo LLM (mais rápido):
  Agenda:   "veja minha agenda", "consulte na minha agenda"
  Ver tela: "um print", "olha minha tela", "o que você vê", etc.
  Modo jogo: "modo jogo", "modo reunião", "modo hibernação"
  Spotify pausa: "luna pausa", "pausar música", "pausa aí"
  Spotify próxima: "próxima música", "pular música", "pula essa"
  Mute: "muta", "silencia", "desliga o som"
  Desmute: "desmuta", "volta o som", "liga o som"
  Tradução: "traduz isso", "traduza isso" — faz Ctrl+C no selecionado e traduz para PT-BR

================================================================================
7. ATALHOS DE TECLADO (GLOBAIS)
================================================================================
Ctrl + Alt + F8   — PTT: segura para gravar, solta para enviar
Ctrl + F9         — interrompe fala imediatamente (sd.stop())
Ctrl + F7         — toggle Modo Suspenso (bloqueia proativa e respostas)

================================================================================
8. INTERFACE WEB (servidor.py + templates/Index.html)
================================================================================
Acesso: http://localhost:5000 (janela nativa via pywebview)

Funcionalidades:
  - Exibe fala da Luna e do usuário em tempo real (typewriter effect)
  - GIF animado via Giphy (termo extraído da resposta: [gif:termo])
  - Painel de pensamento colapsável (ferramenta usada + resultado; com thinking off,
    normalmente não há bloco de raciocínio — ele só aparece se o thinking for religado)
  - Métricas de velocidade: tok/s da fase de roteamento e da persona
    (o número inclui o tempo de LER o prompt, então parece menor que os ~32 tok/s de geração)
  - Histórico de conversas da sessão (painel lateral esquerdo)
  - Drag & drop de arquivos: .txt, .md, .py, .js, .json, .pdf e outros
    → conteúdo injetado no prompt antes de enviar à LLM
  - Painel de configurações (engrenagem):
    - Toggle: Proativo, Memória permanente
    - Tarefas proativas individuais: jogos, emails, agenda, pausa, clima, bom_dia, steam, navegador
    - Seleção de voz (F1-F5, M1-M5) e velocidade TTS
    - Recarregar interface / Fechar Luna

WebSocket (/ws): canal bidirecional para todos os broadcasts em tempo real.

================================================================================
9. MÓDULO PROATIVO (proativa.py)
================================================================================
Thread separada, loop a cada 30 segundos.

Camada 1 — sempre ativa (ignora suspensão e AFK):
  _tarefa_monitorar_jogos:
    - Detecta abertura/fechamento via psutil
    - Jogos monitorados: Overwatch.exe, League of Legends.exe, Deadlock.exe
    - Ao abrir Overwatch: briefing frio com dados reais (rank + tendência de desempenho)
    - Ao abrir Deadlock: briefing com winrate atual da conta
    - Ao abrir outros: registra início da sessão em 1 frase
    - Ao fechar Overwatch: consulta OverFast API (endosso, main, horas, KDA, winrate)
    - Ao fechar LoL: aguarda 15s, consulta LCU API local via lockfile
      (KDA, campeão, CS, dano, resultado — vitória ou derrota)
    - Ao fechar Deadlock: consulta deadlock-api.com (KDA, net worth, winrate geral)

Camada 2 — ativa se NÃO suspenso e AFK ≤ 5 min, e sem jogo aberto:
  _tarefa_checar_emails      — a cada 12h, silêncio entre 18h–9h
  _tarefa_checar_agenda      — a cada 60min, avisa se evento em < 30min
  _tarefa_lembrete_pausa     — a cada 90min, lembrete ergonômico
  _tarefa_monitorar_clima    — a cada 20min, fala só se começou a chover
  _tarefa_steam_wishlist     — a cada 24h, alerta se desconto ≥ 50%
  _tarefa_bom_dia            — 1x/dia entre 8h–11h, agenda + emails matinais
  _tarefa_autoconhecimento   — introspecção: comenta algo real sobre o próprio funcionamento
  _tarefa_radar_rss          — acompanha feeds RSS do vault e avisa de novidades
  _tarefa_contexto_navegador — Firefox em foco + mesma URL há 10+ min:
    - YouTube: pergunta se quer resumo
    - Redes sociais (Reddit, Twitter, etc.): silêncio
    - Artigos/sites: comenta sobre o tema do título (não sobre o ato de navegar)
    - Firefox em background: silêncio total

Suspensão automática:
  Após MAX_TENTATIVAS (3) falas proativas sem resposta → _suspensa = True
  Resetado por: qualquer fala do usuário ou abertura de jogo

APIs externas do proativo:
  OverFast API  — perfil público Overwatch (sem chave)
  LCU API       — API local do cliente LoL via lockfile (porta + senha dinâmicas)
  deadlock-api.com — histórico e stats do Deadlock (sem chave)
  Steam API     — wishlist + preços (requer STEAM_API_KEY e STEAM_ID)
  Open-Meteo    — clima (sem chave)

================================================================================
10. APIS EXTERNAS E CHAVES
================================================================================
ATENÇÃO: chaves ficam em .env / modulos/habilidades.py — NÃO commitar, NÃO enviar para IA web.

  GEMINI_API_KEY  — Google AI Studio — usado em: ver_tela e analisar_imagem_gemini (VISÃO).
                    (NÃO é mais usado pra persona — a persona é 100% local no TurboLLM.)
  HF_TOKEN        — huggingface.co/settings/tokens — geração de imagem (desenhar_imagem, FLUX.1-schnell)
                    requer permissão "Make calls to Inference Providers"
  GIPHY_API_KEY   — giphy.com/dev — GIFs na interface web (opcional)
  OW_BATTLETAG    — BattleTag do Overwatch (ex: "Fabio-1600") — em .env ou habilidades.py

Obs: GROQ_API_KEY não é mais usado (o provedor de persona na nuvem foi removido).

Google APIs (OAuth2, token em arquivo local):
  Google Calendar — credenciais em modelos/ (token.json + credentials.json)
  Gmail IMAP      — configurado em habilidades.py

Spotify:
  CLIENT_ID, CLIENT_SECRET, REDIRECT_URI em habilidades.py
  Cache de token em .spotify_cache

Steam:
  STEAM_API_KEY, STEAM_ID em proativa.py

================================================================================
11. PERSONA (pensar.py)
================================================================================
Tom de AMIGA próxima — leve, animada, bem-humorada, calorosa e direta.
IMPORTANTE: Luna é amiga/parceira, NUNCA namorada ou esposa (a esposa do Fábio é a
Keila). Modelos pequenos tendem a "virar esposa" se o papel não for explícito — por
isso o prompt deixa o limite claro.

PROMPT_LUNA_PERSONA (um só — antes eram LOCAL e CLOUD idênticos):
  "Você é a Luna, a IA pessoal e amiga próxima do Fábio. Fale sempre em PT-BR coloquial
   (trate por 'você', nunca 'tu'/conjugações de Portugal).
   - Fale em PRIMEIRA PESSOA (é a Luna, nunca 'a Luna' em 3ª pessoa).
   - Tom leve, animado e bem-humorado, como uma amiga de verdade — calorosa e direta.
   - Amiga e parceira de PC; a esposa do Fábio é a Keila; NÃO é namorada nem esposa.
   - Respostas curtas e naturais (1 a 3 frases). Pode brincar.
   - Sem emojis, asteriscos ou markdown. Tags de voz <laugh>/<sigh>/<breath> com parcimônia.
   - OBRIGATÓRIO: termina com [gif:termo] em inglês (meme/cultura internet)."

Regra de idioma: jargão de jogo (tank, headshot, background) é ok; trocar palavra comum
por inglês/espanhol não ("those"→"esses", "cumpleaños"→"aniversário"). O Gemma respeita bem.

O proativo usa REGRA_PERSONA (proativa.py) com o mesmo tom amigável.

GIF:
  Extraído com regex flexível de [gif:termo] ou <gif:termo>
  Busca no Giphy via GIPHY_API_KEY e faz broadcast pela interface web

================================================================================
12. CONFIGURAÇÕES RÁPIDAS (pensar.py, topo do arquivo)
================================================================================
BASE_LOCAL     = "http://127.0.0.1:6996/v1"   # TurboLLM (OpenAI-compatível)
MODELO_PERSONA = "gemma 4 12b it qat"         # ESPAÇOS (JIT do TurboLLM); faz tools + persona
_MARCA_MODELO  = "gemma-4-12b"                # confere qual GGUF o TurboLLM serviu
THINK_OFF      = {"chat_template_kwargs": {"enable_thinking": False}}  # em TODA chamada
ATIVAR_MEMORIA_PERMANENTE = False             # True = LLM extrai e salva fatos em background

Trocar de modelo/servidor: mudar BASE_LOCAL e MODELO_PERSONA. Se o novo modelo NÃO for
"thinking", o THINK_OFF é inofensivo (pode manter). Se voltar pra um esquema de 2 modelos,
seria preciso reintroduzir a lógica de roteador separado (removida na migração pro mono).

================================================================================
13. LIMITAÇÕES / PENDÊNCIAS
================================================================================
- O TurboLLM precisa estar rodando (sobe sozinho no login via iniciar_turbollm.vbs;
  rodar manual: "turbollm" no cmd). A 1ª resposta após ocioso demora ~6s (recarga JIT).
- TurboLLM detecta a VRAM da RX 9060 XT errado (4,3 GB em vez de 16) → NÃO segura 2 modelos
  ao mesmo tempo. Por isso o desenho MONO (um modelo só). Se um dia corrigir a detecção,
  dá pra reavaliar um esquema de 2 modelos (roteador leve + persona).
- ATIVAR_MEMORIA_PERMANENTE desativado — requer modelo que extraia fatos sem alucinar.
- LCU API do LoL só funciona com LeagueClient.exe rodando (lockfile presente).
- Extensão Firefox deve estar instalada para: controlar_navegador, analisar_aba_atual,
  contexto de navegação proativo.
- enviar_whatsapp desativado (pywhatkit instável).
- Geração de imagem usa Hugging Face (FLUX.1-schnell), não Gemini: o tier grátis do
  Gemini retorna quota 0 para imagem. FLUX leva ~3-8s por imagem.
- pdfplumber opcional — instalar para suporte a PDF no drag & drop.
