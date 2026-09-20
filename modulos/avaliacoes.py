"""Snapshots locais para avaliar a resposta escolhida, mesmo depois de outro turno."""
from collections import OrderedDict
from copy import deepcopy
from datetime import datetime
import hashlib
import json
from pathlib import Path
import threading
import uuid

from modulos.execucoes import controle

CATEGORIAS = {
    "perdeu_assunto", "inventou_informacao", "humor_bom", "humor_ruim",
    "repetitiva", "hora_ruim", "resposta_util", "tom_bom",
    "entendeu_contexto", "boa_iniciativa", "nao_ajudou", "tom_inadequado",
}
_lock = threading.RLock()
_turnos = OrderedDict()
_revisoes = {}
_LIMITE = 200
ARQUIVO = Path(__file__).resolve().parents[1] / "logs" / "avaliacoes.jsonl"


def _texto(valor, limite):
    return str(valor or "")[:limite]


def registrar_contexto(**dados):
    turno = controle.contexto.get()
    if turno is not None and controle.valida(turno):
        if not hasattr(turno, "diagnostico"):
            turno.diagnostico = {}
        turno.diagnostico.update(deepcopy(dados))


def registrar_chamada(modelo, parametros):
    turno = controle.contexto.get()
    if turno is None or not controle.valida(turno):
        return
    mensagens = parametros.get("messages", [])
    sistema = "\n".join(str(m.get("content", "")) for m in mensagens if m.get("role") == "system")
    diagnostico = deepcopy(getattr(turno, "diagnostico", {}))
    chamadas = diagnostico.get("chamadas", [])[-3:]
    chamadas.append({
        "modelo": _texto(modelo, 200),
        "prompt_sistema_chars": len(sistema),
        "prompt_sha256": hashlib.sha256(sistema.encode("utf-8")).hexdigest(),
        "max_tokens": parametros.get("max_tokens"),
        "stream": bool(parametros.get("stream")),
    })
    registrar_contexto(chamadas=chamadas)


def historico_curto(historico):
    return [{"role": m.get("role"), "content": _texto(m.get("content"), 700),
             **({"origem": m["origem"]} if m.get("origem") else {})}
            for m in historico[-4:] if m.get("role") in ("user", "assistant")]


def capturar_turno(turno, anteriores=(), canal="web"):
    identificador = uuid.uuid4().hex
    execucao = controle.contexto.get()
    contexto = deepcopy(getattr(execucao, "diagnostico", {})) if execucao else {}
    contexto["conversa_anterior"] = [
        {k: _texto(t.get(k), 700) for k in ("usuario", "luna", "origem_proativa")}
        for t in list(anteriores)[-3:]
    ]
    dados = {
        "turno_id": identificador, "canal": canal,
        "execucao_id": execucao.numero if execucao else None,
        "tempo_resposta": datetime.now().isoformat(timespec="seconds"),
        "usuario": str(turno.get("usuario") or ""), "luna": str(turno.get("luna") or ""),
        "origem_proativa": turno.get("origem_proativa", ""),
        "clima": turno.get("clima", ""), "contexto": contexto,
    }
    if turno.get("links_novidades"):
        dados["links"] = deepcopy(turno["links_novidades"])
    with _lock:
        _turnos[identificador] = dados
        while len(_turnos) > _LIMITE:
            antigo, _ = _turnos.popitem(last=False)
            _revisoes.pop(antigo, None)
    return identificador


def obter_turno(identificador):
    with _lock:
        return deepcopy(_turnos.get(identificador))


def salvar(registro):
    """Complementos são revisões do mesmo voto; o JSONL antigo nunca é reescrito."""
    with _lock:
        chave = registro.get("turno_id")
        anterior = _revisoes.get(chave) if chave else None
        novo = deepcopy(registro)
        if anterior and anterior.get("ferramenta") and not novo.get("ferramenta"):
            novo["ferramenta"] = deepcopy(anterior["ferramenta"])
        if anterior and all(anterior.get(k) == v for k, v in novo.items()):
            return deepcopy(anterior)
        novo["schema_version"] = 2
        novo["avaliacao_id"] = anterior["avaliacao_id"] if anterior else uuid.uuid4().hex
        novo["revisao"] = anterior["revisao"] + 1 if anterior else 1
        novo["tempo"] = datetime.now().isoformat(timespec="seconds")
        ARQUIVO.parent.mkdir(parents=True, exist_ok=True)
        with ARQUIVO.open("a", encoding="utf-8") as arquivo:
            arquivo.write(json.dumps(novo, ensure_ascii=False) + "\n")
        if chave:
            _revisoes[chave] = novo
        return novo


def ler_consolidadas(caminho=None):
    """Lê V1 e V2: um complemento de motivo não vira um segundo voto no relatório."""
    registros = OrderedDict()
    destino = Path(caminho) if caminho is not None else ARQUIVO
    if not destino.exists():
        return []
    with destino.open(encoding="utf-8") as arquivo:
        for numero, linha in enumerate(arquivo):
            try:
                item = json.loads(linha)
                if not isinstance(item, dict):
                    continue
                chave = item.get("avaliacao_id") or f"legado:{numero}"
                registros[chave] = item
            except json.JSONDecodeError:
                continue
    return list(registros.values())
