import os
import tempfile
import unittest
from unittest import mock

from modulos import obsidian, pendencias


class TestPendencias(unittest.TestCase):
    def test_lista_somente_checkboxes_abertas(self):
        with tempfile.TemporaryDirectory() as vault:
            pasta = os.path.join(vault, "Pessoal")
            os.makedirs(pasta)
            with open(os.path.join(pasta, "Contas mensais.md"), "w", encoding="utf-8") as arquivo:
                arquivo.write("- [x] Internet\n- [ ] Parcela carro\n- texto comum\n")
            with mock.patch.object(obsidian, "_VAULT", vault):
                resultado = obsidian.listar_tarefas_pendentes("contas mensais")
        self.assertIn("Parcela carro", resultado)
        self.assertNotIn("Internet", resultado)
        self.assertNotIn("texto comum", resultado)

    def test_consulta_ampla_separa_fontes(self):
        with mock.patch.object(obsidian, "listar_tarefas_pendentes", return_value="- tarefa"), \
             mock.patch.object(pendencias, "ler_agenda_google", return_value="- compromisso"), \
             mock.patch.object(pendencias, "_acompanhamentos_abertos", return_value="- retorno"):
            resultado = pendencias.consultar()
        self.assertIn("TAREFAS ABERTAS NO OBSIDIAN", resultado)
        self.assertIn("COMPROMISSOS FUTUROS NA AGENDA", resultado)
        self.assertIn("ACOMPANHAMENTOS ESPERANDO DESFECHO", resultado)

    def test_assunto_especifico_nao_mistura_agenda(self):
        with mock.patch.object(obsidian, "listar_tarefas_pendentes", return_value="- Parcela carro") as listar, \
             mock.patch.object(pendencias, "ler_agenda_google") as agenda:
            resultado = pendencias.consultar("contas mensais")
        listar.assert_called_once_with("contas mensais")
        agenda.assert_not_called()
        self.assertIn("Parcela carro", resultado)

    def test_assunto_desconhecido_nao_devolve_tarefas_alheias(self):
        with tempfile.TemporaryDirectory() as vault:
            with open(os.path.join(vault, "Contas.md"), "w", encoding="utf-8") as arquivo:
                arquivo.write("- [ ] Parcela carro\n")
            with mock.patch.object(obsidian, "_VAULT", vault):
                resultado = obsidian.listar_tarefas_pendentes("reforma cozinha")
        self.assertIn("Nenhuma tarefa aberta", resultado)
        self.assertNotIn("Parcela carro", resultado)


if __name__ == "__main__":
    unittest.main()
