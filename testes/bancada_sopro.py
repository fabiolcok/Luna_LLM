"""Mede Sopro em CPU e gera WAVs, sem importar ou iniciar a Luna."""
from __future__ import annotations

import argparse
from datetime import datetime
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import sys
import time

RAIZ = Path(__file__).resolve().parents[1]
TEXTOS = {
    "curta": "E aí? Dormiu bem ou acordou negociando com o despertador?",
    "morte": "Lordran devia pagar insalubridade pra você. Esse expediente tá um absurdo.",
    "conquista": "Agora sim! O Demônio Touro caiu. Esse castelo já pode atualizar a lista de funcionários.",
    "numeros": "Você jogou por duas horas e trinta e sete minutos. A promoção está por R$ 51,95.",
}
MODELO = "samuel-vitorino/sopro-v2-turbo"
REVISAO = "6c4aa6bba196ea3c8ee8e3e8b5dabe7a715fac92"


def gravar(path, dados):
    path.write_text(json.dumps(dados, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def configurar_cache():
    cache = RAIZ / "logs/cache_sopro"
    os.environ["HF_HOME"] = str(cache)
    os.environ["TORCH_HOME"] = str(cache / "torch")
    os.environ["HF_HUB_DISABLE_XET"] = "1"
    os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
    return cache


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ref", type=Path, required=True, help="WAV de referência de 5 a 20 segundos")
    parser.add_argument("--saida", type=Path, required=True)
    parser.add_argument("--modo", choices=("ambos", "offline", "stream"), default="ambos")
    parser.add_argument("--caso", choices=("todos", *TEXTOS), default="todos")
    parser.add_argument("--threads", type=int, default=6)
    parser.add_argument("--int8", action="store_true")
    parser.add_argument("--modelo-local", type=Path)
    args = parser.parse_args()
    if args.threads < 1:
        parser.error("--threads precisa ser positivo")
    referencia = args.ref.resolve()
    if not referencia.is_file():
        parser.error("Arquivo de referência não encontrado")
    saida = args.saida.resolve()
    saida.mkdir(parents=True, exist_ok=True)
    resultado = saida / ("resultado_sopro_int8.json" if args.int8 else "resultado_sopro.json")
    if resultado.exists():
        parser.error("Use outro --saida para preservar os resultados anteriores")
    cache = configurar_cache()
    import numpy as np
    import soundfile as sf
    import torch
    from sopro import SoproTTS
    torch.set_num_threads(args.threads)
    torch.set_num_interop_threads(1)
    info = sf.info(referencia)
    if not 5 <= info.duration <= 20:
        parser.error("A referência deve durar entre 5 e 20 segundos")
    dados = {
        "criado_em": datetime.now().astimezone().isoformat(), "modelo": MODELO,
        "revision": REVISAO if not args.modelo_local else None,
        "referencia": str(referencia.relative_to(RAIZ)) if referencia.is_relative_to(RAIZ) else referencia.name,
        "referencia_sha256": hashlib.sha256(referencia.read_bytes()).hexdigest(),
        "referencia_s": info.duration, "threads": args.threads, "device": "cpu",
        "quantization": "int8" if args.int8 else None, "python": sys.version,
        "plataforma": platform.platform(), "seed": 42, "lang": "pt",
        "pacotes": {p: importlib.metadata.version(p) for p in
                    ("sopro", "torch", "torchaudio", "numpy", "soundfile", "huggingface-hub")},
        "fonte_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "amostras": [], "concluido": False,
    }
    gravar(resultado, dados)
    try:
        inicio = time.perf_counter()
        modelo = SoproTTS.from_pretrained(
            str(args.modelo_local.resolve()) if args.modelo_local else MODELO,
            device="cpu", revision=None if args.modelo_local else REVISAO,
            cache_dir=str(cache / "hub"), quantization=dados["quantization"],
        )
        assert str(modelo.device) == "cpu"
        assert {str(p.device) for p in modelo.model.parameters()} == {"cpu"}
        dados["carga_e_download_s"] = time.perf_counter() - inicio
        dados["torch_cuda"] = torch.version.cuda
        dados["torch_hip"] = torch.version.hip
        dados["sample_rate"] = modelo.sample_rate
        dados["geracao_config"] = vars(modelo.generation)
        print(f"Carregado em {dados['carga_e_download_s']:.2f}s; CPU; {modelo.sample_rate} Hz", flush=True)
        modos = ("offline", "stream") if args.modo == "ambos" else (args.modo,)
        referencias = {}
        dados["preparo_referencia_s"] = {}
        for modo in modos:
            inicio = time.perf_counter()
            referencias[modo] = modelo.prepare_reference(ref_audio_path=referencia, stream=modo == "stream")
            dados["preparo_referencia_s"][modo] = time.perf_counter() - inicio
        # A referência já fica em memória; carga e aquecimento não entram na latência de cada frase.
        dados["aquecimento_s"] = {}
        for modo in modos:
            torch.manual_seed(41)
            inicio = time.perf_counter()
            opcoes = dict(ref=referencias[modo], lang="pt", max_seconds=20)
            if modo == "offline":
                modelo.synthesize(TEXTOS["curta"], **opcoes)
            else:
                list(modelo.stream(TEXTOS["curta"], **opcoes))
            dados["aquecimento_s"][modo] = time.perf_counter() - inicio
        gravar(resultado, dados)
        casos = TEXTOS if args.caso == "todos" else {args.caso: TEXTOS[args.caso]}
        for caso, texto in casos.items():
            for modo in modos:
                print(f"Gerando {caso} / {modo}...", flush=True)
                torch.manual_seed(42)
                inicio = time.perf_counter()
                opcoes = dict(ref=referencias[modo], lang="pt", max_seconds=20)
                partes, eventos = [], []
                if modo == "stream":
                    for chunk in modelo.stream(texto, **opcoes):
                        t = time.perf_counter() - inicio
                        audio = chunk.detach().cpu().float().numpy().reshape(-1)
                        if not audio.size or not np.isfinite(audio).all():
                            raise RuntimeError("Chunk vazio ou não finito")
                        partes.append(audio)
                        eventos.append({"emitido_s": t, "audio_s": len(audio) / modelo.sample_rate})
                    if not partes:
                        raise RuntimeError("Nenhum chunk produzido")
                    audio = np.concatenate(partes)
                else:
                    audio = modelo.synthesize(texto, **opcoes).detach().cpu().float().numpy().reshape(-1)
                total = time.perf_counter() - inicio
                if not audio.size or not np.isfinite(audio).all() or np.max(np.abs(audio)) == 0:
                    raise RuntimeError("Áudio vazio, não finito ou silencioso")
                duracao = len(audio) / modelo.sample_rate
                nome = f"sopro_{caso}_{modo}{'_int8' if args.int8 else ''}.wav"
                sf.write(saida / nome, audio, modelo.sample_rate, subtype="PCM_16")
                item = {"caso": caso, "texto": texto, "modo": modo, "arquivo": nome,
                        "sintese_s": total, "primeiro_audio_s": eventos[0]["emitido_s"] if eventos else total,
                        "audio_s": duracao, "rtf": total / duracao, "chunks": len(eventos) if eventos else 1,
                        "emissoes": eventos, "pico": float(np.max(np.abs(audio))),
                        "rms": float(np.sqrt(np.mean(audio ** 2)))}
                dados["amostras"].append(item)
                gravar(resultado, dados)
                print(f"{nome}: primeiro={item['primeiro_audio_s']:.2f}s; total={total:.2f}s; "
                      f"áudio={duracao:.2f}s; RTF={item['rtf']:.2f}", flush=True)
        dados["concluido"] = True
    except Exception as erro:
        dados["erro"] = repr(erro)
        raise
    finally:
        gravar(resultado, dados)


if __name__ == "__main__":
    main()
