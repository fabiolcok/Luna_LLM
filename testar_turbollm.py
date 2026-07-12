# testar_turbollm.py — checa se o TurboLLM serve pra Luna.
# Pré-requisito: TurboLLM ligado (npx turbollm). NÃO precisa carregar nada na mão:
# o gateway auto-carrega o modelo pelo nome que a gente manda (fuzzy match na biblioteca).
# Rode com o python do venv:  venv\Scripts\python testar_turbollm.py

import time
from openai import OpenAI

BASE = "http://127.0.0.1:6996/v1"   # porta padrão do TurboLLM
cliente = OpenAI(base_url=BASE, api_key="turbollm")

# Nomes que a Luna vai usar. O gateway faz fuzzy match — mandamos algo específico
# o bastante pra acertar o E4B QAT (a persona rápida) e não o 12B nem o não-QAT.
ROTEADOR = "nemotron"                 # só existe um → match fácil
PERSONA  = "gemma-4-e4b-it-qat"       # específico p/ o E4B QAT (não o 12B, não o Q4_K_M)

# --- Conexão ---
try:
    carregado = [m.id for m in cliente.models.list().data]
except Exception as e:
    print("❌ Não conectei no TurboLLM. Ele está ligado (npx turbollm) na porta 6996?\n  ", e)
    raise SystemExit(1)
print("Modelo carregado agora:", carregado or "(nenhum — tudo bem, o gateway carrega sob demanda)")
print(f"Vou pedir por nome:  roteador='{ROTEADOR}'  persona='{PERSONA}'\n")

ferr = [{"type": "function", "function": {
    "name": "obter_horas", "description": "Retorna a hora atual.",
    "parameters": {"type": "object", "properties": {}}}}]

def chamar(modelo, msg, tools=None, max_tokens=120):
    t0 = time.time()
    r = cliente.chat.completions.create(
        model=modelo, messages=[{"role": "user", "content": msg}],
        tools=tools, temperature=0.3 if tools else 0.6, max_tokens=max_tokens)
    dur = time.time() - t0
    return r, dur

def confere(pedido, servido, deve_conter):
    # O TurboLLM cai silenciosamente no modelo carregado se não achar o pedido.
    # Denuncia isso: se o modelo servido não contém o que esperamos, avisa alto.
    s = servido.lower()
    if deve_conter not in s:
        print(f"   🚨 FALLBACK! pedi '{pedido}' mas respondeu '{servido.split(chr(92))[-1]}' "
              f"(esperava conter '{deve_conter}') — o gateway NÃO carregou o modelo certo.")
        return False
    return True

# === TESTE 1: function-calling no roteador (gateway auto-carrega o Nemotron) ===
print("=== TESTE 1: function-calling (roteador) ===")
try:
    r, _ = chamar(ROTEADOR, "que horas são agora?", tools=ferr)
    confere(ROTEADOR, r.model, "nemotron")
    msg = r.choices[0].message
    if getattr(msg, "tool_calls", None):
        print("✅ PASSOU — o roteador faz function-calling! Chamou:", msg.tool_calls[0].function.name)
    else:
        print("⚠️  Não chamou a ferramenta. Resposta:", (msg.content or "")[:150])
except Exception as e:
    print("❌ FALHOU — nome não bateu ou 'tools' recusado:\n  ", e)

# === TESTE 2: o LOOP REAL da Luna — alterna roteador→persona e mede o custo do swap ===
# Não exige os dois pré-carregados: o gateway carrega pelo nome. Se ele segura os dois
# quentes (LRU pool), as chamadas ficam CONSTANTES e baixas. Se descarrega um pra abrir
# o outro relendo do disco, a chamada trocada dá PICO de tempo a cada rodada.
print("\n=== TESTE 2: loop real (rota → persona, 3x) — mede o swap ===")
print("   (a 1ª rodada inclui o carregamento inicial dos dois — olhe da 2ª em diante)\n")
ok = True
for i in range(1, 4):
    try:
        r_r, dr = chamar(ROTEADOR, "que horas são?", tools=ferr)
        r_p, dp = chamar(PERSONA, "Diga em uma frase algo gentil pro seu usuário.")
        tp = r_p.usage.completion_tokens or 0
        spd = f"{tp/dp:.0f} tok/s" if dp > 0 else "-"
        print(f"   Rodada {i}: rota={dr:.1f}s | persona={dp:.1f}s ({spd})")
        # Denuncia se algum caiu no modelo errado (sem isso, medimos fantasma):
        confere(ROTEADOR, r_r.model, "nemotron")
        confere(PERSONA,  r_p.model, "e4b")
    except Exception as e:
        print(f"   Rodada {i}: ❌", e); ok = False; break

if ok:
    print("\n   Leitura: se 'rota' e 'persona' ficam CONSTANTES e baixos (<2s) da rodada 2 pra frente,")
    print("   o swap é barato (pool quente) → a Luna roda liso.")
    print("   Se a persona dá pico (ex: 5-8s) TODA rodada, o swap está relendo do disco e dói.")

print("\nPronto. TESTE 1 (tools) + TESTE 2 (swap barato) passando = TurboLLM vira o motor da Luna.")
