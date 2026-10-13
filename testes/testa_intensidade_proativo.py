import unittest
from unittest.mock import patch

from modulos import proativa


class TestaIntensidadeProativo(unittest.TestCase):
    def setUp(self):
        self.addCleanup(proativa.configurar_intensidade, proativa.INTENSIDADE_PADRAO)
        self.addCleanup(proativa.registrar_interacao)

    def test_niveis_ajustam_espera_e_tentativas(self):
        proativa.configurar_intensidade("discreto")
        self.assertEqual((proativa._CD_PROATIVO_MIN, proativa._CD_PROATIVO_MAX), (240, 480))
        self.assertEqual(proativa.MAX_TENTATIVAS, 3)
        proativa.configurar_intensidade("normal")
        self.assertEqual((proativa._CD_PROATIVO_MIN, proativa._CD_PROATIVO_MAX), (60, 150))
        self.assertEqual(proativa.MAX_TENTATIVAS, 6)

    def test_nivel_invalido_nao_muda_nada(self):
        proativa.configurar_intensidade("discreto")
        for valor in ("desligado", "alto", None, True, 2):
            with self.assertRaises(ValueError):
                proativa.configurar_intensidade(valor)
        self.assertEqual(proativa.intensidade_atual(), "discreto")

    def test_suspensao_respeita_o_limite_do_nivel(self):
        proativa.configurar_intensidade("normal")
        proativa.registrar_interacao()
        for _ in range(5):
            proativa.registrar_tentativa()
        self.assertFalse(proativa._suspensa)   # o antigo limite de 3 já teria suspendido
        proativa.registrar_tentativa()
        self.assertTrue(proativa._suspensa)

    def test_suspender_funciona_em_qualquer_nivel(self):
        for nivel in proativa.INTENSIDADES:
            proativa.configurar_intensidade(nivel)
            proativa.registrar_interacao()
            proativa.suspender()
            self.assertTrue(proativa._suspensa, nivel)

    def test_espera_em_curso_obedece_o_nivel_novo(self):
        proativa.configurar_intensidade("normal")
        with patch.object(proativa, "_cd_proativo_atual", 90.0):
            proativa.configurar_intensidade("discreto")
            self.assertGreaterEqual(proativa._cd_proativo_atual, 240)


class TestaConfigWeb(unittest.TestCase):
    def test_servidor_rejeita_intensidade_invalida(self):
        import servidor
        recebidos = []
        estado = dict(servidor._estado_config)
        self.addCleanup(servidor._estado_config.update, estado)
        with patch.object(servidor, "_broadcast", recebidos.append), \
             patch.object(servidor, "_salvar_config"), \
             patch.dict(servidor._config_handlers, {"proativo_intensidade": proativa.configurar_intensidade}):
            servidor._aplicar_config({"config": "proativo_intensidade", "valor": "turbo"})
            self.assertEqual(servidor._estado_config["proativo_intensidade"], estado["proativo_intensidade"])
            servidor._aplicar_config({"config": "proativo_intensidade", "valor": "discreto"})
            self.assertEqual(servidor._estado_config["proativo_intensidade"], "discreto")
            self.assertEqual(proativa.intensidade_atual(), "discreto")
        proativa.configurar_intensidade(proativa.INTENSIDADE_PADRAO)


if __name__ == "__main__":
    unittest.main()
