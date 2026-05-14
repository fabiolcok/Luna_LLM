import numpy as np
import sounddevice as sd
from supertonic import TTS
import re
import modelos.cores as cor


""" 

MÓDULO DE FALA DA LUNA 
---------------------------------------------------------
Este arquivo contem todas as funcoes para que a luna pode transformar o texto em fala (TTS)

Atualmente estou usando o Supertonic

- limpar_acentos_para_motor(texto): tenta ajustar as palavras para a fhonetica correta (não vira naun)
- falar_texto(texto, voz="F1", velocidade=1.35, ao_iniciar=None, ao_terminar=None): o motor do tts


"""



# ==========================================
# Inicialização do Motor Supertonic
# ==========================================
try:
    # auto_download=True fará o download do modelo na primeira vez que rodar
    tts_motor = TTS(auto_download=True)
    
    # Se der algum erro nas bibliotecas da placa de vídeo (RX 9060 XT), 
    # você pode forçar a rodar no Ryzen 5 alterando a linha acima para:
    # tts_motor = TTS(auto_download=True, device="cpu")

    print("Motor Supertonic carregado com sucesso!")
except Exception as e:
    print(f"Erro ao inicializar o Supertonic: {e}")
    tts_motor = None



def limpar_acentos_para_motor(texto):
    # Regras fonéticas vitais (Apenas o que o modelo gringo realmente não entende)
    regras_foneticas = {
        r'ês\b': 'eis',    # Pega português, inglês, mês
        r'ç': 'ss',        # O clássico problema do Ç
        r'ão\b': 'aun',    # Pega qualquer final 'ão'
        r'ões\b': 'oins',  # Pega qualquer final 'ões' (configurações)
        r'õe\b': 'oin'     # Pega qualquer final 'õe' (compõe)
    }

    # Aplica as regras vitais
    for padrao, substituto in regras_foneticas.items():
        texto = re.sub(padrao, substituto, texto, flags=re.IGNORECASE)

    # 2. O EXTERMINADOR DE EMOJIS
    # Mantém apenas: letras (\w), espaços (\s) e pontuações normais.
    # Qualquer emoji como 🎮 ou 😎 será deletado do texto_limpo invisivelmente.
    texto = re.sub(r'[^\w\s.,?!:;\'"()-]', '', texto)

    return texto


# ==========================================
# Função Principal
# ==========================================
def falar_texto(texto, voz="F1", velocidade=1.05, ao_iniciar=None, ao_terminar=None):
    if not texto or not texto.strip():
        return

    try:
        # Passamos o texto pelo nosso filtro fonético
        #texto_limpo = limpar_acentos_para_motor(texto)
        texto_limpo = texto
        

        print("===================================")
        cor.ciano(f"[🌚💬 Luna falando...] '{texto}'")
        print("===================================")
        
        estilo_voz = tts_motor.get_voice_style(voice_name=voz)
        
        # Mandamos a versão "limpa" para o motor gerar o áudio
        wav, duration = tts_motor.synthesize(
            texto_limpo,
            voice_style=estilo_voz,
            total_steps = 20,
            lang="pt",
            speed=velocidade,
            silence_duration=0.5
        )

        # Achata a matriz do Supertonic para a placa de som entender
        wav_achatado = np.squeeze(wav)
        
        if ao_iniciar:
            ao_iniciar()

        # 5. Tocamos direto no alto-falante usando o 'wav_achatado'
        sd.play(wav_achatado, 44100)
        sd.wait()

        if ao_terminar:
            ao_terminar()

    except Exception as e:
        print(f"Erro ao gerar/tocar fala no Supertonic: {e}")
        if ao_terminar:
            ao_terminar()


def limpar_texto_para_voz(texto):
    """Remove markdown e formatações que atrapalham o TTS."""
    if not texto:
        return ""

    import re

    texto = re.sub(r'^\[[\w]+\]\s*', '', texto)

    if re.match(r'^\s*\{.*\}\s*$', texto, re.DOTALL):
        return ""

    texto = re.sub(r'\*+', '', texto)
    texto = re.sub(r'#+\s*', '', texto)
    texto = re.sub(r'`+', '', texto)
    texto = re.sub(r'_{1,2}(.*?)_{1,2}', r'\1', texto)
    texto = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', texto)

    texto = re.sub(r'^\s*[\*\-•]\s+', '', texto, flags=re.MULTILINE)
    texto = re.sub(r'^\s*\d+\.\s+', '', texto, flags=re.MULTILINE)

    texto = re.sub(r'\n{2,}', '\n', texto)
    texto = texto.strip()

    return texto