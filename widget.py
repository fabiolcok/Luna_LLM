"""Janela visual isolada do mascote — não inicia voz, Telegram, modelo ou servidor."""

import json
import os
import threading
import time

# O widget usa Qt porque o WebView2 deixa o fundo da janela WinForms visível no
# Windows. Fixar o binding antes de importar o pywebview evita escolher outro Qt
# que por acaso esteja instalado na máquina do usuário.
os.environ["QT_API"] = "pyside6"

import webview


_RAIZ = os.path.dirname(os.path.abspath(__file__))
_POSICAO = os.path.join(_RAIZ, "modelos", "widget_posicao.json")


def _carregar_posicao():
    try:
        with open(_POSICAO, "r", encoding="utf-8") as arquivo:
            dados = json.load(arquivo)
        return int(dados["x"]), int(dados["y"])
    except (OSError, ValueError, KeyError, TypeError):
        return None


def _salvar_posicao(x, y):
    try:
        os.makedirs(os.path.dirname(_POSICAO), exist_ok=True)
        with open(_POSICAO, "w", encoding="utf-8") as arquivo:
            json.dump({"x": int(x), "y": int(y)}, arquivo)
    except OSError:
        pass


class _ApiWidget:
    def __init__(self):
        self._janela = None

    def recolher_mascote(self):
        janela = self._janela

        def fechar():
            time.sleep(0.75)  # deixa a Promise da ponte responder antes de descartar o WebView2
            janela.destroy()

        threading.Thread(target=fechar, daemon=True).start()
        return True


def main():
    api = _ApiWidget()
    kwargs = dict(
        width=320, height=320, resizable=False,
        frameless=True, easy_drag=False, shadow=False,
        on_top=True, transparent=True, background_color="#000000",
        focus=True, js_api=api,
    )
    posicao = _carregar_posicao()
    if posicao:
        kwargs.update(x=posicao[0], y=posicao[1])

    janela = webview.create_window(
        "Luna — mascote", "http://localhost:5000/?widget=1", **kwargs
    )
    api._janela = janela
    janela.events.moved += _salvar_posicao
    # Qt compõe alfa real na janela; o backend WinForms/WebView2 revelava um
    # retângulo branco ou preto no lugar da área transparente.
    webview.start(gui="qt")


if __name__ == "__main__":
    main()
