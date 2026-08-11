# ferramentas/debug_memoria.py
# Ferramenta de diagnóstico: imprime tudo que está guardado no ChromaDB
# (a memória semântica de conversas que a Luna busca para montar contexto).
# Útil para inspecionar/limpar contaminação de contexto. Rode da raiz do projeto:
#     venv\Scripts\python ferramentas\debug_memoria.py
import os
import sys
from pathlib import Path

# ChromaDB e configuração usam caminhos relativos à raiz.
RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))
os.chdir(RAIZ)

from modulos.memoria import _colecao

resultado = _colecao.get()
for doc in resultado["documents"]:
    print("---")
    print(doc)
