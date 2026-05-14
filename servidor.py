# servidor.py atualizado

from flask import Flask, render_template
from flask_sock import Sock
import threading
import json

app  = Flask(__name__)
sock = Sock(app)

_clientes      = set()
_clientes_lock = threading.Lock()
_callback_interrupcao = None
_ultima_fala_usuario = "Aguardando áudio..."
_ultima_fala_luna    = "Zzz... dormindo."

def registrar_callback_interrupcao(fn):
    global _callback_interrupcao
    _callback_interrupcao = fn

@app.route('/')
def index():
    return render_template('index.html')

@sock.route('/ws')
def websocket(ws):
    with _clientes_lock:
        _clientes.add(ws)
        
    # --- NOVIDADE: Assim que o site conecta, enviamos o que já temos guardado
    try:
        boas_vindas = json.dumps({
            'usuario': _ultima_fala_usuario,
            'legenda': _ultima_fala_luna
        }, ensure_ascii=False)
        ws.send(boas_vindas)
    except:
        pass

    try:
        while True:
            msg = ws.receive(timeout=60)
            if msg:
                dados = json.loads(msg)
                if dados.get('comando') == 'interromper' and _callback_interrupcao:
                    _callback_interrupcao()
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

# --- FUNÇÕES PARA VOCÊ USAR NO MAIN.PY ---

def atualizar_legenda(texto: str):
    global _ultima_fala_luna
    _ultima_fala_luna = texto # Salva na memória
    _broadcast({'legenda': texto})

def atualizar_usuario(texto: str):
    global _ultima_fala_usuario
    _ultima_fala_usuario = texto # Salva na memória
    _broadcast({'usuario': texto})

def atualizar_estado_rosto(estado: str):
    """Ainda mantida caso você queira usar lógica de cores no futuro."""
    _broadcast({'estado': estado})

#------------------------------

def iniciar_servidor():
    """Inicia o servidor Flask em uma thread separada para não bloquear o main.py"""
    threading.Thread(
        target=lambda: app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False),
        daemon=True
    ).start()
    print("[🌐 Servidor da Luna: Rodando em http://localhost:5000]")