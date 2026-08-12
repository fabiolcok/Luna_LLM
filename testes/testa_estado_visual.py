"""Contrato do diagnóstico de estados enviados ao mascote web."""

import unittest
from pathlib import Path
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

    def test_atalhos_de_voz_fecham_o_ciclo_visual(self):
        fonte = (Path(__file__).parents[1] / "main.py").read_text(encoding="utf-8")
        for fala in (
            "Modo jogo ativado. Pode jogar em paz, bot.",
            "Pausado.",
            "Pulando.",
            "Nenhum texto selecionado para traduzir.",
            "Mutando.",
            "Som ativado.",
        ):
            self.assertIn(f'_falar_atalho("{fala}")', fonte)

    def test_fala_proativa_troca_sonar_por_falando_e_depois_repousa(self):
        fonte = (Path(__file__).parents[1] / "modulos" / "proativa.py").read_text(encoding="utf-8")
        self.assertIn('ao_iniciar=_iniciar_visual_fala_proativa', fonte)
        self.assertIn('ao_terminar=_terminar_visual_fala_proativa', fonte)
        self.assertIn('_srv.atualizar_status("◗ Por aqui")', fonte)
        self.assertIn('_srv.atualizar_estado_rosto("falando")', fonte)
        self.assertIn('_srv.atualizar_estado_rosto("dormindo")', fonte)


if __name__ == "__main__":
    unittest.main()
