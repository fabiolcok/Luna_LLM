import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from modulos import conclusao_tarefas, obsidian


class TestConclusaoTarefas(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.vault = os.path.join(self.tmp.name, "vault")
        os.makedirs(self.vault)
        self.estado = Path(self.tmp.name) / "estado.json"
        self.patches = [
            mock.patch.object(obsidian, "_VAULT", self.vault),
            mock.patch.object(conclusao_tarefas, "_VAULT", self.vault),
            mock.patch.object(conclusao_tarefas, "CAMINHO_ESTADO", self.estado),
            mock.patch.object(conclusao_tarefas, "_notificar"),
        ]
        for patch in self.patches:
            patch.start()

    def tearDown(self):
        for patch in reversed(self.patches):
            patch.stop()
        self.tmp.cleanup()

    def _nota(self, nome="Contas mensais.md", texto="- [ ] Parcela carro\n"):
        caminho = os.path.join(self.vault, nome)
        with open(caminho, "w", encoding="utf-8", newline="") as arquivo:
            arquivo.write(texto)
        return caminho

    def test_so_edita_depois_da_confirmacao(self):
        caminho = self._nota()
        pergunta = conclusao_tarefas.propor("parcela carro")
        self.assertIn("Confirmar como concluída?", pergunta)
        self.assertIn("[ ]", Path(caminho).read_text(encoding="utf-8"))
        resposta = conclusao_tarefas.interceptar_resposta("sim, pode marcar")
        self.assertIn("marquei", resposta)
        self.assertIn("[x] Parcela carro", Path(caminho).read_text(encoding="utf-8"))

    def test_cancelar_nao_edita(self):
        caminho = self._nota()
        conclusao_tarefas.propor("parcela carro")
        resposta = conclusao_tarefas.interceptar_resposta("não, deixa pra lá")
        self.assertIn("não alterei", resposta)
        self.assertIn("[ ] Parcela carro", Path(caminho).read_text(encoding="utf-8"))

    def test_ambiguidade_nao_cria_confirmacao(self):
        self._nota("Casa.md", "- [ ] Pagar internet\n")
        self._nota("Escritório.md", "- [ ] Pagar internet\n")
        resposta = conclusao_tarefas.propor("pagar internet")
        self.assertIn("mais de uma tarefa", resposta)
        self.assertIsNone(conclusao_tarefas.estado_interface()["confirmacao"])

    def test_nota_alterada_recusa_edicao(self):
        caminho = self._nota()
        conclusao_tarefas.propor("parcela carro")
        Path(caminho).write_text("- [ ] Outra tarefa\n", encoding="utf-8")
        resposta = conclusao_tarefas.interceptar_resposta("confirma")
        self.assertIn("nota mudou", resposta)
        self.assertNotIn("[x]", Path(caminho).read_text(encoding="utf-8"))

    def test_novo_pedido_invalido_limpa_confirmacao_antiga(self):
        self._nota()
        conclusao_tarefas.propor("parcela carro")
        self.assertIsNotNone(conclusao_tarefas.estado_interface()["confirmacao"])
        conclusao_tarefas.propor("tarefa inexistente")
        self.assertIsNone(conclusao_tarefas.estado_interface()["confirmacao"])


if __name__ == "__main__":
    unittest.main()
