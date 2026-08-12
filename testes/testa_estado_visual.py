"""Contrato do diagnóstico de estados enviados ao mascote web."""

import unittest
from unittest.mock import patch

import servidor


class TestaEstadoVisual(unittest.TestCase):
    def test_registra_apenas_transicoes_mas_mantem_broadcasts(self):
        with (
            patch.object(servidor, "_ultimo_estado_rosto", None),
            patch.object(servidor, "_broadcast") as broadcast,
            patch.object(servidor.cor, "cinza") as log,
        ):
            servidor.atualizar_estado_rosto("ouvindo")
            servidor.atualizar_estado_rosto("ouvindo")
            servidor.atualizar_estado_rosto("pensando")

        self.assertEqual(3, broadcast.call_count)
        self.assertEqual(2, log.call_count)
        self.assertIn("inicial → ouvindo", log.call_args_list[0].args[0])
        self.assertIn("ouvindo → pensando", log.call_args_list[1].args[0])


if __name__ == "__main__":
    unittest.main()
