"""Demo local do Sopro com backend Python CPU e referência de voz disponível."""
from __future__ import annotations

import argparse
from functools import partial
from http.server import ThreadingHTTPServer
from pathlib import Path
import re
import shutil

from testes.bancada_sopro import RAIZ, REVISAO, TEXTOS, configurar_cache


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=7860)
    parser.add_argument("--parar", action="store_true", help="encerra a demo local nessa porta")
    parser.add_argument("--ref", type=Path, default=RAIZ / "logs/bancada_tts/kitten2-20261003/amostras/kokoro_conquista_stable.wav")
    args = parser.parse_args()
    if args.parar:
        from urllib.request import Request, urlopen
        pedido = Request(f"http://127.0.0.1:{args.port}/api/luna-piloto/encerrar",
                         data=b"{}", headers={"Content-Type": "application/json", "X-Sopro-Piloto": "1"})
        with urlopen(pedido, timeout=10) as resposta:
            print(resposta.read().decode("utf-8"))
        return
    cache = configurar_cache()
    snapshot = cache / "hub/models--samuel-vitorino--sopro-v2-turbo/snapshots" / REVISAO
    if not (snapshot / "model.safetensors").is_file():
        parser.error("Execute a bancada primeiro para baixar o snapshot do modelo.")
    if not args.ref.is_file():
        parser.error("Referência ausente; use --ref apontando para um WAV de 5 a 20 segundos.")
    import torch
    import sopro.server as servidor
    torch.set_num_threads(6)
    torch.set_num_interop_threads(1)
    destino = RAIZ / "logs/bancada_tts/sopro-20261004/demo"
    shutil.copytree(servidor._static_root(), destino, dirs_exist_ok=True)
    index = destino / "index.html"
    html = index.read_text(encoding="utf-8")
    # A demo distribuída inclui um importmap para ONNX/CDN, mas aqui só usamos o backend Python.
    html, quantidade = re.subn(r'<script type="importmap">.*?</script>', "", html, flags=re.S)
    if quantidade != 1:
        raise RuntimeError("A estrutura da demo mudou; confira o importmap antes de servir.")
    html = html.replace('<html lang="en">', '<html lang="pt-BR">')
    html = html.replace("<title>Sopro ONNX</title>", "<title>Sopro local · CPU</title>")
    html = html.replace("The smallest voice can still fill a room.", TEXTOS["morte"])
    html = html.replace('<option value="" selected>Auto</option>', '<option value="">Auto</option>')
    html = html.replace('<option value="pt">PT</option>', '<option value="pt" selected>PT</option>')
    html = html.replace("<span>Speak</span>", "<span>Gerar fala</span>")
    html = html.replace("Text to speak", "Texto para falar")
    html = html.replace("Choose a file or record 5-20 seconds", "Referência local pronta; você pode escolher outro áudio de 5–20 segundos")
    index.write_text(html, encoding="utf-8")
    shutil.copy2(args.ref, destino / "referencia.wav")
    script = destino / "main.js"
    fonte = script.read_text(encoding="utf-8")
    if not fonte.endswith("boot();\n"):
        raise RuntimeError("A inicialização da demo mudou; confira antes de servir.")
    fonte = fonte[:-len("boot();\n")] + """boot().then(async () => {
  if (!tts) return;
  try {
    const response = await fetch('./referencia.wav');
    if (!response.ok) throw new Error('Não foi possível carregar a referência local');
    await setReference(new File([await response.blob()], __REFERENCIA_NOME__, {type:'audio/wav'}));
  } catch (error) { console.error(error); setStatus(error.message); }
});
"""
    import json
    fonte = fonte.replace("__REFERENCIA_NOME__", json.dumps(args.ref.name))
    script.write_text(fonte, encoding="utf-8")
    shutil.copy2(destino / "backend-python.js", destino / "backend.js")
    # O handler original redireciona backend.js pela raiz do pacote; apontamos a raiz para a cópia sem CDN.
    servidor._static_root = lambda: destino
    class Handler(servidor.DemoHandler):
        def do_POST(self):
            if self.path != "/api/luna-piloto/encerrar":
                return super().do_POST()
            # O header impede que um formulário de outro site encerre o piloto por um POST simples.
            if self.headers.get("X-Sopro-Piloto") != "1":
                self.send_error(403)
                return
            self._body(1024)
            self._json(200, {"encerrado": True})
            import threading
            threading.Thread(target=self.server.shutdown, daemon=True).start()

    Handler.state = servidor.DemoState(str(snapshot), "cpu", False)
    handler = partial(Handler, directory=str(destino))
    server = ThreadingHTTPServer(("127.0.0.1", args.port), handler)
    print(f"Sopro local em http://127.0.0.1:{args.port}/ · CPU · Ctrl+C encerra.", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
