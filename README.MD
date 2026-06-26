[CONTEXTO DO PROJETO PARA A LLM]
Assistente pessoal de IA local chamada Luna, rodando em Python no Windows 11.
Desenvolvida pelo Fábio. Persona com prompt mínimo — o modelo define o tom naturalmente.

================================================================================
1. HARDWARE
================================================================================
- GPU: RX 9060 XT 16GB VRAM
- CPU: Ryzen 5600
- RAM: 32GB
- OS:  Windows 11

================================================================================
2. STACK DE IA
================================================================================
STT (voz → texto):
  - Faster-Whisper "small", CPU, int8
  - PTT: Ctrl+Alt+F8 (segura para gravar, solta para enviar)

TTS (texto → voz):
  - Supertonic v1.2.1, PT-BR, voz "F1", velocidade 1.2x
  - Roda localmente via sounddevice
  - Tags de expressão inline: <breath>, <sigh>, <throatclear> (persona Gemini)

Tool Calling / Roteador (decide qual ferramenta chamar):
  - Modelo: nvidia/nemotron-3-nano-4b via LM Studio (local, ~3GB VRAM)
  - MODO_DUAL_LLM = True — roteador separado da persona

Persona (gera as respostas com personalidade):
  - PROVEDOR_PERSONA = "local" | "groq" | "gemini"
  - Local:  dolphin3.0-llama3.1-8b via LM Studio (atual — testando)
  - Groq:   llama-3.3-70b-versatile — free tier 1000 RPD
  - Gemini: gemini-2.5-flash — melhor qualidade
  - Fallback automático: se Groq/Gemini atingir quota → muda para local + avisa por voz
  - Trocar provedor: alterar MODELO_PERSONA e PROVEDOR_PERSONA no topo de pensar.py
  - Modelos testados: gemma-4-e4b-it, lfm2.5-8b-a1b (ruim em tool calling), hermes-3-llama-3.1-8b,
    dolphin-2.9-llama3-8b, dolphin3.0-llama3.1-8b

Memória de Conversas:
  - ChromaDB local — guarda últimas 30 conversas, busca semântica por relevância
  - Modelo de embedding: all-MiniLM-L6-v2 (CPU, ~80MB)

Memória Permanente (fatos sobre o usuário):
  - modelos/memoria_permanente.json
  - ATIVAR_MEMORIA_PERMANENTE = False (desativado — requer LLM capaz de extrair fatos)

================================================================================
3. ARQUITETURA — FLUXO PRINCIPAL (main.py → loop_voz)
================================================================================
1. OUVIR    → ouvir.py: PTT (Ctrl+Alt+F8), grava áudio, Whisper transcreve
2. INTERCEP → main.py: palavras-chave ativam ações sem passar pela LLM (ver seção 6)
3. PENSAR   → pensar.py: Nemotron decide ferramenta → executa → persona gera resposta
4. FALAR    → falar.py: limpa markdown/artefatos → Supertonic sintetiza → sounddevice toca

Interface:
  - Flask + WebSocket (servidor.py) rodando em localhost:5000
  - pywebview abre a interface como janela nativa (Edge WebView2)
  - System tray (pystray): Abrir interface / Ver logs / Fechar Luna

================================================================================
4. ESTRUTURA DE ARQUIVOS
================================================================================
main.py              — entry point, loop de voz, interceptadores de palavras-chave
servidor.py          — WebSocket/Flask: estado da interface, histórico, config, arquivos
modulos/
  pensar.py          — motor de inferência: tool calling + persona + ChromaDB
  falar.py           — TTS Supertonic + limpeza de texto (limpar_texto_para_voz)
  ouvir.py           — STT Faster-Whisper + PTT por teclado
  habilidades.py     — todas as integrações externas (APIs, Spotify, etc.)
  proativa.py        — thread autônoma com tarefas de background
  memoria.py         — ChromaDB + JSON (estado_luna, estado_proativo, vistos)
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
resumir_youtube      — baixa transcrição da aba ativa e resume com o Nemotron
resumir_site         — faz fetch de qualquer URL (Firefox ou clipboard) e resume
adicionar_agenda     — adiciona evento no Google Calendar
ler_agenda_google    — lista eventos dos próximos 30 dias
controlar_spotify    — tocar / pausar / próxima (via spotipy + OAuth)
pesquisar_web        — DuckDuckGo, lê conteúdo dos 3 primeiros resultados
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
  - Painel de pensamento colapsável (raciocínio do roteador + ferramenta usada)
  - Métricas de velocidade: tok/s do roteador e da persona
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
ATENÇÃO: chaves ficam em modulos/habilidades.py — NÃO commitar, NÃO enviar para IA web.

  GEMINI_API_KEY  — Google AI Studio — usado em: ver_tela (analisar_imagem_gemini)
                    e persona quando PROVEDOR_PERSONA = "gemini"
  GROQ_API_KEY    — console.groq.com — usado em: persona quando PROVEDOR_PERSONA = "groq"
  HF_TOKEN        — huggingface.co/settings/tokens — geração de imagem (desenhar_imagem, FLUX.1-schnell)
                    requer permissão "Make calls to Inference Providers"
  GIPHY_API_KEY   — giphy.com/dev — GIFs na interface web (opcional)
  OW_BATTLETAG    — BattleTag do Overwatch (ex: "Fabio-1600") — em .env ou habilidades.py

Google APIs (OAuth2, token em arquivo local):
  Google Calendar — credenciais em modelos/ (token.json + credentials.json)
  Gmail IMAP      — configurado em habilidades.py

Spotify:
  CLIENT_ID, CLIENT_SECRET, REDIRECT_URI em habilidades.py
  Cache de token em .spotify_cache

Steam:
  STEAM_API_KEY, STEAM_ID em proativa.py

================================================================================
11. PERSONAS (pensar.py)
================================================================================
Tom de AMIGA próxima — leve, animada, bem-humorada, calorosa e direta.
IMPORTANTE: Luna é amiga/parceira, NUNCA namorada ou esposa (a esposa do Fábio é a
Keila). Modelos pequenos tendem a "virar esposa" se o papel não for explícito — por
isso o prompt deixa o limite claro.

PROMPT_LUNA_PERSONA_LOCAL e PROMPT_LUNA_PERSONA_CLOUD (idênticos):
  "Você é a Luna, a IA pessoal e amiga próxima do Fábio. Fale sempre em PT-BR.
   - Tom leve, animado e bem-humorado, como uma amiga de verdade — calorosa e direta.
   - Amiga e parceira de PC; a esposa do Fábio é a Keila; NÃO é namorada nem esposa.
   - Respostas curtas e naturais (1 a 3 frases). Pode brincar.
   - Sem emojis, asteriscos ou markdown.
   - OBRIGATÓRIO: termina com [gif:termo] em inglês (meme/cultura internet)."

O proativo usa REGRA_PERSONA (proativa.py) com o mesmo tom amigável.

GIF:
  Extraído com regex flexível de [gif:termo] ou <gif:termo>
  Busca no Giphy via GIPHY_API_KEY e faz broadcast pela interface web

================================================================================
12. CONFIGURAÇÕES RÁPIDAS (pensar.py, topo do arquivo)
================================================================================
MODELO_ROTEADOR        = "nvidia/nemotron-3-nano-4b"       # LM Studio, tool calling (roteia ferramentas)
MODELO_PERSONA         = "ministral-3-14b-instruct-2512"  # local; gera a resposta com persona
PROVEDOR_PERSONA       = "local"   # "groq" | "gemini" | "local"
MODO_DUAL_LLM          = True      # True = Nemotron roteia (rápido/disciplinado) + Ministral 14B na persona. False = só o Ministral faz tudo (roteio aleatório e lento no backend Vulkan da AMD)
ATIVAR_MEMORIA_PERMANENTE = False  # True = LLM extrai e salva fatos em background

================================================================================
13. LIMITAÇÕES / PENDÊNCIAS
================================================================================
- ATIVAR_MEMORIA_PERMANENTE desativado — requer modelo que extraia fatos sem alucinar
- Groq free tier: 1000 RPD no Llama 3.3 70B (suficiente para uso pessoal diário)
- LCU API do LoL só funciona com LeagueClient.exe rodando (lockfile presente)
- Extensão Firefox deve estar instalada para: controlar_navegador, analisar_aba_atual,
  contexto de navegação proativo
- enviar_whatsapp desativado (pywhatkit instável)
- Geração de imagem usa Hugging Face (FLUX.1-schnell), não Gemini: o tier grátis do
  Gemini retorna quota 0 para imagem (só funciona com billing ativo). Pollinations grátis
  também foi descontinuado (402 Payment Required). FLUX leva ~3-8s por imagem.
- pdfplumber opcional — instalar para suporte a PDF no drag & drop
- Modelo local (gemma-4-e4b-it) pode ocasionalmente usar GIF no formato errado
  (<gif:termo> em vez de [gif:termo]) — regex flexível trata ambos
