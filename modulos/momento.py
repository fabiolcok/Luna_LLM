"""Fatos transitórios do momento. Sem LLM, disco, captura de tela ou consultas novas."""
from copy import deepcopy
import math
import re
import threading
import time

TTL_CONVERSA = 15 * 60
TTL_JOGOS = {"processos": 120, "steam": 240}
_lock = threading.RLock()
_jogos = {}


def texto_curto(valor, limite):
    texto = re.sub(r"\s+", " ", str(valor or "")).strip()
    return texto if len(texto) <= limite else texto[:limite - 1] + "…"


def idade(instante, agora):
    try:
        delta = agora - float(instante)
        return int(delta) if math.isfinite(delta) and delta >= 0 else None
    except (TypeError, ValueError, OverflowError):
        return None


def observar_jogos(fonte, nomes, agora=None):
    if fonte not in TTL_JOGOS:
        raise ValueError("Fonte de jogo desconhecida")
    agora = time.time() if agora is None else agora
    # A lista vazia também é observação: fechar o jogo invalida a detecção anterior.
    with _lock:
        _jogos[fonte] = {"instante": agora, "nomes": list(dict.fromkeys(
            texto_curto(n, 90) for n in nomes if n))[:4]}


def jogos_recentes(agora=None):
    agora = time.time() if agora is None else agora
    with _lock:
        fontes = deepcopy(_jogos)
    resultado = []
    for fonte, dado in fontes.items():
        segundos = idade(dado["instante"], agora)
        if segundos is not None and segundos <= TTL_JOGOS[fonte]:
            resultado.append({"fonte": fonte, "idade_s": segundos, "nomes": dado["nomes"]})
    return resultado


def conversa_recente(historico, agora=None):
    agora = time.time() if agora is None else agora
    recentes = []
    for mensagem in historico or []:
        segundos = idade(mensagem.get("instante"), agora)
        if (mensagem.get("origem") != "proativo" and mensagem.get("role") in ("user", "assistant")
                and segundos is not None and segundos <= TTL_CONVERSA):
            recentes.append(mensagem)
    return recentes


def titulo_janela(retorno):
    texto = str(retorno or "").strip()
    prefixo = "SISTEMA: O usuário está com a janela '"
    sufixo = "' em foco no momento."
    if texto.startswith(prefixo) and texto.endswith(sufixo):
        texto = texto[len(prefixo):-len(sufixo)]
    elif texto.startswith("SISTEMA:"):
        # Área de trabalho e falha da API não são títulos nem prova de presença.
        return ""
    return texto_curto(texto, 140)


def capturar(*, canal, janela="", historico=(), agora=None):
    agora = time.time() if agora is None else agora
    dados = {"canal": canal, "capturado_em": agora}
    if canal != "telegram":
        dados["janela"] = titulo_janela(janela)
        dados["jogos"] = jogos_recentes(agora)
        from modulos import dark_souls
        souls = dark_souls.contexto()
        if souls:
            # Sem isto, MOMENTO reintroduz no proativo a contagem retirada do briefing.
            partes = ([] if canal == "proativo" else
                      [f"{souls['mortes_sessao']} mortes acompanhadas nesta sessão"])
            for e in souls["eventos"][-2:]:
                fato = {"morte": "personagem morreu", "chefe": "chefe derrotado",
                        "fogueira": "fogueira liberada"}[e["tipo"]]
                partes.append(f"há {e['idade_s']}s: {fato}" + (f" — {e['nome']}" if e["nome"] else ""))
            if partes:
                dados["dark_souls"] = texto_curto("; ".join(partes), 320)
            if not any(souls["jogo"].casefold() == n.casefold()
                       for fonte in dados["jogos"] for n in fonte["nomes"]):
                dados["jogos"].insert(0, {"fonte": "leitor local", "idade_s": 0, "nomes": [souls["jogo"]]})
    recentes = conversa_recente(historico, agora)
    ultima = next((m for m in reversed(recentes) if m["role"] == "user"), None)
    if ultima:
        dados["fala_usuario"] = {"texto": texto_curto(ultima.get("content"), 240),
                                 "idade_s": idade(ultima["instante"], agora)}
    return dados


def jogo_unico(dados):
    nomes = list(dict.fromkeys(n for fonte in dados.get("jogos", []) for n in fonte["nomes"]))
    return nomes[0] if len(nomes) == 1 else ""
