# proativa.py
import json
import os
import time
import threading
import datetime
import random
import requests
import ctypes
from modulos.habilidades import checar_emails_nao_lidos, ler_agenda_google, obter_previsao_tempo, obter_janela_em_foco, controlar_firefox_via_extensao, NOME_USUARIO
from modulos.pensar import gerar_resposta
from modulos.falar import falar_texto
from modulos.memoria import carregar_vistos, salvar_vistos, atualizar_estado_luna
from modulos import obsidian
import modelos.cores as cor
import psutil
import re
import html

"""
MÓDULO DE ROTINAS PROATIVAS DA LUNA
---------------------------------------------------------
Tarefas autônomas executadas em background sem o usuário pedir,
baseadas em tempo, estado do sistema ou eventos detectados.

─────────────────────────────────────────────────────────
ARQUITETURA DO LOOP
─────────────────────────────────────────────────────────
_loop_proativo() — roda a cada 30 segundos em thread separada.

  Camada 1 — SEMPRE ativa (ignora suspensão e AFK):
    └─ _tarefa_monitorar_jogos(): detecta abertura/fechamento de jogos via psutil.

  Camada 2 — Ativa apenas se NÃO suspensa e AFK ≤ 5 min, e sem jogo aberto:
    └─ emails, agenda, pausa, clima, steam_wishlist, bom_dia.

Suspensão automática:
  Cada fala proativa chama registrar_tentativa(). Após MAX_TENTATIVAS (3) sem
  resposta do usuário, _suspensa = True e a Camada 2 é bloqueada.
  Resetado por: qualquer fala do usuário (registrar_interacao()) ou abertura de jogo.

Memória física (modelos/estado_proativo.json):
  Persiste entre reinicializações. Evita repetir bom_dia no mesmo dia.

Sensor AFK (obter_tempo_afk):
  Usa ctypes/WinAPI (GetLastInputInfo) para medir inatividade real de teclado e mouse.

─────────────────────────────────────────────────────────
INTEGRAÇÕES DE API
─────────────────────────────────────────────────────────
- OverFast API  (_buscar_dados_overwatch): perfil público do Overwatch —
    endosso, hero main, horas totais. Usado ao fechar Overwatch.exe.

- LCU API       (_buscar_dados_lol): API local do cliente do League of Legends
    (https://127.0.0.1:{porta} via lockfile). Lê última partida do histórico —
    vitória/derrota, campeão, KDA, CS, dano, duração.
    Funciona com: Normal, Ranked, ARAM e modos PvP temporários.
    NÃO funciona com: Prática de Ferreiro, tutoriais.
    Aguarda 15s após fechar League of Legends.exe antes de consultar.

- Steam API     (_pegar_wishlist / _pegar_preco): monitora a wishlist e alerta
    quando um desconto supera DESCONTO_MINIMO (padrão: 50%).

─────────────────────────────────────────────────────────
TAREFAS AUTÔNOMAS ATIVAS
─────────────────────────────────────────────────────────
- _tarefa_monitorar_jogos(): Overwatch, LoL e Deadlock via psutil.
    Ao abrir: briefing frio de sessão (rank/winrate via API) + reseta suspensão.
    Ao fechar: consulta API do jogo e faz comentário factual com os dados reais.
- _tarefa_checar_emails(): a cada 12h, fora do horário de silêncio (18h–09h).
- _tarefa_checar_agenda(): a cada 60 min. Avisa apenas se evento em menos de 30 min.
- _tarefa_lembrete_pausa(): a cada 90 min. Cobra pausa ergonômica.
- _tarefa_monitorar_clima(): a cada 20 min. Fala apenas se começou a chover agora.
- _tarefa_steam_wishlist(): a cada 24h. Avisa sobre promoções na wishlist.
- _tarefa_bom_dia(): 1x/dia entre 08h–10h59. Resume agenda + emails com comentário matinal.

─────────────────────────────────────────────────────────
CONTROLE DA THREAD
─────────────────────────────────────────────────────────
- iniciar_modo_proativo(): inicia a thread e sincroniza todos os timers (evita avalanche inicial).
- parar_modo_proativo(): encerra o loop com segurança.
"""



# ============================================================
# CONFIGURAÇÃO — ajuste os intervalos conforme sua preferência
# ============================================================


CONFIGURACAO = {
    "emails": {
        "ativo": True,
        "intervalo_minutos": 720,
        "horario_silencio": (18, 9),
    },
    "agenda": {
        "ativo": True,
        "intervalo_minutos": 60,
        "antecedencia_aviso_minutos": 30,
    },
    "lembrete_pausa": {
        "ativo": True,
        "intervalo_minutos": 150,
    },
    "Lista_Steam": {
        "ativo": True,
        "intervalo_horas": 24,
    },
    "bom_dia": {
        "ativo": True,
        "horario_falar": (8, 11),  # Vai falar entre 08:00 e 10:59
        "ultimo_dia_falado": None  # Guarda o dia do mês para resetar sozinho
    },
    "Radar_RSS": {
        "ativo": True,
        "intervalo_minutos": 30,
        "horario_silencio": (0, 7),   # não checa de madrugada
    },
    "Autoconhecimento": {
        "ativo": True,
        "intervalo_minutos": 240,     # ~a cada 4h — reflexão ocasional, não repetitiva
        "horario_silencio": (0, 8),
    },
    "Animes": {
        "ativo": True,
        "intervalo_minutos": 360,     # episódio é evento diário — checar ~4x/dia basta
        "horario_silencio": (0, 9),
    },
}

# Jogos para ser monitorados.
PROCESSOS_JOGOS = {
    "Overwatch.exe": "Overwatch",
    "League of Legends.exe": "League of Legends",
    "Deadlock.exe" : "Deadlock"
}

# Jogos Steam que o monitor proativo deve IGNORAR — ex: idle games que ficam
# SEMPRE abertos (não são "sessão de jogo"; senão a Luna comenta e ativa o
# "não perturbe" à toa). Casa por appid (confiável) OU por trecho do nome.
_STEAM_IGNORAR_APPIDS = {"3678970"}         # TBH: Task Bar Hero (idle)
_STEAM_IGNORAR_NOMES  = {"task bar hero"}   # reserva, caso o appid mude

def _steam_ignorado(appid, nome) -> bool:
    return bool(appid) and (
        str(appid) in _STEAM_IGNORAR_APPIDS
        or any(ig in (nome or "").lower() for ig in _STEAM_IGNORAR_NOMES)
    )

# Estado interno para não ficar repetindo a fala
ESTADO_JOGOS = {
    "Overwatch": False,
    "League of Legends": False,
    "Deadlock" :False
}

# Estado da sessão Steam GENÉRICA (qualquer jogo da biblioteca, sem API dedicada).
# Complementa ESTADO_JOGOS: os jogos com tratamento próprio ficam com aquele handler.
_STEAM_SESSAO = {
    "appid": None,        # appid do jogo aberto agora (None = nenhum)
    "nome": None,         # nome do jogo aberto agora
    "inicio": 0.0,        # timestamp de abertura da sessão
    "conq_inicio": None,  # (feitas, total) de conquistas na abertura — pra diferença no fim
}
_STEAM_JOGANDO_AGORA = False  # alimenta o "não perturbe" pra QUALQUER jogo Steam



STEAM_API_KEY    = os.getenv("STEAM_API_KEY", "")
STEAM_ID         = os.getenv("STEAM_ID", "")
DESCONTO_MINIMO  = 50

# ============================================================
# REGRAS DE PERSONA (Injetado nos prompts proativos)
# ============================================================
# Só o que é ESPECÍFICO do proativo: falar em 2ª pessoa e ser breve.
# Idioma, personalidade, sarcasmo e "amiga-não-esposa" já vêm do PROMPT_LUNA_PERSONA
# (pensar.py), aplicado como sistema em toda chamada — repetir aqui só duplicava/conflitava.
REGRA_PERSONA = (
    f"Fale DIRETAMENTE com o {NOME_USUARIO}, em SEGUNDA pessoa (você, seu, te). Mesmo que a instrução "
    "mencione 'o usuário' ou 'dele' (é só o contexto te informando), NUNCA fale dele em terceira "
    "pessoa: diga 'seus stats', 'você está em Gold' — nunca 'os stats dele'. "
    "Seja breve e natural: máximo 2 frases."
)
# ============================================================
# ESTADO GLOBAL
# ============================================================
_tentativas_sem_resposta = 0
MAX_TENTATIVAS = 3
_suspensa = False
_ultima_execucao = {}
_emails_vistos = set()
_compromissos_avisados = set()
_luna_ocupada = threading.Event()
_historico_proativo = []
_thread_rodando = False
_ultimo_clima = {"chuva": None}
_sessao_inicio: float = 0.0
_proativo_ativo = True
TAREFAS_ATIVAS = {
    "jogos": True, "emails": True, "agenda": True,
    "pausa": True, "clima": True, "bom_dia": True, "steam": True, "navegador": True,
    "radar_rss": True, "autoconhecimento": True, "steam_jogo": True, "animes": True,
    "memoria": True,
}

# Estado interno da tarefa de contexto de navegação
_nav_url_atual = ""
_nav_url_desde = 0.0
_nav_ultimo_comentario_url = ""

ARQUIVO_ESTADO_PROATIVO = "modelos/estado_proativo.json"

def configurar_proativo(ativo: bool):
    global _proativo_ativo
    _proativo_ativo = bool(ativo)

def configurar_tarefa(nome: str, ativo: bool):
    if nome in TAREFAS_ATIVAS:
        TAREFAS_ATIVAS[nome] = bool(ativo)

def registrar_tentativa():
    global _tentativas_sem_resposta, _suspensa
    _tentativas_sem_resposta += 1
    if _tentativas_sem_resposta >= MAX_TENTATIVAS:
        _suspensa = True

def registrar_interacao():
    global _tentativas_sem_resposta, _suspensa
    _tentativas_sem_resposta = 0
    _suspensa = False

def esta_suspensa():
    return _suspensa

def luna_esta_livre():
    return not _luna_ocupada.is_set()

def marcar_luna_ocupada(ocupada: bool):
    if ocupada:
        _luna_ocupada.set()
    else:
        _luna_ocupada.clear()

def _em_horario_silencio(inicio_h, fim_h):
    hora_atual = datetime.datetime.now().hour
    if inicio_h > fim_h:
        return hora_atual >= inicio_h or hora_atual < fim_h
    return inicio_h <= hora_atual < fim_h

def _passou_intervalo(chave, minutos):
    agora = time.time()
    ultima = _ultima_execucao.get(chave, 0)
    diferenca = agora - ultima
    if diferenca >= minutos * 60:
        _ultima_execucao[chave] = agora
        return True
    return False

# Histórico da conversa de voz (main.py registra a lista dele aqui). As falas
# proativas entram nele — senão a Luna avisa "tem 2 novidades", o usuário pergunta
# "quais são?" e ela não faz ideia do que falou (aconteceu, avaliação de 28/06).
_historico_principal = None

def registrar_historico_principal(lista):
    global _historico_principal
    _historico_principal = lista


def _falar_proativamente(texto_resposta) -> bool:
    """Fala o texto quando a Luna ficar livre. Retorna True SE falou de verdade —
    quem depende do aviso (ex: dedup da wishlist) só deve marcar 'avisado' com True."""
    if not texto_resposta or not str(texto_resposta).strip():
        return False
    timeout = time.time() + 300
    while not luna_esta_livre():
        if time.time() > timeout:
            return False
        time.sleep(3)
    try:
        import servidor as _srv
        _srv.atualizar_legenda(texto_resposta)
        _srv.atualizar_usuario("")
    except Exception:
        pass
    # Registra a fala na conversa principal pra follow-ups terem contexto
    if _historico_principal is not None:
        _historico_principal.append({"role": "assistant", "content": texto_resposta})
        if len(_historico_principal) > 12:
            del _historico_principal[:-12]
    falar_texto(texto_resposta)
    return True

# Abordagens sorteadas para o proativo não ficar repetitivo (variar=True)
_ABORDAGENS = [
    "um comentário curto e direto",
    "uma pergunta casual pro usuário",
    "uma curiosidade ou observação leve sobre o assunto",
    "uma provocação leve e bem-humorada (sem ofender)",
]
# Últimas falas proativas, para evitar repetir tema/palavras
_falas_recentes = []

def _gerar_fala_proativa(prompt_sistema, tarefa="", max_tokens=150, variar=True):
    global _historico_proativo

    cor.amarelo(f"[🌚 Proativo: {tarefa}]")
    try:
        import servidor as _srv
        _srv.atualizar_status(f"🌚 Proativo: {tarefa}")
    except Exception:
        pass

    if len(prompt_sistema) > 1500:
        prompt_sistema = prompt_sistema[:1500] + "... [texto cortado]"

    # Variedade + anti-repetição (adicionados após o corte, para nunca serem truncados)
    if variar:
        prompt_sistema += f"\nDesta vez, faça isso como {random.choice(_ABORDAGENS)}."
    if _falas_recentes:
        prompt_sistema += ("\nVocê já falou isto há pouco — NÃO repita o tema nem as mesmas palavras: "
                           + " / ".join(_falas_recentes[-3:]))

    try:
        resposta = gerar_resposta(
            prompt_sistema,
            _historico_proativo,
            analisar=False,
            salvar=False,
            max_tokens=max_tokens
        )
        _historico_proativo = []
        if resposta:
            _falas_recentes.append(resposta.strip()[:120])
            if len(_falas_recentes) > 5:
                _falas_recentes.pop(0)
        return resposta
    except Exception as e:
        cor.vermelho(f"[Erro na geração proativa: {e}]")
        _historico_proativo = []
        return None

def ler_estado_proativo():
    """Lê o arquivo de memória de curto prazo do disco."""
    if os.path.exists(ARQUIVO_ESTADO_PROATIVO):
        try:
            with open(ARQUIVO_ESTADO_PROATIVO, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            pass
    return {"ultimo_dia_bom_dia": None}

def salvar_estado_proativo(chave, valor):
    """Salva a informação no disco para sobreviver a reinicializações."""
    estado = ler_estado_proativo()
    estado[chave] = valor
    with open(ARQUIVO_ESTADO_PROATIVO, "w", encoding="utf-8") as f:
        json.dump(estado, f)

def obter_tempo_afk():
    """Retorna há quantos segundos o usuário não mexe no mouse ou teclado."""
    class LASTINPUTINFO(ctypes.Structure):
        _fields_ = [("cbSize", ctypes.c_uint), ("dwTime", ctypes.c_uint)]
        
    lii = LASTINPUTINFO()
    lii.cbSize = ctypes.sizeof(LASTINPUTINFO)
    
    # Chama a DLL nativa do Windows
    ctypes.windll.user32.GetLastInputInfo(ctypes.byref(lii))
    
    # Pega o tempo de atividade do sistema e subtrai o tempo do último input
    millis = ctypes.windll.kernel32.GetTickCount() - lii.dwTime
    return millis / 1000.0

# ============================================================
# INTEGRAÇÕES STEAM E WEB
# ============================================================
def _pegar_wishlist():
    url = f"https://api.steampowered.com/IWishlistService/GetWishlist/v1/?key={STEAM_API_KEY}&steamid={STEAM_ID}"
    try:
        resposta = requests.get(url, timeout=10)
        if resposta.status_code != 200: return []
        items = resposta.json().get("response", {}).get("items", [])
        return [str(item["appid"]) for item in items]
    except:
        return []

def _pegar_preco(appid):
    url = f"https://store.steampowered.com/api/appdetails?appids={appid}&cc=br&l=brazilian&filters=price_overview,basic"

    try:
        dados = requests.get(url, timeout=10).json()
        info = dados.get(str(appid), {})
        if not info.get("success"): return None
        data = info.get("data", {})
        preco_info = data.get("price_overview")
        if not preco_info: return None
        return {
            "appid": appid,
            "nome": data.get("name", f"AppID {appid}"),
            "desconto": preco_info.get("discount_percent", 0),
            "preco_original": preco_info.get("initial_formatted", ""),
            "preco_atual": preco_info.get("final_formatted", ""),
        }
    except:
        return None

# ------------------------------------------------------------
# STEAM AO VIVO — o que o usuário está jogando AGORA (genérico)
# ------------------------------------------------------------
def _steam_cliente_aberto():
    """True se o cliente Steam (steam.exe) está rodando. Checagem local barata:
    se o Steam nem está aberto, não há jogo Steam possível — poupa a chamada à API."""
    try:
        for p in psutil.process_iter(['name']):
            if (p.info.get('name') or '').lower() == 'steam.exe':
                return True
    except Exception:
        return True  # na dúvida, deixa a API decidir
    return False

def _steam_status_atual():
    """Pergunta pro Steam o que o usuário está jogando neste momento.
    Retorna (appid:str, nome:str) ou (None, None) se não estiver jogando."""
    if not STEAM_API_KEY or not STEAM_ID:
        return None, None
    url = (f"https://api.steampowered.com/ISteamUser/GetPlayerSummaries/v2/"
           f"?key={STEAM_API_KEY}&steamids={STEAM_ID}")
    try:
        r = requests.get(url, timeout=10)
        if r.status_code != 200:
            return None, None
        players = r.json().get("response", {}).get("players", [])
        if not players:
            return None, None
        p = players[0]
        nome = p.get("gameextrainfo")
        appid = p.get("gameid")
        if nome and appid:
            return str(appid), nome
        return None, None
    except Exception:
        return None, None

def _steam_conquistas(appid):
    """(feitas, total) de conquistas do jogo. None se o jogo não tem achievements
    ou os dados estão indisponíveis."""
    if not appid:
        return None
    url = (f"https://api.steampowered.com/ISteamUserStats/GetPlayerAchievements/v1/"
           f"?appid={appid}&key={STEAM_API_KEY}&steamid={STEAM_ID}")
    try:
        resp = requests.get(url, timeout=10).json().get("playerstats", {})
        if not resp.get("success"):
            return None
        achs = resp.get("achievements", [])
        if not achs:
            return None
        feitas = sum(1 for a in achs if a.get("achieved"))
        return feitas, len(achs)
    except Exception:
        return None

def _steam_horas(appid):
    """Horas totais nesse jogo (via jogos recentes). 0.0 se não encontrar."""
    if not appid:
        return 0.0
    url = (f"https://api.steampowered.com/IPlayerService/GetRecentlyPlayedGames/v1/"
           f"?key={STEAM_API_KEY}&steamid={STEAM_ID}")
    try:
        jogos = requests.get(url, timeout=10).json().get("response", {}).get("games", [])
        for g in jogos:
            if str(g.get("appid")) == str(appid):
                return round(g.get("playtime_forever", 0) / 60, 1)
    except Exception:
        pass
    return 0.0

# Palavras que denunciam parágrafo TÉCNICO/burocrático no "Sobre este jogo"
# (specs de PC, acessibilidade, requisitos) — nada disso serve pra Luna comentar.
# Palavras que denunciam parágrafo TÉCNICO/burocrático no "Sobre este jogo"
# (specs de PC, acessibilidade, requisitos) — nada disso serve pra Luna comentar.
_STEAM_DESC_LIXO = (
    "esta edição", "esta edicao", "requer", "compatível", "compativel", "compatibilidade",
    "dlss", "fsr", "xess", "directstorage", "hdr", "ultrawide", "widescreen", "conexão",
    "conexao", "dualsense", "troféu", "trofeu", "playstation", "mapeamento", "upscaling",
    "áudio descritivo", "audio descritivo", "resolução", "resolucao", "placa de vídeo",
)
# Parágrafo de marketing (prêmios/aclamação) — já vem na descrição curta; aqui queremos a HISTÓRIA.
_STEAM_DESC_MKT = ("prémio", "premio", "prêmio", "jogo do ano", "vencedor", "aclamad", "definitiva")

def _steam_premissa(html_about):
    """Pesca o parágrafo de HISTÓRIA do 'Sobre este jogo' (HTML cru da Steam).
    A premissa costuma ser o 1º parágrafo narrativo — pulando técnico e marketing."""
    if not html_about:
        return ""
    for p in re.findall(r"<p[^>]*>(.*?)</p>", html_about, re.DOTALL):
        t = html.unescape(re.sub(r"<[^>]+>", "", p)).strip()
        if len(t) < 150:                      # curto demais = título/bullet técnico
            continue
        low = t.lower()
        if any(x in low for x in _STEAM_DESC_LIXO):
            continue
        if any(x in low for x in _STEAM_DESC_MKT):
            continue
        return t[:450]                        # 1º parágrafo narrativo = a premissa
    return ""

def _steam_info_jogo(appid):
    """Material do jogo pra Luna comentar: gênero + descrição curta (prêmios/modos) +
    premissa da história (extraída limpa do 'Sobre este jogo'). '' se falhar."""
    if not appid:
        return ""
    # Sem filtro: precisamos de about_the_game (o 'basic' só traz a descrição curta).
    # l=brazilian → pt-BR (l=portuguese vem de Portugal, com conjugação que a persona proíbe).
    url = f"https://store.steampowered.com/api/appdetails?appids={appid}&cc=br&l=brazilian"
    try:
        dados = requests.get(url, timeout=10).json().get(str(appid), {})
        if not dados.get("success"):
            return ""
        data = dados.get("data", {})
        partes = []
        generos = ", ".join(g.get("description", "") for g in data.get("genres", []))
        if generos:
            partes.append(f"Gênero: {generos}.")
        desc = (data.get("short_description") or "").strip()
        if desc:
            partes.append(desc)
        historia = _steam_premissa(data.get("about_the_game", ""))
        if historia:
            partes.append(f"História: {historia}")
        return " ".join(partes)[:700]
    except Exception:
        return ""

# ============================================================
# APIS JOGOS
# ============================================================

def _buscar_dados_overwatch():
    """Busca o perfil completo do usuário e os heróis mais jogados na API do Overwatch."""
    battletag = os.getenv("OW_BATTLETAG", "")
    
    url_perfil = f"https://overfast-api.tekrop.fr/players/{battletag}/summary"
    url_status = f"https://overfast-api.tekrop.fr/players/{battletag}/stats/summary"
    
    try:
        resp_perfil = requests.get(url_perfil, timeout=10)
        if resp_perfil.status_code != 200:
            return "SISTEMA: Os servidores da Blizzard estão inalcançáveis no momento."

        perfil = resp_perfil.json()
        privacidade = perfil.get("privacy", "unknown")
        endorsement = perfil.get("endorsement", {}).get("level", "Desconhecido")
        titulo = perfil.get("title", "Nenhum")

        texto_stats = f"DADOS DA CONTA (Overwatch) - Nível de Endosso: {endorsement}. Título equipado: '{titulo}'. "

        if privacidade == "private":
            texto_stats += "O perfil está marcado como PRIVADO — horas de jogo e rankings não estão acessíveis."
            return texto_stats
            
        # 1. PEGAR OS RANKS COMPETITIVOS DO PC
        comp_data = perfil.get("competitive", {}).get("pc", {})
        if comp_data:
            ranks = []
            for role in ["tank", "damage", "support"]:
                if role in comp_data and comp_data[role]:
                    tier = comp_data[role].get("division", "Unranked").capitalize() # Ex: Gold, Silver
                    level = comp_data[role].get("tier", "") # Ex: 1, 2, 3
                    ranks.append(f"{role.capitalize()}: {tier} {level}")
            
            if ranks:
                texto_stats += f"Rankings Atuais no PC -> {', '.join(ranks)}. "
            else:
                texto_stats += "Sem ranking competitivo registrado nesta temporada. "
        
        # 2. PEGAR ESTATÍSTICAS GERAIS (KDA e WINRATE)
        resp_status = requests.get(url_status, timeout=10)
        if resp_status.status_code == 200:
            stats = resp_status.json()
            
            geral = stats.get("general", {})
            tempo_total_horas = int(geral.get("time_played", 0) / 3600)
            
            jogos_ganhos = geral.get("games_won", 0)
            jogos_perdidos = geral.get("games_lost", 0)
            winrate = geral.get("winrate", 0)
            
            eliminacoes = geral.get("eliminations", 0)
            mortes = geral.get("deaths", 0)
            
            texto_stats += f"Tempo total de jogo: {tempo_total_horas} horas. "
            texto_stats += f"Eficiência de partidas: {jogos_ganhos} vitórias contra {jogos_perdidos} derrotas (Taxa de vitória: {winrate}%). "
            if eliminacoes > 0 or mortes > 0:
                texto_stats += f"Eficiência em combate: {eliminacoes} eliminações e {mortes} mortes ao longo da carreira. "
            
            # 3. PEGAR O MAIN E A TAXA DE VITÓRIA DELE
            herois = stats.get("heroes", {})
            if herois:
                # O herói mais jogado
                heroi_main = max(herois, key=lambda k: herois[k].get("time_played", 0))
                horas_main = int(herois[heroi_main].get("time_played", 0) / 3600)
                winrate_main = herois[heroi_main].get("winrate", "Desconhecido")
                
                texto_stats += f"O personagem ('Main') mais jogado é {heroi_main.capitalize()}, com {horas_main} horas jogadas e taxa de vitória de {winrate_main}%. "
                
        return texto_stats
            
    except Exception as e:
        print(f"\n[⚠️ ALERTA DEBUG: Falha na API do Overwatch: {e}]\n")
        return "SISTEMA: Erro ao contatar a Blizzard. Não há dados."

def _buscar_dados_lol():
    """Busca dados da última partida via LCU (API local do cliente do LoL).
    O lockfile fica ativo enquanto o LeagueClient.exe estiver rodando —
    então pode ser consultado assim que League of Legends.exe fecha.
    """
    import base64
    try:
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    except Exception:
        pass

    caminhos_lockfile = [
        r"C:\Riot Games\League of Legends\lockfile",
        os.path.join(os.path.expanduser("~"), r"AppData\Local\Riot Games\League of Legends\lockfile"),
    ]
    lockfile = next((p for p in caminhos_lockfile if os.path.exists(p)), None)
    if not lockfile:
        return "ERRO_LOCKFILE"

    try:
        with open(lockfile, "r") as f:
            partes = f.read().strip().split(":")
        # Formato: LeagueClient:PID:PORT:PASSWORD:PROTOCOL
        porta, senha = partes[2], partes[3]
        base = f"https://127.0.0.1:{porta}"
        hdrs = {"Authorization": "Basic " + base64.b64encode(f"riot:{senha}".encode()).decode()}

        # Summoner atual
        resp_me = requests.get(f"{base}/lol-summoner/v1/current-summoner",
                               headers=hdrs, verify=False, timeout=5)
        if resp_me.status_code != 200:
            cor.vermelho(f"[LCU summoner: status={resp_me.status_code} | {resp_me.text[:200]}]")
            return "ERRO_LCU"
        dados_summoner = resp_me.json()
        puuid = dados_summoner.get("puuid", "")
        summoner_id = dados_summoner.get("summonerId", "")
        cor.amarelo(f"[LCU puuid: {puuid[:36]} | summonerId: {summoner_id}]")

        # Mapa de championId → nome via LCU local
        mapa_campeoes = {}
        resp_champs = requests.get(
            f"{base}/lol-game-data/assets/v1/champion-summary.json",
            headers=hdrs, verify=False, timeout=5
        )
        if resp_champs.status_code == 200:
            for c in resp_champs.json():
                mapa_campeoes[c.get("id")] = c.get("name", "?")

        # Última partida — endpoint atual usa /matches (não /games)
        jogos = []
        resp_hist = requests.get(
            f"{base}/lol-match-history/v1/products/lol/current-summoner/matches",
            headers=hdrs, verify=False, timeout=5
        )
        cor.amarelo(f"[LCU hist: status={resp_hist.status_code}]")
        if resp_hist.status_code == 200:
            raw = resp_hist.json()
            cor.amarelo(f"[LCU hist raw keys: {list(raw.keys())}]")
            # Tenta diferentes estruturas de resposta
            jogos = (raw.get("games", {}).get("games")
                     or raw.get("matches")
                     or raw.get("games")
                     or [])
        else:
            cor.vermelho(f"[LCU hist: {resp_hist.text[:300]}]")
            return "ERRO_HISTORICO"
        if not jogos:
            return "ERRO_SEM_JOGO"

        jogo = jogos[0]
        stats, campeao = {}, "?"

        for part in jogo.get("participants", []):
            if part.get("puuid") == puuid:
                stats = part.get("stats", {})
                champ_id = part.get("championId")
                campeao = (part.get("championName")
                           or mapa_campeoes.get(champ_id)
                           or (str(champ_id) if champ_id else "?"))
                break

        if not stats and jogo.get("participants"):
            part = jogo["participants"][0]
            stats = part.get("stats", {})
            champ_id = part.get("championId")
            campeao = (part.get("championName")
                       or mapa_campeoes.get(champ_id)
                       or (str(champ_id) if champ_id else "?"))

        vitoria = stats.get("win", False)
        k = stats.get("kills", 0)
        d = stats.get("deaths", 0)
        a = stats.get("assists", 0)
        cs = stats.get("totalMinionsKilled", 0) + stats.get("neutralMinionsKilled", 0)
        dano = stats.get("totalDamageDealtToChampions", 0)
        duracao = jogo.get("gameDuration", 0) // 60

        return (
            f"{'VITÓRIA' if vitoria else 'DERROTA'} com {campeao}. "
            f"KDA: {k}/{d}/{a}. CS: {cs}. "
            f"Dano causado: {dano:,}. Duração: {duracao} minutos."
        )

    except Exception as e:
        return f"ERRO: {e}"

def _buscar_dados_deadlock():
    """Busca última partida e stats agregados via deadlock-api.com (sem chave)."""
    steam_id = int(os.getenv("STEAM_ID", "0"))
    if steam_id <= 0:
        return "STEAM_ID não configurado."
    account_id = steam_id - 76561197960265728

    try:
        # Busca última partida com force_refetch para garantir dado fresco
        r_hist = requests.get(
            f"https://api.deadlock-api.com/v1/players/{account_id}/match-history",
            params={"force_refetch": "true"},
            timeout=15,
        )
        partidas = r_hist.json() if r_hist.status_code == 200 else []

        # Busca stats agregados por herói (winrate geral)
        r_stats = requests.get(
            "https://api.deadlock-api.com/v1/hero-stats",
            params={"account_ids": account_id},
            timeout=10,
        )
        hero_stats = r_stats.json() if r_stats.status_code == 200 else []

        # ── Resumo agregado ──
        total_partidas = sum(s.get("matches_played", 0) for s in hero_stats)
        total_vitorias = sum(s.get("wins", 0) for s in hero_stats)
        winrate_geral  = round(total_vitorias / total_partidas * 100) if total_partidas > 0 else None

        heroi_mais_jogado = None
        if hero_stats:
            top = max(hero_stats, key=lambda s: s.get("matches_played", 0))
            heroi_mais_jogado = f"herói ID {top['hero_id']} ({top['matches_played']} partidas, {round(top['wins']/top['matches_played']*100) if top['matches_played'] else 0}% winrate)"

        # ── Última partida ──
        if not partidas:
            partes = []
            if total_partidas:
                partes.append(f"Total de {total_partidas} partidas registradas")
            if winrate_geral is not None:
                partes.append(f"winrate geral {winrate_geral}%")
            if heroi_mais_jogado:
                partes.append(f"mais jogado: {heroi_mais_jogado}")
            return "Sem dados da última partida. " + (". ".join(partes) or "Histórico ainda não indexado.") + "."

        p       = partidas[0]
        vitoria = p.get("match_result") == p.get("player_team")
        k       = p.get("player_kills", 0)
        d       = p.get("player_deaths", 0)
        a       = p.get("player_assists", 0)
        heroi   = f"herói ID {p.get('hero_id', '?')}"
        duracao = round(p.get("match_duration_s", 0) / 60)
        net_worth = p.get("net_worth", 0)
        modo    = "Ranked" if p.get("match_mode") == 1 else "Unranked"

        resumo = (
            f"{'VITÓRIA' if vitoria else 'DERROTA'} ({modo}) com {heroi}. "
            f"KDA: {k}/{d}/{a}. Net worth: {net_worth:,}. Duração: {duracao} minutos."
        )
        if winrate_geral is not None:
            resumo += f" Winrate geral na conta: {winrate_geral}% em {total_partidas} partidas."
        return resumo

    except Exception as e:
        return f"ERRO_DE_CONEXAO: {e}"

# ============================================================
# TAREFAS PROATIVAS
# ============================================================

def _tarefa_checar_emails():
    cfg = CONFIGURACAO["emails"]
    if not cfg["ativo"] or _em_horario_silencio(*cfg["horario_silencio"]) or not _passou_intervalo("emails", cfg["intervalo_minutos"]): return
    try:
        resultado = checar_emails_nao_lidos()
        novos = [linha for linha in resultado.strip().split("\n") if linha and linha not in _emails_vistos]
        for n in novos: _emails_vistos.add(n)
        if not novos or "não há novos" in resultado.lower(): return
        prompt = f"O usuário tem {len(novos)} emails novos. Remetentes: {' | '.join(novos[:5])}. Avise-o. {REGRA_PERSONA}"
        _falar_proativamente(_gerar_fala_proativa(prompt, "checar_emails", variar=False))
        registrar_tentativa()
    except Exception as e: cor.vermelho(f"[Erro emails: {e}]")

def _tarefa_checar_agenda():
    cfg = CONFIGURACAO["agenda"]
    if not cfg["ativo"] or not _passou_intervalo("agenda", cfg["intervalo_minutos"]): return
    
    try:
        dados_agenda = ler_agenda_google()
        if not dados_agenda or "nenhum" in dados_agenda.lower(): return

        agora = datetime.datetime.now()
        limite_min = cfg['antecedencia_aviso_minutos']
        urgentes = []

        # Analisa linha a linha ("- Nome | data"). Distingue evento com hora de evento de dia inteiro.
        for linha in dados_agenda.splitlines():
            if "|" not in linha:
                continue
            nome, _, data_str = linha.partition("|")
            nome = nome.strip(" -\t")
            data_str = data_str.strip()

            m_hora = re.search(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}", data_str)
            if m_hora:
                # Evento com hora marcada: urgente só se faltar <= antecedência (ex: 30 min)
                try:
                    data_evento = datetime.datetime.strptime(m_hora.group()[:19], "%Y-%m-%dT%H:%M:%S")
                except ValueError:
                    continue
                minutos = (data_evento - agora).total_seconds() / 60
                if 0 <= minutos <= limite_min:
                    urgentes.append(f"{nome} (em {int(minutos)} min)")
            else:
                # Evento de dia inteiro (só data): urgente APENAS se for hoje
                m_dia = re.search(r"\d{4}-\d{2}-\d{2}", data_str)
                if not m_dia:
                    continue
                try:
                    dia_evento = datetime.datetime.strptime(m_dia.group(), "%Y-%m-%d").date()
                except ValueError:
                    continue
                if dia_evento == agora.date():
                    urgentes.append(f"{nome} (hoje)")

        # Silêncio absoluto se nada está realmente próximo
        if not urgentes:
            return

        prompt = (
            f"Estes compromissos estão próximos AGORA: {'; '.join(urgentes)}. "
            f"Avise o usuário de forma seca e direta, mencionando só esses. {REGRA_PERSONA}"
        )

        fala = _gerar_fala_proativa(prompt, "checar_agenda", variar=False)
        if fala:
            _falar_proativamente(fala)
            registrar_tentativa()

    except Exception as e:
        cor.vermelho(f"[Erro agenda: {e}]")

def _tarefa_lembrete_pausa():
    cfg = CONFIGURACAO["lembrete_pausa"]
    if not cfg["ativo"] or _em_horario_silencio(18, 9) or not _passou_intervalo("pausa", cfg["intervalo_minutos"]): return
    _falar_proativamente(_gerar_fala_proativa(f"Mande o usuário fazer uma pausa ou beber água em uma frase. {REGRA_PERSONA}", "lembrete_pausa"))
    registrar_tentativa()

def _tarefa_monitorar_clima():
    if not _passou_intervalo("clima", 20): return
    chovendo_agora = "Chovendo" in obter_previsao_tempo()
    if _ultimo_clima["chuva"] is None:
        _ultimo_clima["chuva"] = chovendo_agora
        return
    if chovendo_agora and not _ultimo_clima["chuva"]:
        _falar_proativamente(_gerar_fala_proativa(f"Começou a chover agora. Faça um comentário curto e direto sobre isso. {REGRA_PERSONA}", "monitorar_clima"))
        registrar_tentativa()
    _ultimo_clima["chuva"] = chovendo_agora

def _tarefa_steam_wishlist():
    cfg = CONFIGURACAO["Lista_Steam"]
    if not cfg["ativo"]: return

    # Usa timestamp persistido em disco para sobreviver a reinicializações
    estado = ler_estado_proativo()
    ultima_steam = estado.get("ultima_steam", 0)
    agora = time.time()
    if agora - ultima_steam < cfg["intervalo_horas"] * 3600:
        return
    salvar_estado_proativo("ultima_steam", agora)
    appids = _pegar_wishlist()
    if not appids: return
    promocoes, vistos = [], carregar_vistos()
    jogos_avisados = vistos.get("steam", {})
    for appid in appids:
        info = _pegar_preco(appid)
        if not info: continue
        desconto = info["desconto"]
        if desconto < DESCONTO_MINIMO:
            jogos_avisados.pop(appid, None)   # saiu da promoção — libera avisar de novo no futuro
            continue
        if jogos_avisados.get(appid) == desconto: continue
        promocoes.append(info)
    if promocoes:
        lista = ", ".join(f"{j['nome']} ({j['desconto']}%)" for j in promocoes)
        prompt = f"Tem promoção na wishlist da Steam: {lista}. Avise o usuário para gastar dinheiro. {REGRA_PERSONA}"
        falou = _falar_proativamente(_gerar_fala_proativa(prompt, "steam_wishlist"))
        # Só carimba 'avisado' se a fala SAIU de verdade — senão tenta de novo na
        # próxima rodada (bug antigo: carimbava antes de falar e o aviso sumia).
        if falou:
            for j in promocoes:
                jogos_avisados[str(j["appid"])] = j["desconto"]
            registrar_tentativa()
    vistos["steam"] = jogos_avisados
    salvar_vistos(vistos)

def _limpar_resumo(html_txt, limite=280):
    """Tira o HTML do resumo do feed e corta num tamanho legível pro Obsidian."""
    import html as _html
    txt = re.sub(r'<[^>]+>', ' ', html_txt or '')
    txt = _html.unescape(txt)
    txt = re.sub(r'\s+', ' ', txt).strip()
    return (txt[:limite].rstrip() + '…') if len(txt) > limite else txt

def _extrair_imagem(entry):
    """Acha a thumbnail do item do feed (media:thumbnail, media:content, enclosure
    ou o 1o <img> do resumo). Retorna '' se não houver."""
    if entry.get("media_thumbnail"):
        return entry.media_thumbnail[0].get("url", "")
    if entry.get("media_content"):
        return entry.media_content[0].get("url", "")
    if entry.get("enclosures"):
        return entry.enclosures[0].get("href", "")
    m = re.search(r'<img[^>]+src=["\']([^"\']+)', entry.get("summary", ""))
    return m.group(1) if m else ""

_RADAR_MAX_VISTOS = 1000   # teto de itens vistos guardados (os antigos já saíram dos feeds)

def _tarefa_radar_rss():
    """Radar Geek: lê feeds RSS (config em Luna/radar_rss.md), escreve os itens
    novos em Novidades.md (B) e dá uma campainha curta na voz (A). Determinístico:
    item inédito = novidade. Feed recém-adicionado é 'semeado' em silêncio (não
    despeja o histórico todo na 1a vez)."""
    cfg = CONFIGURACAO["Radar_RSS"]
    if not cfg["ativo"] or _em_horario_silencio(*cfg["horario_silencio"]) or not _passou_intervalo("radar_rss", cfg["intervalo_minutos"]):
        return
    feeds = obsidian.ler_feeds_radar()
    if not feeds:
        return
    try:
        import feedparser
    except ImportError:
        cor.vermelho("[📡 Radar: feedparser não instalado — pip install feedparser]")
        return

    vistos = carregar_vistos()
    itens_vistos = vistos.get("radar", {})          # id_do_item -> True
    feeds_semeados = vistos.get("radar_feeds", [])  # feeds cujo baseline já foi marcado
    # Auto-sincroniza com a nota: descarta feeds que saíram do radar_rss.md (órfãos).
    # Assim o registro espelha a nota e um feed re-adicionado volta a semear em silêncio.
    feeds_semeados = [u for u in feeds_semeados if u in feeds]

    # Rodízio: o Reddit dá 429 se martelar vários feeds numa janela curta. Então
    # cada rodada checa só uns poucos, alternando — bem mais gentil no rate-limit.
    # A janela DÁ A VOLTA na lista: com o slice simples feeds[idx:idx+N], quando idx>0
    # o feeds[0] nunca era checado (slice não wrapa) e o radar_idx podia travar, deixando
    # um feed eternamente de fora.
    POR_RODADA = 3
    n_feeds = len(feeds)
    quantos = min(POR_RODADA, n_feeds)
    idx = vistos.get("radar_idx", 0) % n_feeds
    feeds_rodada = [feeds[(idx + k) % n_feeds] for k in range(quantos)]
    vistos["radar_idx"] = (idx + quantos) % n_feeds

    novos = []
    for i, url in enumerate(feeds_rodada):
        if i > 0:
            time.sleep(3)   # espaça os requests dentro da rodada (Reddit dá 429 em rajada)
        try:
            d = feedparser.parse(url, agent="LunaRadar/1.0 (+local companion)")
        except Exception:
            continue
        if not d.entries:   # 429, feed fora do ar ou vazio — pula SEM marcar como semeado (tenta de novo depois)
            continue
        fonte = (d.feed.get("title") or url)[:40]
        feed_novo = url not in feeds_semeados       # 1a vez vendo esse feed?
        for entry in d.entries[:15]:
            link = entry.get("link", "")
            eid = entry.get("id") or link
            if not eid or itens_vistos.get(eid):
                continue
            itens_vistos[eid] = True
            if not feed_novo:   # feed já conhecido: é novidade de verdade
                resumo = _limpar_resumo(entry.get("summary", "") or entry.get("description", ""))
                imagem = _extrair_imagem(entry)
                novos.append((entry.get("title", "(sem título)").strip(), link, fonte, resumo, imagem))
            # feed novo: só marca como visto (semeia baseline), sem anunciar
        if feed_novo:
            feeds_semeados.append(url)
    # Auto-limite: guarda só os últimos N itens vistos (dict preserva ordem de
    # inserção, então são os mais recentes). Os antigos já saíram dos feeds — que
    # mostram só os recentes —, então descartar é seguro e não re-anuncia nada.
    if len(itens_vistos) > _RADAR_MAX_VISTOS:
        itens_vistos = dict(list(itens_vistos.items())[-_RADAR_MAX_VISTOS:])
    vistos["radar"] = itens_vistos
    vistos["radar_feeds"] = feeds_semeados
    salvar_vistos(vistos)

    if novos:
        obsidian.adicionar_novidades(novos)
        n = len(novos)
        cor.amarelo(f"[📡 Radar: {n} novidade(s) → Novidades.md]")

        # Teaser: resume UMA novidade em destaque e diz que tem mais na nota.
        destaque = random.choice(novos)
        titulo_d, resumo_d = destaque[0], destaque[3]
        amostra = f"Título: {titulo_d}." + (f" Resumo: {resumo_d}" if resumo_d else "")

        if n == 1:
            prompt = (
                f"Você achou 1 novidade nos feeds que o usuário acompanha e anotou na nota 'Novidades' dele.\n"
                f"A NOVIDADE: {amostra}\n"
                f"Conte pra ele, do seu jeito e em 1-2 frases, o que é essa novidade (resuminho leve, "
                f"NÃO copie o texto). {REGRA_PERSONA}"
            )
        else:
            prompt = (
                f"Você achou {n} novidades nos feeds que o usuário acompanha e anotou todas na nota 'Novidades' dele.\n"
                f"NOVIDADE EM DESTAQUE (só uma amostra das {n}): {amostra}\n"
                f"Dê um resuminho leve SÓ dessa novidade em destaque (1-2 frases, sem copiar o texto) e, no fim, "
                f"avise que tem mais {n - 1} esperando na nota Novidades. {REGRA_PERSONA}"
            )
        _falar_proativamente(_gerar_fala_proativa(prompt, "radar_rss", max_tokens=220))
        registrar_tentativa()

def _anilist_temporada_no_ar(nome):
    """Acha a temporada EM EXIBIÇÃO do anime pelo nome — (media_id, titulo) ou None.
    No AniList cada temporada é uma entrada separada; a busca simples pegava a 1ª
    (encerrada) e silenciava franquias com temporada nova no ar (ex: Slime S4).
    Por isso buscamos vários e ficamos com a que tem episódio agendado (RELEASING)."""
    q = ("query($busca: String) { Page(perPage: 8) {"
         " media(search: $busca, type: ANIME, sort: SEARCH_MATCH) {"
         " id title { romaji english } nextAiringEpisode { episode } } } }")
    try:
        r = requests.post("https://graphql.anilist.co",
                          json={"query": q, "variables": {"busca": nome}}, timeout=10)
        medias = ((r.json().get("data") or {}).get("Page") or {}).get("media", [])
        m = next((x for x in medias if x.get("nextAiringEpisode")), None)
        if not m:
            return None
        # prefere o título em inglês (o da Crunchyroll, que o usuário conhece)
        titulo = m["title"].get("english") or m["title"]["romaji"]
        return (m["id"], titulo)
    except Exception:
        return None


def _anilist_ultimo_episodio(media_id):
    """Último episódio JÁ EXIBIDO dessa temporada — (episodio, timestamp) ou None.
    O nextAiringEpisode aponta pro FUTURO (quando sai o ep 15, ele já pula pro 16),
    então não serve pra 'já saiu'. Aqui pegamos a agenda ordenada por tempo
    decrescente e ficamos com o episódio mais recente que JÁ foi ao ar."""
    q = ("query($id: Int) { Page(perPage: 1) {"
         " airingSchedules(mediaId: $id, notYetAired: false, sort: TIME_DESC) {"
         " episode airingAt } } }")
    try:
        r = requests.post("https://graphql.anilist.co",
                          json={"query": q, "variables": {"id": media_id}}, timeout=10)
        nodes = ((r.json().get("data") or {}).get("Page") or {}).get("airingSchedules", [])
        if not nodes:
            return None
        return (nodes[0]["episode"], nodes[0]["airingAt"])
    except Exception:
        return None


_ANIMES_JANELA_H = 24   # avisa se o episódio saiu nas últimas N horas (não "vai sair")

def _tarefa_avisar_animes():
    """Avisa quando SAIU episódio novo dos animes da nota Luna/animes.md (janela de
    ~24h). Fonte: AniList. Dedup por (anime, episódio) em vistos['animes'] — e o
    carimbo só acontece se a fala saiu de verdade (lição da wishlist)."""
    cfg = CONFIGURACAO["Animes"]
    if not cfg["ativo"] or _em_horario_silencio(*cfg["horario_silencio"]) or not _passou_intervalo("animes", cfg["intervalo_minutos"]):
        return
    lista = obsidian.ler_lista_animes()
    if not lista:
        return

    vistos = carregar_vistos()
    avisados = vistos.get("animes", {})
    agora = time.time()
    sairam = []
    for nome, apelido in lista[:10]:     # teto de sanidade na quantidade de consultas
        temporada = _anilist_temporada_no_ar(nome)
        time.sleep(1)                    # gentileza com a API
        if not temporada:
            continue
        media_id, titulo = temporada
        ult = _anilist_ultimo_episodio(media_id)
        time.sleep(1)
        if not ult:
            continue
        ep, ts = ult
        if ts > agora or (agora - ts) > _ANIMES_JANELA_H * 3600:   # ainda não saiu, ou saiu há +24h
            continue
        if avisados.get(titulo) == ep:   # já avisou ESSE episódio (dedup pelo título real)
            continue
        # a Luna FALA o apelido (se houver); o dedup fica no título oficial (estável)
        sairam.append((titulo, apelido or titulo, ep))

    if not sairam:
        return
    lista_txt = "; ".join(f"{falado} (episódio {e})" for _, falado, e in sairam)
    cor.amarelo(f"[🎌 Animes — episódio novo: {lista_txt}]")
    # Quando há apelido (falado != titulo oficial), o 12B tende a "corrigir" pro nome
    # canônico que ele conhece. Damos o contra-exemplo explícito pra travar isso.
    proibidos = "; ".join(f"chame de '{falado}', NUNCA de '{titulo}'"
                          for titulo, falado, _ in sairam if falado != titulo)
    regra_nome = f" IMPORTANTE: {proibidos}." if proibidos else ""
    prompt = (
        f"SAIU episódio novo de anime que o usuário acompanha: {lista_txt}. "
        f"Avise ele com empolgação leve. Use EXATAMENTE o nome que eu dei, sem traduzir, "
        f"expandir nem trocar pelo título oficial em inglês.{regra_nome} "
        f"Já está no ar pra assistir. {REGRA_PERSONA}"
    )
    if _falar_proativamente(_gerar_fala_proativa(prompt, "animes")):
        for titulo, _, e in sairam:
            avisados[titulo] = e
        vistos["animes"] = avisados
        salvar_vistos(vistos)
        registrar_tentativa()


def _tarefa_autoconhecimento():
    """Introspecção: a Luna comenta algo REAL sobre o próprio funcionamento (modelo,
    roteador, nº de ferramentas, tempo ligada). Python junta os fatos; a persona
    embrulha de leve. Não é 'consciência' — é autoconhecimento factual do programa."""
    cfg = CONFIGURACAO["Autoconhecimento"]
    if not cfg["ativo"] or _em_horario_silencio(*cfg["horario_silencio"]) or not _passou_intervalo("autoconhecimento", cfg["intervalo_minutos"]):
        return
    import modulos.pensar as _p   # introspecção: lê os próprios modelos/ferramentas
    horas = (time.time() - _sessao_inicio) / 3600 if _sessao_inicio else 0
    fatos = [
        f"eu rodo num modelo local só, o {_p.MODELO_PERSONA}, que faz tanto a minha personalidade quanto decidir qual ferramenta eu uso",
        f"eu tenho {len(_p.FUNCOES_DISPONIVEIS)} ferramentas à disposição",
    ]
    try:   # voz atual — lida ao vivo do falar.py (fica certa mesmo se trocar de novo)
        from modulos import falar as _f
        fatos.append(f"minha voz é a {_f._voz_padrao} do Kokoro, sintetizada na CPU do teu PC")
    except Exception:
        pass
    ativas = sum(1 for v in TAREFAS_ATIVAS.values() if v)
    fatos.append(f"eu tenho {ativas} tarefas proativas ligadas agora — jogos, radar de notícias, clima, essas coisas")
    if horas >= 0.5:
        fatos.append(f"tô ligada há {horas:.1f} horas nessa sessão")
    fato = random.choice(fatos)
    prompt = (
        f"Faça um comentário curto, leve e curioso sobre VOCÊ MESMA, como quem se dá conta de "
        f"algo sobre o próprio funcionamento. Fato REAL pra usar: {fato}. "
        f"Fale natural, sem soar como relatório técnico nem se gabando. {REGRA_PERSONA}"
    )
    _falar_proativamente(_gerar_fala_proativa(prompt, "autoconhecimento"))
    registrar_tentativa()

def _tarefa_bom_dia():
    cfg = CONFIGURACAO["bom_dia"]
    if not cfg["ativo"]: return
    
    agora = datetime.datetime.now()
    hora_atual = agora.hour
    dia_atual = agora.day
    
    horario_inicio, horario_fim = cfg["horario_falar"]
    
    # 1. Verifica se está dentro da janela (ex: 8h às 10h)
    if horario_inicio <= hora_atual < horario_fim:
        
        # 2. Puxa a memória física do disco
        estado = ler_estado_proativo()
        
        # 3. Verifica se o dia salvo lá é diferente de hoje
        if estado.get("ultimo_dia_bom_dia") != dia_atual:
            print("\n[🌅 Horário detectado. Iniciando rotina Proativa de Bom Dia...]")
            
            try:
                dados_agenda = ler_agenda_google()
            except:
                dados_agenda = "Não foi possível acessar a agenda."
                
            # 2. Tenta ler os emails isoladamente
            try:
                dados_email = checar_emails_nao_lidos()
            except:
                dados_email = "Não foi possível acessar os emails."
                
            prompt_matinal = f"""O sistema notou que o horário atual está dentro da janela matinal e o usuário está ativo.
DADOS DA AGENDA PARA HOJE: {dados_agenda}.
DADOS DA CAIXA DE EMAIL:{dados_email}.

Dê um 'bom dia' usando sua personalidade {REGRA_PERSONA} EXCEÇÃO ao limite de frases: aqui, informe o que tem na agenda e quantos emails há (com o assunto deles) em até 5 frases."""

            texto = _gerar_fala_proativa(prompt_matinal, "bom_dia", max_tokens=400, variar=False)
            
            if texto:
                _falar_proativamente(texto)
                
                # 4. SALVA NO DISCO: A Luna nunca mais vai esquecer que já falou hoje
                salvar_estado_proativo("ultimo_dia_bom_dia", dia_atual)

def _tarefa_monitorar_jogos():
    """Verifica se o usuário iniciou ou encerrou uma partida."""
    global ESTADO_JOGOS
    
    # Pega todos os nomes de processos rodando agora (case-insensitive)
    processos_ativos = {p.info['name'].lower() for p in psutil.process_iter(['name'])}

    for exe, nome_jogo in PROCESSOS_JOGOS.items():
        esta_rodando_agora = exe.lower() in processos_ativos
        estava_rodando_antes = ESTADO_JOGOS[nome_jogo]

        # CASO 1: Acabou de abrir o jogo
        if esta_rodando_agora and not estava_rodando_antes:
            ESTADO_JOGOS[nome_jogo] = True
            registrar_interacao()  # usuário está ativo — reseta suspensão
            atualizar_estado_luna("jogo_ativo", nome_jogo)
            print(f"[🎮 Jogo Detectado: {nome_jogo}]")
            
            if nome_jogo == "Overwatch":
                print("[📊 Buscando dados para briefing de sessão...]")
                dados_abertura = _buscar_dados_overwatch()
                prompt = (
                    f"O usuário acabou de abrir Overwatch.\n"
                    f"DADOS ATUAIS DA CONTA: {dados_abertura}\n"
                    f"Faça um briefing de sessão direto, do seu jeito: rank atual + uma observação sobre tendência de desempenho. "
                    f"{REGRA_PERSONA}"
                )
            elif nome_jogo == "Deadlock":
                print("[📊 Buscando dados para briefing de sessão Deadlock...]")
                dados_abertura = _buscar_dados_deadlock()
                prompt = (
                    f"O usuário acabou de abrir Deadlock.\n"
                    f"DADOS DA CONTA: {dados_abertura}\n"
                    f"Faça um briefing de sessão direto: winrate atual + observação sobre tendência. "
                    f"{REGRA_PERSONA}"
                )
            else:
                prompt = f"O usuário acabou de abrir o {nome_jogo}. Comente o início da sessão do seu jeito. {REGRA_PERSONA} 1 frase."

            texto = _gerar_fala_proativa(prompt, f"jogo_aberto_{nome_jogo}")
            if texto: _falar_proativamente(texto)

        # CASO 2: Acabou de fechar o jogo
        elif not esta_rodando_agora and estava_rodando_antes:
            ESTADO_JOGOS[nome_jogo] = False
            atualizar_estado_luna("jogo_ativo", None)
            print(f"[🚫 Jogo Encerrado: {nome_jogo}]")
            
            # Dados padrão se o jogo não tiver API
            dados_extras = "Sem dados de API no momento."
            instrucao_especifica = f"Registre o encerramento da sessão de {nome_jogo} de forma factual e direta."
            
            # ==========================================
            # ROTEAMENTO DE APIS E DEBOCHES ESPECÍFICOS
            # ==========================================
            if nome_jogo == "Overwatch":
                print("[🔎 Buscando estatísticas da conta de Overwatch...]")
                dados_extras = _buscar_dados_overwatch()
               
                if dados_extras == "ERRO_DE_CONEXAO":
                    instrucao_especifica = "Deu erro de rede ao buscar os dados. Registre o fim da sessão e pode soltar uma alfinetada leve na internet ou nos servidores da Blizzard — nunca nele."
                else:
                    instrucao_especifica = (
                        "Use os dados como observação factual. "
                        "1 frase com o dado mais relevante (rank ou winrate). "
                        "1 frase de análise de padrão — precisa; uma alfinetada leve cabe, crueldade não."
                    )
            
            elif nome_jogo == "League of Legends":
                print("[🔎 Aguardando dados da última partida via LCU (15s)...]")
                time.sleep(15)
                dados_extras = _buscar_dados_lol()
                cor.amarelo(f"[🎮 LCU retornou: {dados_extras[:120]}]")
                if dados_extras.startswith("ERRO"):
                    instrucao_especifica = "Não foi possível recuperar os dados da última partida. Registre o fim da sessão em 1 frase, sem inventar resultado."
                else:
                    instrucao_especifica = (
                        "Use os dados como observação factual. "
                        "1 frase com o resultado da partida e o KDA. "
                        "1 frase de análise de padrão (ex: impacto do KDA no resultado) — precisa; uma alfinetada leve cabe, crueldade não."
                    )
                
            elif nome_jogo == "Deadlock":
                print("[🔎 Buscando estatísticas da conta de Deadlock...]")
                dados_extras = _buscar_dados_deadlock()
                if dados_extras.startswith("ERRO"):
                    instrucao_especifica = "Erro ao buscar dados. Registre o fim da sessão e pode alfinetar de leve que nem a API quis colaborar hoje."
                else:
                    instrucao_especifica = (
                        "Use os dados como observação factual. "
                        "1 frase com o resultado da partida e KDA. "
                        "1 frase sobre winrate ou padrão de desempenho — análise direta; alfinetada leve cabe."
                    )

            # ==========================================
            # MONTAGEM DO PROMPT
            # ==========================================
            prompt = f"""O usuário acabou de fechar o {nome_jogo}.
DADOS TÉCNICOS DA CONTA: {dados_extras}

Registre o encerramento da sessão com tom observacional:
{REGRA_PERSONA}

INSTRUÇÃO: {instrucao_especifica}
Máximo 2 frases. SEM EMOJIS."""

            texto = _gerar_fala_proativa(prompt, f"jogo_fechado_{nome_jogo}", max_tokens=300)
            if texto: _falar_proativamente(texto)


def _fmt_duracao(minutos: int) -> str:
    """Duração falável pra voz: 132 -> '2 horas e 12 minutos' (nunca número quebrado)."""
    if minutos < 60:
        return f"{minutos} minuto" + ("s" if minutos > 1 else "")
    h, m = divmod(minutos, 60)
    horas_txt = f"{h} hora" + ("s" if h > 1 else "")
    min_txt = f"{m} minuto" + ("s" if m > 1 else "")
    return f"{horas_txt} e {min_txt}" if m else horas_txt


def _tarefa_monitorar_steam():
    """Detecta início/fim de QUALQUER jogo da Steam, de forma genérica, via API.
    Complementa _tarefa_monitorar_jogos: os jogos com API dedicada
    (Overwatch/LoL/Deadlock) continuam sendo tratados lá e são ignorados aqui.
    Puxa tempo de sessão, horas totais e conquistas destravadas na sessão."""
    global _STEAM_SESSAO, _STEAM_JOGANDO_AGORA

    if not STEAM_API_KEY or not STEAM_ID:
        return
    # Intervalo adaptativo: sem jogo, checa devagar (não tem pressa pra dar oi);
    # com jogo aberto, checa mais amiúde pra pegar logo a hora do fim da sessão.
    intervalo = 1.5 if _STEAM_SESSAO["appid"] else 3.0
    if not _passou_intervalo("steam_status", intervalo):
        return

    # Só consulta a API se o cliente Steam estiver aberto (senão: 0 chamadas).
    # Se o Steam foi fechado com um jogo em sessão, appid=None cai no CASO 2 (fim).
    if _steam_cliente_aberto():
        appid, nome = _steam_status_atual()
    else:
        appid, nome = None, None

    # Jogos que já têm tratamento dedicado ficam com o outro handler
    if nome and nome in set(PROCESSOS_JOGOS.values()):
        appid, nome = None, None

    # Jogos ignorados (idle sempre aberto, ex: Task Bar Hero): a Luna não trata
    # como sessão — nem comenta na abertura, nem liga o "não perturbe".
    if _steam_ignorado(appid, nome):
        appid, nome = None, None

    appid_antes = _STEAM_SESSAO["appid"]

    # CASO 1: abriu um jogo (não havia nada rodando antes)
    if appid and not appid_antes:
        conq = _steam_conquistas(appid)
        _STEAM_SESSAO.update({
            "appid": appid, "nome": nome,
            "inicio": time.time(), "conq_inicio": conq,
        })
        _STEAM_JOGANDO_AGORA = True
        registrar_interacao()  # usuário ativo — reseta suspensão
        atualizar_estado_luna("jogo_ativo", nome)
        print(f"[🎮 Steam: {nome} aberto]")

        horas = _steam_horas(appid)
        info = _steam_info_jogo(appid)
        partes = [f"Jogo: {nome}."]
        if horas >= 1:
            # horas inteiras: '642.4h' vira '642 horas' (a voz lê número quebrado mal)
            partes.append(f"Você já tem {int(round(horas))} horas totais nele.")
        if conq:
            partes.append(f"Conquistas: {conq[0]} de {conq[1]} destravadas.")
        if info:
            partes.append(f"Sobre o jogo: {info}")
        dados = " ".join(partes)

        prompt = (
            f"O usuário acabou de abrir {nome} na Steam.\n"
            f"DADOS: {dados}\n"
            f"Comente a abertura da sessão de forma leve e amigável. Puxe UM detalhe ESPECÍFICO "
            f"do jogo (a história/premissa, um prêmio ou um modo de jogo — nunca algo genérico) "
            f"E encaixe um dado dele (horas ou conquistas). {REGRA_PERSONA} "
            f"(exceção: aqui pode usar até 3 frases pra caber o detalhe do jogo)."
        )
        texto = _gerar_fala_proativa(prompt, f"steam_abriu_{nome}")
        if texto: _falar_proativamente(texto)

    # CASO 2: fechou (ou trocou de jogo) — havia algo antes e agora é outra coisa
    elif appid_antes and appid != appid_antes:
        nome_antes = _STEAM_SESSAO["nome"]
        inicio = _STEAM_SESSAO["inicio"]
        conq_inicio = _STEAM_SESSAO["conq_inicio"]

        dur_min = int((time.time() - inicio) / 60) if inicio else 0
        conq_fim = _steam_conquistas(appid_antes)
        novas = 0
        if conq_inicio and conq_fim:
            novas = max(0, conq_fim[0] - conq_inicio[0])

        print(f"[🚫 Steam: {nome_antes} fechado — {dur_min}min, +{novas} conquistas]")

        # zera a sessão ANTES de qualquer coisa (evita reprocessar)
        _STEAM_SESSAO.update({"appid": None, "nome": None, "inicio": 0.0, "conq_inicio": None})
        _STEAM_JOGANDO_AGORA = False
        atualizar_estado_luna("jogo_ativo", None)

        if dur_min >= 2:  # ignora aberturas acidentais de poucos segundos
            partes = [f"Duração da sessão: {_fmt_duracao(dur_min)}."]
            if novas > 0:
                partes.append(f"Conquistas destravadas nesta sessão: {novas}.")
            elif conq_inicio:
                partes.append("Nenhuma conquista nova nesta sessão.")
            dados = " ".join(partes)
            prompt = (
                f"O usuário acabou de fechar {nome_antes} (Steam).\n"
                f"DADOS DA SESSÃO: {dados}\n"
                f"Feche a sessão de forma leve: comente o tempo jogado e, se houve, as conquistas novas. "
                f"{REGRA_PERSONA}"
            )
            texto = _gerar_fala_proativa(prompt, f"steam_fechou_{nome_antes}", max_tokens=300)
            if texto: _falar_proativamente(texto)


# Sites onde a Luna fica calada: scroll passivo (redes) e ferramentas de trabalho
# (ex: chat de suporte do plantão — não cabe comentário e não pode atrapalhar).
_DOMINIOS_IGNORAR = ("reddit.com", "twitter.com", "x.com", "facebook.com",
                     "instagram.com", "tiktok.com", "twitch.tv",
                     "chatmobi.com.br")

def _tarefa_contexto_navegador():
    global _nav_url_atual, _nav_url_desde, _nav_ultimo_comentario_url

    # 1. Firefox precisa estar na janela em foco
    janela = obter_janela_em_foco().lower()
    if "firefox" not in janela:
        return

    # 2. Limita chamadas à extensão a cada 2 minutos
    if not _passou_intervalo("contexto_nav_ping", 2):
        return

    url = controlar_firefox_via_extensao("obter_url")
    if not url or "Erro:" in url or not url.startswith("http"):
        return

    agora = time.time()

    # URL mudou → reseta o cronômetro, sem comentar ainda
    if url != _nav_url_atual:
        _nav_url_atual = url
        _nav_url_desde = agora
        return

    minutos_na_url = (agora - _nav_url_desde) / 60

    # Só fala após 10 minutos e nunca repete na mesma URL
    if minutos_na_url < 10 or url == _nav_ultimo_comentario_url:
        return

    url_lower = url.lower()

    # Feeds e redes sociais → silêncio (scroll passivo, nada útil a dizer)
    if any(d in url_lower for d in _DOMINIOS_IGNORAR):
        _nav_ultimo_comentario_url = url  # marca para não checar de novo
        return

    # YouTube com vídeo aberto → ação concreta
    if "youtube.com/watch" in url_lower or "youtu.be/" in url_lower:
        prompt = (
            f"O usuário está com um vídeo do YouTube aberto há {int(minutos_na_url)} minutos. "
            f"Pergunte de forma casual e direta se ele quer que você resuma o vídeo. "
            f"NÃO diga 'você está assistindo' ou descreva o que ele faz. Só a pergunta. "
            f"{REGRA_PERSONA} 1 frase."
        )
    # Outros sites de conteúdo (artigo, doc, notícia)
    else:
        titulo = (controlar_firefox_via_extensao("obter_titulo") or "").strip()
        # Barra qualquer resposta de sistema/erro da extensão (ex: "Comando desconhecido")
        if (not titulo or len(titulo) < 8
                or titulo.upper().startswith("SISTEMA:")
                or "desconhecid" in titulo.lower()
                or "Erro" in titulo):
            return
        prompt = (
            f"O usuário está nessa página há {int(minutos_na_url)} minutos: '{titulo}'. "
            f"Faça UM comentário curto sobre o assunto do título — fale sobre o tema, "
            f"NÃO sobre o fato de ele estar lendo. Sem 'você está', sem narração. "
            f"{REGRA_PERSONA} 1 frase."
        )

    texto = _gerar_fala_proativa(prompt, "contexto_navegador")
    if texto:
        _nav_ultimo_comentario_url = url
        _falar_proativamente(texto)
        registrar_tentativa()


# ============================================================
# MEMÓRIA EPISÓDICA — extração de fatos duráveis (roda no ocioso)
# ============================================================
def _tarefa_extrair_memoria(forcar=False):
    """Lê as conversas novas (ChromaDB desde o marcador), pede pro 12B extrair FATOS
    DURÁVEIS e joga na fila de pendentes pra você confirmar no web. NÃO grava na
    memória direto — só PROPÕE (a confirmação é o anti-alucinação). Roda no ocioso
    (AFK) ou forçado pelo botão 'processar agora'."""
    if not forcar and not _passou_intervalo("extrair_memoria", 30):   # no máx a cada 30 min no ocioso
        return
    from modulos import memoria
    memoria.mem_limpar_lixo()                       # aproveita e limpa o lixo velho
    novas = memoria.conversas_desde(memoria.mem_marcador())
    if not novas:
        return
    blocos = "\n---\n".join(doc for _, doc in novas)[:6000]
    prompt = (
        "Você extrai FATOS DURÁVEIS e NOVOS sobre o usuário destas conversas, pra uma "
        "memória de longo prazo que ajuda a lembrar dele e dar continuidade depois.\n\n"
        f"CONVERSAS:\n\"\"\"\n{blocos}\n\"\"\"\n\n"
        "REGRAS:\n"
        "- Extraia SÓ o que vale lembrar pra PUXAR ASSUNTO depois: planos, decisões, compras, "
        "eventos marcantes, mudanças de vida, gostos, e estado que persiste (ex: 'anda estressado "
        "com o plantão', 'o pai está doente', 'quer terminar o Silksong').\n"
        "- IGNORE: comandos ('toca música'), perguntas factuais, saudações, coisa efêmera, e "
        "TRIVIA TÉCNICA solta (specs de hardware, números) — a não ser que seja uma compra/decisão.\n"
        "- Cada fato: UMA frase curta e NATURAL, sem começar com 'O usuário' (ex: 'comprou um "
        "Steam Deck', 'tem uma filha', 'joga Hollow Knight').\n"
        "- Nada que valha lembrar? Retorne lista vazia.\n"
        'FORMATO (só JSON, nada mais): {"fatos": ["...", "..."]}'
    )
    try:
        bruto = gerar_resposta(prompt, [], analisar=False, salvar=False, modo_memoria=True)
        m = re.search(r'\{.*\}', bruto or "", re.DOTALL)
        fatos = json.loads(m.group()).get("fatos", []) if m else []
        fatos = [f.strip() for f in fatos if isinstance(f, str) and len(f.strip()) >= 5][:8]
    except Exception as e:
        cor.vermelho(f"[🧠 Extração de memória falhou: {e}]")
        return
    memoria.mem_set_marcador(novas[-1][0])          # marca até onde processou (não relê)
    if fatos:
        n = memoria.mem_adicionar_candidatos(fatos)
        if n:
            cor.amarelo(f"[🧠 Memória: {n} lembrança(s) nova(s) pra você revisar no web]")
            try:
                import servidor as _srv
                _srv.notificar_memoria(len(memoria.mem_listar_pendentes()))
            except Exception:
                pass

def processar_memoria_agora() -> int:
    """Entrada manual (botão 'processar agora' do web): força a extração e devolve
    quantos pendentes existem depois."""
    _tarefa_extrair_memoria(forcar=True)
    from modulos import memoria
    return len(memoria.mem_listar_pendentes())


# ============================================================
# LOOP PRINCIPAL DA THREAD PROATIVA
# ============================================================
def _loop_proativo():
    time.sleep(10)
    _ja_imprimiu_suspensa = False
    _ja_imprimiu_jogando = False
    
    while _thread_rodando:
        if not _proativo_ativo:
            time.sleep(30)
            continue

        if _sessao_inicio:
            atualizar_estado_luna("horas_na_sessao", round((time.time() - _sessao_inicio) / 3600, 1))
        segundos_afk = obter_tempo_afk()
        minutos_afk = segundos_afk / 60

        # Camada 1 — sempre ativa, independente de suspensão ou AFK
        if TAREFAS_ATIVAS.get("jogos", True):
            _tarefa_monitorar_jogos()
        if TAREFAS_ATIVAS.get("steam_jogo", True):
            _tarefa_monitorar_steam()

        if not esta_suspensa() and minutos_afk <= 5:
            if _ja_imprimiu_suspensa:   # estava suspensa e acordou agora
                try:
                    import servidor as _srv
                    _srv.atualizar_status("🌚 Por aqui")
                except Exception:
                    pass
            _ja_imprimiu_suspensa = False

            jogando_agora = any(ESTADO_JOGOS.values()) or _STEAM_JOGANDO_AGORA

            # O MODO "NÃO PERTURBE"
            if not jogando_agora:
                _ja_imprimiu_jogando = False
                if TAREFAS_ATIVAS.get("emails", True): _tarefa_checar_emails()
                if TAREFAS_ATIVAS.get("agenda", True): _tarefa_checar_agenda()
                if TAREFAS_ATIVAS.get("pausa", True): _tarefa_lembrete_pausa()
                if TAREFAS_ATIVAS.get("clima", True): _tarefa_monitorar_clima()
                if TAREFAS_ATIVAS.get("steam", True): _tarefa_steam_wishlist()
                if TAREFAS_ATIVAS.get("bom_dia", True): _tarefa_bom_dia()
                if TAREFAS_ATIVAS.get("navegador", True): _tarefa_contexto_navegador()
                if TAREFAS_ATIVAS.get("radar_rss", True): _tarefa_radar_rss()
                if TAREFAS_ATIVAS.get("animes", True): _tarefa_avisar_animes()
                if TAREFAS_ATIVAS.get("autoconhecimento", True): _tarefa_autoconhecimento()
            else:
                if not _ja_imprimiu_jogando:
                    cor.amarelo("[🔇 Modo Não Perturbe Ativado — Aguardando o fim da partida]")
                    _ja_imprimiu_jogando = True
        else:
            if not _ja_imprimiu_suspensa:
                if minutos_afk > 5:
                    cor.verde(f"[🌑 Luna em modo de espera automático — Usuário AFK há {minutos_afk:.1f} min]")
                else:
                    cor.verde("[🌑 Luna suspensa — aguardando interação]")
                _ja_imprimiu_suspensa = True
                try:
                    import servidor as _srv
                    _srv.atualizar_status("🌑 Suspensa — aguardando interação")
                    _srv.atualizar_gif("sleeping")
                except Exception:
                    pass
            # Ocioso é o melhor momento pra extrair memória (você fora, sem competir com nada).
            if TAREFAS_ATIVAS.get("memoria", True):
                _tarefa_extrair_memoria()

        time.sleep(30)

def iniciar_modo_proativo():
    global _thread_rodando, _sessao_inicio
    if _thread_rodando: return

    # CURA DA AVALANCHE: Definindo o 'ponto zero' como agora
    agora = time.time()
    for chave in ["emails", "agenda", "pausa", "clima", "autoconhecimento"]:
        _ultima_execucao[chave] = agora

    _sessao_inicio = agora
    atualizar_estado_luna("horas_na_sessao", 0)
    atualizar_estado_luna("jogo_ativo", None)
    atualizar_estado_luna("programa_atual", "")
    atualizar_estado_luna("programa_desde", None)

    _thread_rodando = True
    t = threading.Thread(target=_loop_proativo, daemon=True)
    t.start()
    cor.magenta("[🌚 Luna proativa: thread iniciada]")

def parar_modo_proativo():
    global _thread_rodando
    _thread_rodando = False