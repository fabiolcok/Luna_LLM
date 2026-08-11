"""Testes dos estados de configuração sem acessar nenhuma API externa."""

import os
import unittest
from unittest.mock import patch

from modulos.diagnostico import estado_integracao


class TestaDiagnostico(unittest.TestCase):
    def test_integracao_preenchida(self):
        with patch.dict(os.environ, {"ID": "valor", "SEGREDO": "valor"}, clear=True):
            self.assertEqual("preenchida", estado_integracao(("ID", "SEGREDO")))

    def test_integracao_incompleta(self):
        with patch.dict(os.environ, {"ID": "valor", "SEGREDO": ""}, clear=True):
            self.assertEqual("incompleta", estado_integracao(("ID", "SEGREDO")))

    def test_placeholder_conta_como_ausente(self):
        with patch.dict(os.environ, {"TOKEN": "seu_token_aqui"}, clear=True):
            self.assertEqual("ausente", estado_integracao(("TOKEN",)))


if __name__ == "__main__":
    unittest.main()
