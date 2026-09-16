"""Valida volume sem carregar Kokoro nem reproduzir som."""
import ast
import unittest
from pathlib import Path
from types import SimpleNamespace
import numpy as np
import threading


class TestaVolume(unittest.TestCase):
    def setUp(self):
        arvore = ast.parse((Path(__file__).parents[1] / 'modulos/falar.py').read_text(encoding='utf-8'))
        nos = [n for n in arvore.body if isinstance(n, ast.FunctionDef)
               and n.name in ('configurar_voz', 'repetir_ultima_fala', '_tocar_com_volume')]
        self.audios = []
        self.original = np.array([0.8, -0.4], dtype=np.float32)
        self.escopo = dict(np=np, _volume_padrao=1.0, _ultima_fala_wav=self.original,
                           _audio_volume_lock=threading.RLock(), _audio_volume_atual=None,
                           _pipe=True, SAMPLE_RATE=24000,
                           sd=SimpleNamespace(stop=lambda: None,
                                              play=lambda wav, rate: self.audios.append(wav.copy())))
        exec(compile(ast.Module(body=nos, type_ignores=[]), '<voz real>', 'exec'), self.escopo)

    def test_volume_muda_no_mesmo_buffer_sem_reiniciar_audio(self):
        tocados = []
        self.escopo['sd'].play = lambda wav, rate: tocados.append(wav)
        self.escopo['_tocar_com_volume'](self.original)
        for volume in (0.5, 0.0, 1.0):
            self.escopo['configurar_voz'](volume=volume)
            self.assertEqual(1, len(tocados))
            np.testing.assert_allclose(tocados[0], self.original * volume)
        np.testing.assert_allclose(self.original, [0.8, -0.4])

    def test_repetir_aplica_volume_sem_modificar_cache(self):
        for volume in (0.5, 0.0, 1.0):
            self.escopo['configurar_voz'](volume=volume)
            self.assertTrue(self.escopo['repetir_ultima_fala']())
            np.testing.assert_allclose(self.audios[-1], self.original * volume)
        np.testing.assert_allclose(self.original, [0.8, -0.4])

    def test_limites_e_valores_invalidos(self):
        self.escopo['configurar_voz'](volume=2)
        self.assertEqual(1, self.escopo['_volume_padrao'])
        self.escopo['configurar_voz'](volume=-1)
        self.assertEqual(0, self.escopo['_volume_padrao'])
        for invalido in ('nan', 'inf', 'texto'):
            with self.assertRaises(ValueError):
                self.escopo['configurar_voz'](volume=invalido)
