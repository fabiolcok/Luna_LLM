"""Ativação e diagnóstico do piloto, sem iniciar Luna, voz ou Telegram."""
import argparse
import json
import time
from modulos.dark_souls import RAIZ, Monitor, habilitado, configurar


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("acao", choices=["ativar", "desativar", "status", "observar"])
    parser.add_argument("--segundos", type=int, default=20)
    args = parser.parse_args()
    if args.acao in {"ativar", "desativar"}:
        configurar(args.acao == "ativar")
    if args.acao != "observar":
        print("Piloto Remastered: " + ("ativado" if habilitado() else "desativado"))
        if args.acao == "ativar":
            print("Na primeira instalação, reinicie a Luna para carregar o monitor.")
        return
    if not 1 <= args.segundos <= 3600:
        parser.error("--segundos deve estar entre 1 e 3600")
    from integracoes.dark_souls.leitor import LeitorRemastered
    leitor, monitor = LeitorRemastered(), Monitor()
    destino = RAIZ / "logs/dark_souls/diagnostico.jsonl"
    destino.parent.mkdir(parents=True, exist_ok=True)
    inicio = time.monotonic()
    primeiro = True
    try:
        while time.monotonic() - inicio < args.segundos:
            try:
                s = leitor.snapshot()
                eventos = monitor.observar(s, time.time())
                if primeiro:
                    print(f"Leitura OK: {s['mortes']} mortes acumuladas, "
                          f"{sum(v['derrotado'] for v in s['chefes'].values())} chefes derrotados, "
                          f"{len(s['fogueiras'])} registros de fogueiras. Nenhuma fala será gerada.", flush=True)
                    primeiro = False
                for e in eventos:
                    print(json.dumps(e, ensure_ascii=False), flush=True)
                with destino.open("a", encoding="utf-8") as f:
                    f.write(json.dumps({"instante": time.time(), "leitura": "ok", "eventos": eventos}) + "\n")
            except Exception as exc:
                monitor.indisponivel()
                print(f"Aguardando: {exc}", flush=True)
            time.sleep(1)
    finally:
        leitor.close()


if __name__ == "__main__":
    main()
