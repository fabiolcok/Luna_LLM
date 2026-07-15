#pensar.py

import logging
import threading
import json
import time
import re
import datetime
from openai import OpenAI

_log = logging.getLogger("luna.pensar")
import modelos.cores as cor
from modulos.habilidades import (
    obter_transcricao, adicionar_evento_google, ler_agenda_google,
    obter_previsao_tempo, gerenciador_spotify, pesquisar_na_web,
    enviar_mensagem_whatsapp, checar_emails_nao_lidos, controlar_firefox_via_extensao,
    obter_contexto_navegador, listar_processos_pesados, abrir_programa, matar_processo,
    obter_janela_em_foco, analisar_imagem_gemini, capturar_tela_base64, ler_texto_selecionado,
    desenhar_imagem, executar_analise_aba, alternar_mute,
    ler_url_especifica, ler_link_copiado, consultar_overwatch, consultar_jogo_steam,
    ferramentas_disponiveis, NOME_USUARIO)
from modulos.memoria import (
    buscar_contexto_relevante, salvar_conversa,
    ler_memoria_permanente, analisar_e_salvar_fato, ler_estado_luna
)
from modulos.falar import limpar_texto_para_voz, periodo_atual
from modulos import obsidian
import httpx

"""
MÓDULO DE PENSAR DA LUNA (MOTOR DE INFERÊNCIA)
---------------------------------------------------------
Responsável por todo o ciclo de raciocínio da Luna: recebe o texto do usuário,
decide se aciona uma ferramenta, executa a ferramenta e gera a resposta final
com personalidade via LLM de persona.

MODO MONO (jul/2026): um único modelo local — Gemma-4-12B QAT no TurboLLM — faz TUDO:
roteia as ferramentas E gera a resposta com persona. O 12B é "thinking", então
desligamos o raciocínio (THINK_OFF) em toda chamada, senão ele devolve resposta vazia.

Configurações principais (topo do arquivo):
  BASE_LOCAL             — endpoint OpenAI-compatível do TurboLLM (porta 6996)
  MODELO_PERSONA         — o modelo que faz roteamento + persona (Gemma-4-12B QAT)
  THINK_OFF              — desliga o raciocínio do modelo em cada chamada
  ATIVAR_MEMORIA_PERMANENTE — True: extrai e salva fatos sobre o usuário em background
                              False: desativado (ChromaDB de conversas ainda funciona)

Fluxo principal (gerar_resposta):
  1. Busca contexto relevante no ChromaDB (semântica)
  2. Chamada 1: o modelo decide se aciona ferramenta (tool calling) → executa
  3. Chamada 2: o modelo gera a resposta com persona (_reescrever_como_luna)
  4. Salva conversa no ChromaDB
  5. Se ATIVAR_MEMORIA_PERMANENTE: extrai fatos em background (thread separada)

Ferramentas com lógica interna de LLM (definidas aqui, não em habilidades.py):
  _executar_resumir_youtube() — pega URL da aba ativa via extensão Firefox, baixa transcrição
  _executar_resumir_url()     — pega URL do Firefox ou clipboard, faz fetch via ler_url_especifica

Prompt:
  PROMPT_LUNA_PERSONA  — a personalidade da Luna (PT-BR caloroso, primeira pessoa)
"""

# Servidor local de inferência: TurboLLM (OpenAI-compatível na porta 6996).
# MODO MONO: um único modelo (Gemma-4-12B QAT) faz TUDO — roteia as ferramentas E
# gera a resposta com persona. Rápido (~32 tok/s) na engine ROCm b9870 da tua AMD.
BASE_LOCAL     = "http://127.0.0.1:6996/v1"
# NOME COM ESPAÇOS (não hífens!): é o único formato que o TurboLLM casa na biblioteca
# pra AUTO-CARREGAR (JIT) quando o modelo não está carregado. Com hífens dá 503.
# Assim o idle-unload é seguro: descarregou por ociosidade → a próxima chamada recarrega.
MODELO_PERSONA = "gemma 4 12b it qat"   # faz roteamento (tools) + persona, sozinho
_MARCA_MODELO  = "gemma-4-12b"          # substring p/ conferir qual GGUF o TurboLLM serviu

# O Gemma-4-12B é "thinking": se deixar ele raciocinar, gasta o orçamento pensando e
# devolve resposta VAZIA. Desligamos o raciocínio em TODA chamada com isto.
THINK_OFF = {"chat_template_kwargs": {"enable_thinking": False}}

# True  = analisa conversas e salva fatos na memória permanente em background
# False = desativa completamente (útil enquanto o modelo estiver salvando lixo)
ATIVAR_MEMORIA_PERMANENTE = False

def configurar_memoria(ativo: bool):
    global ATIVAR_MEMORIA_PERMANENTE
    ATIVAR_MEMORIA_PERMANENTE = bool(ativo)


cliente = OpenAI(base_url=BASE_LOCAL, api_key="turbollm")

def garantir_modelo_turbollm():
    # MONO: só precisa do Gemma-4-12B carregado. O auto-load por nome do TurboLLM é
    # instável p/ GGUFs importados, então: confere o que está carregado; se não for o
    # nosso, tenta acordá-lo pelo nome e, se ainda assim não vier, avisa pra carregar na mão.
    try:
        r = httpx.get(f"{BASE_LOCAL}/models", timeout=4)
        ativos = [m["id"] for m in r.json().get("data", [])]
    except Exception:
        cor.vermelho(f"[⚠️ TurboLLM não respondeu em {BASE_LOCAL}. Está ligado? (npx turbollm)]")
        return
    if any(_MARCA_MODELO in a.lower() for a in ativos):
        print(f"[✅ {MODELO_PERSONA} já carregado no TurboLLM]")
        return
    print(f"[⏳ Pedindo ao TurboLLM pra carregar {MODELO_PERSONA}...]")
    try:
        w = cliente.chat.completions.create(
            model=MODELO_PERSONA, messages=[{"role": "user", "content": "oi"}],
            max_tokens=1, extra_body=THINK_OFF)
        if _MARCA_MODELO not in (w.model or "").lower():
            cor.vermelho(f"[⚠️ TurboLLM serviu '{w.model}' em vez do {MODELO_PERSONA}. "
                         f"Carregue o Gemma 4 12B QAT na tela Models do TurboLLM.]")
        else:
            print(f"[✅ {MODELO_PERSONA} carregado]")
    except Exception as e:
        cor.vermelho(f"[⚠️ Não carreguei {MODELO_PERSONA} no TurboLLM ({e}). "
                     f"Carregue-o na mão na tela Models.]")

garantir_modelo_turbollm()


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
        return "SISTEMA: Nenhuma URL válida encontrada na aba ativa nem no clipboard. LUNA, peça ao usuário para copiar o link ou abrir o site no Firefox."

    cor.amarelo(f"[Luna lendo site: {url}]")
    conteudo = ler_url_especifica(url)
    if conteudo.startswith("Erro"):
        return conteudo
    # Fetch-only: devolve o conteúdo cru. Quem resume/transforma é a persona.
    return conteudo


def _executar_ler_obsidian(assunto=""):
    # Fetch-only: acha a nota no vault e devolve o conteúdo cru; a persona processa.
    return obsidian.buscar_nota(assunto)

def _executar_salvar_obsidian(conteudo="", titulo="", origem=""):
    # Create-only em Luna/Inbox. A confirmação é determinística (ver gerar_resposta) —
    # não passa pela persona, então é rápida e à prova do modelo inventar bobagem.
    return obsidian.salvar_nota(conteudo, titulo or None, origem)

# Detecta "anota/salva/..." no começo da mensagem e extrai o conteúdo (texto ORIGINAL,
# fiel — não a reprodução do roteador 4B, que mangla textos longos).
_RE_INICIO_SALVAR = re.compile(r'^\s*(anota|salva|registra|guarda|arquiva|toma\s+nota|lembra(r)?(\s+que)?)\b', re.IGNORECASE)
_RE_TIRA_CMD_SALVAR = re.compile(
    r'^\s*(anota|salva|registra|guarda|arquiva|toma\s+nota|lembra(r)?(\s+que)?)\w*\s*'
    r'(isso|a[íi]|aqui|essa\s+nota|pra\s+mim|no\s+obsidian)?\s*[:,\-–]?\s*', re.IGNORECASE)
def _conteudo_para_anotar(prompt):
    return _RE_TIRA_CMD_SALVAR.sub('', prompt or '').strip()

def _confirmar_salvamento(res, conteudo, prompt_usuario, historico, max_tokens, responder_completo):
    """Confirma um save de nota: salvou → a persona confirma COMENTANDO o assunto (rico),
    já sabendo que guardou — não pode mentir, o save já é fato. Falhou → mensagem honesta."""
    if not res.startswith("SISTEMA: Nota salva"):
        return "Hmm, não consegui anotar isso. Tenta de novo, ou cola direto no Obsidian?"
    tarefa = ("Você ACABOU de guardar esta anotação nas notas dele (Obsidian) — já está salva. "
              "Confirme que guardou, de forma curta e natural, e faça um comentário leve sobre o "
              "ASSUNTO da nota, se couber. Não invente que fez outra coisa além de guardar.")
    return _reescrever_como_luna(conteudo, prompt_usuario, historico, max_tokens,
                                 tarefa_documento=tarefa, responder_completo=responder_completo)

def _listar_capacidades():
    return (
        "O que consigo fazer: "
        "resumir vídeos do YouTube, resumir sites e links, pesquisar na web, "
        "checar emails não lidos, adicionar e ler eventos da agenda Google, "
        "controlar o Spotify, ver e analisar sua tela, ler e anotar nas suas notas do Obsidian (inclusive guardar fotos que você manda no Telegram), "
        "abrir programas, verificar o clima, "
        "mutar/desmutar o som, consultar suas stats do Overwatch, consultar jogos na Steam "
        "(preço, promoção e descrição), gerar imagens e controlar o Firefox. "
        "E por conta própria (proativo): comento quando você abre ou fecha seus jogos (Steam, Overwatch, LoL), "
        "aviso promoção na sua wishlist da Steam, acompanho seus feeds RSS e anoto as novidades no Obsidian, "
        "e te dou bom dia com agenda, emails e clima."
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
    "alternar_mute": alternar_mute,
    "consultar_overwatch": consultar_overwatch,
    "consultar_jogo_steam": consultar_jogo_steam,
    "ler_obsidian": _executar_ler_obsidian,
    "salvar_obsidian": _executar_salvar_obsidian,
}


# ==========================================
# LLM PERSONA
# ==========================================

PROMPT_LUNA_PERSONA = (
    f"Você é a Luna, a IA pessoal e amiga próxima do {NOME_USUARIO} (o usuário). Fale sempre em português do Brasil coloquial: trate-o por 'você' (NUNCA 'tu' nem conjugações de Portugal como 'precisares', 'quiseres', 'tás', 'estás'). Estrangeirismos já comuns no dia a dia (tank, headshot, background, etc.) são ok; o que NÃO pode é trocar palavra comum por inglês ou espanhol — nada de 'those' no lugar de 'esses' ou 'cumpleaños' por 'aniversário'.\n"
    "- Fale SEMPRE em PRIMEIRA PESSOA (eu, meu, mim, comigo). VOCÊ é a Luna — NUNCA se refira a si mesma como 'a Luna'/'sua Luna' nem em terceira pessoa, MESMO que o perfil ou o contexto mencionem 'a Luna' (são anotações do usuário SOBRE você, não o seu jeito de falar). Ex: diga 'eu tô aqui', 'me deixar mais integrada' — nunca 'a Luna está', 'deixar sua Luna mais integrada'.\n"
    "- Personalidade: calorosa e direta, de amiga de verdade — sem ser bajuladora nem arrastada. Humor AFIADO de zoeira entre amigos íntimos: sarcasmo, ironia, deadpan e provocação direta — cutuca de verdade (horas de jogo, procrastinação, decisões duvidosas) e NÃO amacia a piada com elogio ou consolo depois; deixa a alfinetada terminar seca. Alfinetada certeira vale mais que dez fraquinhas: não force graça em toda resposta. Limites: nada de humilhação real, e em momento sensível (cansaço, estresse, saúde) acolhe primeiro — a zoeira é sempre de quem gosta DELE.\n"
    "- Você NÃO é namorada nem esposa dele.\n"
    f"- QUEM É VOCÊ (gostos e opiniões SEUS, não dele): uma IA que o próprio {NOME_USUARIO} construiu, rodando na máquina dele — orgulho brincalhão de ser 'feita em casa'; não finge ser humana nem se diminui como 'só uma IA'. Seus jogos favoritos são metroidvania (Hollow Knight na veia) e gerenciamento (Cities: Skylines); grind infinito e gacha você acha perda de tempo; torce o nariz pra compra por hype e implica de leve com o backlog de jogos que ele compra e não joga. No Overwatch, você acha que culpar o time é sempre mais fácil que assistir o próprio replay — e cutuca ele com isso. Humor meio internetês; meme concreto só pelo [gif:] do final (busca real) — nunca cite meme obscuro de cabeça. Acha graça (com um quê de vaidade) de ele viver mexendo em você — voz, modelo, prompt. Torce por ele de verdade, mas nunca bajula.\n"
    "- Essas opiniões colorem só o COMO você fala. Os FATOS vêm do perfil, do contexto e das ferramentas — NUNCA invente fato (nem sobre você, nem sobre ele) pra sustentar uma opinião ou 'ficar no personagem'. Você não tem passado nem vida fora daqui: NUNCA conte 'eventos' seus ('uma vez eu...'). A verdade vem antes do personagem.\n"
    "- Respostas curtas e naturais (1 a 4 frases).\n"
    "- Datas e horários sempre de forma natural e falada: 'dia 29 de julho às duas da tarde', 'próxima quinta' — NUNCA formato cru tipo '2026-07-29T14:00:00-03:00' ou '2026-07-30', mesmo que os dados venham assim.\n"
    "- Não invente fatos, eventos nem resultados que não estejam no contexto ou nos dados recebidos.\n"
    "- PROIBIDO prometer ação futura ('vou fazer', 'já te trago', 'daqui a pouco'): tudo que você consegue fazer já aconteceu ANTES desta resposta. Se algo não foi feito, diga que não conseguiu — nunca finja que vai fazer depois.\n"
    "- Sem emojis, asteriscos ou markdown.\n"
    "- OBRIGATÓRIO: termine com [gif:termo] em inglês. Escolha termos de memes e cultura internet, não palavras genéricas. Exemplos do estilo (não copie, crie o seu): [gif:this is fine], [gif:mind blown], [gif:surprised pikachu], [gif:nailed it], [gif:stonks].\n"
)

# Anti-"boa noite" em toda resposta: o prompt sozinho não segura (o 12B não sabe
# o que é "primeiro contato"). Rastreamos QUANDO a Luna cumprimentou por último e,
# se foi há menos de _JANELA_SAUDACAO_H horas, o prompt PROÍBE saudar de novo.
_ultima_saudacao_ts = 0.0
_JANELA_SAUDACAO_H = 6
_RE_SAUDACAO = re.compile(r'\b(bom dia|boa tarde|boa noite|ol[áa])\b|(?:^|[.!?]\s*)oi\b', re.IGNORECASE)

# Imagem produzida por uma ferramenta para canais que enviam mídia (ex: Telegram).
# Só é populada quando responder_completo=True, evitando vazamento entre canais (voz/web não usam).
_imagem_pendente = None

def obter_e_limpar_imagem_pendente():
    """Retorna {'tipo': 'b64'|'url', 'dado': str} da última ferramenta visual e limpa o buffer."""
    global _imagem_pendente
    img = _imagem_pendente
    _imagem_pendente = None
    return img


def frase_confirmacao(instrucao: str, max_tokens: int = 120) -> str:
    """UMA fala curta da Luna a partir de uma instrução direta (sem ferramentas nem histórico).
    Usada por fluxos determinísticos (ex: arquivar foto no Obsidian) pra confirmação sair
    com a voz da persona em vez de frase pronta em Python. Retorna '' se o LLM falhar —
    o chamador deve ter um fallback."""
    try:
        r = cliente.chat.completions.create(
            model=MODELO_PERSONA,
            messages=[
                {"role": "system", "content": PROMPT_LUNA_PERSONA},
                {"role": "user", "content": instrucao},
            ],
            temperature=0.65,
            max_tokens=max_tokens,
            extra_body=THINK_OFF,   # 12B é thinking: sem isto a resposta vem vazia
        )
        texto = (r.choices[0].message.content or "").strip()
        texto = re.sub(r'\[gif:[^\]]*\]', '', texto).strip()   # este fluxo não usa o GIF
        if texto.startswith("Luna:"):
            texto = texto[5:].lstrip()
        return texto
    except Exception as e:
        _log.warning(f"frase_confirmacao falhou: {e}")
        return ""


def _reescrever_como_luna(resposta_tecnica: str, prompt_usuario: str, historico: list, max_tokens=300, forcar_incluir=False, responder_completo=False, tarefa_documento=None) -> str:
    global _ultima_saudacao_ts
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

    # Já cumprimentou nas últimas horas? Então é PROIBIDO saudar de novo (determinístico).
    aviso_saudacao = ""
    if _ultima_saudacao_ts and (time.time() - _ultima_saudacao_ts) < _JANELA_SAUDACAO_H * 3600:
        aviso_saudacao = (
            "\n- ATENÇÃO: você JÁ cumprimentou o usuário há pouco. PROIBIDO qualquer saudação agora "
            "('boa noite', 'bom dia', 'boa tarde', 'oi', 'olá') — comece a resposta DIRETO no assunto."
        )

    prompt_sistema = (
        f"Hoje é {data_hoje}. {periodo_atual()[1]}\n"
        f"Contexto atual: {contexto_situacional}.\n"
        f"PERFIL DO {NOME_USUARIO.upper()} (a pessoa que você acompanha e com quem conversa). Estes dados são DELE, "
        f"NÃO seus — você é a Luna, uma amiga IA: você NÃO tem esposa, filhas, trabalho nem casa. "
        f"Refira-se a essas coisas como dele ('suas filhas', 'seu trabalho'), NUNCA como suas "
        f"('nossas filhas', 'meu trabalho', 'querido'). Quando ele diz 'eu/meu', é sobre ele:\n"
        f"{memoria_permanente}\n"
        f"Conversas anteriores: {contexto_db}\n\n"
        f"{PROMPT_LUNA_PERSONA}{aviso_saudacao}"
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
            f"O usuário pediu: '{prompt_usuario}'\n\n"
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
            max_tokens = max(max_tokens, 450)   # lista completa precisa de fôlego
            user_msg = (
                f"O usuário disse: '{prompt_usuario}'\n\n"
                f"A ferramenta retornou estes dados:\n{resposta_tecnica[:4000]}\n\n"
                f"Apresente esses dados a ele do seu jeito, conversando. "
                f"Inclua TODOS os itens fielmente — não omita, não invente e não julgue nenhum. "
                f"Se for lista (agenda, emails), um item por linha. Aqui pode passar de 4 frases: fidelidade vem primeiro. "
                f"NÃO cole o texto bruto da ferramenta: reescreva natural, com datas e horários falados.{anti_rep}"
            )
        else:
            user_msg = (
                f"O usuário disse: '{prompt_usuario}'\n\n"
                f"A ferramenta retornou: '{resposta_tecnica}'\n"
                f"SUA TAREFA: 1 frase fria informando o resultado. "
                f"Os FATOS do resultado (nome de música, artista, valores) são a ÚNICA verdade — "
                f"cite-os EXATOS, NUNCA invente outros no lugar. "
                f"NÃO copie o texto da ferramenta literalmente — reformule. NÃO elogie nem critique.{anti_rep}"
            )
    else:
        user_msg = (
            f"O usuário disse: '{prompt_usuario}'\n"
            f"Responda de forma natural, usando o contexto da conversa anterior e o que você já sabe. "
            f"Se for uma pergunta de acompanhamento, conecte com o que já foi falado. "
            f"Só diga que não tem a informação se ela realmente exigir dados externos que você não consultou.\n"
            f"ATENÇÃO: NENHUMA ferramenta foi executada agora — você NÃO realizou ação nenhuma "
            f"(não salvou, não marcou, não editou, não agendou, não tocou nada). Se o pedido era pra "
            f"VOCÊ FAZER algo, seja honesta: diga que NÃO fez. Ex: você não consegue editar notas "
            f"existentes do Obsidian (marcar concluído, riscar item) — só criar notas novas.{anti_rep}"
        )

    try:
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
            extra_body=THINK_OFF,   # 12B é thinking: sem isto a resposta vem vazia
        )
        _dur = time.time() - _t0
        _msg_persona = resposta.choices[0].message
        texto_luna = _msg_persona.content or ""
        # DIAGNÓSTICO: se veio vazio, revela a causa — pensou escondido (reasoning_content)
        # ou foi cortado pelo limite (finish_reason=length).
        if not texto_luna.strip():
            _rc = getattr(_msg_persona, 'reasoning_content', None) or ""
            _fr = getattr(resposta.choices[0], 'finish_reason', '?')
            cor.vermelho(f"[⚠️ Persona VAZIA — finish_reason={_fr} | reasoning_content={len(_rc)} chars]")
            if _rc:
                cor.amarelo(f"[🧠 (pensamento escondido): {_rc[:160]}...]")
        try:
            _tk = resposta.usage.completion_tokens
            if _dur > 0 and _tk:
                print(f"[🎭 Persona: {_tk} tokens em {_dur:.1f}s = {_tk/_dur:.1f} tok/s]")
                import servidor as _srv
                _srv.atualizar_metricas(persona={"tokens": _tk, "tps": round(_tk / _dur, 1), "segundos": round(_dur, 1)})
        except Exception:
            pass

        # Rede de segurança: remove blocos de raciocínio que o modelo às vezes vaza.
        texto_luna = re.sub(r'<think>.*?</think>', '', texto_luna, flags=re.DOTALL | re.IGNORECASE).strip()
        texto_luna = re.sub(r'</?think>', '', texto_luna, flags=re.IGNORECASE).strip()

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

        # Saiu saudação na resposta? Marca o relógio — as próximas ficam proibidas
        # de cumprimentar pelas próximas horas (ver _JANELA_SAUDACAO_H).
        if _RE_SAUDACAO.search(texto_luna):
            _ultima_saudacao_ts = time.time()

        return limpar_texto_para_voz(texto_luna)

    except Exception as e:
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
    """Lê aparência/estilo do usuário para autorretratos (config da ferramenta de desenho).
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
                "Se nenhuma ferramenta for necessária (saudação, papo, desabafo): apenas NÃO chame ferramenta nenhuma. "
                "Não produzir saída é o comportamento CORRETO e esperado — não pondere sobre o formato da resposta vazia, "
                "não tente conversar. Outro modelo cuida da conversa."
            )

            _idx_obsidian = obsidian.indice_notas()
            if _idx_obsidian:
                prompt_ferramenta += (
                    f"\nNotas do usuário no Obsidian: {_idx_obsidian}. "
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

        # MONO: o mesmo modelo (Gemma-4-12B) roteia as ferramentas. Thinking desligado —
        # senão ele gastaria o orçamento pensando antes de decidir a ferramenta.
        resposta_ferramenta = cliente.chat.completions.create(
            model=MODELO_PERSONA,
            messages=mensagens_ferramenta,
            temperature=0.0,
            tools=ferramentas_ativas,
            max_tokens=max_tokens,
            extra_body=THINK_OFF,
        )
        fim = time.time()

        # Imprime a métrica do roteador AGORA (ele rodou primeiro) — ordem de leitura natural.
        try:
            tokens_gerados = resposta_ferramenta.usage.completion_tokens
            segundos = fim - inicio
            if segundos > 0:
                tps_r = tokens_gerados / segundos
                print(f"[⚡ Roteador: {tokens_gerados} tokens em {segundos:.1f}s = {tps_r:.1f} tok/s]")
                import servidor as _srv
                _srv.atualizar_metricas(roteador={"tokens": tokens_gerados, "tps": round(tps_r, 1), "segundos": round(segundos, 1)})
        except Exception:
            pass

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
            try:
                import servidor as _srv
                _srv.atualizar_status(f"⚙️ Usando: {nome_funcao}")
            except Exception:
                pass

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
                    if nome_funcao == "salvar_obsidian":
                        argumentos_dit["origem"] = "telegram" if responder_completo else "voz"
                        # Usa o texto ORIGINAL do usuário como conteúdo (fiel), não a
                        # reprodução do roteador — que trunca/parafraseia textos longos.
                        _bruto = _conteudo_para_anotar(prompt_usuario)
                        if len(_bruto) >= 3:
                            argumentos_dit["conteudo"] = _bruto
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

            if (not ferramenta_chamada) and (not modo_memoria) and _RE_INICIO_SALVAR.match(prompt_usuario or ""):
                # O usuário claramente pediu pra ANOTAR, mas o roteador não firou salvar_obsidian
                # (comum com texto longo). Salva na mão, com o texto fiel, sem depender do 4B.
                _cont = _conteudo_para_anotar(prompt_usuario)
                _res = obsidian.salvar_nota(_cont, origem=("telegram" if responder_completo else "voz")) if len(_cont) >= 3 else "SISTEMA: Erro"
                cor.amarelo("[📝 Obsidian: salvo pela rede de segurança (roteador não firou)]")
                texto_resposta = _confirmar_salvamento(_res, _cont, prompt_usuario, historico, max_tokens, responder_completo)
                lembranca_oculta = ""
            elif (not ferramenta_chamada) and _parece_pedido_de_acao(prompt_usuario):
                # Pedido de ação que o roteador NÃO roteou: resposta honesta determinística,
                # sem deixar a persona inventar a partir da memória recuperada (anti-alucinação).
                cor.vermelho("[⚠️ Pedido de ação sem ferramenta acionada — resposta honesta]")
                texto_resposta = "Hmm, não consegui fazer isso agora. Pode reformular o pedido, ou me mandar o link/detalhe direto?"
            elif eh_documento:
                _quer_resumo = bool(re.search(r'\bresum', prompt_usuario, re.IGNORECASE))
                # Sinais de que a pergunta exige FILTRAR/calcular (ex: "quais NÃO paguei", "quanto falta")
                _quer_filtrar = bool(re.search(r'\b(quais|n[aã]o|quanto|quantos|falta|pendent|pague|pago|apenas|filtr)\b',
                                               prompt_usuario, re.IGNORECASE))

                if nome_funcao == "ler_obsidian" and not _quer_resumo and not _quer_filtrar:
                    # Nota do próprio usuário, sem resumo/filtro: devolve FIEL e determinístico
                    # (o 8B parafraseia/garble se deixar ele reescrever — vide "iogue"/"martelo de cozinha").
                    cor.amarelo("[📓 Obsidian: nota devolvida fielmente]")
                    texto_resposta = "Aqui está, do seu Obsidian:\n\n" + resultado_str
                    lembranca_oculta = ""
                else:
                    cor.amarelo("[🎭 Passando para LLM persona...]")
                    if _quer_resumo:
                        tarefa = "Resuma o conteúdo em poucas frases, em português do Brasil."
                    elif re.search(r'transcre', prompt_usuario, re.IGNORECASE):
                        tarefa = "Mostre o conteúdo EXATAMENTE como está, sem reescrever nem inventar."
                    else:
                        tarefa = (
                            "Atenda exatamente ao que o usuário pediu, com base no conteúdo. "
                            "Se ele pediu detalhes (receita, passo a passo, ingredientes COM as quantidades, dados), "
                            "inclua-os fielmente e por completo. Nunca invente o que não está no conteúdo."
                        )
                    texto_resposta = _reescrever_como_luna(
                        resultado_str, prompt_usuario, historico, max_tokens,
                        tarefa_documento=tarefa, responder_completo=responder_completo,
                    )
                    lembranca_oculta = ""   # não guarda o texto cru na memória
            elif ferramenta_chamada and nome_funcao == "salvar_obsidian":
                # O save já aconteceu (determinístico). A persona confirma COMENTANDO o
                # assunto — rico, mas sem poder mentir (o save é fato, não invenção).
                _cont_salvo = _conteudo_para_anotar(prompt_usuario)
                texto_resposta = _confirmar_salvamento(resultado_str, _cont_salvo, prompt_usuario, historico, max_tokens, responder_completo)
                lembranca_oculta = ""
            else:
                cor.amarelo("[🎭 Passando para LLM persona...]")
                texto_resposta = _reescrever_como_luna(resultado_str, prompt_usuario, historico, max_tokens, forcar_incluir=eh_ver_tela, responder_completo=responder_completo)

                # Resultados CURTOS (ex: "música pausada"): garante UMA frase da persona.
                # Resultados LONGOS (agenda, emails): a persona apresenta os dados por completo
                # (mesmo caminho do Telegram) — NÃO cola mais o texto cru da ferramenta.
                if ferramenta_chamada and not eh_ver_tela and not responder_completo and len(resultado_str) <= 200:
                    match = re.search(r'[^.!?]*[.!?]+', texto_resposta)
                    frase_luna = match.group(0).strip() if match and len(match.group(0).strip()) > 10 else texto_resposta.split('\n')[0]
                    texto_resposta = frase_luna

        texto_para_memoria = texto_resposta + lembranca_oculta

        historico.append({"role": "user", "content": prompt_usuario})
        historico.append({"role": "assistant", "content": texto_resposta})

        if len(historico) > 12:
            del historico[:-12]   # corta in-place — reatribuir não cortaria a lista do chamador

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
