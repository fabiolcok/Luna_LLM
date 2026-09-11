"""Executa o detector real sem inicializar modelos ou serviços."""
import ast
import re
import unittest
from pathlib import Path

arvore = ast.parse((Path(__file__).parents[1] / 'modulos/pensar.py').read_text(encoding='utf-8'))
nos = [n for n in arvore.body if
       (isinstance(n, ast.FunctionDef) and n.name == '_parece_pedido_de_acao') or
       (isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == '_PADRAO_ACAO'
                                        for t in n.targets))]
escopo = {'re': re}
exec(compile(ast.Module(body=nos, type_ignores=[]), '<detector real>', 'exec'), escopo)


class TestaRelatoAcao(unittest.TestCase):
    def test_relato_nao_pede_ferramenta(self):
        self.assertFalse(escopo['_parece_pedido_de_acao'](
            'meu modem usa a net CGNAT... nao consigo abrir porta ainda... '
            'estou falando com o pessoal do provedor.'))

    def test_pedido_junto_do_relato_continua_pedido(self):
        for texto in ('Não consigo abrir porta ainda, pesquisa uma alternativa.',
                      'Estou tentando abrir portas; busque informações.',
                      'Pode abrir o navegador?', 'Não abra o site; pesquise o assunto.'):
            with self.subTest(texto=texto):
                self.assertTrue(escopo['_parece_pedido_de_acao'](texto))
