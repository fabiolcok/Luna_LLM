"""Reproduz a leitura indevida de Memoria.md sem consultar notas ou bancos reais."""
from contextlib import ExitStack
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from modulos.intencao_memoria import pergunta_de_lembranca

PERGUNTA = "Você lembra o que estava impedindo o acesso externo ao meu servidor?"


class TestaIntencaoMemoria(unittest.TestCase):
    def test_retoma_conversa_sem_depender_do_assunto(self):
        for texto in (
            PERGUNTA, "vc lembra do problema que te contei?",
            "Lembra o que faltava para abrir as portas?",
            "Luna, lembra de qual jogo eu falei?",
            "Você se recorda do problema com o provedor?",
            "O que te contei sobre o modem?",
        ):
            with self.subTest(texto=texto):
                self.assertTrue(pergunta_de_lembranca(texto))

    def test_preserva_leitura_de_notas_e_acoes(self):
        for texto in (
            "Mostra a nota Memoria.md", "Você lembra das minhas anotações?",
            "Você lembra do servidor? Pode abrir a nota no Obsidian?",
            "Você lembra do modem? Pode pesquisar isso agora?",
            "Anota que meu modem está em CGNAT.",
            "Lembra que preciso falar com o provedor.",
            "Quero a receita de mousse.", "Oi!",
        ):
            with self.subTest(texto=texto):
                self.assertFalse(pergunta_de_lembranca(texto))


class TestaFluxoMemoria(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from modulos import pensar
        cls.pensar = pensar

    def executar(self, pergunta, ferramenta="ler_obsidian"):
        p = self.pensar
        chamada = SimpleNamespace(function=SimpleNamespace(
            name=ferramenta, arguments='{"assunto":"memória"}'))
        mensagem = SimpleNamespace(
            content="", tool_calls=[chamada] if ferramenta else None, reasoning_content="")
        resposta = SimpleNamespace(choices=[SimpleNamespace(message=mensagem)],
                                   usage=SimpleNamespace(completion_tokens=8))
        self.ler = Mock(return_value="# Memória da Luna\n\nConteúdo da nota.")
        self.salvar = Mock(return_value="SISTEMA: Nota salva")
        self.persona = Mock(return_value="Era o CGNAT do provedor.")
        self.confirmar = Mock(return_value="Anotado.")
        self.salvar_fallback = Mock(return_value="SISTEMA: Nota salva")
        servidor_falso = SimpleNamespace(
            atualizar_metricas=Mock(), atualizar_status=Mock(), atualizar_pensamento=Mock())
        with ExitStack() as pilha:
            for contexto in (
                patch.object(p, "_chamar_llm", return_value=resposta),
                patch.object(p, "_capturar_momento", return_value={"canal": "web", "jogos": []}),
                patch.object(p, "_reescrever_como_luna", self.persona),
                patch.object(p, "_confirmar_salvamento", self.confirmar),
                patch.object(p, "ATIVAR_MEMORIA_PERMANENTE", False),
                patch.object(p.obsidian, "indice_notas", return_value="Memoria, Receita"),
                patch.object(p.obsidian, "salvar_nota", self.salvar_fallback),
                patch.dict(p.FUNCOES_DISPONIVEIS,
                           {"ler_obsidian": self.ler, "salvar_obsidian": self.salvar}),
                patch.dict("sys.modules", {"servidor": servidor_falso}),
                patch("modulos.avaliacoes.registrar_contexto"),
                patch("modulos.metricas_ferramentas.registrar_uso"),
            ):
                pilha.enter_context(contexto)
            resultado = p.gerar_resposta(pergunta, [], salvar=False, responder_completo=True)
        return resultado

    def test_leitura_indevida_vai_para_persona(self):
        self.assertEqual(self.executar(PERGUNTA), "Era o CGNAT do provedor.")
        self.ler.assert_not_called()
        self.salvar.assert_not_called()
        self.persona.assert_called_once()
        self.assertEqual(self.persona.call_args.args[:2], ("", PERGUNTA))

    def test_salvamento_indevido_nao_grava_pergunta(self):
        self.assertEqual(self.executar(PERGUNTA, "salvar_obsidian"), "Era o CGNAT do provedor.")
        self.salvar.assert_not_called()
        self.salvar_fallback.assert_not_called()
        self.persona.assert_called_once()

    def test_lembra_no_inicio_nao_vira_salvamento_nem_pedido_de_acao(self):
        pergunta = "Lembra o que faltava para abrir as portas?"
        self.assertEqual(self.executar(pergunta, None), "Era o CGNAT do provedor.")
        self.salvar_fallback.assert_not_called()
        self.persona.assert_called_once()

    def test_nota_explicita_continua_fiel(self):
        self.assertEqual(self.executar("Mostra a nota Memoria.md"),
                         "Aqui está, do seu Obsidian:\n\n# Memória da Luna\n\nConteúdo da nota.")
        self.ler.assert_called_once()
        self.persona.assert_not_called()

    def test_anotacao_explicita_continua_salvando(self):
        self.assertEqual(self.executar("Anota que meu modem está em CGNAT.", "salvar_obsidian"),
                         "Anotado.")
        self.salvar.assert_called_once()
        self.confirmar.assert_called_once()

    def test_acao_sem_ferramenta_continua_honesta(self):
        resultado = self.executar("Você lembra do modem? Pode pesquisar isso agora?", None)
        self.assertIn("não consegui fazer isso agora", resultado)
        self.persona.assert_not_called()
        self.salvar_fallback.assert_not_called()


if __name__ == "__main__":
    unittest.main()
