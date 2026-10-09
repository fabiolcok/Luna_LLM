"""Prepara o novo índice sem iniciar a Luna; preserva e confere a coleção antiga."""
import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path

import chromadb
from chromadb.errors import NotFoundError
import numpy as np

from modulos import embeddings
from modulos.indice_memoria import abrir_historico, COLECAO_ANTIGA

RAIZ = Path(__file__).resolve().parents[1]


def assinatura(colecao):
    if colecao is None:
        return hashlib.sha256(b"{}").hexdigest()
    dados = colecao.get(include=["documents", "metadatas", "embeddings"])
    vetores = np.asarray(dados["embeddings"]).tolist() if dados["ids"] else []
    registros = {id_: {"documento": doc, "metadados": meta, "vetor": vetor}
                 for id_, doc, meta, vetor in zip(dados["ids"], dados["documents"],
                                                 dados["metadatas"], vetores)}
    return hashlib.sha256(json.dumps(registros, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=RAIZ / "modelos/chromadb")
    parser.add_argument("--backup", type=Path, default=RAIZ / "modelos/backups_embeddings")
    parser.add_argument("--relatorio", type=Path)
    args = parser.parse_args()
    relatorio = args.relatorio or RAIZ / "logs/migracao_embeddings" / (datetime.now().strftime("%Y%m%d-%H%M%S") + ".json")
    if relatorio.exists():
        raise FileExistsError("Escolha outro relatório")
    cliente = chromadb.PersistentClient(path=str(args.db))
    try:
        try:
            antiga = cliente.get_collection(COLECAO_ANTIGA, embedding_function=None)
        except NotFoundError:
            antiga = None
        antes = assinatura(antiga)
        total_antigo = antiga.count() if antiga is not None else 0
        nova, migradas = abrir_historico(cliente, embeddings.obter_embedder(), args.backup)
        depois = assinatura(antiga)
        if antes != depois:
            raise RuntimeError("A origem mudou durante a migração; execute novamente para sincronizar as novas falas")
        vetores = nova.get(include=["embeddings"])["embeddings"]
        if nova.count() and (np.asarray(vetores).shape[1] != embeddings.DIMENSOES or not np.isfinite(vetores).all()):
            raise RuntimeError("Formato inesperado nos novos vetores")
        dados = {
            "quando": datetime.now().astimezone().isoformat(), "modelo": embeddings.MODELO,
            "revisao": embeddings.REVISAO, "dimensoes": embeddings.DIMENSOES, "device": "cpu",
            "conversas_origem": total_antigo, "conversas_destino": nova.count(),
            "conversas_copiadas": migradas, "origem_preservada": antes == depois,
            "sha256_origem_antes": antes, "sha256_origem_depois": depois,
        }
        relatorio.parent.mkdir(parents=True, exist_ok=True)
        with relatorio.open("x", encoding="utf-8") as f:
            json.dump(dados, f, ensure_ascii=False, indent=2)
        print(f"EmbeddingGemma CPU: {migradas} conversas copiadas; novo índice com {nova.count()} conversas.")
        print("Textos, metadados e vetores da origem conferidos e preservados.")
        print(f"Relatório: {relatorio}")
    finally:
        cliente.close()


if __name__ == "__main__":
    main()
