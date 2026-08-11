"""Regressões do estado compartilhado por botão, texto, STT e Telegram."""

import datetime as dt
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from modulos import acompanhamentos


class TestaAcompanhamentos(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.raiz = Path(self.tmp.name)
        self.vault = self.raiz / "vault"
        (self.vault / "Luna").mkdir(parents=True)
        self.agora = dt.datetime(2026, 8, 11, 14, 30)
        self.patches = [
            patch.object(acompanhamentos, "CAMINHO_ESTADO", self.raiz / "estado.json"),
            patch.object(acompanhamentos, "_VAULT", str(self.vault)),
            patch.object(acompanhamentos, "_agora", return_value=self.agora),
            patch.object(acompanhamentos, "_notificar", return_value=None),
        ]
        for p in self.patches:
            p.start()

    def tearDown(self):
        for p in reversed(self.patches):
            p.stop()
        self.tmp.cleanup()

    def _estado_cru(self):
        return json.loads(acompanhamentos.CAMINHO_ESTADO.read_text(encoding="utf-8"))

    def test_proposta_nao_salva_antes_da_confirmacao(self):
        retorno = acompanhamentos.propor("saber como ficou o PC na assistência")
        estado = acompanhamentos.estado_interface()

        self.assertTrue(retorno.startswith("ACOMPANHAMENTO_PROPOSTO:"))
        self.assertEqual([], estado["ativos"])
        self.assertEqual("proposta", estado["confirmacao"]["tipo"])

    def test_sim_por_texto_ou_stt_confirma_a_mesma_proposta(self):
        acompanhamentos.propor("saber como ficou o PC na assistência", "amanhã às 10")
        resposta = acompanhamentos.interceptar_resposta("Pode, me pergunta amanhã às 10.")
        estado = acompanhamentos.estado_interface()

        self.assertIn("Vou perguntar", resposta)
        self.assertIsNone(estado["confirmacao"])
        self.assertEqual(1, len(estado["ativos"]))
        self.assertEqual("2026-08-12T10:00:00", estado["ativos"][0]["perguntar_em"])

    def test_data_sem_hora_nao_ganha_horario_inventado(self):
        acompanhamentos.propor("saber como ficou o PC", "amanhã")
        acompanhamentos.interceptar_resposta("sim")

        quando = acompanhamentos.estado_interface()["ativos"][0]["perguntar_em"]
        self.assertEqual("2026-08-12T19:00:00", quando)

    def test_pode_agendar_em_minutos_para_retorno_curto(self):
        acompanhamentos.propor("saber como terminou o teste", "daqui a 10 minutos")
        acompanhamentos.interceptar_resposta("sim")

        quando = acompanhamentos.estado_interface()["ativos"][0]["perguntar_em"]
        self.assertEqual("2026-08-11T14:40:00", quando)

    def test_negativa_descarta_sem_criar_acompanhamento(self):
        acompanhamentos.propor("saber como ficou o PC na assistência")
        resposta = acompanhamentos.interceptar_resposta("Não precisa, só comentei.")

        self.assertIn("só um comentário", resposta)
        self.assertEqual([], acompanhamentos.estado_interface()["ativos"])

    def test_agenda_lembrete_e_cotidiano_nao_podem_ser_propostos(self):
        self.assertFalse(acompanhamentos.pode_propor("Me lembra amanhã de pagar o boleto"))
        self.assertFalse(acompanhamentos.pode_propor("Coloca dentista na agenda"))
        self.assertFalse(acompanhamentos.pode_propor("Vou comprar um jogo na Steam"))
        self.assertTrue(acompanhamentos.pode_propor("Amanhã vou levar o PC para a assistência"))

    def test_id_velho_nao_confirma_proposta_nova(self):
        acompanhamentos.propor("saber como ficou o PC na assistência")
        self.assertIsNone(acompanhamentos.resolver("confirmar", "id-velho"))
        self.assertEqual("proposta", acompanhamentos.estado_interface()["confirmacao"]["tipo"])

    def test_segunda_proposta_nao_substitui_decisao_pendente(self):
        acompanhamentos.propor("saber como ficou o PC na assistência")
        retorno = acompanhamentos.propor("saber como foi a entrevista")

        self.assertTrue(retorno.startswith("ACOMPANHAMENTO_DECISAO_PENDENTE:"))
        self.assertIn("PC na assistência",
                      acompanhamentos.estado_interface()["confirmacao"]["assunto"])

    def test_retorno_pode_ser_resolvido_adiado_ou_esquecido(self):
        acompanhamentos.propor("saber como ficou o PC na assistência")
        acompanhamentos.interceptar_resposta("sim")
        item = acompanhamentos.estado_interface()["ativos"][0]

        self.assertTrue(acompanhamentos.registrar_pergunta(item["id"], self.agora))
        self.assertIn("volto nisso", acompanhamentos.interceptar_resposta("Ainda não, semana que vem"))
        adiado = acompanhamentos.estado_interface()["ativos"][0]
        self.assertEqual("2026-08-18T19:00:00", adiado["perguntar_em"])

        acompanhamentos.registrar_pergunta(item["id"], self.agora)
        self.assertIn("resolvido", acompanhamentos.interceptar_resposta("Deu certo, resolvido"))
        self.assertEqual([], acompanhamentos.estado_interface()["ativos"])

    def test_desfecho_com_detalhes_fecha_estado_mas_continua_conversa(self):
        acompanhamentos.propor("saber como ficou o PC na assistência")
        acompanhamentos.interceptar_resposta("sim")
        item = acompanhamentos.estado_interface()["ativos"][0]
        acompanhamentos.registrar_pergunta(item["id"], self.agora)

        resposta_direta = acompanhamentos.interceptar_resposta(
            "Deu certo, trocaram a fonte e o PC voltou a ligar."
        )

        self.assertIsNone(resposta_direta)
        self.assertEqual([], acompanhamentos.estado_interface()["ativos"])

    def test_proposta_expirada_nao_rouba_um_sim_da_conversa(self):
        acompanhamentos.propor("saber como ficou o PC na assistência")
        with patch.object(acompanhamentos, "_agora",
                          return_value=self.agora + dt.timedelta(minutes=16)):
            self.assertIsNone(acompanhamentos.interceptar_resposta("sim"))

    def test_obsidian_recebe_apenas_acompanhamento_confirmado(self):
        acompanhamentos.propor("saber como ficou o PC na assistência")
        nota = self.vault / "Luna" / "Acompanhamentos.md"
        self.assertIn("Nenhum acompanhamento", nota.read_text(encoding="utf-8"))

        acompanhamentos.interceptar_resposta("sim")
        texto = nota.read_text(encoding="utf-8")
        self.assertIn("- [ ] saber como ficou o PC", texto)
        self.assertIn("Próxima pergunta", texto)

    def test_assunto_ativo_bloqueia_curadoria_e_retomada_duplicadas(self):
        acompanhamentos.propor("saber como ficou o PC na assistência")
        acompanhamentos.interceptar_resposta("sim")

        self.assertTrue(acompanhamentos.relacionado_a_ativo(
            "Amanhã vai levar o PC para a assistência técnica"
        ))
        self.assertFalse(acompanhamentos.relacionado_a_ativo(
            "Comprou um jogo de corrida na Steam"
        ))


if __name__ == "__main__":
    unittest.main()
