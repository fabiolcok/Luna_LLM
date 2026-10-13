import unittest

from modulos import avaliacoes


class TestaDiagnosticoTurno(unittest.TestCase):
    def _turno(self, contexto, **turno):
        identificador = avaliacoes.capturar_turno({"usuario": "e na agenda?", "luna": "Amanhã às 9h.", **turno})
        avaliacoes._turnos[identificador]["contexto"].update(contexto)
        self.addCleanup(avaliacoes._turnos.pop, identificador, None)
        return identificador

    def test_resposta_com_ferramenta(self):
        tid = self._turno({
            "ferramenta": {"nome": "ler_agenda_google", "sucesso": True, "segundos": 2.1, "argumentos": "{}"},
            "dados_origem": "Seus compromissos: ligar para o cliente às 9h" + "x" * 2000,
            "personalidade": 1, "caminho_prompt": "PROMPT_COMPLETO", "emocao": "EMOCAO",
            "canal_resposta": "texto", "memoria_chars": 507,
            "chamadas": [{"prompt_sistema_chars": 11194}],
            "roteador_segundos": 4.1, "persona_segundos": 4.4, "persona_tokens": 56,
        }, clima="carinho")
        r = avaliacoes.resumo_diagnostico(tid)
        self.assertEqual(r["origem"], "conversa")
        self.assertEqual(r["ferramenta"]["nome"], "ler_agenda_google")
        self.assertLessEqual(len(r["dados_origem"]), 600)
        self.assertEqual(r["personalidade"], "LUNA")
        self.assertEqual(r["sistema_chars"], 11194)
        self.assertEqual(r["tempos"], {"roteador": 4.1, "persona": 4.4})
        self.assertEqual(r["clima"], "carinho")

    def test_sem_ferramenta_nao_expoe_dados_de_origem(self):
        # Sem ferramenta, dados_origem não traz nada útil para mostrar.
        tid = self._turno({"dados_origem": "texto interno", "caminho_prompt": "ENXUTO_CANSACO"})
        r = avaliacoes.resumo_diagnostico(tid)
        self.assertIsNone(r["ferramenta"])
        self.assertEqual(r["dados_origem"], "")
        self.assertEqual(r["tempos"], {})

    def test_proativo_mostra_a_origem(self):
        tid = self._turno({}, usuario="", origem_proativa="radar_rss")
        self.assertEqual(avaliacoes.resumo_diagnostico(tid)["origem"], "radar_rss")

    def test_resposta_que_nao_existe_mais(self):
        self.assertIsNone(avaliacoes.resumo_diagnostico("inexistente"))
        self.assertIsNone(avaliacoes.resumo_diagnostico(None))


if __name__ == "__main__":
    unittest.main()
