"""Bancada CPU de embeddings; usa fixtures sintéticas, sem importar a Luna.

Execute no ambiente separado:
  logs/bancada_embeddings/venv/Scripts/python.exe -X utf8 -u -m testes.bancada_embeddings
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
import platform
import statistics
import subprocess
import sys
import threading
import time
from datetime import datetime
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
CENARIOS = RAIZ / "testes/cenarios_embeddings.json"
MODELOS = {
    "minilm_l6": "sentence-transformers/all-MiniLM-L6-v2",
    "minilm_multi": "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
    "gemma2": "google/embeddinggemma-2",
}
GEMMA_REVISION = "914f7f89142e33e77833254d9c9b90c3cef7303b"


def gravar_json(path, dados):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(dados, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temp.replace(path)


def validar_cenarios(dados):
    for nome, suite in dados["suites"].items():
        ids = {d["id"] for d in suite["documentos"]}
        if len(ids) != len(suite["documentos"]):
            raise ValueError(f"Documento duplicado em {nome}")
        consultas = suite["consultas"]
        if len({q["id"] for q in consultas}) != len(consultas):
            raise ValueError(f"Consulta duplicada em {nome}")
        for q in consultas:
            if q["split"] not in {"calibracao", "teste"} or not set(q["relevantes"]) <= ids:
                raise ValueError(f"Rótulo inválido: {q['id']}")
        for split in ("calibracao", "teste"):
            casos = [q for q in consultas if q["split"] == split]
            if not any(q["relevantes"] for q in casos) or not any(not q["relevantes"] for q in casos):
                raise ValueError(f"{nome}/{split} precisa de positivos e negativos")


def calibrar_limiar(linhas):
    # Só as negativas da calibração escolhem o piso; o teste fica intocado.
    negativos = [r["ranking"][0]["score"] for r in linhas
                 if r["split"] == "calibracao" and not r["relevantes"]]
    if not negativos:
        raise ValueError("Faltam negativas de calibração")
    return max(negativos) + 1e-6


def avaliar(linhas, split="teste", limiar=None):
    casos = [r for r in linhas if r["split"] == split]
    positivos = [r for r in casos if r["relevantes"]]
    negativos = [r for r in casos if not r["relevantes"]]
    hit1 = hit3 = recall = falsos_positivos = 0
    corretos = incorretos = 0
    reciprocais = []
    for r in casos:
        alvos = set(r["relevantes"])
        ranking = r["ranking"]
        retornados = [p for p in ranking[:3] if limiar is None or p["score"] >= limiar]
        certos = sum(p["id"] in alvos for p in retornados)
        corretos += certos
        incorretos += len(retornados) - certos
        if alvos:
            hit1 += ranking[0]["id"] in alvos
            hit3 += any(p["id"] in alvos for p in ranking[:3])
            recall += bool(certos)
            reciprocais.append(next((1 / (i + 1) for i, p in enumerate(ranking)
                                     if p["id"] in alvos), 0))
        elif retornados:
            falsos_positivos += 1  # memória indevida numa pergunta sem resposta no corpus
    return {
        "positivas": len(positivos), "negativas": len(negativos),
        "hit1": hit1, "hit3": hit3,
        "mrr": statistics.mean(reciprocais) if reciprocais else 0,
        "positivas_com_relevante": recall,
        "negativas_com_memoria_indevida": falsos_positivos,
        "itens_corretos": corretos, "itens_incorretos": incorretos,
        "limiar": limiar,
    }


def avaliar_l2(linhas):
    convertidas = [{**r, "ranking": [
        {"id": p["id"], "score": -p["distancia2"]} for p in r["ranking_l2"]
    ]} for r in linhas]
    return avaliar(convertidas, limiar=-1.3)


class MonitorRAM:
    def __init__(self, processo):
        self.processo = processo
        self.peak = processo.memory_info().rss
        self.stop = threading.Event()
        self.thread = threading.Thread(target=self._loop, daemon=True)

    def _loop(self):
        while not self.stop.wait(.02):
            self.peak = max(self.peak, self.processo.memory_info().rss)

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, *args):
        self.peak = max(self.peak, self.processo.memory_info().rss)
        self.stop.set()
        self.thread.join()


def configurar_cpu(threads):
    # Vale antes do import de torch; impede que a bancada tome VRAM ou todos os núcleos.
    os.environ.update(CUDA_VISIBLE_DEVICES="-1", HIP_VISIBLE_DEVICES="-1",
                      ROCR_VISIBLE_DEVICES="-1", OMP_NUM_THREADS=str(threads),
                      MKL_NUM_THREADS=str(threads), TOKENIZERS_PARALLELISM="false",
                      HF_HUB_DISABLE_PROGRESS_BARS="1", HF_HUB_DISABLE_TELEMETRY="1",
                      HF_HUB_DISABLE_IMPLICIT_TOKEN="1")


def worker(args):
    configurar_cpu(args.threads)
    import numpy as np
    import psutil
    import torch
    from sentence_transformers import SentenceTransformer

    torch.set_num_threads(args.threads)
    torch.set_num_interop_threads(1)
    dados = json.loads(CENARIOS.read_text(encoding="utf-8"))
    validar_cenarios(dados)
    baseline_rss = psutil.Process().memory_info().rss
    gemma = args.worker == "gemma2"
    kwargs = {"config_kwargs": {"vision_config": None, "audio_config": None}} if gemma else {}
    print(f"[{args.worker}] Carregando na CPU, float32, {args.threads} threads...", flush=True)
    with MonitorRAM(psutil.Process()) as ram:
        inicio = time.perf_counter()
        model = SentenceTransformer(args.checkpoint, device="cpu", local_files_only=True,
                                    trust_remote_code=False,
                                    model_kwargs={"dtype": torch.float32}, **kwargs)
        load_s = time.perf_counter() - inicio
        assert all(p.device.type == "cpu" for p in model.parameters())
        assert all(p.dtype == torch.float32 for p in model.parameters() if p.is_floating_point())
        if gemma:
            # O tokenizer declara um sentinela enorme; limite textual publicado: 8192.
            model.max_seq_length = 8192
            assert not any("vision" in n or "audio" in n for n, _ in model.named_parameters())
            assert {"SearchQuery", "Document"} <= set(model.prompts)
        memoria_load = psutil.Process().memory_info().rss

        def encode(textos, documento=False):
            opcoes = {"prompt_name": "Document" if documento else "SearchQuery"} if gemma else {"prompt": ""}
            return np.asarray(model.encode(textos, batch_size=8, show_progress_bar=False,
                convert_to_numpy=True, normalize_embeddings=False, **opcoes), dtype=np.float32)

        encode(["Esta frase aquece a inferência."], documento=True)
        for _ in range(3):
            encode(["Qual voz foi escolhida para a Luna?"])
        resultados = {}
        latencias = []
        for nome, suite in dados["suites"].items():
            print(f"[{args.worker}] {nome}: 30 documentos, 40 consultas...", flush=True)
            inicio = time.perf_counter()
            documentos = encode([d["texto"] for d in suite["documentos"]], documento=True)
            index_ms = (time.perf_counter() - inicio) * 1000
            query_vecs = []
            for q in suite["consultas"]:
                inicio = time.perf_counter()
                vector = encode([q["texto"]])[0]
                elapsed = (time.perf_counter() - inicio) * 1000
                latencias.append(elapsed)
                query_vecs.append(vector)
            query_vecs = np.stack(query_vecs)
            assert np.isfinite(documentos).all() and np.isfinite(query_vecs).all()
            variantes = (768, 256) if gemma else (documentos.shape[1],)
            for dim in variantes:
                docs = documentos[:, :dim]
                queries = query_vecs[:, :dim]
                norms_docs = np.linalg.norm(docs, axis=1, keepdims=True)
                norms_q = np.linalg.norm(queries, axis=1, keepdims=True)
                assert (norms_docs > 0).all() and (norms_q > 0).all()
                scores = (queries / norms_q) @ (docs / norms_docs).T
                linhas = []
                for i, q in enumerate(suite["consultas"]):
                    order = np.argsort(-scores[i], kind="stable")
                    # MRL exige renormalizar depois do corte, inclusive no diagn?stico L2.
                    docs_l2 = docs / norms_docs if gemma else docs
                    query_l2 = queries[i] / norms_q[i] if gemma else queries[i]
                    distancias = ((query_l2 - docs_l2) ** 2).sum(axis=1)
                    ordem_l2 = np.argsort(distancias, kind="stable")
                    linhas.append({**q,
                        "ranking": [{"id": suite["documentos"][j]["id"], "score": float(scores[i, j])}
                                    for j in order],
                        "ranking_l2": [{"id": suite["documentos"][j]["id"], "distancia2": float(distancias[j])}
                                       for j in ordem_l2]})
                limiar = calibrar_limiar(linhas)
                key = f"{nome}_{dim}d"
                resultados[key] = {"suite": nome, "dimensoes": dim, "index_ms": index_ms,
                    "vetores_bytes": int(len(docs) * dim * 4), "limiar_calibracao": limiar,
                    "sem_filtro": avaliar(linhas),
                    "piso_0_52": avaliar(linhas, limiar=.52),
                    "conservador_calibracao": avaliar(linhas, split="calibracao", limiar=limiar),
                    "conservador_teste": avaliar(linhas, limiar=limiar),
                    "l2_1_3": avaliar_l2(linhas), "consultas": linhas}
            print(f"[{args.worker}] {nome} concluído.", flush=True)
        memoria_final = psutil.Process().memory_info().rss
    resultado = {"modelo": MODELOS[args.worker], "revisao": Path(args.checkpoint).name,
        "cenarios_sha256": hashlib.sha256(CENARIOS.read_bytes()).hexdigest(),
        "device": "cpu", "dtype": "float32", "threads": args.threads,
        "parametros_carregados": sum(p.numel() for p in model.parameters()),
        "bytes_parametros": sum(p.numel() * p.element_size() for p in model.parameters()),
        "load_s_sem_download": load_s, "rss_imports_mib": baseline_rss / 2**20,
        "rss_load_mib": memoria_load / 2**20, "rss_final_mib": memoria_final / 2**20,
        "rss_peak_mib": ram.peak / 2**20, "rss_peak_extra_mib": (ram.peak - baseline_rss) / 2**20,
        "latencia_mediana_ms": statistics.median(latencias),
        "latencia_p95_ms": float(np.percentile(latencias, 95)), "latencias_ms": latencias,
        "max_seq_length": model.max_seq_length,
        "prefixos": {"consulta": "SearchQuery", "documento": "Document"} if gemma else None,
        "versoes": {p: importlib.metadata.version(p) for p in
                    ("torch", "torchvision", "pillow", "transformers", "sentence-transformers", "numpy", "psutil")},
        "resultados": resultados}
    gravar_json(args.saida / f"{args.worker}.json", resultado)
    print(f"[{args.worker}] RAM pico {ram.peak / 2**20:.0f} MiB; consulta mediana {statistics.median(latencias):.1f} ms", flush=True)


def preparar_checkpoint(nome):
    from huggingface_hub import snapshot_download
    modelo = MODELOS[nome]
    if nome == "gemma2":
        pronto = RAIZ / "logs/bancada_embeddings/modelo_gemma.json"
        if pronto.exists():
            info = json.loads(pronto.read_text(encoding="utf-8"))
            path = Path(info["path"])
            if info["revision"] == GEMMA_REVISION and (path / "chat_template.jinja").is_file():
                return str(path)
        return snapshot_download(modelo, revision=GEMMA_REVISION, token=False,
            cache_dir=RAIZ / "logs/bancada_embeddings/cache_hf",
            allow_patterns=["*.json", "*.safetensors", "*.txt", "*.model", "*.jinja"])
    try:
        return snapshot_download(modelo, local_files_only=True, token=False)
    except Exception:
        return snapshot_download(modelo, token=False,
            cache_dir=RAIZ / "logs/bancada_embeddings/cache_hf",
            allow_patterns=["*.json", "*.safetensors", "*.txt", "*.model", "*.jinja"])


def relatorio(saida, modelos):
    linhas = ["# Bancada de embeddings — CPU", "",
        "Fixture sintética: 30 documentos e 40 consultas por canal. Por canal: 20 consultas",
        "de calibração (12 positivas, 8 negativas) e 20 de teste (12 positivas, 8 negativas).",
        "Só as negativas de calibração escolhem o limiar conservador; o teste não participa.",
        "Todos os modelos: mesmo ambiente, float32, CPU, processos separados; threads registradas no JSON.",
        "Não importa a Luna nem acessa o histórico, o ChromaDB ou memórias reais.", "",
        "| Modelo | Parâmetros carregados | RAM pico do processo (MiB) | RAM extra sobre imports (MiB) | Consulta mediana / p95 (ms) |",
        "|---|---:|---:|---:|---:|"]
    for nome, r in modelos.items():
        linhas.append(f"| {nome} | {r['parametros_carregados']:,} | {r['rss_peak_mib']:.0f} | {r['rss_peak_extra_mib']:.0f} | {r['latencia_mediana_ms']:.1f} / {r['latencia_p95_ms']:.1f} |")
    linhas += ["", "## Qualidade em consultas de teste", "",
        "Hit@1/3 usa só as 12 positivas por canal, antes do filtro. As negativas perguntam",
        "sobre informação ausente ou conhecimento externo. Ruído nos itens conta também",
        "memórias relacionadas ao tema, mas que não correspondem ao episódio pedido.", "",
        "| Modelo | Canal | Dim | Hit@1 | Hit@3 | MRR | Limiar conservador | Positivas recuperadas | Negativas com memória indevida | Ruído entre itens aceitos |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for nome, r in modelos.items():
        for data in r["resultados"].values():
            raw, m = data["sem_filtro"], data["conservador_teste"]
            linhas.append(f"| {nome} | {data['suite']} | {data['dimensoes']} | {raw['hit1']}/12 | {raw['hit3']}/12 | {raw['mrr']:.3f} | {data['limiar_calibracao']:.4f} | {m['positivas_com_relevante']}/12 | {m['negativas_com_memoria_indevida']}/8 | {m['itens_incorretos']} |")
    linhas += ["", "## Aplicar o piso atual de 0,52 sem calibrar", "",
        "| Modelo | Canal | Dim | Positivas recuperadas | Negativas com memória indevida |",
        "|---|---|---:|---:|---:|"]
    for nome, r in modelos.items():
        for data in r["resultados"].values():
            m = data["piso_0_52"]
            linhas.append(f"| {nome} | {data['suite']} | {data['dimensoes']} | {m['positivas_com_relevante']}/12 | {m['negativas_com_memoria_indevida']}/8 |")
    linhas += ["", "## Erros de primeiro lugar nas positivas", ""]
    for nome, r in modelos.items():
        for data in r["resultados"].values():
            for q in data["consultas"]:
                if q["split"] == "teste" and q["relevantes"] and q["ranking"][0]["id"] not in q["relevantes"]:
                    linhas.append(f"- {nome}/{data['suite']}/{data['dimensoes']}d: “{q['texto']}” → {q['ranking'][0]['id']}; esperado {', '.join(q['relevantes'])}.")
    linhas += ["", "## Limitações", "",
        "- Uma rodada e um corpus pequeno de exemplos sintéticos; não prova melhoria na memória real.",
        "- Tempo mede codificação de uma consulta depois do aquecimento, não a resposta completa da Luna.",
        "- RSS inclui Python, PyTorch e bibliotecas. A RAM extra é um delta observado, não só tamanho dos pesos.",
        "- Download fica fora do tempo de carregamento. Há cache de arquivos do sistema operacional.",
        "- 256d reutiliza a mesma inferência do Gemma 768d; a economia é no armazenamento dos vetores.",
        "- Modelos atuais foram executados no mesmo ambiente atualizado da bancada; o runtime da Luna não mudou.",
        "- O filtro histórico L2=1,3 é registrado no JSON; não é intercambiável com um piso de cosseno.",
        "- Dimensões, prefixos, índice e pisos precisam ser revistos antes de qualquer migração.", ""]
    (saida / "resultado.md").write_text("\n".join(linhas), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--saida", type=Path)
    parser.add_argument("--threads", type=int, default=4)
    parser.add_argument("--worker", choices=MODELOS)
    parser.add_argument("--checkpoint")
    args = parser.parse_args()
    if not 1 <= args.threads <= 16:
        parser.error("Use entre 1 e 16 threads")
    args.saida = args.saida or RAIZ / "logs/bancada_embeddings" / datetime.now().strftime("%Y%m%d-%H%M%S")
    args.saida = args.saida.resolve()
    args.saida.mkdir(parents=True, exist_ok=True)
    if args.worker:
        if not args.checkpoint:
            parser.error("--worker exige --checkpoint")
        if (args.saida / f"{args.worker}.json").exists():
            raise FileExistsError("Escolha outro destino; resultado existente")
        worker(args)
        return
    if any((args.saida / f"{nome}.json").exists() for nome in MODELOS):
        raise FileExistsError("Escolha outro destino; resultados existentes")
    configurar_cpu(args.threads)
    validar_cenarios(json.loads(CENARIOS.read_text(encoding="utf-8")))
    import psutil
    gravar_json(args.saida / "manifesto.json", {
        "inicio": datetime.now().astimezone().isoformat(),
        "cenarios_sha256": hashlib.sha256(CENARIOS.read_bytes()).hexdigest(),
        "sistema": platform.platform(), "cpu": platform.processor(),
        "cpus_logicos": os.cpu_count(), "ram_total_gib": psutil.virtual_memory().total / 2**30,
        "threads": args.threads, "python": sys.version, "modelos": MODELOS,
    })
    modelos = {}
    for nome in MODELOS:
        result = args.saida / f"{nome}.json"
        if result.exists():
            raise FileExistsError(f"Não sobrescreve resultado existente: {result}")
        checkpoint = preparar_checkpoint(nome)
        subprocess.run([sys.executable, "-X", "utf8", "-u", "-m", "testes.bancada_embeddings",
                        "--worker", nome, "--checkpoint", checkpoint,
                        "--threads", str(args.threads), "--saida", str(args.saida)],
                       cwd=RAIZ, check=True)
        modelos[nome] = json.loads(result.read_text(encoding="utf-8"))
        relatorio(args.saida, modelos)
    print(f"Resultados: {args.saida}", flush=True)


if __name__ == "__main__":
    main()
