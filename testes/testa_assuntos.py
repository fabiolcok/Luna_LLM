"""Testes do estado local de assuntos em andamento, sem usar LLM nem Obsidian."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from modulos import assuntos


class TestaAssuntosEmAndamento(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.caminho = Path(self.tmp.name) / "assuntos.json"
        self.patch = patch.object(assuntos, "CAMINHO", self.caminho)
        self.patch.start()

    def tearDown(self):
        self.patch.stop()
        self.tmp.cleanup()

    def test_cria_e_atualiza_o_mesmo_assunto_por_id(self):
        self.assertTrue(assuntos.registrar_candidato({
            "fato": "instalou o Fluxer no Ubuntu", "assunto": "Fluxer no Ubuntu",
            "status": "aberto", "evidencia": "fiz aqui no servidor",
        }))
        criado = assuntos.listar()[0]
        self.assertTrue(assuntos.registrar_candidato({
            "fato": "a instância continua sem outros usuários", "assunto_id": criado["id"],
            "assunto": "Fluxer no Ubuntu", "status": "aberto",
            "evidencia": "ninguém quis vir",
        }))
        itens = assuntos.listar()
        self.assertEqual(1, len(itens))
        self.assertEqual("a instância continua sem outros usuários", itens[0]["estado_atual"])
        self.assertEqual(2, len(itens[0]["historico"]))

    def test_assunto_so_volta_quando_a_mensagem_casa(self):
        assuntos.registrar_candidato({
            "fato": "instalou o Fluxer no Ubuntu", "assunto": "Fluxer no Ubuntu",
            "status": "aberto",
        })
        self.assertEqual(1, len(assuntos.buscar_relacionados("voltei a mexer no Fluxer")))
        self.assertEqual([], assuntos.buscar_relacionados("vou preparar o jantar"))
        self.assertEqual([], assuntos.buscar_relacionados("estou vendo outro servidor"))

    def test_status_concluido_fica_registrado(self):
        assuntos.registrar_candidato({
            "fato": "desistiu de manter a instância", "assunto": "Fluxer no Ubuntu",
            "status": "concluido",
        })
        self.assertEqual("concluido", assuntos.listar()[0]["status"])

    def test_cumprimento_nao_retoma_assunto_por_palavra_solta(self):
        assuntos.registrar_candidato({
            "fato": "Busca um notebook para plantões com boa bateria, de dia ou à noite",
            "assunto": "Compra de Notebook", "status": "aberto",
        })
        for pergunta in ("Boa noite.", "Boa tarde!", "Bom dia", "boa noite, Luna",
                         "oi, tudo bem?", "Olá", "eae"):
            with self.subTest(pergunta=pergunta):
                self.assertEqual([], assuntos.buscar_relacionados(pergunta))
                self.assertEqual("", assuntos.contexto_relacionado(pergunta))

    def test_saudacao_com_assunto_explicito_preserva_recuperacao(self):
        assuntos.registrar_candidato({
            "fato": "Busca um notebook para plantões com boa bateria",
            "assunto": "Compra de Notebook", "status": "aberto",
        })
        for pergunta in ("Boa noite, voltei a procurar o notebook",
                         "Bom dia, notebook com boa bateria?", "e o notebook?"):
            with self.subTest(pergunta=pergunta):
                self.assertEqual(1, len(assuntos.buscar_relacionados(pergunta)))


if __name__ == "__main__":
    unittest.main()
