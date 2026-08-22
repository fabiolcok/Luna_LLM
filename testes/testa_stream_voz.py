import unittest

from modulos.stream_voz import SegmentadorFrases


class SegmentadorFrasesTeste(unittest.TestCase):
    def test_incremental_nao_repete_frases(self):
        s = SegmentadorFrases()
        self.assertEqual(s.receber("Primeira frase. Ainda ger"), ["Primeira frase."])
        self.assertEqual(s.receber("Primeira frase. Ainda gerando a segunda! Resto"),
                         ["Ainda gerando a segunda!"])
        self.assertEqual(s.finalizar("Primeira frase. Ainda gerando a segunda! Resto final"),
                         ["Resto final"])

    def test_nao_corta_abreviacao_nem_decimal(self):
        s = SegmentadorFrases()
        texto = "Falei com o Dr. Silva sobre a versão 3.5. Deu certo. Próxima"
        self.assertEqual(s.receber(texto),
                         ["Falei com o Dr. Silva sobre a versão 3.5.", "Deu certo."])
        self.assertEqual(s.finalizar(texto), ["Próxima"])

    def test_final_curto_tambem_e_falado(self):
        s = SegmentadorFrases()
        self.assertEqual(s.receber("Sim."), [])  # stream ainda pode acrescentar metadados
        self.assertEqual(s.finalizar("Sim."), ["Sim."])


if __name__ == "__main__":
    unittest.main()
