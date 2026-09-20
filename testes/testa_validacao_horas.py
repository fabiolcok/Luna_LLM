import unittest
import ast
import re
from pathlib import Path
from types import SimpleNamespace
from modulos.validacao_horas import horas_conferem, quantidades_horas
from modulos.execucoes import Coordenador


class TestaHoras(unittest.TestCase):
    def test_gerador_descarta_antes_de_registrar_fala(self):
        arvore = ast.parse((Path(__file__).parents[1] / 'modulos/proativa.py').read_text(encoding='utf-8'))
        no = next(n for n in arvore.body if isinstance(n, ast.FunctionDef)
                  and n.name == '_gerar_fala_proativa')
        limpezas = []
        avisos = []
        escopo = dict(re=re, _historico_proativo=[], _historico_principal=[], _falas_recentes=[],
                      _execucoes=Coordenador(),
                      _pode_falar_proativo=lambda: True,
                      _contexto_recente_para_proativo=lambda texto: '',
                      cor=SimpleNamespace(amarelo=lambda x: None, vermelho=avisos.append),
                      gerar_resposta=lambda *a, **k: 'Oitenta horas nesse jogo.',
                      _limpar_visual_proativo=lambda: limpezas.append(True))
        exec(compile(ast.Module(body=[no], type_ignores=[]), '<gerador real>', 'exec'), escopo)
        import sys
        from unittest.mock import patch
        with patch.dict(sys.modules, {'servidor': SimpleNamespace(atualizar_status=lambda x: None)}):
            self.assertIsNone(escopo['_gerar_fala_proativa'](
                '16 horas nas últimas 2 semanas', 'hábito de jogo', variar=False))
        self.assertEqual([True], limpezas)
        self.assertEqual([], escopo['_falas_recentes'])
        self.assertTrue(any('Horas divergentes' in aviso for aviso in avisos), avisos)

    def test_regressao_16_virando_80(self):
        self.assertFalse(horas_conferem('16.0 horas nas últimas 2 semanas', 'Oitenta horas nesse jogo.'))
        self.assertTrue(horas_conferem('16.0 horas nas últimas 2 semanas', 'Dezesseis horas nesse jogo.'))

    def test_preserva_hiperbole_sem_numeros(self):
        self.assertTrue(horas_conferem('16 horas', 'Esse jogo já virou sua segunda residência.'))

    def test_centenas_e_milhares(self):
        self.assertEqual([142, 2000], quantidades_horas('cento e quarenta e duas horas, duas mil horas'))

    def test_decimal_em_algarismos(self):
        self.assertTrue(horas_conferem('16.5 horas', '16,5 horas'))
        self.assertFalse(horas_conferem('16.5 horas', '65 horas'))
        self.assertTrue(horas_conferem('16.5 horas', 'dezesseis vírgula cinco horas'))
