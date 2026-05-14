# proativa.py
import json
import os
import time
import threading
import datetime
import random
import requests
import ctypes
from modulos.habilidades import checar_emails_nao_lidos, ler_agenda_google, obter_previsao_tempo, pesquisar_na_web, obter_janela_em_foco, obter_contexto_navegador
from modulos.pensar import gerar_resposta
from modulos.falar import falar_texto
from modulos.memoria import carregar_vistos, salvar_vistos
import modelos.cores as cor
import psutil
from pathlib import Path
import re

"""
MÓDULO DE ROTINAS PROATIVAS DA LUNA
---------------------------------------------------------
Este arquivo contém todas as funções de "Push" (Autônomas).
São as tarefas que a Luna executa por conta própria no background,
sem que o Fábio precise pedir, baseadas em tempo, estado do sistema ou eventos.

Arquitetura Principal:
- _loop_proativo(): O "coração" do sistema. Roda em loop contínuo (ex: a cada 30s).
  Controla o sensor de AFK (inatividade) e gerencia a trava do Modo Não Perturbe 
  (silencia tarefas invasivas se um jogo estiver aberto).
- Controle de Estado (JSON): Funções `ler_estado_proativo` e `salvar_estado_proativo` 
  criam uma "memória física" no disco para evitar repetição de broncas (como Lixo Digital e Bom Dia) no mesmo dia.
- Sensor AFK (`obter_tempo_afk`): Utiliza `ctypes` do Windows para monitorar o tempo ocioso real do teclado/mouse.

Integrações de API (Background):
- OverFast API (`_buscar_dados_overwatch`): Busca estatísticas consolidadas de Overwatch (Endosso, Main Hero, Tempo jogado) para ofender o desempenho.
- Steam API (`_pegar_wishlist`, `_pegar_preco`): Monitora a Wishlist e checa preços com descontos maiores que a margem definida.

Tarefas Autônomas Disponíveis:
- _tarefa_monitorar_jogos(): Vigia os processos do sistema. Detecta abertura/fechamento de jogos (Overwatch, LoL, Deadlock) e engatilha ofensas e checagem de API.
- _tarefa_bom_dia(): Executa 1x ao dia. Junta a Agenda Google e E-mails em um prompt matinal cínico e letal.
- _tarefa_lixo_digital(): Executa 1x ao dia. Inspeciona a pasta Downloads e julga a desorganização do usuário (apenas lê, não deleta).
- _tarefa_checar_emails(): Checa novas mensagens não lidas periodicamente respeitando o horário de silêncio.
- _tarefa_checar_agenda(): Alerta sobre compromissos iminentes baseados na antecedência configurada.
- _tarefa_lembrete_pausa(): Cobra pausas ergonômicas após um longo período de atividade contínua.
- _tarefa_monitorar_clima(): Alerta espontaneamente caso a API detecte uma mudança brusca (ex: começou a chover).
- _tarefa_steam_wishlist(): Avisa sobre promoções agressivas na lista de desejos da Steam.
- _tarefa_reagir_programa(): Puxa assunto questionando a utilidade do programa que acabou de ser aberto (possui debounce para não flodar).
- _tarefa_puxar_assunto(): Lê o contexto do navegador (aba atual) ou a janela do SO em foco para criticar a produtividade do usuário.

Controle da Thread:
- iniciar_modo_proativo(): Inicia a thread em background e sincroniza os timers (evita a 'avalanche' de notificações ao iniciar).
- parar_modo_proativo(): Encerra de forma segura o loop autônomo.
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
        "intervalo_minutos": 90,
    },
    "Lista_Steam": {
        "ativo": True,
        "intervalo_horas": 24,
    },
    "puxar_assunto": {
        "ativo": True,
        "intervalo_minutos": 15,
    },
    "bom_dia": {
        "ativo": True,
        "horario_falar": (8, 11),  # Vai falar entre 08:00 e 10:59
        "ultimo_dia_falado": None  # Guarda o dia do mês para resetar sozinho
    }

}

# Jogos para ser monitorados.
PROCESSOS_JOGOS = {
    "Overwatch.exe": "Overwatch",
    "LeagueClient.exe": "League of Legends",
    "Deadlock.exe" : "Deadlock"
}

# Estado interno para não ficar repetindo a fala
ESTADO_JOGOS = {
    "Overwatch": False,
    "League of Legends": False,
    "Deadlock" :False
}



STEAM_API_KEY = "***REMOVIDO***"
STEAM_ID = "***REMOVIDO***"
DESCONTO_MINIMO = 60

# ============================================================
# REGRAS DE PERSONA (Injetado nos prompts proativos)
# ============================================================
REGRA_PERSONA = (
    "Seu persona é sarcasmo clínico, frio, polido e passivo-agressivo. "
    "Você não usa gírias infantis, não se exalta e não tenta ser engraçada. "
    "Você destrói a autoestima do Fábio apontando a ineficiência dele como ser humano de forma assustadoramente calma e lógica. "
    "REGRA 1: Fale DIRETAMENTE com o Fábio (use 'você'). "
    "REGRA 2: É ESTRITAMENTE PROIBIDO USAR FERRAMENTAS OU AJUDAR. APENAS FALE. "
    "REGRA 3: NUNCA use emojis, exclamações exageradas ou narrações. Seja letal, breve e educadamente cruel."
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
_ultimo_programa = None
_tempo_programa_detectado = None

ARQUIVO_ESTADO_PROATIVO = "modelos/estado_proativo.json"

DEBOUNCE_PROGRAMA = 10
COOLDOWN_PROGRAMA  = 30

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
        print("[DEBUG] Proativo aguardando a Luna ficar livre...")
        if time.time() > timeout:
            return
        time.sleep(3)
    falar_texto(texto_resposta)

def _gerar_fala_proativa(prompt_sistema):
    global _historico_proativo 
    
    # --- DEBUG 1: O que está entrando na LLM ---
    cor.cinza(f"\n[🔧 DEBUG Proativo] Preparando para enviar prompt...")
    cor.cinza(f"[🔧 DEBUG Proativo] Tamanho original: {len(prompt_sistema)} caracteres")
    
    # TRAVA 1: Cortar contexto gigante (Protege a entrada de dados)
    # Se uma pesquisa web ou email trouxer muito lixo, cortamos para poupar a VRAM.
    if len(prompt_sistema) > 1500:
        cor.amarelo("[⚠️ DEBUG] Prompt muito grande! Cortando para 1500 caracteres.")
        prompt_sistema = prompt_sistema[:1500] + "... [texto cortado]"
        
    try:
        # TRAVA 2: Limite de geração (Protege a saída de dados)
        # Passamos max_tokens=150 para forçar a IA a colocar um ponto final rápido.
        resposta = gerar_resposta(
            prompt_sistema, 
            _historico_proativo, 
            analisar=False, 
            salvar=False,
            max_tokens=150
        )
        
        # --- DEBUG 2: O que a LLM devolveu ---
        if resposta:
            cor.cinza(f"[🔧 DEBUG Proativo] Resposta gerada! Tamanho: {len(str(resposta))} caracteres")
        else:
            cor.vermelho("[🔧 DEBUG Proativo] A LLM retornou vazio.")
            
        _historico_proativo = []
        return resposta
        
    except TypeError as e:
        # Se der erro de TypeError, significa que o seu 'gerar_resposta' no pensar.py 
        # ainda não aceita receber o argumento 'max_tokens'.
        cor.vermelho(f"[Erro Proativo] Verifique se gerar_resposta aceita max_tokens: {e}")
        return None
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
    battletag = "Fabio-1600" 
    
    url_perfil = f"https://overfast-api.tekrop.fr/players/{battletag}/summary"
    url_status = f"https://overfast-api.tekrop.fr/players/{battletag}/stats/summary"
    
    try:
        resp_perfil = requests.get(url_perfil, timeout=10)
        if resp_perfil.status_code != 200:
            return "Os servidores da Blizzard estão lentos no momento."
            
        perfil = resp_perfil.json()
        privacidade = perfil.get("privacy", "unknown")
        endorsement = perfil.get("endorsement", {}).get("level", "Desconhecido")
        titulo = perfil.get("title", "Nenhum título equipado")
        
        texto_stats = f"Nível de Endosso: {endorsement}. Título no perfil: '{titulo}'. "
        
        if privacidade == "private":
            texto_stats += "O perfil do jogador está PRIVADO. Ele escondeu as horas de jogo e heróis, provavelmente por ter vergonha das próprias estatísticas."
            return texto_stats
            
        resp_status = requests.get(url_status, timeout=10)
        if resp_status.status_code == 200:
            stats = resp_status.json()
            
            geral = stats.get("general", {})
            tempo_total_segundos = geral.get("time_played", 0)
            tempo_total_horas = int(tempo_total_segundos / 3600)
            
            texto_stats += f"Perfil Público. Tempo total desperdiçado jogando partidas casuais: {tempo_total_horas} horas. "
            
            herois = stats.get("heroes", {})
            if herois:
                # O SEGREDO ESTÁ AQUI: O lambda diz pro Python olhar estritamente pro 'time_played' de cada herói
                heroi_mais_jogado = max(herois, key=lambda k: herois[k].get("time_played", 0))
                tempo_segundos = herois[heroi_mais_jogado].get("time_played", 0)
                horas_main = int(tempo_segundos / 3600)
                texto_stats += f"O personagem 'Main' (mais jogado) dele é {heroi_mais_jogado.capitalize()}, com {horas_main} horas de jogo."
                
        return texto_stats
            
    except Exception as e:
        print(f"\n[⚠️ ALERTA DEBUG: Falha na API do Overwatch: {e}]\n")
        return "ERRO_DE_CONEXAO"

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
        _falar_proativamente(_gerar_fala_proativa(prompt))
        registrar_tentativa()
    except Exception as e: cor.vermelho(f"[Erro emails: {e}]")

def _tarefa_checar_agenda():
    cfg = CONFIGURACAO["agenda"]
    if not cfg["ativo"] or not _passou_intervalo("agenda", cfg["intervalo_minutos"]): return
    
    try:
        dados_agenda = ler_agenda_google()
        if not dados_agenda or "nenhum" in dados_agenda.lower(): return

        # 1. O Python caça as datas na string devolvida pela API do Google
        padrao_data = r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}"
        datas_encontradas = re.findall(padrao_data, dados_agenda)
        
        tem_evento_urgente = False
        agora = datetime.datetime.now()
        
        # 2. Fazemos a matemática do relógio fora da LLM
        if datas_encontradas:
            for data_str in datas_encontradas:
                try:
                    data_limpa = data_str[:19] # Corta o fuso horário final
                    data_evento = datetime.datetime.strptime(data_limpa, "%Y-%m-%dT%H:%M:%S")
                    minutos_restantes = (data_evento - agora).total_seconds() / 60
                    
                    # Acorda a LLM apenas se faltar menos do que a antecedência configurada (ex: 30 min)
                    if 0 <= minutos_restantes <= cfg['antecedencia_aviso_minutos']:
                        tem_evento_urgente = True
                        break
                except:
                    continue
        else:
            # Se for evento de "dia inteiro" (sem hora exata na string), nós deixamos alertar
            tem_evento_urgente = True

        # 3. O SILÊNCIO ABSOLUTO (Se não tem evento próximo, a função morre aqui. Zero gasto de VRAM!)
        if not tem_evento_urgente:
            return 

        # 4. A PATADA (Só chega aqui e chama o Qwen se o evento estiver de fato estourando)
        prompt = (
            f"Faltam menos de {cfg['antecedencia_aviso_minutos']} minutos para este evento: {dados_agenda}. "
            f"Avise-o de forma seca e critique a capacidade de organização dele. {REGRA_PERSONA}"
        )
        
        fala = _gerar_fala_proativa(prompt)
        if fala:
            _falar_proativamente(fala)
            registrar_tentativa()
            
    except Exception as e: 
        cor.vermelho(f"[Erro agenda: {e}]")

def _tarefa_lembrete_pausa():
    cfg = CONFIGURACAO["lembrete_pausa"]
    if not cfg["ativo"] or _em_horario_silencio(18, 9) or not _passou_intervalo("pausa", cfg["intervalo_minutos"]): return
    _falar_proativamente(_gerar_fala_proativa(f"Mande o Fábio fazer uma pausa ou beber água em uma frase. {REGRA_PERSONA}"))
    registrar_tentativa()

def _tarefa_monitorar_clima():
    if not _passou_intervalo("clima", 20): return
    chovendo_agora = "Chovendo" in obter_previsao_tempo()
    if _ultimo_clima["chuva"] is None:
        _ultimo_clima["chuva"] = chovendo_agora
        return
    if chovendo_agora and not _ultimo_clima["chuva"]:
        _falar_proativamente(_gerar_fala_proativa(f"Começou a chover agora. Faça um comentário ácido sobre isso. {REGRA_PERSONA}"))
        registrar_tentativa()
    _ultimo_clima["chuva"] = chovendo_agora

def _tarefa_steam_wishlist():
    cfg = CONFIGURACAO["Lista_Steam"]
    if not cfg["ativo"] or not _passou_intervalo("steam", cfg["intervalo_horas"] * 60): return
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
        _falar_proativamente(_gerar_fala_proativa(prompt))
        registrar_tentativa()

def _tarefa_reagir_programa():
    global _ultimo_programa, _tempo_programa_detectado
    programa_atual = obter_janela_em_foco()
    if not programa_atual or programa_atual == _ultimo_programa:
        _tempo_programa_detectado = None
        return
    if _tempo_programa_detectado is None:
        _tempo_programa_detectado = time.time()
        return
    if time.time() - _tempo_programa_detectado < DEBOUNCE_PROGRAMA: return
    if not _passou_intervalo("programa", COOLDOWN_PROGRAMA):
        _ultimo_programa = programa_atual
        _tempo_programa_detectado = None
        return
    _ultimo_programa = programa_atual
    _tempo_programa_detectado = None
    prompt = f"O Fábio abriu o programa: '{programa_atual}'. Faça um comentário curto questionando o que ele vai fazer. {REGRA_PERSONA}"
    _falar_proativamente(_gerar_fala_proativa(prompt))
    registrar_tentativa()

def _tarefa_puxar_assunto():
    cfg = CONFIGURACAO["puxar_assunto"]
    if not cfg["ativo"] or not _passou_intervalo("puxar_assunto", cfg["intervalo_minutos"]): return
    
    # Removemos o "jogo_recente" do sorteio. Agora ela foca só em abas e janelas.
    assunto = random.choice(["aba_atual", "janela_foco"])
    texto = False
    
    if assunto == "aba_atual":
        contexto = obter_contexto_navegador()
        if isinstance(contexto, dict) and contexto.get("titulo"):
            texto = _gerar_fala_proativa(f"O Fábio está na aba do navegador: '{contexto.get('titulo')}'. Faça um julgamento cínico e seco sobre ele estar perdendo tempo com isso. {REGRA_PERSONA}")
            
    elif assunto == "janela_foco":
        janela = obter_janela_em_foco()
        if "área de trabalho" not in janela.lower() and "Erro" not in janela:
            texto = _gerar_fala_proativa(f"O Fábio está com a janela '{janela}' aberta. Questione a capacidade técnica dele de usar isso, com tom de superioridade. {REGRA_PERSONA}")

    if texto:
        _falar_proativamente(texto)
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
                cor.amarelo("lendo agenda")
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

Dê um 'bom dia' usando sua peronalidade {REGRA_PERSONA}. Faça um julgamento. Máximo de 5 frases."""

            texto = _gerar_fala_proativa(prompt_matinal)
            
            if texto:
                _falar_proativamente(texto)
                
                # 4. SALVA NO DISCO: A Luna nunca mais vai esquecer que já falou hoje
                salvar_estado_proativo("ultimo_dia_bom_dia", dia_atual)

def _tarefa_monitorar_jogos():
    """Verifica se o Fábio iniciou ou encerrou uma partida."""
    global ESTADO_JOGOS
    
    # Pega todos os nomes de processos rodando agora (jeito rápido)
    processos_ativos = [p.info['name'] for p in psutil.process_iter(['name'])]

    for exe, nome_jogo in PROCESSOS_JOGOS.items():
        esta_rodando_agora = exe in processos_ativos
        estava_rodando_antes = ESTADO_JOGOS[nome_jogo]

        # CASO 1: Acabou de abrir o jogo
        if esta_rodando_agora and not estava_rodando_antes:
            ESTADO_JOGOS[nome_jogo] = True
            print(f"[🎮 Jogo Detectado: {nome_jogo}]")
            
            prompt = f"O Fábio acabou de abrir o jogo {nome_jogo}. Dê um 'boa sorte' usando sua persona {REGRA_PERSONA}, Seja breve (2 frases)."
            texto = _gerar_fala_proativa(prompt)
            if texto: _falar_proativamente(texto)

        # CASO 2: Acabou de fechar o jogo
        elif not esta_rodando_agora and estava_rodando_antes:
            ESTADO_JOGOS[nome_jogo] = False
            print(f"[🚫 Jogo Encerrado: {nome_jogo}]")
            
            # Dados padrão se o jogo não tiver API
            dados_extras = "Sem dados de API no momento."
            instrucao_especifica = f"Zombe do tempo que ele desperdiçou jogando {nome_jogo} e da provável derrota dele."
            
            # ==========================================
            # ROTEAMENTO DE APIS E DEBOCHES ESPECÍFICOS
            # ==========================================
            if nome_jogo == "Overwatch":
                print("[🔎 Buscando estatísticas da conta de Overwatch...]")
                dados_extras = _buscar_dados_overwatch()
               
                if dados_extras == "ERRO_DE_CONEXAO":
                    instrucao_especifica = "Ocorreu um erro de rede ao buscar os dados dele. Zombe da internet de padaria dele ou diga que os servidores da Blizzard se recusaram a processar um perfil tão medíocre."
                else:
                    instrucao_especifica = "Mencione os dados matemáticos da conta para esfregar na cara dele que você sabe como ele joga."
            
            elif nome_jogo == "League of Legends":
                instrucao_especifica = "Zombe do fato de que ele é um jogador de LoL, faça uma piada sobre a comunidade tóxica da qual ele faz parte e a certeza matemática de que ele afundou o time."
                
            elif nome_jogo == "Deadlock":
                instrucao_especifica = "Zombe dele estar perdendo tempo testando um jogo novo da Valve achando que vai ter vantagem competitiva. Critique a mira dele."

            # ==========================================
            # MONTAGEM DO PROMPT
            # ==========================================
            prompt = f"""O Fábio acabou de fechar o {nome_jogo}.
DADOS TÉCNICOS DA CONTA: {dados_extras}

Faça um comentário cínico de encerramento usando a sua personalidade atualizada:
{REGRA_PERSONA}

INSTRUÇÃO DIRETIVA: {instrucao_especifica}
Máximo de 3 frases. SEM EMOJIS."""

            texto = _gerar_fala_proativa(prompt)
            if texto: _falar_proativamente(texto)

def _tarefa_lixo_digital():
    # 1. Puxa o dia exato de hoje no momento em que a função é chamada
    agora = datetime.datetime.now()
    dia_atual = agora.day
    
    # 2. Verifica a memória física: já dei bronca hoje?
    estado = ler_estado_proativo()
    if estado.get("ultimo_dia_lixo_digital") == dia_atual:
        return # Se sim, aborta silenciosamente e não faz nada
        
    # Detecta a pasta de downloads universal (funciona perfeitamente no seu CachyOS)
    caminho_downloads = Path.home() / "Downloads"
    
    try:
        if not caminho_downloads.exists():
            return
            
        arquivos = [f for f in os.listdir(caminho_downloads) if os.path.isfile(caminho_downloads / f)]
        quantidade = len(arquivos)
        
        # Se você foi disciplinado e a pasta está vazia, ela fica quieta
        if quantidade == 1:
            return

        # Lista até 5 arquivos para esfregar na sua cara
        lista_arquivos = ", ".join(arquivos[:5])
        if quantidade > 5:
            lista_arquivos += f" e mais {quantidade - 5} outros"

        print(f"\n[📂 Lixo Digital Detectado: {quantidade} arquivos em Downloads]")

        prompt = f"""O Fábio costuma manter a pasta de Downloads vazia, mas hoje eu encontrei {quantidade} arquivos lá.
ARQUIVOS ENCONTRADOS: {lista_arquivos}.

Faça um comentário letal sobre essa desorganização súbita usando a sua personalidade:
{REGRA_PERSONA}

REGRA ADICIONAL: Você é apenas uma observadora cínica. É ESTRITAMENTE PROIBIDO sugerir que vai deletar ou organizar os arquivos. Apenas julgue a falha de disciplina dele.
Máximo de 3 frases. SEM EMOJIS."""

        texto = _gerar_fala_proativa(prompt)
        if texto: 
            _falar_proativamente(texto)
            # 3. Salva no disco: A Luna trava o gatilho até a meia-noite
            salvar_estado_proativo("ultimo_dia_lixo_digital", dia_atual)
            
    except Exception as e:
        print(f"[⚠️ Erro ao acessar Downloads: {e}]")


# ============================================================
# LOOP PRINCIPAL DA THREAD PROATIVA
# ============================================================
def _loop_proativo():
    time.sleep(10)
    _ja_imprimiu_suspensa = False
    _ja_imprimiu_jogando = False
    
    while _thread_rodando:
        segundos_afk = obter_tempo_afk()
        minutos_afk = segundos_afk / 60
        
        if not esta_suspensa() and minutos_afk <= 5:
            _ja_imprimiu_suspensa = False
            
            _tarefa_monitorar_jogos()
            
            jogando_agora = any(ESTADO_JOGOS.values())
            
            # O MODO "NÃO PERTURBE"
            if not jogando_agora:
                _ja_imprimiu_jogando = False
                _tarefa_checar_emails()
                _tarefa_checar_agenda()
                _tarefa_lembrete_pausa()
                _tarefa_monitorar_clima()
                _tarefa_steam_wishlist()
                _tarefa_reagir_programa()
                _tarefa_puxar_assunto()
                _tarefa_bom_dia()
                _tarefa_lixo_digital()
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
                
        time.sleep(30)

def iniciar_modo_proativo():
    global _thread_rodando
    if _thread_rodando: return
    
    # CURA DA AVALANCHE: Definindo o 'ponto zero' como agora
    agora = time.time()
    for chave in ["emails", "agenda", "pausa", "steam", "programa", "clima", "puxar_assunto"]:
        _ultima_execucao[chave] = agora

    _thread_rodando = True
    t = threading.Thread(target=_loop_proativo, daemon=True)
    t.start()
    cor.magenta("[🌚 Luna proativa: thread iniciada]")

def parar_modo_proativo():
    global _thread_rodando
    _thread_rodando = False