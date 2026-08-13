"""Métricas locais de uso das ferramentas, sem guardar argumentos ou retornos."""

import datetime
import json
import os
import re
import threading
import uuid
from collections import deque


_PASTA = "logs"
_HISTORICO = os.path.join(_PASTA, "uso_ferramentas.jsonl")
_RESUMO = os.path.join(_PASTA, "uso_ferramentas_resumo.json")
_lock = threading.Lock()
_recentes = deque(maxlen=100)
_avaliados = set()


def _agora():
    return datetime.datetime.now().astimezone().isoformat(timespec="seconds")


def _chave_texto(texto):
    # Telegram remove tags de rosto/voz antes de exibir; comparar a versão limpa
    # mantém o vínculo com a execução original sem depender dessas marcações visuais.
    limpo = re.sub(r"\[[^\]]{1,80}\]", "", texto or "")
    limpo = re.sub(r"</?[^>]{1,30}>", "", limpo)
    return re.sub(r"\s+", " ", limpo).strip()


def _ler_resumo():
    try:
        with open(_RESUMO, "r", encoding="utf-8") as arquivo:
            dados = json.load(arquivo)
        return dados if isinstance(dados, dict) else {}
    except (OSError, ValueError, TypeError):
        return {}


def _salvar_resumo(resumo):
    os.makedirs(_PASTA, exist_ok=True)
    temporario = _RESUMO + ".tmp"
    with open(temporario, "w", encoding="utf-8") as arquivo:
        json.dump(resumo, arquivo, ensure_ascii=False, indent=2)
    os.replace(temporario, _RESUMO)


def _anexar(evento):
    os.makedirs(_PASTA, exist_ok=True)
    with open(_HISTORICO, "a", encoding="utf-8") as arquivo:
        arquivo.write(json.dumps(evento, ensure_ascii=False) + "\n")


def registrar_uso(nome, sucesso, duracao_s, usuario, luna, canal):
    """Conta uma execução e guarda só o necessário para ligá-la a um 👍/👎 posterior."""
    if not nome:
        return None
    uso_id = uuid.uuid4().hex[:12]
    evento = {
        "tipo": "uso", "id": uso_id, "tempo": _agora(), "ferramenta": nome,
        "canal": canal, "sucesso": bool(sucesso), "duracao_s": round(float(duracao_s), 2),
    }
    with _lock:
        try:
            _anexar(evento)
            resumo = _ler_resumo()
            item = resumo.setdefault(nome, {
                "usos": 0, "sucessos": 0, "erros": 0,
                "avaliacoes_bom": 0, "avaliacoes_ruim": 0,
            })
            item["usos"] += 1
            item["sucessos" if sucesso else "erros"] += 1
            item["ultima_utilizacao"] = evento["tempo"]
            _salvar_resumo(resumo)
            _recentes.append({
                "id": uso_id, "ferramenta": nome, "usuario": usuario or "",
                "luna": _chave_texto(luna), "canal": canal,
            })
        except OSError:
            return None
    return uso_id


def vincular_avaliacao(rating, usuario, luna, canal):
    """Liga a avaliação à ferramenta da resposta, sem contar duas vezes o motivo do 👎."""
    if rating not in ("bom", "ruim"):
        return None
    with _lock:
        uso = next((item for item in reversed(_recentes)
                    if item["canal"] == canal
                    and item["usuario"] == (usuario or "")
                    and item["luna"] == _chave_texto(luna)), None)
        if not uso:
            return None
        if uso["id"] in _avaliados:
            return uso["ferramenta"]
        try:
            _anexar({
                "tipo": "avaliacao", "tempo": _agora(), "uso_id": uso["id"],
                "ferramenta": uso["ferramenta"], "canal": canal, "rating": rating,
            })
            resumo = _ler_resumo()
            item = resumo.setdefault(uso["ferramenta"], {
                "usos": 0, "sucessos": 0, "erros": 0,
                "avaliacoes_bom": 0, "avaliacoes_ruim": 0,
            })
            item[f"avaliacoes_{rating}"] += 1
            _salvar_resumo(resumo)
            _avaliados.add(uso["id"])
        except OSError:
            return None
    return uso["ferramenta"]
