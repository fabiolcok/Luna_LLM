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


def imagem_promocao(nome):
    """Reaproveita a foto do Obsidian sem expor caminhos locais no histórico web."""
    if isinstance(nome, str) and re.fullmatch(r"[\w-]{1,100}\.jpg", nome, re.ASCII):
        return "/imagens/promocoes/" + nome
    return ""


def _imagem_promocao(valor):
    if isinstance(valor, str) and valor.startswith("/imagens/promocoes/"):
        return imagem_promocao(valor.removeprefix("/imagens/promocoes/"))
    return _url(valor)


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
        if tipo in ("noticia", "promocao"):
            if tipo == "noticia" and not url:
                continue
            mais = item.get("mais", 0)
            imagem = _imagem_promocao(item.get("imagem")) if tipo == "promocao" else _url(item.get("imagem"))
            base.update(url=url, fonte=_texto(item.get("fonte"), 80), imagem=imagem,
                        mais=min(max(mais, 0), 1000) if type(mais) is int else 0)
            if item.get('resumo'):
                base['resumo'] = _texto(item.get('resumo'), 800)
            if tipo == "noticia":
                from modulos.novidades_web import normalizar_sugestoes
                sugestoes = normalizar_sugestoes(item.get("sugestoes"))
                if sugestoes:
                    base.update(sugestoes=sugestoes, resumo=_texto(item.get("resumo"), 800))
        elif tipo == "agenda":
            from modulos.agenda_web import normalizar_eventos, data
            if not isinstance(item.get('eventos'), list):
                continue
            eventos = normalizar_eventos(item.get("eventos"))[:50]
            total = item.get("total")
            base.update(eventos=eventos, total=max(len(eventos), min(total, 10000)) if type(total) is int else len(eventos),
                        mais=item.get("mais") is True,
                        inicio_periodo=data(item.get("inicio_periodo")), fim_periodo=data(item.get("fim_periodo")))
        elif tipo == "proposta_fonte":
            from modulos.acompanhamento_fontes import validar_url
            identificador = _texto(item.get("id"), 80)
            fontes = item.get('fontes')
            if not re.fullmatch(r'[a-f0-9]{16}', identificador) or not isinstance(fontes, list) or not 1 <= len(fontes) <= 3:
                continue
            try:
                fontes = [validar_url(u) for u in fontes]
            except ValueError:
                continue
            base.update(id=identificador, interesse=_texto(item.get('interesse'), 400),
                        situacao=_texto(item.get('situacao'), 300), fontes=fontes)
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


class TextoComCartoes(str):
    def __new__(cls, texto, cartoes):
        obj = super().__new__(cls, texto)
        obj.cartoes_web = normalizar(cartoes)
        return obj


def anexar(texto, origem):
    cartoes = getattr(origem, 'cartoes_web', None)
    return TextoComCartoes(texto, cartoes) if cartoes else texto


def noticia(titulo, fonte, url, mais=0, imagem="", *, resumo="", sugestoes=None):
    return {"tipo": "noticia", "titulo": titulo, "fonte": fonte, "url": url, "mais": mais,
            "imagem": imagem, "resumo": resumo, "sugestoes": sugestoes or []}


def promocao(titulo, fonte, url, mais=0, imagem=""):
    return {"tipo": "promocao", "titulo": titulo, "fonte": fonte, "url": url, "mais": mais,
            "imagem": imagem}


def acompanhamento(origem, estado, novidade=None):
    novidade = novidade or {}
    return {"tipo": "acompanhamento", "origem": origem, "id": estado.get("id", ""),
            "titulo": estado.get("assunto") or estado.get("titulo", ""),
            "situacao": estado.get("situacao", ""), "proximo_passo": estado.get("proximo_passo", ""),
            "url": novidade.get("url", ""), "fonte": novidade.get("fonte", ""),
            "trecho": novidade.get("evidencia") or novidade.get("trecho", ""),
            "etapa": novidade.get("etapa") or novidade.get("tipo", "")}
