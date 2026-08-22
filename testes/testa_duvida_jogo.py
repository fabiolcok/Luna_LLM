import unittest

from modulos.intencao_gameplay import contexto_gameplay_anterior, validar_pedido_gameplay
from modulos import rotina_jogos


class IntencaoGameplayTeste(unittest.TestCase):
    def test_comentario_airbuster_nao_vira_tutorial(self):
        texto = "Estou em um chefão, acho que é o Airbuster, parei um pouco, mas estou gostando."
        self.assertFalse(validar_pedido_gameplay(texto, "como derrotar o Airbuster?"))
        self.assertFalse(validar_pedido_gameplay(texto, "estou em um chefão"))

    def test_pergunta_explicita_ativa(self):
        texto = "Como derroto o Airbuster no Final Fantasy VII Remake?"
        self.assertTrue(validar_pedido_gameplay(texto, texto))
        self.assertTrue(validar_pedido_gameplay(
            "Tem alguma dica para esse chefe?", "alguma dica para esse chefe?"))

    def test_followup_herda_pergunta_do_usuario(self):
        historico = [
            {"role": "user", "content": "Como derroto o Airbuster?"},
            {"role": "assistant", "content": "Use eletricidade e guarde MP.",
             "_ferramenta": "duvida_do_jogo", "_jogo": "Final Fantasy VII Remake"},
        ]
        self.assertTrue(validar_pedido_gameplay("E na segunda fase", "E na segunda fase", historico))
        self.assertEqual(contexto_gameplay_anterior(historico)["nome_jogo"],
                         "Final Fantasy VII Remake")

    def test_persona_sozinha_nao_autoriza(self):
        historico = [
            {"role": "assistant", "content": "Você travou no Airbuster?"},
        ]
        self.assertFalse(validar_pedido_gameplay(
            "E na segunda fase", "E na segunda fase", historico))

    def test_opiniao_preserva_jogo_identificado_pelo_roteador(self):
        declaracao = rotina_jogos.detectar_declaracao(
            "Parei um pouco, mas estou gostando.",
            nome_contexto="Final Fantasy VII Remake",
        )
        self.assertEqual(declaracao["nome_jogo"], "Final Fantasy VII Remake")
        self.assertEqual(declaracao["opiniao"], "Parei um pouco, mas estou gostando.")


if __name__ == "__main__":
    unittest.main()
