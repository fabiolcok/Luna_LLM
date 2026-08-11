"""Regressão: placeholders do .env.example não podem aparecer como configurados no web."""

import io
import os
import unittest
from unittest.mock import patch

import servidor


class TestaStatusChaves(unittest.TestCase):
    def test_distingue_placeholder_de_valor_real(self):
        exemplo = io.StringIO(
            "GEMINI_API_KEY=sua_chave_gemini_aqui\n"
            "TELEGRAM_TOKEN=seu_token_telegram\n"
            "USUARIO_NOME=SeuNome\n"
            "STEAM_API_KEY=sua_chave_steam\n"
            "EMAIL_SENHA=sua_senha_de_app_16_caracteres_sem_espacos\n"
        )
        ambiente = {
            "GEMINI_API_KEY": "sua_chave_gemini_aqui",
            "TELEGRAM_TOKEN": "token-real",
            "USUARIO_NOME": "SeuNome",
            "STEAM_API_KEY": "",
            "EMAIL_SENHA": "sua_senha_de_app_16_caracteres_sem_espacos",
        }
        with (patch.dict(os.environ, ambiente, clear=True),
              patch("dotenv.load_dotenv"),
              patch("builtins.open", return_value=exemplo)):
            status = {item["chave"]: item["ok"] for item in servidor._status_chaves()}

        self.assertFalse(status["GEMINI_API_KEY"])
        self.assertTrue(status["TELEGRAM_TOKEN"])
        self.assertFalse(status["USUARIO_NOME"])
        self.assertFalse(status["STEAM_API_KEY"])
        self.assertFalse(status["EMAIL_SENHA"])


if __name__ == "__main__":
    unittest.main()
