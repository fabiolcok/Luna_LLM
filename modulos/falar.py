import logging
import re
import datetime
import numpy as np
import sounddevice as sd
from supertonic import TTS
import modelos.cores as cor

_log = logging.getLogger("luna.falar")


def periodo_atual():
    """Retorna (nome, descrição de tom para a persona, fator) conforme a hora.
    O tom (índice 1) é injetado no prompt da persona. O fator de velocidade NÃO é mais
    aplicado — baixar a velocidade fazia o Supertonic 'comer palavras'. Mantido só por compat."""
    h = datetime.datetime.now().hour
    if 0 <= h < 6:
        return ("madrugada", "Agora é MADRUGADA (se for cumprimentar, use 'boa noite'): fale bem tranquila e baixo, frases curtas.", 0.88)
    if 6 <= h < 12:
        return ("manhã", "Agora é MANHÃ (cumprimento correto: 'bom dia'): tom disposto e animado.", 1.0)
    if 12 <= h < 18:
        return ("tarde", "Agora é TARDE (cumprimento correto: 'boa tarde'): tom normal e leve.", 1.0)
    return ("noite", "Agora é NOITE (cumprimento correto: 'boa noite'): tom mais calmo e relaxado, sem empolgação.", 0.95)


"""
MÓDULO DE FALA DA LUNA (TTS)
---------------------------------------------------------
Transforma texto em fala usando o Supertonic v1.2.1 (PT-BR, voz F1, velocidade 1.2x).
Roda localmente via sounddevice — sem API externa.

Funções principais:
  falar_texto(texto, voz, velocidade, ao_iniciar, ao_terminar)
      Motor TTS principal. Chama limpar_texto_para_voz antes de sintetizar.
      Callbacks ao_iniciar/ao_terminar permitem controle externo (ex: mute mic).

  limpar_texto_para_voz(texto)
      Remove markdown, tokens de modelo, artefatos de tool result e alucinações
      de training data antes de mandar para o TTS. Preserva '...', '!!!' e '??'
      que o Supertonic usa para pausas e ênfase dramática.
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


_voz_padrao = "F1"
_velocidade_padrao = 1.2

def configurar_voz(voz=None, velocidade=None):
    global _voz_padrao, _velocidade_padrao
    if voz is not None:
        _voz_padrao = str(voz)
    if velocidade is not None:
        _velocidade_padrao = float(velocidade)


def _enfase_pontuacao(texto):
    """Ênfase só na FALA: '!' e '?' (1 ou 2) viram '!!!' e '???' — o Supertonic só
    muda a entonação com pontuação tripla. Não toca no que já é triplo. Aplicada
    apenas no áudio (dentro de falar_texto), então NÃO altera o texto exibido."""
    import re
    texto = re.sub(r'(?<![!?])!{1,2}(?![!?])', '!!!', texto)
    texto = re.sub(r'(?<![!?])\?{1,2}(?![!?])', '???', texto)
    return texto


# Dicionário de pronúncia: palavras que o Supertonic lê ERRADO -> grafia que ele ACERTA.
# Aplicado SÓ no áudio (como o _enfase_pontuacao), então NÃO altera o texto exibido/logado:
# a Luna continua ESCREVENDO certo ("Poxa") e só PRONUNCIA melhor ("Pôxa").
# Cresce conforme o Fábio for achando palavras mal ditas (via avaliação).
_PRONUNCIA = {
    "poxa": "pôxa",   # sem o acento o Supertonic diz "pocsa" (lê o x como /ks/)
}
_RE_PRONUNCIA = re.compile(r'\b(' + '|'.join(map(re.escape, _PRONUNCIA)) + r')\b', re.IGNORECASE)

def _corrigir_pronuncia(texto):
    """Troca palavras mal pronunciadas pela grafia que o Supertonic acerta.
    Preserva a inicial maiúscula. Só no áudio — o texto exibido fica igual."""
    def _sub(m):
        orig = m.group(0)
        novo = _PRONUNCIA[orig.lower()]
        return novo[:1].upper() + novo[1:] if orig[:1].isupper() else novo
    return _RE_PRONUNCIA.sub(_sub, texto)


# ==========================================
# Função Principal
# ==========================================
def falar_texto(texto, voz=None, velocidade=None, ao_iniciar=None, ao_terminar=None):
    if not texto or not texto.strip():
        return

    voz_usada = voz if voz is not None else _voz_padrao
    velocidade_usada = velocidade if velocidade is not None else _velocidade_padrao

    try:
        texto_limpo = limpar_texto_para_voz(texto)
        if not texto_limpo.strip():
            return

        print("===================================")
        cor.ciano(f"[🌚💬 Luna falando ] '{texto_limpo}'")
        print("===================================")

        # Ênfase + correção de pronúncia, SÓ no ÁUDIO (o texto exibido/log fica original).
        texto_falar = _enfase_pontuacao(texto_limpo)
        texto_falar = _corrigir_pronuncia(texto_falar)
        estilo_voz = tts_motor.get_voice_style(voice_name=voz_usada)

        wav, duration = tts_motor.synthesize(
            texto_falar,
            voice_style=estilo_voz,
            total_steps=15,
            lang="pt",
            speed=velocidade_usada,
            silence_duration=0.5
        )

        wav_achatado = np.squeeze(wav)

        if ao_iniciar:
            ao_iniciar()

        sd.play(wav_achatado, tts_motor.sample_rate)
        sd.wait()

        if ao_terminar:
            ao_terminar()

    except Exception as e:
        print(f"Erro ao gerar/tocar fala no Supertonic: {e}")
        _log.exception(f"Erro no TTS Supertonic ao falar '{texto[:80]}': {e}")
        if ao_terminar:
            ao_terminar()


def limpar_texto_para_voz(texto):
    """Remove markdown e formatações que atrapalham o TTS."""
    if not texto:
        return ""

    import re

    texto = re.sub(r'(?i)^SISTEMA:.*$', '', texto, flags=re.MULTILINE).strip()
    # Remove blocos de aviso do sistema que não devem ser lidos (ex: [AVISO DE SISTEMA...]: texto)
    texto = re.sub(r'\[AVISO DE SISTEMA[^\]]*\][^\n]*', '', texto, flags=re.IGNORECASE)
    texto = re.sub(r'^\[[\w]+\]\s*', '', texto)
    # Remove linhas que o modelo alucina como resultado de ferramenta
    texto = re.sub(r'(?i)^A ferramenta\b.*$', '', texto, flags=re.MULTILINE).strip()
    texto = re.sub(r'(?i)^Resultado\b.*:.*$', '', texto, flags=re.MULTILINE).strip()
    # Remove descrições brutas do Gemini (ver_tela) que o modelo ecoa na resposta
    texto = re.sub(r'(?i)^\[?(?:capturando tela|tela mostra|a tela (?:mostra|exibe|apresenta)).*$', '', texto, flags=re.MULTILINE).strip()
    texto = re.sub(r'\[[^\]]{50,}\]', '', texto)  # Remove blocos longos entre colchetes
    # Remove tokens de modelos fine-tuned (<|im_end|> etc). NÃO afeta expression tags do Supertonic
    # (<breath>, <sigh>, <throatclear>, ...) — esses são processados pelo ONNX e devem passar intactos.
    texto = re.sub(r'<\|[^|>]*\|+>?', '', texto)
    # Remove aspas duplas que envolvem o texto inteiro (artefato do completion-style)
    texto = re.sub(r'^"(.*)"$', r'\1', texto, flags=re.DOTALL)
    # Remove artifacts de modelos fine-tuned (Dolphin etc) que simulam blocos de tool result
    texto = re.sub(r'^\+{3,}.*$', '', texto, flags=re.MULTILINE)
    texto = re.sub(r'\[TOOL_RESULT\].*?(\[ENDTOOLRESULT\]|$)', '', texto, flags=re.DOTALL)
    # Remove código Python alucinado do training data (ex: Dolphin injetando exemplos de código)
    texto = re.sub(r'^(?:from \S+ import|import \S+|def \w+\s*\(|class \w+[\s:(]).*$', '', texto, flags=re.MULTILINE)
    texto = re.sub(r'^\s{4,}\S.*$', '', texto, flags=re.MULTILINE)  # linhas indentadas (corpo de função)
    texto = re.sub(r'^\w[\w.]* = \w[\w.]*\.(?:from_pretrained|generate|encode|decode|from_config)\(.*$', '', texto, flags=re.MULTILINE)
    # Remove texto em inglês que é training data (linhas que começam com artigos/pronomes ingleses + contexto de AI/tech)
    texto = re.sub(r'^(?:The |An |A )(?:\w+ ){0,3}(?:AI|artificial|machine|neural|model|generator|system|assistant)\b.*$', '', texto, flags=re.MULTILINE | re.IGNORECASE)
    # Remove linhas que a persona gera simulando resultado de ferramenta (ex: "Tocando agora: X")
    texto = re.sub(r'(?i)^(?:tocando agora|playing now|now playing|reproduzindo agora)\s*:.*$', '', texto, flags=re.MULTILINE)
    # Remove ponto antes de ! ou ? múltiplos (ex: "recursos.!!!" → "recursos...")
    texto = re.sub(r'\.([!?]{2,})', r'...\1', texto)
    # Normaliza mistura de ! e ? (ex: !!?? ou ?!?! → escolhe o predominante)
    texto = re.sub(r'[!?]*[!][!?]*[?][!?]*|[!?]*[?][!?]*[!][!?]*', lambda m: '!!' if m.group().count('!') >= m.group().count('?') else '??', texto)
    # Remove ... no início de linha nova (cria pausa dupla estranha)
    texto = re.sub(r'\n\s*\.\.\.', ' ', texto)
    # Remove ... sozinho no final do texto
    texto = re.sub(r'\s*\.\.\.\s*$', '', texto)

    if re.match(r'^\s*\{.*\}\s*$', texto, re.DOTALL):
        return ""

    texto = re.sub(r'\*+', '', texto)
    texto = re.sub(r'#+\s*', '', texto)
    texto = re.sub(r'`+', '', texto)
    texto = re.sub(r'_{1,2}(.*?)_{1,2}', r'\1', texto)
    texto = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', texto)

    texto = re.sub(r'^\s*[\*\-•]\s+', '', texto, flags=re.MULTILINE)
    texto = re.sub(r'^\s*\d+\.\s+', '', texto, flags=re.MULTILINE)
    texto = re.sub(r'^\s*-{3,}\s*$', '', texto, flags=re.MULTILINE)  # Remove --- horizontal rule

    # Números/símbolos que o Supertonic lê mal (ex: "51.95%" -> "51 vírgula 95 por cento")
    texto = re.sub(r'(\d+)[.,](\d+)\s*%', r'\1 vírgula \2 por cento', texto)
    texto = re.sub(r'(\d+)\s*%', r'\1 por cento', texto)
    texto = re.sub(r'(?<=\d)\.(?=\d)', ' vírgula ', texto)   # decimal solto: 3.5 -> 3 vírgula 5

    # Remove emojis e pictogramas (o TTS engasga neles). Tags <sigh>/<laugh> são ASCII e sobrevivem.
    texto = re.sub(
        "["
        "\U0001F300-\U0001FAFF"   # símbolos, emoticons, pictogramas estendidos
        "\U00002600-\U000027BF"   # símbolos diversos e dingbats
        "\U0001F1E6-\U0001F1FF"   # bandeiras
        "\U0000FE00-\U0000FE0F"   # seletores de variação
        "\U00002190-\U000021FF"   # setas
        "\U00002B00-\U00002BFF"   # símbolos e setas diversos
        "]+",
        "",
        texto,
    )
    texto = re.sub(r'[ \t]{2,}', ' ', texto)   # colapsa espaços deixados pelos emojis

    texto = re.sub(r'\n{2,}', '\n', texto)
    texto = texto.strip()

    return texto