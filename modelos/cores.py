# cores.py
# Sistema de cores para o terminal da Luna

class Cor:
    RESET   = "\033[0m"
    VERDE   = "\033[92m"
    AZUL    = "\033[94m"
    AMARELO = "\033[93m"
    VERMELHO= "\033[91m"
    CINZA   = "\033[90m"
    CIANO   = "\033[96m" 
    MAGENTA = "\033[95m"

def azul(msg): print(f"{Cor.AZUL}{msg}{Cor.RESET}")
def verde(msg): print(f"{Cor.VERDE}{msg}{Cor.RESET}")
def ciano(msg): print(f"{Cor.CIANO}{msg}{Cor.RESET}")
def vermelho(msg): print(f"{Cor.VERMELHO}{msg}{Cor.RESET}")
def cinza(msg): print(f"{Cor.CINZA}{msg}{Cor.RESET}")
def amarelo(msg): print(f"{Cor.AMARELO}{msg}{Cor.RESET}")
def magenta(msg): print(f"{Cor.MAGENTA}{msg}{Cor.RESET}")

#ferramenta amarelo
