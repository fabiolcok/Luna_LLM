# teste_pronuncia.py
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from modulos.falar import falar_texto

VOZES_DISPONIVEIS = ["F1", "F2", "F3", "F4", "F5", "M1", "M2", "M3", "M4", "M5"]

SEQUENCIAS = {
    "1": {
        "nome": "Exclamacao (1 a 6 !)",
        "frases": [
            "Que descoberta interessante voce fez hoje!",
            "Que descoberta interessante voce fez hoje!!",
            "Que descoberta interessante voce fez hoje!!!",
            "Que descoberta interessante voce fez hoje!!!!",
            "Que descoberta interessante voce fez hoje!!!!!",
            "Que descoberta interessante voce fez hoje!!!!!!",
        ]
    },
    "2": {
        "nome": "Interrogacao (1 a 6 ?)",
        "frases": [
            "Voce tem certeza que isso vai funcionar?",
            "Voce tem certeza que isso vai funcionar??",
            "Voce tem certeza que isso vai funcionar???",
            "Voce tem certeza que isso vai funcionar????",
            "Voce tem certeza que isso vai funcionar?????",
            "Voce tem certeza que isso vai funcionar??????",
        ]
    },
    "3": {
        "nome": "Pausa + Enfase (... com 1 a 3 !)",
        "frases": [
            "Isso e... impressionante!",
            "Isso e... impressionante!!",
            "Isso e... impressionante!!!",
        ]
    },
}

_voz_atual = "F1"
_vel_atual = 1.15

def menu():
    print("\n" + "="*50)
    print("  BANCADA DE TESTE DE PRONUNCIA DA LUNA")
    print(f"  Voz atual: {_voz_atual}  |  Velocidade: {_vel_atual}")
    print("="*50)
    for chave, seq in SEQUENCIAS.items():
        print(f"  [{chave}] {seq['nome']} ({len(seq['frases'])} frases)")
    print("  [0] Modo livre — digitar frase manualmente")
    print("  [v] Trocar voz")
    print("  [e] Trocar velocidade")
    print("  [t] Testar todas as vozes (frase padrão)")
    print("  [s] Sair")
    print("="*50)
    return input("Escolha: ").strip().lower()

def rodar_sequencia(seq):
    nome = seq["nome"]
    frases = seq["frases"]
    print(f"\n--- {nome} ---")
    for i, frase in enumerate(frases, 1):
        print(f"\n[{i}/{len(frases)}] {frase}")
        input("  Enter para falar...")
        falar_texto(frase, voz=_voz_atual, velocidade=_vel_atual)

def modo_livre():
    print("\n--- Modo Livre (digite 'menu' para voltar) ---")
    while True:
        texto = input("\nFrase: ").strip()
        if not texto:
            continue
        if texto.lower() == "menu":
            break
        falar_texto(texto, voz=_voz_atual, velocidade=_vel_atual)

def trocar_voz():
    global _voz_atual
    print(f"\n  Vozes disponíveis: {', '.join(VOZES_DISPONIVEIS)}")
    nova = input(f"  Voz [{_voz_atual}]: ").strip().upper()
    if nova in VOZES_DISPONIVEIS:
        _voz_atual = nova
        print(f"  Voz alterada para: {_voz_atual}")
    elif nova:
        print("  Voz inválida. Mantendo atual.")

def trocar_velocidade():
    global _vel_atual
    print(f"\n  Velocidades sugeridas: 0.8 (lento)  1.0 (normal)  1.15 (padrão)  1.4 (rápido)  1.8 (muito rápido)")
    try:
        nova = float(input(f"  Velocidade [{_vel_atual}]: ").strip())
        if 0.7 <= nova <= 2.0:
            _vel_atual = nova
            print(f"  Velocidade alterada para: {_vel_atual}")
        else:
            print("  Fora do intervalo (0.7–2.0). Mantendo atual.")
    except ValueError:
        print("  Valor inválido. Mantendo atual.")

def testar_todas_vozes():
    frase = "Oi, eu sou a Luna. Esta é minha voz."
    print(f"\n--- Testando todas as vozes com velocidade {_vel_atual} ---")
    for voz in VOZES_DISPONIVEIS:
        print(f"\n  Voz: {voz}")
        input("  Enter para falar...")
        falar_texto(frase, voz=voz, velocidade=_vel_atual)

while True:
    escolha = menu()
    if escolha == "s":
        print("Encerrando...")
        break
    elif escolha == "0":
        modo_livre()
    elif escolha == "v":
        trocar_voz()
    elif escolha == "e":
        trocar_velocidade()
    elif escolha == "t":
        testar_todas_vozes()
    elif escolha in SEQUENCIAS:
        rodar_sequencia(SEQUENCIAS[escolha])
    else:
        print("Opcao invalida.")