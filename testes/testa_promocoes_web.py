"""Promoções usam a foto já baixada para o Obsidian, sem chamar Telegram ou LLM de verdade."""
import ast
import re
import tempfile
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

import servidor
from modulos import obsidian, radar_promo


class TestaPromocoesWeb(unittest.TestCase):
    def test_foto_ja_baixada_e_servida_pela_rota(self):
        with tempfile.TemporaryDirectory() as pasta, patch.object(obsidian, '_VAULT', pasta):
            fotos = Path(pasta, *obsidian._PASTA_IMGS_PROMO)
            fotos.mkdir(parents=True)
            conteudo = b'\xff\xd8foto-de-teste\xff\xd9'
            (fotos / 'canal_teste_123.jpg').write_bytes(conteudo)
            with servidor.app.test_client() as client:
                resposta = client.get('/imagens/promocoes/canal_teste_123.jpg')
                try:
                    self.assertEqual(resposta.status_code, 200)
                    self.assertEqual(resposta.data, conteudo)
                    self.assertEqual(resposta.mimetype, 'image/jpeg')
                    self.assertEqual(resposta.headers['X-Content-Type-Options'], 'nosniff')
                finally:
                    resposta.close()

    def test_rota_nao_acessa_notas_ou_fotos_fora_da_pasta(self):
        with tempfile.TemporaryDirectory() as pasta, patch.object(obsidian, '_VAULT', pasta):
            (Path(pasta) / 'segredo.jpg').write_bytes(b'fora do cache')
            with servidor.app.test_client() as client:
                for url in ('/imagens/promocoes/segredo.jpg', '/imagens/promocoes/../segredo.jpg',
                            '/imagens/promocoes/%2e%2e%2fsegredo.jpg', '/imagens/promocoes/Memoria.md',
                            '/imagens/promocoes/foto.svg', '/imagens/promocoes/inexistente.jpg'):
                    with self.subTest(url=url):
                        self.assertEqual(client.get(url).status_code, 404)
        with patch.object(obsidian, '_VAULT', ''):
            self.assertEqual(servidor.app.test_client().get('/imagens/promocoes/foto.jpg').status_code, 404)

    def test_link_no_disco_nao_pode_apontar_para_fora_do_cache(self):
        with tempfile.TemporaryDirectory() as pasta, patch.object(obsidian, '_VAULT', pasta):
            fora = str(Path(pasta, 'segredo.jpg'))
            base = str(Path(pasta, *obsidian._PASTA_IMGS_PROMO))
            # Simula a resolução do link sem exigir privilégios de symlink no Windows.
            with patch.object(servidor.os.path, 'realpath', side_effect=[base, fora]):
                self.assertEqual(servidor.app.test_client().get('/imagens/promocoes/foto.jpg').status_code, 404)

    def executar_radar(self, tem_foto=True, baixou=True, link='https://t.me/canal_teste/123'):
        arvore = ast.parse(Path('modulos/proativa.py').read_text(encoding='utf8'))
        nos = [n for n in arvore.body if isinstance(n, (ast.FunctionDef, ast.ClassDef))
               and n.name in {'_tarefa_radar_promocoes', '_FalaProativa'}]
        e = {
            'CONFIGURACAO': {'Radar_Promocoes': {'ativo': True, 'horario_silencio': (0, 0), 'intervalo_minutos': 30}},
            '_em_horario_silencio': lambda *a: False, '_passou_intervalo': lambda *a: True,
            'obsidian': SimpleNamespace(
                ler_config_promocoes=lambda: (['@canal_teste'], ['batedeira']),
                preparar_img_promo=Mock(return_value=('cache/canal_teste_123.jpg', 'canal_teste_123.jpg')),
                link_promocoes=lambda: 'obsidian://open?path=Promocoes.md', adicionar_promocoes=Mock()),
            'carregar_vistos': lambda: {'promo': {}, 'promo_canais': ['@canal_teste']},
            'salvar_vistos': Mock(), '_sem_acento': lambda s: s.lower(), '_RADAR_MAX_VISTOS': 1000,
            'random': SimpleNamespace(choice=lambda xs: xs[0]), 'REGRA_PERSONA': '',
            're': re, 'registrar_tentativa': Mock(), 'cor': Mock(), '_ultima_execucao': {},
        }
        exec(compile(ast.Module(body=nos, type_ignores=[]), 'radar-promo-isolado', 'exec'), e)
        e['_gerar_fala_proativa'] = Mock(return_value=e['_FalaProativa']('Tem uma promoção de batedeira!'))
        e['_falar_proativamente'] = Mock(return_value=True)
        mensagens = [('@canal_teste', 123, 'Batedeira de teste em promoção', link, None, tem_foto)]
        with patch.object(radar_promo, 'buscar_mensagens', return_value=mensagens), \
             patch.object(radar_promo, 'baixar_foto', return_value=baixou) as baixar:
            e['_tarefa_radar_promocoes']()
        return e, baixar

    def test_radar_reaproveita_foto_da_mesma_promocao_sem_chamada_extra(self):
        e, baixar = self.executar_radar()
        baixar.assert_called_once_with('@canal_teste', 123, 'cache/canal_teste_123.jpg')
        e['_gerar_fala_proativa'].assert_called_once()
        fala = e['_falar_proativamente'].call_args.args[0]
        cartao = fala.cartoes_web[0]
        self.assertEqual(cartao['tipo'], 'promocao')
        self.assertEqual(cartao['titulo'], 'batedeira')
        self.assertEqual(cartao['url'], fala.links_novidades['ofertas'][0]['url'])
        self.assertEqual(cartao['imagem'], '/imagens/promocoes/canal_teste_123.jpg')
        salvo = e['obsidian'].adicionar_promocoes.call_args.args[0][0]
        self.assertEqual(salvo[4], 'canal_teste_123.jpg')
        self.assertNotIn(cartao['imagem'], e['_gerar_fala_proativa'].call_args.args[0])
        self.assertNotIn('123.jpg', str(fala))

    def test_sem_foto_ou_download_com_falha_preserva_cartao_e_links(self):
        for tem_foto, baixou in ((False, False), (True, False)):
            with self.subTest(tem_foto=tem_foto):
                e, baixar = self.executar_radar(tem_foto=tem_foto, baixou=baixou)
                fala = e['_falar_proativamente'].call_args.args[0]
                self.assertEqual(fala.cartoes_web[0]['imagem'], '')
                self.assertEqual(fala.cartoes_web[0]['url'], 'https://t.me/canal_teste/123')
                self.assertEqual(baixar.call_count, int(tem_foto))

    def test_canal_sem_link_publico_nao_recebe_link_inventado(self):
        e, _ = self.executar_radar(link='')
        fala = e['_falar_proativamente'].call_args.args[0]
        self.assertEqual(fala.cartoes_web[0]['url'], '')
        self.assertTrue(fala.cartoes_web[0]['imagem'])


if __name__ == '__main__':
    unittest.main()
