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

from flask import Flask, render_template, request, abort, send_from_directory
from flask_sock import Sock
from simple_websocket import ConnectionClosed
from modulos.execucoes import controle, vincular
from modulos.vozes_kokoro import VOZES_VALIDAS, VOZ_PADRAO, normalizar_favoritas, vozes_para_web
from contextvars import ContextVar
import threading
import json
import logging
import os
import random
import queue
import re
import socket
import time
import uuid
import httpx
import modelos.cores as cor

# Tags de expressão do Supertonic (<sigh>, <laugh>...) são só para a VOZ.
# No texto (web/histórico) aparecem literais ou somem no innerHTML — então removemos.
_TAGS_VOZ = re.compile(r'</?(?:laugh|breath|sigh|surprise|scream|throatclear|sad|angry|cough|yawn)>', re.IGNORECASE)

def _remover_tags_voz(texto: str) -> str:
    if not texto:
        return texto
    return _TAGS_VOZ.sub('', texto).strip()

app  = Flask(__name__)
app.config['TEMPLATES_AUTO_RELOAD'] = True
# Detecta conexões abandonadas após suspensão/perda de rede, em vez de mantê-las no broadcast.
app.config['SOCK_SERVER_OPTIONS'] = {"ping_interval": 20}
sock = Sock(app)
_log = logging.getLogger("luna.servidor")


@app.after_request
def _nao_cachear_interface(resposta):
    """Preferências persistem no WebView2, mas o HTML precisa refletir cada atualização."""
    if request.path == "/":
        resposta.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        resposta.headers["Pragma"] = "no-cache"
        resposta.headers["Expires"] = "0"
    return resposta

_clientes      = set()
_clientes_lock = threading.Lock()
_callback_interrupcao = None
_handler_acompanhamento_web = None
_handler_conclusao_web = None
_ultima_fala_usuario = "Aguardando áudio..."
_ultima_fala_luna    = "Zzz... dormindo."
_ultimo_pensamento   = ""
_ultimo_status       = "🌚 Por aqui"   # o que a Luna está fazendo agora (linha de status do web)
_ultimo_estado_rosto = None       # diagnóstico das transições reais enviadas ao mascote
_ultimo_kaomoji      = None       # nova janela do widget já nasce com a expressão atual
_clima_turno_pendente = ""        # consumido pelo próximo balão; não confunde com o rosto atual
_historico_web       = []   # lista de {usuario, luna, tempo}
_textos_web = {}
_textos_web_lock = threading.RLock()
_texto_web_id = ContextVar("texto_web_id", default=None)
_audios_web = {}
_audios_web_lock = threading.RLock()
_mascote_solto       = False
_relogio_visual_iniciado = False
_relogio_visual_lock = threading.Lock()

# Os intervalos continuam os mesmos que existiam no JavaScript, agora em segundos. Um relógio
# no servidor sobrevive à troca entre WebView2 e Qt; antes cada página recomeçava do zero.
_INTERVALOS_EVENTOS_VISUAIS = {
    "cometa": (720, 1800),
    "ovni": (840, 2040),
    "foguete": (900, 2400),
    "satelites": (1080, 2700),
    "sujeira": (1200, 3000),
    "chuva": (1320, 3000),
    "cometao": (1500, 3300),
    "invasao": (1560, 3480),
    "eclipse": (2700, 5400),
}

_ACOES_LAB_VISUAL = {
    "foguete", "satelite", "cometao", "sujeira", "chuva", "invasao", "desistir",
    "cometa", "ovni", "eclipse", "confete", "spotify", "radar", "video", "tela",
    "jogo", "sonar", "ouvindo", "pensando", "falando", "digitando", "afk", "noite", "limpar", "rosto",
}

_arquivo_pendente = None  # {"nome": str, "conteudo": str}
_imagem_anexada_pendente = None  # {"nome": str, "dados": bytes, "ext": str} — imagem anexada no web p/ arquivar

_config_handlers = {}
_estado_config = {
    "proativo": True,
    # Ligado/desligado continua em "proativo" (o atalho do modo suspenso alterna só ele).
    "proativo_intensidade": "normal",
    "memoria": False,
    "tarefas": {"jogos": True, "emails": True, "agenda": True, "pausa": True,
                "clima": True, "bom_dia": True, "retomar": True, "steam": True, "navegador": True,
                "steam_jogo": True, "radar_rss": True, "animes": True,
                "autoconhecimento": True, "memoria": True, "habitos": True, "lol_mortes": True,
                "radar_promocoes": True, "acompanhamentos": True},
    "voz": VOZ_PADRAO,
    "vozes_favoritas": [],
    "velocidade": 0.9,
    "volume": 1.0,
    "modelo_local": "",
    "modelo_thinking": "desligado",
    "personalidade": 2,  # preserva o TARS ativo em instalações anteriores ao seletor
    "teclas": {"ptt": "ctrl+alt+f8", "interromper": "ctrl+f9", "suspenso": "ctrl+f7"},
}

_CAMINHO_CONFIG = "modelos/config_luna.json"
_trava_personalidade = threading.Lock()
_personalidade_pendente = False
_personalidade_erro = ""

def _salvar_config():
    """Persiste o estado de config no disco para sobreviver a reinicializações."""
    try:
        os.makedirs("modelos", exist_ok=True)
        with open(_CAMINHO_CONFIG, "w", encoding="utf-8") as f:
            json.dump(_estado_config, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

def carregar_e_aplicar_config():
    """Lê a config salva e aplica via os handlers já registrados.
    Deve ser chamada no main.py DEPOIS de registrar todos os handlers."""
    if os.path.exists(_CAMINHO_CONFIG):
        try:
            with open(_CAMINHO_CONFIG, "r", encoding="utf-8") as f:
                salvo = json.load(f)
            for k, v in salvo.items():
                if k in ("tarefas", "teclas") and isinstance(v, dict):
                    _estado_config.setdefault(k, {}).update(v)
                else:
                    _estado_config[k] = v
        except Exception:
            pass

    if not isinstance(_estado_config.get("voz"), str) or _estado_config["voz"] not in VOZES_VALIDAS:
        _estado_config["voz"] = VOZ_PADRAO
    _estado_config["vozes_favoritas"] = normalizar_favoritas(_estado_config.get("vozes_favoritas"))
    from modulos.proativa import INTENSIDADES, INTENSIDADE_PADRAO
    if _estado_config.get("proativo_intensidade") not in INTENSIDADES:
        _estado_config["proativo_intensidade"] = INTENSIDADE_PADRAO
    from modulos import prompts
    try:
        _estado_config["personalidade"] = prompts.validar_personalidade(_estado_config["personalidade"])
    except (KeyError, ValueError):
        _estado_config["personalidade"] = prompts.PERSONALIDADE_PADRAO
    # Aplica os valores carregados nos módulos reais
    for chave in ("proativo", "proativo_intensidade", "memoria", "voz", "velocidade", "volume", "personalidade"):
        fn = _config_handlers.get(chave)
        if fn and chave in _estado_config:
            try: fn(_estado_config[chave])
            except Exception: pass
    fn_tarefa = _config_handlers.get("tarefa")
    if fn_tarefa:
        for nome, val in _estado_config.get("tarefas", {}).items():
            try: fn_tarefa(nome, val)
            except Exception: pass
    fn_tecla = _config_handlers.get("tecla")
    if fn_tecla:
        for nome, combo in _estado_config.get("teclas", {}).items():
            try: fn_tecla(nome, combo)
            except Exception: pass

def registrar_callback_interrupcao(fn):
    global _callback_interrupcao
    _callback_interrupcao = fn

_handler_texto_web = None
_handler_ouvir_web = None


def registrar_handler_ouvir_web(fn):
    global _handler_ouvir_web
    _handler_ouvir_web = fn


def registrar_handler_texto_web(fn):
    """main.py registra aqui a função que processa uma mensagem DIGITADA na caixa do web."""
    global _handler_texto_web
    _handler_texto_web = fn

def registrar_handler_acompanhamento_web(fn):
    """Entrega decisões dos botões ao fluxo de conversa sem acoplar servidor.py ao main.py."""
    global _handler_acompanhamento_web
    _handler_acompanhamento_web = fn

def registrar_handler_conclusao_web(fn):
    """Entrega confirmação de checkbox ao fluxo visual sem deixar o servidor editar notas."""
    global _handler_conclusao_web
    _handler_conclusao_web = fn

def sincronizar_config(chave: str, valor):
    """Atualiza o estado de config e faz broadcast sem chamar os handlers Python."""
    _estado_config[chave] = valor
    _salvar_config()
    _broadcast({"tipo": "config_estado", "estado": _config_para_web()})

def registrar_config_handler(chave: str, fn):
    _config_handlers[chave] = fn

def _config_para_web(erro_dark_souls=""):
    from modulos import dark_souls
    # Não persiste uma segunda cópia: o comando de terminal continua usando o mesmo arquivo.
    return {**_estado_config, "dark_souls": dark_souls.habilitado(),
            "dark_souls_erro": erro_dark_souls,
            "personalidade_disponivel": callable(_config_handlers.get("personalidade")),
            "personalidade_pendente": _personalidade_pendente,
            "personalidade_erro": _personalidade_erro,
            "vozes": vozes_para_web()}


def _trocar_personalidade_web(valor):
    """Reserva na fila antes de abrir a thread; uma mensagem seguinte usa o perfil novo."""
    global _personalidade_pendente, _personalidade_erro
    from modulos import prompts
    try:
        nivel = prompts.validar_personalidade(valor)
    except ValueError as erro:
        _personalidade_erro = str(erro)
        _broadcast({"tipo": "config_estado", "estado": _config_para_web()})
        return
    fn = _config_handlers.get("personalidade")
    if not callable(fn):
        _personalidade_erro = "Reinicie a Luna para disponibilizar este controle."
        _broadcast({"tipo": "config_estado", "estado": _config_para_web()})
        return
    if not _trava_personalidade.acquire(blocking=False):
        _broadcast({"tipo": "config_estado", "estado": _config_para_web()})
        return
    if nivel == _estado_config.get("personalidade"):
        _trava_personalidade.release()
        _personalidade_erro = ""
        _broadcast({"tipo": "config_estado", "estado": _config_para_web()})
        return
    try:
        trabalho = fn.preparar(nivel) if callable(getattr(fn, "preparar", None)) else lambda: fn(nivel)
    except Exception:
        _trava_personalidade.release()
        _personalidade_erro = "Não consegui preparar a troca. O perfil anterior foi mantido."
        _broadcast({"tipo": "config_estado", "estado": _config_para_web()})
        return
    _personalidade_pendente = True
    _personalidade_erro = ""
    _broadcast({"tipo": "config_estado", "estado": _config_para_web()})

    def aplicar():
        global _personalidade_pendente, _personalidade_erro
        try:
            trabalho()
            _estado_config["personalidade"] = nivel
            _personalidade_erro = ""
            _salvar_config()
        except Exception:
            _log.exception("Falha ao trocar a personalidade")
            _personalidade_erro = "Não consegui trocar. O perfil anterior foi mantido."
        finally:
            _personalidade_pendente = False
            _trava_personalidade.release()
            _broadcast({"tipo": "config_estado", "estado": _config_para_web()})

    threading.Thread(target=aplicar, daemon=True).start()

def _aplicar_config(dados: dict):
    chave = dados.get('config')
    if not chave:
        return
    if chave == 'personalidade':
        _trocar_personalidade_web(dados.get('valor'))
        return
    if chave == 'dark_souls':
        from modulos import dark_souls
        erro = ""
        try:
            dark_souls.configurar(dados.get('valor'))
        except (OSError, ValueError):
            erro = "Não consegui salvar. A configuração anterior foi mantida."
        _broadcast({"tipo": "config_estado", "estado": _config_para_web(erro)})
        return
    if chave == 'tarefa':
        nome = dados.get('nome')
        valor = dados.get('valor')
        fn = _config_handlers.get('tarefa')
        if fn:
            try: fn(nome, valor)
            except Exception: pass
        _estado_config.setdefault('tarefas', {})[nome] = valor
    elif chave == 'voz_favorita':
        voz, favorita = dados.get('voz'), dados.get('valor')
        if not isinstance(voz, str) or voz not in VOZES_VALIDAS or not isinstance(favorita, bool):
            _broadcast({"tipo": "config_estado", "estado": _config_para_web()})
            return
        favoritas = normalizar_favoritas(_estado_config.get('vozes_favoritas'))
        if favorita and voz not in favoritas:
            favoritas.append(voz)
        elif not favorita and voz in favoritas:
            favoritas.remove(voz)
        # Alterar uma estrela não substitui a lista enviada por outra janela nem troca o timbre ativo.
        _estado_config['vozes_favoritas'] = favoritas
    elif chave == 'tecla':
        nome = dados.get('nome')
        valor = str(dados.get('valor', '')).lower().strip()
        fn = _config_handlers.get('tecla')
        aceitou = False
        if fn and nome and valor:
            try: aceitou = bool(fn(nome, valor))
            except Exception: aceitou = False
        if aceitou:
            _estado_config.setdefault('teclas', {})[nome] = valor
        # combo inválido: não salva — o broadcast devolve o valor antigo pro painel
    else:
        valor = dados.get('valor')
        if chave == 'voz' and (not isinstance(valor, str) or valor not in VOZES_VALIDAS):
            _broadcast({"tipo": "config_estado", "estado": _config_para_web()})
            return
        if chave == 'proativo_intensidade':
            from modulos.proativa import INTENSIDADES
            if valor not in INTENSIDADES:
                _broadcast({"tipo": "config_estado", "estado": _config_para_web()})
                return
        if chave == 'volume':
            try:
                valor = float(valor)
                if not 0.0 <= valor <= 1.0:
                    return
            except (TypeError, ValueError):
                return
        fn = _config_handlers.get(chave)
        if fn:
            try: fn(valor)
            except Exception:
                if chave == 'voz':
                    _broadcast({"tipo": "config_estado", "estado": _config_para_web()})
                    return
        _estado_config[chave] = valor
    # Arrastar ajusta o áudio ao vivo; só soltar grava a preferência no disco.
    if not (chave == 'volume' and dados.get('previa') is True):
        _salvar_config()
    _broadcast({"tipo": "config_estado", "estado": _config_para_web()})


def _estado_modelos():
    from modulos import pensar
    return pensar.estado_seletor_modelos()


def _trocar_modelo_web(chave: str, thinking: str):
    """Carrega em thread: um GGUF grande não pode congelar o WebSocket do painel."""
    from modulos import pensar
    _broadcast({"tipo": "modelo_status", "carregando": True,
                "texto": "Carregando o modelo escolhido..."})
    resultado = pensar.trocar_modelo_local(chave, thinking)
    if resultado.get("ok"):
        _estado_config["modelo_local"] = str(chave or "").strip()
        _estado_config["modelo_thinking"] = resultado["thinking"]
        _salvar_config()
        _broadcast({"tipo": "modelo_status", "carregando": False, "ok": True,
                    "texto": f"Modelo ativo: {resultado['modelo']}"})
    else:
        _broadcast({"tipo": "modelo_status", "carregando": False, "ok": False,
                    "texto": resultado.get("erro", "não consegui trocar o modelo")})
    _broadcast({"tipo": "modelos", "estado": _estado_modelos()})

@app.route('/')
def index():
    return render_template('index.html')


@app.get('/api/biblioteca')
@app.get('/api/historico')
def consultar_biblioteca_web():
    from modulos import biblioteca_web, obsidian
    try:
        inicio = int(request.args.get('inicio', '0'))
        if request.path == '/api/biblioteca':
            biblioteca_web.importar_notas(obsidian._VAULT)
        else:
            biblioteca_web.importar_conversas()
        return biblioteca_web.consultar(modo='historico' if request.path == '/api/historico' else 'itens',
            tipo=request.args.get('tipo', ''), leitura=request.args.get('leitura', ''),
            busca=request.args.get('busca', ''), inicio=inicio)
    except ValueError:
        return {'erro': 'Página inválida.'}, 400
    except OSError:
        _log.exception('Não foi possível abrir a biblioteca web')
        return {'erro': 'Não consegui abrir o arquivo local. Tente novamente.'}, 503


@app.post('/api/biblioteca/<identificador>/leitura')
def marcar_biblioteca_web(identificador):
    from modulos.biblioteca_web import marcar_leitura
    dados = request.get_json(silent=True) or {}
    if not isinstance(dados, dict) or type(dados.get('lido')) is not bool:
        return {'erro': 'Leitura inválida.'}, 400
    try:
        if not marcar_leitura(identificador, dados['lido']):
            return {'erro': 'Item não encontrado.'}, 404
    except OSError:
        _log.exception('Não foi possível salvar a leitura')
        return {'erro': 'Não consegui salvar a leitura. Tente novamente.'}, 503
    return {'ok': True}


# ── Patchnotes renderizado (markdown → HTML, sem dependência externa) ──
def _md_para_html(md: str) -> str:
    import html as _html
    linhas_html, em_lista = [], False
    for linha in md.splitlines():
        l = linha.rstrip()
        if l.startswith('- '):
            if not em_lista:
                linhas_html.append('<ul>'); em_lista = True
            linhas_html.append(f'<li>{_html.escape(l[2:])}</li>')
            continue
        if em_lista and (l.startswith('  ') and l.strip()):   # continuação de bullet
            linhas_html[-1] = linhas_html[-1][:-5] + ' ' + _html.escape(l.strip()) + '</li>'
            continue
        if em_lista:
            linhas_html.append('</ul>'); em_lista = False
        if l.startswith('### '):  linhas_html.append(f'<h3>{_html.escape(l[4:])}</h3>')
        elif l.startswith('## '): linhas_html.append(f'<h2>{_html.escape(l[3:])}</h2>')
        elif l.startswith('# '):  linhas_html.append(f'<h1>{_html.escape(l[2:])}</h1>')
        elif l.strip() in ('---', '***'): linhas_html.append('<hr>')
        elif l.strip():           linhas_html.append(f'<p>{_html.escape(l)}</p>')
    if em_lista:
        linhas_html.append('</ul>')
    corpo = '\n'.join(linhas_html)
    # inline: **negrito**, *itálico* (depois do escape, seguro)
    corpo = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', corpo)
    corpo = re.sub(r'(?<!\*)\*([^*\n]+)\*(?!\*)', r'<em>\1</em>', corpo)
    return corpo

@app.route('/imagens/promocoes/<nome>')
def imagem_promocao_web(nome):
    from modulos import obsidian, cartoes_web
    if not obsidian._VAULT or not cartoes_web.imagem_promocao(nome):
        abort(404)
    pasta = os.path.realpath(os.path.join(obsidian._VAULT, *obsidian._PASTA_IMGS_PROMO))
    caminho = os.path.realpath(os.path.join(pasta, nome))
    # A rota serve só a pasta das fotos do radar, inclusive quando há links no disco.
    if os.path.normcase(os.path.dirname(caminho)) != os.path.normcase(pasta) or not os.path.isfile(caminho):
        abort(404)
    resposta = send_from_directory(pasta, nome, mimetype="image/jpeg", max_age=3600)
    resposta.headers['X-Content-Type-Options'] = 'nosniff'
    return resposta


@app.route('/patchnotes')
def patchnotes():
    try:
        with open('PATCHNOTES.md', encoding='utf-8') as f:
            corpo = _md_para_html(f.read())
    except Exception as e:
        corpo = f'<p>Não consegui ler o PATCHNOTES.md: {e}</p>'
    return f"""<!DOCTYPE html><html lang="pt-br"><head><meta charset="utf-8">
<title>Luna — Novidades</title><style>
body {{ background:#0d0d12; color:#e0e0e0; font-family:'Segoe UI',sans-serif;
       max-width:760px; margin:0 auto; padding:32px 20px; line-height:1.6; }}
h1 {{ color:#b4f9f8; }} h2 {{ color:#7aa2f7; margin-top:28px; border-bottom:1px solid #1a1a2e; padding-bottom:6px; }}
li {{ margin:8px 0; }} strong {{ color:#bb9af7; }} hr {{ border:none; border-top:1px solid #1a1a2e; margin:24px 0; }}
a {{ color:#7aa2f7; }} p {{ color:#9aa5ce; }}
</style></head><body>
<p><a href="/">← voltar pra Luna</a></p>
{corpo}
</body></html>"""


# ── Oficina: helpers dos comandos do painel (teste de fala, arquivos, chaves) ──
_ABRIR_PERMITIDOS = {   # o que o botão "abrir" pode abrir no PC (whitelist)
    "avaliacoes": "logs/avaliacoes.jsonl",
    "vistos":     "modelos/vistos.json",
    "log":        "logs/luna.log",
    "logs_pasta": "logs",
    "env":        ".env",
    "pronuncia":  "modelos/pronuncia.json",
}

def _abrir_no_pc(alvo: str) -> str:
    caminho = _ABRIR_PERMITIDOS.get(alvo)
    if not caminho or not os.path.exists(caminho):
        return f"'{alvo}' não encontrado"
    try:
        os.startfile(os.path.abspath(caminho))   # abre no app padrão do Windows
        return ""
    except Exception as e:
        return str(e)

def _status_chaves() -> list:
    """[{'chave': 'GEMINI_API_KEY', 'ok': True}, ...] — nomes vêm do .env.example
    (fica em sincronia sozinho); NUNCA envia o valor, só se está preenchida."""
    try:
        from dotenv import load_dotenv
        load_dotenv()   # garante o .env carregado independente da ordem de import
    except Exception:
        pass
    from modulos.config_env import esta_configurado
    chaves = []
    try:
        with open('.env.example', encoding='utf-8') as f:
            for linha in f:
                m = re.match(r'^([A-Z][A-Z0-9_]*)=', linha.strip())
                if m:
                    nome = m.group(1)
                    chaves.append({"chave": nome, "ok": esta_configurado(nome)})
    except Exception:
        pass
    return chaves

def _falar_teste(texto: str):
    """Fala um texto de teste no PC (thread própria — não trava o WebSocket)."""
    def _rodar():
        try:
            from modulos import falar
            falar.falar_texto(texto)
        except Exception:
            pass
    threading.Thread(target=_rodar, daemon=True).start()

# ── Memória episódica (caixa de revisão) ──
def _memoria_estado() -> dict:
    """{pendentes:[...], lixo:[...]} pra caixa de revisão do web."""
    try:
        from modulos import memoria, assuntos
        return {"pendentes": memoria.mem_listar_pendentes(), "lixo": memoria.mem_listar_lixo(),
                "assuntos": assuntos.listar()}
    except Exception:
        return {"pendentes": [], "lixo": [], "assuntos": []}

def notificar_memoria(n=None):
    """Broadcast do nº de lembranças pendentes (acende o badge no web).
    Chamado pela extração da proativa e após cada ação na caixa."""
    if n is None:
        try:
            from modulos import memoria
            n = len(memoria.mem_listar_pendentes())
        except Exception:
            n = 0
    _broadcast({"tipo": "memoria_badge", "n": n})


def _acompanhamentos_estado() -> dict:
    try:
        from modulos import acompanhamentos
        estado = acompanhamentos.estado_interface()
    except Exception:
        estado = {"confirmacao": None, "ativos": []}
    try:
        from modulos import conclusao_tarefas
        estado["conclusao_tarefa"] = conclusao_tarefas.estado_interface().get("confirmacao")
    except Exception:
        estado["conclusao_tarefa"] = None
    try:
        from modulos import acompanhamento_sopro
        estado["sopro"] = acompanhamento_sopro.estado_interface()
    except Exception:
        estado["sopro"] = None
    try:
        from modulos import acompanhamento_fontes
        estado["fontes"] = acompanhamento_fontes.estado_interface()
    except Exception:
        estado["fontes"] = {"itens": [], "erro": "Não consegui carregar as fontes cadastradas."}
    from modulos import fontes_conversa
    estado['propostas_fontes'] = fontes_conversa.estado_interface()
    from modulos import interesses_radar
    estado['interesses_radar'] = interesses_radar.estado_interface()
    return estado


def notificar_acompanhamentos():
    """Atualiza card e lista sem atrelar o estado à fala atual da Luna."""
    _broadcast({"tipo": "acompanhamentos", "estado": _acompanhamentos_estado()})

def _receber_ouvir_web(ws, dados):
    from modulos.execucoes import ExecucaoCancelada
    referencia, request_id = dados.get('turno_id'), dados.get('request_id')
    def feedback(estado, texto=''):
        payload = {'tipo': 'audio_resposta', 'turno_id': referencia, 'request_id': request_id,
                   'estado': estado, 'texto': texto}
        if estado == 'erro':
            ws.send(json.dumps(payload, ensure_ascii=False))
        else:
            _broadcast(payload)
    turno = next((t for t in tuple(_historico_web) if t.get('id') == referencia), None)
    if (not isinstance(request_id, str) or not re.fullmatch(r'[\w-]{1,80}', request_id, re.ASCII)
            or not turno or not isinstance(turno.get('luna'), str) or not turno['luna'].strip()
            or not _handler_ouvir_web):
        feedback('erro', 'Não consegui encontrar essa resposta para ouvir.'); return
    texto = turno['luna']
    with _audios_web_lock:
        if request_id in _audios_web:
            return
        if len(_audios_web) >= 8:
            feedback('erro', 'Já há pedidos de áudio aguardando. Tente novamente.'); return
        execucao = controle.reservar(leitura=True)
        _audios_web[request_id] = {'execucao': execucao, 'turno_id': referencia}
    feedback('fila')
    def ouvir():
        estado, erro = 'fim', ''
        try:
            with controle.executar(execucao):
                controle.verificar()
                feedback('gerando')
                _handler_ouvir_web(texto, lambda: feedback('falando'))
                if execucao.cancelada.is_set():
                    estado = 'interrompido'
        except ExecucaoCancelada:
            estado = 'interrompido'
        except Exception:
            _log.exception('Falha ao ouvir resposta Web')
            estado, erro = 'erro', 'Não consegui gerar o áudio dessa resposta.'
        finally:
            with _audios_web_lock:
                _audios_web.pop(request_id, None)
            with controle.condicao:
                if controle.atual is None and not controle.fila:
                    atualizar_estado_rosto('dormindo')
            feedback(estado, erro)
    try:
        threading.Thread(target=ouvir, daemon=True, name='Luna-Ouvir-Web').start()
    except Exception:
        with controle.condicao:
            controle.fila.remove(execucao)
            controle.condicao.notify_all()
        with _audios_web_lock:
            _audios_web.pop(request_id, None)
        feedback('erro', 'Não consegui iniciar a leitura da resposta.')


def _parar_leitura_web(request_id):
    with _audios_web_lock:
        pedido = _audios_web.get(request_id) if isinstance(request_id, str) else None
    if not pedido:
        return
    execucao = pedido['execucao']
    with controle.condicao:
        execucao.cancelada.set()
        if controle.atual is execucao and controle.parar_audio:
            controle.parar_audio()
    _broadcast({'tipo': 'audio_resposta', 'estado': 'interrompido',
                'turno_id': pedido['turno_id'], 'request_id': request_id})


def _fila_texto_web():
    with _textos_web_lock:
        return [{k: v for k, v in item.items() if k != "recebido_em"}
                for item in _textos_web.values()]


def _notificar_fila_texto():
    with _textos_web_lock:
        _broadcast({"tipo": "fila_texto", "mensagens": _fila_texto_web()})


def _receber_texto_web(ws, dados):
    texto = (dados.get('texto') or '').strip()
    noticia = None
    resposta = None
    if 'resposta_a' in dados:
        from modulos.biblioteca_web import resolver_resposta
        resolvida = resolver_resposta(dados['resposta_a'], _historico_web)
        if not resolvida or 'novidade' in dados:
            ws.send(json.dumps({'tipo': 'mensagem_texto_recebida', 'request_id': dados.get('request_id'),
                                'ok': False, 'erro': 'Essa referência não está mais disponível. Escolha outra mensagem.'},
                               ensure_ascii=False))
            return
        resposta, noticia = resolvida
    if 'novidade' in dados:
        from modulos.novidades_web import resolver_continuacao
        continuacao = resolver_continuacao(_historico_web, dados['novidade'])
        if not continuacao:
            ws.send(json.dumps({"tipo": "mensagem_texto_recebida", "request_id": dados.get('request_id'),
                                "ok": False, "erro": "Esta notícia saiu do histórico. Escolha uma mais recente."},
                               ensure_ascii=False))
            return
        texto, noticia = continuacao
    ok = bool(texto and _handler_texto_web)
    if ok:
        identificador = uuid.uuid4().hex
        recebido_em = time.monotonic()
        _log.info("[Web] Texto recebido id=%s (%d caracteres)", identificador, len(texto))
        preparar = getattr(_handler_texto_web, "preparar", None)
        trabalho = preparar(texto) if preparar else lambda: _handler_texto_web(texto)
        with _textos_web_lock:
            _textos_web[identificador] = {
                "id": identificador, "usuario": texto, "estado": "fila",
                "tempo": time.strftime("%H:%M"), "recebido_em": recebido_em,
            }
        # A entrada aceita aparece antes da geração, sem trocar o usuário do turno atual.
        _notificar_fila_texto()

        def atender():
            from modulos.novidades_web import contexto_novidade
            from modulos.biblioteca_web import contexto_resposta
            token = _texto_web_id.set(identificador)
            token_noticia = contexto_novidade.set(noticia)
            token_resposta = contexto_resposta.set(resposta)
            try:
                trabalho()
            finally:
                contexto_resposta.reset(token_resposta)
                contexto_novidade.reset(token_noticia)
                _texto_web_id.reset(token)
                with _textos_web_lock:
                    _textos_web.pop(identificador, None)
                _notificar_fila_texto()

        threading.Thread(target=atender, daemon=True).start()
    # Confirma a entrada na fila; a resposta do modelo pode demorar sem segurar o rascunho.
    ws.send(json.dumps({"tipo": "mensagem_texto_recebida", "request_id": dados.get('request_id'),
                        "ok": ok, "erro": "" if ok else "A Luna ainda não está pronta para receber texto. Tente novamente."},
                       ensure_ascii=False))


class _ClienteWeb:
    """Uma conexão lenta não pode segurar a trava que libera a conversa."""

    def __init__(self, ws):
        self.ws = ws
        self.fila = queue.Queue(maxsize=128)
        self.encerrado = threading.Event()
        threading.Thread(target=self._enviar, daemon=True).start()

    def send(self, payload):
        if self.encerrado.is_set():
            raise ConnectionClosed()
        try:
            self.fila.put_nowait(payload)
        except queue.Full:
            _log.warning("[Web] Conexão lenta: fila de saída cheia; reconectando")
            self.encerrar()
            raise ConnectionClosed()

    def receive(self, timeout=None):
        return self.ws.receive(timeout=timeout)

    def encerrar(self):
        if self.encerrado.is_set():
            return
        self.encerrado.set()
        try:
            self.fila.put_nowait(None)
        except queue.Full:
            pass
        # close() também escreve na rede. Shutdown desbloqueia um send preso sem
        # exigir outro envio pela conexão que deixou de receber os eventos.
        try:
            self.ws.sock.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass

    def _enviar(self):
        try:
            while not self.encerrado.is_set():
                payload = self.fila.get()
                if payload is None:
                    return
                self.ws.send(payload)
        except Exception:
            self.encerrar()


@sock.route('/ws')
def websocket(ws):
    ws = _ClienteWeb(ws)
    # O servidor escuta em 0.0.0.0 (dá pra abrir do celular). Ações que mexem NO PC
    # (abrir arquivo/pasta) ficam restritas a conexões do próprio PC.
    try:
        _eh_local = request.remote_addr in ('127.0.0.1', '::1')
    except Exception:
        _eh_local = False
    with _clientes_lock:
        _clientes.add(ws)
        
    # Assim que o site conecta, enviamos o estado atual
    try:
        boas_vindas = json.dumps({
            'usuario': _ultima_fala_usuario,
            'legenda': _ultima_fala_luna,
            'pensamento': _ultimo_pensamento,
            'estado': _ultimo_estado_rosto,
            'kaomoji': _ultimo_kaomoji,
        }, ensure_ascii=False)
        ws.send(boas_vindas)
        ws.send(json.dumps({"tipo": "config_estado", "estado": _config_para_web()}))
        ws.send(json.dumps({"tipo": "historico_completo", "turnos": list(_historico_web),
                            "pendentes": _fila_texto_web()}))
        ws.send(json.dumps({"tipo": "status", "texto": _ultimo_status}))
        ws.send(json.dumps({"tipo": "memoria_badge", "n": len(_memoria_estado()["pendentes"])}))
        ws.send(json.dumps({"tipo": "acompanhamentos", "estado": _acompanhamentos_estado()},
                           ensure_ascii=False))
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
                    global _arquivo_pendente, _imagem_anexada_pendente
                    if dados.get('formato') == 'imagem':
                        import base64
                        nome = dados.get('nome', 'imagem')
                        _imagem_anexada_pendente = {
                            "nome": nome,
                            "dados": base64.b64decode(dados.get('conteudo', '')),
                            "ext": (os.path.splitext(nome)[1].lstrip('.') or 'jpg').lower(),
                        }
                        _broadcast({"tipo": "arquivo_confirmado", "nome": nome})
                    else:
                        _arquivo_pendente = _processar_arquivo(dados)
                        _broadcast({"tipo": "arquivo_confirmado", "nome": _arquivo_pendente["nome"]})
                elif dados.get('tipo') == 'limpar_arquivo':
                    _arquivo_pendente = None
                    _imagem_anexada_pendente = None
                elif dados.get('comando') == 'limpar_historico':
                    _historico_web.clear()
                    _broadcast({"tipo": "historico_completo", "turnos": [],
                                "pendentes": _fila_texto_web()})
                elif dados.get('comando') == 'avaliar':
                    resultado = _registrar_avaliacao(
                        dados.get('rating', ''), dados.get('motivo', ''),
                        turno_id=dados.get('turno_id'), categorias=dados.get('categorias', []))
                    ws.send(json.dumps({"tipo": "avaliacao_salva", "ok": bool(resultado),
                                        "turno_id": dados.get('turno_id')}))
                elif dados.get('comando') in ('atividade_abrir', 'atividade_fechar'):
                    _assinar_atividade(ws, dados.get('comando') == 'atividade_abrir')
                elif dados.get('comando') == 'diagnostico_turno':
                    from modulos import avaliacoes
                    ws.send(json.dumps({"tipo": "diagnostico_turno", "turno_id": dados.get('turno_id'),
                                        "dados": avaliacoes.resumo_diagnostico(dados.get('turno_id'))},
                                       ensure_ascii=False))
                elif dados.get('comando') == 'repetir_fala':
                    try:
                        from modulos import falar
                        falar.repetir_ultima_fala()
                    except Exception:
                        pass
                elif dados.get('tipo') == 'mensagem_texto':
                    # Usuário DIGITOU na caixa do web (não falou) -> mesmas regras do Telegram,
                    # mas presença = no PC. Roda em thread pra não travar o WebSocket.
                    _receber_texto_web(ws, dados)
                elif dados.get('comando') == 'laboratorio_visual':
                    acao = str(dados.get('acao', ''))
                    if acao in _ACOES_LAB_VISUAL:
                        pacote = {
                            "tipo": "laboratorio_visual",
                            "acao": acao,
                            "destino": "widget" if _mascote_solto else "principal",
                        }
                        if acao == "rosto":
                            pacote["valor"] = str(dados.get('valor', ''))[:32]
                        _broadcast(pacote)
                # ---- Oficina (painel de config) ----
                elif dados.get('comando') == 'abrir_arquivo':
                    if _eh_local:
                        erro = _abrir_no_pc(dados.get('alvo', ''))
                        if erro:
                            ws.send(json.dumps({"tipo": "oficina_erro", "texto": erro}))
                    else:
                        ws.send(json.dumps({"tipo": "oficina_erro",
                                            "texto": "abrir arquivos só funciona no próprio PC"}))
                elif dados.get('comando') == 'falar_teste':
                    texto = (dados.get('texto') or '').strip()[:400]
                    if texto:
                        _falar_teste(texto)
                elif dados.get('comando') == 'pronuncia_listar':
                    from modulos import falar
                    ws.send(json.dumps({"tipo": "pronuncia", "itens": falar.obter_pronuncia()},
                                       ensure_ascii=False))
                elif dados.get('comando') == 'pronuncia_definir':
                    from modulos import falar
                    falar.definir_pronuncia(dados.get('palavra', ''), dados.get('grafia', ''))
                    _broadcast({"tipo": "pronuncia", "itens": falar.obter_pronuncia()})
                elif dados.get('comando') == 'pronuncia_remover':
                    from modulos import falar
                    falar.remover_pronuncia(dados.get('palavra', ''))
                    _broadcast({"tipo": "pronuncia", "itens": falar.obter_pronuncia()})
                elif dados.get('comando') == 'chaves_status':
                    ws.send(json.dumps({"tipo": "chaves", "itens": _status_chaves()},
                                       ensure_ascii=False))
                elif dados.get('comando') == 'modelos_listar':
                    ws.send(json.dumps({"tipo": "modelos", "estado": _estado_modelos()},
                                       ensure_ascii=False))
                elif dados.get('comando') == 'modelo_trocar':
                    if not _eh_local:
                        ws.send(json.dumps({"tipo": "modelo_status", "carregando": False,
                                            "ok": False,
                                            "texto": "trocar modelo só funciona no próprio PC"},
                                           ensure_ascii=False))
                    else:
                        threading.Thread(
                            target=_trocar_modelo_web,
                            args=(dados.get('modelo', ''), dados.get('thinking', 'desligado')),
                            daemon=True,
                        ).start()
                # ---- Memória episódica (caixa de revisão) ----
                elif dados.get('comando') == 'memoria_listar':
                    ws.send(json.dumps({"tipo": "memoria", "estado": _memoria_estado()}, ensure_ascii=False))
                elif dados.get('comando') == 'memoria_confirmar':
                    from modulos import memoria
                    memoria.mem_confirmar(dados.get('id', ''), dados.get('texto'))
                    _broadcast({"tipo": "memoria", "estado": _memoria_estado()})
                    notificar_memoria()
                elif dados.get('comando') == 'memoria_descartar':
                    from modulos import memoria
                    memoria.mem_descartar(dados.get('id', ''))
                    _broadcast({"tipo": "memoria", "estado": _memoria_estado()})
                    notificar_memoria()
                elif dados.get('comando') == 'memoria_restaurar':
                    from modulos import memoria
                    memoria.mem_restaurar(dados.get('id', ''))
                    _broadcast({"tipo": "memoria", "estado": _memoria_estado()})
                    notificar_memoria()
                elif dados.get('comando') == 'memoria_processar':
                    ws.send(json.dumps({"tipo": "memoria_processando"}))
                    def _processar_mem():
                        try:
                            from modulos import proativa
                            proativa.processar_memoria_agora()
                        except Exception:
                            pass
                        _broadcast({"tipo": "memoria", "estado": _memoria_estado()})
                        notificar_memoria()
                    threading.Thread(target=_processar_mem, daemon=True).start()
                # ---- Acompanhamentos: botões e fala resolvem o mesmo estado ----
                elif dados.get('comando') == 'acompanhamento_acao':
                    from modulos import acompanhamentos
                    confirmacao = acompanhamentos.estado_interface().get("confirmacao")
                    resposta = acompanhamentos.resolver(
                        dados.get('acao', ''), dados.get('id', ''), dados.get('quando', ''))
                    ws.send(json.dumps({"tipo": "acompanhamento_feedback",
                                        "texto": resposta or "Essa decisão já expirou."},
                                       ensure_ascii=False))
                    notificar_acompanhamentos()
                    # O toast confirma o estado, mas não substitui a conversa. Antes o clique
                    # encerrava tudo em silêncio; agora a persona recebe a escolha e o contexto.
                    if (resposta and confirmacao and confirmacao.get("tipo") == "proposta"
                            and _handler_acompanhamento_web):
                        import threading as _th
                        _th.Thread(
                            target=_handler_acompanhamento_web,
                            args=(dados.get('acao', ''), confirmacao, resposta),
                            daemon=True,
                        ).start()
                elif dados.get('comando') == 'sopro_acao':
                    from modulos import acompanhamento_sopro
                    resposta = acompanhamento_sopro.agir(
                        str(dados.get('acao', '')), identificador=str(dados.get('id', '')),
                        situacao=str(dados.get('situacao', '')))
                    ws.send(json.dumps({"tipo": "acompanhamento_feedback", "texto": resposta},
                                       ensure_ascii=False))
                    notificar_acompanhamentos()
                elif dados.get('comando') == 'ouvir_resposta':
                    _receber_ouvir_web(ws, dados)
                elif dados.get('comando') == 'parar_leitura':
                    _parar_leitura_web(dados.get('request_id'))
                elif dados.get('comando') == 'radar_interesse':
                    resposta = _receber_interesse_radar(dados)
                    ws.send(json.dumps({**resposta, 'tipo': 'radar_interesse_feedback',
                                        'turno_id': dados.get('turno_id', '')}, ensure_ascii=False))
                    notificar_acompanhamentos()
                elif dados.get('comando') == 'fonte_proposta_acao':
                    from modulos import fontes_conversa
                    resposta = fontes_conversa.resolver(dados.get('acao'), dados.get('id'), dados.get('cadastro'))
                    ws.send(json.dumps({**resposta, 'tipo': 'fonte_proposta_feedback'}, ensure_ascii=False))
                    notificar_acompanhamentos()
                elif dados.get('comando') == 'fonte_acao':
                    from modulos import acompanhamento_fontes
                    resposta = acompanhamento_fontes.agir(
                        str(dados.get('acao', '')), identificador=str(dados.get('id', '')),
                        cadastro=dados.get('cadastro'), novidade_id=str(dados.get('novidade_id', '')))
                    ws.send(json.dumps({**resposta, "tipo": "fonte_feedback",
                                        "acao": dados.get('acao', ''),
                                        "request_id": dados.get('request_id', '')}, ensure_ascii=False))
                    notificar_acompanhamentos()
                elif dados.get('comando') == 'acompanhamento_cancelar':
                    from modulos import acompanhamentos
                    ok = acompanhamentos.cancelar(dados.get('id', ''))
                    ws.send(json.dumps({"tipo": "acompanhamento_feedback",
                                        "texto": ("Acompanhamento removido." if ok
                                                  else "Esse acompanhamento não existe mais.")},
                                       ensure_ascii=False))
                    notificar_acompanhamentos()
                elif dados.get('comando') == 'conclusao_tarefa_acao':
                    from modulos import conclusao_tarefas
                    confirmacao = conclusao_tarefas.estado_interface().get("confirmacao")
                    resposta = conclusao_tarefas.resolver(dados.get('acao', ''), dados.get('id', ''))
                    ws.send(json.dumps({"tipo": "acompanhamento_feedback",
                                        "texto": resposta or "Essa decisão já expirou."},
                                       ensure_ascii=False))
                    notificar_acompanhamentos()
                    if resposta and confirmacao and _handler_conclusao_web:
                        import threading as _th
                        _th.Thread(
                            target=_handler_conclusao_web,
                            args=(dados.get('acao', ''), confirmacao, resposta),
                            daemon=True,
                        ).start()
                elif dados.get('config'):
                    _aplicar_config(dados)
    except ConnectionClosed:
        pass
    except Exception:
        _log.exception("Falha na conexão Web da Luna")
    finally:
        with _clientes_lock:
            _clientes.discard(ws)
        ws.encerrar()

def _receber_interesse_radar(dados):
    from modulos import interesses_radar
    if dados.get('acao') != 'remover':
        turno = next((t for t in tuple(_historico_web) if t.get('id') == dados.get('turno_id') and
                      t.get('origem_proativa') == 'radar_rss'), None)
        if not turno or not any(c.get('tipo') == 'noticia' for c in turno.get('cartoes_web', [])):
            return {'ok': False, 'texto': 'Esta notícia não está mais no histórico. Use uma notícia recente.'}
    return interesses_radar.agir(dados.get('acao'), dados.get('assunto'))


# Painel Atividade: só quem está com ele aberto recebe as linhas do CMD — sem isso o
# celular receberia o terminal inteiro o tempo todo. A marca fica no próprio cliente:
# quem desconecta sai de _clientes e, com isso, da atividade.
def _enviar_linha_atividade(linha):
    payload = json.dumps({"tipo": "atividade_linha", "linha": linha}, ensure_ascii=False)
    with _clientes_lock:
        alvos = [ws for ws in _clientes if getattr(ws, "atividade", False)]
    for ws in alvos:
        try:
            ws.send(payload)   # _ClienteWeb só enfileira: não trava quem deu o print
        except Exception:
            ws.atividade = False


def _assinar_atividade(ws, assinar: bool):
    from modulos import atividade
    atividade.ouvir(_enviar_linha_atividade)
    ws.atividade = bool(assinar)
    if assinar:
        ws.send(json.dumps({"tipo": "atividade_inicio", "linhas": atividade.instantaneo()},
                           ensure_ascii=False))


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


def atualizar_mascote_solto(solto: bool):
    """Define qual das duas interfaces deve receber o próximo evento visual."""
    global _mascote_solto
    _mascote_solto = bool(solto)


def _relogio_eventos_visuais():
    """Mantém um cronômetro por evento numa única thread, sem depender da página aberta."""
    agora = time.monotonic()
    proximos = {
        nome: agora + random.uniform(*intervalo)
        for nome, intervalo in _INTERVALOS_EVENTOS_VISUAIS.items()
    }
    while True:
        agora = time.monotonic()
        vencidos = [nome for nome, quando in proximos.items() if quando <= agora]
        for nome in vencidos:
            _broadcast({
                "tipo": "evento_visual",
                "evento": nome,
                "destino": "widget" if _mascote_solto else "principal",
            })
            proximos[nome] = agora + random.uniform(*_INTERVALOS_EVENTOS_VISUAIS[nome])

        proximo = min(proximos.values())
        time.sleep(max(0.25, min(60.0, proximo - time.monotonic())))


def _iniciar_relogio_eventos_visuais():
    global _relogio_visual_iniciado
    with _relogio_visual_lock:
        if _relogio_visual_iniciado:
            return
        _relogio_visual_iniciado = True
    threading.Thread(target=_relogio_eventos_visuais, daemon=True).start()

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


def injetar_arquivo_pendente(texto: str) -> str:
    """Anexa texto/PDF pendente à mensagem, independente de ela vir por voz ou teclado."""
    arquivo = obter_e_limpar_arquivo()
    if not arquivo:
        return texto
    print(f"[Arquivo injetado: {arquivo['nome']} ({len(arquivo['conteudo'])} chars)]")
    return f"[Arquivo: {arquivo['nome']}]\n{arquivo['conteudo']}\n\n{texto}"

def obter_e_limpar_imagem_anexada():
    global _imagem_anexada_pendente
    img = _imagem_anexada_pendente
    _imagem_anexada_pendente = None
    return img

# --- FUNÇÕES PARA VOCÊ USAR NO MAIN.PY ---

def _registrar_avaliacao(rating: str, motivo: str = "", usuario=None, luna=None, canal="web",
                        turno_id=None, categorias=None):
    """Grava a avaliação (👍/👎) de uma resposta para análise posterior.
    O ID fixa o alvo; chamadas antigas sem ID usam o último turno completo."""
    if rating not in ("bom", "ruim"):
        return
    from modulos import avaliacoes
    try:
        if not turno_id and canal == "web" and usuario is None and luna is None and _historico_web:
            turno_id = _historico_web[-1].get("id")
        snapshot = avaliacoes.obter_turno(turno_id) if turno_id else None
        if turno_id and (not snapshot or snapshot["canal"] != canal):
            return None  # ID expirado nunca pode avaliar outra resposta silenciosamente.
        usuario_real = snapshot["usuario"] if snapshot else (usuario or "")
        luna_real = snapshot["luna"] if snapshot else (luna or "")
        if not luna_real:
            return None
        from modulos import metricas_ferramentas
        ferramenta = metricas_ferramentas.vincular_avaliacao(
            rating, usuario_real, luna_real, canal
        )
        registro = dict(snapshot or {})
        registro.update({
            "canal": canal,
            "rating": rating,
            "motivo": str(motivo or "").strip()[:1000],
            "categorias": list(dict.fromkeys(c for c in (categorias or [])
                               if isinstance(c, str) and c in avaliacoes.CATEGORIAS))[:8]
                               if isinstance(categorias, list) else [],
            "usuario": usuario_real,
            "luna": luna_real,
        })
        if ferramenta:
            registro["ferramenta"] = ferramenta
        salvo = avaliacoes.salvar(registro)
        print(f"[{'👍' if rating == 'bom' else '👎'} Avaliação ({canal}): {rating}]")
        return salvo["avaliacao_id"]
    except Exception:
        pass

def _registrar_turno(usuario: str, luna: str, origem_proativa: str = "", clima: str = "", links_novidades=None,
                    cartoes_web=None):
    global _clima_turno_pendente
    import datetime
    from modulos import avaliacoes
    execucao = avaliacoes.controle.contexto.get()
    anterior = avaliacoes.obter_turno(_historico_web[-1].get("id")) if _historico_web else None
    if (_historico_web and _historico_web[-1].get("luna") == luna
            and _historico_web[-1].get("usuario") == usuario
            and (execucao is None or (anterior and anterior.get("execucao_id") == execucao.numero))):
        _clima_turno_pendente = ""
        return  # evita duplicação quando atualizar_legenda é chamada duas vezes
    turno = {
        "usuario": usuario,
        "luna": luna,
        "tempo": datetime.datetime.now().strftime("%H:%M"),
    }
    if _texto_web_id.get():
        turno["request_id"] = _texto_web_id.get()
    if origem_proativa:
        turno["origem_proativa"] = origem_proativa
    if links_novidades:
        turno["links_novidades"] = dict(links_novidades)
    if cartoes_web:
        from modulos.cartoes_web import normalizar
        cartoes = normalizar(cartoes_web)
        if cartoes:
            turno["cartoes_web"] = cartoes
    clima_turno = str(clima or _clima_turno_pendente or "").strip()
    if clima_turno:
        turno["clima"] = clima_turno
        cor.cinza(f"[🎭 Clima do turno Web: {clima_turno}]")
    _clima_turno_pendente = ""
    turno["id"] = avaliacoes.capturar_turno(turno, _historico_web)
    from modulos.biblioteca_web import contexto_resposta, registrar_turno
    referencia = contexto_resposta.get()
    if referencia:
        turno['resposta_a'] = {**referencia['referencia'], 'trecho': referencia['luna'][:140]}
    try:
        registrar_turno(turno)
    except (OSError, ValueError):
        _log.exception('Não foi possível arquivar o turno para a busca')
    _historico_web.append(turno)
    if len(_historico_web) > 40:
        _historico_web.pop(0)
    _broadcast({"tipo": "historico_novo", "turno": turno})

def atualizar_legenda(texto: str, origem_proativa: str = "", clima: str = ""):
    global _ultima_fala_luna
    links_novidades = getattr(texto, "links_novidades", None)
    cartoes_web = getattr(texto, "cartoes_web", None)
    texto = _remover_tags_voz(texto)   # voz fica com os tags; texto exibido não
    _ultima_fala_luna = texto
    _broadcast({'legenda': texto})
    if texto:
        _registrar_turno(_ultima_fala_usuario, texto, origem_proativa, clima, links_novidades, cartoes_web)

def atualizar_stream_resposta(texto: str):
    """Mostra uma prévia da persona sem contaminar histórico, avaliação ou última fala."""
    _broadcast({"tipo": "resposta_stream", "texto": texto or ""})

def atualizar_stream_interrompido(motivo: str = "interrompida"):
    """Fecha só a prévia visual; uma resposta incompleta nunca vira turno nem avaliação."""
    _broadcast({"tipo": "resposta_stream_interrompida", "motivo": motivo})

def atualizar_usuario(texto: str):
    global _ultima_fala_usuario
    _ultima_fala_usuario = texto
    identificador = _texto_web_id.get()
    if identificador:
        with _textos_web_lock:
            item = _textos_web.get(identificador)
            if item:
                item["estado"] = "respondendo"
                espera = time.monotonic() - item["recebido_em"]
                _log.info("[Web] Iniciando id=%s; espera na fila %.1fs", identificador, espera)
                cor.cinza(f"[⌨️ Web: espera na fila {espera:.1f}s]")
    _broadcast({'usuario': texto, 'request_id': identificador})

def atualizar_estado_rosto(estado: str):
    """Envia o estado visual e deixa a transição observável no terminal."""
    global _ultimo_estado_rosto
    if estado != _ultimo_estado_rosto:
        anterior = _ultimo_estado_rosto or "inicial"
        cor.cinza(f"[🎭 Estado visual: {anterior} → {estado}]")
        _ultimo_estado_rosto = estado
    _broadcast({'estado': estado})

# Catálogo CURADO de reações -> termos-meme testados (que dão GIF bom, não "pedra").
# O 12B escolhe só a REAÇÃO (ex: [gif:deboche]); a gente traduz pro termo real. Isso mata
# o problema de ele inventar adjetivo vago (chillax/vibing) que o Giphy resolve com stock
# genérico. Termo fora da lista -> fallback (busca direto, como antes).
_REACOES_GIF = {
    "deboche":    ["deal with it", "oh really"],
    "facepalm":   ["picard facepalm", "facepalm"],
    "cope":       ["this is fine"],
    "suspeita":   ["suspicious"],
    "orgulho":    ["nailed it"],
    "hype":       ["lets go", "excited"],
    "aplauso":    ["slow clap", "applause"],
    "choque":     ["surprised pikachu", "mind blown"],
    "cansaco":    ["tired anime", "tired tom"],
    "tedio":      ["bored waiting", "tumbleweed"],
    "desisto":    ["rage quit"],
    "carinho":    ["hug meme", "there there"],
    "torcida":    ["you got this"],
    "gg":         ["gg", "victory", "gg ez"],
    "carregar":   ["hard carry", "1v9"],
    "pensando":   ["math lady", "hmm"],
    "sem_reacao": ["blank stare", "unamused"],
    "musica":     ["music"],
    "leitura":    ["read"],
}

def _resolver_reacao(termo: str) -> str:
    """Traduz uma REAÇÃO do catálogo pra um termo-meme curado (sorteando entre os da lista).
    Normaliza minúsculas/acento/espaços pra casar 'Cansaço'/'sem reação' etc. Se não for
    reação conhecida, devolve o termo como veio (fallback do comportamento antigo)."""
    import unicodedata, random
    chave = unicodedata.normalize("NFKD", (termo or "").strip().lower())
    chave = "".join(c for c in chave if not unicodedata.combining(c)).replace(" ", "_")
    if chave in _REACOES_GIF:
        return random.choice(_REACOES_GIF[chave])
    return termo

def _buscar_gif(termo: str) -> str:
    api_key = os.getenv("GIPHY_API_KEY", "")
    if not api_key:
        return ""
    termo = _resolver_reacao(termo)               # reação -> termo-meme curado (ou passa direto)
    try:
        r = httpx.get(
            "https://api.giphy.com/v1/gifs/search",
            params={"api_key": api_key, "q": termo, "limit": 5, "rating": "r", "lang": "en"},
            timeout=5,
        )
        gifs = r.json().get("data", [])
        if gifs:
            import random
            # top-3 (não top-5): o 1º costuma ser o meme icônico; sortear entre os 3
            # primeiros dá variedade sem cair no resultado ruim lá do fim da lista.
            escolhido = random.choice(gifs[:3])
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

def atualizar_status(texto: str):
    """Linha de status do web: o que a Luna está fazendo agora (proativo, ferramenta, suspensa)."""
    global _ultimo_status
    _ultimo_status = texto or "🌚 Por aqui"
    _broadcast({"tipo": "status", "texto": _ultimo_status})

def atualizar_jogo(nome):
    """Avisa o web que um jogo abriu (nome) ou fechou (None) — a presença entra em modo jogo."""
    _broadcast({"jogo": nome or ""})

def atualizar_kaomoji(k: str, clima: str = ""):
    """Manda o rosto ao mascote e vincula o clima à próxima fala exibida no Web."""
    global _ultimo_kaomoji, _clima_turno_pendente
    _ultimo_kaomoji = k
    _clima_turno_pendente = str(clima or "").strip()
    _broadcast({"kaomoji": k, "clima": _clima_turno_pendente})

def atualizar_gif(termo: str):
    """Busca um GIF no Giphy para o termo e faz broadcast — chamada não bloqueia."""
    def _worker():
        url = _buscar_gif(termo)
        if url:
            controle.efeito(_broadcast)({"gif_url": url, "gif_termo": termo})
    threading.Thread(target=vincular(_worker), daemon=True).start()

#------------------------------

def iniciar_servidor():
    """Inicia o servidor Flask em uma thread separada para não bloquear o main.py"""
    _iniciar_relogio_eventos_visuais()
    threading.Thread(
        target=lambda: app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False),
        daemon=True
    ).start()
    print("[🌐 Servidor da Luna: Rodando em http://localhost:5000]")


# Protege estado e broadcast juntos, inclusive callbacks atrasados.
atualizar_legenda = controle.efeito(atualizar_legenda)
atualizar_stream_resposta = controle.efeito(atualizar_stream_resposta)
atualizar_stream_interrompido = controle.efeito(atualizar_stream_interrompido)
atualizar_usuario = controle.efeito(atualizar_usuario)
atualizar_estado_rosto = controle.efeito(atualizar_estado_rosto)
atualizar_metricas = controle.efeito(atualizar_metricas)
atualizar_pensamento = controle.efeito(atualizar_pensamento)
atualizar_status = controle.efeito(atualizar_status)
atualizar_kaomoji = controle.efeito(atualizar_kaomoji)
atualizar_gif = controle.efeito(atualizar_gif)
