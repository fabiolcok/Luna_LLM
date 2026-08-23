"""Compara duas rodadas da bancada. É a peça que faltava para medir sem ajuda externa.

    # 1. antes de mexer em qualquer prompt
    .\\venv\\Scripts\\python.exe -X utf8 testes\\bancada_persona.py -r 3 --rotulo antes

    # 2. edita o prompt

    # 3. mesma coisa, outro rótulo
    .\\venv\\Scripts\\python.exe -X utf8 testes\\bancada_persona.py -r 3 --rotulo depois

    # 4. compara
    .\\venv\\Scripts\\python.exe -X utf8 testes\\comparar.py antes depois

Sem argumento nenhum, lista os rótulos que já existem no log. Com `--caminhos`, mostra por qual
prompt cada cenário passa — serve para saber QUAIS rodar antes de gastar tempo com os 40.

POR QUE ISSO IMPORTA: o placar total da bancada tem ruído de ~6 pontos em 102. Comparar totais
engana. O que decide é olhar só os cenários que a sua mudança toca, e é isso que este script
põe na frente.
"""

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

RAIZ = Path(__file__).parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))
LOG = RAIZ / "logs" / "bancada_persona.jsonl"


def carregar():
    if not LOG.exists():
        print("Não achei %s — rode a bancada pelo menos uma vez." % LOG)
        raise SystemExit(1)
    with LOG.open(encoding="utf-8") as f:
        return [json.loads(linha) for linha in f if linha.strip()]


def listar_rotulos(itens):
    por_rotulo = defaultdict(lambda: {"n": 0, "ok": 0, "quando": ""})
    for d in itens:
        r = por_rotulo[d.get("rotulo", "?")]
        r["n"] += 1
        r["ok"] += bool(d.get("ok"))
        r["quando"] = max(r["quando"], d.get("tempo", ""))
    print("%-38s %10s  %s" % ("rótulo", "placar", "última execução"))
    print("-" * 76)
    for nome, r in sorted(por_rotulo.items(), key=lambda kv: kv[1]["quando"]):
        print("%-38s %4d/%-5d  %s" % (nome, r["ok"], r["n"],
                                      r["quando"][:16].replace("T", " ")))
    print("\nPara comparar duas:  python testes/comparar.py <rótulo-antes> <rótulo-depois>")


def mostrar_caminhos():
    """Qual prompt cada cenário usa. Mudou o EMOCAO? Só os de PROMPT_COMPLETO sentem."""
    import contextlib
    import io
    import time
    from unittest.mock import patch

    from testes import bancada_persona as B
    from modulos import pensar, prompts

    class _Resp:
        class _Uso:
            completion_tokens = 5

        class _Msg:
            content = "ok [clima:zoeira]"
            reasoning_content = ""

        class _Escolha:
            message = None
            finish_reason = "stop"

        def __init__(self):
            escolha = self._Escolha()
            escolha.message = self._Msg()
            self.choices = [escolha]
            self.usage = self._Uso()

    # a montagem de cada prompt imprime o [🧩] e o [📏]; aqui isso seria só ruído
    por_caminho = defaultdict(list)
    silencio = io.StringIO()
    for cenario in B.CENARIOS:
        capturado = {}

        def duble(**parametros):
            capturado.setdefault("sistema", parametros["messages"][0]["content"])
            return _Resp()

        pensar._ultima_saudacao_ts = time.time()
        pensar._kaomoji_recentes.clear()
        pensar._presenca_pc.set(True)
        with (
            contextlib.redirect_stdout(silencio),
            patch.object(pensar, "_chamar_llm", duble),
            patch.object(pensar.obsidian, "ler_perfil", return_value=B.PERFIL_NEUTRO),
            patch.object(pensar.obsidian, "listar_memoria_episodica",
                         return_value=list(cenario.get("memorias", []))),
            patch.object(pensar, "buscar_memoria_relevante", return_value=[]),
            patch.object(pensar, "buscar_contexto_relevante",
                         return_value=cenario.get("chroma", "")),
            patch.object(pensar, "ler_estado_luna", return_value={}),
            patch.object(pensar, "obter_janela_em_foco", return_value="bancada"),
        ):
            pensar._reescrever_como_luna(
                cenario.get("tecnica", ""), cenario.get("usuario", ""),
                [dict(m) for m in cenario.get("historico", [])], max_tokens=200,
                forcar_incluir=cenario.get("forcar_incluir", False),
                responder_completo=cenario.get("responder_completo", True))
        sistema = capturado.get("sistema", "")
        nome = next((n for n in dir(prompts)
                     if n.startswith("ENXUTO_") and getattr(prompts, n) in sistema),
                    "PROMPT_COMPLETO")
        por_caminho[nome.replace("ENXUTO_", "")].append(cenario["id"])

    print("Mexeu num prompt? Rode SÓ os cenários da linha dele.\n")
    for caminho, ids in sorted(por_caminho.items(), key=lambda kv: -len(kv[1])):
        marca = ("   <- a persona (IDENTIDADE/EMOCAO/ESTRUTURA/LIMITES) só age aqui"
                 if caminho == "PROMPT_COMPLETO" else "")
        print("%-22s %s%s" % (caminho, ",".join(sorted(ids)), marca))
    print("\nExemplo:  bancada_persona.py -r 3 --rotulo antes --cenario " +
          ",".join(sorted(por_caminho.get("PROMPT_COMPLETO", []))[:3]) + ",...")


def comparar(itens, antes, depois):
    def fatiar(rotulo):
        por_cenario = defaultdict(lambda: [0, 0])          # [acertos, execuções]
        for d in itens:
            if d.get("rotulo") != rotulo:
                continue
            atual = por_cenario[d["cenario"]]
            atual[0] += bool(d.get("ok"))
            atual[1] += 1
        return por_cenario

    a, b = fatiar(antes), fatiar(depois)
    if not a:
        print("Não achei nenhuma execução com o rótulo '%s'." % antes)
        raise SystemExit(1)
    if not b:
        print("Não achei nenhuma execução com o rótulo '%s'." % depois)
        raise SystemExit(1)

    comuns = sorted(set(a) & set(b))
    if not comuns:
        print("As duas rodadas não têm cenário em comum — não dá para comparar.")
        raise SystemExit(1)

    mudou, piorou, melhorou = [], 0, 0
    for cid in comuns:
        taxa_a, taxa_b = a[cid][0] / a[cid][1], b[cid][0] / b[cid][1]
        if taxa_a != taxa_b:
            mudou.append((cid, a[cid], b[cid], taxa_b < taxa_a))
            if taxa_b < taxa_a:
                piorou += 1
            else:
                melhorou += 1

    print("%s  ->  %s\n" % (antes, depois))
    if mudou:
        print("%-34s %9s %9s" % ("cenário", antes[:9], depois[:9]))
        print("-" * 58)
        for cid, va, vb, caiu in mudou:
            print("%-34s %5d/%-3d %5d/%-3d  %s"
                  % (cid, va[0], va[1], vb[0], vb[1], "PIOROU" if caiu else "melhorou"))
    else:
        print("Nenhum cenário mudou de placar.")

    total_a = sum(v[1] for k, v in a.items() if k in comuns)
    ok_a = sum(v[0] for k, v in a.items() if k in comuns)
    total_b = sum(v[1] for k, v in b.items() if k in comuns)
    ok_b = sum(v[0] for k, v in b.items() if k in comuns)
    print("\nnos %d cenários em comum:   %d/%d  ->  %d/%d"
          % (len(comuns), ok_a, total_a, ok_b, total_b))

    print("\nCOMO LER ISTO")
    print("  O ruído da bancada é de ~6 pontos em 102. Um cenário que foi de 3/3 para 2/3 (ou o")
    print("  contrário) provavelmente é temperatura, não a sua mudança.")
    print("  O que decide: os cenários que a SUA mudança toca melhoraram ou pioraram?")
    print("  `--caminhos` diz quais são. Cenário que a mudança nem alcança aparecendo aqui é")
    print("  ruído — já aconteceu de uma 'queda' de 97/102 para 91/102 ser zero regressão, com")
    print("  todas as falhas em cenários cujo prompt era byte a byte o mesmo.")
    if piorou and not melhorou:
        print("\n  %d cenário(s) só pioraram — se algum for tocado pela mudança, desconfie."
              % piorou)


def main():
    ap = argparse.ArgumentParser(description="Compara duas rodadas da bancada da persona")
    ap.add_argument("antes", nargs="?", help="rótulo da rodada de referência")
    ap.add_argument("depois", nargs="?", help="rótulo da rodada nova")
    ap.add_argument("--caminhos", action="store_true",
                    help="mostra por qual prompt cada cenário passa (não usa o log)")
    args = ap.parse_args()

    if args.caminhos:
        mostrar_caminhos()
        return 0
    itens = carregar()
    if not args.antes or not args.depois:
        listar_rotulos(itens)
        return 0
    comparar(itens, args.antes, args.depois)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
