"""A janela nasce antes dos imports de voz e modelo, no thread principal."""
import ctypes
import json
import os
from pathlib import Path
import threading
import time
from urllib.request import urlopen

RAIZ = Path(__file__).resolve().parents[1]
_janela = None


def progresso(texto):
    if _janela is not None:
        try:
            _janela.evaluate_js("document.getElementById('etapa').textContent = " + json.dumps(texto))
        except Exception:
            pass


def esperar_servidor(url, timeout=30):
    limite = time.monotonic() + timeout
    while time.monotonic() < limite:
        try:
            with urlopen(url, timeout=1) as resposta:
                if resposta.status == 200:
                    return
        except OSError:
            pass
        time.sleep(0.2)
    raise TimeoutError("A interface local não respondeu a tempo. Confira logs/luna.log.")


def geometria_inicial():
    try:
        dados = json.loads((RAIZ / "modelos/janela_principal.json").read_text(encoding="utf-8"))
        largura, altura = int(dados['width']), int(dados['height'])
        if not (380 <= largura <= 4000 and 520 <= altura <= 2400):
            raise ValueError("Dimensões inválidas")
        resultado = dict(width=largura, height=altura)
        if dados.get('x') is not None and dados.get('y') is not None:
            x, y = int(dados['x']), int(dados['y'])
            if x > -30000 and y > -30000:
                resultado.update(x=x, y=y)
        return resultado
    except (OSError, ValueError, KeyError, TypeError):
        return dict(width=460, height=760)


def carregar(janela, importar=None):
    try:
        progresso("Carregando os componentes da Luna…")
        if importar is None:
            import importlib
            importar = lambda: importlib.import_module('main')
        runtime = importar()
        runtime.main(janela=janela)
    except BaseException as exc:
        import logging
        logging.getLogger('luna.boot').exception('Falha na inicialização')
        mensagem = f"Não consegui iniciar: {type(exc).__name__}: {exc}"
        janela.evaluate_js("mostrarErro(" + json.dumps(mensagem) + ")")


def iniciar():
    global _janela
    # A posse fica viva no lançador enquanto o runtime é importado em outro thread.
    mutex = ctypes.windll.kernel32.CreateMutexW(None, True, "Luna_LLM_SingleInstance")
    if ctypes.windll.kernel32.GetLastError() == 183:
        ctypes.windll.user32.MessageBoxW(0, "Luna já está rodando.", "Luna", 0x30)
        return
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("LunaLLM.Interface")
    import webview
    _janela = webview.create_window('Luna', html=(RAIZ / 'static/inicializacao.html').read_text(encoding='utf-8'),
                                    **geometria_inicial())
    def identidade():
        from modulos.identidade_janela import aplicar_identidade
        try:
            aplicar_identidade(_janela.native.Handle.ToInt64())
        except Exception:
            pass
    _janela.events.before_show += identidade
    carregada = threading.Event()
    _janela.events.loaded += carregada.set
    def preparar():
        if carregada.wait(30):
            carregar(_janela)
    webview.start(func=preparar, icon=str(RAIZ / 'static/luna.ico'), private_mode=False,
                  storage_path=str(RAIZ / 'modelos/webview_dados'))
    # Fechar durante o boot precisa também encerrar bibliotecas já inicializadas.
    os._exit(0)
