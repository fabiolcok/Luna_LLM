# modulos/telegram_bot.py

import os
import re
import random
import threading
import logging
import telebot
from telebot import types

_log = logging.getLogger("luna.telegram")
logging.getLogger("TeleBot").setLevel(logging.CRITICAL)  # suprime tracebacks de rede

TELEGRAM_TOKEN   = os.getenv("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = int(os.getenv("TELEGRAM_CHAT_ID", "0"))

_historico_telegram = []

# Avaliação 👍/👎: guarda exchanges recentes e o reply pendente de motivo
_avaliacoes = {}        # aid -> (usuario, luna)
_aval_seq = 0
_motivo_por_msg = {}    # message_id do pedido de motivo -> aid


def _limpar_resposta(texto: str) -> str:
    texto = re.sub(r'\[gif:[^\]]*\]', '', texto)   # [gif:termo]
    texto = re.sub(r'\[[^\]]{1,40}\]', '', texto)  # [streak], [thinking emoji], etc.
    # Tags de voz do Supertonic (<sigh>, <laugh>...) não fazem sentido no texto
    texto = re.sub(r'</?(?:laugh|breath|sigh|surprise|scream|throatclear|sad|angry|cough|yawn)>', '', texto, flags=re.IGNORECASE)
    return texto.strip()


def _registrar_exchange(usuario: str, luna: str) -> str:
    """Guarda o par pergunta/resposta e devolve um id, para os botões de avaliação."""
    global _aval_seq
    _aval_seq += 1
    aid = str(_aval_seq)
    _avaliacoes[aid] = (usuario, luna)
    if len(_avaliacoes) > 40:
        _avaliacoes.pop(next(iter(_avaliacoes)))
    return aid


def _teclado_aval(aid: str):
    kb = types.InlineKeyboardMarkup()
    kb.add(
        types.InlineKeyboardButton("👍", callback_data=f"av|bom|{aid}"),
        types.InlineKeyboardButton("👎", callback_data=f"av|ruim|{aid}"),
    )
    return kb


def iniciar_bot_telegram():
    if not TELEGRAM_TOKEN:
        _log.warning("TELEGRAM_TOKEN não configurado — bot Telegram desativado.")
        return

    bot = telebot.TeleBot(TELEGRAM_TOKEN, parse_mode=None)

    def _responder_como_luna(texto: str):
        """Fluxo comum de resposta (texto digitado OU áudio transcrito):
        gera a resposta da Luna e envia, com foto e botões de avaliação."""
        import servidor as _srv
        import modelos.cores as cor
        try:
            from modulos.pensar import gerar_resposta, obter_e_limpar_imagem_pendente
            # Bloqueia broadcast de GIF para não consumir cota desnecessariamente
            _gif_original = _srv.atualizar_gif
            _srv.atualizar_gif = lambda termo: None

            resposta = gerar_resposta(texto, _historico_telegram, responder_completo=True)
            imagem = obter_e_limpar_imagem_pendente()

            _srv.atualizar_gif = _gif_original  # restaura

            resposta_limpa = _limpar_resposta(resposta)
            if not resposta_limpa and not imagem:
                return

            aid = _registrar_exchange(texto, resposta_limpa)
            teclado = _teclado_aval(aid)

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
                    bot.send_photo(TELEGRAM_CHAT_ID, foto, caption=(resposta_limpa[:1024] or None), reply_markup=teclado)
                    cor.ciano(f"[📱 Telegram Luna 📷] {resposta_limpa[:80]}")
                    _log.info(f"[Telegram] Luna [foto]: {resposta_limpa[:100]}")
                except Exception as e:
                    _log.exception(f"Erro ao enviar foto Telegram: {e}")
                    if resposta_limpa:
                        bot.send_message(TELEGRAM_CHAT_ID, resposta_limpa, reply_markup=teclado)
            elif resposta_limpa:
                bot.send_message(TELEGRAM_CHAT_ID, resposta_limpa, reply_markup=teclado)
                cor.ciano(f"[📱 Telegram Luna] {resposta_limpa}")
                _log.info(f"[Telegram] Luna: {resposta_limpa[:100]}")
        except Exception as e:
            _log.exception(f"Erro Telegram: {e}")
            bot.send_message(TELEGRAM_CHAT_ID, "Deu um erro aqui, tenta de novo.")

    @bot.message_handler(func=lambda m: True)
    def handle_message(message):
        if message.from_user.id != TELEGRAM_CHAT_ID:
            return

        texto = (message.text or "").strip()
        if not texto:
            return

        import servidor as _srv
        import modelos.cores as cor

        # É uma resposta (reply) dando o motivo de um 👎?
        reply = getattr(message, "reply_to_message", None)
        if reply and reply.message_id in _motivo_por_msg:
            aid = _motivo_por_msg.pop(reply.message_id)
            u, l = _avaliacoes.get(aid, ("", ""))
            _srv._registrar_avaliacao("ruim", texto, u, l, canal="telegram")
            bot.send_message(TELEGRAM_CHAT_ID, "Anotado, valeu! 🙏")
            return

        cor.azul(f"[📱 Telegram] {texto}")
        _log.info(f"[Telegram] Usuário: {texto}")
        _responder_como_luna(texto)

    @bot.message_handler(content_types=['voice', 'audio'])
    def handle_voice(message):
        # Modo STT: áudio/voice vira texto (Whisper local) e segue o fluxo normal.
        if message.from_user.id != TELEGRAM_CHAT_ID:
            return

        import modelos.cores as cor
        arq = message.voice or message.audio
        if getattr(arq, "duration", 0) > 120:
            bot.reply_to(message, "Áudio muito longo (mais de 2 minutos) — manda um mais curtinho?")
            return

        try:
            info = bot.get_file(arq.file_id)
            dados = bot.download_file(info.file_path)

            from modulos.ouvir import transcrever_bytes
            texto = transcrever_bytes(dados)
            if not texto:
                bot.reply_to(message, "Não consegui entender o áudio, pode repetir?")
                return

            # Mostra o que foi entendido (colado no áudio) — ajuda a conferir a transcrição
            bot.reply_to(message, f'🎤 "{texto}"')
            cor.azul(f"[📱 Telegram 🎤] {texto}")
            _log.info(f"[Telegram] Usuário [voz]: {texto}")
            _responder_como_luna(texto)
        except Exception as e:
            _log.exception(f"Erro no áudio Telegram: {e}")
            bot.send_message(TELEGRAM_CHAT_ID, "Deu erro ao processar o áudio, tenta de novo.")

    @bot.message_handler(content_types=['photo'])
    def handle_photo(message):
        # Caminho A (arquivar): salva a foto + legenda no Inbox, SEM Gemini.
        # A legenda é a descrição; análise por visão fica para o Caminho B.
        if message.from_user.id != TELEGRAM_CHAT_ID:
            return

        import modelos.cores as cor
        from modulos import obsidian

        legenda = (message.caption or "").strip()
        cor.azul(f"[📱 Telegram 📷] foto recebida — legenda: '{legenda or '(sem legenda)'}'")
        _log.info(f"[Telegram] Usuário [foto]: {legenda or '(sem legenda)'}")

        try:
            info = bot.get_file(message.photo[-1].file_id)   # [-1] = maior resolução
            dados = bot.download_file(info.file_path)
            resultado = obsidian.salvar_foto(dados, legenda, origem="telegram", ext="jpg")

            if resultado.startswith("SISTEMA: Foto salva"):
                m = re.search(r"Inbox\): '(.+)'", resultado)
                t = (m.group(1) if m else (legenda or "a foto")).strip()
                # Confirmação com a voz da persona; frases prontas só como fallback.
                from modulos.pensar import frase_confirmacao
                conf = frase_confirmacao(
                    f"Você acabou de arquivar no Inbox do Obsidian do Fábio uma foto que ele "
                    f"te mandou pelo Telegram, com o título '{t}'. Confirme pra ele em 1 frase "
                    f"curta, do seu jeito, citando o título."
                ) or random.choice([
                    f'Salvei a foto no seu Inbox: "{t}". 📷',
                    f'Prontinho, guardei a foto "{t}" nas suas notas.',
                    f'Foto arquivada no seu Obsidian: "{t}".',
                ])
                cor.ciano(f"[📱 Telegram Luna] {conf}")
                _log.info(f"[Telegram] Luna [foto salva]: {t}")
            else:
                conf = "Não consegui salvar a foto agora, tenta de novo?"
                _log.warning(f"[Telegram] falha ao salvar foto: {resultado}")
            bot.send_message(TELEGRAM_CHAT_ID, conf)
        except Exception as e:
            _log.exception(f"Erro ao salvar foto Telegram: {e}")
            bot.send_message(TELEGRAM_CHAT_ID, "Deu erro ao salvar a foto, tenta de novo.")

    @bot.callback_query_handler(func=lambda c: (c.data or "").startswith("av|"))
    def handle_aval(c):
        import servidor as _srv
        try:
            _, rating, aid = c.data.split("|", 2)
            u, l = _avaliacoes.get(aid, ("", ""))
            if rating == "bom":
                _srv._registrar_avaliacao("bom", "", u, l, canal="telegram")
                bot.answer_callback_query(c.id, "👍 valeu!")
            else:
                _srv._registrar_avaliacao("ruim", "", u, l, canal="telegram")  # registra já; motivo é opcional
                bot.answer_callback_query(c.id, "👎 anotado")
                msg = bot.send_message(TELEGRAM_CHAT_ID, "O que não funcionou? Responda ESTA mensagem (ou ignore).")
                _motivo_por_msg[msg.message_id] = aid
                if len(_motivo_por_msg) > 20:
                    _motivo_por_msg.pop(next(iter(_motivo_por_msg)))
        except Exception as e:
            _log.exception(f"Erro avaliação Telegram: {e}")
        # remove os botões pra não avaliar duas vezes
        try:
            bot.edit_message_reply_markup(c.message.chat.id, c.message.message_id, reply_markup=None)
        except Exception:
            pass

    def _rodar():
        print("[📱 Bot Telegram: aguardando mensagens]")
        _log.info("Bot Telegram iniciado.")
        bot.infinity_polling(timeout=20, long_polling_timeout=10)

    threading.Thread(target=_rodar, daemon=True).start()
