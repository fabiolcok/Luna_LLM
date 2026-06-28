# proativa.py
import json
import os
import time
import threading
import datetime
import random
import requests
import ctypes
from modulos.habilidades import checar_emails_nao_lidos, ler_agenda_google, obter_previsao_tempo, obter_janela_em_foco, controlar_firefox_via_extensao
from modulos.pensar import gerar_resposta
from modulos.falar import falar_texto
from modulos.memoria import carregar_vistos, salvar_vistos, atualizar_estado_luna
from modulos import obsidian
import modelos.cores as cor
import psutil
import re

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
}

# Jogos para ser monitorados.
PROCESSOS_JOGOS = {
    "Overwatch.exe": "Overwatch",
    "League of Legends.exe": "League of Legends",
    "Deadlock.exe" : "Deadlock"
}

# Estado interno para não ficar repetindo a fala
ESTADO_JOGOS = {
    "Overwatch": False,
    "League of Legends": False,
    "Deadlock" :False
}



STEAM_API_KEY    = os.getenv("STEAM_API_KEY", "")
STEAM_ID         = os.getenv("STEAM_ID", "")
DESCONTO_MINIMO  = 50

# ============================================================
# REGRAS DE PERSONA (Injetado nos prompts proativos)
# ============================================================
REGRA_PERSONA = (
    "Responda em português do Brasil coloquial, com tom leve e amigável, como uma amiga falando DIRETAMENTE com o Fábio. "
    "Fale com ele em SEGUNDA pessoa (você, seu, te). Mesmo que a instrução mencione 'o Fábio' ou 'dele' (é só o contexto te informando), "
    "NUNCA fale dele em terceira pessoa: diga 'seus stats', 'você está em Gold', nunca 'os stats dele' ou 'ele está'. "
    "NÃO use 'tu' nem formas de Portugal ('precisares'/'tás'). "
    "Pode ter bom humor, mas seja breve e natural — nada de robótica nem de bajulação. "
    "Você é amiga dele, não namorada nem esposa. Sem emojis, sem asteriscos. Máximo 2 frases."
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
    "radar_rss": True
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

def _falar_proativamente(texto_resposta):
    timeout = time.time() + 300
    while not luna_esta_livre():
        if time.time() > timeout:
            return
        time.sleep(3)
    try:
        import servidor as _srv
        _srv.atualizar_legenda(texto_resposta)
        _srv.atualizar_usuario("")
    except Exception:
        pass
    falar_texto(texto_resposta)

# Abordagens sorteadas para o proativo não ficar repetitivo (variar=True)
_ABORDAGENS = [
    "um comentário curto e direto",
    "uma pergunta casual pro Fábio",
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
    url = f"https://store.steampowered.com/api/appdetails?appids={appid}&cc=br&l=portuguese&filters=price_overview,basic"

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

# ============================================================
# APIS JOGOS
# ============================================================

def _buscar_dados_overwatch():
    """Busca o perfil completo do Fábio e os heróis mais jogados na API do Overwatch."""
    battletag = os.getenv("OW_BATTLETAG", "Fabio-1600")
    
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
        prompt = f"O Fábio tem {len(novos)} emails novos. Remetentes: {' | '.join(novos[:5])}. Avise-o. {REGRA_PERSONA}"
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
            f"Avise o Fábio de forma seca e direta, mencionando só esses. {REGRA_PERSONA}"
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
    _falar_proativamente(_gerar_fala_proativa(f"Mande o Fábio fazer uma pausa ou beber água em uma frase. {REGRA_PERSONA}", "lembrete_pausa"))
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
            jogos_avisados.pop(appid, None)
            continue
        if jogos_avisados.get(appid) == desconto: continue
        jogos_avisados[appid] = desconto
        promocoes.append(info)
    vistos["steam"] = jogos_avisados
    salvar_vistos(vistos)
    if promocoes:
        lista = ", ".join(f"{j['nome']} ({j['desconto']}%)" for j in promocoes)
        prompt = f"Tem promoção na wishlist da Steam: {lista}. Avise o Fábio para gastar dinheiro. {REGRA_PERSONA}"
        _falar_proativamente(_gerar_fala_proativa(prompt, "steam_wishlist"))
        registrar_tentativa()

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
    novos = []
    for url in feeds:
        try:
            d = feedparser.parse(url, agent="LunaRadar/1.0 (+local companion)")
        except Exception:
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
                novos.append((entry.get("title", "(sem título)").strip(), link, fonte))
            # feed novo: só marca como visto (semeia baseline), sem anunciar
        if feed_novo:
            feeds_semeados.append(url)
    vistos["radar"] = itens_vistos
    vistos["radar_feeds"] = feeds_semeados
    salvar_vistos(vistos)

    if novos:
        obsidian.adicionar_novidades(novos)
        n = len(novos)
        cor.amarelo(f"[📡 Radar: {n} novidade(s) → Novidades.md]")
        prompt = (
            f"Você encontrou {n} novidade(s) nos feeds que o Fábio acompanha e já anotou na nota 'Novidades' dele. "
            f"Avise em 1 frase curta que tem {n} novidade(s) no radar pra ele dar uma olhada — NÃO liste os títulos. {REGRA_PERSONA}"
        )
        _falar_proativamente(_gerar_fala_proativa(prompt, "radar_rss"))
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
                
            prompt_matinal = f"""O sistema notou que o horário atual está dentro da janela matinal e o Fábio está ativo.
DADOS DA AGENDA PARA HOJE: {dados_agenda}.
DADOS DA CAIXA DE EMAIL:{dados_email}.

Dê um 'bom dia' usando sua personalidade {REGRA_PERSONA}. Informe o que tem na agenda e quantos emails há, com o assunto deles. Máximo de 5 frases."""

            texto = _gerar_fala_proativa(prompt_matinal, "bom_dia", max_tokens=400, variar=False)
            
            if texto:
                _falar_proativamente(texto)
                
                # 4. SALVA NO DISCO: A Luna nunca mais vai esquecer que já falou hoje
                salvar_estado_proativo("ultimo_dia_bom_dia", dia_atual)

def _tarefa_monitorar_jogos():
    """Verifica se o Fábio iniciou ou encerrou uma partida."""
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
                    f"O Fábio acabou de abrir Overwatch.\n"
                    f"DADOS ATUAIS DA CONTA: {dados_abertura}\n"
                    f"Faça um briefing de sessão frio e direto: rank atual + uma observação analítica sobre tendência de desempenho. "
                    f"{REGRA_PERSONA} Máximo 2 frases."
                )
            elif nome_jogo == "Deadlock":
                print("[📊 Buscando dados para briefing de sessão Deadlock...]")
                dados_abertura = _buscar_dados_deadlock()
                prompt = (
                    f"O Fábio acabou de abrir Deadlock.\n"
                    f"DADOS DA CONTA: {dados_abertura}\n"
                    f"Faça um briefing de sessão frio: winrate atual + observação sobre tendência. "
                    f"{REGRA_PERSONA} Máximo 2 frases."
                )
            else:
                prompt = f"O Fábio acabou de abrir o {nome_jogo}. Registre o início da sessão de forma fria e direta. {REGRA_PERSONA} 1 frase."

            texto = _gerar_fala_proativa(prompt, f"jogo_aberto_{nome_jogo}")
            if texto: _falar_proativamente(texto)

        # CASO 2: Acabou de fechar o jogo
        elif not esta_rodando_agora and estava_rodando_antes:
            ESTADO_JOGOS[nome_jogo] = False
            atualizar_estado_luna("jogo_ativo", None)
            print(f"[🚫 Jogo Encerrado: {nome_jogo}]")
            
            # Dados padrão se o jogo não tiver API
            dados_extras = "Sem dados de API no momento."
            instrucao_especifica = f"Registre o encerramento da sessão de {nome_jogo} de forma factual e direta, sem zombaria."
            
            # ==========================================
            # ROTEAMENTO DE APIS E DEBOCHES ESPECÍFICOS
            # ==========================================
            if nome_jogo == "Overwatch":
                print("[🔎 Buscando estatísticas da conta de Overwatch...]")
                dados_extras = _buscar_dados_overwatch()
               
                if dados_extras == "ERRO_DE_CONEXAO":
                    instrucao_especifica = "Ocorreu um erro de rede ao buscar os dados dele. Zombe da internet de padaria dele ou diga que os servidores da Blizzard se recusaram a processar um perfil tão medíocre."
                else:
                    instrucao_especifica = (
                        "Use os dados como observação factual. "
                        "1 frase com o dado mais relevante (rank ou winrate). "
                        "1 frase de análise de padrão — sem zombaria, sem crueldade, apenas exatidão."
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
                        "1 frase de análise de padrão (ex: impacto do KDA no resultado) — sem zombaria, sem crueldade, apenas exatidão."
                    )
                
            elif nome_jogo == "Deadlock":
                print("[🔎 Buscando estatísticas da conta de Deadlock...]")
                dados_extras = _buscar_dados_deadlock()
                if dados_extras.startswith("ERRO"):
                    instrucao_especifica = "Erro ao buscar dados. Comente sobre o fato de que nem a API conseguiu registrar o desempenho dele."
                else:
                    instrucao_especifica = (
                        "Use os dados como observação factual. "
                        "1 frase com o resultado da partida e KDA. "
                        "1 frase sobre winrate ou padrão de desempenho — sem zombaria, apenas análise fria."
                    )

            # ==========================================
            # MONTAGEM DO PROMPT
            # ==========================================
            prompt = f"""O Fábio acabou de fechar o {nome_jogo}.
DADOS TÉCNICOS DA CONTA: {dados_extras}

Registre o encerramento da sessão com tom observacional:
{REGRA_PERSONA}

INSTRUÇÃO: {instrucao_especifica}
Máximo 2 frases. SEM EMOJIS."""

            texto = _gerar_fala_proativa(prompt, f"jogo_fechado_{nome_jogo}", max_tokens=300)
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
            f"O Fábio está com um vídeo do YouTube aberto há {int(minutos_na_url)} minutos. "
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
            f"O Fábio está nessa página há {int(minutos_na_url)} minutos: '{titulo}'. "
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

        if not esta_suspensa() and minutos_afk <= 5:
            if _ja_imprimiu_suspensa:   # estava suspensa e acordou agora
                try:
                    import servidor as _srv
                    _srv.atualizar_status("🌚 Por aqui")
                except Exception:
                    pass
            _ja_imprimiu_suspensa = False

            jogando_agora = any(ESTADO_JOGOS.values())

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
                    _srv.atualizar_gif("desligando")
                except Exception:
                    pass
                
        time.sleep(30)

def iniciar_modo_proativo():
    global _thread_rodando, _sessao_inicio
    if _thread_rodando: return

    # CURA DA AVALANCHE: Definindo o 'ponto zero' como agora
    agora = time.time()
    for chave in ["emails", "agenda", "pausa", "clima"]:
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