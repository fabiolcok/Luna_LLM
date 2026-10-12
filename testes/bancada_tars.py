"""Piloto TARS: persona real, roteador simulado e nenhuma ação externa."""
from contextlib import redirect_stdout
from copy import deepcopy
import hashlib
import io
from pathlib import Path
import re

from testes.bancada_dark_souls_thinking import preparar_runtime
from testes.bancada_ferramentas_glados import executar_turno, historicos
from testes.bancada_acolhimento_glados import sem_ferramenta
from testes.bancada_proativos_glados import casos, gerar
from testes.bancada_modelos import chamar, conferir_identidade, gravar_json, identidade

BASE = "http://127.0.0.1:6996"
PASTA = Path("logs/bancada_tars/20261012-piloto")


def main():
    destino = PASTA / "resultados.json"
    if destino.exists():
        raise RuntimeError("Preserve a rodada anterior: escolha outra pasta.")
    modelo = identidade(BASE, "")
    with redirect_stdout(io.StringIO()):
        pensar = preparar_runtime()
    fonte = Path("modulos/prompts.py").read_bytes()
    dados = dict(modelo=modelo, prompt_sha256=hashlib.sha256(fonte).hexdigest(),
                 concluido=False, resultados=[])
    morno = [dict(role="user", content="oi"),
             dict(role="assistant", content="Olá! Como você está hoje?"),
             dict(role="user", content="tudo tranquilo"),
             dict(role="assistant", content="Que bom, fico feliz em saber.")]
    acido = next(h for h in historicos().values() if h)
    chats = [
        ("casual", "eae", []),
        ("saudacao", "oi, tudo bem?", []),
        ("botao_morno", "Passei meia hora mudando a cor de um botão e ainda não escolhi.", morno),
        ("tristeza", "Acordei triste hoje e não sei bem por quê.", []),
        ("luto", "Meu cachorro morreu ontem. A casa tá estranha sem ele.", []),
        ("saude", "Uma pessoa próxima de mim está doente. Estou preocupado com ela.", []),
        ("mal_estar", "Hoje não tô bem. Não tenho vontade de conversar com ninguém, mas queria ficar aqui um pouco.", []),
        ("sem_piada_acido", "Não quero conselho nem piada agora. Só queria que você ficasse comigo um pouco.", acido),
        ("cansaco", "Hoje foi bem puxado e eu tô cansado.", []),
        ("explicacao", "Qual a diferença entre RAM e VRAM?", []),
    ]

    def inferir(pedido):
        assert Path("modulos/prompts.py").read_bytes() == fonte
        sistema = pedido["messages"][0]["content"]
        assert "TARS" in sistema and "GLaDOS" not in sistema
        conferir_identidade(identidade(BASE, ""), modelo)
        resposta = chamar(BASE, modelo, deepcopy(pedido))
        conferir_identidade(identidade(BASE, ""), modelo)
        assert resposta["finish_reason"] == "stop" and not resposta["ferramentas"]
        return resposta

    def guardar(registro):
        dados["resultados"].append(registro)
        gravar_json(destino, dados)
        print(registro["caso"], registro["seed"], registro["fala"], flush=True)

    for seed in (13001, 13002):
        for nome, mensagem, hist in chats:
            def executar(pedido, ramo):
                return sem_ferramenta() if ramo == "roteador" else inferir(pedido)
            r = executar_turno(pensar, dict(id=nome, usuario=mensagem, ferramenta=None, retorno=""),
                               hist, seed, executar)
            assert not r["erro"] and not r["despachos"]
            persona = r["chamadas"][-1]
            ramo = re.search(r"Prompt: (.+?) · texto", r["diagnostico"]).group(1)
            guardar(dict(caso=nome, seed=seed, grupo="chat", ramo=ramo,
                         fala=persona["texto"], resultado=r))
        for caso in casos():
            if caso["id"] not in {"rss_gpu_rumor", "ds_morte", "ds_taurus"}:
                continue
            r = gerar(pensar, caso, seed, inferir)
            guardar(dict(caso=caso["id"], seed=seed, grupo="proativo", ramo=r["ramo"],
                         fala=r["fala"], resultado=r))
    dados["concluido"] = True
    gravar_json(destino, dados)
    linhas = ["# Respostas brutas — piloto TARS", ""]
    for r in dados["resultados"]:
        linhas.extend([f"## {r['caso']} / {r['seed']} / {r['ramo']}", "", r["fala"], ""])
    (PASTA / "respostas.md").write_text("\n".join(linhas), encoding="utf-8")


if __name__ == "__main__":
    main()
