"""Memória estruturada de sessões; registra fatos sem pedir interpretação à LLM."""

import datetime
import json
import os
import re
import threading
import unicodedata


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


def _nome_normalizado(nome: str) -> str:
    texto = unicodedata.normalize("NFKD", str(nome or "")).encode("ascii", "ignore").decode()
    return re.sub(r'[^a-z0-9]+', ' ', texto.lower()).strip()


def _achar_por_nome(estado: dict, nome: str):
    alvo = _nome_normalizado(nome)
    for chave, jogo in estado.get("jogos", {}).items():
        if _nome_normalizado(jogo.get("nome")) == alvo:
            return chave, jogo
    return None, None


def _jogo_base(appid, nome: str, agora: datetime.datetime) -> dict:
    return {
        "appid": str(appid or ""), "nome": nome, "sessoes": 0,
        "minutos_observados": 0, "primeira_abertura": agora.isoformat(),
        "ultima_abertura": None, "ultima_sessao_min": None, "em_andamento": False,
        "estado": None, "estado_declarado_em": None, "platinado": None,
        "platina_declarada_em": None, "opinioes": [],
    }


def registrar_abertura(appid, nome: str, agora: datetime.datetime = None) -> dict:
    """Incrementa uma sessão observada e devolve apenas o contexto que merece virar fala."""
    agora = agora or _agora()
    chave = _chave(appid, nome)
    with _LOCK:
        estado = _carregar()
        # Uma lista pessoal pode ser importada só pelo nome. Na primeira abertura real,
        # migra o registro para o appid sem perder estado nem opiniões.
        jogo = estado["jogos"].get(chave)
        if jogo is None:
            chave_nome, jogo_nome = _achar_por_nome(estado, nome)
            if jogo_nome is not None:
                jogo = jogo_nome
                if chave_nome != chave:
                    estado["jogos"].pop(chave_nome, None)
                    estado["jogos"][chave] = jogo
            else:
                jogo = _jogo_base(appid, nome, agora)
                estado["jogos"][chave] = jogo
        jogo.setdefault("estado", None)
        jogo.setdefault("estado_declarado_em", None)
        jogo.setdefault("platinado", None)
        jogo.setdefault("platina_declarada_em", None)
        jogo.setdefault("opinioes", [])
        jogo["appid"] = str(appid or jogo.get("appid") or "")
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
            "estado": jogo.get("estado"),
            "platinado": jogo.get("platinado"),
            "opinioes": list(jogo.get("opinioes") or [])[-2:],
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


def contexto_pessoal(registro: dict) -> str:
    """Estado/opinião só acompanha o próprio jogo; nunca despeja a biblioteca no prompt."""
    if not registro:
        return ""
    partes = []
    if registro.get("estado"):
        partes.append(f"O usuário declarou este jogo como {registro['estado']}.")
    if registro.get("platinado") is True:
        partes.append("O usuário declarou que platinou este jogo.")
    elif registro.get("platinado") is False:
        partes.append("O usuário declarou que ainda não platinou este jogo.")
    opinioes = registro.get("opinioes") or []
    if opinioes:
        partes.append("Opinião declarada pelo usuário: " + opinioes[-1]["texto"])
    return " ".join(partes)


def registrar_declaracao(nome: str, estado_jogo: str = "", opiniao: str = "",
                         agora: datetime.datetime = None, platinado=None) -> str:
    """Guarda somente o que o usuário declarou; não deduz gosto a partir do uso."""
    agora = agora or _agora()
    nome = str(nome or "").strip()
    estado_jogo = str(estado_jogo or "").strip().lower()
    opiniao = str(opiniao or "").strip()
    permitidos = {"jogando", "zerado", "abandonado"}
    if estado_jogo and estado_jogo not in permitidos:
        return "SISTEMA: estado de jogo inválido; nada foi registrado."
    if not estado_jogo and not opiniao and platinado is None:
        return "SISTEMA: faltou o jogo ou a declaração; nada foi registrado."

    with _LOCK:
        dados = _carregar()
        nome_vago = _nome_normalizado(nome) in {
            "", "nao especificado", "nao informado", "esse jogo", "o jogo", "jogo atual"
        }
        if nome_vago:
            ativos = [str(j.get("nome") or "").strip() for j in dados.get("jogos", {}).values()
                      if j.get("em_andamento") and j.get("nome")]
            if len(ativos) != 1:
                return "SISTEMA: jogo ambíguo; nada foi registrado."
            nome = ativos[0]
        chave, jogo = _achar_por_nome(dados, nome)
        if jogo is None:
            chave = _chave(None, nome)
            jogo = _jogo_base("", nome, agora)
            dados["jogos"][chave] = jogo
        jogo.setdefault("opinioes", [])
        jogo.setdefault("platinado", None)
        jogo.setdefault("platina_declarada_em", None)
        if estado_jogo:
            jogo["estado"] = estado_jogo
            jogo["estado_declarado_em"] = agora.isoformat()
        if platinado is not None:
            jogo["platinado"] = bool(platinado)
            jogo["platina_declarada_em"] = agora.isoformat()
        if opiniao and not any(item.get("texto") == opiniao for item in jogo["opinioes"]):
            jogo["opinioes"].append({"texto": opiniao, "declarada_em": agora.isoformat()})
            jogo["opinioes"] = jogo["opinioes"][-10:]
        dados["ultimo_jogo"] = chave
        _salvar(dados)

    fatos = []
    if estado_jogo:
        fatos.append(f"estado '{estado_jogo}'")
    if opiniao:
        fatos.append("opinião registrada")
    if platinado is not None:
        fatos.append("platina registrada")
    return f"SISTEMA: rotina de {nome} atualizada ({', '.join(fatos)})."


def detectar_declaracao(texto: str) -> dict | None:
    """Rede de segurança para fatos explícitos sobre jogos que já existem na rotina."""
    original = str(texto or "").strip()
    normalizado = _nome_normalizado(original)
    if not original:
        return None
    estado_jogo = ""
    if re.search(r'\b(zerei|terminei|finalizei)\b', original, re.IGNORECASE):
        estado_jogo = "zerado"
    elif re.search(r'\b(desisti|abandonei)\b', original, re.IGNORECASE):
        estado_jogo = "abandonado"
    elif re.search(r'\b(estou\s+jogando|comecei\s+a\s+jogar)\b', original, re.IGNORECASE):
        estado_jogo = "jogando"
    platina = None
    if re.search(r'\b(n[aã]o|ainda\s+n[aã]o)\s+platin', original, re.IGNORECASE):
        platina = False
    elif re.search(r'\b(quero|queria|pretendo|vou\s+tentar)\s+platinar\b|'
                   r'\bfaltam?\s+(?:algumas?\s+)?conquistas?\b', original, re.IGNORECASE):
        platina = False
    elif re.search(r'\b(platinei|platinado)\b', original, re.IGNORECASE):
        platina = True
    if not estado_jogo and platina is None:
        return None

    dados = _carregar()
    candidatos = []
    for jogo in dados.get("jogos", {}).values():
        nome = str(jogo.get("nome") or "").strip()
        nome_norm = _nome_normalizado(nome)
        if nome_norm and re.search(rf'(^| ){re.escape(nome_norm)}($| )', normalizado):
            candidatos.append(nome)
    if not candidatos:
        ativos = [str(j.get("nome") or "").strip() for j in dados.get("jogos", {}).values()
                  if j.get("em_andamento") and j.get("nome")]
        # "esse jogo" é inequívoco somente quando o monitor tem um único jogo aberto.
        if len(ativos) != 1:
            return None
        candidatos = ativos
    nome = max(candidatos, key=len)
    tem_opiniao = bool(re.search(
        r'\b(gostei|curti|n[aã]o\s+gostei|n[aã]o\s+curti|achei)\b',
        original, re.IGNORECASE,
    ))
    return {"nome_jogo": nome, "estado_jogo": estado_jogo,
            "platinado": platina, "opiniao": original if tem_opiniao else ""}


def importar_estados(nomes: list[str], estado_jogo: str = "zerado") -> int:
    """Carga local idempotente; usada para listas pessoais trazidas de outra fonte."""
    importados = 0
    for nome in nomes:
        if nome and registrar_declaracao(nome, estado_jogo).startswith("SISTEMA: rotina"):
            importados += 1
    return importados
