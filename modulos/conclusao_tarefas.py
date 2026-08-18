"""Confirmação determinística antes de fechar uma checkbox no Obsidian."""

from __future__ import annotations

import datetime as dt
import json
import os
import re
import threading
import unicodedata
import uuid
from pathlib import Path

from modulos import config_env, obsidian


CAMINHO_ESTADO = Path("modelos/conclusao_tarefa.json")
_VAULT = config_env.texto("OBSIDIAN_VAULT")
_LOCK = threading.RLock()
_TTL_MIN = 15


def _norm(texto: str) -> str:
    sem_acento = unicodedata.normalize("NFKD", texto or "").encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", sem_acento.lower()).strip(" .,!?:;")


def _carregar() -> dict:
    try:
        dados = json.loads(CAMINHO_ESTADO.read_text(encoding="utf-8"))
        return dados if isinstance(dados, dict) else {"confirmacao": None}
    except (OSError, ValueError):
        return {"confirmacao": None}


def _salvar(estado: dict) -> None:
    CAMINHO_ESTADO.parent.mkdir(parents=True, exist_ok=True)
    temporario = CAMINHO_ESTADO.with_suffix(".tmp")
    temporario.write_text(json.dumps(estado, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(temporario, CAMINHO_ESTADO)


def _notificar() -> None:
    try:
        import servidor
        servidor.notificar_acompanhamentos()
    except Exception:
        pass


def _confirmacao_valida(estado: dict) -> dict | None:
    conf = estado.get("confirmacao")
    if not conf:
        return None
    try:
        expira = dt.datetime.fromisoformat(conf["expira_em"])
    except (KeyError, TypeError, ValueError):
        expira = dt.datetime.min
    if dt.datetime.now() >= expira:
        estado["confirmacao"] = None
        return None
    return conf


def estado_interface() -> dict:
    with _LOCK:
        estado = _carregar()
        antes = estado.get("confirmacao")
        conf = _confirmacao_valida(estado)
        if antes and not conf:
            _salvar(estado)
        return {"confirmacao": conf}


def propor(tarefa: str, nota: str = "", origem: str = "pc") -> str:
    # Um novo pedido explícito substitui a decisão anterior. Sem isso, uma busca sem
    # resultado deixaria um botão velho capaz de concluir outra tarefa por acidente.
    with _LOCK:
        estado_anterior = _carregar()
        tinha_anterior = bool(estado_anterior.get("confirmacao"))
        if tinha_anterior:
            _salvar({"confirmacao": None})
    candidatas = obsidian.encontrar_tarefas_abertas(tarefa, nota)
    if not candidatas:
        if tinha_anterior:
            _notificar()
        return f"Não encontrei uma tarefa aberta correspondente a ‘{tarefa}’."
    melhor_score = candidatas[0]["score"]
    melhores = [item for item in candidatas if item["score"] == melhor_score]
    if len(melhores) > 1:
        if tinha_anterior:
            _notificar()
        opcoes = "; ".join(f"‘{i['texto']}’ em {i['nota']}.md" for i in melhores[:4])
        return f"Encontrei mais de uma tarefa parecida: {opcoes}. Diga qual delas você quer concluir."

    item = melhores[0]
    agora = dt.datetime.now().replace(microsecond=0)
    conf = {
        "id": uuid.uuid4().hex[:12],
        "tipo": "concluir_tarefa",
        "tarefa": item["texto"],
        "nota": item["nota"],
        "caminho": item["caminho"],
        "linha": item["linha"],
        "original": item["original"],
        "origem": origem,
        "criado_em": agora.isoformat(),
        "expira_em": (agora + dt.timedelta(minutes=_TTL_MIN)).isoformat(),
    }
    with _LOCK:
        _salvar({"confirmacao": conf})
    _notificar()
    return (f"Encontrei ‘{item['texto']}’ em {item['nota']}.md. "
            "Confirmar como concluída?")


def _marcar(conf: dict) -> str:
    raiz = os.path.realpath(_VAULT)
    caminho = os.path.realpath(os.path.join(raiz, conf["caminho"]))
    try:
        if os.path.commonpath([raiz, caminho]) != raiz:
            return "Não alterei nada: o caminho da nota não é seguro."
    except ValueError:
        return "Não alterei nada: o caminho da nota não é seguro."
    try:
        with open(caminho, encoding="utf-8", newline="") as arquivo:
            linhas = arquivo.readlines()
    except OSError:
        return "Não consegui abrir a nota; nada foi alterado."

    original = conf["original"]
    indice = int(conf["linha"]) - 1
    candidatos = [i for i, linha in enumerate(linhas) if linha.rstrip("\r\n") == original]
    if 0 <= indice < len(linhas) and linhas[indice].rstrip("\r\n") == original:
        alvo = indice
    elif len(candidatos) == 1:
        alvo = candidatos[0]
    else:
        return "A nota mudou desde a confirmação; não alterei nada. Peça de novo."

    nova, trocas = re.subn(r'^(\s*[-*]\s*)\[\s*\]', r'\1[x]', linhas[alvo], count=1)
    if trocas != 1:
        return "A tarefa já não está aberta; não alterei nada."
    linhas[alvo] = nova
    temporario = caminho + ".luna.tmp"
    try:
        with open(temporario, "w", encoding="utf-8", newline="") as arquivo:
            arquivo.writelines(linhas)
        os.replace(temporario, caminho)
    except OSError:
        try:
            os.remove(temporario)
        except OSError:
            pass
        return "Não consegui salvar a nota; nada foi alterado."
    return f"Pronto, marquei ‘{conf['tarefa']}’ como concluída em {conf['nota']}.md."


def resolver(acao: str, identificador: str = "") -> str | None:
    acao = _norm(acao)
    with _LOCK:
        estado = _carregar()
        conf = _confirmacao_valida(estado)
        if not conf or (identificador and identificador != conf.get("id")):
            return None
        if acao in {"confirmar", "sim", "confirma", "pode marcar", "concluir"}:
            resposta = _marcar(conf)
        elif acao in {"cancelar", "nao", "cancela", "deixa", "deixa pra la"}:
            resposta = "Beleza, não alterei a tarefa."
        else:
            return None
        estado["confirmacao"] = None
        _salvar(estado)
    _notificar()
    return resposta


def interceptar_resposta(texto: str) -> str | None:
    conf = estado_interface().get("confirmacao")
    if not conf:
        return None
    normalizado = _norm(texto)
    if re.match(r"^(sim|confirma|confirmo|pode|pode marcar|marca|isso|conclui)\b", normalizado):
        return resolver("confirmar", conf["id"])
    if re.match(r"^(nao|cancela|cancelar|deixa|deixa pra la)\b", normalizado):
        return resolver("cancelar", conf["id"])
    return None
