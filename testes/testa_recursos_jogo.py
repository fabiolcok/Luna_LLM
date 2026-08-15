"""Regressão da lista branca de RAM usada quando um jogo abre."""

import ast
import unittest
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
