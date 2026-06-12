#ouvir.py

import time
import sounddevice as sd
import numpy as np
from faster_whisper import WhisperModel
from pynput import keyboard
import modelos.cores as cor




"""
MÓDULO DE OUVIR DA LUNA (STT)
---------------------------------------------------------
Captura a fala do usuário e transcreve para texto usando Faster-Whisper.
Modelo: "small", CPU, int8 — leve e rápido o suficiente para uso contínuo.

PTT (Push-to-Talk): Ctrl+Alt+F8
  Segure a combinação para gravar, solte para transcrever e enviar.
  Áudios com menos de 0.6s são descartados (evita falsos gatilhos).
  Alucinações conhecidas do Whisper (créditos de vídeo, inscreva-se, etc.)
  são filtradas automaticamente antes de retornar.

Funções principais:
  escutar_usuario() — abre o stream de áudio, aguarda o PTT, transcreve e retorna o texto.
"""




modelo_whisper = WhisperModel("small", device="cpu", compute_type="int8")



TECLA_PTT = {keyboard.Key.ctrl_l, keyboard.Key.alt_l, keyboard.Key.f8}

def escutar_usuario():
    taxa_amostragem = 16000
    audio_frames = []
    gravando = False
    segurando = False
    _teclas_pressionadas = set()

    def callback_audio(indata, frames, time_info, status):
        if gravando:
            audio_frames.append(indata.copy())

    def on_press(key):
        nonlocal gravando, segurando
        _teclas_pressionadas.add(key)
        if TECLA_PTT.issubset(_teclas_pressionadas) and not segurando:
            segurando = True
            gravando = True
            cor.verde("\n[🎙️ Gravando... Solte para ENVIAR]")
            try:
                import servidor as _srv
                _srv.atualizar_status_mic("gravando")
            except Exception:
                pass

    def on_release(key):
        nonlocal gravando, segurando
        _teclas_pressionadas.discard(key)
        if not TECLA_PTT.issubset(_teclas_pressionadas) and segurando:
            gravando = False
            segurando = False
            return False


    cor.cinza(f"\n===========================================")
    cor.verde("[🌑 Aguardando... Segure Ctrl+Alt+F8 para falar]")
    try:
        import servidor as _srv
        _srv.atualizar_status_mic("aguardando")
    except Exception:
        pass


    stream = sd.InputStream(samplerate=taxa_amostragem, channels=1, dtype='float32', callback=callback_audio)
    stream.start()

    with keyboard.Listener(on_press=on_press, on_release=on_release) as listener:
        listener.join()

    gravando = False
    stream.stop()
    stream.close()

    if len(audio_frames) == 0:
        return ""

    cor.verde("[Processando áudio...]")
    try:
        import servidor as _srv
        _srv.atualizar_status_mic("processando")
    except Exception:
        pass
    audio_completo = np.concatenate(audio_frames, axis=0)
    audio_1d = np.squeeze(audio_completo)

    # Ignorar áudios muito curtos (< 0.6s) — evita false triggers do PTT
    duracao_segundos = len(audio_1d) / taxa_amostragem
    if duracao_segundos < 0.6:
        return ""

    try:
        segmentos, _ = modelo_whisper.transcribe(audio_1d, language="pt", beam_size=5)
        texto_final = "".join([segmento.text for segmento in segmentos]).strip()

        # Filtrar alucinações conhecidas do Whisper (áudio ambiente, silêncio, vídeos)
        _ALUCINACOES_WHISPER = {
            "amara.org", "legendas pela comunidade", "transcrições por",
            "subtitles by", "subtitle by", "legendado por", "traduzido por",
            "obrigado por assistir", "inscreva-se no canal",
        }
        texto_lower = texto_final.lower()
        if any(a in texto_lower for a in _ALUCINACOES_WHISPER):
            cor.cinza(f"[🔇 Alucinação Whisper descartada: '{texto_final[:60]}']")
            return ""

        return texto_final
    except Exception as e:
        cor.vermelho(f"Erro na transcrição: {e}")
        return ""