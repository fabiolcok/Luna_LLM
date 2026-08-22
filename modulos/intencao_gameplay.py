"""Valida evidência literal de uma dúvida de gameplay sem catalogar termos de jogos."""

import re
import unicodedata


def _normalizar(texto: str) -> str:
    texto = unicodedata.normalize("NFKD", texto or "").encode("ascii", "ignore").decode().lower()
    texto = re.sub(r"[^a-z0-9? ]+", " ", texto)
    return re.sub(r"\s+", " ", texto).strip()


# São formas gerais de pedir informação, não uma lista de chefes, itens, verbos ou mecânicas.
_SINAL_PEDIDO = re.compile(
    r"\b(como|onde|aonde|o que|que que|qual|quais|por que|me ajuda|me da uma dica|"
    r"me de uma dica|alguma dica|tem dica|preciso de ajuda)\b"
)
_FOLLOWUP = re.compile(
    r"^(?:e|mas)?\s*(?:na|no|nessa|nesse|depois|durante|contra|com|e quanto a|e quanto ao)\b"
)


def contexto_gameplay_anterior(historico: list | None) -> dict | None:
    """Somente a resposta imediatamente anterior pode sustentar um follow-up curto."""
    if not historico:
        return None
    ultima = historico[-1]
    if ultima.get("role") != "assistant" or ultima.get("_ferramenta") != "duvida_do_jogo":
        return None
    return {"nome_jogo": str(ultima.get("_jogo") or "").strip()}


def validar_pedido_gameplay(texto: str, trecho_pedido: str,
                            historico: list | None = None) -> bool:
    """Exige uma citação real da fala; o roteador não pode fabricar uma pergunta melhor."""
    atual = _normalizar(texto)
    evidencia = _normalizar(trecho_pedido)
    if len(evidencia) < 3 or evidencia not in atual:
        return False
    if _SINAL_PEDIDO.search(evidencia) or "?" in evidencia:
        return True
    return bool(contexto_gameplay_anterior(historico) and _FOLLOWUP.search(evidencia))
