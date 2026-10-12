"""Repete jogos, proativos e ferramentas com TARS, preservando a rodada GLaDOS."""
import argparse
from contextlib import ExitStack
import hashlib
import json
from pathlib import Path
import re
from unittest.mock import patch

from testes import bancada_ferramentas_glados as ferramentas
from testes import bancada_proativos_glados as proativos

PASTA = Path("logs/bancada_tars/20261012-integracoes")
FONTES = ("modulos/prompts.py", "modulos/pensar.py", "modulos/proativa.py",
          "modulos/habilidades.py", "modulos/falar.py", "modulos/agenda_web.py",
          "modulos/fontes_conversa.py", "modulos/anotacoes.py", "modulos/momento.py",
          "modulos/rotina_jogos.py", "modulos/antirrepeticao.py", "testes/prompt_golden.txt",
          "testes/bancada_dark_souls_thinking.py", "testes/bancada_modelos.py",
          "testes/bancada_proativos_glados.py", "testes/bancada_ferramentas_glados.py",
          "testes/bancada_tars_integracoes.py",
          "logs/experimentos_prompt/20261012-glados/smoke.json",
          "logs/bancada_tars/20261012-piloto/resultados.json")


def hashes():
    return {f: hashlib.sha256(Path(f).read_bytes()).hexdigest() for f in FONTES}


def historicos():
    originais = ferramentas.historicos()
    piloto = json.loads(Path(FONTES[-1]).read_text(encoding="utf-8"))
    hist = []
    for caso in ("casual", "botao_morno"):
        r = next(r for r in piloto["resultados"] if r["caso"] == caso and r["seed"] == 13001)
        pedido = r["resultado"]["chamadas"][-1]["pedido"]
        hist.extend([dict(role="user", content=pedido["messages"][-1]["content"]),
                     dict(role="assistant", content=re.sub(r"\s*\[clima:[^]]+\]", "", r["fala"]).strip())])
    # Só a fala visível do usuário entra no histórico; instruções internas do turno
    # anterior alterariam o roteamento e deixariam de representar uma conversa.
    hist[0]["content"] = "eae"
    hist[2]["content"] = "Passei meia hora mudando a cor de um botão e ainda não escolhi."
    return {**originais, "historico_tars": hist}


def executar(acao, pasta):
    with ExitStack() as contexto:
        for modulo in (proativos, ferramentas):
            contexto.enter_context(patch.object(modulo, "hashes", hashes))
        if acao == "preparar":
            proativos.preparar(pasta / "proativos-jogos", personagem="TARS")
            ferramentas.preparar(pasta / "ferramentas", personagem="TARS", historicos_teste=historicos())
        elif acao == "proativos":
            proativos.rodar(pasta / "proativos-jogos")
        elif acao == "ferramentas":
            ferramentas.rodar(pasta / "ferramentas")
        else:
            proativos.resumir(pasta / "proativos-jogos")
            ferramentas.resumir(pasta / "ferramentas")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("acao", choices=("preparar", "proativos", "ferramentas", "resumir"))
    parser.add_argument("--pasta", type=Path, default=PASTA)
    args = parser.parse_args()
    executar(args.acao, args.pasta)
