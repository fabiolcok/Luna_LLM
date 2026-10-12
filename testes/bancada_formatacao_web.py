"""A/B da apresentação web, com prompts reais e dados inteiramente sintéticos.

Não acessa memórias, não executa ferramentas e não inicia a Luna. Captura antes de
editar o prompt; repete os snapshots no modelo já carregado, com seeds iguais.
"""
import argparse
from contextlib import redirect_stdout
from copy import deepcopy
import io
import json
from pathlib import Path
import re
from unittest.mock import patch

from testes.bancada_dark_souls_thinking import preparar_runtime
from testes.bancada_modelos import chamar, conferir_identidade, digest, gravar_json, identidade

CASOS = [
    {"id": "comparacao", "usuario": "Compara essas duas opções para mim e diz qual combina com meu uso.",
     "tecnica": "DADOS SINTÉTICOS: modelo Aurora: 6 GB, 30 tokens/s, perde nuances de humor. "
                "Modelo Brisa: 9 GB, 18 tokens/s, preserva melhor nuances de humor. "
                "Uso: conversar enquanto jogo; placa de 12 GB. Consumo do jogo desconhecido."},
    {"id": "passos", "usuario": "A mensagem some da caixa e não aparece na conversa. Como verifico isso, passo a passo?",
     "tecnica": "DIAGNÓSTICO SINTÉTICO: a conexão WebSocket está fechada; o servidor não recebeu a mensagem. "
                "Após recarregar a página, a conexão volta. Não há erro de modelo nesse teste."},
    {"id": "codigo", "usuario": "Me mostra um exemplo pequeno em Python de como ler um JSON de um arquivo, e explica.",
     "tecnica": ""},
    {"id": "explicacao", "usuario": "Me explica a diferença entre o histórico da conversa e a memória permanente da Luna, e quando cada um ajuda.",
     "tecnica": "DADOS SINTÉTICOS: o histórico preserva os turnos recentes desta conversa; a memória "
                "permanente armazena fatos confirmados para conversas futuras. Não há tamanho ou prazo informado."},
    {"id": "comentario_leve", "usuario": "Hoje o jogo me deu uma surra, mas foi divertido.", "tecnica": "", "seeds": [901]},
    {"id": "saudacao_enxuta", "usuario": "oi, tudo bem?", "tecnica": "", "seeds": [901]},
]


def capturar(caso):
    pensar = preparar_runtime()
    from modulos import momento, tom
    pedido = {}

    class Capturado(BaseException):
        pass

    def interceptar(**kw):
        pedido.update(deepcopy(kw))
        raise Capturado()

    pensar._presenca_pc.set(True)
    pensar._ultima_saudacao_ts = 1e20
    pensar._kaomoji_recentes.clear()
    saida = io.StringIO()
    with (
        patch.object(pensar, "_chamar_llm", interceptar),
        patch.object(pensar, "MODO_PENSAMENTO", "desligado"),
        patch.object(pensar, "OPCOES_MODELO", {"chat_template_kwargs": {"enable_thinking": False}}),
        patch.object(pensar.obsidian, "ler_perfil", return_value="Gosta de jogos, humor exagerado e explicações claras."),
        patch.object(pensar.obsidian, "listar_memoria_episodica", return_value=[]),
        patch.object(pensar, "buscar_memoria_relevante", return_value=[]),
        patch.object(pensar, "buscar_contexto_relevante", return_value=""),
        patch.object(pensar.assuntos, "contexto_relacionado", return_value=""),
        patch.object(pensar, "ler_estado_luna", return_value={}),
        patch.object(pensar, "obter_janela_em_foco", return_value="Luna"),
        patch.object(tom, "obter_hint", return_value=""),
        patch.object(momento, "_jogos", {}),
        pensar.controle.executar() as execucao, redirect_stdout(saida),
    ):
        try:
            pensar._reescrever_como_luna(caso["tecnica"], caso["usuario"], [],
                                        max_tokens=800, responder_completo=True)
        except Capturado:
            pass
    if not pedido:
        raise RuntimeError(f"Não capturou {caso['id']}: {saida.getvalue()}")
    pedido.update(pedido.pop("extra_body", {}))
    pedido.update(stream=True, stream_options={"include_usage": True}, cache_prompt=False)
    pedido["messages"][0]["content"] = re.sub(
        r"^Hoje é .*", "Hoje é quinta-feira, 08/10/2026 10:00 (manhã).",
        pedido["messages"][0]["content"], count=1, flags=re.MULTILINE)
    ramo = getattr(execucao, "diagnostico", {}).get("caminho_prompt", "DESCONHECIDO")
    if caso["id"] == "saudacao_enxuta" and ramo != "ENXUTO_SAUDACAO":
        raise RuntimeError("A saudação não acionou o núcleo enxuto; não é um controle válido.")
    return {"id": caso["id"], "ramo": ramo, "pedido": pedido}


def preparar(pasta, variante):
    destino = pasta / f"{variante}.json"
    if destino.exists():
        raise ValueError("Snapshot já existe; escolha outra pasta.")
    if variante == "antes":
        for nome in ("modulos/prompts.py", "modulos/pensar.py", "templates/Index.html", "testes/prompt_golden.txt"):
            copia = pasta / "fontes_antes" / nome
            copia.parent.mkdir(parents=True, exist_ok=True)
            copia.write_bytes(Path(nome).read_bytes())
    gravar_json(destino, {"variante": variante, "casos": [capturar(c) for c in CASOS]})
    print(destino, flush=True)


def rodar(pasta):
    suites = {v: json.loads((pasta / f"{v}.json").read_text(encoding="utf8")) for v in ("antes", "depois")}
    snapshots = {v: digest(s) for v, s in suites.items()}
    modelo = identidade("http://127.0.0.1:6996", "gemma")
    destino = pasta / "resultados.json"
    dados = {"modelo": modelo, "snapshots": snapshots, "concluido": False, "resultados": []}
    if destino.exists():
        dados = json.loads(destino.read_text(encoding="utf8"))
        conferir_identidade(modelo, dados["modelo"])
        if snapshots != dados["snapshots"]:
            raise ValueError("Os snapshots mudaram; use outra pasta.")
    existentes = {(r["id"], r["seed"], r["variante"]) for r in dados["resultados"]}
    for n, caso in enumerate(CASOS):
        for seed in caso.get("seeds", [901, 902]):
            for variante in (("antes", "depois") if (n + seed) % 2 else ("depois", "antes")):
                if (caso["id"], seed, variante) in existentes:
                    continue
                conferir_identidade(identidade("http://127.0.0.1:6996", "gemma"), modelo)
                snapshot = next(c for c in suites[variante]["casos"] if c["id"] == caso["id"])
                pedido = deepcopy(snapshot["pedido"])
                pedido["seed"] = seed
                print(f"{caso['id']} / {seed} / {variante} / {snapshot['ramo']}", flush=True)
                resultado = chamar("http://127.0.0.1:6996", modelo, pedido)
                dados["resultados"].append({"id": caso["id"], "seed": seed, "variante": variante,
                                             "ramo": snapshot["ramo"], **resultado})
                gravar_json(destino, dados)
    dados["concluido"] = True
    gravar_json(destino, dados)
    print(destino, flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("acao", choices=["preparar", "rodar"])
    parser.add_argument("--pasta", type=Path, required=True)
    parser.add_argument("--variante", choices=["antes", "depois"], default="antes")
    args = parser.parse_args()
    preparar(args.pasta, args.variante) if args.acao == "preparar" else rodar(args.pasta)
