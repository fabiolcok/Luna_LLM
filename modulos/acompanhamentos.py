"""Acompanhamentos confirmados pelo usuário, separados de agenda e memória.

O modelo só pode PROPOR. Salvar, adiar, resolver e esquecer passam por funções
determinísticas deste módulo, usadas igualmente por voz, texto web e Telegram.
"""

from __future__ import annotations

import datetime as dt
import json
import os
import re
import threading
import unicodedata
import uuid
from pathlib import Path

from modulos import config_env


CAMINHO_ESTADO = Path("modelos/acompanhamentos.json")
_VAULT = config_env.texto("OBSIDIAN_VAULT")
_LOCK = threading.RLock()
_TTL_PROPOSTA_MIN = 15
_TTL_RETORNO_H = 36
_MAX_TENTATIVAS = 3
_RE_AGENDA_OU_LEMBRETE = re.compile(
    r"\b(me\s+lembra|me\s+lembre|lembrete|coloca\w*\s+(?:na|no)\s+agenda|"
    r"agenda\w*|marca\w*\s+(?:na|no)\s+agenda|cria\w*\s+(?:um\s+)?evento)\b",
    re.IGNORECASE,
)
_RE_COTIDIANO_SEM_DESFECHO = re.compile(
    r"^\s*(?:eu\s+)?(?:vou|to indo|estou indo)\s+(?:comer|comprar|dormir|jogar|sair|tomar)\b",
    re.IGNORECASE,
)


def _agora() -> dt.datetime:
    return dt.datetime.now().replace(microsecond=0)


def _iso(valor: dt.datetime) -> str:
    return valor.replace(microsecond=0).isoformat()


def _data(valor: str | None) -> dt.datetime | None:
    try:
        return dt.datetime.fromisoformat(str(valor or "").replace("Z", "+00:00")).replace(tzinfo=None)
    except (TypeError, ValueError):
        return None


def _norm(texto: str) -> str:
    sem_acento = unicodedata.normalize("NFKD", texto or "").encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", sem_acento.lower()).strip(" .,!?:;")


def pode_propor(texto: str) -> bool:
    """Última trava contra transformar agenda ou conversa cotidiana em acompanhamento."""
    normalizado = _norm(texto)
    return bool(normalizado and not _RE_AGENDA_OU_LEMBRETE.search(normalizado)
                and not _RE_COTIDIANO_SEM_DESFECHO.search(normalizado))


def _estado_vazio() -> dict:
    return {"versao": 1, "confirmacao": None, "ativos": [], "historico": []}


def _carregar() -> dict:
    try:
        dados = json.loads(CAMINHO_ESTADO.read_text(encoding="utf-8"))
        if not isinstance(dados, dict):
            return _estado_vazio()
    except (OSError, ValueError):
        return _estado_vazio()
    base = _estado_vazio()
    base.update(dados)
    base["ativos"] = base["ativos"] if isinstance(base.get("ativos"), list) else []
    base["historico"] = base["historico"] if isinstance(base.get("historico"), list) else []
    if not isinstance(base.get("confirmacao"), (dict, type(None))):
        base["confirmacao"] = None
    return base


def _confirmacao_valida(estado: dict, agora: dt.datetime) -> dict | None:
    conf = estado.get("confirmacao")
    if not conf:
        return None
    expira = _data(conf.get("expira_em"))
    if not expira or expira <= agora:
        estado["confirmacao"] = None
        return None
    return conf


def _salvar(estado: dict) -> None:
    CAMINHO_ESTADO.parent.mkdir(parents=True, exist_ok=True)
    temporario = CAMINHO_ESTADO.with_suffix(".tmp")
    temporario.write_text(json.dumps(estado, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(temporario, CAMINHO_ESTADO)
    _espelhar_obsidian(estado)


def _espelhar_obsidian(estado: dict) -> None:
    """Mantém uma visão humana no vault; o JSON local continua sendo a fonte de estado."""
    if not _VAULT or not os.path.isdir(_VAULT):
        return
    caminho = Path(_VAULT) / "Luna" / "Acompanhamentos.md"
    linhas = [
        "# Acompanhamentos da Luna",
        "",
        "> Gerenciado automaticamente. Use os botões da Luna ou responda por voz/texto.",
        "> Isto não é agenda nem memória: são assuntos ainda esperando um desfecho.",
        "",
    ]
    ativos = estado.get("ativos", [])
    if not ativos:
        linhas.append("_Nenhum acompanhamento pendente._")
    for item in ativos:
        quando = _data(item.get("perguntar_em"))
        quando_txt = quando.strftime("%d/%m/%Y às %H:%M") if quando else "sem data válida"
        linhas.extend([
            f"- [ ] {item.get('assunto', '').strip()}",
            f"  - Próxima pergunta: {quando_txt}",
            f"  - Tentativas: {int(item.get('tentativas', 0))}/{_MAX_TENTATIVAS}",
            f"  - ID: `{item.get('id', '')}`",
        ])
    try:
        caminho.parent.mkdir(parents=True, exist_ok=True)
        caminho.write_text("\n".join(linhas).rstrip() + "\n", encoding="utf-8")
    except OSError:
        pass


def _notificar() -> None:
    try:
        import servidor
        servidor.notificar_acompanhamentos()
    except Exception:
        pass


def _hora_no_texto(normalizado: str) -> tuple[int, int] | None:
    m = re.search(r"(?:as|por volta das)\s*(\d{1,2})(?::(\d{2}))?\s*h?\b", normalizado)
    if not m:
        m = re.search(r"\b(\d{1,2})(?::(\d{2}))?h\b", normalizado)
    if not m:
        return None
    hora, minuto = int(m.group(1)), int(m.group(2) or 0)
    return (hora, minuto) if 0 <= hora <= 23 and 0 <= minuto <= 59 else None


def interpretar_quando(texto: str, agora: dt.datetime | None = None) -> str | None:
    """Resolve os adiamentos cotidianos sem pedir outra decisão ao modelo de 12B."""
    agora = (agora or _agora()).replace(second=0, microsecond=0)
    normalizado = _norm(texto)
    if not normalizado:
        return None
    direto = _data(texto.strip())
    if direto and direto > agora:
        return _iso(direto)

    destino = None
    m = re.search(r"daqui a (\d+)\s*(minuto|minutos|hora|horas|dia|dias|semana|semanas)\b",
                  normalizado)
    if m:
        n = max(1, int(m.group(1)))
        unidade = m.group(2)
        if unidade.startswith("minuto"):
            destino = agora + dt.timedelta(minutes=n)
        elif unidade.startswith("hora"):
            destino = agora + dt.timedelta(hours=n)
        elif unidade.startswith("dia"):
            destino = agora + dt.timedelta(days=n)
        else:
            destino = agora + dt.timedelta(weeks=n)
    elif "depois de amanha" in normalizado:
        destino = agora + dt.timedelta(days=2)
    elif "amanha" in normalizado:
        destino = agora + dt.timedelta(days=1)
    elif "semana que vem" in normalizado or "proxima semana" in normalizado:
        destino = agora + dt.timedelta(days=7)
    elif "hoje" in normalizado:
        destino = agora
    else:
        dias = {"segunda": 0, "terca": 1, "quarta": 2, "quinta": 3,
                "sexta": 4, "sabado": 5, "domingo": 6}
        alvo = next((n for nome, n in dias.items() if re.search(rf"\b{nome}(?:-feira)?\b", normalizado)), None)
        if alvo is not None:
            salto = (alvo - agora.weekday()) % 7 or 7
            destino = agora + dt.timedelta(days=salto)

    if destino is None:
        return None
    hora = _hora_no_texto(normalizado)
    if hora:
        destino = destino.replace(hour=hora[0], minute=hora[1])
    elif "de manha" in normalizado:
        destino = destino.replace(hour=9, minute=0)
    elif "a tarde" in normalizado or "de tarde" in normalizado:
        destino = destino.replace(hour=15, minute=0)
    elif "a noite" in normalizado or "de noite" in normalizado:
        destino = destino.replace(hour=19, minute=0)
    elif destino.date() != agora.date():
        destino = destino.replace(hour=19, minute=0)
    if destino <= agora:
        destino += dt.timedelta(days=1)
    return _iso(destino)


def _quando_padrao(agora: dt.datetime) -> str:
    return _iso((agora + dt.timedelta(days=1)).replace(hour=19, minute=0, second=0, microsecond=0))


def _quando_legivel(valor: str) -> str:
    data = _data(valor)
    return data.strftime("%d/%m às %H:%M") if data else "depois"


def propor(assunto: str, perguntar_em: str = "", origem: str = "pc") -> str:
    """Cria apenas a confirmação temporária; não transforma a proposta em acompanhamento."""
    assunto = re.sub(r"\s+", " ", str(assunto or "")).strip(" .")[:180]
    if len(assunto) < 5:
        return "Erro: proposta de acompanhamento sem assunto concreto."
    agora = _agora()
    quando = interpretar_quando(perguntar_em, agora) or _quando_padrao(agora)
    with _LOCK:
        estado = _carregar()
        confirmacao_atual = _confirmacao_valida(estado, agora)
        if confirmacao_atual:
            return ("ACOMPANHAMENTO_DECISAO_PENDENTE: espere o usuário confirmar ou descartar "
                    f"'{confirmacao_atual.get('assunto', '')}' antes de oferecer outro.")
        duplicado = next((i for i in estado["ativos"] if _norm(i.get("assunto", "")) == _norm(assunto)), None)
        if duplicado:
            return ("ACOMPANHAMENTO_JA_ATIVO: esse assunto já está ativo para "
                    f"{_quando_legivel(duplicado.get('perguntar_em', ''))}; não ofereça de novo.")
        estado["confirmacao"] = {
            "id": uuid.uuid4().hex[:12], "tipo": "proposta", "assunto": assunto,
            "perguntar_em": quando, "origem": origem,
            "criado_em": _iso(agora),
            "expira_em": _iso(agora + dt.timedelta(minutes=_TTL_PROPOSTA_MIN)),
        }
        _salvar(estado)
    _notificar()
    return ("ACOMPANHAMENTO_PROPOSTO: ainda NÃO foi salvo. Pergunte se o usuário quer que você "
            f"acompanhe o RESULTADO de: '{assunto}'. Não chame isso de agenda ou lembrete.")


def estado_interface() -> dict:
    with _LOCK:
        estado = _carregar()
        antes = estado.get("confirmacao")
        confirmacao = _confirmacao_valida(estado, _agora())
        if antes and not confirmacao:
            _salvar(estado)
        return {"confirmacao": confirmacao, "ativos": list(estado["ativos"])}


def relacionado_a_ativo(texto: str) -> bool:
    """Evita que memória e retomada automática disputem o mesmo assunto confirmado."""
    if not texto or not texto.strip():
        return False
    with _LOCK:
        assuntos = [i.get("assunto", "") for i in _carregar()["ativos"]]
    if not assuntos:
        return False
    from modulos import obsidian
    genericas = {"saber", "como", "ficou", "resultado", "acompanhar", "perguntar", "depois"}
    for assunto in assuntos:
        if not assunto:
            continue
        nucleo = " ".join(p for p in _norm(assunto).split() if p not in genericas)
        if (obsidian.avaliar_relevancia(nucleo, texto, minimo=0.50)
                or obsidian.avaliar_relevancia(texto, assunto, minimo=0.34)
                or obsidian.avaliar_relevancia(assunto, texto, minimo=0.34)):
            return True
    return False


def _arquivar(estado: dict, item: dict, status: str, agora: dt.datetime) -> None:
    registro = dict(item)
    registro.update({"status": status, "encerrado_em": _iso(agora)})
    estado["historico"].append(registro)
    estado["historico"] = estado["historico"][-60:]
    estado["ativos"] = [i for i in estado["ativos"] if i.get("id") != item.get("id")]


def resolver(acao: str, identificador: str = "", quando_texto: str = "") -> str | None:
    """Resolve uma ação de botão ou de fala; ids impedem clique velho de agir no item novo."""
    agora = _agora()
    acao = _norm(acao).replace(" ", "_")
    with _LOCK:
        estado = _carregar()
        conf = _confirmacao_valida(estado, agora)
        if not conf or (identificador and identificador != conf.get("id")):
            return None

        if conf["tipo"] == "proposta":
            if acao in ("descartar", "nao", "so_comentei", "esquecer"):
                estado["confirmacao"] = None
                _salvar(estado)
                resposta = "Beleza, foi só um comentário."
            elif acao in ("confirmar", "sim", "acompanhar"):
                quando = interpretar_quando(quando_texto, agora) or conf["perguntar_em"]
                item = {
                    "id": conf["id"], "assunto": conf["assunto"], "perguntar_em": quando,
                    "origem": conf.get("origem", "pc"), "criado_em": _iso(agora),
                    "tentativas": 0, "status": "pendente",
                }
                estado["ativos"].append(item)
                estado["confirmacao"] = None
                _salvar(estado)
                resposta = f"Fechado. Vou perguntar sobre isso em {_quando_legivel(quando)}."
            else:
                return None
        else:
            item = next((i for i in estado["ativos"] if i.get("id") == conf.get("item_id")), None)
            if not item:
                estado["confirmacao"] = None
                _salvar(estado)
                return None
            if acao in ("resolvido", "resolveu", "feito", "concluido"):
                _arquivar(estado, item, "resolvido", agora)
                resposta = "Boa, marquei como resolvido."
            elif acao in ("esquecer", "descartar", "cancelar"):
                _arquivar(estado, item, "esquecido", agora)
                resposta = "Beleza, não acompanho mais isso."
            elif acao in ("amanha", "adiar", "ainda_nao", "semana_que_vem"):
                texto_data = quando_texto or ("semana que vem" if acao == "semana_que_vem" else "amanhã")
                item["perguntar_em"] = interpretar_quando(texto_data, agora) or _quando_padrao(agora)
                item["status"] = "pendente"
                resposta = f"Tá, volto nisso em {_quando_legivel(item['perguntar_em'])}."
            else:
                return None
            estado["confirmacao"] = None
            _salvar(estado)
    _notificar()
    return resposta


def interceptar_resposta(texto: str) -> str | None:
    """Consome somente respostas inequívocas enquanto existe uma decisão pendente."""
    normalizado = _norm(texto)
    with _LOCK:
        estado = _carregar()
        tinha_confirmacao = bool(estado.get("confirmacao"))
        conf = _confirmacao_valida(estado, _agora())
        if tinha_confirmacao and not conf:
            _salvar(estado)
    if not conf:
        return None
    if conf["tipo"] == "proposta":
        if re.match(r"^(nao|deixa|deixa pra la|nao precisa|so comentei|esquece)\b", normalizado):
            return resolver("descartar", conf["id"])
        tem_data = interpretar_quando(texto) is not None
        if tem_data or re.match(r"^(sim|pode|acompanha|acompanhe|fechado|quero)\b", normalizado):
            return resolver("confirmar", conf["id"], texto if tem_data else "")
    else:
        desfecho = re.search(
            r"\b(resolveu|resolvido|resolvida|deu certo|nao deu certo|consegui|nao consegui|"
            r"feito|concluido|concluida)\b", normalizado)
        if desfecho:
            resposta = resolver("resolvido", conf["id"])
            # "Deu certo, trocaram a fonte e o PC voltou" é conversa, não comando de botão:
            # encerra o estado, mas deixa a frase completa chegar à persona para ela reagir.
            return resposta if len(normalizado.split()) <= 4 else None
        if re.match(r"^(esquece|deixa pra la|nao precisa|cancela)\b", normalizado):
            return resolver("esquecer", conf["id"])
        if re.search(r"\b(ainda nao|amanha|semana que vem|proxima semana|daqui a \d+)\b", normalizado):
            return resolver("adiar", conf["id"], texto)
    return None


def cancelar(identificador: str) -> bool:
    with _LOCK:
        estado = _carregar()
        item = next((i for i in estado["ativos"] if i.get("id") == identificador), None)
        if not item:
            return False
        _arquivar(estado, item, "cancelado", _agora())
        conf = estado.get("confirmacao") or {}
        if conf.get("item_id") == identificador:
            estado["confirmacao"] = None
        _salvar(estado)
    _notificar()
    return True


def proximo_vencido(agora: dt.datetime | None = None) -> dict | None:
    agora = agora or _agora()
    with _LOCK:
        estado = _carregar()
        tinha_confirmacao = bool(estado.get("confirmacao"))
        if _confirmacao_valida(estado, agora):
            return None
        if tinha_confirmacao:
            _salvar(estado)
        candidatos = [i for i in estado["ativos"]
                      if int(i.get("tentativas", 0)) < _MAX_TENTATIVAS
                      and (_data(i.get("perguntar_em")) or dt.datetime.max) <= agora]
        candidatos.sort(key=lambda i: i.get("perguntar_em", ""))
        return dict(candidatos[0]) if candidatos else None


def registrar_pergunta(identificador: str, agora: dt.datetime | None = None) -> bool:
    """Arma as ações de desfecho só depois que a pergunta proativa saiu de verdade."""
    agora = agora or _agora()
    with _LOCK:
        estado = _carregar()
        item = next((i for i in estado["ativos"] if i.get("id") == identificador), None)
        if not item:
            return False
        item["tentativas"] = int(item.get("tentativas", 0)) + 1
        item["ultima_pergunta_em"] = _iso(agora)
        item["perguntar_em"] = _iso(agora + dt.timedelta(days=3))
        item["status"] = ("sem_resposta" if item["tentativas"] >= _MAX_TENTATIVAS
                          else "aguardando_resposta")
        estado["confirmacao"] = {
            "id": uuid.uuid4().hex[:12], "tipo": "retorno", "item_id": item["id"],
            "assunto": item["assunto"], "origem": item.get("origem", "pc"),
            "criado_em": _iso(agora),
            "expira_em": _iso(agora + dt.timedelta(hours=_TTL_RETORNO_H)),
        }
        _salvar(estado)
    _notificar()
    return True
