"""Compara a conversa comum antes/depois, com controles dos modos enxutos.

Congela pedidos reais com fontes sintéticas; não inicia Luna, ferramentas,
áudio ou embeddings. A execução usa somente o Gemma já carregado.
"""
import argparse
from copy import deepcopy
import json
from pathlib import Path
from unittest.mock import patch

from testes import bancada_conversa_casual as casual
from testes.bancada_dark_souls_thinking import preparar_runtime
from testes.bancada_modelos import chamar, conferir_identidade, digest, gravar_json, identidade

BASE = "http://127.0.0.1:6996"
PASTA = Path("logs/bancada_casual/20261011-conversa-completa")
PERFIL = "- Trabalha com suporte de sistemas.\n- Foco da semana: só vivendo.\n- Hoje está tranquilo."
SEEDS = (21101, 21102)
CASOS = [
    {"id": "abertura", "usuario": "eae", "historico": []},
    {"id": "sem_pedido", "usuario": "nada so conversando", "historico": casual.HISTORICO[:2]},
    {"id": "convite", "usuario": "e o que faremos?", "historico": casual.HISTORICO[:4]},
    {"id": "reciprocidade", "usuario": "to bom e vc ?", "historico": [
        {"role": "user", "content": "eae"},
        {"role": "assistant", "content": "Boa noite. Como é que você tá?"}]},
    {"id": "situacao_leve", "usuario": "Passei quarenta minutos escolhendo um jogo e perdi a vontade de jogar.", "historico": []},
    {"id": "explorar_ideia", "usuario": "Acho mais fácil criar ideias pra Luna do que ter vontade de conversar com ela. O que faz uma conversa render de verdade?", "historico": []},
    {"id": "encerramento", "usuario": "por hoje é isso, vou sair", "historico": casual.HISTORICO[:4]},
    {"id": "controle_agradecimento", "usuario": "vlw", "historico": [], "controle": True},
    {"id": "controle_sensivel", "usuario": "tô triste hoje", "historico": [], "controle": True},
]


def capturar():
    pensar = preparar_runtime()
    casos = []
    with patch.object(casual, "PERFIL", PERFIL):
        for caso in CASOS:
            pedido = casual.capturar(pensar, caso, exigir_completo=not caso.get("controle"))
            # O orçamento é igual nos pares; comprimento não pode ser limitado pela bancada.
            pedido["max_tokens"] = 500
            casos.append({**deepcopy(caso), "pedido": pedido})
    return casos


def congelar(pasta):
    caminho = pasta / "antes.json"
    if caminho.exists():
        raise RuntimeError("Snapshot anterior já existe; use outra pasta para não substituí-lo.")
    casos = capturar()
    gravar_json(caminho, {"perfil": PERFIL, "casos": casos, "sha256": digest(casos)})
    print("Antes congelado:", caminho, flush=True)


def preparar(pasta):
    antes = json.loads((pasta / "antes.json").read_text(encoding="utf-8"))
    if digest(antes["casos"]) != antes["sha256"]:
        raise RuntimeError("Snapshot anterior foi alterado.")
    if (pasta / "suite.json").exists():
        raise RuntimeError("Comparação já existe; não substitua uma rodada preparada.")
    atuais = {c["id"]: c for c in capturar()}
    suite = {"metodo": "9 casos x 2 seeds x 2 variantes. Históricos fixos; fontes sintéticas. "
                       "Sete casos completos e dois controles enxutos; analisar separadamente.",
             "seeds": SEEDS, "casos": []}
    for anterior in antes["casos"]:
        atual = atuais[anterior["id"]]
        a, b = anterior["pedido"], atual["pedido"]
        # A calibração só muda a orientação final do papo comum, mantendo a persona.
        assert a["messages"][:-1] == b["messages"][:-1], anterior["id"]
        assert {k: v for k, v in a.items() if k != "messages"} == {
            k: v for k, v in b.items() if k != "messages"}, anterior["id"]
        if anterior.get("controle"):
            assert a == b, anterior["id"]
        suite["casos"].append({k: deepcopy(v) for k, v in anterior.items() if k != "pedido"} | {
            "pedidos": {"antes": a, "ajustado": b}})
    suite["sha256"] = digest(suite)
    gravar_json(pasta / "suite.json", suite)
    print("Comparação preparada:", suite["sha256"], flush=True)


def rodar(pasta):
    suite = json.loads((pasta / "suite.json").read_text(encoding="utf-8"))
    hash_suite = suite.pop("sha256")
    if digest(suite) != hash_suite:
        raise RuntimeError("Pedidos da comparação foram alterados.")
    modelo = identidade(BASE, "gemma-4-12B")
    caminho = pasta / "resultados.json"
    dados = (json.loads(caminho.read_text(encoding="utf-8")) if caminho.exists() else {
        "suite_sha256": hash_suite, "modelo": modelo, "concluido": False, "resultados": []})
    if dados["suite_sha256"] != hash_suite:
        raise RuntimeError("Resultados são de outra comparação.")
    conferir_identidade(modelo, dados["modelo"])
    feitos = {(r["caso"], r["seed"], r["variante"]) for r in dados["resultados"]}
    for caso in suite["casos"]:
        for seed in suite["seeds"]:
            ordem = ("antes", "ajustado") if seed % 2 else ("ajustado", "antes")
            for variante in ordem:
                if (caso["id"], seed, variante) in feitos:
                    continue
                conferir_identidade(identidade(BASE, "gemma-4-12B"), modelo)
                pedido = {**deepcopy(caso["pedidos"][variante]), "seed": seed}
                resultado = chamar(BASE, modelo, pedido)
                dados["resultados"].append({"caso": caso["id"], "controle": caso.get("controle", False),
                    "seed": seed, "variante": variante, "pedido_sha256": digest(pedido), **resultado})
                gravar_json(caminho, dados)
                print(caso["id"], seed, variante, resultado["texto"], flush=True)
    conferir_identidade(identidade(BASE, "gemma-4-12B"), modelo)
    dados["concluido"] = True
    gravar_json(caminho, dados)
    print("Concluído; respostas completas em", caminho, flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("acao", choices=("congelar", "preparar", "rodar"))
    parser.add_argument("--pasta", type=Path, default=PASTA)
    args = parser.parse_args()
    {"congelar": congelar, "preparar": preparar, "rodar": rodar}[args.acao](args.pasta)
