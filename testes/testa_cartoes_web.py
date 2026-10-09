"""Contratos dos cartões com legenda/histórico, sem LLM, notas pessoais ou áudio."""
import ast
import json
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from modulos import cartoes_web as cartoes


class TestaCartoesWeb(unittest.TestCase):
    def test_legenda_e_historico_preservam_texto_e_metadados_separados(self):
        eventos = []
        contexto = dict(_clima_turno_pendente='', _historico_web=[], _ultima_fala_usuario='',
                        _remover_tags_voz=lambda t: str(t).replace('[clima:zoeira]', '').strip(),
                        _broadcast=eventos.append, cor=SimpleNamespace(cinza=lambda t: None))
        arvore = ast.parse(Path('servidor.py').read_text(encoding='utf8'))
        arvore.body = [n for n in arvore.body if isinstance(n, ast.FunctionDef)
                      and n.name in {'_registrar_turno', 'atualizar_legenda'}]
        exec(compile(arvore, 'servidor-isolado', 'exec'), contexto)
        class Fala(str):
            pass
        fala = Fala('Comentário natural da Luna. [clima:zoeira]')
        imagem = 'https://example.org/imagem.jpg'
        fala.cartoes_web = [cartoes.noticia('Título da fonte', 'Feed de teste', 'https://example.org/n', 2, imagem)]
        fala.links_novidades = {'noticia': 'https://example.org/n', 'nota': 'obsidian://open?path=nota'}
        with patch('modulos.avaliacoes.capturar_turno', return_value='turno-teste'):
            contexto['atualizar_legenda'](fala, 'radar_rss', 'zoeira')
        turno = json.loads(json.dumps(contexto['_historico_web']))[0]
        self.assertEqual('Comentário natural da Luna.', eventos[0]['legenda'])
        self.assertEqual('Comentário natural da Luna.', turno['luna'])
        self.assertEqual('Título da fonte', turno['cartoes_web'][0]['titulo'])
        self.assertEqual(imagem, turno['cartoes_web'][0]['imagem'])
        self.assertEqual(fala.links_novidades, turno['links_novidades'])
        fala.cartoes_web[0]['titulo'] = 'Alteração posterior'
        self.assertEqual('Título da fonte', contexto['_historico_web'][0]['cartoes_web'][0]['titulo'])
        self.assertNotIn('cartoes_web', json.dumps({'role': 'assistant', 'content': fala}))
        self.assertNotIn(imagem, json.dumps({'role': 'assistant', 'content': fala}))
        self.assertNotIn('https', eventos[0]['legenda'])

    def test_dados_invalidos_nao_quebram_o_historico_nem_criam_acoes(self):
        for bruto in (None, {}, 'texto', [None], [{'tipo': 'html', 'titulo': 'X'}],
                      [cartoes.noticia('X', 'Y', 'javascript:alert(1)')],
                      [{'tipo': 'acompanhamento', 'titulo': 'X', 'origem': {}, 'id': 'a'}],
                      [{'tipo': 'acompanhamento', 'titulo': 'X', 'origem': 'sopro', 'id': 'outro'}]):
            with self.subTest(bruto=bruto):
                self.assertEqual([], cartoes.normalizar(bruto))
        valido = cartoes.acompanhamento('fontes', {'id': 'a', 'assunto': 'Tema'})
        valido.update(acao={'comando': 'apagar'}, etapa={})
        recebido = cartoes.normalizar([valido])[0]
        self.assertNotIn('acao', recebido)
        self.assertEqual('', recebido['etapa'])

    def test_imagem_invalida_ou_ausente_preserva_noticia(self):
        for imagem in (None, {}, '', 'javascript:alert(1)', 'data:image/png;base64,ABC',
                       'file:///imagem.jpg', 'obsidian://open?path=imagem', 'https://[',
                       'https://example.org/imagem com espaco.jpg'):
            with self.subTest(imagem=imagem):
                recebido = cartoes.normalizar([cartoes.noticia('Título', 'Feed', 'https://example.org/n', imagem=imagem)])
                self.assertEqual(1, len(recebido))
                self.assertEqual('', recebido[0]['imagem'])
                self.assertEqual('Título', recebido[0]['titulo'])

    def test_conversa_confirmada_recebe_referencia_do_item(self):
        arvore = ast.parse(Path('modulos/proativa.py').read_text(encoding='utf8'))
        arvore.body = [n for n in arvore.body if isinstance(n, (ast.FunctionDef, ast.ClassDef))
                      and n.name in {'_tarefa_acompanhamentos', '_FalaProativa'}]
        contexto = {'registrar_tentativa': lambda: None}
        exec(compile(arvore, 'proativa-isolada', 'exec'), contexto)
        falas, pedidos, registrados = [], [], []
        item = {'id': 'conversa1', 'assunto': 'Acesso externo do servidor', 'status': 'pendente'}
        def gerar(*args, **kwargs):
            pedidos.append((args, kwargs))
            return contexto['_FalaProativa']('Como ficou o acesso externo?')
        contexto['_gerar_fala_proativa'] = gerar
        contexto['_falar_proativamente'] = lambda fala: falas.append(fala) or True
        with patch('modulos.acompanhamentos.proximo_vencido', return_value=item), \
             patch('modulos.acompanhamentos.registrar_pergunta', side_effect=registrados.append):
            contexto['_tarefa_acompanhamentos']()
        self.assertEqual(1, len(pedidos))
        self.assertEqual(['conversa1'], registrados)
        self.assertEqual('conversa', falas[0].cartoes_web[0]['origem'])
        self.assertEqual('conversa1', falas[0].cartoes_web[0]['id'])
        self.assertEqual('Como ficou o acesso externo?', str(falas[0]))


if __name__ == '__main__':
    unittest.main()
