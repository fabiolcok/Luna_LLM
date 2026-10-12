"""A/B dos exemplos de estilo, sem editar os prompts usados pela Luna.

Captura a montagem real com fontes sintéticas. Mantém EMOCAO, instruções,
histórico, sorteio e parâmetros nos pares. Histórico vazio e morno são grupos
separados; as tags de clima não substituem a leitura das falas.
"""
import argparse
from collections import Counter
from copy import deepcopy
from datetime import datetime
import hashlib
import json
from pathlib import Path
import random
import re
import statistics
import unicodedata
from unittest.mock import patch

from testes import bancada_conversa_casual as casual
from testes.bancada_dark_souls_thinking import preparar_runtime
from testes.bancada_modelos import chamar, conferir_identidade, digest, gravar_json, identidade

RAIZ = Path(__file__).resolve().parents[1]
BASE = "http://127.0.0.1:6996"
PASTA = RAIZ / "logs/bancada_casual/20261012-exemplos-tom"
EXEMPLOS = RAIZ / "testes/fixtures/exemplos_tom_sarcastico.json"
SEEDS = (12021, 12022)
PERFIL = "- Trabalha com suporte de sistemas.\n- Joga no PC."
HORARIO = "Hoje é 12/10/2026 10:00. Agora é MANHÃ. SÓ SE for cumprimentar, a saudação certa é 'bom dia'."
HISTORICO_MORNO = [
    {"role": "user", "content": "oi"},
    {"role": "assistant", "content": "Olá! Como você está hoje?"},
    {"role": "user", "content": "tudo tranquilo, sem nada específico"},
    {"role": "assistant", "content": "Que bom que está tudo tranquilo. Aproveitar esses momentos é importante."},
    {"role": "user", "content": "só queria conversar um pouco"},
    {"role": "assistant", "content": "Claro, estou aqui para conversar. Pode falar sobre qualquer coisa que quiser."},
]
CASOS = [
    ("cumprimento", "eae"),
    ("reciprocidade", "to bom e vc ?"),
    ("papo_sem_pedido", "nada so conversando"),
    ("botao", "Acabei de mudar a cor de um botão pela quarta vez e ainda não escolhi."),
    ("escolher_jogo", "Estou há meia hora escolhendo um jogo e ainda não comecei a jogar."),
    ("editar_prompt", "Mudei o seu prompt. Você ficou mais engraçada?"),
    ("explicacao", "Qual é a diferença entre RAM e VRAM? Explica de um jeito simples."),
]
CONTROLES = [
    ("agradecimento", "vlw"),
    ("sensivel", "tô triste hoje"),
]


def arquivos_producao():
    return {p: hashlib.sha256((RAIZ / p).read_bytes()).hexdigest()
            for p in ("modulos/prompts.py", "modulos/pensar.py", "modulos/falar.py",
                      "testes/prompt_golden.txt")}


def preparar(pasta, exemplos):
    if (pasta / "suite.json").exists():
        raise RuntimeError("Suite já existe; use outra pasta para uma nova comparação.")
    pensar = preparar_runtime()
    prompts = pensar._prompts
    atuais = deepcopy(prompts.EXEMPLOS_TOM)
    candidatos = json.loads(exemplos.read_text(encoding="utf-8"))
    # Manter as mesmas entradas isola a intensidade das respostas de exemplo.
    assert [e[0] for e in candidatos] == [e[0] for e in atuais]
    assert all(len(e) == 2 and all(isinstance(t, str) and t for t in e) for e in candidatos)
    suite = {"metodo": "7 casos x 2 históricos x 2 seeds x 2 variantes = 56 respostas completas; "
                       "2 controles enxutos x 2 seeds x 2 variantes = 8 respostas. "
                       "Só muda a resposta dos três exemplos selecionados. Sem ferramentas, áudio "
                       "ou memória real. Não simula a saudação obrigatória do primeiro turno do dia.",
             "horario_prompt": HORARIO, "perfil": PERFIL,
             "historico_morno": HISTORICO_MORNO, "seeds": SEEDS,
             "exemplos_atuais": atuais, "exemplos_candidatos": candidatos,
             "arquivos_producao": arquivos_producao(), "pares": []}
    grupos = [(nome, fala, grupo, hist, False) for nome, fala in CASOS
              for grupo, hist in (("vazio", []), ("morno", HISTORICO_MORNO))]
    grupos += [(nome, fala, "controle_enxuto", [], True) for nome, fala in CONTROLES]
    for nome, fala, grupo, historico, controle in grupos:
        for seed in SEEDS:
            # Usa o seletor da produção e restaura o RNG, sem afetar o aplicativo.
            estado = random.getstate()
            try:
                random.seed(seed)
                selecionados = prompts.sortear_exemplos_tom(fala)
            finally:
                random.setstate(estado)
            indices = [atuais.index(e) for e in selecionados]
            novos = [candidatos[i] for i in indices]
            with patch.object(casual, "PERFIL", PERFIL), patch.object(
                prompts, "sortear_exemplos_tom", return_value=selecionados
            ):
                atual = casual.capturar(pensar, {"id": nome, "usuario": fala,
                    "historico": deepcopy(historico)}, exigir_completo=not controle)
            atual["max_tokens"] = 500
            atual["messages"][0]["content"] = re.sub(
                r"^Hoje é .*", HORARIO, atual["messages"][0]["content"], count=1,
                flags=re.MULTILINE)
            alternativo = deepcopy(atual)
            bloco = prompts.bloco_exemplos_tom(selecionados)
            novo_bloco = prompts.bloco_exemplos_tom(novos)
            sistema = atual["messages"][0]["content"]
            if controle:
                assert bloco not in sistema
            else:
                assert sistema.count(bloco) == 1 and sistema.count(prompts.EMOCAO) == 1
                alternativo["messages"][0]["content"] = sistema.replace(bloco, novo_bloco, 1)
                assert sistema.replace(bloco, "", 1) == alternativo["messages"][0]["content"].replace(novo_bloco, "", 1)
            assert atual["messages"][1:] == alternativo["messages"][1:]
            assert {k: v for k, v in atual.items() if k != "messages"} == {
                k: v for k, v in alternativo.items() if k != "messages"}
            suite["pares"].append({"caso": nome, "usuario": fala, "grupo": grupo,
                "seed": seed, "indices_exemplos": indices,
                "pedidos": {"atual": atual, "sarcastico": alternativo}})
    suite["sha256"] = digest(suite)
    gravar_json(pasta / "suite.json", suite)
    print("Preparados", len(suite["pares"])*2, "pedidos; produção preservada.", flush=True)


def ler_suite(pasta):
    suite = json.loads((pasta / "suite.json").read_text(encoding="utf-8"))
    checksum = suite.pop("sha256")
    assert digest(suite) == checksum, "Snapshot foi alterado."
    return suite, checksum


def rodar(pasta):
    suite, checksum = ler_suite(pasta)
    modelo = identidade(BASE, "gemma-4-12B")
    arquivo = pasta / "resultados.json"
    dados = json.loads(arquivo.read_text(encoding="utf-8")) if arquivo.exists() else {
        "suite_sha256": checksum, "modelo": modelo,
        "inicio_local": datetime.now().astimezone().isoformat(),
        "concluido": False, "resultados": []}
    assert dados["suite_sha256"] == checksum
    conferir_identidade(modelo, dados["modelo"])
    feitos = {(r["caso"], r["grupo"], r["seed"], r["variante"]) for r in dados["resultados"]}
    for par in suite["pares"]:
        ordem = ("atual", "sarcastico") if par["seed"] % 2 else ("sarcastico", "atual")
        for variante in ordem:
            chave = (par["caso"], par["grupo"], par["seed"], variante)
            if chave in feitos:
                continue
            conferir_identidade(identidade(BASE, "gemma-4-12B"), modelo)
            pedido = {**deepcopy(par["pedidos"][variante]), "seed": par["seed"]}
            resultado = chamar(BASE, modelo, pedido)
            dados["resultados"].append({"caso": par["caso"], "grupo": par["grupo"],
                "seed": par["seed"], "variante": variante,
                "pedido_sha256": digest(pedido), **resultado})
            gravar_json(arquivo, dados)
            print(len(dados["resultados"]), "/", len(suite["pares"])*2,
                  *chave, resultado["texto"], flush=True)
    conferir_identidade(identidade(BASE, "gemma-4-12B"), modelo)
    assert arquivos_producao() == suite["arquivos_producao"], "Produção mudou durante a bancada."
    dados["concluido"] = True
    dados["fim_local"] = datetime.now().astimezone().isoformat()
    gravar_json(arquivo, dados)
    resumir(pasta)


def palavras(texto):
    texto = re.sub(r"\[clima:[^]]+\]", "", texto)
    texto = unicodedata.normalize("NFKD", texto.casefold())
    return re.findall(r"\w+", "".join(c for c in texto if not unicodedata.combining(c)))


def resumir(pasta):
    suite, checksum = ler_suite(pasta)
    dados = json.loads((pasta / "resultados.json").read_text(encoding="utf-8"))
    assert dados["suite_sha256"] == checksum
    linhas = ["# Comparação dos exemplos de tom", "", suite["metodo"], "",
              "Produção preservada. Tags e cópia são verificações técnicas; avaliar acidez e fatos pela leitura.", ""]
    for r in dados["resultados"]:
        par = next(p for p in suite["pares"] if (p["caso"], p["grupo"], p["seed"]) == (r["caso"], r["grupo"], r["seed"]))
        exemplos = suite["exemplos_atuais" if r["variante"] == "atual" else "exemplos_candidatos"]
        ws = palavras(r["texto"])
        cinco = {tuple(ws[i:i+5]) for i in range(len(ws)-4)}
        copias = []
        if r["grupo"] != "controle_enxuto":
            for indice in par["indices_exemplos"]:
                ex = palavras(exemplos[indice][1])
                comuns = cinco & {tuple(ex[i:i+5]) for i in range(len(ex)-4)}
                copias.extend(" ".join(s) for s in sorted(comuns))
        r["trechos_compartilhados_5_palavras"] = copias
        linhas += [f"## {r['caso']} · {r['grupo']} · {r['seed']} · {r['variante']}", "",
                   r["texto"], "", f"Geração: {r['total_s']:.2f}s · fim: {r['finish_reason']} · "
                   f"Trechos compartilhados: {', '.join(copias) or 'nenhum'}", ""]
    gravar_json(pasta / "leitura.json", dados)
    (pasta / "respostas.md").write_text("\n".join(linhas), encoding="utf-8")
    grupos = []
    for grupo in ("vazio", "morno", "controle_enxuto"):
        for variante in ("atual", "sarcastico"):
            itens = [r for r in dados["resultados"] if r["grupo"] == grupo and r["variante"] == variante]
            climas = Counter()
            for r in itens:
                tag = re.search(r"\[clima:([^]]+)\]\s*$", r["texto"])
                climas[tag.group(1) if tag else "ausente"] += 1
            grupos.append({"grupo": grupo, "variante": variante, "n": len(itens),
                "climas": dict(climas),
                "respostas_com_trecho_de_exemplo": sum(bool(r["trechos_compartilhados_5_palavras"]) for r in itens),
                "fim": dict(Counter(r["finish_reason"] for r in itens)),
                "com_ferramentas": sum(bool(r["ferramentas"]) for r in itens),
                "com_thinking": sum(bool(r["pensamento_chars"]) for r in itens),
                "mediana_geracao_s": statistics.median(r["total_s"] for r in itens) if itens else None,
                "tokens_entrada": [min(r["uso"]["prompt_tokens"] for r in itens),
                                  max(r["uso"]["prompt_tokens"] for r in itens)] if itens else [],
            })
            print(grupo, variante, "n=", len(itens), "mediana_s=",
                  round(statistics.median(r["total_s"] for r in itens),2) if itens else None)
    gravar_json(pasta / "resumo_tecnico.json", {"suite_sha256": checksum,
        "modelo": dados["modelo"], "inicio_local": dados["inicio_local"],
        "fim_local": dados.get("fim_local"), "grupos": grupos})


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("acao", choices=("preparar", "rodar", "resumir"))
    parser.add_argument("--pasta", type=Path, default=PASTA)
    parser.add_argument("--exemplos", type=Path, default=EXEMPLOS)
    args = parser.parse_args()
    if args.acao == "preparar":
        preparar(args.pasta, args.exemplos)
    else:
        {"rodar": rodar, "resumir": resumir}[args.acao](args.pasta)
