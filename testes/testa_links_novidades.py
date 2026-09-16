import ast
import os
import unittest
from pathlib import Path
from types import SimpleNamespace
from urllib.parse import urlparse, parse_qs

RAIZ = Path(__file__).parents[1]


def carregar(arquivo, nomes, escopo):
    arvore = ast.parse((RAIZ / arquivo).read_text(encoding='utf-8'))
    nos = [n for n in arvore.body if isinstance(n, ast.FunctionDef) and n.name in nomes]
    exec(compile(ast.Module(body=nos, type_ignores=[]), arquivo, 'exec'), escopo)


class TestaLinksNovidades(unittest.TestCase):
    def test_nota_com_espacos_e_sem_vault(self):
        escopo = dict(os=os, _VAULT=os.path.abspath('vault de teste'))
        carregar('modulos/obsidian.py', ['link_novidades', 'link_promocoes', '_link_nota_radar'], escopo)
        uri = escopo['link_novidades']()
        self.assertEqual(os.path.join(escopo['_VAULT'], 'Novidades.md'),
                         parse_qs(urlparse(uri).query)['path'][0])
        self.assertEqual(os.path.join(escopo['_VAULT'], 'Promocoes.md'),
                         parse_qs(urlparse(escopo['link_promocoes']()).query)['path'][0])
        escopo['_VAULT'] = ''
        self.assertEqual('', escopo['link_novidades']())

    def test_links_sobrevivem_a_limpeza_e_entram_no_historico(self):
        eventos = []
        escopo = dict(_clima_turno_pendente='', _historico_web=[], _ultima_fala_usuario='',
                      _remover_tags_voz=lambda t: str(t).replace('[clima:zoeira]', '').strip(),
                      _broadcast=eventos.append, cor=SimpleNamespace(cinza=lambda t: None))
        carregar('servidor.py', ['_registrar_turno', 'atualizar_legenda'], escopo)
        class Fala(str):
            pass
        fala = Fala('Comentário da notícia. [clima:zoeira]')
        fala.links_novidades = dict(noticia='https://example.org/materia', nota='obsidian://open?path=nota')
        escopo['atualizar_legenda'](fala, 'radar_rss', 'zoeira')
        turno = escopo['_historico_web'][0]
        self.assertEqual(fala.links_novidades, turno['links_novidades'])
        self.assertEqual('Comentário da notícia.', turno['luna'])
        self.assertNotIn('https', eventos[0]['legenda'])
