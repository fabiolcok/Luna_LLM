"""Dados de apresentação derivados das ferramentas, separados do texto da Luna."""
import re
from urllib.parse import urlsplit


def _texto(valor, limite):
    return valor.strip()[:limite] if isinstance(valor, str) else ""


def _url(valor):
    texto = _texto(valor, 2048)
    try:
        url = urlsplit(texto)
        return texto if url.scheme in {"http", "https"} and url.hostname and not re.search(r"\s", texto) else ""
    except ValueError:
        return ""


def normalizar(cartoes):
    """Restringe o histórico a tipos conhecidos; metadados nunca viram comandos livres."""
    if not isinstance(cartoes, list):
        return []
    retorno = []
    for item in cartoes[:3]:
        if not isinstance(item, dict):
            continue
        tipo = item.get("tipo")
        titulo = _texto(item.get("titulo"), 240)
        if not titulo:
            continue
        base = {"tipo": tipo, "titulo": titulo}
        url = _url(item.get("url"))
        if tipo == "noticia":
            if not url:
                continue
            mais = item.get("mais", 0)
            base.update(url=url, fonte=_texto(item.get("fonte"), 80), imagem=_url(item.get("imagem")),
                        mais=min(max(mais, 0), 1000) if type(mais) is int else 0)
        elif tipo == "acompanhamento":
            origem = item.get("origem")
            identificador = _texto(item.get("id"), 80)
            if not isinstance(origem, str) or origem not in {"sopro", "fontes", "conversa"} or not re.fullmatch(r"[\w-]{1,80}", identificador, re.ASCII):
                continue
            if origem == "sopro" and identificador != "sopro_ptbr":
                continue
            base.update(origem=origem, id=identificador, url=url,
                        situacao=_texto(item.get("situacao"), 300),
                        proximo_passo=_texto(item.get("proximo_passo"), 300),
                        fonte=_texto(item.get("fonte"), 80), trecho=_texto(item.get("trecho"), 500))
            etapa = item.get("etapa")
            base["etapa"] = etapa if isinstance(etapa, str) and etapa in {"plano", "anuncio", "mencao"} else ""
        else:
            continue
        retorno.append(base)
    return retorno


def noticia(titulo, fonte, url, mais=0, imagem=""):
    return {"tipo": "noticia", "titulo": titulo, "fonte": fonte, "url": url, "mais": mais,
            "imagem": imagem}


def acompanhamento(origem, estado, novidade=None):
    novidade = novidade or {}
    return {"tipo": "acompanhamento", "origem": origem, "id": estado.get("id", ""),
            "titulo": estado.get("assunto") or estado.get("titulo", ""),
            "situacao": estado.get("situacao", ""), "proximo_passo": estado.get("proximo_passo", ""),
            "url": novidade.get("url", ""), "fonte": novidade.get("fonte", ""),
            "trecho": novidade.get("evidencia") or novidade.get("trecho", ""),
            "etapa": novidade.get("etapa") or novidade.get("tipo", "")}
