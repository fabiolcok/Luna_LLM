#habilidades.py

from youtube_transcript_api import YouTubeTranscriptApi
import pyperclip
import re
import datetime
import requests
import calendar
import spotipy
import pyautogui
import base64
import io
from spotipy.oauth2 import SpotifyOAuth
import pywhatkit as kit
import imaplib
import email
import psutil
from email.header import decode_header
import asyncio
import websockets
import json
import threading
import os
import ctypes
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from ddgs import DDGS
import psutil
import time
import modelos.cores as cor
import urllib.parse
import webbrowser
from bs4 import BeautifulSoup
from dotenv import load_dotenv

from google import genai
from google.genai import types
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

load_dotenv()



"""
MÓDULO DE HABILIDADES (FERRAMENTAS) DA LUNA
---------------------------------------------------------
Este arquivo contém todas as funções de "Pull" (Reativas).
São as ferramentas que a Luna pode decidir acionar por conta própria quando o Fábio 
faz uma pergunta direta ou quando o Fabio fala um termo que ativa a habilidade.


Funções Disponíveis:
- ler_link_copiado(): Le o que esta no ctrl + C 
- ler_texto_selecionado(): Um massete para que a propia llm faz o ctrl + c sem que o usuario precise apertar.
- extrair_id_youtube(url): Pega um link cheio de lixo e extrai só o ID do vídeo
- obter_transcricao(url): Baixa o texto completo do vídeo sem precisar baixar o áudio/vídeo
- obter_creds_google(): Faz os paranaues dos tokens do google api (para usar o google agenda)
- ler_agenda_google(): manda para a LLM os eventos da agenda, limitado a 30 dias
- adicionar_evento_google(resumo, data_hora_iso): adiciona eventos na agenda do google
- obter_previsao_tempo(): Busca o clima atual usando a API gratuita do Open-Meteo
- tocar_musica_spotify(nome_musica): procura a musica no spotfy e da play
- pausar_spotify(): pausa a musica spotfy
- proxima_musica_spotify(): passa a musica no spotfy
- gerenciador_spotify(acao, nome_musica=""): Função gerente que recebe o comando da IA e distribui para as funções reais. (tocar_musica_spotify,pausar_spotify,proxima_musica_spotify)
- capturar_tela_base64() -> str: Tira um print da tela e retorna como string base64 (JPEG comprimido).
- analisar_imagem_gemini(imagem_base64, pergunta): Envia a captura de tela para a API Gemini e retorna a descrição.
- executar_analise_aba(): Combina obter_contexto_navegador + analisar_imagem_gemini para resumir a aba ativa.
- pesquisar_na_web(pergunta): Pesquisa no DuckDuckGo, pega os 3 primeiros resultados e lê o conteúdo completo do site principal.
- enviar_mensagem_whatsapp(destinatario, mensagem): Envia WhatsApp. O destinatário pode ser um nome da agenda ou um número.
- checar_emails_nao_lidos(limite=5): Conecta no e-mail, busca as últimas mensagens não lidas e retorna Remetente e Assunto.
- controlar_firefox_via_extensao(acao: str, parametro: str = ""):Função que a Luna vai chamar para controlar o navegador (junto com as funcoes _manipulador conexão,_iniciar servidor,_rodar_thread_websocket,iniciar_servidor_extensao)
- obter_contexto_navegador(): Pede à extensão o pacote completo de dados da aba ativa
- listar_processos_pesados(): Retorna os 5 processos que mais estão consumindo RAM/CPU no momento.
- abrir_programa(nome_programa): Permite a Luna abrir jogos ou aplicativos.
- matar_processo(nome_processo): Permite a Luna forçar o fechamento de um programa que travou.
- obter_janela_em_foco(): Descobre qual programa ou janela está em primeiro plano no Windows do Fábio.
- desenhar_imagem(prompt_imagem): Gera uma imagem baseada na descrição da Luna e abre no navegador do Fábio.
- alternar_mute(): Muta ou desmuta o volume do sistema via pycaw (Windows).
- ler_url_especifica(url): Faz fetch de uma URL, extrai parágrafos com BeautifulSoup e retorna até 15000 chars de texto limpo.

"""


#=======================================================
#       FERRAMENTA LER O QUE COPIEI (CTRL + C)
#=======================================================

def ler_link_copiado():
    #Lê a área de transferência do seu sistema (o que você deu Ctrl+C)
    return pyperclip.paste()

def ler_texto_selecionado():
    clipboard_antigo = pyperclip.paste()
    
    pyautogui.hotkey('ctrl', 'c')
    time.sleep(0.1) # Dá tempo do Windows processar
    texto_copiado = pyperclip.paste()
    
    # Restaura o clipboard antigo (opcional, para não bagunçar o PC)
    # pyperclip.copy(clipboard_antigo) 
    
    if texto_copiado and texto_copiado != clipboard_antigo:
        return f"Texto selecionado: '{texto_copiado}'"
    return "Erro: nenhum texto selecionado."

#=======================================================
#               FERRAMENTA YOUTUBE
#=======================================================

def extrair_id_youtube(url):
    #Pega um link cheio de lixo e extrai só o ID do vídeo
    
    padrao = r'(?:v=|\/)([0-9A-Za-z_-]{11}).*'
    match = re.search(padrao, url)
    return match.group(1) if match else None

def obter_transcricao(url):
    #Baixa o texto completo do vídeo sem precisar baixar o áudio/vídeo

    try:
        video_id = extrair_id_youtube(url)
        if not video_id:
            return "ERRO: O link fornecido não parece ser do YouTube."

        ytt_api = YouTubeTranscriptApi()
        lista_disponivel = ytt_api.list(video_id)
        
        try:
            # Tenta achar PT-BR, PT ou Inglês
            legenda_escolhida = lista_disponivel.find_transcript(['pt-BR', 'pt', 'en', 'en-US'])
        except:
            # Se não achar nenhuma dessas, pega a primeira que existir no vídeo
            legenda_escolhida = next(iter(lista_disponivel))
            
        lista_transcricao = legenda_escolhida.fetch()
        texto_completo = " ".join([linha.text if hasattr(linha, 'text') else linha['text'] for linha in lista_transcricao])
        
        return texto_completo[:5000] 
        
    except Exception as e:
        return f"ERRO: Detalhe técnico - {e}"  

#=======================================================
#               FERRAMENTA GOOGLE AGENDA
#=======================================================

# Local aonde esta o token do google
caminho_token = r"modelos\token.json" 

def obter_creds_google():
    SCOPES = ['https://www.googleapis.com/auth/calendar']
    creds = None
    
    # Tenta carregar o token existente
    if os.path.exists(caminho_token):
        creds = Credentials.from_authorized_user_file(caminho_token, SCOPES)
    
    # Se não existe ou é inválido
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception:
                creds = None # Força re-login se a renovação falhar
        
        if not creds:
            # O SEGREDO: prompt='consent' e access_type='offline' garantem o Refresh Token
            # Certifique-se que o credentials.json está na pasta modelos
            caminho_credentials = r"modelos\credentials.json" 
            flow = InstalledAppFlow.from_client_secrets_file(caminho_credentials, SCOPES)
            creds = flow.run_local_server(port=0, prompt='consent', access_type='offline')
        
        # Salva o token (novo ou renovado)
        with open(caminho_token, 'w') as token:
            token.write(creds.to_json())
            
    return creds

def ler_agenda_google():
    cor.amarelo("[🌚📖 Acessando Agenda Google...]")
    """Conecta no Google e retorna os eventos dos próximos 30 dias."""
    try:
        creds = obter_creds_google()
        service = build('calendar', 'v3', credentials=creds)
        
        agora = datetime.datetime.now()
        inicio_iso = agora.isoformat() + 'Z'
        fim_iso = (agora + datetime.timedelta(days=30)).isoformat() + 'Z'
        
        events_result = service.events().list(
            calendarId='primary', 
            timeMin=inicio_iso,
            timeMax=fim_iso,
            singleEvents=True,
            orderBy='startTime').execute()
            
        events = events_result.get('items', [])
        
        if not events:
            return "A sua agenda está completamente vazia para os próximos 30 dias."
            
        agenda_texto = "Aqui estão os seus compromissos:\n"
        for event in events:
            inicio_raw = event['start'].get('dateTime', event['start'].get('date'))
            resumo = event['summary']
            agenda_texto += f"- {resumo} | {inicio_raw}\n"
            
        return agenda_texto
        
    except Exception as e:
        return f"Erro ao acessar a agenda: {e}"

def adicionar_evento_google(resumo, data_hora_iso):
    """Adiciona um evento à agenda."""
    try:
        creds = obter_creds_google()
        service = build('calendar', 'v3', credentials=creds)

        inicio = datetime.datetime.fromisoformat(data_hora_iso)
        fim = (inicio + datetime.timedelta(hours=1)).isoformat()

        evento = {
            'summary': resumo,
            'start': {'dateTime': data_hora_iso, 'timeZone': 'America/Sao_Paulo'},
            'end': {'dateTime': fim, 'timeZone': 'America/Sao_Paulo'},
        }

        service.events().insert(calendarId='primary', body=evento).execute()
        return f"Sucesso! O evento '{resumo}' foi criado para {data_hora_iso}."

    except Exception as e:
        return f"Erro ao adicionar evento: {e}"
    
#=======================================================
#               FERRAMENTA CLIMA
#=======================================================    

def obter_previsao_tempo():
    """Busca o clima atual usando a API gratuita do Open-Meteo"""
    latitude = -15.7343385  # Itapoa parque
    longitude = -47.7771159
    
    url = f"https://api.open-meteo.com/v1/forecast?latitude={latitude}&longitude={longitude}&current=temperature_2m,relative_humidity_2m,precipitation,weather_code&timezone=America%2FSao_Paulo"
    
    try:
        resposta = requests.get(url, timeout=5)
        dados = resposta.json()
        
        atual = dados.get('current', {})
        temp = atual.get('temperature_2m')
        chuva = atual.get('precipitation')
        
        # Mapeamento simplificado de códigos de clima (WMO)
        codigo = atual.get('weather_code', 0)
        if codigo in [0, 1]: condicao = "Céu limpo"
        elif codigo in [2, 3]: condicao = "Nublado"
        elif codigo in [51, 53, 55, 61, 63, 65, 80, 81, 82]: condicao = "Chovendo"
        elif codigo in [71, 73, 75]: condicao = "Nevando"
        elif codigo in [95, 96, 99]: condicao = "Tempestade"
        else: condicao = "Tempo instável"
            
        texto_clima = f"O clima agora na sua cidade é: {condicao}, com {temp}°C. "
        if chuva > 0:
            texto_clima += f"Está chovendo {chuva}mm no momento."
        else:
            texto_clima += "Não está chovendo agora."
            
        return texto_clima
        
    except Exception as e:
        return "Aviso: Não foi possível obter os dados do clima no momento."
    
#=======================================================
#               FERRAMENTA SPOTFY
#=======================================================    

SPOTIPY_CLIENT_ID     = os.getenv("SPOTIPY_CLIENT_ID", "")
SPOTIPY_CLIENT_SECRET = os.getenv("SPOTIPY_CLIENT_SECRET", "")
SPOTIPY_REDIRECT_URI  = os.getenv("SPOTIPY_REDIRECT_URI", "http://127.0.0.1:8080")

def tocar_musica_spotify(nome_musica):
    """Busca uma música e dá o play no dispositivo ativo do Spotify"""
    try:
        # Autenticação (pede permissão para ler e modificar o player)
        auth_manager = SpotifyOAuth(
            client_id=SPOTIPY_CLIENT_ID,
            client_secret=SPOTIPY_CLIENT_SECRET,
            redirect_uri=SPOTIPY_REDIRECT_URI,
            scope="user-modify-playback-state,user-read-playback-state",
            cache_path=r"G:\Projetos\Luna_LLM\modelos\spotify_cache"
        )
        sp = spotipy.Spotify(auth_manager=auth_manager)
        
        resultado = sp.search(q=nome_musica, limit=1, type='track')
        if not resultado['tracks']['items']:
            return f"Não encontrei a música '{nome_musica}'."
            
        musica = resultado['tracks']['items'][0]
        uri_musica = musica['uri']
        
        # 1. PEGA TODOS OS APARELHOS LOGADOS
        dispositivos = sp.devices()
        if not dispositivos['devices']:
            return "O Spotify precisa estar aberto em algum lugar!"

        # 2. TENTA ACHAR O ATIVO
        id_dispositivo = None
        for d in dispositivos['devices']:
            if d['is_active']:
                id_dispositivo = d['id']
                break
        
        # 3. SE NÃO TIVER ATIVO, PEGA O PRIMEIRO DA LISTA (FORÇA O ACORDO)
        if not id_dispositivo:
            id_dispositivo = dispositivos['devices'][0]['id']
            cor.amarelo(f"[Forçando reprodução no dispositivo: {dispositivos['devices'][0]['name']}]")

        # 4. PASSA O device_id NO PLAY
        sp.start_playback(device_id=id_dispositivo, uris=[uri_musica])
        return f"Tocando agora: {musica['name']} - {musica['artists'][0]['name']}"
        
    except Exception as e:
        return f"Erro no Spotify: {e}"
    
def pausar_spotify():
    """Pausa a música atual no Spotify"""
    try:
        sp = spotipy.Spotify(auth_manager=SpotifyOAuth(client_id=SPOTIPY_CLIENT_ID, client_secret=SPOTIPY_CLIENT_SECRET, redirect_uri=SPOTIPY_REDIRECT_URI, scope="user-modify-playback-state",cache_path=r"G:\Projetos\Luna_LLM\modelos\spotify_cache"))
        sp.pause_playback()
        return "Música pausada."
    except Exception as e: return f"Erro ao pausar: {e}"

def proxima_musica_spotify():
    """Pula para a próxima música no Spotify"""
    try:
        sp = spotipy.Spotify(auth_manager=SpotifyOAuth(client_id=SPOTIPY_CLIENT_ID, client_secret=SPOTIPY_CLIENT_SECRET, redirect_uri=SPOTIPY_REDIRECT_URI, scope="user-modify-playback-state",cache_path=r"G:\Projetos\Luna_LLM\modelos\spotify_cache"))
        sp.next_track()
        return "Pulando para a próxima música."
    except Exception as e: return f"Erro ao pular música: {e}"

def gerenciador_spotify(acao, nome_musica=""):
    """
    Função gerente que recebe o comando da IA e distribui para as funções reais.
    """
    if acao == "tocar":
        if not nome_musica:
            return "Aviso para a IA: O usuário não disse o nome da música. Peça a ele."
        return tocar_musica_spotify(nome_musica)
        
    elif acao == "pausar":
        return pausar_spotify()
        
    elif acao == "proxima":
        return proxima_musica_spotify()
        
    else:
        return "Ação do Spotify não reconhecida."


#=======================================================
#               FERRAMENTA LER A TELA (PRINT)
#=======================================================    

def capturar_tela_base64() -> str:
    """
    Tira um print da tela e retorna como string base64 (JPEG comprimido).
    JPEG com qualidade 75 mantém o texto legível e pesa ~3x menos que PNG.
    """
    img = pyautogui.screenshot()

    buffer = io.BytesIO()
    img.save(buffer, format="JPEG", quality=90)
    #img.save(buffer, format="PNG")
    buffer.seek(0)

    return base64.b64encode(buffer.read()).decode("utf-8")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GROQ_API_KEY   = os.getenv("GROQ_API_KEY", "")

def analisar_imagem_gemini(imagem_base64: str, pergunta: str = "") -> str:
    client = genai.Client(api_key=GEMINI_API_KEY)
    
    import base64
    imagem_bytes = base64.b64decode(imagem_base64)
    
    prompt = pergunta if pergunta else "Descreva o que está na tela."
    prompt += " Responda de forma direta e concisa, sem markdown, sem listas."
    
    resposta = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=[
            types.Part.from_bytes(data=imagem_bytes, mime_type="image/jpeg"),
            prompt
        ]
    )
    return resposta.text

#=======================================================
#               FERRAMENTA LER URL ESPECÍFICA
#=======================================================

def ler_url_especifica(url: str) -> str:
    """Faz o fetch de uma URL e retorna o texto extraído dos parágrafos."""
    cor.amarelo(f"[🌚🌎 Lendo URL: '{url}']")
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        resposta = requests.get(url, headers=headers, timeout=8)
        resposta.raise_for_status()

        soup = BeautifulSoup(resposta.text, 'html.parser')
        for tag in soup(['script', 'style', 'nav', 'footer', 'header']):
            tag.decompose()

        paragrafos = soup.find_all('p')
        texto = "\n".join([p.get_text().strip() for p in paragrafos if len(p.get_text().strip()) > 30])

        if not texto.strip():
            texto = soup.get_text(separator='\n', strip=True)

        return texto[:15000]
    except Exception as e:
        return f"Erro ao ler URL: {e}"


#=======================================================
#               FERRAMENTA PESQUISAR DUCK DUCK GO
#=======================================================

def pesquisar_na_web(pergunta):
    """Pesquisa no DuckDuckGo, pega os 3 primeiros resultados e lê o conteúdo completo do site principal."""
    cor.amarelo(f"[🌚🌎 Pesquisando na web por: '{pergunta}']")
    try:
        # Busca os 3 primeiros resultados
        resultados = DDGS().text(pergunta, region='br-pt', safesearch='moderate', max_results=3)
        
        if not resultados:
            return "Aviso: A pesquisa não retornou nenhum resultado."
            
        texto_compilado = "Resumo dos resultados da pesquisa:\n\n"
        primeiro_link = None
        
        for i, res in enumerate(resultados, 1):
            titulo = res.get('title', 'Sem título')
            resumo = res.get('body', 'Sem descrição')
            link = res.get('href', '')
            texto_compilado += f"[{i}] {titulo}\nResumo: {resumo}\n\n"
            
            # Salva o primeiro link válido para extração profunda
            if i == 1 and link:
                primeiro_link = link

        # Scraping leve: entra no primeiro link para ler o artigo/documentação
        if primeiro_link:
            try:
                headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
                resposta_site = requests.get(primeiro_link, headers=headers, timeout=5)
                
                # Só processa se a página responder com sucesso
                if resposta_site.status_code == 200:
                    soup = BeautifulSoup(resposta_site.text, 'html.parser')
                    
                    # Pega apenas os parágrafos reais (ignora menus e barras laterais)
                    paragrafos = soup.find_all('p')
                    texto_pagina = "\n".join([p.get_text().strip() for p in paragrafos if len(p.get_text().strip()) > 30])
                    
                    # Limita a 3000 caracteres para poupar a memória de contexto do Qwen
                    texto_pagina = texto_pagina[:3000] + "...\n(Fim do artigo)" if len(texto_pagina) > 3000 else texto_pagina
                    
                    if texto_pagina.strip():
                        texto_compilado += f"--- CONTEÚDO PROFUNDO DO SITE PRINCIPAL ({primeiro_link}) ---\n{texto_pagina}\n"
            except Exception as e_site:
                texto_compilado += f"\n(Aviso: O site principal bloqueou a leitura do artigo completo: {e_site})\n"
                
        return texto_compilado
        
    except Exception as e:
        return f"Erro ao tentar acessar a internet: {e}"

#=======================================================
#               FERRAMENTA WHATSAPP
#=======================================================    

#agenda:
CONTATOS_WHATSAPP = {
    "caian": "5500000000000",
    "amor": "5500000000000",
    "fábio": "5500000000000",
    "mim": "5500000000000",
    "eduardo": "5500000000000",
    "filha": "5500000000000",
    "fausto": "5500000000000",
}

def enviar_mensagem_whatsapp(destinatario, mensagem):
    """Envia WhatsApp. O destinatário pode ser um nome da agenda ou um número."""
    try:
        destinatario_limpo = destinatario.lower().strip()
        
        # 1. Checa se o nome existe na nossa agenda
        if destinatario_limpo in CONTATOS_WHATSAPP:
            numero_final = CONTATOS_WHATSAPP[destinatario_limpo]
            cor.amarelo(f"[📱 Contato reconhecido: {destinatario_limpo} -> {numero_final}]")
            
        # 2. Se não for um nome da agenda, assume que o usuário ditou o número
        else:
            # Remove espaços e traços que a IA possa ter colocado
            numero_final = destinatario_limpo.replace(" ", "").replace("-", "")
            cor.amarelo(f"[📱 Enviando para número avulso: {numero_final}]")

        # Adiciona o código do Brasil (+55) se o número não tiver
        if not numero_final.startswith("+55"):
            numero_final = f"+55{numero_final}"

        mensagem_com_assinatura = f"🌚 *Luna:*\n\n{mensagem}"
            
        # Envia a mensagem!
        kit.sendwhatmsg_instantly(numero_final, mensagem_com_assinatura, wait_time=20, tab_close=True, close_time=3)
        return f"Mensagem enviada com sucesso para {destinatario}."
        
    except Exception as e:
        return f"Erro ao tentar enviar o WhatsApp: {e}"

#=======================================================
#               FERRAMENTA GMAIL
#=======================================================  


#📧 CONFIGURAÇÕES DE E-MAIL
EMAIL_USUARIO = os.getenv("EMAIL_USUARIO", "")
EMAIL_SENHA   = os.getenv("EMAIL_SENHA", "")
SERVIDOR_IMAP = "imap.gmail.com"

def checar_emails_nao_lidos(limite=5):
    """Conecta no e-mail, busca as últimas mensagens não lidas e retorna Remetente e Assunto."""
    
    cor.amarelo("[🌚📧 Acessando Caixa de Entrada...]")
    
    try:
        # Conecta ao servidor e faz login
        mail = imaplib.IMAP4_SSL(SERVIDOR_IMAP)
        mail.login(EMAIL_USUARIO, EMAIL_SENHA)
        
        # Seleciona apenas a Caixa de Entrada normal
        mail.select("inbox")
        
        # Busca apenas os e-mails NÃO LIDOS ("UNSEEN")
        status, mensagens = mail.search(None, "UNSEEN")
        
        if status != "OK" or not mensagens[0]:
            return "Aviso para a IA: Não há novos e-mails não lidos na caixa de entrada do Fábio."
            
        lista_ids = mensagens[0].split()
        ids_recentes = lista_ids[-limite:] # Pega apenas os últimos X e-mails
        
        resumo_emails = "Lista de e-mails não lidos do Fábio:\n\n"
        
        for id_email in ids_recentes:
            _, msg_data = mail.fetch(id_email, "(RFC822)")
            for response_part in msg_data:
                if isinstance(response_part, tuple):
                    msg = email.message_from_bytes(response_part[1])
                    
                    # Decodifica o Assunto e Remetente
                    assunto, encoding = decode_header(msg["Subject"])[0]
                    if isinstance(assunto, bytes):
                        assunto = assunto.decode(encoding if encoding else "utf-8", errors='ignore')
                    remetente = msg.get("From")
                    
                    resumo_emails += f"- De: {remetente}\n- Assunto: {assunto}\n\n"
                    
        mail.logout()

        resumo_emails += (
            "\n[AVISO DE SISTEMA OBRIGATÓRIO PARA A LUNA]: "
            "Você só tem acesso ao Remetente e ao Assunto. O corpo do e-mail NÃO foi baixado para "
            "poupar processamento e proteger a privacidade. NUNCA tente adivinhar ou inventar o conteúdo "
            "da mensagem. Se o Fábio perguntar o que está escrito dentro do e-mail, diga explicitamente "
            "que o seu sistema só permite ler o remetente e o assunto."
        )

        return resumo_emails
    
    except Exception as e:
        return f"Erro ao tentar acessar os e-mails: {e}"
    


#=======================================================
#               FERRAMENTA CONTROLAR FIREFOX
#=======================================================  

_conexao_ativa = None
_resposta_pendente = None
_evento_resposta = threading.Event()
_loop_websocket = None

import logging
_logger_ws_silencioso = logging.getLogger("websockets.luna")
_logger_ws_silencioso.addHandler(logging.NullHandler())
_logger_ws_silencioso.propagate = False
_logger_ws_silencioso.setLevel(logging.CRITICAL)

async def _manipulador_conexao(websocket):
    global _conexao_ativa, _resposta_pendente
    cor.amarelo("[🌐 Firefox conectado à 🌚 Luna com sucesso!]")
    _conexao_ativa = websocket
    try:
        # Fica ouvindo as mensagens (respostas) que a extensão mandar
        async for mensagem in websocket:
            _resposta_pendente = mensagem
            _evento_resposta.set() # Avisa a thread principal que a resposta chegou
    except websockets.exceptions.ConnectionClosed:
        cor.vermelho("[❌ Firefox desconectado]")
    finally:
        _conexao_ativa = None

async def _iniciar_servidor():
    async with websockets.serve(_manipulador_conexao, "127.0.0.1", 8765, logger=_logger_ws_silencioso):
        await asyncio.Future()  # Roda para sempre

def _rodar_thread_websocket():
    global _loop_websocket
    _loop_websocket = asyncio.new_event_loop()
    asyncio.set_event_loop(_loop_websocket)
    _loop_websocket.run_until_complete(_iniciar_servidor())

def iniciar_servidor_extensao():
    """Chame isso no main.py para ligar o servidor em background"""
    t = threading.Thread(target=_rodar_thread_websocket, daemon=True)
    t.start()

def controlar_firefox_via_extensao(acao: str, parametro: str = ""):
    """Função que a Luna vai chamar para controlar o navegador"""
    global _resposta_pendente

    if not _conexao_ativa or not _loop_websocket:
        return "Erro: O Firefox não está conectado no momento. Peça ao Fábio para abrir o navegador."

    # Garante que abrir_url sempre receba uma URL válida —
    # se o modelo mandar só um nome (ex: "Wikipedia"), converte em busca do Google.
    if acao == "abrir_url" and parametro and not parametro.startswith("http"):
        parametro = f"https://www.google.com/search?q={urllib.parse.quote(parametro)}"

    comando = json.dumps({"acao": acao, "parametro": parametro})
    
    # Prepara para esperar a resposta
    _evento_resposta.clear()
    _resposta_pendente = None

    # Dispara a mensagem do Python para o Javascript de forma segura
    asyncio.run_coroutine_threadsafe(_conexao_ativa.send(comando), _loop_websocket)

    # Aguarda a extensão responder (timeout de 10s para a Luna não ficar travada)
    se_respondeu = _evento_resposta.wait(timeout=10.0)

    if se_respondeu:
        return _resposta_pendente
    else:
        return "Erro: O Firefox demorou muito para responder à ação."
    
def obter_contexto_navegador():
    """Pede à extensão o pacote completo de dados da aba ativa"""
    # Usamos a função base que você já tem para enviar o comando
    resposta = controlar_firefox_via_extensao("contexto_total")
    
    try:
        # Tenta transformar a string JSON que veio do JavaScript em um dicionário Python
        dados = json.loads(resposta)
        return dados
    except json.JSONDecodeError:
        # Se não for JSON (ex: a extensão mandou um erro tipo "Firefox fechado"), retorna puro
        return resposta

#================================================================
#          FERRAMENTA TRATAR PROCESSOS E EXECUTAVEIS DO PC
#================================================================  



def listar_processos_pesados():
    """Retorna os 5 processos que mais estão consumindo RAM/CPU no momento."""
    processos = []
    for proc in psutil.process_iter(['name', 'memory_info', 'cpu_percent']):
        try:
            # Pega processos reais, ignorando processos do sistema inacessíveis
            info = proc.info
            memoria_mb = info['memory_info'].rss / (1024 * 1024)
            processos.append({
                'nome': info['name'],
                'memoria_mb': round(memoria_mb, 1),
                'cpu': info['cpu_percent']
            })
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass

    # Ordena pelos que mais gastam memória e pega os top 5
    processos_ordenados = sorted(processos, key=lambda p: p['memoria_mb'], reverse=True)[:5]
    
    relatorio = "SISTEMA: Processos mais pesados rodando agora:\n"
    for p in processos_ordenados:
        relatorio += f"- {p['nome']}: {p['memoria_mb']} MB de RAM\n"
        
    return relatorio

def abrir_programa(nome_programa):
    """Permite a Luna abrir jogos ou aplicativos."""
    # Um dicionário mapeando os nomes para os caminhos reais no seu PC
    atalhos = {
        "overwatch": "steam://rungameid/2357570",
        "obsidian": "C:\\Users\\Fabio\\AppData\\Local\\Obsidian\\Obsidian.exe",
        "firefox": "start firefox"
    }
    
    comando = atalhos.get(nome_programa.lower())
    if comando:
        os.system(comando)
        return f"SISTEMA: O {nome_programa} foi aberto. LUNA, avise o Fábio que você abriu."
    return "SISTEMA: Programa não encontrado nos atalhos."

def matar_processo(nome_processo):
    """Permite a Luna forçar o fechamento de um programa que travou."""
    os.system(f"taskkill /f /im {nome_processo}.exe")
    return f"SISTEMA: O processo {nome_processo} foi finalizado."

def obter_janela_em_foco():
    """Descobre qual programa ou janela está em primeiro plano no Windows do Fábio."""
    try:
        # Pega o ID da janela que está ativa agora no Windows
        hwnd = ctypes.windll.user32.GetForegroundWindow()
        
        # Descobre o tamanho do texto do título da janela e extrai
        tamanho = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
        buffer = ctypes.create_unicode_buffer(tamanho + 1)
        ctypes.windll.user32.GetWindowTextW(hwnd, buffer, tamanho + 1)
        
        nome_janela = buffer.value
        if nome_janela:
            return f"SISTEMA: O Fábio está com a janela '{nome_janela}' em foco no momento."
        return "SISTEMA: O Fábio está na área de trabalho ou nenhuma janela está em foco."
    except Exception as e:
        return f"SISTEMA: Erro ao tentar ler a janela em foco: {e}"
    

#================================================================
#          FERRAMENTA DESENHAR COM APPS DE TERCEIROS
#================================================================  

# Hugging Face — geração de imagem grátis. Token em https://huggingface.co/settings/tokens
HF_TOKEN = os.getenv("HF_TOKEN", "")
MODELO_IMAGEM = "black-forest-labs/FLUX.1-schnell"

# Guarda os bytes da última imagem gerada, para canais que enviam mídia (Telegram).
_ultima_imagem_bytes = None

def gerar_imagem_bytes(prompt_imagem, tentativas=2):
    """Gera a imagem via Hugging Face (FLUX.1-schnell) e retorna os bytes PNG. None se falhar."""
    if not HF_TOKEN:
        cor.amarelo("[Imagem: HF_TOKEN nao configurado no .env]")
        return None
    from huggingface_hub import InferenceClient
    client = InferenceClient(token=HF_TOKEN)
    for i in range(tentativas):
        try:
            imagem = client.text_to_image(prompt_imagem, model=MODELO_IMAGEM)
            buf = io.BytesIO()
            imagem.save(buf, format="PNG")
            return buf.getvalue()
        except Exception as e:
            cor.amarelo(f"[Imagem HF falhou (tentativa {i+1}/{tentativas}): {e}]")
            time.sleep(3)
    return None

def obter_ultima_imagem_bytes():
    """Retorna (e limpa) os bytes da última imagem gerada — usado pelo Telegram."""
    global _ultima_imagem_bytes
    b = _ultima_imagem_bytes
    _ultima_imagem_bytes = None
    return b

def desenhar_imagem(prompt_imagem):
    """
    Gera uma imagem baseada na descrição da Luna, salva localmente e abre no navegador.
    Os bytes ficam disponíveis em obter_ultima_imagem_bytes() para envio pelo Telegram.
    """
    global _ultima_imagem_bytes
    _ultima_imagem_bytes = None

    dados = gerar_imagem_bytes(prompt_imagem)
    if not dados:
        return "Erro: o serviço de geração de imagens está sobrecarregado agora. Tente de novo em alguns instantes."

    _ultima_imagem_bytes = dados

    # Salva em arquivo temporário e abre no navegador padrão (interface por voz/web)
    try:
        import tempfile
        caminho = os.path.join(tempfile.gettempdir(), "luna_desenho.png")
        with open(caminho, "wb") as f:
            f.write(dados)
        webbrowser.open(caminho)
    except Exception:
        pass

    return "Imagem gerada."


#================================================================
#          FERRAMENTA LEMBRETE COM TIMER
#================================================================

#================================================================
#          FERRAMENTA MUTE DO SISTEMA
#================================================================

def alternar_mute():
    """Muta ou desmuta o volume do sistema Windows via pycaw."""
    try:
        from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
        from ctypes import cast, POINTER
        from comtypes import CLSCTX_ALL, CoInitialize, CoUninitialize
    except ImportError:
        return "Erro: pycaw não instalado. Execute: pip install pycaw"

    # Inicializa o COM NESTA thread. Sem isso, os objetos COM podem ser liberados
    # depois, por GC em outra thread/após o COM já fechar -> access violation no __del__.
    CoInitialize()
    try:
        device = AudioUtilities.GetSpeakers()
        # GetSpeakers() retorna AudioDevice wrapper — o COM object real fica em ._dev
        interface = device._dev.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        volume = cast(interface, POINTER(IAudioEndpointVolume))

        mute_atual = volume.GetMute()
        volume.SetMute(not mute_atual, None)
        resultado = "Volume mutado." if not mute_atual else "Volume desmutado."

        # Libera os ponteiros COM agora, enquanto o COM ainda está vivo nesta thread
        # (em vez de deixar pro GC liberar depois e estourar access violation).
        del volume, interface, device
        return resultado
    except Exception as e:
        return f"Erro ao controlar volume: {e}"
    finally:
        CoUninitialize()


#================================================================
#          FERRAMENTA OVERWATCH (STATS EM TEMPO REAL)
#================================================================

def consultar_overwatch() -> str:
    """Busca perfil e estatísticas do Fábio no Overwatch via OverFast API."""
    battletag = os.getenv("OW_BATTLETAG", "Fabio-1600")
    url_perfil = f"https://overfast-api.tekrop.fr/players/{battletag}/summary"
    url_stats  = f"https://overfast-api.tekrop.fr/players/{battletag}/stats/summary"

    try:
        resp = requests.get(url_perfil, timeout=10)
        if resp.status_code != 200:
            return "Perfil do Overwatch inacessível no momento."

        perfil = resp.json()
        if perfil.get("privacy") == "private":
            return "Perfil do Overwatch está privado. Stats não disponíveis."

        endorsement = perfil.get("endorsement", {}).get("level", "?")
        titulo      = perfil.get("title") or "nenhum"

        comp = perfil.get("competitive", {}).get("pc", {})
        ranks = []
        for role in ["tank", "damage", "support"]:
            if role in comp and comp[role]:
                tier  = comp[role].get("division", "Unranked").capitalize()
                level = comp[role].get("tier", "")
                ranks.append(f"{role}: {tier} {level}".strip())
        rank_texto = ", ".join(ranks) if ranks else "sem rank competitivo"

        texto = f"Overwatch — Endorsement {endorsement}, título: {titulo}, ranks: {rank_texto}."

        resp2 = requests.get(url_stats, timeout=10)
        if resp2.status_code == 200:
            dados2  = resp2.json()
            geral   = dados2.get("general", {})
            horas   = int(geral.get("time_played", 0) / 3600)
            winrate = geral.get("winrate", 0)
            elim    = geral.get("eliminations", 0)
            mortes  = geral.get("deaths", 0)
            texto  += f" Total: {horas}h, winrate: {winrate}%, K/D: {elim}/{mortes}."

            herois = dados2.get("heroes", {})
            if herois:
                main     = max(herois, key=lambda k: herois[k].get("time_played", 0))
                h_horas  = int(herois[main].get("time_played", 0) / 3600)
                h_wr     = herois[main].get("winrate", "?")
                texto   += f" Main: {main.capitalize()} ({h_horas}h, {h_wr}% winrate)."

        return texto

    except Exception as e:
        return f"Erro ao consultar Overwatch: {e}"


#================================================================
#          FERRAMENTA CONSULTAR JOGO NA STEAM
#================================================================

def consultar_jogo_steam(nome_jogo):
    """Busca um jogo na loja da Steam pelo nome e retorna ficha:
    preço, desconto, descrição curta, gênero, lançamento e Metacritic."""
    try:
        busca = requests.get(
            "https://store.steampowered.com/api/storesearch/",
            params={"term": nome_jogo, "cc": "br", "l": "portuguese"},
            timeout=10,
        )
        itens = busca.json().get("items", []) if busca.status_code == 200 else []
        if not itens:
            return f"Não encontrei nenhum jogo chamado '{nome_jogo}' na Steam."

        appid = itens[0]["id"]
        det = requests.get(
            "https://store.steampowered.com/api/appdetails",
            params={"appids": appid, "cc": "br", "l": "portuguese"},
            timeout=10,
        )
        info = det.json().get(str(appid), {})
        if not info.get("success"):
            return f"Encontrei '{itens[0].get('name', nome_jogo)}' na Steam, mas não consegui pegar os detalhes."
        d = info.get("data", {})

        nome = d.get("name", nome_jogo)
        desc = (d.get("short_description") or "").strip()
        generos = ", ".join(g.get("description", "") for g in d.get("genres", []))
        lancamento = d.get("release_date", {}).get("date", "")
        metacritic = d.get("metacritic", {}).get("score")

        if d.get("is_free"):
            preco = "Gratuito"
        else:
            po = d.get("price_overview")
            if po and po.get("discount_percent"):
                preco = f"{po.get('final_formatted')} ({po.get('discount_percent')}% de desconto, de {po.get('initial_formatted')})"
            elif po:
                preco = po.get("final_formatted", "preço indisponível")
            else:
                preco = "preço indisponível (sem página de venda)"

        partes = [f"{nome} (Steam)."]
        if desc:       partes.append(desc)
        if generos:    partes.append(f"Gênero: {generos}.")
        if lancamento: partes.append(f"Lançamento: {lancamento}.")
        partes.append(f"Preço: {preco}.")
        if metacritic: partes.append(f"Metacritic: {metacritic}.")
        return " ".join(partes)

    except Exception as e:
        return f"Erro ao consultar a Steam: {e}"


#================================================================
#          CATÁLOGO DE FERRAMENTAS (SCHEMAS E MAPA DE FUNÇÕES)
#================================================================

def executar_analise_aba():
    contexto = obter_contexto_navegador()
    if isinstance(contexto, dict):
        relatorio = (
            f"Título: {contexto.get('titulo', 'Desconhecido')}\n"
            f"URL: {contexto.get('url', 'Desconhecida')}\n"
            f"Conteúdo: {contexto.get('texto', '')}"
        )
        return relatorio
    return contexto


ferramentas_disponiveis = [
    {
        "type": "function",
        "function": {
            "name": "resumir_youtube",
            "description": "Resume um vídeo do YouTube. Se o Fábio mandar um link (ex: pelo Telegram), passe-o em 'url'. Se ele não mandar link (ex: pedindo por voz no PC), deixe 'url' vazio para usar a aba ativa do Firefox.",
            "parameters": {
                "type": "object",
                "properties": {"url": {"type": "string", "description": "URL do vídeo do YouTube, se o usuário tiver fornecido. Caso contrário, omita."}},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "adicionar_agenda",
            "description": "Cria um NOVO evento na agenda Google. Use para compromissos COM data e hora marcadas (ex: 'dentista quinta às 15h', 'reunião dia 10'). Para recado/ideia SEM data e hora, use salvar_obsidian. NUNCA use esta ferramenta para consultar ou ler a agenda.",
            "parameters": {
                "type": "object",
                "properties": {
                    "resumo": {"type": "string"},
                    "data_hora_iso": {"type": "string", "description": "Data e hora no formato ISO 8601 (YYYY-MM-DDTHH:MM:SS). Use o ano e mês atuais informados no contexto; nunca invente o ano."}
                },
                "required": ["resumo", "data_hora_iso"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "controlar_spotify",
            "description": "Use para tocar músicas no Spotify. IMPORTANTE: Se o usuário pedir 'qualquer música' ou NÃO especificar o nome, você TEM PERMISSÃO para escolher o nome de uma música famosa aleatória por conta própria.",
            "parameters": {
                "type": "object",
                "properties": {
                    "acao": {"type": "string", "enum": ["tocar"]},
                    "nome_musica": {
                        "type": "string",
                        "description": "O nome da música. Se o usuário não disse qual, invente uma música popular e coloque aqui."
                    }
                },
                "required": ["acao", "nome_musica"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "pesquisar_web",
            "description": "Use quando o usuário pedir explicitamente uma pesquisa, ou quando a pergunta envolver eventos recentes, notícias ou fatos que você claramente não sabe. NÃO use para perguntas gerais de conhecimento. NÃO use para JOGOS (preço, do que se trata, lançamento) — para jogos use 'consultar_jogo_steam'.",
            "parameters": {
                "type": "object",
                "properties": {
                    "pergunta": {"type": "string"}
                },
                "required": ["pergunta"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "checar_emails",
            "description": "Use para ver os novos e-mails.",
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "controlar_navegador",
            "description": "Controla a aba ativa do Firefox.",
            "parameters": {
                "type": "object",
                "properties": {
                    "acao": {"type": "string", "enum": ["abrir_url", "clicar", "ler_texto", "rolar_baixo", "digitar_texto", "navegacao", "controle_midia", "listar_abas", "trocar_aba"]},
                    "parametro": {"type": "string"}
                },
                "required": ["acao"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "analisar_aba_atual",
            "description": "Lê o CONTEÚDO TEXTUAL da aba ativa do Firefox.",
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "abrir_programa",
            "description": "Abre um programa ou jogo no computador do Fábio.",
            "parameters": {
                "type": "object",
                "properties": {"nome_programa": {"type": "string"}},
                "required": ["nome_programa"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "desenhar_imagem",
            "description": "Gera uma imagem. Use quando o Fábio pedir um desenho.",
            "parameters": {
                "type": "object",
                "properties": {"prompt_imagem": {"type": "string"}},
                "required": ["prompt_imagem"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "ler_agenda_google",
            "description": "Lê os eventos e compromissos agendados nos próximos 10 dias.",
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "obter_clima",
            "description": "Obtém a previsão do tempo e a temperatura atual.",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "alternar_mute",
            "description": "Muta ou desmuta o volume do sistema Windows.",
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "consultar_overwatch",
            "description": "Consulta o perfil, rank, winrate, KDA e herói main do Fábio no Overwatch. Use quando ele perguntar sobre as próprias stats, rank, ou desempenho no Overwatch.",
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "resumir_site",
            "description": "Lê/resume um site ou artigo. Se o Fábio mandar um link (ex: pelo Telegram), passe-o em 'url'. Se ele não mandar link (ex: por voz no PC), deixe 'url' vazio para usar a aba do Firefox ou o clipboard.",
            "parameters": {
                "type": "object",
                "properties": {"url": {"type": "string", "description": "URL do site/artigo, se o usuário tiver fornecido. Caso contrário, omita."}},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "listar_capacidades",
            "description": "Use SOMENTE quando o usuário perguntar o que a Luna consegue fazer, quais são suas capacidades, habilidades ou funções disponíveis.",
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "ver_tela",
            "description": "Tira um print da tela atual do PC do Fábio e descreve o que está nela. Use quando ele pedir para ver/olhar a tela, tirar um print, ou ajuda com algo que está na tela.",
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "consultar_jogo_steam",
            "description": "Informações de um JOGO: preço, valor, quanto custa, promoção/desconto, do que se trata, gênero, data de lançamento. Use SEMPRE que a pergunta for sobre um jogo (mesmo que ele não cite 'Steam'). PREFIRA esta ferramenta a 'pesquisar_web' para qualquer pergunta sobre jogos.",
            "parameters": {
                "type": "object",
                "properties": {"nome_jogo": {"type": "string", "description": "Nome do jogo. Se o usuário usar pronome (ex: 'dele', 'desse'), use o nome do jogo citado antes na conversa."}},
                "required": ["nome_jogo"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "ler_obsidian",
            "description": "Lê uma nota das ANOTAÇÕES PESSOAIS do Fábio (Obsidian) — receitas, listas, coisas que ele salvou. Use quando ele pedir algo das 'minhas notas/anotações', ou algo que esteja na lista de notas informada no contexto. NÃO use para a web (isso é pesquisar_web) nem para links (resumir_site).",
            "parameters": {
                "type": "object",
                "properties": {"assunto": {"type": "string", "description": "Do que é a nota que ele quer (ex: 'receita do biscoito', 'contas do mês')."}},
                "required": ["assunto"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "salvar_obsidian",
            "description": "Anota/salva um recado, ideia ou lembrete SEM data e hora marcadas nas notas do Fábio (Obsidian). Use quando ele disser 'anota', 'salva isso', 'registra', 'guarda', 'lembra que', 'toma nota' seguido do que guardar (ex: 'anota que preciso renovar o seguro'). Se for compromisso COM dia e hora, use adicionar_agenda. NÃO use para LER nota (isso é ler_obsidian).",
            "parameters": {
                "type": "object",
                "properties": {
                    "conteudo": {"type": "string", "description": "O que deve ser anotado, exatamente como o Fábio quer guardar (ex: 'renovar o seguro do carro esse mês')."},
                    "titulo": {"type": "string", "description": "Título curto opcional (ex: 'Seguro do carro'). Se não souber, deixe vazio."}
                },
                "required": ["conteudo"]
            }
        }
    },
]