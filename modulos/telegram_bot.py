# modulos/telegram_bot.py

import os
import re
import threading
import logging
import telebot

_log = logging.getLogger("luna.telegram")
logging.getLogger("TeleBot").setLevel(logging.CRITICAL)  # suprime tracebacks de rede

TELEGRAM_TOKEN   = os.getenv("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = int(os.getenv("TELEGRAM_CHAT_ID", "0"))

_historico_telegram = []


def _limpar_resposta(texto: str) -> str:
    texto = re.sub(r'\[gif:[^\]]*\]', '', texto)   # [gif:termo]
    texto = re.sub(r'\[[^\]]{1,40}\]', '', texto)  # [streak], [thinking emoji], etc.
    return texto.strip()


def iniciar_bot_telegram():
    if not TELEGRAM_TOKEN:
        _log.warning("TELEGRAM_TOKEN não configurado — bot Telegram desativado.")
        return

    bot = telebot.TeleBot(TELEGRAM_TOKEN, parse_mode=None)

    @bot.message_handler(func=lambda m: True)
    def handle_message(message):
        global _historico_telegram

        if message.from_user.id != TELEGRAM_CHAT_ID:
            return

        texto = (message.text or "").strip()
        if not texto:
            return

        import modelos.cores as cor
        cor.azul(f"[📱 Telegram] {texto}")
        _log.info(f"[Telegram] Usuário: {texto}")

        try:
            from modulos.pensar import gerar_resposta, obter_e_limpar_imagem_pendente
            import servidor as _srv
            # Bloqueia broadcast de GIF para não consumir cota desnecessariamente
            _gif_original = _srv.atualizar_gif
            _srv.atualizar_gif = lambda termo: None

            resposta = gerar_resposta(texto, _historico_telegram, responder_completo=True)
            imagem = obter_e_limpar_imagem_pendente()

            _srv.atualizar_gif = _gif_original  # restaura

            resposta_limpa = _limpar_resposta(resposta)

            if imagem:
                try:
                    import io
                    if imagem["tipo"] == "b64":
                        import base64
                        foto = io.BytesIO(base64.b64decode(imagem["dado"]))
                        foto.name = "luna.jpg"
                    elif imagem["tipo"] == "bytes":
                        foto = io.BytesIO(imagem["dado"])
                        foto.name = "luna.png"
                    else:  # 'url' (fallback)
                        foto = imagem["dado"]
                    bot.send_photo(TELEGRAM_CHAT_ID, foto, caption=(resposta_limpa[:1024] or None))
                    cor.ciano(f"[📱 Telegram Luna 📷] {resposta_limpa[:80]}")
                    _log.info(f"[Telegram] Luna [foto]: {resposta_limpa[:100]}")
                except Exception as e:
                    _log.exception(f"Erro ao enviar foto Telegram: {e}")
                    if resposta_limpa:
                        bot.send_message(TELEGRAM_CHAT_ID, resposta_limpa)
            elif resposta_limpa:
                bot.send_message(TELEGRAM_CHAT_ID, resposta_limpa)
                cor.ciano(f"[📱 Telegram Luna] {resposta_limpa}")
                _log.info(f"[Telegram] Luna: {resposta_limpa[:100]}")
        except Exception as e:
            _log.exception(f"Erro Telegram: {e}")
            bot.send_message(TELEGRAM_CHAT_ID, "Deu um erro aqui, tenta de novo.")

    def _rodar():
        print("[📱 Bot Telegram: aguardando mensagens]")
        _log.info("Bot Telegram iniciado.")
        bot.infinity_polling(timeout=20, long_polling_timeout=10)

    threading.Thread(target=_rodar, daemon=True).start()
