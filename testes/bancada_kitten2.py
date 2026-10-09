"""Bancada KittenTTS 2 x Kokoro: CPU, WAVs locais, sem iniciar a Luna."""
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
EMOCOES = {"morte": "[stern] ", "conquista": "[joyful] "}


def gravar(p, dados):
    p.write_text(json.dumps(dados, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--motor", choices=("kitten2", "kokoro"), required=True)
    parser.add_argument("--saida", type=Path, required=True)
    parser.add_argument("--caso", choices=("todos", *TEXTOS), default="todos")
    parser.add_argument("--threads", type=int, default=6)
    parser.add_argument("--somente-estavel", action="store_true")
    parser.add_argument("--modelo-local", type=Path, help="snapshot local para fixar a revisao dos pesos")
    args = parser.parse_args()
    saida = args.saida.resolve()
    saida.mkdir(parents=True, exist_ok=True)
    destino = saida / ("resultado_" + args.motor + ".json")
    if destino.exists():
        parser.error("Use outro --saida para preservar resultados anteriores.")
    # Os dois processos/venvs escrevem WAVs. Nenhum toca audio ou altera o motor da Luna.
    cache = RAIZ / "logs/cache_kitten2"
    if args.motor == "kitten2":
        os.environ["HF_HOME"] = str(cache)
        os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
        os.environ["TORCH_HOME"] = str(cache / "torch")
        os.environ["NUMBA_CACHE_DIR"] = str(cache / "numba")
        os.environ["HF_HUB_DISABLE_XET"] = "1"
    import numpy as np
    import soundfile as sf
    import torch
    torch.set_num_threads(args.threads)
    torch.set_num_interop_threads(1)
    pacotes = {}
    for nome in ("kittenml", "torch", "torchaudio", "transformers", "kokoro", "numpy", "soundfile"):
        try:
            pacotes[nome] = importlib.metadata.version(nome)
        except importlib.metadata.PackageNotFoundError:
            pass
    dados = {"criado_em": datetime.now().isoformat(), "motor": args.motor, "dispositivo": "cpu",
             "threads": args.threads, "plataforma": platform.platform(), "python": sys.version,
             "pacotes": pacotes, "amostras": [], "concluido": False,
             "fonte_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    gravar(destino, dados)
    casos = TEXTOS if args.caso == "todos" else {args.caso: TEXTOS[args.caso]}
    try:
        inicio = time.perf_counter()
        if args.motor == "kitten2":
            from kittenml import KittenTTS
            repositorio = str(args.modelo_local.resolve()) if args.modelo_local else "KittenML/kitten-tts-2"
            modelo = KittenTTS(repositorio, device="cpu", cache_dir=str(cache / "hub"),
                              weights="packed")
            dados.update(modelo="KittenML/kitten-tts-2", snapshot=repositorio, voz="Portuguese",
                         pesos="packed", decoder=modelo.decoder, dtype=str(modelo.dtype),
                         dispositivo_real=str(modelo.device), vozes=modelo.available_voices)
            assert str(modelo.device) == "cpu"
            assert "Portuguese" in modelo.available_voices
            sample_rate = modelo.sample_rate
            def gerar(texto, preset):
                return modelo.generate_stream(texto, voice="Portuguese", normalize=False,
                            preset=preset, advanced={"seed": 42}, max_new_tokens=750)
        else:
            from testes.bancada_tts import _configurar_espeak
            from kokoro import KPipeline
            _configurar_espeak()
            modelo = KPipeline(lang_code="p", device="cpu")
            sample_rate = 24000
            dados.update(modelo="Kokoro-82M", voz="af_nicole", velocidade=0.9,
                         dispositivo_real=str(modelo.model.device))
            def gerar(texto, preset):
                return (audio for _, _, audio in modelo(texto, voice="af_nicole", speed=0.9))
        dados["carga_e_download_s"] = time.perf_counter() - inicio
        gravar(destino, dados)
        print(f"Carregado {args.motor} em {dados['carga_e_download_s']:.1f}s", flush=True)
        rodadas = [(nome, texto, "stable", "") for nome, texto in casos.items()]
        if args.motor == "kitten2" and not args.somente_estavel:
            rodadas += [(nome, casos[nome], "expressive", tag) for nome, tag in EMOCOES.items()
                        if nome in casos]
        for nome, texto, preset, tag in rodadas:
            entrada = tag + texto
            print(f"Gerando {nome} / {preset}...", flush=True)
            inicio = time.perf_counter()
            partes, primeiro = [], None
            for parte in gerar(entrada, preset):
                if primeiro is None:
                    primeiro = time.perf_counter() - inicio
                if hasattr(parte, "detach"):
                    parte = parte.detach().cpu().numpy()
                audio = np.asarray(parte, dtype=np.float32).reshape(-1)
                if not len(audio) or not np.all(np.isfinite(audio)):
                    raise RuntimeError("Chunk de audio vazio ou nao finito.")
                partes.append(audio)
            total = time.perf_counter() - inicio
            if not partes:
                raise RuntimeError("O motor nao devolveu audio.")
            audio = np.concatenate(partes)
            pico = float(np.max(np.abs(audio)))
            if pico == 0:
                raise RuntimeError("O motor devolveu apenas silencio.")
            duracao = len(audio) / sample_rate
            arquivo = f"{args.motor}_{nome}_{preset}.wav"
            sf.write(saida / arquivo, audio, sample_rate, subtype="PCM_16")
            item = {"caso": nome, "texto": texto, "entrada": entrada, "preset": preset,
                    "voz": dados["voz"], "arquivo": arquivo, "primeiro_audio_s": primeiro,
                    "sintese_s": total, "audio_s": duracao, "rtf": total / duracao,
                    "sample_rate": sample_rate, "chunks": len(partes), "pico": pico,
                    "rms": float(np.sqrt(np.mean(audio ** 2)))}
            dados["amostras"].append(item)
            gravar(destino, dados)
            print(f"{arquivo}: primeiro={primeiro:.2f}s, total={total:.2f}s, "
                  f"audio={duracao:.2f}s, RTF={item['rtf']:.2f}", flush=True)
        dados["concluido"] = True
    except Exception as erro:
        dados["erro"] = repr(erro)
        raise
    finally:
        gravar(destino, dados)


if __name__ == "__main__":
    main()
