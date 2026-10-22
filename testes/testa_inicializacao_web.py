"""Inicialização sem iniciar modelos, áudio ou uma segunda Luna."""
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch
from modulos import inicializacao_web as boot


class TestaInicializacao(unittest.TestCase):
    def test_runtime_recebe_a_mesma_janela(self):
        janela = Mock()
        runtime = Mock()
        boot.carregar(janela, lambda: runtime)
        runtime.main.assert_called_once_with(janela=janela)

    def test_erro_no_import_aparece_na_janela(self):
        janela = Mock()
        with self.assertLogs('luna.boot', level='ERROR'):
            boot.carregar(janela, Mock(side_effect=RuntimeError('falha "teste"')))
        script = janela.evaluate_js.call_args.args[0]
        self.assertTrue(script.startswith('mostrarErro('))
        self.assertIn('RuntimeError', json.loads(script[len('mostrarErro('):-1]))

    def test_servidor_lento_e_timeout(self):
        resposta = Mock()
        resposta.__enter__ = Mock(return_value=SimpleNamespace(status=200))
        resposta.__exit__ = Mock(return_value=False)
        with patch.object(boot, 'urlopen', side_effect=[OSError(), resposta]) as abrir, patch.object(boot.time, 'sleep'):
            boot.esperar_servidor('http://localhost:5000/')
            self.assertEqual(abrir.call_count, 2)
        with self.assertRaises(TimeoutError):
            boot.esperar_servidor('http://localhost:5000/', timeout=0)

    def test_geometria_minimizada_nao_esconde_boot(self):
        with tempfile.TemporaryDirectory() as pasta:
            raiz = Path(pasta)
            (raiz / 'modelos').mkdir()
            (raiz / 'modelos/janela_principal.json').write_text(json.dumps(dict(width=720, height=900, x=-32000, y=-32000)))
            with patch.object(boot, 'RAIZ', raiz):
                self.assertEqual(boot.geometria_inicial(), dict(width=720, height=900))


if __name__ == '__main__':
    unittest.main()
