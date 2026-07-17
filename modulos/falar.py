import json
import logging
import os
import re
import datetime
import numpy as np
import sounddevice as sd
import modelos.cores as cor

_log = logging.getLogger("luna.falar")


def periodo_atual():
    """Retorna (nome, descrição de tom para a persona, fator) conforme a hora.
    O tom (índice 1) é injetado no prompt da persona. O fator de velocidade é só
    informativo/compat — a velocidade real vem da config."""
    h = datetime.datetime.now().hour
    if 0 <= h < 6:
        return ("madrugada", "Agora é MADRUGADA (se for cumprimentar, use 'boa noite'): fale bem tranquila e baixo, frases curtas.", 0.88)
    if 6 <= h < 12:
        return ("manhã", "Agora é MANHÃ: tom disposto e animado. SÓ SE for cumprimentar, a saudação certa é 'bom dia'.", 1.0)
    if 12 <= h < 18:
        return ("tarde", "Agora é TARDE: tom normal e leve. SÓ SE for cumprimentar, a saudação certa é 'boa tarde'.", 1.0)
    return ("noite", "Agora é NOITE: tom mais calmo e relaxado, sem empolgação. SÓ SE for cumprimentar, a saudação certa é 'boa noite'.", 0.95)


"""
MÓDULO DE FALA DA LUNA (TTS)
---------------------------------------------------------
Transforma texto em fala usando o Kokoro-82M (pt-BR, lang_code='p'), rodando
localmente na CPU via sounddevice — sem API externa.

Por que Kokoro: prosódia natural de ? e ! (entonação de pergunta/exclamação),
qualidade boa e leve na CPU (RTF ~0.3). O Supertonic ficou como plano B
arquivado (ver G:\\Projetos\\TTS_teste), pra retomar fácil se sair um v4.

Vozes disponíveis (timbre; a pronúncia é sempre pt-BR):
  jf_alpha  — feminina (japonesa lendo pt-BR, com charme de sotaque) [padrão]
  af_bella  — feminina (americana)
  af_nicole — feminina (americana, tom mais sussurrado)

Funções principais:
  falar_texto(texto, voz, velocidade, ao_iniciar, ao_terminar)
      Motor TTS principal. Limpa o texto, corrige pronúncia e sintetiza.
  limpar_texto_para_voz(texto)
      Remove markdown, tokens de modelo, tags de voz e artefatos antes do TTS.
  configurar_voz(voz, velocidade)
      Troca a voz/velocidade padrão (usado pela config do web).
  repetir_ultima_fala()
      Toca de novo o último áudio (botão ▶️ do web), sem re-sintetizar.
"""


# ==========================================
# Vozes e padrões
# ==========================================
SAMPLE_RATE = 24000                       # Kokoro sempre gera a 24 kHz
_VOZES_VALIDAS = {"jf_alpha", "af_bella", "af_nicole"}
_VOZ_FALLBACK  = "jf_alpha"

_voz_padrao = "jf_alpha"
_velocidade_padrao = 0.9
_ultima_fala_wav = None   # último áudio gerado — pro botão "repetir" do web


# ==========================================
# Inicialização do Motor Kokoro (pt-BR)
# ==========================================
try:
    # O pt-BR converte texto->fonemas via espeak-ng, que vem embutido no pacote
    # espeakng-loader (nada pra instalar no Windows).
    import espeakng_loader
    from phonemizer.backend.espeak.wrapper import EspeakWrapper
    EspeakWrapper.set_library(espeakng_loader.get_library_path())
    try:
        EspeakWrapper.set_data_path(espeakng_loader.get_data_path())
    except Exception:
        pass

    from kokoro import KPipeline
    _pipe = KPipeline(lang_code='p')      # 'p' = português do Brasil
    print("Motor Kokoro (pt-BR) carregado com sucesso!")
except Exception as e:
    print(f"Erro ao inicializar o Kokoro: {e}")
    _pipe = None


def configurar_voz(voz=None, velocidade=None):
    """Troca voz/velocidade padrão. Voz inválida (ex: config antiga do Supertonic
    'F1'/'M1') cai no fallback jf_alpha, pra não quebrar."""
    global _voz_padrao, _velocidade_padrao
    if voz is not None:
        v = str(voz)
        if v not in _VOZES_VALIDAS:
            cor.amarelo(f"[voz '{v}' não é do Kokoro; usando {_VOZ_FALLBACK}]")
            v = _VOZ_FALLBACK
        _voz_padrao = v
    if velocidade is not None:
        _velocidade_padrao = float(velocidade)


# ==========================================
# Dicionário de pronúncia (modelos/pronuncia.json — editável pela config web)
# ==========================================
# Se o Kokoro falar uma palavra ERRADO, mapeia a grafia que ele ACERTA.
# Afeta SÓ o ÁUDIO — a Luna continua ESCREVENDO certo, só PRONUNCIA melhor.
# Preserva a inicial maiúscula automaticamente. Ex: {"hype": "raipe"}.
# Vive num JSON pra web editar e valer NA HORA, sem reiniciar a Luna.
_CAMINHO_PRONUNCIA = "modelos/pronuncia.json"
_PRONUNCIA = {}
_RE_PRONUNCIA = None

def _reconstruir_regex_pronuncia():
    global _RE_PRONUNCIA
    _RE_PRONUNCIA = (
        re.compile(r'\b(' + '|'.join(map(re.escape, _PRONUNCIA)) + r')\b', re.IGNORECASE)
        if _PRONUNCIA else None
    )

def _carregar_pronuncia():
    """Lê o JSON do disco (cria com o conteúdo padrão na 1ª vez)."""
    global _PRONUNCIA
    try:
        with open(_CAMINHO_PRONUNCIA, encoding="utf-8") as f:
            _PRONUNCIA = {str(k).lower(): str(v) for k, v in json.load(f).items()}
    except FileNotFoundError:
        _PRONUNCIA = {"hype": "raipe"}
        _salvar_pronuncia()
    except Exception as e:
        _log.warning(f"pronuncia.json inválido ({e}) — seguindo sem correções")
        _PRONUNCIA = {}
    _reconstruir_regex_pronuncia()

def _salvar_pronuncia():
    os.makedirs("modelos", exist_ok=True)
    with open(_CAMINHO_PRONUNCIA, "w", encoding="utf-8") as f:
        json.dump(_PRONUNCIA, f, ensure_ascii=False, indent=2)

def obter_pronuncia() -> dict:
    """Cópia do dicionário atual (pra config web listar)."""
    return dict(_PRONUNCIA)

def definir_pronuncia(palavra: str, grafia: str):
    """Adiciona/atualiza uma correção e aplica na hora (sem reiniciar)."""
    palavra, grafia = str(palavra).strip().lower(), str(grafia).strip()
    if not palavra or not grafia:
        return False
    _PRONUNCIA[palavra] = grafia
    _salvar_pronuncia()
    _reconstruir_regex_pronuncia()
    return True

def remover_pronuncia(palavra: str):
    """Remove uma correção e aplica na hora."""
    if _PRONUNCIA.pop(str(palavra).strip().lower(), None) is None:
        return False
    _salvar_pronuncia()
    _reconstruir_regex_pronuncia()
    return True

_carregar_pronuncia()

def _corrigir_pronuncia(texto):
    """Troca palavras mal pronunciadas pela grafia que o Kokoro acerta.
    Preserva a inicial maiúscula. Só no áudio — o texto exibido fica igual."""
    if not _RE_PRONUNCIA:
        return texto
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
    if _pipe is None:
        _log.warning("Kokoro indisponível; não há como falar.")
        if ao_terminar:
            ao_terminar()
        return

    voz_usada = voz if voz is not None else _voz_padrao
    if voz_usada not in _VOZES_VALIDAS:
        voz_usada = _VOZ_FALLBACK
    velocidade_usada = velocidade if velocidade is not None else _velocidade_padrao

    try:
        texto_limpo = limpar_texto_para_voz(texto)
        if not texto_limpo.strip():
            return

        print("===================================")
        cor.ciano(f"[🌚💬 Luna falando ] '{texto_limpo}'")
        print("===================================")

        # Correção de pronúncia SÓ no áudio (o texto exibido/log fica original).
        texto_falar = _corrigir_pronuncia(texto_limpo)

        partes = [a for _, _, a in _pipe(texto_falar, voice=voz_usada, speed=velocidade_usada)]
        if not partes:
            if ao_terminar:
                ao_terminar()
            return
        wav = np.concatenate([a if hasattr(a, 'shape') else a.numpy() for a in partes])
        wav_achatado = np.squeeze(wav)

        global _ultima_fala_wav
        _ultima_fala_wav = wav_achatado   # guarda pro botão "repetir" do web

        if ao_iniciar:
            ao_iniciar()

        sd.play(wav_achatado, SAMPLE_RATE)
        sd.wait()

        if ao_terminar:
            ao_terminar()

    except Exception as e:
        print(f"Erro ao gerar/tocar fala no Kokoro: {e}")
        _log.exception(f"Erro no TTS Kokoro ao falar '{texto[:80]}': {e}")
        if ao_terminar:
            ao_terminar()


def repetir_ultima_fala():
    """Toca de novo o último áudio que a Luna falou (botão 'repetir' do web).
    Reusa o WAV já gerado — não re-sintetiza. Retorna True se havia algo pra repetir."""
    if _ultima_fala_wav is None or _pipe is None:
        return False
    try:
        sd.stop()                                      # corta o que estiver tocando
        sd.play(_ultima_fala_wav, SAMPLE_RATE)
        return True
    except Exception as e:
        _log.exception(f"Erro ao repetir a fala: {e}")
        return False


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
    # Remove tokens de modelos fine-tuned (<|im_end|> etc).
    texto = re.sub(r'<\|[^|>]*\|+>?', '', texto)
    # Kokoro NÃO usa as tags de expressão do Supertonic (<laugh>, <sigh>, <breath>...):
    # remove pra não serem lidas em voz alta nem exibidas.
    texto = re.sub(r'</?(?:laugh|breath|sigh|surprise|scream|throatclear|sad|angry|cough|yawn)>', '', texto, flags=re.IGNORECASE)
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

    # Números/símbolos que o TTS lê mal (ex: "51.95%" -> "51 vírgula 95 por cento")
    texto = re.sub(r'(\d+)[.,](\d+)\s*%', r'\1 vírgula \2 por cento', texto)
    texto = re.sub(r'(\d+)\s*%', r'\1 por cento', texto)
    texto = re.sub(r'(?<=\d)\.(?=\d)', ' vírgula ', texto)   # decimal solto: 3.5 -> 3 vírgula 5

    # Remove emojis e pictogramas (o TTS engasga neles).
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
