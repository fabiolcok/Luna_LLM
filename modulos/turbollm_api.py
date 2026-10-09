"""Recuperação do modelo descarregado pela API de gerenciamento do TurboLLM."""

import json
import time
import unicodedata

import httpx


def _norm(texto: str) -> str:
    sem_acentos = unicodedata.normalize("NFKD", texto or "").encode("ascii", "ignore").decode()
    return "".join(c for c in sem_acentos.lower() if c.isalnum())


def opcoes_pensamento(valor: str) -> tuple[str, dict]:
    """Traduz a configuração humana do .env para o chat template do modelo."""
    modo = _norm(valor or "desligado")
    if modo in {"auto", "automatico"}:
        return "automatico", {}
    if modo in {"sim", "on", "true", "1", "ligado"}:
        return "ligado", {"chat_template_kwargs": {"enable_thinking": True}}
    # Desligado também é o fallback seguro: preserva o comportamento que o Gemma
    # já tinha antes desta opção existir e evita gastar a resposta só raciocinando.
    return "desligado", {"chat_template_kwargs": {"enable_thinking": False}}


def erro_modelo_descarregado(erro: Exception) -> bool:
    """Distingue falhas recuperáveis de rota de outros 503."""
    status = getattr(erro, "status_code", None)
    texto = str(erro).lower()
    return status == 503 and any(mensagem in texto for mensagem in (
        "no model loaded",
        "no model matching",
    ))


def erro_alternancia_papeis(erro: Exception) -> bool:
    return (getattr(erro, "status_code", None) == 400
            and "conversation roles must alternate" in str(erro).lower())


def adaptar_mensagens_alternadas(mensagens: list, contexto_inicial: str) -> list:
    """Preserva contexto textual sem inventar pedidos para justificar falas proativas."""
    if not mensagens or any(
        not isinstance(m, dict) or set(m) - {"role", "content"}
        or m.get("role") not in {"system", "user", "assistant"}
        or not isinstance(m.get("content"), str) for m in mensagens
    ):
        # Tool calls e conteúdo multimodal têm contratos próprios; não os achata em texto.
        return mensagens
    inicio = int(mensagens[0]["role"] == "system")
    if any(m["role"] == "system" for m in mensagens[inicio:]):
        return mensagens
    conversa = [dict(m) for m in mensagens[inicio:]]
    primeiro_usuario = next((i for i, m in enumerate(conversa) if m["role"] == "user"), None)
    if primeiro_usuario is None:
        return mensagens
    if primeiro_usuario:
        anteriores = [m["content"] for m in conversa[:primeiro_usuario]]
        conversa = conversa[primeiro_usuario:]
        conversa[0]["content"] = contexto_inicial.format(
            falas=json.dumps(anteriores, ensure_ascii=False), mensagem=conversa[0]["content"])
    saida = [dict(m) for m in mensagens[:inicio]]
    for mensagem in conversa:
        if saida and saida[-1]["role"] == mensagem["role"]:
            # O recorte pode conter vários proativos ou mensagens interrompidas do usuário.
            saida[-1]["content"] += "\n\n" + mensagem["content"]
        else:
            saida.append(mensagem)
    return saida


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

    # O .env é uma escolha explícita. Sem ele, o modelo padrão vem antes do último
    # carregado; assim apagar MODELO_LLM realmente desfaz um teste e volta ao padrão.
    for referencia in (configurado, preferido, marca, ultimo):
        chave = casar(referencia)
        if chave:
            return chave
    return validos[0]["key"] if len(validos) == 1 else None


def listar_biblioteca(base_openai: str, cliente_http=httpx) -> dict:
    """Lista modelos cadastrados e o engine atual sem carregar ou descarregar nada."""
    base = base_openai.removesuffix("/v1").rstrip("/")
    try:
        resposta_modelos = cliente_http.get(f"{base}/api/v1/models", timeout=5)
        resposta_modelos.raise_for_status()
        resposta_status = cliente_http.get(f"{base}/api/v1/status", timeout=3)
        resposta_status.raise_for_status()
        modelos = []
        for item in resposta_modelos.json().get("models", []):
            if not isinstance(item, dict) or not item.get("key"):
                continue
            modelos.append({
                "key": str(item["key"]),
                "name": str(item.get("name") or item["key"]),
            })
        status = resposta_status.json()
        atual = (status.get("model") or {}).get("key", "")
        return {"ok": True, "modelos": modelos, "ativo": str(atual or "")}
    except Exception as erro:
        return {"ok": False, "modelos": [], "ativo": "", "erro": str(erro)}


def recarregar_modelo(base_openai: str, configurado: str = "",
                      preferido: str = "", marca: str = "", segundos: int = 180,
                      aceitar_atual: bool = True,
                      cliente_http=httpx, dormir=time.sleep) -> dict:
    """Carrega o modelo pela API do TurboLLM e espera o engine ficar pronto."""
    base = base_openai.removesuffix("/v1").rstrip("/")
    try:
        resposta_status = cliente_http.get(f"{base}/api/v1/status", timeout=3)
        resposta_status.raise_for_status()
        status = resposta_status.json()

        engine = status.get("engine") or {}
        modelo_atual = status.get("model") or {}
        # Sem escolha explícita, um modelo já rodando é aceito: isso mantém compatibilidade
        # com instalações que batizaram o Gemma de um jeito impossível de adivinhar.
        if (aceitar_atual and not configurado and engine.get("state") == "running"
                and modelo_atual.get("key")):
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

        if engine.get("state") == "running" and modelo_atual.get("key") == chave:
            return {"ok": True, "modelo": chave, "ja_estava_pronto": True}

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
