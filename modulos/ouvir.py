#ouvir.py

import time
import sounddevice as sd
import numpy as np
from faster_whisper import WhisperModel
from pynput import keyboard
import modelos.cores as cor




""" 

MÓDULO DE OUVIR DA LUNA 
---------------------------------------------------------
Este arquivo contem todas as funcoes para que a fala do usuario vire texto para a Luna ler. (STT)
Alem disso ele tem um leitor leve que tenta descobrir qual das 4 emoções o usuario esta no momento da fala.
Atualmente estou usando o faster_whisper

Funcoes principais:
- escutar_usuario(): faz tudo.

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

    def on_release(key):
        nonlocal gravando, segurando
        _teclas_pressionadas.discard(key)
        if not TECLA_PTT.issubset(_teclas_pressionadas) and segurando:
            gravando = False
            segurando = False
            return False


    cor.cinza(f"\n==================================================")
    cor.verde("[🌑 Aguardando... Segure F12 para falar]")


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
    audio_completo = np.concatenate(audio_frames, axis=0)
    audio_1d = np.squeeze(audio_completo)

    try:
        segmentos, _ = modelo_whisper.transcribe(audio_1d, language="pt", beam_size=5)
        texto_final = "".join([segmento.text for segmento in segmentos])
        return texto_final.strip()
    except Exception as e:
        cor.vermelho(f"Erro na transcrição: {e}")
        return ""