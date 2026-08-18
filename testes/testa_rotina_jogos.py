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

    def test_declaracao_guarda_estado_e_opiniao_sem_deduzir_um_do_outro(self):
        retorno = rotina_jogos.registrar_declaracao(
            "Hellblade II", "zerado", "Gostei da narrativa, mas achei o combate repetitivo.",
            self.agora,
        )
        self.assertIn("rotina de Hellblade II atualizada", retorno)

        estado = json.loads(self.caminho.read_text(encoding="utf-8"))
        jogo = estado["jogos"]["hellblade ii"]
        self.assertEqual("zerado", jogo["estado"])
        self.assertEqual(1, len(jogo["opinioes"]))
        self.assertIn("combate repetitivo", jogo["opinioes"][0]["texto"])

        rotina_jogos.registrar_declaracao("Outro jogo", opiniao="Gostei da trilha.", agora=self.agora)
        estado = json.loads(self.caminho.read_text(encoding="utf-8"))
        self.assertIsNone(estado["jogos"]["outro jogo"]["estado"])

    def test_abertura_associa_lista_importada_ao_appid(self):
        rotina_jogos.registrar_declaracao("Hollow Knight", "zerado", agora=self.agora)
        abertura = rotina_jogos.registrar_abertura(
            "367520", "Hollow Knight", self.agora + datetime.timedelta(days=1))

        estado = json.loads(self.caminho.read_text(encoding="utf-8"))
        self.assertNotIn("hollow knight", estado["jogos"])
        self.assertEqual("zerado", estado["jogos"]["367520"]["estado"])
        self.assertIn("declarou este jogo como zerado", rotina_jogos.contexto_pessoal(abertura))

    def test_opiniao_duplicada_nao_infla_historico(self):
        for _ in range(2):
            rotina_jogos.registrar_declaracao(
                "Portal 2", opiniao="Os puzzles são excelentes.", agora=self.agora)
        estado = json.loads(self.caminho.read_text(encoding="utf-8"))
        self.assertEqual(1, len(estado["jogos"]["portal 2"]["opinioes"]))

    def test_platina_fica_separada_do_estado_zerado(self):
        rotina_jogos.registrar_declaracao(
            "Hollow Knight", "zerado", agora=self.agora, platinado=True)
        estado = json.loads(self.caminho.read_text(encoding="utf-8"))
        jogo = estado["jogos"]["hollow knight"]
        self.assertEqual("zerado", jogo["estado"])
        self.assertTrue(jogo["platinado"])

    def test_rede_de_seguranca_recupera_declaracao_que_roteador_perdeu(self):
        rotina_jogos.importar_estados(["Hollow Knight", "Hollow Knight: Silksong"])
        declaracao = rotina_jogos.detectar_declaracao(
            "mas o hollow knight, eu zerei ele e ainda por cima platinei.")
        self.assertEqual("Hollow Knight", declaracao["nome_jogo"])
        self.assertEqual("zerado", declaracao["estado_jogo"])
        self.assertTrue(declaracao["platinado"])
        self.assertEqual("", declaracao["opiniao"])

    def test_intencao_de_platinar_significa_que_ainda_nao_platinou(self):
        rotina_jogos.importar_estados(["Hollow Knight: Silksong"])
        rotina_jogos.registrar_abertura("1030300", "Hollow Knight: Silksong", self.agora)
        declaracao = rotina_jogos.detectar_declaracao(
            "ainda faltam algumas conquistas, queria platinar esse jogo também.")
        self.assertEqual("Hollow Knight: Silksong", declaracao["nome_jogo"])
        self.assertFalse(declaracao["platinado"])

        declaracao = rotina_jogos.detectar_declaracao(
            "ainda faltam algumas conquistas no Hollow Knight: Silksong, queria platinar.")
        self.assertEqual("Hollow Knight: Silksong", declaracao["nome_jogo"])
        self.assertFalse(declaracao["platinado"])

    def test_pergunta_ou_mencao_nao_vira_declaracao(self):
        rotina_jogos.importar_estados(["Hollow Knight"])
        self.assertIsNone(rotina_jogos.detectar_declaracao(
            "Você acha Hollow Knight difícil?"))
        self.assertIsNone(rotina_jogos.detectar_declaracao(
            "Quantas conquistas existem em Hollow Knight?"))

    def test_pronome_nao_escolhe_quando_estado_tem_dois_jogos_abertos(self):
        rotina_jogos.registrar_abertura("1", "Hollow Knight", self.agora)
        rotina_jogos.registrar_abertura("2", "Portal 2", self.agora)
        self.assertIsNone(rotina_jogos.detectar_declaracao(
            "Zerei esse jogo e ainda platinei."))

    def test_nome_vago_do_roteador_vira_unico_jogo_aberto(self):
        rotina_jogos.registrar_abertura("1030300", "Hollow Knight: Silksong", self.agora)
        resposta = rotina_jogos.registrar_declaracao(
            "Não especificado", platinado=False, agora=self.agora)
        self.assertIn("rotina de Hollow Knight: Silksong atualizada", resposta)
        estado = json.loads(self.caminho.read_text(encoding="utf-8"))
        self.assertNotIn("não especificado", estado["jogos"])
        self.assertFalse(estado["jogos"]["1030300"]["platinado"])


if __name__ == "__main__":
    unittest.main()
