"""Testes unitários da deduplicação da curadoria, sem carregar modelos de embedding."""

import unittest
from unittest.mock import patch

from modulos import memoria


class TestaDeduplicacaoMemoria(unittest.TestCase):
    def test_repeticao_normalizada_nem_chama_llm(self):
        confirmadas = [("2026-08-10", "Está pensando em comprar um Steam Deck.")]
        llm = unittest.mock.Mock()
        with patch.object(memoria, "_memorias_episodicas_confirmadas",
                          return_value=confirmadas):
            resultado = memoria.mem_filtrar_candidatos(
                ["  ESTA pensando em comprar um Steam Deck!  "], llm)
        self.assertEqual([], resultado)
        llm.assert_not_called()

    def test_parafrase_rejeitada_e_atualizacao_aceita(self):
        confirmadas = [("2026-08-10", "Quer comprar um Steam Deck")]
        semelhantes = ["Quer comprar um Steam Deck"]
        llm = unittest.mock.Mock(return_value='{"aceitar": [1]}')
        with (patch.object(memoria, "_memorias_episodicas_confirmadas",
                           return_value=confirmadas),
              patch.object(memoria, "_memorias_semelhantes_para_dedup",
                           return_value=semelhantes)):
            resultado = memoria.mem_filtrar_candidatos([
                "Ainda pensa em comprar um Steam Deck",
                "Comprou um Steam Deck",
            ], llm)
        self.assertEqual(["Comprou um Steam Deck"], resultado)

    def test_falha_do_classificador_preserva_candidato(self):
        llm = unittest.mock.Mock(return_value="resposta inválida")
        with (patch.object(memoria, "_memorias_episodicas_confirmadas", return_value=[]),
              patch.object(memoria, "_memorias_semelhantes_para_dedup",
                           return_value=["Fato parecido"])):
            resultado = memoria.mem_filtrar_candidatos(["Possível atualização"], llm)
        self.assertEqual(["Possível atualização"], resultado)

    def test_acompanhamento_ativo_nao_vira_segundo_cartao_de_memoria(self):
        estado = {"marcador_ts": 0.0, "pendentes": [], "lixo": [], "recusados": []}
        salvar = unittest.mock.Mock()
        with (patch.object(memoria, "carregar_mem_pendente", return_value=estado),
              patch.object(memoria, "salvar_mem_pendente", salvar),
              patch("modulos.acompanhamentos.relacionado_a_ativo", return_value=True)):
            adicionados = memoria.mem_adicionar_candidatos([
                "Amanhã vai levar o PC para a assistência"
            ])
        self.assertEqual(0, adicionados)
        salvar.assert_not_called()


if __name__ == "__main__":
    unittest.main()
