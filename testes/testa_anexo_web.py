"""Regressão: mensagem digitada no web também precisa consumir o arquivo anexado."""

import unittest

import servidor


class TestaAnexoWeb(unittest.TestCase):
    def tearDown(self):
        servidor._arquivo_pendente = None

    def test_injeta_e_consumo_acontece_uma_vez(self):
        servidor._arquivo_pendente = {"nome": "nota.txt", "conteudo": "conteúdo do arquivo"}

        primeira = servidor.injetar_arquivo_pendente("me fala o que está escrito")
        segunda = servidor.injetar_arquivo_pendente("outra mensagem")

        self.assertIn("[Arquivo: nota.txt]", primeira)
        self.assertIn("conteúdo do arquivo", primeira)
        self.assertTrue(primeira.endswith("me fala o que está escrito"))
        self.assertEqual("outra mensagem", segunda)


if __name__ == "__main__":
    unittest.main()
