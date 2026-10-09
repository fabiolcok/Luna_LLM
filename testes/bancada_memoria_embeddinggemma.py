"""Valida os caminhos reais de memória com exemplos sintéticos, sem notas privadas."""
import argparse
from contextlib import ExitStack
from datetime import datetime
import importlib.metadata
import json
from pathlib import Path
from unittest.mock import patch

import chromadb
import numpy as np

from modulos import memoria, embeddings
from modulos.indice_memoria import abrir_historico, COLECAO_ANTIGA

RAIZ = Path(__file__).resolve().parents[1]


def notas(documentos):
    stack = ExitStack()
    stack.enter_context(patch("modulos.obsidian.listar_memoria_episodica",
                              return_value=[("2026-10-06", d["texto"]) for d in documentos]))
    stack.enter_context(patch("modulos.obsidian.listar_memoria_arquivo", return_value=[]))
    stack.enter_context(patch("modulos.obsidian.esquentar_memoria"))
    return stack


def placar(linhas):
    positivas = [q for q in linhas if q["relevantes"]]
    negativas = [q for q in linhas if not q["relevantes"]]
    return {
        "positivas": len(positivas), "negativas": len(negativas),
        "positivas_recuperadas": sum(bool(set(q["relevantes"]) & set(q["aceitas"])) for q in positivas),
        "negativas_com_contexto": sum(bool(q["aceitas"]) for q in negativas),
        "itens_sem_relevancia_direta": sum(len(set(q["aceitas"]) - set(q["relevantes"])) for q in linhas),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--saida", type=Path)
    args = parser.parse_args()
    destino = args.saida or RAIZ / "logs/bancada_embeddings" / datetime.now().strftime("integracao-%Y%m%d-%H%M%S")
    if (destino / "resultado.json").exists():
        raise FileExistsError("Escolha outro destino")
    destino.mkdir(parents=True, exist_ok=True)
    fixture = json.loads((RAIZ / "testes/cenarios_embeddings.json").read_text(encoding="utf-8"))
    resultados = {}
    suite = fixture["suites"]["episodica"]
    mapa = {d["texto"]: d["id"] for d in suite["documentos"]}
    with notas(suite["documentos"]), patch.object(memoria, "_mem_emb_cache", {
            "assinatura": None, "fatos": [], "vecs": []}):
        linhas = []
        for q in suite["consultas"]:
            if q["split"] == "teste":
                aceitas = memoria.buscar_memoria_relevante(q["texto"])
                linhas.append({**q, "aceitas": [mapa[f] for _, f in aceitas]})
        resultados["episodica"] = {"placar": placar(linhas), "consultas": linhas}

    cliente = chromadb.PersistentClient(path=str(destino / "indice_sintetico"))
    try:
        suite = fixture["suites"]["historico"]
        antiga = cliente.get_or_create_collection(COLECAO_ANTIGA, embedding_function=None)
        antiga.upsert(ids=[d["id"] for d in suite["documentos"]],
                      documents=[d["texto"] for d in suite["documentos"]],
                      metadatas=[{"data": "06/10/2026", "timestamp": float(i)} for i in range(30)],
                      embeddings=np.ones((30, 384), dtype=np.float32))
        nova, migradas = abrir_historico(cliente, embeddings.obter_embedder(), destino / "backups")
        assert migradas == 30 and antiga.count() == 30 and nova.count() == 30
        linhas = []
        with patch.object(memoria, "_historico", return_value=nova):
            for q in suite["consultas"]:
                if q["split"] == "teste":
                    contexto = memoria.buscar_contexto_relevante(q["texto"])
                    linhas.append({**q, "aceitas": [d["id"] for d in suite["documentos"] if d["texto"] in contexto]})
        resultados["historico"] = {"placar": placar(linhas), "consultas": linhas}
    finally:
        cliente.close()

    conhecidos = [
        "Pretende comprar um Steam Deck.",
        "Toca violão para relaxar.",
        "Prefere a voz Kokoro para a Luna.",
        "Quer comentários de mortes de Dark Souls sem falar o total de mortes.",
        "Embeddings e reconhecimento de fala ficam na CPU para reservar VRAM ao LLM.",
        "Quer que o volume mude ao vivo enquanto arrasta o slider.",
        "Está atrás de CGNAT e negocia abrir portas com o provedor.",
        "Ainda vai configurar backup automático do servidor.",
    ]
    probes = [
        ("repeticao", "Está pensando em adquirir um Steam Deck.", 0),
        ("repeticao", "Gosta de tocar violão para descontrair.", 1),
        ("repeticao", "A Kokoro segue como voz favorita da Luna.", 2),
        ("repeticao", "A Luna deve comentar mortes no Dark Souls sem citar uma contagem.", 3),
        ("repeticao", "Deixa embeddings e transcrição na CPU para sobrar VRAM para o modelo.", 4),
        ("repeticao", "O controle de volume precisa alterar a fala durante a reprodução.", 5),
        ("repeticao", "O CGNAT impede abrir portas; está conversando com o provedor.", 6),
        ("repeticao", "O backup automático do servidor continua pendente.", 7),
        ("atualizacao", "Já comprou o Steam Deck que estava planejando.", 0),
        ("atualizacao", "Agora prefere o Sopro e deixou de usar a Kokoro.", 2),
        ("atualizacao", "O provedor removeu o CGNAT e liberou a abertura de portas.", 6),
        ("atualizacao", "Terminou de configurar backups automáticos do servidor.", 7),
        ("novo", "Gosta de café sem açúcar.", None),
        ("novo", "Adotou um cachorro.", None),
        ("novo", "Começou a aprender jardinagem.", None),
        ("novo", "Prefere viajar de trem.", None),
    ]
    with notas([{"texto": t} for t in conhecidos]), patch.object(memoria, "_mem_emb_cache", {
            "assinatura": None, "fatos": [], "vecs": []}):
        linhas = []
        for tipo, texto, alvo in probes:
            aceitas = memoria._memorias_semelhantes_para_dedup(texto)
            linhas.append({"tipo": tipo, "texto": texto, "alvo": alvo,
                           "aceitas": [conhecidos.index(t) for t in aceitas]})
        resultados["dedup"] = {"probes": linhas}
        for tipo in ("repeticao", "atualizacao", "novo"):
            grupo = [q for q in linhas if q["tipo"] == tipo]
            resultados["dedup"][tipo] = {"total": len(grupo),
                "com_alvo": sum(q["alvo"] in q["aceitas"] for q in grupo if q["alvo"] is not None),
                "com_contexto": sum(bool(q["aceitas"]) for q in grupo)}
    dados = {"modelo": embeddings.MODELO, "revisao": embeddings.REVISAO,
             "dimensoes": embeddings.DIMENSOES, "device": "cpu",
             "pisos": {"historico": memoria.LIMIAR_HISTORICO, "memoria": memoria.LIMIAR_MEMORIA,
                       "dedup": memoria.LIMIAR_DEDUP},
             "versoes": {p: importlib.metadata.version(p) for p in (
                 "torch", "transformers", "sentence-transformers", "numpy", "torchvision")},
             "resultados": resultados}
    (destino / "resultado.json").write_text(json.dumps(dados,ensure_ascii=False,indent=2),encoding="utf-8")
    print({n: d.get("placar", {k:v for k,v in d.items() if k!="probes"}) for n,d in resultados.items()})
    print(f"Resultados em {destino}")


if __name__ == "__main__":
    main()
