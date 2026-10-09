import unittest
import ast
from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import re
from types import ModuleType, SimpleNamespace
import unicodedata
from unittest.mock import Mock, patch

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

    def test_comentario_aion_com_como_nao_e_pedido(self):
        texto = ("esse jogo parece bem menos cuidado do que o primeiro aion, os cratfts estao "
                 "simplorios, a extracao conta como skill...")
        for trecho in (texto, "a extracao conta como skill", "como skill", "como"):
            with self.subTest(trecho=trecho):
                self.assertFalse(validar_pedido_gameplay(texto, trecho))

    def test_comparacao_e_negacao_nao_viram_pedido(self):
        for texto in ("Esse sistema funciona como o do primeiro jogo.",
                      "O craft parece uma loja onde só tem uma escolha.",
                      "Não preciso de ajuda, só estou comentando."):
            with self.subTest(texto=texto):
                self.assertFalse(validar_pedido_gameplay(texto, texto))

    def test_pedido_sem_interrogacao_e_indireto_continuam_ativos(self):
        for texto in ("Como funciona a extração", "Luna, como funciona a extração",
                      "Tem alguma dica para esse chefe", "Me explica essa extração",
                      "Você pode me explicar a extração", "Queria saber como funciona a extração",
                      "Estou no AION 2. Como funciona a extração"):
            with self.subTest(texto=texto):
                trecho = "Como funciona a extração" if ". " in texto else texto
                self.assertTrue(validar_pedido_gameplay(texto, trecho))

    def test_evidencia_inteira_pode_conter_pedido_na_segunda_oracao(self):
        texto = "Estou no AION 2. Como funciona a extração"
        self.assertTrue(validar_pedido_gameplay(texto, texto))

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

    def test_recorte_nao_fabrica_followup(self):
        historico = [{"role": "assistant", "content": "Use eletricidade.",
                      "_ferramenta": "duvida_do_jogo", "_jogo": "Jogo de teste"}]
        self.assertFalse(validar_pedido_gameplay(
            "Gostei dessa luta na segunda fase", "na segunda fase", historico))

    def test_opiniao_preserva_jogo_identificado_pelo_roteador(self):
        declaracao = rotina_jogos.detectar_declaracao(
            "Parei um pouco, mas estou gostando.",
            nome_contexto="Final Fantasy VII Remake",
        )
        self.assertEqual(declaracao["nome_jogo"], "Final Fantasy VII Remake")
        self.assertEqual(declaracao["opiniao"], "Parei um pouco, mas estou gostando.")


class ResultadoGameplayTeste(unittest.TestCase):
    def setUp(self):
        # Executa as funções reais sem inicializar os clientes de outras integrações.
        arquivo = Path(__file__).parents[1] / "modulos/habilidades.py"
        arvore = ast.parse(arquivo.read_text(encoding="utf8"))
        nomes = {"_norm_txt", "_nucleo_jogo", "duvida_do_jogo"}
        arvore.body = [n for n in arvore.body if (
            isinstance(n, ast.FunctionDef) and n.name in nomes) or (
            isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and
                t.id == "_JOGO_SUFIXOS_FIM" for t in n.targets))]
        self.buscar = Mock()
        escopo = {"re": re, "unicodedata": unicodedata, "pesquisar_na_web": self.buscar}
        exec(compile(arvore, str(arquivo), "exec"), escopo)
        self.consultar = escopo["duvida_do_jogo"]
        memoria = ModuleType("modulos.memoria")
        memoria.ler_estado_luna = lambda: {}
        self.stub = patch.dict("sys.modules", {"modulos.memoria": memoria})
        self.stub.start()
        self.addCleanup(self.stub.stop)

    def test_consulta_concluida_preserva_dados(self):
        self.buscar.return_value = "AION 2: material sintético de teste sobre extração."
        resposta = self.consultar("Como funciona a extração?", "AION 2")
        self.assertTrue(resposta.startswith("SISTEMA: Resultado da pesquisa sobre "))
        self.assertIn(self.buscar.return_value, resposta)

    def test_falta_de_material_nao_e_erro_de_acesso(self):
        for resultado in ("Aviso: A pesquisa não retornou nenhum resultado.",
                          "Guia de extração de AION 1", ""):
            with self.subTest(resultado=resultado):
                self.buscar.return_value = resultado
                resposta = self.consultar("Como funciona a extração?", "AION 2")
                self.assertTrue(resposta.startswith("SISTEMA: PESQUISA_JOGO_SEM_DADOS:"))

    def test_erro_de_acesso_preserva_o_motivo(self):
        self.buscar.return_value = "Erro ao tentar acessar a internet: conexão indisponível."
        resposta = self.consultar("Como funciona a extração?", "AION 2")
        self.assertTrue(resposta.startswith("SISTEMA: PESQUISA_JOGO_ERRO:"))
        self.assertIn("conexão indisponível", resposta)

    def test_sem_jogo_nao_alega_pesquisa(self):
        resposta = self.consultar("Como funciona a extração?")
        self.buscar.assert_not_called()
        self.assertTrue(resposta.startswith("SISTEMA: PESQUISA_JOGO_SEM_CONTEXTO:"))


class FluxoGameplayTeste(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from testes.bancada_dark_souls_thinking import preparar_runtime
        cls.pensar = preparar_runtime()

    def capturar_despacho(self, texto, trecho):
        from modulos import momento
        pensar = self.pensar
        consulta = Mock(return_value="SISTEMA: Resultado da pesquisa sobre 'AION 2':\nDados de teste.")
        funcao = SimpleNamespace(name="duvida_do_jogo", arguments=json.dumps({
            "pergunta": texto, "nome_jogo": "AION 2", "trecho_pedido": trecho}))
        resposta = SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(
            content="", tool_calls=[SimpleNamespace(function=funcao)]))],
            usage=SimpleNamespace(completion_tokens=12))
        capturado = {}

        class MontagemCapturada(BaseException):
            pass

        def persona(tecnica, usuario, historico, *args, **kwargs):
            capturado.update(tecnica=tecnica, usuario=usuario)
            raise MontagemCapturada()

        # Interrompe antes de salvar histórico/métricas; testa o despacho real sem chamar a LLM.
        with (
            patch.object(pensar, "_chamar_llm", return_value=resposta),
            patch.object(pensar, "_reescrever_como_luna", side_effect=persona),
            patch.dict(pensar.FUNCOES_DISPONIVEIS, {"duvida_do_jogo": consulta}),
            patch.object(pensar.obsidian, "indice_notas", return_value=""),
            patch.object(pensar, "ler_estado_luna", return_value={}),
            patch.object(pensar, "obter_janela_em_foco", return_value="bancada"),
            patch.object(momento, "_jogos", {}),
            pensar.controle.executar(),
            redirect_stdout(io.StringIO()),
        ):
            with self.assertRaises(MontagemCapturada):
                pensar.gerar_resposta(texto, [], salvar=False, responder_completo=True)
        return consulta, capturado

    def test_roteador_errado_nao_pesquisa_comentario(self):
        texto = "o craft parece simplório, a extração conta como skill"
        consulta, capturado = self.capturar_despacho(texto, "como skill")
        consulta.assert_not_called()
        self.assertEqual(capturado, {"tecnica": "", "usuario": texto})

    def test_pedido_explicito_executa_consulta(self):
        texto = "Como funciona a extração no AION 2"
        consulta, capturado = self.capturar_despacho(texto, texto)
        consulta.assert_called_once_with(pergunta=texto, nome_jogo="AION 2")
        self.assertEqual(capturado["tecnica"], consulta.return_value)


if __name__ == "__main__":
    unittest.main()
