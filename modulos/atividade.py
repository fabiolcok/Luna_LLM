"""Atividade: as linhas do CMD guardadas para o painel da web (Configuração > Avançado).

O print com horário do main.py manda cada linha para cá; avisos e erros que só iam para o
luna.log entram pelo HandlerLog. Fica só em memória: é para olhar o que está acontecendo
agora sem abrir o terminal, não para substituir o luna.log.
"""
import collections
import datetime
import logging
import re
import threading

LIMITE = 600
_ANSI = re.compile(r"\x1b\[[0-9;]*m")
_VERMELHO = "\x1b[91m"

# Ordem importa: a primeira que casar vence. "visual" vem antes de "modelo" porque as linhas
# de estado do rosto também usam 🎭 e são as mais frequentes — separadas, dá pra escondê-las.
_REGRAS = (
    ("erro", re.compile(r"⚠️|❌|\berro\b|falh|descartad|exception|traceback|\[(WARNING|ERROR|CRITICAL)\]", re.I)),
    ("visual", re.compile(r"Estado visual|Evento visual|kaomoji", re.I)),
    ("conversa", re.compile(r"⌨️|💬|Você:|Luna respondeu|Web texto|Telegram|Usuário:")),
    ("ferramenta", re.compile(r"⚙️|Motor Lógico|Ferramenta|Usando:|Acessando|habilidade", re.I)),
    ("proativo", re.compile(r"proativ|radar|📡", re.I)),
    ("modelo", re.compile(r"🎭|🧩|📦|Roteador|Persona|🧠|TurboLLM|Modelo|Personalidade", re.I)),
    ("voz", re.compile(r"🎙|🔊|🎤|Kokoro|Whisper|\bouv|\bfala\b|áudio|audio", re.I)),
    ("memoria", re.compile(r"📏|mem[oó]ria|💾|Obsidian|ChromaDB|embedding", re.I)),
)

_lock = threading.Lock()
_linhas = collections.deque(maxlen=LIMITE)
_ouvintes = []
_seq = 0


def categoria(texto: str, bruto: str = "") -> str:
    if _VERMELHO in bruto:
        return "erro"
    for nome, regra in _REGRAS:
        if regra.search(texto):
            return nome
    return "outros"


def registrar(bruto: str, hora: str = ""):
    """Nunca levanta: é chamado de dentro do print global."""
    global _seq
    try:
        texto = _ANSI.sub("", str(bruto)).strip()
        if not texto or set(texto) <= set("=-─━ "):   # separadores do CMD não são atividade
            return
        with _lock:
            _seq += 1
            linha = {"n": _seq, "hora": hora or datetime.datetime.now().strftime("%H:%M:%S"),
                     "texto": texto[:2000], "categoria": categoria(texto, str(bruto))}
            _linhas.append(linha)
            ouvintes = list(_ouvintes)
        for fn in ouvintes:
            try:
                fn(linha)
            except Exception:
                pass
    except Exception:
        pass


def instantaneo() -> list:
    with _lock:
        return list(_linhas)


def ouvir(fn):
    with _lock:
        if fn not in _ouvintes:
            _ouvintes.append(fn)


class HandlerLog(logging.Handler):
    """Avisos e erros do logging (inclusive exceções que não passam pelo print)."""
    def __init__(self):
        super().__init__(level=logging.WARNING)

    def emit(self, record):
        try:
            texto = f"[{record.levelname}] {record.name}: {record.getMessage()}"
            if record.exc_info and record.exc_info[1] is not None:
                texto += f" — {type(record.exc_info[1]).__name__}: {record.exc_info[1]}"
            registrar(texto)
        except Exception:
            pass
