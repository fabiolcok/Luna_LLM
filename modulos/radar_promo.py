# radar_promo.py — TRANSPORTE do radar de promoções: lê mensagens recentes dos canais
# do Telegram que o usuário acompanha (via Telethon, logado como a conta DELE).
#
# É o gêmeo do feedparser do radar de RSS: só busca e devolve as mensagens cruas. Quem
# filtra por palavra-chave, deduplica e escreve no Obsidian é a proativa (_tarefa_radar_
# promocoes), igualzinho ao radar de RSS. Assim o resto da engrenagem é reaproveitado.
#
# Telethon é async; aqui roda um loop asyncio próprio numa thread daemon, e a proativa
# (síncrona) fala com ele via run_coroutine_threadsafe. Degrada em silêncio se o telethon
# não estiver instalado, o .env não tiver as chaves, ou a sessão não estiver autorizada
# (nesse caso o usuário roda setup_telegram_promo.py UMA vez pra logar).

import os
import asyncio
import threading
import logging

import modelos.cores as cor

_log = logging.getLogger("luna.promo")

API_ID = os.getenv("TELEGRAM_API_ID", "").strip()
API_HASH = os.getenv("TELEGRAM_API_HASH", "").strip()
SESSION = "modelos/luna_promo"   # Telethon salva como modelos/luna_promo.session (gitignored)

_loop = None
_loop_pronto = threading.Event()
_client = None
_estado = None            # None=não tentou | False=indisponível | True=ok
_avisou = False           # pra não repetir o mesmo erro em todo ciclo
_lock = threading.Lock()


def _rodar_loop():
    global _loop
    _loop = asyncio.new_event_loop()
    asyncio.set_event_loop(_loop)
    _loop_pronto.set()
    _loop.run_forever()


async def _conectar() -> bool:
    """Cria o client DENTRO do loop dedicado (bind correto) e checa se está logado."""
    global _client
    from telethon import TelegramClient
    _client = TelegramClient(SESSION, int(API_ID), API_HASH)
    await _client.connect()
    return await _client.is_user_authorized()


def _garantir_cliente() -> bool:
    """Sobe o loop + client na 1a chamada. Devolve True se der pra usar. Não lança."""
    global _estado, _avisou
    if _estado is not None:
        return _estado
    with _lock:
        if _estado is not None:
            return _estado
        if not API_ID or not API_HASH:
            if not _avisou:
                cor.vermelho("[🏷️ Promoções: falta TELEGRAM_API_ID/TELEGRAM_API_HASH no .env — radar off]")
                _avisou = True
            _estado = False
            return False
        try:
            import telethon  # noqa: F401
        except ImportError:
            if not _avisou:
                cor.vermelho("[🏷️ Promoções: telethon não instalado — pip install telethon]")
                _avisou = True
            _estado = False
            return False
        try:
            if _loop is None:
                threading.Thread(target=_rodar_loop, daemon=True).start()
                _loop_pronto.wait(timeout=10)
            autorizado = asyncio.run_coroutine_threadsafe(_conectar(), _loop).result(timeout=30)
            if not autorizado:
                if not _avisou:
                    cor.vermelho("[🏷️ Promoções: sessão não autorizada — rode 'python setup_telegram_promo.py' uma vez]")
                    _avisou = True
                _estado = False
                return False
            cor.magenta("[🏷️ Radar de promoções conectado ao Telegram]")
            _estado = True
            return True
        except Exception as e:
            if not _avisou:
                cor.vermelho(f"[🏷️ Promoções: falha ao conectar ({e}) — radar off]")
                _avisou = True
            _estado = False
            return False


async def _buscar(canais, limite):
    out = []
    for canal in canais:
        try:
            ent = await _client.get_entity(canal)
            uname = getattr(ent, "username", None)
            async for msg in _client.iter_messages(ent, limit=limite):
                txt = msg.message or ""
                if not txt.strip():
                    continue
                link = f"https://t.me/{uname}/{msg.id}" if uname else ""
                tem_foto = bool(getattr(msg, "photo", None))
                out.append((canal, msg.id, txt, link, msg.date, tem_foto))
        except Exception as e:
            _log.warning(f"[promo] canal {canal} falhou: {e}")
            continue
    return out


def buscar_mensagens(canais: list, limite: int = 25) -> list:
    """Devolve mensagens recentes dos canais: lista de (canal, msg_id, texto, link, data, tem_foto).
    Síncrona (a proativa chama assim); ponte pro loop async do Telethon. [] se indisponível."""
    if not canais or not _garantir_cliente():
        return []
    try:
        return asyncio.run_coroutine_threadsafe(_buscar(canais, limite), _loop).result(timeout=90)
    except Exception as e:
        _log.warning(f"[promo] busca falhou: {e}")
        return []


async def _baixar_foto(canal, mid, destino):
    ent = await _client.get_entity(canal)
    msg = await _client.get_messages(ent, ids=mid)
    if msg and getattr(msg, "photo", None):
        return await _client.download_media(msg, file=destino)
    return None


def baixar_foto(canal: str, mid: int, destino: str):
    """Baixa a foto de UMA mensagem (só as que casaram) pro caminho 'destino'.
    Devolve o caminho salvo ou None. Não lança."""
    if not _garantir_cliente():
        return None
    try:
        return asyncio.run_coroutine_threadsafe(_baixar_foto(canal, mid, destino), _loop).result(timeout=60)
    except Exception as e:
        _log.warning(f"[promo] download de foto falhou ({canal}:{mid}): {e}")
        return None
