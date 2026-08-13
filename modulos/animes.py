"""Consulta compartilhada do AniList para o radar e para perguntas do usuário."""

import datetime
import time

import requests

from modulos import obsidian


JANELA_RECENTES_H = 72


def temporada_no_ar(nome):
    """Encontra a temporada em exibição e devolve id, título e próximo episódio."""
    query = (
        "query($busca: String) { Page(perPage: 8) {"
        " media(search: $busca, type: ANIME, sort: SEARCH_MATCH) {"
        " id title { romaji english } nextAiringEpisode { episode airingAt } } } }"
    )
    try:
        resposta = requests.post(
            "https://graphql.anilist.co",
            json={"query": query, "variables": {"busca": nome}}, timeout=10,
        )
        resposta.raise_for_status()
        medias = ((resposta.json().get("data") or {}).get("Page") or {}).get("media", [])
        media = next((item for item in medias if item.get("nextAiringEpisode")), None)
        if not media:
            return None
        titulo = media["title"].get("english") or media["title"]["romaji"]
        return media["id"], titulo, media.get("nextAiringEpisode")
    except (requests.RequestException, KeyError, TypeError, ValueError):
        # False distingue falha de rede/API de uma busca válida sem temporada no ar.
        return False


def ultimo_episodio(media_id):
    """Devolve número e horário do episódio mais recente que já foi exibido."""
    query = (
        "query($id: Int) { Page(perPage: 1) {"
        " airingSchedules(mediaId: $id, notYetAired: false, sort: TIME_DESC) {"
        " episode airingAt } } }"
    )
    try:
        resposta = requests.post(
            "https://graphql.anilist.co",
            json={"query": query, "variables": {"id": media_id}}, timeout=10,
        )
        resposta.raise_for_status()
        itens = ((resposta.json().get("data") or {}).get("Page") or {}).get("airingSchedules", [])
        if not itens:
            return None
        return itens[0]["episode"], itens[0]["airingAt"]
    except (requests.RequestException, KeyError, TypeError, ValueError):
        return False


def _horario(timestamp):
    return datetime.datetime.fromtimestamp(timestamp).astimezone().strftime("%d/%m/%Y às %H:%M")


def consultar(nome_anime=""):
    """Consulta episódios sem tocar no registro de avisos do proativo."""
    nome_anime = (nome_anime or "").strip()
    lista = [(nome_anime, "")] if nome_anime else obsidian.ler_lista_animes()[:10]
    if not lista:
        return "SISTEMA: A lista animes.md está vazia ou ainda não foi configurada."

    agora = time.time()
    resultados = []
    falhas = 0
    for nome, apelido in lista:
        temporada = temporada_no_ar(nome)
        if temporada is False:
            falhas += 1
            continue
        if temporada is None:
            continue
        media_id, titulo, proximo = temporada
        ultimo = ultimo_episodio(media_id)
        if ultimo is False:
            falhas += 1
            continue
        if ultimo is None:
            continue

        episodio, exibido_em = ultimo
        falado = apelido or titulo
        if not nome_anime and (exibido_em > agora or agora - exibido_em > JANELA_RECENTES_H * 3600):
            continue

        partes = [f"{falado}: episódio {episodio} saiu em {_horario(exibido_em)}"]
        if proximo and proximo.get("airingAt", 0) > agora:
            partes.append(f"próximo é o episódio {proximo['episode']} em {_horario(proximo['airingAt'])}")
        resultados.append("; ".join(partes) + ".")

    if resultados:
        escopo = f"Consulta do anime pedido ({nome_anime})" if nome_anime else "Episódios dos animes acompanhados que saíram nas últimas 72 horas"
        return f"SISTEMA: {escopo}:\n" + "\n".join(resultados)
    if falhas == len(lista):
        return "SISTEMA: Não consegui consultar o AniList agora."
    if falhas:
        return "SISTEMA: Nenhum episódio da sua lista saiu nas últimas 72 horas; parte da consulta ao AniList falhou."
    return "SISTEMA: Nenhum episódio da sua lista saiu nas últimas 72 horas."
