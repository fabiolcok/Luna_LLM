"""A/B de posição do EMOCAO e controle de histórico, sem alterar a Luna.

Captura a montagem real da persona com fontes sintéticas. A execução repete
snapshots no modelo já carregado, sem roteador, ferramentas, áudio ou embeddings.
"""
import argparse
from contextlib import redirect_stdout
from copy import deepcopy
import io
import json
from pathlib import Path
import re
import sys
from unittest.mock import patch

from testes.bancada_dark_souls_thinking import preparar_runtime
from testes.bancada_modelos import chamar, conferir_identidade, digest, gravar_json, identidade

PASTA = Path("logs/bancada_casual/20261011-generica")
BASE = "http://127.0.0.1:6996"
SEEDS = (11101, 11102, 11103)
PERFIL = "- Trabalha com suporte de sistemas.\n- Joga no PC."
HISTORICO = [
    {"role": "user", "content": "opa"},
    {"role": "assistant", "content": "Boa tarde! No que eu posso te ajudar agora?"},
    {"role": "user", "content": "nada so conversando"},
    {"role": "assistant", "content": "Aproveitar esse sossego é essencial, ainda mais com a sua semana de plantão chegando. É bom dar um tempo pro cérebro antes da correria começar de verdade."},
    {"role": "user", "content": "e o que faremos?"},
    {"role": "assistant", "content": "A gente pode só ficar no modo 'observação de vida' por um tempo. Se você não tem nenhum plano mirabolante agora, eu tô aqui pra ouvir qualquer coisa que passar pela sua cabeça ou pra eu te cutucar com alguma ideia aleatória."},
]
CASOS = [
    {"id": "saudacao_sem_historico", "usuario": "opa", "historico": []},
    {"id": "conversa_sem_pedido", "usuario": "nada so conversando", "historico": HISTORICO[:2]},
    {"id": "convite_com_historico_morno", "usuario": "e o que faremos?", "historico": HISTORICO[:4]},
    {"id": "encerramento", "usuario": "tendi vlw", "historico": HISTORICO},
    {"id": "plantao_concreto", "usuario": "ta tenso.... plantao ainda", "historico": [
        {"role": "user", "content": "ola"},
        {"role": "assistant", "content": "Boa tarde! Como é que tá esse ânimo hoje?"}]},
    # Mesma mensagem do convite, sem as respostas antigas: controle separado do A/B de posição.
    {"id": "convite_sem_historico", "usuario": "e o que faremos?", "historico": []},
]


def capturar(pensar, caso, *, exigir_completo=True):
    from modulos import momento, tom
    from modulos.biblioteca_web import contexto_resposta
    from modulos.novidades_web import contexto_novidade
    pedido = {}

    class Capturado(BaseException):
        pass

    def interceptar(**kw):
        pedido.update(deepcopy(kw))
        raise Capturado()

    token_resposta = contexto_resposta.set(None)
    token_novidade = contexto_novidade.set(None)
    pensar._presenca_pc.set(True)
    pensar._ultima_saudacao_ts = 1e20
    pensar._kaomoji_recentes.clear()
    try:
        with (
            patch.object(pensar, "_chamar_llm", interceptar),
            patch.object(pensar, "MODO_PENSAMENTO", "desligado"),
            patch.object(pensar, "OPCOES_MODELO", {"chat_template_kwargs": {"enable_thinking": False}}),
            patch.object(pensar.obsidian, "ler_perfil", return_value=PERFIL),
            patch.object(pensar.obsidian, "listar_memoria_episodica", return_value=[]),
            patch.object(pensar, "buscar_memoria_relevante", return_value=[]),
            patch.object(pensar, "buscar_contexto_relevante", return_value=""),
            patch.object(pensar.assuntos, "contexto_relacionado", return_value=""),
            patch.object(pensar, "ler_estado_luna", return_value={}),
            patch.object(pensar, "obter_janela_em_foco", return_value="Luna"),
            patch.object(tom, "obter_hint", return_value=""),
            patch.object(momento, "_jogos", {}),
            pensar.controle.executar() as execucao, redirect_stdout(io.StringIO()),
        ):
            try:
                pensar._reescrever_como_luna("", caso["usuario"], deepcopy(caso["historico"]),
                                            max_tokens=220, responder_completo=True)
            except Capturado:
                pass
    finally:
        contexto_resposta.reset(token_resposta)
        contexto_novidade.reset(token_novidade)
    if not pedido or (exigir_completo and execucao.diagnostico.get("caminho_prompt") != "PROMPT_COMPLETO"):
        raise RuntimeError("A bancada precisa capturar o prompt completo: " + caso["id"])
    pedido.update(pedido.pop("extra_body", {}))
    pedido.update(stream=True, stream_options={"include_usage": True}, cache_prompt=False)
    sistema = pedido["messages"][0]["content"]
    pedido["messages"][0]["content"] = re.sub(
        r"^Hoje é .*", "Hoje é 11/10/2026 17:00. É tarde.", sistema, count=1, flags=re.MULTILINE)
    return pedido


def mover_emocao(pedido, emocao):
    alternativo = deepcopy(pedido)
    sistema = pedido["messages"][0]["content"]
    marcador = "\nREGRA DE EVIDÊNCIA:"
    if sistema.count(emocao) != 1 or sistema.count(marcador) != 1:
        raise RuntimeError("O prompt mudou; revise a posição antes de experimentar.")
    sem_emocao = sistema.replace(emocao, "", 1)
    movido = sem_emocao.replace(marcador, emocao + marcador, 1)
    # A comparação deve mudar apenas a posição, preservando texto e regras de evidência.
    assert len(movido) == len(sistema)
    assert movido.replace(emocao, "", 1) == sem_emocao
    alternativo["messages"][0]["content"] = movido
    return alternativo


def preparar(pasta):
    pensar = preparar_runtime()
    suite = {"metodo": "6 casos x 3 seeds x 2 posições = 36 respostas; históricos fixos. "
                       "EMOCAO movido para antes da regra final de evidência, sem retirar regras. "
                       "Perfil sintético, fontes de memória vazias, sem mensagem antiga selecionada. "
                       "Controle de histórico muda também a orientação antirrepetição da produção.",
             "perfil": PERFIL, "seeds": SEEDS, "casos": []}
    for caso in CASOS:
        pedido = capturar(pensar, caso)
        alternativo = mover_emocao(pedido, pensar._prompts.EMOCAO)
        suite["casos"].append({**deepcopy(caso), "pedidos": {"atual": pedido, "emocao_no_fim": alternativo}})
    suite["sha256"] = digest(suite)
    gravar_json(pasta / "suite.json", suite)
    print("Snapshots prontos:", suite["sha256"], flush=True)


def rodar(pasta):
    suite = json.loads((pasta / "suite.json").read_text(encoding="utf-8"))
    hash_suite = suite.pop("sha256")
    if digest(suite) != hash_suite:
        raise RuntimeError("Snapshots mudaram; prepare outra rodada.")
    modelo = identidade(BASE, "gemma-4-12B")
    caminho = pasta / "resultados.json"
    dados = (json.loads(caminho.read_text(encoding="utf-8")) if caminho.exists()
             else {"suite_sha256": hash_suite, "modelo": modelo, "concluido": False, "resultados": []})
    if dados["suite_sha256"] != hash_suite:
        raise RuntimeError("Resultados pertencem a outros snapshots.")
    conferir_identidade(modelo, dados["modelo"])
    feitos = {(r["caso"], r["seed"], r["variante"]) for r in dados["resultados"]}
    for caso in suite["casos"]:
        for seed in suite["seeds"]:
            # Alternar a ordem entre seeds evita dar sempre o mesmo aquecimento a uma posição.
            ordem = ("atual", "emocao_no_fim") if seed % 2 else ("emocao_no_fim", "atual")
            for variante in ordem:
                if (caso["id"], seed, variante) in feitos:
                    continue
                conferir_identidade(identidade(BASE, "gemma-4-12B"), modelo)
                pedido = {**deepcopy(caso["pedidos"][variante]), "seed": seed}
                resultado = chamar(BASE, modelo, pedido)
                dados["resultados"].append({"caso": caso["id"], "seed": seed, "variante": variante,
                    "pedido_sha256": digest(pedido), **resultado})
                gravar_json(caminho, dados)
                print(caso["id"], seed, variante, resultado["texto"], flush=True)
    conferir_identidade(identidade(BASE, "gemma-4-12B"), modelo)
    dados["concluido"] = True
    gravar_json(caminho, dados)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("acao", choices=("preparar", "rodar"))
    parser.add_argument("--pasta", type=Path, default=PASTA)
    args = parser.parse_args()
    if args.acao == "preparar":
        if (args.pasta / "resultados.json").exists():
            sys.exit("A pasta já contém resultados; use outra pasta para novos snapshots.")
        preparar(args.pasta)
    else:
        rodar(args.pasta)
