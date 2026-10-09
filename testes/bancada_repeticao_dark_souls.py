"""Sequencia de mortes com memoria propria, sem audio e sem trocar o modelo."""
import argparse
from datetime import datetime
import hashlib
from pathlib import Path

from testes.bancada_dark_souls_thinking import BASE, gerar_turno, preparar_runtime
from testes.bancada_modelos import chamar, conferir_identidade, gravar_json, identidade

INICIAL = ("Essa morte foi tão eficiente que parece que o personagem decidiu que a vida era "
           "opcional e resolveu apenas se retirar do plano físico por pura conveniência.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mortes", type=int, default=8)
    parser.add_argument("--modelo", default="gemma-4-12B")
    parser.add_argument("--destino", type=Path)
    args = parser.parse_args()
    if not 1 <= args.mortes <= 20:
        parser.error("--mortes deve estar entre 1 e 20")
    destino = args.destino or Path("logs/dark_souls") / datetime.now().strftime("repeticao-%Y%m%d-%H%M%S.json")
    if destino.exists():
        parser.error("Use outro destino para preservar a rodada anterior.")
    pensar = preparar_runtime()
    modelo = identidade(BASE, args.modelo)
    dados = {"modelo": modelo, "concluido": False, "fala_inicial": INICIAL,
             "fontes_sha256": {f: hashlib.sha256(Path(f).read_bytes()).hexdigest() for f in
                              ("modulos/proativa.py", "modulos/prompts.py", "modulos/antirrepeticao.py",
                               "testes/bancada_dark_souls_thinking.py")},
             "resultados": []}
    recentes, mortes = [INICIAL[:120]], [INICIAL]
    print("Resultados:", destino, flush=True)
    try:
        for n in range(args.mortes):
            conferir_identidade(identidade(BASE, args.modelo), modelo)
            def executar(pedido):
                conferir_identidade(identidade(BASE, args.modelo), modelo)
                resultado = chamar(BASE, modelo, pedido)
                conferir_identidade(identidade(BASE, args.modelo), modelo)
                return resultado
            r = gerar_turno(pensar, {"tipo": "morte", "nome": "", "mortes_sessao": n + 1,
                                    "incremento": 1}, recentes, "desligado", 57 + n,
                            1790526252.4361274, executar, mortes_recentes=mortes)
            dados["resultados"].append(r)
            gravar_json(destino, dados)
            print(f"{n+1}: {len(r['tentativas'])} chamada(s), {r['total_s']:.1f}s | "
                  + (r["fala"] or "(descartada)"), flush=True)
        dados["concluido"] = True
    finally:
        gravar_json(destino, dados)


if __name__ == "__main__":
    main()
