import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

import servidor
from modulos import interesses_radar as radar
from testes.bancada_sugestoes_novidades import executar_radar


class TestaInteressesRadar(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(); self.addCleanup(tmp.cleanup)
        p = patch.object(radar, 'CAMINHO', Path(tmp.name) / 'interesses.json')
        p.start(); self.addCleanup(p.stop)

    def test_preferencia_substitui_anterior_e_pode_ser_removida(self):
        for _ in range(5):
            self.assertTrue(radar.agir('mais', 'OLED')['ok'])
        self.assertEqual(len(radar.estado_interface()['itens']), 1)
        radar.agir('menos', 'oled')
        self.assertEqual(radar.estado_interface()['itens'][0]['preferencia'], 'menos')
        radar.agir('remover', 'OLED')
        self.assertEqual(radar.estado_interface()['itens'], [])
        for assunto in ['de do para', '<img>', 'https://example.org/', 'a' * 81]:
            self.assertFalse(radar.agir('mais', assunto)['ok'])

    def test_pesos_por_palavras_titulo_e_resumo_sem_casar_substring(self):
        noticias = [('Novo QD-OLED', '', '', 'Teste de monitor', ''),
                    ('OLEDium', '', '', 'Outro teste', ''), ('GPU nova', '', '', 'Vídeo integrado', '')]
        self.assertEqual(radar.pesos(noticias, [{'assunto': 'monitor OLED', 'preferencia': 'mais'}]), [5, 1, 1])
        self.assertEqual(radar.pesos(noticias, [{'assunto': 'OLED', 'preferencia': 'menos'}]), [.2, 1, 1])

    def test_sorteio_sem_preferencia_e_falha_preserva_arquivo(self):
        rng = Mock(); noticias = [('Título', '', '', '', '')]
        radar.escolher(noticias, rng=rng); rng.choice.assert_called_once_with(noticias)
        radar.CAMINHO.write_text('corrompido', encoding='utf8')
        self.assertFalse(radar.agir('mais', 'OLED')['ok'])
        self.assertEqual(radar.CAMINHO.read_text(encoding='utf8'), 'corrompido')

    def test_clique_historico_valida_origem_e_nao_altera_avaliacao(self):
        historico = [{'id': 'rss', 'origem_proativa': 'radar_rss', 'cartoes_web': [{'tipo': 'noticia'}]},
                     {'id': 'jogo', 'origem_proativa': 'dark_souls_morte'}]
        with patch.object(servidor, '_historico_web', historico), patch.object(servidor, '_registrar_avaliacao') as avaliar:
            self.assertTrue(servidor._receber_interesse_radar({'turno_id':'rss', 'acao':'mais', 'assunto':'OLED'})['ok'])
            self.assertFalse(servidor._receber_interesse_radar({'turno_id':'jogo', 'acao':'mais', 'assunto':'OLED'})['ok'])
            self.assertFalse(servidor._receber_interesse_radar({'turno_id':'inexistente', 'acao':'mais', 'assunto':'OLED'})['ok'])
            avaliar.assert_not_called()

    def test_preferencia_nao_altera_todas_as_novidades_na_nota(self):
        casos = [{'id':'oled', 'titulo':'Monitor OLED', 'resumo':'Burn-in'},
                 {'id':'gpu', 'titulo':'GPU nova', 'resumo':'Desempenho'}]
        from modulos import cartoes_web
        fala = type('Fala', (str,), {})('Comentário.')
        falas, env = executar_radar(casos, Mock(return_value=fala),
            preferencias=[{'assunto': 'GPU', 'preferencia': 'mais'}])
        self.assertEqual(len(env['obsidian'].adicionar_novidades.call_args.args[0]), 2)
        self.assertEqual(cartoes_web.normalizar(falas[0].cartoes_web)[0]['mais'], 1)
        self.assertEqual(cartoes_web.normalizar(falas[0].cartoes_web)[0]['titulo'], 'GPU nova')


if __name__ == '__main__':
    unittest.main()
