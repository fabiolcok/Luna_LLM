# teste_pronuncia.py
from falar import falar_texto

print("="*50)
print("🎙️ BANCADA DE TESTE DE PRONÚNCIA DA LUNA")
print("Digite 'sair' a qualquer momento para encerrar.")
print("="*50)

while True:
    texto = input("\n📝 Digite a frase para a Luna testar: ")
    
    # Se o usuário só apertar Enter sem querer, o loop pula pro próximo
    if not texto.strip():
        continue
        

    if texto.lower() == "sair":
        print("Encerrando testes...")
        break
        
    # Chama a função de fala
    falar_texto(texto)