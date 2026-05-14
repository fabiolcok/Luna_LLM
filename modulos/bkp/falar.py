# falar.py

import sounddevice as sd
from misaki import espeak
from misaki.espeak import EspeakG2P
from kokoro_onnx import Kokoro
import modelos.cores as cor

CAMINHO_MODELO = "modelos/kokoro-v1.0.onnx"
CAMINHO_VOZES  = "modelos/voices-v1.0.bin"



PRONUNCIAS_EN = {
    "wifi": "uai fai",
    "steam": "istiin",
    "overwatch": "ôver uotch",
    "download": "daun lôudi",
    "update": "up deit",
    "build": "bilde",
    "fps": "éfe pê esse",
    "gpu": "gê pê u",
    "cpu": "cê pê u",
    "bot": "bôt",
    "login": "lôguin",
    "online": "on lain",
    "offline": "of lain",
    "stream": "istirim",
    "gameplay": "guêim plei",
    "patch": "petch",
    "rank": "rênk",
    "ranked": "rênkid",
    "steam deck": "istiim deki",
    "gg":"gê gê",
    "Youtube": "iu tube",
    "spotify" :"ispóti fay",
    "The Last of Us Part II Remastered" : "te Laste ofi Us Parte dois",
    " RAM" : "rram",
    "GTA VI": "GTA 6",
    "pendrive": "pen draive",
    "2GB": "2 GIGAS",
    "nvidia": "enivídia",
    
}

def _substituir_ingles(texto):
    import re
    for palavra, fonetica in PRONUNCIAS_EN.items():
        texto = re.sub(rf'\b{palavra}\b', fonetica, texto, flags=re.IGNORECASE)
    return texto


# ==========================================
# Preparação dos Motores
# ==========================================
fallback = espeak.EspeakFallback(british=False)
g2p = EspeakG2P(language="pt-br")

try:
    kokoro = Kokoro(CAMINHO_MODELO, CAMINHO_VOZES)
except Exception as e:
    cor.vermelho(f"Aviso: Não foi possível carregar o Kokoro. Erro: {e}")
    kokoro = None

VOZ_1 = "jf_alpha"   # Japa
VOZ_2 = "pf_dora"  # Brasil


# ==========================================
# Função Principal
# ==========================================


def falar_texto(texto, voz=VOZ_2, velocidade=1.0, ao_iniciar=None, ao_terminar=None):
    """
    Fala o texto gerado pelo Kokoro.

    Parâmetros:
        ao_iniciar  — callable chamado QUANDO o áudio começa a tocar (ex: mudar rosto p/ "falando")
        ao_terminar — callable chamado QUANDO o áudio termina      (ex: mudar rosto p/ "dormindo")
    """
    if not texto or not texto.strip():
        print("Aviso: Texto vazio. Pulando.")
        return

    if not kokoro:
        cor.vermelho("Erro: Kokoro não carregado.")
        return

    try:
        cor.ciano(f"[🌚💬 Luna falando...] '{texto}'")

        # Passo A: G2P — pode demorar alguns instantes
        texto = _substituir_ingles(texto)
        phonemes, _ = g2p(texto)

        # Passo B: Síntese — é aqui que o tempo passa antes de tocar
        audio, sample_rate = kokoro.create(
            phonemes,
            voice=voz,
            speed=velocidade,
            is_phonemes=True
        )

        # Passo C: Só AGORA avisa que vai começar a falar, depois toca
        if ao_iniciar:
            ao_iniciar()

        sd.play(audio, sample_rate)
        sd.wait()

        # Passo D: Avisou que terminou
        if ao_terminar:
            ao_terminar()

    except Exception as e:
        cor.vermelho(f"Erro ao gerar/tocar fala: {e}")
        if ao_terminar:
            ao_terminar()  # garante que o rosto não trava em "falando" se der erro