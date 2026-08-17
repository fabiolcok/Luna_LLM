"""Testes puros do agregador; nenhuma API externa ou estado real é tocado."""

import unittest
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parents[1]))

from modulos import briefing


class TestaBriefing(unittest.TestCase):
    def test_reune_fontes_em_ordem_sem_consumir_estado(self):
        with (
            patch.object(briefing, "obter_previsao_tempo", return_value="23 graus"),
            patch.object(briefing, "ler_agenda_google", return_value="dentista amanhã"),
            patch.object(briefing.animes, "consultar", return_value="episódio 8 saiu"),
            patch.object(briefing, "_ler_acompanhamentos", return_value="nenhum pendente"),
            patch.object(briefing, "_ler_nota", side_effect=lambda nome: f"nota {nome}"),
        ):
            resposta = briefing.consultar()

        self.assertIn("## CLIMA AGORA\n23 graus", resposta)
        self.assertIn("## AGENDA (PRÓXIMOS COMPROMISSOS)\ndentista amanhã", resposta)
        self.assertIn("## ANIMES RECENTES\nepisódio 8 saiu", resposta)
        self.assertLess(resposta.index("## CLIMA"), resposta.index("## AGENDA"))
        self.assertLess(resposta.index("## AGENDA"), resposta.index("## ANIMES"))

    def test_falha_isolada_e_texto_gigante_nao_derrubam_briefing(self):
        def falhar():
            raise RuntimeError("sem rede")

        with (
            patch.object(briefing, "obter_previsao_tempo", side_effect=falhar),
            patch.object(briefing, "ler_agenda_google", return_value="agenda ok"),
            patch.object(briefing.animes, "consultar", return_value="anime ok"),
            patch.object(briefing, "_ler_acompanhamentos", return_value="acomp ok"),
            patch.object(briefing, "_ler_nota", return_value="x" * 3000),
        ):
            resposta = briefing.consultar()

        self.assertIn("fonte indisponível (RuntimeError)", resposta)
        self.assertIn("agenda ok", resposta)
        self.assertIn("[restante omitido]", resposta)
        self.assertLess(len(resposta), 4000)


if __name__ == "__main__":
    unittest.main()
