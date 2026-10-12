"""Catálogo do Kokoro-82M compartilhado entre a síntese e a interface, sem carregar TTS.

Fonte: https://huggingface.co/hexgrad/Kokoro-82M/blob/main/VOICES.md
Os idiomas identificam o timbre de origem; a Luna usa o pipeline PT-BR para todos.
"""

VOZ_PADRAO = "jf_alpha"

_GRUPOS = (
    ("Português (Brasil)", "pf_dora pm_alex pm_santa"),
    ("Inglês (EUA)", "af_heart af_alloy af_aoede af_bella af_jessica af_kore af_nicole "
     "af_nova af_river af_sarah af_sky am_adam am_echo am_eric am_fenrir am_liam "
     "am_michael am_onyx am_puck am_santa"),
    ("Inglês (Reino Unido)", "bf_alice bf_emma bf_isabella bf_lily bm_daniel bm_fable bm_george bm_lewis"),
    ("Espanhol", "ef_dora em_alex em_santa"),
    ("Francês", "ff_siwis"),
    ("Italiano", "if_sara im_nicola"),
    ("Japonês", "jf_alpha jf_gongitsune jf_nezumi jf_tebukuro jm_kumo"),
    ("Hindi", "hf_alpha hf_beta hm_omega hm_psi"),
    ("Mandarim", "zf_xiaobei zf_xiaoni zf_xiaoxiao zf_xiaoyi zm_yunjian zm_yunxi zm_yunxia zm_yunyang"),
)

VOZES_VALIDAS = frozenset(voz for _, vozes in _GRUPOS for voz in vozes.split())


def normalizar_favoritas(valores):
    if not isinstance(valores, list):
        return []
    return list(dict.fromkeys(voz for voz in valores if isinstance(voz, str) and voz in VOZES_VALIDAS))


def vozes_para_web():
    # Uma única lista evita oferecer um timbre na web que a síntese rejeita silenciosamente.
    return [
        {"idioma": idioma, "vozes": [
            {"id": voz, "nome": voz.split("_", 1)[1].title(),
             "genero": "feminina" if voz[1] == "f" else "masculina"}
            for voz in vozes.split()
        ]}
        for idioma, vozes in _GRUPOS
    ]
