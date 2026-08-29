"""Testes unitários da deduplicação da curadoria, sem carregar modelos de embedding."""

import unittest
from unittest.mock import patch

from modulos import memoria


class TestaDeduplicacaoMemoria(unittest.TestCase):
    def test_extracao_usa_so_a_fala_do_usuario(self):
        falas = memoria.extrair_falas_usuario([
            "Usuário: fiz o Fluxer no servidor Linux\nLuna: então você trabalha com infraestrutura",
            "Usuário: tomei um banho e acordei\nLuna: você estava frustrado",
        ])
        self.assertEqual([
            "fiz o Fluxer no servidor Linux",
            "tomei um banho e acordei",
        ], falas)
        self.assertNotIn("infraestrutura", " ".join(falas))
        self.assertNotIn("frustrado", " ".join(falas))

    def test_candidato_exige_evidencia_literal(self):
        falas = ["fiz essa instância fechada e só eu posso aceitar alguém nela"]
        candidatos = memoria.validar_candidatos_memoria([
            {
                "fato": "mantém uma instância fechada do Fluxer",
                "tipo": "projeto",
                "duracao": "em_andamento",
                "evidencia": "fiz essa instância fechada",
            },
            {
                "fato": "trabalha profissionalmente com infraestrutura",
                "tipo": "fato",
                "duracao": "duravel",
                "evidencia": "trabalho com infraestrutura",
            },
        ], falas)
        self.assertEqual(1, len(candidatos))
        self.assertEqual("projeto", candidatos[0]["tipo"])

    def test_candidato_temporario_ou_sem_schema_e_rejeitado(self):
        falas = ["tomei um banho e acordei"]
        candidatos = memoria.validar_candidatos_memoria([
            {
                "fato": "tomou banho",
                "tipo": "evento",
                "duracao": "temporaria",
                "evidencia": "tomei um banho",
            },
            "tomou banho",
        ], falas)
        self.assertEqual([], candidatos)

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

    def test_metadados_chegam_a_fila_de_revisao(self):
        estado = {"marcador_ts": 0.0, "pendentes": [], "lixo": [], "recusados": []}
        with (patch.object(memoria, "carregar_mem_pendente", return_value=estado),
              patch.object(memoria, "salvar_mem_pendente"),
              patch("modulos.acompanhamentos.relacionado_a_ativo", return_value=False)):
            adicionados = memoria.mem_adicionar_candidatos([{
                "fato": "instalou o Fluxer no servidor",
                "tipo": "projeto",
                "duracao": "em_andamento",
                "evidencia": "fiz aqui no servidor do linux",
            }])
        self.assertEqual(1, adicionados)
        self.assertEqual("projeto", estado["pendentes"][0]["tipo"])
        self.assertEqual("fiz aqui no servidor do linux",
                         estado["pendentes"][0]["evidencia"])


if __name__ == "__main__":
    unittest.main()
