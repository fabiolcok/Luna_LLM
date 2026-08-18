import unittest

from modulos import anotacoes


class TestSalvarObsidian(unittest.TestCase):
    def test_extrai_titulo_e_conteudo_sem_envelope(self):
        mensagem = (
            "ow, tô com uma ideia aqui.\n\n"
            "deixa anotado por favor:\n\n"
            "título: teste\n\n"
            "conteúdo testando o módulo de salvar."
        )
        conteudo, titulo = anotacoes.dados_para_anotar(mensagem, "título inventado")
        self.assertEqual(titulo, "teste")
        self.assertEqual(conteudo, "testando o módulo de salvar.")

    def test_preserva_texto_livre_depois_do_comando_inicial(self):
        conteudo, titulo = anotacoes.dados_para_anotar(
            "anota pra mim: comparar Kokoro com outra voz", "Comparar vozes")
        self.assertEqual(conteudo, "comparar Kokoro com outra voz")
        self.assertEqual(titulo, "Comparar vozes")

    def test_reacao_curta_aponta_para_fala_anterior(self):
        self.assertTrue(anotacoes.pedido_anaforico("boa ideia, deixa isso anotado por favor"))
        historico = [
            {"role": "user", "content": "Como poderíamos melhorar isso?"},
            {"role": "assistant", "content": "Podemos criar um radar de encomendas por código de rastreio."},
        ]
        anterior = anotacoes.contexto_anterior(
            historico, "boa ideia, deixa isso anotado por favor")
        self.assertEqual(
            anterior,
            "Ideia discutida:\nComo poderíamos melhorar isso?\n\n"
            "Considerações:\nPodemos criar um radar de encomendas por código de rastreio.",
        )

    def test_adiamento_vago_continua_apontando_para_conversa(self):
        self.assertTrue(anotacoes.pedido_anaforico(
            "deixa anotado, vou ver isso mais pra frente"))
        self.assertTrue(anotacoes.pedido_anaforico(
            "entendi, então por agora, deixa anotado."))

    def test_sinonimos_referenciais_apontam_para_conversa(self):
        for pedido in ("escreve isso", "grava isso aí", "aponta isso", "coloca nas notas"):
            with self.subTest(pedido=pedido):
                self.assertTrue(anotacoes.pedido_anaforico(pedido))

    def test_mensagem_com_ideia_nova_nao_vira_referencia(self):
        self.assertFalse(anotacoes.pedido_anaforico(
            "boa ideia, anota também que o radar precisa avisar no Telegram"))

    def test_origem_distingue_os_tres_canais(self):
        self.assertEqual(anotacoes.origem(True, True), "web")
        self.assertEqual(anotacoes.origem(False, True), "voz")
        self.assertEqual(anotacoes.origem(True, False), "telegram")


if __name__ == "__main__":
    unittest.main()
