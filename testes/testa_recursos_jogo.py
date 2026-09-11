"""Regressão da lista branca de RAM usada quando um jogo abre."""

import ast
import unittest
import re
import sys
from types import SimpleNamespace
from unittest.mock import patch
from pathlib import Path


def _processos_intocaveis() -> set[str]:
    """Lê só a constante; importar proativa inicializaria voz e modelos nos testes."""
    caminho = Path(__file__).parents[1] / "modulos" / "proativa.py"
    arvore = ast.parse(caminho.read_text(encoding="utf-8"))
    for no in arvore.body:
        if isinstance(no, ast.Assign) and any(
            isinstance(alvo, ast.Name) and alvo.id == "_PROC_INTOCAVEIS"
            for alvo in no.targets
        ):
            return set(ast.literal_eval(no.value))
    raise AssertionError("_PROC_INTOCAVEIS não foi encontrado em proativa.py")


class TestaRecursosJogo(unittest.TestCase):
    def test_exclui_jogo_abreviado_e_preserva_outro_processo(self):
        arvore = ast.parse((Path(__file__).parents[1] / 'modulos/proativa.py').read_text(encoding='utf-8'))
        no = next(n for n in arvore.body if isinstance(n, ast.FunctionDef)
                  and n.name == '_ram_hog_nao_essencial')
        escopo = {'re': re, '_PROC_INTOCAVEIS': _processos_intocaveis(), '_RAM_HOG_MIN_MB': 3000}
        exec(compile(ast.Module(body=[no], type_ignores=[]), '<ram real>', 'exec'), escopo)
        def processo(nome, gb, exe=''):
            return SimpleNamespace(info=dict(name=nome, memory_info=SimpleNamespace(rss=gb*1024**3), exe=exe))
        processos = [processo('ff7remake_.exe', 8), processo('editor.exe', 4),
                     processo('game.exe', 9, r'G:\Steam\common\FINAL FANTASY VII REMAKE\bin\game.exe')]
        with patch.dict(sys.modules, {'psutil': SimpleNamespace(process_iter=lambda campos: processos)}):
            self.assertEqual('editor (4.0GB)', escopo['_ram_hog_nao_essencial']('FINAL FANTASY VII REMAKE INTERGRADE'))

    def test_llama_server_esta_na_lista_branca_com_e_sem_extensao(self):
        intocaveis = _processos_intocaveis()
        self.assertIn("llama-server.exe", intocaveis)
        self.assertIn("llama-server", intocaveis)

    def test_python_da_luna_esta_na_lista_branca_com_e_sem_extensao(self):
        intocaveis = _processos_intocaveis()
        self.assertIn("python3.12.exe", intocaveis)
        self.assertIn("python3.12", intocaveis)


if __name__ == "__main__":
    unittest.main()
