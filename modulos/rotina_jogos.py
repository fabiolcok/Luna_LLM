"""Memória estruturada de sessões; registra fatos sem pedir interpretação à LLM."""

import datetime
import json
import os
import threading


CAMINHO_ESTADO = os.path.join("modelos", "rotina_jogos.json")
_LOCK = threading.RLock()
_MARCOS_SESSAO = {3, 5, 10}


def _agora() -> datetime.datetime:
    return datetime.datetime.now().astimezone()


def _vazio() -> dict:
    return {"versao": 1, "jogos": {}, "ultimo_jogo": None}


def _carregar() -> dict:
    try:
        with open(CAMINHO_ESTADO, encoding="utf-8") as arquivo:
            estado = json.load(arquivo)
        if not isinstance(estado.get("jogos"), dict):
            return _vazio()
        estado.setdefault("versao", 1)
        estado.setdefault("ultimo_jogo", None)
        return estado
    except (OSError, ValueError, TypeError):
        return _vazio()


def _salvar(estado: dict) -> None:
    try:
        pasta = os.path.dirname(CAMINHO_ESTADO)
        if pasta:
            os.makedirs(pasta, exist_ok=True)
        temporario = CAMINHO_ESTADO + ".tmp"
        with open(temporario, "w", encoding="utf-8") as arquivo:
            json.dump(estado, arquivo, ensure_ascii=False, indent=2)
        os.replace(temporario, CAMINHO_ESTADO)
    except OSError:
        pass


def _chave(appid, nome: str) -> str:
    return str(appid or nome).strip().lower()


def registrar_abertura(appid, nome: str, agora: datetime.datetime = None) -> dict:
    """Incrementa uma sessão observada e devolve apenas o contexto que merece virar fala."""
    agora = agora or _agora()
    chave = _chave(appid, nome)
    with _LOCK:
        estado = _carregar()
        jogo = estado["jogos"].setdefault(chave, {
            "appid": str(appid or ""), "nome": nome, "sessoes": 0,
            "minutos_observados": 0, "primeira_abertura": agora.isoformat(),
            "ultima_abertura": None, "ultima_sessao_min": None, "em_andamento": False,
        })
        anterior = jogo.get("ultima_abertura")
        jogo["nome"] = nome
        # Reiniciar a Luna durante o jogo faz a Steam parecer "aberta agora" outra vez.
        # Só tratamos como a mesma sessão se o registro ainda está aberto e é recente.
        mesma_sessao = False
        if jogo.get("em_andamento") and anterior:
            try:
                mesma_sessao = (agora - datetime.datetime.fromisoformat(anterior)).total_seconds() < 12 * 3600
            except (TypeError, ValueError):
                pass
        if not mesma_sessao:
            jogo["sessoes"] = int(jogo.get("sessoes", 0)) + 1
        jogo["ultima_abertura"] = agora.isoformat()
        jogo["em_andamento"] = True
        estado["ultimo_jogo"] = chave
        _salvar(estado)

        sessoes = jogo["sessoes"]
        marco = sessoes in _MARCOS_SESSAO or (sessoes > 10 and sessoes % 10 == 0)
        dias_ausente = None
        if anterior:
            try:
                dias_ausente = (agora - datetime.datetime.fromisoformat(anterior)).days
            except (TypeError, ValueError):
                pass
        return {
            "nome": nome,
            "sessoes": sessoes,
            "marco": marco and not mesma_sessao,
            "dias_ausente": dias_ausente,
            "mesma_sessao": mesma_sessao,
        }


def registrar_fechamento(appid, nome: str, duracao_min: int,
                          agora: datetime.datetime = None) -> None:
    """Consolida duração; abrir por engano ainda fica visível, mas não infla minutos."""
    agora = agora or _agora()
    chave = _chave(appid, nome)
    duracao_min = max(0, int(duracao_min or 0))
    with _LOCK:
        estado = _carregar()
        jogo = estado["jogos"].get(chave)
        if not jogo:
            return
        jogo["ultimo_fechamento"] = agora.isoformat()
        jogo["ultima_sessao_min"] = duracao_min
        jogo["em_andamento"] = False
        if duracao_min >= 2:
            jogo["minutos_observados"] = int(jogo.get("minutos_observados", 0)) + duracao_min
        _salvar(estado)


def contexto_abertura(registro: dict) -> str:
    """Bloco curto e factual; vazio significa que a rotina não deve disputar a fala."""
    if not registro or not registro.get("marco"):
        return ""
    n = int(registro["sessoes"])
    nome = registro.get("nome", "o jogo")
    return (f"FATO DE ROTINA CONFIRMADO: esta é a {n}ª vez que você abre {nome} desde que "
            "eu comecei a acompanhar as sessões.")
