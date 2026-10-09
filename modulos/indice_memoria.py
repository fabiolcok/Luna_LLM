"""Migração retomável do histórico, mantendo a coleção MiniLM e um backup textual."""
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path

from chromadb.errors import NotFoundError

from modulos.embeddings import MODELO, REVISAO, DIMENSOES

COLECAO_ANTIGA = "historico_luna"
COLECAO_NOVA = "historico_luna_embeddinggemma2_768_v1"
_IDENTIDADE = {
    "embedding_model": MODELO, "embedding_revision": REVISAO,
    "embedding_dims": DIMENSOES, "query_prompt": "SearchQuery", "document_prompt": "Document",
}


def abrir_historico(cliente, embedder, pasta_backup):
    colecao = cliente.get_or_create_collection(
        name=COLECAO_NOVA, embedding_function=None,
        configuration={"hnsw": {"space": "cosine", "num_threads": 4}},
        metadata={**_IDENTIDADE, "origem_ids": "[]", "migracao_concluida": False},
    )
    meta = dict(colecao.metadata or {})
    if (any(meta.get(k) != v for k, v in _IDENTIDADE.items())
            or colecao.configuration["hnsw"]["space"] != "cosine"):
        raise ValueError("Índice de memória incompatível com o EmbeddingGemma configurado")
    try:
        antiga = cliente.get_collection(COLECAO_ANTIGA, embedding_function=None)
    except NotFoundError:
        antiga = None
    dados = antiga.get(include=["documents", "metadatas"]) if antiga is not None else {
        "ids": [], "documents": [], "metadatas": [],
    }
    vistos = json.loads(meta.get("origem_ids", "[]"))
    if not isinstance(vistos, list) or not all(isinstance(id_, str) for id_ in vistos):
        raise ValueError("Marcador de migração inválido")
    registros = list(zip(dados["ids"], dados["documents"], dados["metadatas"]))
    novos = [(id_, doc, metadados) for id_, doc, metadados in registros if id_ not in vistos]
    if any(not isinstance(doc, str) or not doc.strip() for _, doc, _ in novos):
        raise ValueError("Conversa de origem sem texto; migração interrompida")
    if novos:
        conteudo = {k: dados[k] for k in ("ids", "documents", "metadatas")}
        bruto = json.dumps(conteudo, ensure_ascii=False, sort_keys=True).encode("utf-8")
        assinatura = hashlib.sha256(bruto).hexdigest()
        destino = Path(pasta_backup) / f"historico-luna-{assinatura[:16]}.json"
        destino.parent.mkdir(parents=True, exist_ok=True)
        if destino.exists():
            salvo = json.loads(destino.read_text(encoding="utf-8"))
            dados_salvos = {k: salvo[k] for k in ("ids", "documents", "metadatas")}
            bytes_salvos = json.dumps(dados_salvos, ensure_ascii=False, sort_keys=True).encode("utf-8")
            if hashlib.sha256(bytes_salvos).hexdigest() != assinatura:
                raise ValueError("Backup de origem inválido; migração interrompida")
        else:
            # Renomear só após fechar/sincronizar evita tratar um JSON parcial como backup.
            temporario = destino.with_suffix(".tmp")
            with temporario.open("w", encoding="utf-8") as f:
                json.dump({"colecao": COLECAO_ANTIGA, "sha256": assinatura,
                           "salvo_em": datetime.now().astimezone().isoformat(), **conteudo},
                          f, ensure_ascii=False, indent=2)
                f.flush()
                os.fsync(f.fileno())
            temporario.replace(destino)
        for inicio in range(0, len(novos), 8):
            lote = novos[inicio:inicio + 8]
            ids, docs, metadados = map(list, zip(*lote))
            vetores = embedder.documentos(docs)
            colecao.upsert(ids=ids, documents=docs, metadatas=metadados, embeddings=vetores)
        copiados = colecao.get(ids=[r[0] for r in novos], include=["documents", "metadatas"])
        conferencia = dict(zip(copiados["ids"], zip(copiados["documents"], copiados["metadatas"])))
        if any(conferencia.get(id_) != (doc, m) for id_, doc, m in novos):
            raise RuntimeError("Cópia do histórico não conferiu; origem preservada")

    if novos or not meta.get("migracao_concluida"):
        # Guardar IDs já vistos evita ressuscitar conversas podadas do novo histórico.
        # Também captura falas feitas na instância antiga antes de o usuário reiniciar.
        colecao.modify(metadata={**meta,
            "origem_ids": json.dumps(sorted(set(vistos) | {r[0] for r in novos})),
            "migracao_concluida": True,
        })
    return colecao, len(novos)
