"""Detecta copia textual entre falas; nao julga humor ou equivalencia semantica."""
from difflib import SequenceMatcher
import re
import unicodedata


def _palavras(texto):
    texto = re.sub(r"\[clima:[^\]]+\]", "", str(texto), flags=re.I)
    texto = unicodedata.normalize("NFKD", texto.casefold())
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return re.findall(r"[^\W_]+", texto)


def repete_fala(texto, anteriores):
    atual = _palavras(texto)
    if not atual:
        return False
    for anterior in anteriores:
        previa = _palavras(anterior)
        if not previa:
            continue
        if atual == previa:
            return True
        if min(len(atual), len(previa)) < 8:
            continue
        # Uma abertura inteira, trecho longo no meio ou quase toda a fala
        # merecem nova tentativa; uma saudacao curta em comum, nao.
        comparador = SequenceMatcher(None, atual, previa, autojunk=False)
        cobertura = sum(bloco.size for bloco in comparador.get_matching_blocks()) / min(len(atual), len(previa))
        if (atual[:8] == previa[:8]
                or comparador.find_longest_match().size >= 12
                or comparador.ratio() >= 0.72
                or (min(len(atual), len(previa)) >= 12 and cobertura >= 0.85)):
            return True
    return False
