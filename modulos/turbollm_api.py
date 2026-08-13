"""Recuperação do modelo descarregado pela API de gerenciamento do TurboLLM."""

import time

import httpx


def _norm(texto: str) -> str:
    return "".join(c for c in (texto or "").lower() if c.isalnum())


def erro_modelo_descarregado(erro: Exception) -> bool:
    """Distingue o idle-unload de outros 503 que não devem ser repetidos às cegas."""
    status = getattr(erro, "status_code", None)
    texto = str(erro).lower()
    return status == 503 and "no model loaded" in texto


def selecionar_chave_modelo(modelos: list, configurado: str = "",
                            ultimo: str = "", preferido: str = "",
                            marca: str = "") -> str | None:
    """Escolhe uma chave da biblioteca sem engessar a instalação no Gemma atual."""
    validos = [m for m in modelos if isinstance(m, dict) and m.get("key")]

    def casar(referencia: str):
        alvo = _norm(referencia)
        if not alvo:
            return None
        for modelo in validos:
            campos = (modelo.get("key", ""), modelo.get("name", ""), modelo.get("path", ""))
            if any(_norm(campo) == alvo for campo in campos):
                return modelo["key"]
        for modelo in validos:
            campos = (modelo.get("key", ""), modelo.get("name", ""), modelo.get("path", ""))
            if any(alvo in _norm(campo) for campo in campos):
                return modelo["key"]
        return None

    # O .env é uma escolha explícita. Sem ele, o último modelo realmente usado é a
    # melhor pista — inclusive quando o usuário trocou o Gemma por outro modelo.
    for referencia in (configurado, ultimo, preferido, marca):
        chave = casar(referencia)
        if chave:
            return chave
    return validos[0]["key"] if len(validos) == 1 else None


def recarregar_modelo(base_openai: str, configurado: str = "",
                      preferido: str = "", marca: str = "", segundos: int = 180,
                      cliente_http=httpx, dormir=time.sleep) -> dict:
    """Carrega o modelo pela API do TurboLLM e espera o engine ficar pronto."""
    base = base_openai.removesuffix("/v1").rstrip("/")
    try:
        resposta_status = cliente_http.get(f"{base}/api/v1/status", timeout=3)
        resposta_status.raise_for_status()
        status = resposta_status.json()

        engine = status.get("engine") or {}
        modelo_atual = status.get("model") or {}
        if engine.get("state") == "running" and modelo_atual.get("key"):
            return {"ok": True, "modelo": modelo_atual["key"], "ja_estava_pronto": True}

        resposta_modelos = cliente_http.get(f"{base}/api/v1/models", timeout=5)
        resposta_modelos.raise_for_status()
        modelos = resposta_modelos.json().get("models", [])
        ultimo = (status.get("lastLoaded") or {}).get("modelKey", "")
        chave = selecionar_chave_modelo(
            modelos, configurado=configurado, ultimo=ultimo,
            preferido=preferido, marca=marca,
        )
        if not chave:
            return {"ok": False, "erro": "não encontrei qual modelo carregar na biblioteca"}

        inicio = cliente_http.post(
            f"{base}/api/v1/engine/start",
            json={"modelKey": chave}, timeout=10,
        )
        inicio.raise_for_status()

        limite = time.monotonic() + segundos
        while time.monotonic() < limite:
            dormir(1)
            consulta = cliente_http.get(f"{base}/api/v1/status", timeout=3)
            consulta.raise_for_status()
            atual = consulta.json()
            estado = (atual.get("engine") or {}).get("state")
            if estado == "running":
                carregado = (atual.get("model") or {}).get("key") or chave
                return {"ok": True, "modelo": carregado, "ja_estava_pronto": False}
            if estado == "error":
                detalhe = (atual.get("engine") or {}).get("err") or "o engine falhou ao carregar"
                return {"ok": False, "erro": str(detalhe)}
        return {"ok": False, "erro": f"o carregamento passou de {segundos}s"}
    except Exception as erro:
        return {"ok": False, "erro": str(erro)}
