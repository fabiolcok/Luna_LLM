"""Estado estruturado de projetos e conversas que ainda podem evoluir.

Não é agenda e não dispara proativo. Um assunto só entra no prompt quando a mensagem atual
casa com ele; assim a Luna lembra onde a história parou sem transformar tudo em cobrança.
"""

import datetime
import json
import os
import re
import unicodedata
import uuid
from pathlib import Path


CAMINHO = Path("modelos/assuntos_em_andamento.json")
_STATUS = {"aberto", "pausado", "concluido"}
_STOP = {
    "a", "o", "as", "os", "de", "da", "do", "das", "dos", "e", "em", "no", "na",
    "nos", "nas", "com", "para", "pra", "por", "um", "uma", "que", "meu", "minha",
    "seu", "sua", "esse", "essa", "isso", "ainda", "agora", "projeto", "ideia",
}
_GENERICAS = {"coisa", "fazer", "sistema", "aplicativo", "app", "servidor", "projeto"}


def _agora() -> str:
    return datetime.datetime.now().isoformat(timespec="minutes")


def _base() -> dict:
    return {"versao": 1, "assuntos": []}


def carregar() -> dict:
    try:
        with open(CAMINHO, encoding="utf-8") as arquivo:
            dados = json.load(arquivo)
        if not isinstance(dados, dict) or not isinstance(dados.get("assuntos"), list):
            return _base()
        return dados
    except Exception:
        return _base()


def _salvar(dados: dict) -> None:
    CAMINHO.parent.mkdir(parents=True, exist_ok=True)
    temporario = Path(str(CAMINHO) + ".tmp")
    with open(temporario, "w", encoding="utf-8") as arquivo:
        json.dump(dados, arquivo, ensure_ascii=False, indent=2)
    os.replace(temporario, CAMINHO)


def _norm(texto: str) -> str:
    texto = unicodedata.normalize("NFKD", str(texto or ""))
    texto = texto.encode("ascii", "ignore").decode().lower()
    return " ".join(re.sub(r"[^a-z0-9]+", " ", texto).split())


def _termos(texto: str) -> set:
    return {p for p in _norm(texto).split() if len(p) >= 3 and p not in _STOP}


def _pontuar(pergunta: str, item: dict) -> float:
    consulta = _termos(pergunta)
    corpo = _termos(" ".join((
        item.get("titulo", ""), item.get("estado_atual", ""),
        " ".join(h.get("texto", "") for h in item.get("historico", [])[-3:]),
    )))
    comuns = consulta & corpo
    if not comuns:
        return 0.0
    # Uma palavra genérica sozinha ("servidor", "projeto") não pode ressuscitar qualquer fio.
    if len(comuns) == 1:
        return 0.0 if next(iter(comuns)) in _GENERICAS else 0.67
    return len(comuns) / max(1, min(len(consulta), len(corpo)))


def listar() -> list:
    return sorted(carregar()["assuntos"], key=lambda i: i.get("atualizado_em", ""), reverse=True)


def resumo_para_extracao(limite: int = 12) -> str:
    """IDs reais para o classificador atualizar um fio sem adivinhar por regex."""
    # Concluídos também entram: se o usuário retomar um deles, o mesmo ID deve reabrir em vez
    # de nascer uma duplicata com outro nome.
    itens = listar()[:limite]
    if not itens:
        return "Nenhum assunto em andamento registrado."
    return "\n".join(
        f'- id={i["id"]} | título={i.get("titulo", "")} | '
        f'estado={i.get("estado_atual", "")} | status={i.get("status", "aberto")}'
        for i in itens
    )


def ids_existentes() -> set:
    return {str(i.get("id", "")) for i in carregar()["assuntos"] if i.get("id")}


def _achar_por_titulo(itens: list, titulo: str):
    termos = _termos(titulo)
    if not termos:
        return None
    melhor, nota = None, 0.0
    for item in itens:
        atuais = _termos(item.get("titulo", ""))
        comuns = termos & atuais
        if not comuns:
            continue
        atual = len(comuns) / max(1, min(len(termos), len(atuais)))
        if len(comuns) == 1 and next(iter(comuns)) in _GENERICAS:
            atual = 0.0
        if atual > nota:
            melhor, nota = item, atual
    return melhor if nota >= 0.67 else None


def registrar_candidato(item: dict, texto_editado: str = "") -> bool:
    """Cria ou atualiza o assunto escolhido na curadoria humana."""
    texto = str(texto_editado or item.get("fato", "")).strip()
    if not texto:
        return False
    dados = carregar()
    itens = dados["assuntos"]
    id_pedido = str(item.get("assunto_id") or "").strip()
    atual = next((i for i in itens if i.get("id") == id_pedido), None) if id_pedido else None
    titulo = str(item.get("assunto") or texto).strip()[:120]
    if atual is None:
        atual = _achar_por_titulo(itens, titulo)
    instante = _agora()
    status = str(item.get("status") or "aberto").strip().lower()
    if status not in _STATUS:
        status = "aberto"
    entrada = {
        "data": str(item.get("data") or datetime.date.today().isoformat()),
        "texto": texto,
        "evidencia": str(item.get("evidencia") or "")[:300],
    }
    if atual is None:
        atual = {
            "id": uuid.uuid4().hex[:12],
            "titulo": titulo,
            "estado_atual": texto,
            "status": status,
            "criado_em": instante,
            "atualizado_em": instante,
            "historico": [entrada],
        }
        itens.append(atual)
    else:
        atual["estado_atual"] = texto
        atual["status"] = status
        atual["atualizado_em"] = instante
        historico = atual.setdefault("historico", [])
        if not historico or _norm(historico[-1].get("texto", "")) != _norm(texto):
            historico.append(entrada)
            del historico[:-8]
    _salvar(dados)
    return True


def buscar_relacionados(pergunta: str, limite: int = 2) -> list:
    if not str(pergunta or "").strip():
        return []
    candidatos = []
    for item in carregar()["assuntos"]:
        nota = _pontuar(pergunta, item)
        if nota >= 0.5:
            candidatos.append((nota, item))
    candidatos.sort(key=lambda par: (par[0], par[1].get("atualizado_em", "")), reverse=True)
    return [item for _, item in candidatos[:limite]]


def contexto_relacionado(pergunta: str, limite: int = 2) -> str:
    linhas = []
    for item in buscar_relacionados(pergunta, limite):
        status = item.get("status", "aberto")
        linhas.append(
            f'- [{status}] {item.get("titulo", "Assunto")} — '
            f'{item.get("estado_atual", "sem estado registrado")}'
        )
    return "\n".join(linhas)
