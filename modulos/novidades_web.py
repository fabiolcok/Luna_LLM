"""Sugestões de conversa sobre uma notícia, sem misturar botões com a voz."""
from contextvars import ContextVar
import json
import re


contexto_novidade = ContextVar("contexto_novidade", default=None)
_ABERTURA = re.compile(r"<sugestoes\s*>", re.IGNORECASE)
_BLOCO = re.compile(r"<sugestoes\s*>(.*?)</sugestoes\s*>", re.IGNORECASE | re.DOTALL)


def normalizar_sugestoes(valores):
    if not isinstance(valores, list):
        return []
    retorno, vistas = [], set()
    for valor in valores[:10]:
        if not isinstance(valor, str):
            continue
        pergunta = valor.strip()
        if (not 8 <= len(pergunta) <= 100 or not pergunta.endswith("?")
                or re.search(r"[<>\[\]\r\n\x00-\x1f]|https?://", pergunta, re.IGNORECASE)):
            continue
        chave = pergunta.casefold()
        if chave not in vistas:
            retorno.append(pergunta)
            vistas.add(chave)
        if len(retorno) == 3:
            break
    return retorno


def separar_sugestoes(texto):
    sugestoes = []
    bloco = _BLOCO.search(texto)
    if bloco:
        try:
            sugestoes = normalizar_sugestoes(json.loads(bloco.group(1)))
        except (ValueError, TypeError):
            pass
        texto = _BLOCO.sub("", texto)
    # Uma geração cortada ainda deve entregar o comentário, sem ler JSON no Kokoro.
    abertura = _ABERTURA.search(texto)
    if abertura:
        texto = texto[:abertura.start()]
    else:
        texto = previa_sem_sugestoes(texto)
    return texto.strip(), sugestoes


def previa_sem_sugestoes(texto):
    # Também esconde a abertura parcial quando a tag chega repartida pelo stream.
    abertura = _ABERTURA.search(texto)
    if abertura:
        return texto[:abertura.start()]
    marcador = "<sugestoes>"
    for tamanho in range(len(marcador) - 1, 0, -1):
        if texto.lower().endswith(marcador[:tamanho]):
            return texto[:-tamanho]
    return texto


class FalaComSugestoes(str):
    def __new__(cls, texto, sugestoes):
        fala = super().__new__(cls, texto)
        fala.sugestoes_novidade = normalizar_sugestoes(sugestoes)
        return fala


def resolver_continuacao(historico, referencia):
    """O clique referencia dados do servidor; o navegador não fornece uma notícia nova."""
    if not isinstance(referencia, dict):
        return None
    turno_id, indice = referencia.get("turno_id"), referencia.get("indice")
    if not isinstance(turno_id, str) or type(indice) is not int or not 0 <= indice < 3:
        return None
    from modulos.cartoes_web import normalizar
    turno = next((t for t in reversed(historico) if t.get("id") == turno_id), None)
    if not turno or turno.get("origem_proativa") != "radar_rss":
        return None
    noticia = next((c for c in normalizar(turno.get("cartoes_web")) if c["tipo"] == "noticia"), None)
    if not noticia or indice >= len(noticia.get("sugestoes", [])):
        return None
    return noticia["sugestoes"][indice], {k: noticia.get(k, "") for k in ("titulo", "fonte", "url", "resumo")}
