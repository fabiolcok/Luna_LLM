# testar_gemma_solo.py — A HIPÓTESE ELEGANTE: um modelo só no TurboLLM.
# Se o Gemma-4-12B QAT fizer function-calling BEM, a Luna roda com ele sozinho
# (MODO_DUAL_LLM=False): sem swap, sem VRAM apertada, sem auto-load quebrado.
# O 12B é mais parrudo → melhor chance de rotear E fazer persona bem, a ~30 t/s.
#
# ANTES DE RODAR: no TurboLLM, carregue SÓ o Gemma 4 12B QAT (pode ejetar o resto).
# Rode:  venv\Scripts\python testar_gemma_solo.py

import time, json
from openai import OpenAI

cliente = OpenAI(base_url="http://127.0.0.1:6996/v1", api_key="turbollm")
PERSONA = "gemma-4-12b-it-qat"   # tem que bater com o Gemma 12B QAT carregado
MARCA   = "12b"                  # substring pra confirmar que foi o 12B (não caiu em fallback)

# 3 ferramentas — pra ver se ele ROTEIA (escolhe a certa), não só chama qualquer uma.
tools = [
    {"type": "function", "function": {"name": "obter_horas",
        "description": "Retorna a hora atual do sistema.",
        "parameters": {"type": "object", "properties": {}}}},
    {"type": "function", "function": {"name": "obter_clima",
        "description": "Retorna a previsão do tempo de uma cidade.",
        "parameters": {"type": "object", "properties": {
            "cidade": {"type": "string", "description": "nome da cidade"}}, "required": ["cidade"]}}},
    {"type": "function", "function": {"name": "tocar_musica",
        "description": "Toca uma música ou artista no Spotify.",
        "parameters": {"type": "object", "properties": {
            "busca": {"type": "string", "description": "música ou artista"}}, "required": ["busca"]}}},
]

# (frase do usuário, ferramenta esperada). None = NÃO deve chamar ferramenta (é papo).
casos = [
    ("que horas são agora?",              "obter_horas"),
    ("como tá o tempo em Brasília?",      "obter_clima"),
    ("bota uma música do Djavan aí",      "tocar_musica"),
    ("oi Luna, tudo bem com você?",       None),
]

def servido_ok(model):
    if MARCA not in model.lower():
        print(f"   🚨 FALLBACK! respondeu '{model.split(chr(92))[-1]}' — carregue o Gemma 12B QAT (só ele).")
        return False
    return True

print(f"=== TESTE ROTEAMENTO: o Gemma 12B QAT escolhe a ferramenta certa? ===\n")
acertos, primeiro_model = 0, None
for frase, esperada in casos:
    try:
        r = cliente.chat.completions.create(model=PERSONA, tools=tools, tool_choice="auto",
                temperature=0.0, max_tokens=150,
                messages=[{"role": "user", "content": frase}])
        if primeiro_model is None:
            primeiro_model = r.model
            if not servido_ok(r.model): break
        tc = getattr(r.choices[0].message, "tool_calls", None)
        chamou = tc[0].function.name if tc else None
        ok = (chamou == esperada)
        acertos += ok
        alvo = esperada or "(nenhuma — papo)"
        print(f"   {'✅' if ok else '❌'} \"{frase[:34]}\"  → esperado: {alvo:16} | chamou: {chamou}")
    except Exception as e:
        print(f"   ❌ \"{frase[:34]}\"  erro:", e); break

print(f"\n   Placar de roteamento: {acertos}/{len(casos)}")

# Persona — DUAS tentativas: com thinking (como veio) e com thinking DESLIGADO.
# O 12B é 'thinking': gasta o orçamento pensando e devolve content vazio. Se desligar
# o raciocínio, ele responde direto (e rápido) → vira um mono excelente.
msgs = [{"role": "system", "content": "Você é a Luna, uma amiga calorosa e próxima do Fábio. Responda direto, sem pensar em voz alta."},
        {"role": "user", "content": "Luna, tô meio cansado hoje. Me anima aí?"}]

def persona(label, extra_body=None, max_tokens=220):
    print(f"\n--- {label} ---")
    try:
        t0 = time.time()
        r = cliente.chat.completions.create(model=PERSONA, temperature=0.7,
                max_tokens=max_tokens, messages=msgs, extra_body=extra_body or {})
        dur = time.time() - t0
        m = r.choices[0].message
        texto = (m.content or "").strip()
        pensou = getattr(m, "reasoning_content", None) or ""
        fim = r.choices[0].finish_reason
        tk = r.usage.completion_tokens or 0
        print(f"   ⚡ {tk} tok em {dur:.1f}s = {tk/dur:.0f} tok/s | finish={fim} | pensou {len(pensou)} chars")
        if not texto:
            print("   ⚠️  content VAZIO (o raciocínio comeu o orçamento).")
        print("   Resposta:", (texto[:500] or "(vazia)"))
    except Exception as e:
        print("   ❌ erro:", e)

print("\n=== TESTE PERSONA ===")
persona("1) como veio (thinking ligado, teto 220)")
# Tenta desligar o raciocínio via chat template (funciona em vários modelos):
persona("2) thinking DESLIGADO (enable_thinking=false)",
        extra_body={"chat_template_kwargs": {"enable_thinking": False}})
# Terceira: thinking ligado com teto ALTO — deixa pensar até o fim pra medir o custo real.
# (pode demorar ~30-60s; olhe 'pensou N chars' + finish=stop vs length)
persona("3) thinking ligado, teto ALTO (deixa pensar até terminar)", max_tokens=3072)

print("\n   VEREDITO:")
print("   • Se a tentativa 2 devolveu texto caloroso a ~30 t/s → 12B mono FUNCIONA (desligar thinking).")
print("   • Se a 3 terminou (finish=stop) com resposta boa → dá pra usar COM thinking, mas veja o tempo")
print("     total: se ele pensa 1500+ tokens toda vez, cada resposta vai levar 40-60s (inviável pra voz).")
print("   • Se AS DUAS (1 e 2) vieram vazias → desligar o reasoning no LOAD do TurboLLM")
print("     (Model Settings → reasoning/thinking off, ou flag --reasoning-budget 0). Aí testamos de novo.")
print("   • Roteamento já passou 4/4 — esse nunca foi o problema. 🌙")
