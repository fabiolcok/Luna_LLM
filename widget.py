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
from PySide6.QtGui import QCursor


_RAIZ = os.path.dirname(os.path.abspath(__file__))
_CONFIG = os.path.join(_RAIZ, "modelos", "widget_posicao.json")
_TAMANHOS = {"pequeno": 240, "normal": 320, "grande": 460}


def _carregar_config():
    try:
        with open(_CONFIG, "r", encoding="utf-8") as arquivo:
            dados = json.load(arquivo)
        tamanho = dados.get("tamanho", "normal")
        return {
            "x": int(dados["x"]) if "x" in dados else None,
            "y": int(dados["y"]) if "y" in dados else None,
            "tamanho": tamanho if tamanho in _TAMANHOS else "normal",
            "sempre_no_topo": bool(dados.get("sempre_no_topo", True)),
        }
    except (OSError, ValueError, TypeError):
        return {"x": None, "y": None, "tamanho": "normal", "sempre_no_topo": True}


def _salvar_config(dados):
    try:
        os.makedirs(os.path.dirname(_CONFIG), exist_ok=True)
        with open(_CONFIG, "w", encoding="utf-8") as arquivo:
            json.dump(dados, arquivo)
    except OSError:
        pass


class _ApiWidget:
    def __init__(self, config):
        self._janela = None
        self._config = config

    def _guardar(self):
        _salvar_config(self._config)

    def registrar_posicao(self, x, y):
        self._config.update(x=int(x), y=int(y))
        self._guardar()

    def estado_widget(self):
        return {"tamanho": self._config["tamanho"],
                "sempre_no_topo": self._config["sempre_no_topo"]}

    def definir_sempre_no_topo(self, ativo):
        ativo = bool(ativo)
        self._config["sempre_no_topo"] = ativo
        self._janela.on_top = ativo
        self._guardar()
        return self.estado_widget()

    def definir_tamanho(self, tamanho):
        if tamanho not in _TAMANHOS:
            return self.estado_widget()
        dimensao = _TAMANHOS[tamanho]
        self._janela.resize(dimensao, dimensao)
        self._config["tamanho"] = tamanho
        self._guardar()
        return self.estado_widget()

    def cursor_relativo(self):
        """Cursor global convertido para coordenadas da janela transparente."""
        ponto = QCursor.pos()
        return {"x": ponto.x() - self._janela.x, "y": ponto.y() - self._janela.y}

    def recolher_mascote(self):
        janela = self._janela

        def fechar():
            time.sleep(0.75)  # deixa a Promise da ponte responder antes de descartar o WebView2
            janela.destroy()

        threading.Thread(target=fechar, daemon=True).start()
        return True


def main():
    config = _carregar_config()
    api = _ApiWidget(config)
    dimensao = _TAMANHOS[config["tamanho"]]
    kwargs = dict(
        width=dimensao, height=dimensao, resizable=False,
        frameless=True, easy_drag=False, shadow=False,
        on_top=config["sempre_no_topo"], transparent=True, background_color="#000000",
        focus=True, js_api=api,
    )
    if config["x"] is not None and config["y"] is not None:
        kwargs.update(x=config["x"], y=config["y"])

    janela = webview.create_window(
        "Luna — mascote", "http://localhost:5000/?widget=1", **kwargs
    )
    api._janela = janela
    janela.events.moved += api.registrar_posicao
    # Qt compõe alfa real na janela; o backend WinForms/WebView2 revelava um
    # retângulo branco ou preto no lugar da área transparente.
    webview.start(gui="qt")


if __name__ == "__main__":
    main()
