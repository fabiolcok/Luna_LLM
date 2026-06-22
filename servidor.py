# servidor.py

"""
SERVIDOR WEB DA LUNA (INTERFACE OPCIONAL)
---------------------------------------------------------
Interface web em Flask + WebSocket para visualizar a conversa em tempo real no navegador.
Ativo por padrão: o main.py chama iniciar_servidor() e o pywebview abre essa página.

Tecnologia: Flask (HTTP) + flask-sock (WebSocket nativo)
Porta: 5000 — acesse http://localhost:5000 quando ativo.

Funções para usar no main.py:
  iniciar_servidor()           — inicia Flask em thread daemon (não bloqueia o loop)
  atualizar_legenda(texto)     — envia fala da Luna para todos os clientes conectados
  atualizar_usuario(texto)     — envia fala do usuário para todos os clientes conectados
  atualizar_estado_rosto(est.) — broadcast de estado visual (cor/expressão do rosto)
  registrar_callback_interrupcao(fn) — registra função a chamar quando o botão de
                                       interrupção for acionado pela interface web

WebSocket (/ws): recebe {'comando': 'interromper'} do frontend para acionar sd.stop().
"""

from flask import Flask, render_template
from flask_sock import Sock
import threading
import json
import os
import re
import httpx

# Tags de expressão do Supertonic (<sigh>, <laugh>...) são só para a VOZ.
# No texto (web/histórico) aparecem literais ou somem no innerHTML — então removemos.
_TAGS_VOZ = re.compile(r'</?(?:laugh|breath|sigh|surprise|scream|throatclear|sad|angry|cough|yawn)>', re.IGNORECASE)

def _remover_tags_voz(texto: str) -> str:
    if not texto:
        return texto
    return _TAGS_VOZ.sub('', texto).strip()

app  = Flask(__name__)
app.config['TEMPLATES_AUTO_RELOAD'] = True
sock = Sock(app)

_clientes      = set()
_clientes_lock = threading.Lock()
_callback_interrupcao = None
_ultima_fala_usuario = "Aguardando áudio..."
_ultima_fala_luna    = "Zzz... dormindo."
_ultimo_pensamento   = ""
_historico_web       = []   # lista de {usuario, luna, tempo}

_arquivo_pendente = None  # {"nome": str, "conteudo": str}

_config_handlers = {}
_estado_config = {
    "proativo": True,
    "memoria": False,
    "tarefas": {"jogos": True, "emails": True, "agenda": True,
                "pausa": True, "clima": True, "bom_dia": True, "steam": True},
    "voz": "F1",
    "velocidade": 1.2,
}

def registrar_callback_interrupcao(fn):
    global _callback_interrupcao
    _callback_interrupcao = fn

def sincronizar_config(chave: str, valor):
    """Atualiza o estado de config e faz broadcast sem chamar os handlers Python."""
    _estado_config[chave] = valor
    _broadcast({"tipo": "config_estado", "estado": _estado_config.copy()})

def registrar_config_handler(chave: str, fn):
    _config_handlers[chave] = fn

def _aplicar_config(dados: dict):
    chave = dados.get('config')
    if not chave:
        return
    if chave == 'tarefa':
        nome = dados.get('nome')
        valor = dados.get('valor')
        fn = _config_handlers.get('tarefa')
        if fn:
            try: fn(nome, valor)
            except Exception: pass
        _estado_config.setdefault('tarefas', {})[nome] = valor
    else:
        valor = dados.get('valor')
        fn = _config_handlers.get(chave)
        if fn:
            try: fn(valor)
            except Exception: pass
        _estado_config[chave] = valor
    _broadcast({"tipo": "config_estado", "estado": _estado_config.copy()})

@app.route('/')
def index():
    return render_template('index.html')

@sock.route('/ws')
def websocket(ws):
    with _clientes_lock:
        _clientes.add(ws)
        
    # Assim que o site conecta, enviamos o estado atual
    try:
        boas_vindas = json.dumps({
            'usuario': _ultima_fala_usuario,
            'legenda': _ultima_fala_luna,
            'pensamento': _ultimo_pensamento,
        }, ensure_ascii=False)
        ws.send(boas_vindas)
        ws.send(json.dumps({"tipo": "config_estado", "estado": _estado_config.copy()}))
        ws.send(json.dumps({"tipo": "historico_completo", "turnos": list(_historico_web)}))
    except:
        pass

    try:
        while True:
            msg = ws.receive(timeout=60)
            if msg:
                dados = json.loads(msg)
                if dados.get('comando') == 'interromper' and _callback_interrupcao:
                    _callback_interrupcao()
                elif dados.get('comando') == 'fechar':
                    os._exit(0)
                elif dados.get('tipo') == 'arquivo':
                    global _arquivo_pendente
                    _arquivo_pendente = _processar_arquivo(dados)
                    _broadcast({"tipo": "arquivo_confirmado", "nome": _arquivo_pendente["nome"]})
                elif dados.get('tipo') == 'limpar_arquivo':
                    _arquivo_pendente = None
                elif dados.get('comando') == 'limpar_historico':
                    _historico_web.clear()
                    _broadcast({"tipo": "historico_completo", "turnos": []})
                elif dados.get('config'):
                    _aplicar_config(dados)
    except Exception:
        pass
    finally:
        with _clientes_lock:
            _clientes.discard(ws)

def _broadcast(dados: dict):
    payload = json.dumps(dados, ensure_ascii=False)
    mortos  = []
    with _clientes_lock:
        for ws in _clientes:
            try:
                ws.send(payload)
            except Exception:
                mortos.append(ws)
        for ws in mortos:
            _clientes.discard(ws)

def _processar_arquivo(dados: dict) -> dict:
    nome = dados.get('nome', 'arquivo')
    fmt  = dados.get('formato', 'txt')
    raw  = dados.get('conteudo', '')
    if fmt == 'pdf':
        try:
            import base64, io, pdfplumber
            with pdfplumber.open(io.BytesIO(base64.b64decode(raw))) as pdf:
                texto = '\n'.join(p.extract_text() or '' for p in pdf.pages).strip()
            if not texto:
                texto = '[PDF sem texto extraível]'
        except ImportError:
            texto = '[PDF: instale pdfplumber — pip install pdfplumber]'
        except Exception as e:
            texto = f'[Erro ao ler PDF: {e}]'
    else:
        texto = raw
    return {"nome": nome, "conteudo": texto[:10000]}

def obter_e_limpar_arquivo():
    global _arquivo_pendente
    arq = _arquivo_pendente
    _arquivo_pendente = None
    return arq

# --- FUNÇÕES PARA VOCÊ USAR NO MAIN.PY ---

def _registrar_turno(usuario: str, luna: str):
    import datetime
    if _historico_web and _historico_web[-1].get("luna") == luna:
        return  # evita duplicação quando atualizar_legenda é chamada duas vezes
    turno = {
        "usuario": usuario,
        "luna": luna,
        "tempo": datetime.datetime.now().strftime("%H:%M"),
    }
    _historico_web.append(turno)
    if len(_historico_web) > 40:
        _historico_web.pop(0)
    _broadcast({"tipo": "historico_novo", "turno": turno})

def atualizar_legenda(texto: str):
    global _ultima_fala_luna
    texto = _remover_tags_voz(texto)   # voz fica com os tags; texto exibido não
    _ultima_fala_luna = texto
    _broadcast({'legenda': texto})
    if texto:
        _registrar_turno(_ultima_fala_usuario, texto)

def atualizar_usuario(texto: str):
    global _ultima_fala_usuario
    _ultima_fala_usuario = texto
    _broadcast({'usuario': texto})

def atualizar_estado_rosto(estado: str):
    """Ainda mantida caso você queira usar lógica de cores no futuro."""
    _broadcast({'estado': estado})

def _buscar_gif(termo: str) -> str:
    api_key = os.getenv("GIPHY_API_KEY", "")
    if not api_key:
        return ""
    try:
        r = httpx.get(
            "https://api.giphy.com/v1/gifs/search",
            params={"api_key": api_key, "q": termo, "limit": 5, "rating": "g", "lang": "en"},
            timeout=5,
        )
        gifs = r.json().get("data", [])
        if gifs:
            import random
            escolhido = random.choice(gifs[:5])
            return escolhido["images"]["original"]["url"]
    except Exception:
        pass
    return ""

def atualizar_status_mic(status: str):
    """status: 'aguardando' | 'gravando' | 'processando'"""
    _broadcast({"tipo": "status_mic", "status": status})

def atualizar_metricas(roteador=None, persona=None):
    dados = {"tipo": "metricas"}
    if roteador is not None:
        dados["roteador"] = roteador
    if persona is not None:
        dados["persona"] = persona
    _broadcast(dados)

def atualizar_pensamento(texto: str):
    global _ultimo_pensamento
    _ultimo_pensamento = texto
    _broadcast({"pensamento": texto})

def atualizar_gif(termo: str):
    """Busca um GIF no Giphy para o termo e faz broadcast — chamada não bloqueia."""
    def _worker():
        url = _buscar_gif(termo)
        if url:
            _broadcast({"gif_url": url, "gif_termo": termo})
    threading.Thread(target=_worker, daemon=True).start()

#------------------------------

def iniciar_servidor():
    """Inicia o servidor Flask em uma thread separada para não bloquear o main.py"""
    threading.Thread(
        target=lambda: app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False),
        daemon=True
    ).start()
    print("[🌐 Servidor da Luna: Rodando em http://localhost:5000]")