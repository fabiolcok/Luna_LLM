r"""Diagnóstico do TurboLLM usando a mesma arquitetura mono da Luna atual.

Rode da raiz do projeto:
    venv\Scripts\python ferramentas\testar_turbollm.py

O script não sobe a Luna. Ele consulta o servidor já ligado, pede o modelo definido em
MODELO_LLM (ou o nome preferido da instalação padrão), testa uma resposta comum, testa
function calling no mesmo modelo e mede três chamadas curtas.
"""

import os
import sys
import time
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI


RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))
os.chdir(RAIZ)
load_dotenv(RAIZ / ".env")

from modulos import config_env  # noqa: E402 — o .env precisa estar carregado antes


BASE = "http://127.0.0.1:6996/v1"
MODELO_PADRAO = "gemma 4 12b it qat"
MODELO_FIXADO = config_env.texto("MODELO_LLM")
MODELO = MODELO_FIXADO or MODELO_PADRAO
THINK_OFF = {"chat_template_kwargs": {"enable_thinking": False}}

cliente = OpenAI(base_url=BASE, api_key="turbollm")

FERRAMENTA_HORA = [{
    "type": "function",
    "function": {
        "name": "obter_horas",
        "description": "Retorna a hora atual.",
        "parameters": {"type": "object", "properties": {}},
    },
}]


def _norm(texto: str) -> str:
    return "".join(c for c in (texto or "").lower() if c.isalnum())


def _modelo_confere(servido: str) -> bool:
    """Detecta o fallback silencioso sem engessar o diagnóstico sempre no Gemma 12B."""
    pedido = _norm(MODELO)
    real = _norm(servido)
    if MODELO_FIXADO:
        return bool(pedido and real and (pedido in real or real in pedido))
    return all(marca in real for marca in ("gemma", "4", "12b"))


def _chamar(texto: str, *, tools=None, max_tokens: int = 80):
    inicio = time.time()
    resposta = cliente.chat.completions.create(
        model=MODELO,
        messages=[{"role": "user", "content": texto}],
        tools=tools,
        temperature=0.0 if tools else 0.6,
        max_tokens=max_tokens,
        extra_body=THINK_OFF,
        timeout=90,
    )
    return resposta, time.time() - inicio


def main() -> int:
    print(f"TurboLLM: {BASE}")
    print(f"Modelo pedido: {MODELO!r}" + (" (.env)" if MODELO_FIXADO else " (padrão)"))

    try:
        ativos = [m.id for m in cliente.models.list().data]
    except Exception as erro:
        print(f"❌ TurboLLM não respondeu: {erro}")
        print("   Confira se ele está ligado com: npx turbollm")
        return 1
    print("Modelos expostos agora:", ativos or "(nenhum; o carregamento sob demanda será testado)")

    falhou = False
    print("\n=== 1. Resposta comum + carregamento do modelo ===")
    try:
        resposta, duracao = _chamar("Responda somente: OK", max_tokens=8)
        texto = (resposta.choices[0].message.content or "").strip()
        servido = resposta.model or ""
        print(f"Servido como: {servido!r} em {duracao:.1f}s | resposta: {texto!r}")
        if not texto:
            print("❌ O modelo devolveu resposta vazia.")
            falhou = True
        if not _modelo_confere(servido):
            print(f"❌ FALLBACK: foi pedido {MODELO!r}, mas o TurboLLM serviu {servido!r}.")
            print("   Se esse é o modelo certo, copie o id servido para MODELO_LLM no .env.")
            falhou = True
    except Exception as erro:
        print(f"❌ Não foi possível carregar/chamar o modelo: {erro}")
        falhou = True

    print("\n=== 2. Function calling no mesmo modelo ===")
    try:
        resposta, duracao = _chamar("Que horas são agora?", tools=FERRAMENTA_HORA)
        chamadas = getattr(resposta.choices[0].message, "tool_calls", None)
        if chamadas and chamadas[0].function.name == "obter_horas":
            print(f"✅ Chamou obter_horas em {duracao:.1f}s.")
        else:
            conteudo = (resposta.choices[0].message.content or "")[:160]
            print(f"❌ Não chamou obter_horas. Resposta: {conteudo!r}")
            falhou = True
    except Exception as erro:
        print(f"❌ Function calling falhou: {erro}")
        falhou = True

    print("\n=== 3. Estabilidade de três chamadas curtas ===")
    tempos = []
    for rodada in range(1, 4):
        try:
            resposta, duracao = _chamar("Diga uma saudação de duas palavras.", max_tokens=12)
            tokens = getattr(resposta.usage, "completion_tokens", 0) or 0
            velocidade = f" | {tokens / duracao:.1f} tok/s" if duracao else ""
            print(f"Rodada {rodada}: {duracao:.1f}s{velocidade}")
            tempos.append(duracao)
        except Exception as erro:
            print(f"Rodada {rodada}: ❌ {erro}")
            falhou = True
            break
    if tempos:
        print(f"Média: {sum(tempos) / len(tempos):.1f}s")

    if falhou:
        print("\n❌ Diagnóstico encontrou problema.")
        return 1
    print("\n✅ TurboLLM respondeu, serviu o modelo esperado e fez function calling.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
