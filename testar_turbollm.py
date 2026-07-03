# testar_turbollm.py — checa se o TurboLLM serve pra Luna.
# Pré-requisito: TurboLLM ligado (npx turbollm) com um modelo carregado.
# Rode com o python do venv:  venv\Scripts\python testar_turbollm.py
# Pode apagar este arquivo depois do teste.

import time
from openai import OpenAI

BASE = "http://127.0.0.1:6996/v1"   # porta padrão do TurboLLM
cliente = OpenAI(base_url=BASE, api_key="turbollm")

# --- Conexão + modelos carregados ---
try:
    modelos = [m.id for m in cliente.models.list().data]
except Exception as e:
    print("❌ Não conectei no TurboLLM. Ele está ligado (npx turbollm) na porta 6996?\n  ", e)
    raise SystemExit(1)

if not modelos:
    print("⚠️  Conectei, mas NENHUM modelo carregado. Carrega um na tela Models do TurboLLM.")
    raise SystemExit(1)

print("Modelos carregados no TurboLLM:", modelos)
MODELO = modelos[0]   # usa o primeiro; pro teste de ferramenta, carregue o NEMOTRON
print(f"Testando com: {MODELO}\n")

# === TESTE 1 (CRÍTICO): function-calling — o roteador da Luna depende disso ===
print("=== TESTE 1: function-calling (tool calling) ===")
ferramenta = [{
    "type": "function",
    "function": {
        "name": "obter_horas",
        "description": "Retorna a hora atual do sistema.",
        "parameters": {"type": "object", "properties": {}},
    },
}]
try:
    r = cliente.chat.completions.create(
        model=MODELO,
        messages=[{"role": "user", "content": "que horas são agora?"}],
        tools=ferramenta,
        temperature=0.0,
        max_tokens=200,
    )
    msg = r.choices[0].message
    if getattr(msg, "tool_calls", None):
        print("✅ PASSOU — o TurboLLM faz function-calling! Chamou:", msg.tool_calls[0].function.name)
    else:
        print("⚠️  Não chamou a ferramenta. Resposta:", (msg.content or "")[:150])
        print("   → Se o modelo carregado NÃO for o Nemotron, é normal. Carregue o Nemotron e rode de novo.")
except Exception as e:
    print("❌ FALHOU — o servidor não aceitou o parâmetro 'tools' (isso quebraria o roteador da Luna):\n  ", e)

# === TESTE 2: velocidade (tok/s) — compare com o LM Studio ===
print("\n=== TESTE 2: velocidade ===")
try:
    t0 = time.time()
    r = cliente.chat.completions.create(
        model=MODELO,
        messages=[{"role": "user", "content": "Escreva um parágrafo curto e natural sobre o Brasil."}],
        temperature=0.7,
        max_tokens=200,
    )
    dur = time.time() - t0
    tk = r.usage.completion_tokens
    print(f"⚡ {tk} tokens em {dur:.1f}s = {tk/dur:.1f} tok/s")
    print("   Compare com o número que aparece no cmd da Luna com o LM Studio.")
except Exception as e:
    print("❌ Erro no teste de velocidade:", e)

print("\nPronto. Se o TESTE 1 passou E o tok/s foi maior que o LM Studio, vale trocar.")
