import tempfile
import ast
from types import SimpleNamespace
import unittest
from pathlib import Path
from unittest.mock import patch
from modulos import avaliacao_ferramentas as af


class AvaliacaoFerramentas(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        p = patch.object(af, 'ARQUIVO', Path(self.tmp.name) / 'votos.json')
        p.start(); self.addCleanup(p.stop)
        self.turno = {'turno_id': 'um', 'usuario': 'Toque a música', 'luna': 'Tocando',
                      'contexto': {'ferramenta': {'nome': 'controlar_spotify', 'argumentos': {'acao': 'tocar'},
                                                  'sucesso': True, 'segundos': 1.2}}}

    def test_persistencia_e_idempotencia(self):
        af.registrar(self.turno)
        af.votar('um', 'bom')
        af.registrar(self.turno)
        self.assertEqual(len(af.listar()), 1)
        self.assertEqual(af.listar()[0]['voto']['rating'], 'bom')
        af.votar('um', 'ruim', 'parametros_errados', 'Outra música')
        self.assertEqual(af.listar()[0]['voto']['comentario'], 'Outra música')

    def test_nao_avaliar_outro_turno(self):
        af.registrar(self.turno)
        with self.assertRaises(ValueError): af.votar('outro', 'bom')
        self.assertIsNone(af.listar()[0]['voto'])

    def test_sem_ferramenta_nao_cria_pendencia(self):
        t = {'turno_id': 'dois', 'contexto': {}, 'usuario': 'Salve', 'luna': 'Não salvei'}
        af.registrar(t)
        self.assertEqual(af.listar(), [])
        af.votar('dois', 'ruim', 'faltou_ferramenta', snapshot=t)
        self.assertIsNone(af.listar()[0]['ferramenta'])

    def test_erro_salvar_nao_confirma_voto(self):
        af.registrar(self.turno)
        with patch.object(af, '_gravar', side_effect=OSError):
            with self.assertRaises(OSError): af.votar('um', 'bom')
        self.assertIsNone(af.listar()[0]['voto'])

    def test_rejeita_voto_negativo_sem_motivo(self):
        af.registrar(self.turno)
        with self.assertRaises(ValueError): af.votar('um', 'ruim')

    def test_endpoint_preserva_turno_e_rejeita_dados_invalidos(self):
        fonte = Path(__file__).resolve().parents[1] / 'servidor.py'
        arvore = ast.parse(fonte.read_text(encoding='utf-8'))
        func = next(n for n in arvore.body if isinstance(n, ast.FunctionDef) and n.name == 'avaliacoes_ferramentas_web')
        func.decorator_list = []
        req = SimpleNamespace(method='GET', get_json=lambda **kw: None)
        scope = {'request': req}
        exec(compile(ast.Module(body=[func], type_ignores=[]), str(fonte), 'exec'), scope)
        rota = scope['avaliacoes_ferramentas_web']
        af.registrar(self.turno)
        self.assertEqual(rota()['itens'][0]['turno_id'], 'um')
        req.method = 'POST'
        req.get_json = lambda **kw: {'turno_id': 'um', 'rating': 'bom'}
        self.assertEqual(rota()['item']['voto']['rating'], 'bom')
        req.get_json = lambda **kw: {'turno_id': 'outro', 'rating': 'bom'}
        self.assertEqual(rota()[1], 400)


if __name__ == '__main__': unittest.main()
