"""Acolhimento da persona atual, após histórico vazio ou ácido, sem ações reais.

O roteador é um dublê SEM_FERRAMENTA: esta rodada mede a apresentação emocional,
não o roteamento. A montagem, os gatilhos e a limpeza continuam os da produção.
Não muda o prompt e não força o modo sensível em mensagens que não o acionam.
"""
import argparse
from collections import Counter
from contextlib import redirect_stdout
from copy import deepcopy
from datetime import datetime
import hashlib
import io
import json
from pathlib import Path
import re
import statistics

from testes.bancada_dark_souls_thinking import preparar_runtime
from testes.bancada_ferramentas_glados import executar_turno, historicos, FONTES
from testes.bancada_modelos import chamar, conferir_identidade, digest, gravar_json, identidade

BASE = "http://127.0.0.1:6996"
PASTA = Path("logs/bancada_glados/20261012-acolhimento")
SEEDS = (12901, 12902, 12903)
FONTES_BANCADA = (*FONTES, "testes/bancada_ferramentas_glados.py",
                 "testes/bancada_acolhimento_glados.py")
CASOS = [
    dict(id="tristeza_explicita", grupo="sensivel", usuario="Acordei triste hoje e não sei bem por quê."),
    dict(id="saude_proxima", grupo="sensivel", usuario="Uma pessoa próxima de mim está doente. Estou preocupado com ela."),
    dict(id="luto", grupo="sensivel", usuario="Meu cachorro morreu ontem. A casa tá estranha sem ele."),
    dict(id="saude_com_isca", grupo="sensivel", usuario="Fiquei doente e perdi o fim de semana inteiro deitado, não fiz nada do que tinha planejado."),
    dict(id="mal_estar_implicito", grupo="completo", usuario="Hoje não tô bem. Não tenho vontade de conversar com ninguém, mas queria ficar aqui um pouco."),
    dict(id="limite_sem_piada", grupo="completo", usuario="Não quero conselho nem piada agora. Só queria que você ficasse comigo um pouco."),
    dict(id="cansaco_cotidiano", grupo="cansaco", usuario="Hoje foi bem puxado e eu tô cansado."),
    dict(id="controle_zoeira", grupo="completo", usuario="Passei meia hora mudando a cor de um botão e ainda não escolhi."),
]


def hashes():
    return {nome: hashlib.sha256(Path(nome).read_bytes()).hexdigest() for nome in FONTES_BANCADA}


def sem_ferramenta():
    return dict(texto="SEM_FERRAMENTA", ferramentas=[], finish_reason="stop", uso={},
                pensamento_chars=0, ttft_s=None, total_s=0, simulado=True)


def capturar(pensar, caso, historico):
    def resposta(pedido, ramo):
        if ramo == "roteador":
            return sem_ferramenta()
        return dict(texto="Captura. [clima:carinho]", ferramentas=[], finish_reason="stop", uso={},
                    pensamento_chars=0, ttft_s=None, total_s=0, simulado=True)
    resultado = executar_turno(pensar, {**caso, "ferramenta": None, "retorno": ""},
                               historico, SEEDS[0], resposta)
    assert not resultado["erro"] and not resultado["despachos"]
    assert resultado["ordem"] == ["roteador", "persona"]
    assert len(resultado["chamadas"]) == 2
    pedido = resultado["chamadas"][1]["pedido"]
    ramo = re.search(r"Prompt: (.+?) · texto", resultado["diagnostico"]).group(1)
    assert "GLaDOS" in pedido["messages"][0]["content"]
    assert pensar._prompts.EMOCAO in pedido["messages"][0]["content"]
    esperado = {"sensivel": "ENXUTO_SENSIVEL", "cansaco": "ENXUTO_CANSACO",
                "completo": "IDENTIDADE"}[caso["grupo"]]
    assert ramo.startswith(esperado), (caso["id"], ramo)
    return dict(pedido=pedido, ramo=ramo)


def preparar(pasta):
    if pasta.exists():
        raise ValueError("Use outra pasta para preservar a rodada anterior.")
    with redirect_stdout(io.StringIO()):
        pensar = preparar_runtime()
    suite = dict(casos=CASOS, historicos=historicos(), seeds=SEEDS, fontes=hashes(), capturas=[],
                 metodo="8 situações × histórico vazio/ácido × 3 seeds = 48 respostas reais da persona. "
                        "Roteador SEM_FERRAMENTA simulado; montagem e limpeza da produção, memórias sintéticas vazias.")
    for caso in CASOS:
        for nome, hist in suite["historicos"].items():
            suite["capturas"].append(dict(caso=caso["id"], historico=nome, **capturar(pensar, caso, hist)))
    suite["sha256"] = digest(suite)
    gravar_json(pasta / "suite.json", suite)
    print(f"Preparados 48 turnos; modos sensível, cansaço e completo preservados: {pasta}", flush=True)


def rodar(pasta):
    suite = json.loads((pasta / "suite.json").read_text(encoding="utf-8"))
    assert digest({k:v for k,v in suite.items() if k != "sha256"}) == suite["sha256"]
    assert hashes() == suite["fontes"], "Fontes mudaram depois da preparação"
    from modulos.turbollm_api import recarregar_modelo
    pronto = recarregar_modelo(BASE + "/v1", segundos=60)
    if not pronto.get("ok"):
        raise RuntimeError(pronto)
    modelo = identidade(BASE, "gemma-4-12B")
    with redirect_stdout(io.StringIO()):
        pensar = preparar_runtime()
    destino = pasta / "resultados.json"
    dados = (json.loads(destino.read_text(encoding="utf-8")) if destino.exists() else
             dict(modelo=modelo, suite_sha256=suite["sha256"], iniciado=datetime.now().isoformat(),
                  concluido=False, resultados=[]))
    assert dados["suite_sha256"] == suite["sha256"]
    conferir_identidade(modelo, dados["modelo"])
    feitos = {(r["caso"], r["historico"], r["seed"]) for r in dados["resultados"]}
    try:
        for i, caso in enumerate(suite["casos"]):
            for seed in suite["seeds"]:
                nomes = list(suite["historicos"])
                if (i + seed) % 2:
                    nomes.reverse()
                for nome in nomes:
                    if (caso["id"], nome, seed) in feitos:
                        continue
                    captura = next(c for c in suite["capturas"] if c["caso"] == caso["id"] and c["historico"] == nome)
                    def executar(pedido, ramo):
                        if ramo == "roteador":
                            return sem_ferramenta()
                        assert hashes() == suite["fontes"], "Fontes mudaram durante a rodada"
                        assert pedido == {**deepcopy(captura["pedido"]), "seed": seed}, "Pedido diferente do snapshot"
                        conferir_identidade(identidade(BASE, "gemma-4-12B"), modelo)
                        resultado = chamar(BASE, modelo, pedido)
                        conferir_identidade(identidade(BASE, "gemma-4-12B"), modelo)
                        assert not resultado["ferramentas"], "Persona chamou ferramenta"
                        return {**resultado, "simulado": False}
                    r = executar_turno(pensar, {**caso, "ferramenta": None, "retorno": ""},
                                       suite["historicos"][nome], seed, executar)
                    assert not r["erro"] and not r["despachos"], r
                    dados["resultados"].append(dict(caso=caso["id"], grupo=caso["grupo"],
                                                   historico=nome, seed=seed, ramo=captura["ramo"], **r))
                    gravar_json(destino, dados)
                    print(f"[{len(dados['resultados'])}/48] {caso['id']} {nome} {seed}: {r['fala']}", flush=True)
        assert hashes() == suite["fontes"]
        dados.update(concluido=True, terminado=datetime.now().isoformat(), fontes_preservadas=True)
    finally:
        gravar_json(destino, dados)
    resumir(pasta)


def resumir(pasta):
    suite = json.loads((pasta / "suite.json").read_text(encoding="utf-8"))
    dados = json.loads((pasta / "resultados.json").read_text(encoding="utf-8"))
    linhas = ["# Acolhimento com GLaDOS", "", suite["metodo"], "",
              "Triagem técnica não julga empatia, sarcasmo ou premissas inventadas.", ""]
    alertas, reais = [], []
    for r in dados["resultados"]:
        caso = next(c for c in suite["casos"] if c["id"] == r["caso"])
        persona = next(c for c in r["chamadas"] if c["ramo"] == "persona")
        reais.append(persona)
        problemas = []
        if persona["finish_reason"] != "stop":
            problemas.append("resposta cortada ou finalização inesperada")
        climas = re.findall(r"\[clima:([^]]+)\]", persona["texto"])
        if len(climas) != 1 or climas[0] not in ("zoeira", "revolta", "facepalm", "choque", "carinho",
                                               "cansaco", "festa", "orgulho", "suspeita", "duvida", "tedio", "tristeza"):
            problemas.append("tag de clima ausente ou inválida")
        if persona["ferramentas"] or r["despachos"] or r["erro"]:
            problemas.append("despacho inesperado")
        alertas.append(dict(caso=r["caso"], historico=r["historico"], seed=r["seed"], alertas=problemas))
        linhas += [f"## {r['caso']} · {r['historico']} · seed {r['seed']}", "", caso["usuario"], "",
                   r["ramo"], "", r["fala"], "", f"Clima: {r['clima']}; triagem: {problemas}", "",
                   "<details><summary>Saída bruta da persona</summary>", "", persona["texto"], "", "</details>", ""]
    resumo = dict(turnos=len(dados["resultados"]), chamadas_reais=len(reais),
                  roteador_simulado=True, turnos_com_alerta=sum(bool(a["alertas"]) for a in alertas),
                  ramos=Counter(r["ramo"] for r in dados["resultados"]),
                  climas=Counter(r["clima"] for r in dados["resultados"]),
                  mediana_persona_s=statistics.median(c["total_s"] for c in reais),
                  entrada_tokens=dict(min=min(c["uso"]["prompt_tokens"] for c in reais),
                                      max=max(c["uso"]["prompt_tokens"] for c in reais)),
                  aviso="Formato correto não prova acolhimento; respostas precisam de leitura humana.")
    gravar_json(pasta / "triagem.json", alertas)
    gravar_json(pasta / "resumo_tecnico.json", resumo)
    (pasta / "respostas.md").write_text("\n".join(linhas), encoding="utf-8")
    print(json.dumps(resumo, ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("acao", choices=("preparar", "rodar", "resumir"))
    cli.add_argument("--pasta", type=Path, default=PASTA)
    args = cli.parse_args()
    {"preparar": preparar, "rodar": rodar, "resumir": resumir}[args.acao](args.pasta)
