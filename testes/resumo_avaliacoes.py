"""Relatório local; não chama LLM nem altera os votos ou prompts."""
import argparse
from collections import Counter
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from modulos.avaliacoes import ARQUIVO, ler_consolidadas


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--arquivo", type=Path, default=ARQUIVO)
    ap.add_argument("--ultimas", type=int, default=8)
    args = ap.parse_args()
    registros = ler_consolidadas(args.arquivo)
    votos = Counter(r.get("rating", "sem voto") for r in registros)
    categorias = Counter(c for r in registros for c in r.get("categorias", []))
    print(f"{len(registros)} avaliações consolidadas: {votos['bom']} boas, {votos['ruim']} ruins.")
    print("Complementos V2 contam uma vez; registros antigos permanecem como foram gravados.")
    print("\nCategorias (uma resposta pode ter mais de uma):")
    for categoria, n in categorias.most_common():
        print(f"  {categoria}: {n}")
    print("\nPor caminho de prompt:")
    caminhos = Counter((r.get("contexto", {}).get("caminho_prompt", "sem diagnóstico"), r.get("rating"))
                       for r in registros)
    for (caminho, rating), n in sorted(caminhos.items(), key=lambda item: str(item[0])):
        print(f"  {caminho} / {rating}: {n}")
    if args.ultimas > 0:
        print("\nÚltimas avaliações com motivo:")
        for registro in [r for r in registros if r.get("motivo")][-args.ultimas:]:
            print(f"  {registro.get('tempo', '?')} [{registro.get('rating')}] {registro['motivo']}")


if __name__ == "__main__":
    main()
