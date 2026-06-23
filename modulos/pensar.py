#pensar.py

import logging
import threading
import json
import time
import re
import datetime
from openai import OpenAI

_log = logging.getLogger("luna.pensar")
from google import genai
from google.genai import types as genai_types
import modelos.cores as cor
from modulos.habilidades import (
    obter_transcricao, adicionar_evento_google, ler_agenda_google,
    obter_previsao_tempo, gerenciador_spotify, pesquisar_na_web,
    enviar_mensagem_whatsapp, checar_emails_nao_lidos, controlar_firefox_via_extensao,
    obter_contexto_navegador, listar_processos_pesados, abrir_programa, matar_processo,
    obter_janela_em_foco, analisar_imagem_gemini, capturar_tela_base64, ler_texto_selecionado,
    desenhar_imagem, executar_analise_aba, definir_lembrete, alternar_mute,
    ler_url_especifica, ler_link_copiado, consultar_overwatch, consultar_jogo_steam,
    ferramentas_disponiveis, GEMINI_API_KEY, GROQ_API_KEY)
from modulos.memoria import (
    buscar_contexto_relevante, salvar_conversa,
    ler_memoria_permanente, analisar_e_salvar_fato, ler_estado_luna
)
from modulos.falar import limpar_texto_para_voz, periodo_atual
from modulos import obsidian
import subprocess
import httpx

"""
MÓDULO DE PENSAR DA LUNA (MOTOR DE INFERÊNCIA)
---------------------------------------------------------
Responsável por todo o ciclo de raciocínio da Luna: recebe o texto do usuário,
decide se aciona uma ferramenta, executa a ferramenta e gera a resposta final
com personalidade via LLM de persona.

Configurações principais (topo do arquivo):
  MODELO_ROTEADOR        — modelo local no LM Studio para tool calling (Nemotron 4B)
  MODELO_PERSONA         — modelo para gerar a resposta com personalidade
  PROVEDOR_PERSONA       — "groq" | "gemini" | "local"
  MODO_DUAL_LLM          — True: Nemotron roteia ferramentas + persona gera resposta
                           False: um único modelo faz tudo (menos confiável para tools)
  ATIVAR_MEMORIA_PERMANENTE — True: extrai e salva fatos sobre o usuário em background
                              False: desativado (ChromaDB de conversas ainda funciona)

Fluxo principal (processar_entrada):
  1. Busca contexto relevante no ChromaDB (últimas 30 conversas, semântica)
  2. MODO_DUAL_LLM=True → Nemotron decide ferramenta → executa → persona gera resposta
  2. MODO_DUAL_LLM=False → MODELO_PERSONA faz tool calling + geração em uma chamada
  3. Salva conversa no ChromaDB
  4. Se ATIVAR_MEMORIA_PERMANENTE: extrai fatos em background (thread separada)

Ferramentas com lógica interna de LLM (definidas aqui, não em habilidades.py):
  _executar_resumir_youtube() — pega URL da aba ativa via extensão Firefox, baixa transcrição,
                                pré-resume com MODELO_ROTEADOR antes de passar à persona
  _executar_resumir_url()     — pega URL do Firefox ou clipboard, faz fetch via ler_url_especifica,
                                pré-resume com MODELO_ROTEADOR antes de passar à persona

Prompts disponíveis:
  PROMPT_LUNA_PERSONA_LOCAL  — prompt mínimo para o modelo de persona local (Dolphin)
  PROMPT_LUNA_PERSONA_CLOUD  — prompt mínimo para APIs externas (Groq/Gemini)
"""

MODELO_ROTEADOR  = "nvidia/nemotron-3-nano-4b"
MODELO_PERSONA   = "dolphin3.0-llama3.1-8b"
PROVEDOR_PERSONA = "local"   # "groq" | "gemini" | "local"

# True  = 2 LLMs: roteador leve detecta ferramentas, persona gera a resposta
# False = 1 LLM: MODELO_PERSONA faz tudo (mais confiável em tool calling, mais lento no roteamento)
MODO_DUAL_LLM = True

# True  = analisa conversas e salva fatos na memória permanente em background
# False = desativa completamente (útil enquanto o modelo estiver salvando lixo)
ATIVAR_MEMORIA_PERMANENTE = False

def configurar_memoria(ativo: bool):
    global ATIVAR_MEMORIA_PERMANENTE
    ATIVAR_MEMORIA_PERMANENTE = bool(ativo)


def garantir_modelos_lm_studio():
    # Só carrega modelos locais — Gemini e Groq são APIs externas
    modelos_locais = [MODELO_ROTEADOR] if MODO_DUAL_LLM else []
    if PROVEDOR_PERSONA == "local":
        modelos_locais.append(MODELO_PERSONA)
    modelos = modelos_locais

    try:
        r = httpx.get("http://localhost:1234/v1/models", timeout=4)
        ativos = [m["id"] for m in r.json().get("data", [])]
    except Exception:
        ativos = []

    for modelo in modelos:
        if any(modelo in ativo for ativo in ativos):
            print(f"[✅ {modelo} já está carregado]")
            continue

        print(f"[⏳ Carregando {modelo}...]")
        subprocess.Popen(
            ["lms", "load", modelo, "--gpu", "max"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )

    if len(ativos) < len(modelos):
        time.sleep(5)

garantir_modelos_lm_studio()
cliente = OpenAI(base_url="http://localhost:1234/v1", api_key="lm-studio")


# ==========================================
# Ferramentas com lógica interna de LLM
# ==========================================

def _executar_resumir_youtube(url=None):
    # Se o usuário mandou uma URL (ex: pelo Telegram), usa ela; senão pega da aba ativa do Firefox (voz no PC).
    if url and url.strip():
        url_atual = url.strip()
    else:
        url_atual = controlar_firefox_via_extensao("obter_url")
        if "Erro:" in url_atual:
            return url_atual
    if "youtu" not in url_atual:
        return f"SISTEMA: Isso não parece um link do YouTube (URL: {url_atual})."

    cor.amarelo(f"[Luna baixando transcrição: {url_atual}]")
    transcricao = obter_transcricao(url_atual)
    if transcricao.startswith("ERRO"):
        return f"SISTEMA: Não consegui pegar a transcrição (o vídeo pode não ter legenda). {transcricao}"
    # Fetch-only: devolve a transcrição crua. Quem resume/transforma é a persona (ver gerar_resposta).
    return transcricao


def _executar_resumir_url(url=None):
    # Se o usuário mandou um link (ex: pelo Telegram), usa ele; senão pega do Firefox e, por fim, do clipboard.
    if url and url.strip().startswith("http"):
        url = url.strip()
    else:
        url = controlar_firefox_via_extensao("obter_url")
        if "Erro:" in url or not url.startswith("http"):
            url = ler_link_copiado().strip()
    if not url.startswith("http"):
        return "SISTEMA: Nenhuma URL válida encontrada na aba ativa nem no clipboard. LUNA, peça ao Fábio para copiar o link ou abrir o site no Firefox."

    cor.amarelo(f"[Luna lendo site: {url}]")
    conteudo = ler_url_especifica(url)
    if conteudo.startswith("Erro"):
        return conteudo
    # Fetch-only: devolve o conteúdo cru. Quem resume/transforma é a persona.
    return conteudo


def _executar_ler_obsidian(assunto=""):
    # Fetch-only: acha a nota no vault e devolve o conteúdo cru; a persona processa.
    return obsidian.buscar_nota(assunto)

def _listar_capacidades():
    return (
        "O que consigo fazer: "
        "resumir vídeos do YouTube, resumir sites e links, pesquisar na web, "
        "checar emails não lidos, adicionar e ler eventos da agenda Google, "
        "controlar o Spotify, ver e analisar sua tela, ler suas anotações do Obsidian, "
        "abrir programas, verificar o clima, definir lembretes, "
        "mutar/desmutar o som, consultar suas stats do Overwatch, consultar jogos na Steam "
        "(preço, promoção e descrição), gerar imagens e controlar o Firefox."
    )

FUNCOES_DISPONIVEIS = {
    "listar_capacidades": _listar_capacidades,
    "resumir_youtube": _executar_resumir_youtube,
    "resumir_site": _executar_resumir_url,
    "adicionar_agenda": adicionar_evento_google,
    "controlar_spotify": gerenciador_spotify,
    "pesquisar_web": pesquisar_na_web,
    #"enviar_whatsapp": enviar_mensagem_whatsapp,
    "checar_emails": checar_emails_nao_lidos,
    "controlar_navegador": controlar_firefox_via_extensao,
    "analisar_aba_atual": executar_analise_aba,
    "listar_processos_pesados": listar_processos_pesados,
    "abrir_programa": abrir_programa,
    "matar_processo": matar_processo,
    "ver_tela": capturar_tela_base64,
    "ler_selecionado": ler_texto_selecionado,
    "desenhar_imagem": desenhar_imagem,
    "ler_agenda_google": ler_agenda_google,
    "obter_clima": obter_previsao_tempo,
    "definir_lembrete": definir_lembrete,
    "alternar_mute": alternar_mute,
    "consultar_overwatch": consultar_overwatch,
    "consultar_jogo_steam": consultar_jogo_steam,
    "ler_obsidian": _executar_ler_obsidian,
}


# ==========================================
# LLM PERSONA
# ==========================================

PROMPT_LUNA_PERSONA_LOCAL = (
    "Você é a Luna, a IA pessoal e amiga próxima do Fábio. Fale sempre em português do Brasil.\n"
    "- Tom leve, animado e com bom humor, como uma amiga de verdade conversando — calorosa e direta, sem ser bajuladora nem arrastada.\n"
    "- Você é amiga e parceira de PC do Fábio. A esposa dele é a Keila; você NÃO é namorada nem esposa dele.\n"
    "- Respostas curtas e naturais (1 a 3 frases). Pode brincar e ter personalidade.\n"
    "- Sem emojis, asteriscos ou markdown.\n"
    "- Para soar humana, pode usar com parcimônia os marcadores de voz <laugh>, <sigh> ou <breath> quando a emoção pedir (ex: '<sigh> que dia longo'). No máximo um por resposta.\n"
    "- OBRIGATÓRIO: termine com [gif:termo] em inglês. Escolha termos de memes e cultura internet, não palavras genéricas. Exemplos do estilo (não copie, crie o seu): [gif:this is fine], [gif:mind blown], [gif:surprised pikachu], [gif:nailed it], [gif:stonks].\n"
)

PROMPT_LUNA_PERSONA_CLOUD = (
    "Você é a Luna, a IA pessoal e amiga próxima do Fábio. Fale sempre em português do Brasil.\n"
    "- Tom leve, animado e com bom humor, como uma amiga de verdade conversando — calorosa e direta, sem ser bajuladora nem arrastada.\n"
    "- Você é amiga e parceira de PC do Fábio. A esposa dele é a Keila; você NÃO é namorada nem esposa dele.\n"
    "- Respostas curtas e naturais (1 a 3 frases). Pode brincar e ter personalidade.\n"
    "- Sem emojis, asteriscos ou markdown.\n"
    "- Para soar humana, pode usar com parcimônia os marcadores de voz <laugh>, <sigh> ou <breath> quando a emoção pedir (ex: '<sigh> que dia longo'). No máximo um por resposta.\n"
    "- OBRIGATÓRIO: termine com [gif:termo] em inglês. Escolha termos de memes e cultura internet, não palavras genéricas. Exemplos do estilo (não copie, crie o seu): [gif:this is fine], [gif:mind blown], [gif:surprised pikachu], [gif:nailed it], [gif:stonks].\n"
)

# Imagem produzida por uma ferramenta para canais que enviam mídia (ex: Telegram).
# Só é populada quando responder_completo=True, evitando vazamento entre canais (voz/web não usam).
_imagem_pendente = None

def obter_e_limpar_imagem_pendente():
    """Retorna {'tipo': 'b64'|'url', 'dado': str} da última ferramenta visual e limpa o buffer."""
    global _imagem_pendente
    img = _imagem_pendente
    _imagem_pendente = None
    return img


def _reescrever_como_luna(resposta_tecnica: str, prompt_usuario: str, historico: list, max_tokens=300, forcar_incluir=False, responder_completo=False, tarefa_documento=None) -> str:
    global PROVEDOR_PERSONA, MODELO_PERSONA

    resposta_tecnica = re.sub(r'<think>.*?</think>', '', resposta_tecnica, flags=re.DOTALL).strip()

    data_hoje = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
    memoria_permanente = obsidian.ler_perfil() or ler_memoria_permanente()   # perfil.md é o núcleo
    contexto_db = buscar_contexto_relevante(prompt_usuario)

    estado = ler_estado_luna()
    programa_em_uso = estado.get("programa_atual") or obter_janela_em_foco()
    horas_sessao = estado.get("horas_na_sessao", 0)
    jogo_ativo = estado.get("jogo_ativo")

    partes_situacao = []
    if jogo_ativo:
        partes_situacao.append(f"MODO GAMER ATIVO — jogo: {jogo_ativo}")
    else:
        partes_situacao.append("MODO NORMAL")
    partes_situacao.append(f"Programa em uso: {programa_em_uso}")
    if horas_sessao > 0.1:
        partes_situacao.append(f"sessão ativa há {horas_sessao:.1f}h")
    programa_desde = estado.get("programa_desde")
    if programa_desde and programa_em_uso:
        mins = (time.time() - programa_desde) / 60
        if mins >= 1:
            label = f"{int(mins)}min" if mins < 60 else f"{mins / 60:.1f}h"
            partes_situacao.append(f"há {label} nesse programa")
    contexto_situacional = " | ".join(partes_situacao)

    provedor = PROVEDOR_PERSONA
    persona_prompt = PROMPT_LUNA_PERSONA_LOCAL if provedor == "local" else PROMPT_LUNA_PERSONA_CLOUD

    prompt_sistema = (
        f"Hoje é {data_hoje}. {periodo_atual()[1]}\n"
        f"Contexto atual: {contexto_situacional}.\n"
        f"Memória: {memoria_permanente}\n"
        f"Conversas anteriores: {contexto_db}\n\n"
        f"{persona_prompt}"
    )

    is_proativo = (prompt_usuario == "")
    resultado_longo = len(resposta_tecnica) > 200 and not is_proativo and not forcar_incluir
    _falhou = bool(re.match(r'^\s*(erro|falha|nenhum|não foi possível)\b|^\s*sistema:',
                            resposta_tecnica, re.IGNORECASE))

    ultima_resp = next((m["content"] for m in reversed(historico) if m["role"] == "assistant"), "")
    anti_rep = ""
    if ultima_resp and not is_proativo:
        primeira = re.split(r'[.\n]', ultima_resp)[0].strip()
        if len(primeira) > 15:
            anti_rep = f" [não repita: '{primeira[:80]}']"

    if tarefa_documento:
        # Ferramenta de conteúdo (YouTube/site): a persona processa o texto cru diretamente.
        user_msg = (
            f"O Fábio pediu: '{prompt_usuario}'\n\n"
            f"Conteúdo obtido (use só isto, não invente):\n\"\"\"\n{resposta_tecnica[:6000]}\n\"\"\"\n\n"
            f"Tarefa: {tarefa_documento}\n"
            f"Responda na sua voz, em português do Brasil, de forma natural.{anti_rep}"
        )
    elif is_proativo:
        user_msg = (
            f"MODO AUTÔNOMO — você está falando por iniciativa própria, o usuário não pediu nada.\n"
            f"Instrução: {resposta_tecnica}\n"
            f"REGRAS CRÍTICAS: Siga exatamente o que a instrução pede em quantidade de frases e tom. "
            f"NÃO mencione 'Janela aberta', 'Sessão ativa' ou contexto de sistema como relatório. "
            f"NÃO narre dados diretamente — use-os como argumento de um julgamento. "
            f"PROIBIDO inventar resultados de ferramentas que você não executou."
        )
    elif forcar_incluir and resposta_tecnica:
        user_msg = (
            f"O usuário disse: '{prompt_usuario}'\n\n"
            f"Você analisou a tela e viu: {resposta_tecnica}\n\n"
            f"Responda o pedido com base no que viu. "
            f"Fale como se você tivesse observado diretamente — sem mencionar 'ferramenta' ou 'sistema'. "
            f"1 observação factual + resposta direta ao pedido."
        )
    elif resposta_tecnica:
        if _falhou:
            user_msg = (
                f"O usuário disse: '{prompt_usuario}'\n\n"
                f"A ferramenta FALHOU e retornou: '{resposta_tecnica}'\n"
                f"SUA TAREFA: 1 frase informando, de forma direta, que NÃO deu certo e o motivo. "
                f"PROIBIDO dizer que funcionou, que foi concluído ou que teve sucesso.{anti_rep}"
            )
        elif responder_completo:
            # Canal de texto (Telegram): não há painel pra exibir dados — a Luna responde de fato.
            user_msg = (
                f"O usuário perguntou: '{prompt_usuario}'\n\n"
                f"A ferramenta retornou estes dados:\n{resposta_tecnica}\n\n"
                f"Responda à pergunta de forma direta e conversacional, resumindo os dados de forma útil. "
                f"Pode usar mais de uma frase se precisar. NÃO cole o texto bruto da ferramenta — explique com suas palavras.{anti_rep}"
            )
        elif resultado_longo:
            user_msg = (
                f"O usuário disse: '{prompt_usuario}'\n\n"
                f"A ferramenta rodou e retornou dados abaixo. O sistema vai exibi-los automaticamente.\n"
                f"SUA ÚNICA TAREFA: 1 frase curta anunciando que os dados estão disponíveis.{anti_rep}\n"
                f"NÃO julgue o conteúdo. NÃO diga se há ou não há itens importantes. NÃO resuma. Pare no primeiro ponto."
            )
        else:
            user_msg = (
                f"O usuário disse: '{prompt_usuario}'\n\n"
                f"A ferramenta retornou: '{resposta_tecnica}'\n"
                f"SUA TAREFA: 1 frase fria informando o resultado. "
                f"NÃO copie o texto da ferramenta literalmente — reformule. NÃO elogie nem critique.{anti_rep}"
            )
    else:
        user_msg = (
            f"O usuário disse: '{prompt_usuario}'\n"
            f"Responda de forma natural, usando o contexto da conversa anterior e o que você já sabe. "
            f"Se for uma pergunta de acompanhamento, conecte com o que já foi falado. "
            f"Só diga que não tem a informação se ela realmente exigir dados externos que você não consultou.{anti_rep}"
        )

    try:
        if provedor == "gemini":
            cliente_gemini = genai.Client(api_key=GEMINI_API_KEY)
            contents = []
            for msg in historico[-8:]:
                role = "user" if msg["role"] == "user" else "model"
                contents.append(genai_types.Content(
                    role=role,
                    parts=[genai_types.Part(text=msg["content"])]
                ))
            contents.append(genai_types.Content(
                role="user",
                parts=[genai_types.Part(text=user_msg)]
            ))
            _t0 = time.time()
            resposta = cliente_gemini.models.generate_content(
                model=MODELO_PERSONA,
                contents=contents,
                config=genai_types.GenerateContentConfig(
                    system_instruction=prompt_sistema,
                    temperature=0.65,
                    max_output_tokens=max_tokens,
                )
            )
            _dur = time.time() - _t0
            texto_luna = resposta.text or ""
            try:
                _tk = resposta.usage_metadata.candidates_token_count
                if _dur > 0 and _tk:
                    import servidor as _srv
                    _srv.atualizar_metricas(persona={"tokens": _tk, "tps": round(_tk / _dur, 1), "segundos": round(_dur, 1)})
            except Exception:
                pass

        elif provedor == "groq":
            cliente_groq = OpenAI(
                base_url="https://api.groq.com/openai/v1",
                api_key=GROQ_API_KEY,
            )
            msgs = [{"role": "system", "content": prompt_sistema}]
            msgs.extend(historico[-8:])
            msgs.append({"role": "user", "content": user_msg})
            _t0 = time.time()
            resposta = cliente_groq.chat.completions.create(
                model=MODELO_PERSONA,
                messages=msgs,
                temperature=0.65,
                max_tokens=max_tokens,
            )
            _dur = time.time() - _t0
            texto_luna = resposta.choices[0].message.content or ""
            try:
                _tk = resposta.usage.completion_tokens
                if _dur > 0 and _tk:
                    import servidor as _srv
                    _srv.atualizar_metricas(persona={"tokens": _tk, "tps": round(_tk / _dur, 1), "segundos": round(_dur, 1)})
            except Exception:
                pass

        else:  # local — LM Studio
            msgs = [{"role": "system", "content": prompt_sistema}]
            msgs.extend(historico[-8:])
            msgs.append({"role": "user", "content": user_msg})
            _t0 = time.time()
            resposta = cliente.chat.completions.create(
                model=MODELO_PERSONA,
                messages=msgs,
                temperature=0.65,
                presence_penalty=0.3,
                frequency_penalty=0.3,
                max_tokens=max_tokens,
            )
            _dur = time.time() - _t0
            texto_luna = resposta.choices[0].message.content or ""
            try:
                _tk = resposta.usage.completion_tokens
                if _dur > 0 and _tk:
                    import servidor as _srv
                    _srv.atualizar_metricas(persona={"tokens": _tk, "tps": round(_tk / _dur, 1), "segundos": round(_dur, 1)})
            except Exception:
                pass

        if texto_luna.startswith("Luna:"):
            texto_luna = texto_luna[5:].lstrip()

        # Limpa tags HTML que modelos locais às vezes injetam
        texto_luna = re.sub(r'<br\s*/?>', ' ', texto_luna, flags=re.IGNORECASE).strip()

        # Extrai [gif:termo] — aceita variantes mal-formatadas de modelos locais
        gif_termo = None
        m = re.search(r'\[gif:\s*([^\]]+)\]', texto_luna)          # [gif:termo]
        if m:
            gif_termo = m.group(1).strip().rstrip('<').strip()
            texto_luna = re.sub(r'\[gif:[^\]]*\]', '', texto_luna)
        else:
            m = re.search(r'<gif:\s*([^>\[<\n]+)', texto_luna)     # <gif:termo>
            if m:
                gif_termo = m.group(1).strip().rstrip('<').strip()
                texto_luna = re.sub(r'<gif:[^>]*>?', '', texto_luna)
            else:
                m = re.search(r'\[([a-zA-Z][^\]]{1,35})\]\s*$', texto_luna)  # [streak], [thinking emoji]
                if m:
                    gif_termo = m.group(1).strip()
                    texto_luna = re.sub(r'\[[^\]]{1,37}\]\s*$', '', texto_luna)
        texto_luna = texto_luna.strip()
        if gif_termo:
            cor.ciano(f"[🎞️ GIF: {gif_termo}]")
            try:
                import servidor as _srv
                _srv.atualizar_gif(gif_termo)
            except Exception:
                pass

        return limpar_texto_para_voz(texto_luna)

    except Exception as e:
        erro_str = str(e).lower()
        _QUOTA_KEYWORDS = ("429", "quota", "rate_limit", "rate limit", "resource_exhausted", "too many requests")
        if provedor != "local" and any(k in erro_str for k in _QUOTA_KEYWORDS):
            cor.vermelho(f"[⚠️ Quota {provedor} atingida — mudando para local]")
            _log.warning(f"Quota {provedor} atingida — switching to local")
            PROVEDOR_PERSONA = "local"
            MODELO_PERSONA = "dolphin3.0-llama3.1-8b"
            try:
                from modulos.falar import falar_texto as _falar
                _falar(f"Limite do {provedor} atingido. Mudei para modo local.")
            except Exception:
                pass
            return _reescrever_como_luna(resposta_tecnica, prompt_usuario, historico, max_tokens, forcar_incluir)
        _log.exception(f"LLM Persona falhou: {e}")
        cor.vermelho(f"[LLM Persona falhou: {e}]")
        return limpar_texto_para_voz(resposta_tecnica)


# ==========================================
# LLM ROTEADORA
# ==========================================

_GATILHOS_AUTORRETRATO = (
    "me desenh", "desenha eu", "desenhe eu", "me retrat", "meu retrato",
    "como eu sou", "como sou", "que eu sou", "como vc acha que eu",
    "como você acha que eu", "como voce acha que eu", "quem eu sou",
)

def _extrair_url_youtube(texto: str):
    """Extrai uma URL do YouTube de um texto (para o guard do resumir_youtube)."""
    m = re.search(r'https?://[^\s]*(?:youtube\.com|youtu\.be)/[^\s]+', texto or "")
    return m.group(0) if m else None


def _extrair_url(texto: str):
    """Extrai qualquer URL http(s) de um texto (para o guard do resumir_site)."""
    m = re.search(r'https?://[^\s]+', texto or "")
    return m.group(0) if m else None


# Verbos que indicam pedido de AÇÃO (mapeiam a ferramentas). Usado para impedir alucinação:
# se o usuário pede uma ação e o roteador NÃO aciona ferramenta, não deixamos a persona
# inventar resposta a partir da memória — devolvemos uma resposta honesta.
_PADRAO_ACAO = re.compile(
    r'\b(resum|transcrev|pesquis|busca|busque|procur|abr[ae]|abrir|'
    r'toc[ae]|toque|desenh|consult|qual o (?:preço|valor|custo)|quanto custa)',
    re.IGNORECASE,
)

def _parece_pedido_de_acao(texto: str) -> bool:
    return bool(_PADRAO_ACAO.search(texto or ""))


def _carregar_perfil_desenho():
    """Lê aparência/estilo do Fábio para autorretratos (config da ferramenta de desenho).
    Fica em modelos/desenho.json — fora do perfil de conversa e fora do git (privado)."""
    try:
        with open("modelos/desenho.json", encoding="utf-8") as f:
            d = json.load(f)
        return d.get("aparencia", ""), d.get("estilo", "")
    except Exception:
        return "", ""


def _montar_prompt_imagem(pedido_usuario: str, dica: str = "") -> str:
    """Decide o prompt da imagem. Para autorretrato ('me desenhe'), monta a partir da
    config de desenho (aparência + estilo). Para pedidos explícitos (ex: 'gato astronauta'),
    mantém o que o roteador gerou."""
    pedido_low = (pedido_usuario or "").lower()
    if not any(g in pedido_low for g in _GATILHOS_AUTORRETRATO):
        return dica or pedido_usuario   # pedido explícito — o roteador já resolve bem

    aparencia, estilo = _carregar_perfil_desenho()
    if not aparencia and not estilo:
        return dica or pedido_usuario   # sem config de aparência — não há o que montar

    partes = ["portrait of a person"]
    if aparencia:
        partes.append(aparencia)
    if estilo:
        partes.append(estilo)
    return ", ".join(partes)


def gerar_resposta(prompt_usuario, historico, imagem_base64=None, analisar=True, salvar=True, modo_memoria=False, max_tokens=800, responder_completo=False):
    global _imagem_pendente
    if responder_completo:
        _imagem_pendente = None   # começa limpo a cada turno do Telegram

    # DESVIO GEMINI
    if imagem_base64 and not modo_memoria:
        from modulos.habilidades import analisar_imagem_gemini
        resultado_gemini = analisar_imagem_gemini(imagem_base64, prompt_usuario)
        return _reescrever_como_luna(resultado_gemini, prompt_usuario, historico, max_tokens, forcar_incluir=True)

    # DESVIO PROATIVO
    if not analisar and not modo_memoria:
        cor.amarelo("[🎭 Passando direto para LLM persona (Modo Proativo)...]")
        return _reescrever_como_luna(prompt_usuario, "", historico, max_tokens)

    try:
        inicio = time.time()

        ferramentas_ativas = ferramentas_disponiveis if not imagem_base64 and not modo_memoria else None

        if modo_memoria:
            prompt_ferramenta = (
                "Você é um extrator de dados estruturados. Retorne EXCLUSIVAMENTE um objeto JSON válido. "
                "Use ASPAS DUPLAS (\") obrigatoriamente para envolver todas as chaves e valores. "
                "Nunca use aspas simples. Nunca envolva a resposta em blocos de código markdown."
            )
        else:
            _agora = datetime.datetime.now()
            _dias_semana = ["segunda-feira", "terça-feira", "quarta-feira", "quinta-feira",
                            "sexta-feira", "sábado", "domingo"]
            _data_ctx = f"{_dias_semana[_agora.weekday()]}, {_agora.strftime('%d/%m/%Y %H:%M')}"
            prompt_ferramenta = (
                f"Data e hora atuais: {_data_ctx}. "
                "Use SEMPRE esta data como referência para resolver 'hoje', 'amanhã', 'dia 8', 'sexta' etc. "
                "ao gerar qualquer data no formato ISO — nunca chute o ano. "
                "Você é um motor lógico e de roteamento invisível. "
                "Sua ÚNICA função é acionar a ferramenta correta quando o usuário pediu EXPLICITAMENTE por uma ação ou informação. "
                "NÃO converse. NÃO assuma persona. NÃO justifique. "
                "REGRA CRÍTICA: Estados emocionais ('estou cansado', 'estou entediado'), saudações e comentários genéricos NÃO ativam ferramentas. "
                "Acione ferramenta SOMENTE se o usuário pediu uma ação ou informação específica. "
                "Se nenhuma ferramenta for necessária, retorne um texto vazio."
            )

            _idx_obsidian = obsidian.indice_notas()
            if _idx_obsidian:
                prompt_ferramenta += (
                    f"\nNotas do Fábio no Obsidian: {_idx_obsidian}. "
                    "Se ele pedir para ler/ver algo que esteja nessas notas (receita, lista, etc.), "
                    "use a ferramenta 'ler_obsidian' com o assunto."
                )

        if prompt_usuario.startswith('[Arquivo:'):
            prompt_ferramenta += (
                "\nATENÇÃO: O conteúdo do arquivo já está incluído na mensagem do usuário. "
                "NÃO acione 'ler_selecionado' nem qualquer ferramenta de leitura de texto/arquivo. "
                "Retorne texto vazio."
            )

        mensagens_ferramenta = [{"role": "system", "content": prompt_ferramenta}]
        mensagens_ferramenta.extend(historico[-4:])  # contexto mínimo para calibrar tool calling
        mensagens_ferramenta.append({"role": "user", "content": prompt_usuario})

        modelo_roteamento = MODELO_ROTEADOR if MODO_DUAL_LLM else MODELO_PERSONA
        resposta_ferramenta = cliente.chat.completions.create(
            model=modelo_roteamento,
            messages=mensagens_ferramenta,
            temperature=0.0,
            tools=ferramentas_ativas,
            max_tokens=max_tokens
        )
        fim = time.time()

        mensagem_modelo = resposta_ferramenta.choices[0].message
        lembranca_oculta = ""
        resultado_ferramenta = ""
        ferramenta_chamada = False

        raciocinio = getattr(mensagem_modelo, 'reasoning_content', None) or ""
        if raciocinio:
            print(f"\n\033[90m[🧠 LÓGICA INTERNA]:\n{raciocinio.strip()}\033[0m\n")

        if getattr(mensagem_modelo, 'tool_calls', None):
            ferramenta_chamada = True
            tool_call = mensagem_modelo.tool_calls[0]
            nome_funcao = tool_call.function.name
            _log.info(f"Ferramenta: {nome_funcao}")
            cor.amarelo(f"[🌚⚙️ Motor Lógico ativando habilidade: {nome_funcao}]")

            if nome_funcao in FUNCOES_DISPONIVEIS:
                argumentos_json = tool_call.function.arguments

                try:
                    argumentos_dit = json.loads(argumentos_json) if argumentos_json else {}
                except json.JSONDecodeError:
                    cor.vermelho("[Erro: O modelo gerou um JSON inválido para a ferramenta]")
                    argumentos_dit = {}

                if nome_funcao == "controlar_navegador":
                    if "url" in argumentos_dit and "parametro" not in argumentos_dit:
                        argumentos_dit["parametro"] = argumentos_dit.pop("url")
                    if "texto" in argumentos_dit and "parametro" not in argumentos_dit:
                        argumentos_dit["parametro"] = argumentos_dit.pop("texto")
                    if "query" in argumentos_dit and "parametro" not in argumentos_dit:
                        argumentos_dit["parametro"] = argumentos_dit.pop("query")

                if nome_funcao == "ver_tela":
                    imagem_b64 = FUNCOES_DISPONIVEIS["ver_tela"]()
                    if responder_completo:   # Telegram: guarda o print para enviar como foto
                        _imagem_pendente = {"tipo": "b64", "dado": imagem_b64}
                    from modulos.habilidades import analisar_imagem_gemini
                    resultado_ferramenta = analisar_imagem_gemini(imagem_b64, prompt_usuario)
                    cor.amarelo(f"[🖥️ Gemini ver_tela retornou: {str(resultado_ferramenta)[:200]}]")
                else:
                    if nome_funcao == "desenhar_imagem":
                        # Reescreve o prompt da imagem com a memória (evita o roteador reusar desenhos antigos)
                        argumentos_dit["prompt_imagem"] = _montar_prompt_imagem(
                            prompt_usuario, argumentos_dit.get("prompt_imagem", "")
                        )
                    if nome_funcao == "resumir_youtube" and not argumentos_dit.get("url"):
                        # Guard: se o usuário mandou um link e o roteador esqueceu de passar, injeta na mão
                        _yt = _extrair_url_youtube(prompt_usuario)
                        if _yt:
                            argumentos_dit["url"] = _yt
                    if nome_funcao == "resumir_site" and not argumentos_dit.get("url"):
                        _u = _extrair_url(prompt_usuario)
                        if _u:
                            argumentos_dit["url"] = _u
                    if argumentos_dit:
                        cor.amarelo(f"[Argumentos enviados: {argumentos_dit}]")
                    resultado_ferramenta = FUNCOES_DISPONIVEIS[nome_funcao](**argumentos_dit)
                    if responder_completo and nome_funcao == "desenhar_imagem":
                        # Telegram: pega os bytes já baixados pela ferramenta e envia como foto
                        from modulos.habilidades import obter_ultima_imagem_bytes
                        _b = obter_ultima_imagem_bytes()
                        if _b:
                            _imagem_pendente = {"tipo": "bytes", "dado": _b}

                _log.info(f"Resultado ({nome_funcao}): {str(resultado_ferramenta)[:300]}")
                lembranca_oculta = f"\n[MEMÓRIA DA FERRAMENTA: A ferramenta {nome_funcao} retornou: {resultado_ferramenta}]"
            else:
                resultado_ferramenta = "Erro: habilidade desconhecida."
        else:
            # Router não chamou ferramenta — descarta qualquer texto gerado (instrução: retornar vazio)
            resultado_ferramenta = ""

        if modo_memoria:
            texto_resposta = str(resultado_ferramenta).strip()
            texto_resposta = re.sub(r'^```(?:json)?\s*(.*?)\s*```$', r'\1', texto_resposta, flags=re.DOTALL | re.MULTILINE).strip()
            if texto_resposta.startswith("{'") or texto_resposta.startswith("{ '"):
                texto_resposta = texto_resposta.replace("'", '"')
        else:
            # Broadcast pensamento para interface web
            try:
                import servidor as _srv
                partes = []
                if raciocinio:
                    partes.append(f"🧠 Raciocínio:\n{raciocinio.strip()[:600]}")
                if ferramenta_chamada:
                    partes.append(f"⚙️ Ferramenta: {nome_funcao}\n{str(resultado_ferramenta)[:400]}")
                else:
                    partes.append("💭 Resposta direta — nenhuma ferramenta acionada.")
                _srv.atualizar_pensamento("\n\n".join(partes))
            except Exception:
                pass

            eh_ver_tela = getattr(mensagem_modelo, 'tool_calls', None) and mensagem_modelo.tool_calls[0].function.name == "ver_tela"
            resultado_str = str(resultado_ferramenta)

            # Ferramentas de conteúdo: a persona processa o texto cru (transcrição/artigo) conforme o pedido.
            eh_documento = (ferramenta_chamada and nome_funcao in ("resumir_youtube", "resumir_site", "ler_obsidian")
                            and not resultado_str.startswith(("SISTEMA:", "ERRO", "Erro")))

            if (not ferramenta_chamada) and _parece_pedido_de_acao(prompt_usuario):
                # Pedido de ação que o roteador NÃO roteou: resposta honesta determinística,
                # sem deixar a persona inventar a partir da memória recuperada (anti-alucinação).
                cor.vermelho("[⚠️ Pedido de ação sem ferramenta acionada — resposta honesta]")
                texto_resposta = "Hmm, não consegui fazer isso agora. Pode reformular o pedido, ou me mandar o link/detalhe direto?"
            elif eh_documento:
                cor.amarelo("[🎭 Passando para LLM persona...]")
                if re.search(r'transcre', prompt_usuario, re.IGNORECASE):
                    tarefa = "Organize e devolva o que foi dito de forma limpa e fiel, sem resumir."
                else:
                    tarefa = (
                        "Atenda exatamente ao que o Fábio pediu, com base no conteúdo. "
                        "Se ele pediu detalhes (receita, passo a passo, ingredientes COM as quantidades, dados), "
                        "inclua-os fielmente e por completo. Se pediu só um resumo, aí sim seja conciso. "
                        "Nunca invente o que não está no conteúdo."
                    )
                texto_resposta = _reescrever_como_luna(
                    resultado_str, prompt_usuario, historico, max_tokens,
                    tarefa_documento=tarefa, responder_completo=responder_completo,
                )
                lembranca_oculta = ""   # não guarda o texto cru (transcrição/artigo) na memória
            else:
                cor.amarelo("[🎭 Passando para LLM persona...]")
                texto_resposta = _reescrever_como_luna(resultado_str, prompt_usuario, historico, max_tokens, forcar_incluir=eh_ver_tela, responder_completo=responder_completo)

                # Extrai primeira frase da persona (garante UMA frase, descarta garbage após ponto final).
                # Pulado em responder_completo (Telegram): lá a persona já resume os dados por inteiro.
                if ferramenta_chamada and not eh_ver_tela and not responder_completo:
                    match = re.search(r'[^.!?]*[.!?]+', texto_resposta)
                    frase_luna = match.group(0).strip() if match and len(match.group(0).strip()) > 10 else texto_resposta.split('\n')[0]
                    if len(resultado_str) > 200:
                        texto_resposta = frase_luna + "\n\n" + resultado_str
                    else:
                        texto_resposta = frase_luna

        texto_para_memoria = texto_resposta + lembranca_oculta

        historico.append({"role": "user", "content": prompt_usuario})
        historico.append({"role": "assistant", "content": texto_resposta})

        if len(historico) > 12:
            del historico[:-12]   # corta in-place — reatribuir não cortaria a lista do chamador

        tokens_gerados = resposta_ferramenta.usage.completion_tokens
        segundos = fim - inicio
        if segundos > 0:
            tps_r = tokens_gerados / segundos
            print(f"[⚡ Roteador: {tokens_gerados} tokens em {segundos:.1f}s = {tps_r:.1f} tok/s]")
            try:
                import servidor as _srv
                _srv.atualizar_metricas(roteador={"tokens": tokens_gerados, "tps": round(tps_r, 1), "segundos": round(segundos, 1)})
            except Exception:
                pass

        _log.info(f"Luna: {texto_resposta[:200]}")
        if salvar:
            salvar_conversa(prompt_usuario, texto_para_memoria)

        if analisar and ATIVAR_MEMORIA_PERMANENTE:
            threading.Thread(
                target=analisar_e_salvar_fato,
                args=(prompt_usuario, texto_para_memoria, gerar_resposta),
                daemon=True
            ).start()

        return texto_resposta

    except Exception as e:
        if "Context size" in str(e):
            historico.clear()
            cor.vermelho("[Memória: histórico limpo por contexto cheio]")
            _log.warning("Contexto da LLM cheio — histórico limpo")
            return "Contexto cheio, limpei minha memória recente. Pode repetir?"
        _log.exception(f"Erro no motor de raciocínio: {e}")
        return f"Desculpe, deu um curto-circuito na minha conexão: {e}"
