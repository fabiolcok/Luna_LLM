"""Compara comentário, consulta útil e consulta sem evidência, sem acessar web ou memórias reais."""

import argparse
from contextlib import redirect_stdout
from copy import deepcopy
import hashlib
import io
import json
from pathlib import Path
import re
from types import ModuleType
from unittest.mock import patch

from testes.bancada_dark_souls_thinking import preparar_runtime
from testes.bancada_modelos import chamar, conferir_identidade, digest, gravar_json, identidade

BASE = "http://127.0.0.1:6996"
FONTES = ("modulos/intencao_gameplay.py", "modulos/habilidades.py", "modulos/pensar.py",
          "modulos/prompts.py", "testes/testa_prompt_montagem.py", "testes/prompt_golden.txt")
COMENTARIO = ("esse jogo parece bem menos cuidado do que o primeiro aion, os cratfts estao "
              "simplorios, a extracao conta como skill...")

# A mecânica abaixo é inventada para a fixture, não informação sobre o AION 2 real.
CASOS = [
    {"id": "comentario", "usuario": COMENTARIO,
     "busca": "AION 2: guia de builds e de combate. Não informa craft nem extração."},
    {"id": "pergunta_com_dados", "usuario": "Como funciona a extração no AION 2?",
     "busca": "FONTE SINTÉTICA DE TESTE — AION 2: para coletar, aproxime-se do recurso e "
              "ative Coleta. Cada coleta consome um ponto de energia. Não há dados sobre o primeiro Aion."},
    {"id": "pergunta_sem_evidencia", "usuario": "Por que simplificaram o craft e a extração no AION 2?",
     "busca": "AION 2: guia de builds e de combate. Não informa craft, extração nem motivo de design."},
    {"id": "busca_vazia", "usuario": "Como funciona a extração no AION 2?",
     "busca": "Aviso: A pesquisa não retornou nenhum resultado."},
    {"id": "erro_de_busca", "usuario": "Como funciona a extração no AION 2?",
     "busca": "Erro ao tentar acessar a internet: conexão indisponível na fixture."},
]


class Capturado(BaseException):
    pass


def capturar(caso):
    """Captura os pedidos reais de produção; fontes pessoais e pesquisa são fixtures."""
    pensar = preparar_runtime()
    from modulos import habilidades, momento, tom
    from modulos.intencao_gameplay import validar_pedido_gameplay
    memoria = ModuleType("modulos.memoria")
    memoria.ler_estado_luna = lambda: {}
    with (patch.dict("sys.modules", {"modulos.memoria": memoria}),
          patch.object(habilidades, "pesquisar_na_web", return_value=caso["busca"])):
        tecnica = (habilidades.duvida_do_jogo(caso["usuario"], "AION 2")
                   if validar_pedido_gameplay(caso["usuario"], caso["usuario"]) else "")

    pedidos = {}
    historia = [{"role": "user", "content": "Estou jogando AION 2."},
                {"role": "assistant", "content": "Como está sendo?"}]
    for ramo in ("roteador", "persona"):
        pedido = {}

        def interceptar(**kw):
            pedido.update(deepcopy(kw))
            raise Capturado()

        pensar._ultima_saudacao_ts = 1e20
        pensar._kaomoji_recentes.clear()
        saida = io.StringIO()
        with (
            patch.object(pensar, "_chamar_llm", interceptar),
            patch.object(pensar, "MODO_PENSAMENTO", "desligado"),
            patch.object(pensar, "OPCOES_MODELO", {"chat_template_kwargs": {"enable_thinking": False}}),
            patch.object(pensar.obsidian, "ler_perfil", return_value="Gosta de jogos e humor exagerado."),
            patch.object(pensar.obsidian, "listar_memoria_episodica", return_value=[]),
            patch.object(pensar.obsidian, "indice_notas", return_value=""),
            patch.object(pensar, "buscar_memoria_relevante", return_value=[]),
            patch.object(pensar, "buscar_contexto_relevante", return_value=""),
            patch.object(pensar.assuntos, "contexto_relacionado", return_value=""),
            patch.object(pensar, "ler_estado_luna", return_value={}),
            patch.object(pensar, "obter_janela_em_foco", return_value="AION 2"),
            patch.object(tom, "obter_hint", return_value=""),
            patch.object(momento, "_jogos", {}),
            pensar.controle.executar(),
            redirect_stdout(saida),
        ):
            momento.observar_jogos("processos", ["AION 2"])
            try:
                if ramo == "roteador":
                    pensar.gerar_resposta(caso["usuario"], deepcopy(historia), salvar=False,
                                         responder_completo=True)
                else:
                    pensar._reescrever_como_luna(tecnica, caso["usuario"], deepcopy(historia),
                                                max_tokens=300, responder_completo=True)
            except Capturado:
                pass
        if not pedido:
            raise RuntimeError(f"Não capturou {ramo}/{caso['id']}: {saida.getvalue()}")
        pedido.update(pedido.pop("extra_body", {}))
        pedido.update(stream=True, stream_options={"include_usage": True}, cache_prompt=False)
        if ramo == "persona":
            # O relógio não deve oferecer uma diferença extra entre os braços do A/B.
            pedido["messages"][0]["content"] = re.sub(
                r"^Hoje é .*", "Hoje é quinta-feira, 08/10/2026 10:00 (manhã).",
                pedido["messages"][0]["content"], count=1, flags=re.MULTILINE)
        pedidos[ramo] = pedido
    return {"cenario": caso, "tecnica": tecnica, "pedidos": pedidos,
            "guard_aceita": validar_pedido_gameplay(caso["usuario"], caso["usuario"])}


def preparar(pasta, variante):
    destino = pasta / f"{variante}.json"
    if destino.exists():
        raise ValueError("Snapshot já existe; use outra pasta para preservar a comparação.")
    fontes = {f: hashlib.sha256(Path(f).read_bytes()).hexdigest() for f in FONTES}
    if variante == "antes":
        for f in FONTES:
            copia = pasta / "fontes_antes" / f
            copia.parent.mkdir(parents=True, exist_ok=True)
            copia.write_bytes(Path(f).read_bytes())
    gravar_json(destino, {"variante": variante, "fontes": fontes,
                         "casos": [capturar(c) for c in CASOS]})
    print(destino, flush=True)


def rodar(pasta, candidato="depois"):
    comparacao = candidato == "depois"
    variantes = ("antes", "depois") if comparacao else (candidato,)
    suites = {v: json.loads((pasta / f"{v}.json").read_text(encoding="utf8"))
              for v in variantes}
    for f in FONTES[:4]:
        if hashlib.sha256(Path(f).read_bytes()).hexdigest() != suites[candidato]["fontes"][f]:
            raise ValueError(f"Produção mudou depois da captura: {f}")
    snapshots = {v: digest(s) for v, s in suites.items()}
    modelo = identidade(BASE, "gemma-4-12B")
    destino = pasta / ("resultados.json" if comparacao else f"resultados-{candidato}.json")
    dados = {"modelo": modelo, "snapshots": snapshots, "seeds": [801, 802],
             "concluido": False, "resultados": []}
    if destino.exists():
        dados = json.loads(destino.read_text(encoding="utf8"))
        conferir_identidade(modelo, dados["modelo"])
        if dados.get("snapshots") != snapshots:
            raise ValueError("Os prompts mudaram desde a rodada anterior; use outra pasta.")
    existentes = {(r["caso"], r["seed"], r["variante"], r["ramo"]) for r in dados["resultados"]}
    for i, caso in enumerate(CASOS):
        for seed in dados["seeds"]:
            for variante in (variantes if (i + seed) % 2 else tuple(reversed(variantes))):
                snapshot = next(c for c in suites[variante]["casos"] if c["cenario"]["id"] == caso["id"])
                for ramo in ("persona", "roteador"):
                    # Roteador não mudou o prompt; basta medir o candidato nos três casos centrais.
                    if ramo == "roteador" and (not comparacao or variante == "antes" or i >= 3):
                        continue
                    chave = (caso["id"], seed, variante, ramo)
                    if chave in existentes:
                        continue
                    conferir_identidade(identidade(BASE, "gemma-4-12B"), modelo)
                    pedido = deepcopy(snapshot["pedidos"][ramo])
                    pedido["seed"] = seed
                    print(f"{caso['id']} / {seed} / {variante} / {ramo}", flush=True)
                    resultado = chamar(BASE, modelo, pedido)
                    registro = {"caso": caso["id"], "seed": seed, "variante": variante,
                                "ramo": ramo, "guard_aceita": snapshot["guard_aceita"], **resultado}
                    if ramo == "roteador":
                        from modulos.intencao_gameplay import validar_pedido_gameplay
                        registro["gameplay_autorizado"] = any(
                            c["name"] == "duvida_do_jogo" and validar_pedido_gameplay(
                                caso["usuario"], json.loads(c["arguments"]).get("trecho_pedido", ""))
                            for c in resultado["ferramentas"])
                    dados["resultados"].append(registro)
                    gravar_json(destino, dados)
    dados["concluido"] = True
    gravar_json(destino, dados)
    linhas = ["# Bancada de conversa e dúvida de jogo", "",
              ("A/B de persona: mesmas situações, duas seeds e histórico fixo; ordem alternada."
               if comparacao else f"Rodada exploratória do candidato {candidato}: mesmas situações, duas seeds e histórico fixo."),
              "Pesquisa simulada e dados sintéticos: não comprovam mecânicas reais do AION 2.",
              "Roteador real medido somente no candidato; o guard é aplicado às chamadas, sem executar ferramentas.",
              "Humor e sustentação factual precisam de leitura humana. Sem TTS ou medição de FPS.", ""]
    for r in dados["resultados"]:
        linhas += [f"## {r['caso']} — {r['variante']} — seed {r['seed']} — {r['ramo']}", "",
                   f"{r['total_s']:.1f}s; finish_reason: {r['finish_reason']}; guard: {r['guard_aceita']}",
                   "", r["texto"] or "(tool call)", ""]
        if r["ferramentas"]:
            linhas += [json.dumps(r["ferramentas"], ensure_ascii=False), ""]
    destino.with_suffix(".md").write_text("\n".join(linhas), encoding="utf8")
    print(destino, flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pasta", type=Path)
    parser.add_argument("--preparar", choices=("antes", "depois", "calibrado", "final", "selecionado", "sistema", "entrega"))
    parser.add_argument("--calibrado", action="store_true")
    parser.add_argument("--rodada", choices=("depois", "calibrado", "final", "selecionado", "sistema", "entrega"), default="depois")
    args = parser.parse_args()
    if args.preparar:
        preparar(args.pasta, args.preparar)
    else:
        rodar(args.pasta, "calibrado" if args.calibrado else args.rodada)
