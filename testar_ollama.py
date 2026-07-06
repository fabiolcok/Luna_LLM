# testar_ollama.py — checa se o Ollama serve pra Luna (models + function-calling + tok/s).
# Ollama rodando. Endpoint OpenAI: 11434/v1.  Rode: venv\Scripts\python testar_ollama.py

import time
from openai import OpenAI

cliente = OpenAI(base_url="http://localhost:11434/v1", api_key="ollama")

try:
    modelos = [m.id for m in cliente.models.list().data]
except Exception as e:
    print("❌ Não conectei no Ollama (11434). Ele está rodando? (ollama serve)\n  ", e)
    raise SystemExit(1)

if not modelos:
    print("⚠️  Ollama sem modelos. Importe os teus: ollama create nemotron-luna -f Modelfile-nemotron")
    raise SystemExit(1)

print("Modelos no Ollama:", modelos)
nemotron = next((m for m in modelos if "nemotron" in m.lower()), None)
gemma    = next((m for m in modelos if "gemma" in m.lower()), None)

# === TESTE 1: function-calling (no NEMOTRON — o roteador da Luna) ===
print("\n=== TESTE 1: function-calling (roteador) ===")
if not nemotron:
    print("⚠️  Nenhum modelo 'nemotron' na lista — importe o Modelfile-nemotron.")
else:
    ferramenta = [{"type": "function", "function": {
        "name": "obter_horas", "description": "Retorna a hora atual.",
        "parameters": {"type": "object", "properties": {}}}}]
    try:
        r = cliente.chat.completions.create(model=nemotron, temperature=0.0, max_tokens=200,
                messages=[{"role": "user", "content": "que horas são agora?"}], tools=ferramenta)
        if getattr(r.choices[0].message, "tool_calls", None):
            print(f"✅ PASSOU — {nemotron} faz function-calling! Chamou:", r.choices[0].message.tool_calls[0].function.name)
        else:
            print(f"⚠️  {nemotron} não chamou a ferramenta:", (r.choices[0].message.content or "")[:130])
    except Exception as e:
        print(f"❌ FALHOU — Ollama não aceitou 'tools' com {nemotron}:\n  ", e)

# === TESTE 2: velocidade (no GEMMA — a persona, o objetivo é ~66 tok/s) ===
print("\n=== TESTE 2: velocidade (persona) ===")
alvo = gemma or nemotron or modelos[0]
try:
    t0 = time.time()
    r = cliente.chat.completions.create(model=alvo, temperature=0.7, max_tokens=200,
            messages=[{"role": "user", "content": "Escreva um parágrafo curto e natural sobre o Brasil."}])
    dur = time.time() - t0
    tk = r.usage.completion_tokens
    print(f"⚡ {alvo}: {tk} tokens em {dur:.1f}s = {tk/dur:.1f} tok/s")
    print("   ~5 = CPU (ROCm não engatou) | ~40-66 = ROCm ok! 🚀")
except Exception as e:
    print(f"❌ Erro no teste de velocidade com {alvo}:", e)
