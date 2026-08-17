"""Estado factual das sessões Steam, sem modelo e sem tocar nos dados reais."""

import datetime
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parents[1]))

from modulos import rotina_jogos


class TestaRotinaJogos(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.caminho = Path(self.tmp.name) / "rotina.json"
        self.patch = patch.object(rotina_jogos, "CAMINHO_ESTADO", str(self.caminho))
        self.patch.start()
        self.agora = datetime.datetime(2026, 8, 17, 20, 0,
                                       tzinfo=datetime.timezone(datetime.timedelta(hours=-3)))

    def tearDown(self):
        self.patch.stop()
        self.tmp.cleanup()

    def test_marco_so_aparece_na_terceira_abertura(self):
        um = rotina_jogos.registrar_abertura("123", "Hellblade 2", self.agora)
        dois = rotina_jogos.registrar_abertura("123", "Hellblade 2",
                                               self.agora + datetime.timedelta(days=1))
        tres = rotina_jogos.registrar_abertura("123", "Hellblade 2",
                                                self.agora + datetime.timedelta(days=2))

        self.assertEqual("", rotina_jogos.contexto_abertura(um))
        self.assertEqual("", rotina_jogos.contexto_abertura(dois))
        self.assertIn("3ª vez", rotina_jogos.contexto_abertura(tres))
        self.assertIn("desde que eu comecei a acompanhar", rotina_jogos.contexto_abertura(tres))

    def test_fechamento_acumula_so_sessao_real(self):
        rotina_jogos.registrar_abertura("123", "Hellblade 2", self.agora)
        rotina_jogos.registrar_fechamento("123", "Hellblade 2", 1, self.agora)
        rotina_jogos.registrar_fechamento("123", "Hellblade 2", 47, self.agora)

        estado = json.loads(self.caminho.read_text(encoding="utf-8"))
        jogo = estado["jogos"]["123"]
        self.assertEqual(47, jogo["minutos_observados"])
        self.assertEqual(47, jogo["ultima_sessao_min"])

    def test_reiniciar_luna_nao_conta_segunda_sessao(self):
        primeira = rotina_jogos.registrar_abertura("123", "Hellblade 2", self.agora)
        reinicio = rotina_jogos.registrar_abertura(
            "123", "Hellblade 2", self.agora + datetime.timedelta(minutes=20)
        )

        self.assertEqual(1, primeira["sessoes"])
        self.assertEqual(1, reinicio["sessoes"])
        self.assertTrue(reinicio["mesma_sessao"])

        rotina_jogos.registrar_fechamento("123", "Hellblade 2", 50, self.agora)
        nova = rotina_jogos.registrar_abertura(
            "123", "Hellblade 2", self.agora + datetime.timedelta(hours=2)
        )
        self.assertEqual(2, nova["sessoes"])


if __name__ == "__main__":
    unittest.main()
