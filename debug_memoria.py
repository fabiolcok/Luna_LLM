# debug_memoria.py
# Ferramenta de diagnóstico: imprime tudo que está guardado no ChromaDB
# (a memória semântica de conversas que a Luna busca para montar contexto).
# Útil para inspecionar/limpar contaminação de contexto. Rode da raiz do projeto:
#     python debug_memoria.py
from modulos.memoria import _colecao

resultado = _colecao.get()
for doc in resultado["documents"]:
    print("---")
    print(doc)
