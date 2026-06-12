# log.py — configuração central de logging da Luna
import logging
import os
from logging.handlers import RotatingFileHandler

_configurado = False

def configurar():
    global _configurado
    if _configurado:
        return
    _configurado = True

    pasta_logs = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")
    os.makedirs(pasta_logs, exist_ok=True)

    arquivo_log = os.path.join(pasta_logs, "luna.log")

    handler_arquivo = RotatingFileHandler(
        arquivo_log,
        maxBytes=1 * 1024 * 1024,  # 1 MB por arquivo
        backupCount=5,
        encoding="utf-8",
    )
    handler_arquivo.setLevel(logging.DEBUG)
    handler_arquivo.setFormatter(logging.Formatter(
        "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    ))

    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.addHandler(handler_arquivo)

    # Silencia libs barulhentas que poluem o log com requests/internals
    for lib in (
        "urllib3", "httpx", "httpcore", "websockets", "asyncio",
        "openai", "openai._base_client",           # evita dump do corpo das requests
        "chromadb", "chromadb.config",             # internals do banco vetorial
        "sentence_transformers",                   # carregamento do modelo de embeddings
        "supertonic", "supertonic.loader",         # carregamento do TTS
        "faster_whisper",                          # internals do STT
    ):
        logging.getLogger(lib).setLevel(logging.WARNING)
