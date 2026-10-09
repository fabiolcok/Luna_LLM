"""Compara Kokoro e Pocket TTS sem alterar o motor de voz da Luna.

Gera os mesmos textos em WAV e registra latência, duração e velocidade. O Pocket
TTS é uma dependência opcional da bancada; ele não entra no requirements principal.
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import re
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path

import numpy as np
import soundfile as sf


RAIZ = Path(__file__).resolve().parents[1]
TEXTOS = {
    "curta": "E aí! Dormiu bem ou acordou negociando com o despertador?",
    "nomes_numeros": (
        "O Hollow Knight: Silksong ficou aberto por duas horas e trinta e sete minutos. "
        "Você desbloqueou 51,95% das conquistas e ainda faltam doze."
    ),
    "pontuacao": (
        "Sério? Você vai comprar outro jogo agora! A biblioteca já está pedindo uma "
        "intervenção, mas tudo bem... qual é o nome dele?"
    ),
    "longa": (
        "Terminei de organizar suas anotações. O projeto do servidor continua em andamento: "
        "a instalação funcionou, mas ainda falta configurar o backup e testar o acesso de "
        "outro computador. Não é uma emergência; é só mais uma dessas tarefas pequenas que "
        "entram na sala carregando uma prancheta e saem promovidas a obra de infraestrutura."
    ),
}


@dataclass
class Medicao:
    motor: str
    voz: str
    caso: str
    repeticao: int
    caracteres: int
    carga_s: float
    preparo_voz_s: float
    primeiro_audio_s: float
    sintese_s: float
    audio_s: float
    rtf: float
    vezes_tempo_real: float
    arquivo: str


def _configurar_espeak():
    import espeakng_loader
    from phonemizer.backend.espeak.wrapper import EspeakWrapper

    EspeakWrapper.set_library(espeakng_loader.get_library_path())
    try:
        EspeakWrapper.set_data_path(espeakng_loader.get_data_path())
    except Exception:
        pass


def _tensor_numpy(audio):
    if hasattr(audio, "detach"):
        audio = audio.detach().cpu().numpy()
    return np.asarray(audio, dtype=np.float32).squeeze()


def _rotulo_voz(voz):
    """Caminho de voz não pode vazar barras/dois-pontos para o nome do WAV."""
    nome = Path(str(voz)).stem if Path(str(voz)).suffix else str(voz)
    return re.sub(r"[^a-zA-Z0-9_-]+", "-", nome).strip("-") or "voz"


def _medir_fluxo(gerador, sample_rate):
    inicio = time.perf_counter()
    primeiro = None
    partes = []
    for parte in gerador:
        if primeiro is None:
            primeiro = time.perf_counter() - inicio
        partes.append(_tensor_numpy(parte))
    total = time.perf_counter() - inicio
    if not partes:
        raise RuntimeError("o motor não produziu áudio")
    wav = np.concatenate(partes)
    duracao = len(wav) / sample_rate
    return wav, primeiro or total, total, duracao


def _carregar_kokoro(voz):
    _configurar_espeak()
    from kokoro import KPipeline

    inicio = time.perf_counter()
    modelo = KPipeline(lang_code="p")
    carga = time.perf_counter() - inicio

    def gerar(texto):
        return (audio for _, _, audio in modelo(texto, voice=voz, speed=0.9))

    return gerar, 24000, carga, 0.0


def _carregar_pocket(voz, idioma, quantizado, temperatura=None):
    try:
        from pocket_tts import TTSModel
    except ImportError as exc:
        raise RuntimeError(
            "Pocket TTS não instalado. Rode: "
            r".\venv\Scripts\python.exe -m pip install -r testes\requirements_tts.txt"
        ) from exc

    inicio = time.perf_counter()
    opcoes = {"language": idioma, "quantize": quantizado}
    if temperatura is not None:
        opcoes["temp"] = temperatura
    modelo = TTSModel.load_model(**opcoes)
    carga = time.perf_counter() - inicio
    inicio_voz = time.perf_counter()
    estado_voz = modelo.get_state_for_audio_prompt(voz)
    preparo = time.perf_counter() - inicio_voz

    def gerar(texto):
        return modelo.generate_audio_stream(estado_voz, texto)

    return gerar, modelo.sample_rate, carga, preparo


def _resumo(medicoes):
    grupos = {}
    for item in medicoes:
        grupos.setdefault(item.motor, []).append(item)
    print("\nRESUMO (menor latência/RTF é melhor; maior x tempo real é melhor)")
    print("-" * 86)
    for motor, itens in grupos.items():
        media = lambda campo: sum(getattr(x, campo) for x in itens) / len(itens)
        print(
            f"{motor:24} carga={itens[0].carga_s:6.2f}s  "
            f"voz={itens[0].preparo_voz_s:6.2f}s  "
            f"1º áudio={media('primeiro_audio_s'):5.2f}s  "
            f"RTF={media('rtf'):5.2f}  "
            f"velocidade={media('vezes_tempo_real'):5.2f}x"
        )


def _normalizar_pasta(pasta, alvo_rms):
    """Cria cópias para comparação auditiva; os WAVs brutos continuam intocados."""
    pasta = pasta if pasta.is_absolute() else RAIZ / pasta
    destino = pasta / "normalizados"
    destino.mkdir(parents=True, exist_ok=True)
    arquivos = sorted(p for p in pasta.glob("*.wav") if not p.name.endswith("_normalizado.wav"))
    if not arquivos:
        raise RuntimeError(f"nenhum WAV encontrado em {pasta}")
    for arquivo in arquivos:
        wav, sample_rate = sf.read(arquivo, dtype="float32")
        rms = float(np.sqrt(np.mean(wav * wav))) if len(wav) else 0.0
        pico = float(np.max(np.abs(wav))) if len(wav) else 0.0
        ganho = alvo_rms / rms if rms else 1.0
        ganho = min(ganho, 0.95 / (pico or 1.0))
        saida = destino / f"{arquivo.stem}_normalizado.wav"
        sf.write(saida, np.clip(wav * ganho, -0.95, 0.95), sample_rate)
        print(f"{saida.name}: ganho {ganho:.2f}x")
    print(f"Cópias normalizadas: {destino}")


def main():
    parser = argparse.ArgumentParser(description="Bancada Kokoro x Pocket TTS")
    parser.add_argument("--motor", choices=("ambos", "kokoro", "pocket"), default="ambos")
    parser.add_argument("--kokoro-voz", default="af_nicole")
    parser.add_argument("--pocket-voz", default="rafael")
    parser.add_argument(
        "--pocket-idioma",
        choices=("portuguese", "portuguese_24l"),
        default="portuguese",
        help="portuguese é leve; portuguese_24l tem mais qualidade e custa mais CPU",
    )
    parser.add_argument("--quantizar-pocket", action="store_true")
    parser.add_argument(
        "--pocket-temperatura",
        type=float,
        help="sobrescreve a temperatura do Pocket (português usa 0.7 por padrão)",
    )
    parser.add_argument("--repeticoes", type=int, default=1)
    parser.add_argument("--caso", choices=("todos", *TEXTOS), default="todos")
    parser.add_argument("--saida", type=Path)
    parser.add_argument("--normalizar-pasta", type=Path, help="só cria cópias normalizadas dos WAVs da pasta")
    parser.add_argument("--normalizar-rms", type=float, default=0.049, help="RMS alvo da normalização")
    args = parser.parse_args()

    if args.repeticoes < 1:
        parser.error("--repeticoes precisa ser pelo menos 1")
    if args.normalizar_pasta:
        _normalizar_pasta(args.normalizar_pasta, args.normalizar_rms)
        return 0

    instante = datetime.now().strftime("%Y%m%d-%H%M%S")
    saida = args.saida or Path("logs") / "bancada_tts" / instante
    if not saida.is_absolute():
        saida = RAIZ / saida
    saida.mkdir(parents=True, exist_ok=True)
    casos = TEXTOS if args.caso == "todos" else {args.caso: TEXTOS[args.caso]}

    # Pocket exige NumPy 2 e a Luna fixa 1.26. Os dois motores rodam em processos/venvs
    # separados para a bancada nunca alterar silenciosamente o ambiente principal.
    if args.motor == "ambos":
        python_pocket = RAIZ / ".venv-tts" / "Scripts" / "python.exe"
        if not python_pocket.exists():
            print(
                "Ambiente isolado do Pocket não existe. Crie com:\n"
                r"  py -3.12 -m venv .venv-tts" "\n"
                r"  .\.venv-tts\Scripts\python.exe -m pip install -r testes\requirements_tts.txt",
                file=sys.stderr,
            )
            return 1

        comuns = [
            "--caso", args.caso,
            "--repeticoes", str(args.repeticoes),
            "--saida", str(saida),
        ]
        cmd_kokoro = [sys.executable, "-X", "utf8", str(Path(__file__).resolve()), "--motor", "kokoro",
                      "--kokoro-voz", args.kokoro_voz, *comuns]
        cmd_pocket = [str(python_pocket), "-X", "utf8", str(Path(__file__).resolve()), "--motor", "pocket",
                      "--pocket-voz", args.pocket_voz,
                      "--pocket-idioma", args.pocket_idioma, *comuns]
        if args.quantizar_pocket:
            cmd_pocket.append("--quantizar-pocket")
        if args.pocket_temperatura is not None:
            cmd_pocket.extend(("--pocket-temperatura", str(args.pocket_temperatura)))
        codigo_kokoro = subprocess.run(cmd_kokoro, cwd=RAIZ).returncode
        codigo_pocket = subprocess.run(cmd_pocket, cwd=RAIZ).returncode
        if codigo_kokoro == 0 and codigo_pocket == 0:
            reunidas = []
            for relatorio in saida.glob("resultado_*.json"):
                dados = json.loads(relatorio.read_text(encoding="utf-8"))
                reunidas.extend(Medicao(**item) for item in dados.get("medicoes", []))
            _resumo(reunidas)
            print(f"\nCompare os WAVs em: {saida}")
            return 0
        return 1

    motores = []
    if args.motor == "kokoro":
        motores.append(("kokoro", args.kokoro_voz, lambda: _carregar_kokoro(args.kokoro_voz)))
    if args.motor == "pocket":
        temp = f"-t{args.pocket_temperatura:g}" if args.pocket_temperatura is not None else ""
        nome = f"pocket-{args.pocket_idioma}{temp}{'-int8' if args.quantizar_pocket else ''}"
        motores.append(
            (nome, args.pocket_voz, lambda: _carregar_pocket(
                args.pocket_voz, args.pocket_idioma, args.quantizar_pocket,
                args.pocket_temperatura,
            ))
        )

    medicoes = []
    for nome_motor, voz, carregar in motores:
        print(f"\nCarregando {nome_motor} ({voz})...")
        try:
            gerar, sample_rate, carga, preparo = carregar()
        except Exception as exc:
            print(f"ERRO em {nome_motor}: {exc}", file=sys.stderr)
            if args.motor != "ambos":
                return 1
            continue

        for repeticao in range(1, args.repeticoes + 1):
            for nome_caso, texto in casos.items():
                print(f"  {nome_caso}, rodada {repeticao}...", end=" ", flush=True)
                wav, primeiro, total, duracao = _medir_fluxo(gerar(texto), sample_rate)
                arquivo = saida / f"{nome_motor}_{_rotulo_voz(voz)}_{nome_caso}_r{repeticao}.wav"
                sf.write(arquivo, wav, sample_rate)
                rtf = total / duracao if duracao else 0.0
                velocidade = duracao / total if total else 0.0
                item = Medicao(
                    motor=nome_motor,
                    voz=voz,
                    caso=nome_caso,
                    repeticao=repeticao,
                    caracteres=len(texto),
                    carga_s=round(carga, 4),
                    preparo_voz_s=round(preparo, 4),
                    primeiro_audio_s=round(primeiro, 4),
                    sintese_s=round(total, 4),
                    audio_s=round(duracao, 4),
                    rtf=round(rtf, 4),
                    vezes_tempo_real=round(velocidade, 4),
                    arquivo=str(arquivo.relative_to(RAIZ)),
                )
                medicoes.append(item)
                print(f"1º={primeiro:.2f}s · total={total:.2f}s · áudio={duracao:.2f}s · {velocidade:.2f}x")

    relatorio = {
        "gerado_em": datetime.now().isoformat(timespec="seconds"),
        "sistema": {"python": sys.version.split()[0], "plataforma": platform.platform()},
        "argumentos": vars(args) | {"saida": str(saida)},
        "medicoes": [asdict(x) for x in medicoes],
    }
    sufixo_relatorio = medicoes[0].motor if medicoes else args.motor
    (saida / f"resultado_{sufixo_relatorio}.json").write_text(
        json.dumps(relatorio, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    _resumo(medicoes)
    print(f"\nWAVs e resultado: {saida}")
    return 0 if medicoes else 1


if __name__ == "__main__":
    raise SystemExit(main())
