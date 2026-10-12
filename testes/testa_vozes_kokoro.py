"""Vozes da web e preferências persistidas, sem carregar o modelo nem tocar áudio."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

import servidor
from modulos.vozes_kokoro import VOZES_VALIDAS, VOZ_PADRAO, vozes_para_web


class TestaVozesKokoro(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.config = Path(tmp.name) / 'config.json'
        self.handler = Mock()
        self.envios = []
        for mudanca in (
            patch.object(servidor, '_CAMINHO_CONFIG', str(self.config)),
            patch.object(servidor, '_estado_config', deepcopy(servidor._estado_config)),
            patch.object(servidor, '_config_handlers', {'voz': self.handler}),
            patch.object(servidor, '_broadcast', side_effect=self.envios.append),
        ):
            mudanca.start()
            self.addCleanup(mudanca.stop)
        servidor._estado_config['voz'] = VOZ_PADRAO
        servidor._estado_config['vozes_favoritas'] = []

    def test_catalogo_unico_tem_54_vozes_em_nove_grupos(self):
        grupos = servidor._config_para_web()['vozes']
        self.assertEqual(len(grupos), 9)
        self.assertEqual(grupos[0]['idioma'], 'Português (Brasil)')
        ids = [voz['id'] for grupo in grupos for voz in grupo['vozes']]
        self.assertEqual(len(ids), 54)
        self.assertEqual(len(set(ids)), 54)
        self.assertEqual(set(ids), VOZES_VALIDAS)
        self.assertTrue({'jf_alpha', 'af_bella', 'af_nicole', 'pf_dora', 'pm_alex', 'pm_santa'} <= set(ids))
        for grupo in grupos:
            for voz in grupo['vozes']:
                self.assertTrue(voz['nome'])
                self.assertIn(voz['genero'], ('feminina', 'masculina'))
        grupos[0]['vozes'].clear()
        self.assertEqual(len(vozes_para_web()[0]['vozes']), 3)

    def test_web_aplica_e_persiste_todas_as_vozes(self):
        for voz in sorted(VOZES_VALIDAS):
            with self.subTest(voz=voz):
                servidor._aplicar_config({'config': 'voz', 'valor': voz})
                self.handler.assert_called_with(voz)
                salvo = json.loads(self.config.read_text(encoding='utf8'))
                self.assertEqual(salvo['voz'], voz)
                self.assertNotIn('vozes', salvo)
                self.assertEqual(self.envios[-1]['estado']['voz'], voz)
                self.handler.reset_mock()

    def test_web_rejeita_vozes_invalidas_sem_salvar(self):
        for valor in ('F1', 'nao_existe', '../voz.pt', '', None, True, 42, [], {}):
            with self.subTest(valor=valor):
                servidor._aplicar_config({'config': 'voz', 'valor': valor})
                self.handler.assert_not_called()
                self.assertFalse(self.config.exists())
                self.assertEqual(self.envios[-1]['estado']['voz'], VOZ_PADRAO)

    def test_handler_falhou_mantem_voz_anterior(self):
        self.handler.side_effect = RuntimeError('Falha simulada')
        servidor._aplicar_config({'config': 'voz', 'valor': 'pf_dora'})
        self.assertFalse(self.config.exists())
        self.assertEqual(self.envios[-1]['estado']['voz'], VOZ_PADRAO)

    def test_reinicio_preserva_voz_e_normaliza_config_antiga(self):
        for voz in ('pm_alex', 'zf_xiaobei', 'af_nicole', 'F1', None, ['jf_alpha']):
            with self.subTest(voz=voz):
                self.config.write_text(json.dumps({'voz': voz}), encoding='utf8')
                servidor.carregar_e_aplicar_config()
                esperada = voz if isinstance(voz, str) and voz in VOZES_VALIDAS else VOZ_PADRAO
                self.handler.assert_called_with(esperada)
                self.assertEqual(servidor._estado_config['voz'], esperada)

    def test_favoritar_persiste_sem_trocar_voz_nem_duplicar(self):
        for voz in ('af_nicole', 'pf_dora', 'af_nicole'):
            servidor._aplicar_config({'config': 'voz_favorita', 'voz': voz, 'valor': True})
        self.handler.assert_not_called()
        self.assertEqual(servidor._estado_config['voz'], VOZ_PADRAO)
        self.assertEqual(servidor._estado_config['vozes_favoritas'], ['af_nicole', 'pf_dora'])
        salvo = json.loads(self.config.read_text(encoding='utf8'))
        self.assertEqual(salvo['vozes_favoritas'], ['af_nicole', 'pf_dora'])
        servidor._estado_config['vozes_favoritas'] = []
        servidor.carregar_e_aplicar_config()
        self.assertEqual(self.envios[-1]['estado']['vozes_favoritas'], ['af_nicole', 'pf_dora'])

    def test_desfavoritar_mantem_as_outras_e_a_voz_ativa(self):
        servidor._estado_config['vozes_favoritas'] = ['af_nicole', 'pf_dora']
        for _ in range(2):
            servidor._aplicar_config({'config': 'voz_favorita', 'voz': 'af_nicole', 'valor': False})
        self.assertEqual(self.envios[-1]['estado']['vozes_favoritas'], ['pf_dora'])
        self.assertEqual(self.envios[-1]['estado']['voz'], VOZ_PADRAO)
        self.handler.assert_not_called()
        servidor._aplicar_config({'config': 'voz_favorita', 'voz': 'pf_dora', 'valor': False})
        self.assertEqual(json.loads(self.config.read_text(encoding='utf8'))['vozes_favoritas'], [])

    def test_favoritas_invalidas_nao_sao_gravadas(self):
        for voz, valor in ((None, True), ([], True), ('F1', True), ('af_nicole', 'true'),
                           ('af_nicole', None), ('af_nicole', 1)):
            with self.subTest(voz=voz, valor=valor):
                servidor._aplicar_config({'config': 'voz_favorita', 'voz': voz, 'valor': valor})
                self.assertFalse(self.config.exists())
                self.assertEqual(servidor._estado_config['vozes_favoritas'], [])
        self.handler.assert_not_called()

    def test_reinicio_limpa_favoritas_invalidas_e_repetidas(self):
        for favoritas, esperadas in (
            (['af_nicole', 'F1', None, ['pf_dora'], 'af_nicole', 'pf_dora'], ['af_nicole', 'pf_dora']),
            ('af_nicole', []), (None, []),
        ):
            with self.subTest(favoritas=favoritas):
                self.config.write_text(json.dumps({'vozes_favoritas': favoritas}), encoding='utf8')
                servidor.carregar_e_aplicar_config()
                self.assertEqual(servidor._estado_config['vozes_favoritas'], esperadas)


if __name__ == '__main__':
    unittest.main()
