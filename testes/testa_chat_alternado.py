"""Compatibilidade com templates estritos sem apagar proativos nem falsificar tool calls."""
import ast
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from modulos.turbollm_api import adaptar_mensagens_alternadas, erro_alternancia_papeis

CONTEXTO = "Falas anteriores da assistente: {falas}\nMensagem do usuário: {mensagem}"


def msg(role, content):
    return {"role": role, "content": content}


class ErroRoles(Exception):
    status_code = 400

    def __str__(self):
        return "Jinja Exception: After the optional system message, conversation roles must alternate user/assistant/..."


class TestaMensagensAlternadas(unittest.TestCase):
    def test_conversa_normal_permanece_igual(self):
        mensagens = [msg("system", "regras"), msg("user", "oi"), msg("assistant", "olá"), msg("user", "voltei")]
        self.assertEqual(adaptar_mensagens_alternadas(mensagens, CONTEXTO), mensagens)

    def test_proativos_iniciais_viram_contexto_sem_apagar_ou_inventar_pedido(self):
        mensagens = [msg("system", "regras"), msg("assistant", "Uma novidade."),
                     msg("assistant", "Outra novidade."), msg("user", "Qual delas?")]
        antes = deepcopy(mensagens)
        novas = adaptar_mensagens_alternadas(mensagens, CONTEXTO)
        self.assertEqual(mensagens, antes)
        self.assertEqual([m["role"] for m in novas], ["system", "user"])
        self.assertEqual(novas[0], antes[0])
        self.assertEqual(novas[1]["content"], CONTEXTO.format(
            falas='["Uma novidade.", "Outra novidade."]', mensagem="Qual delas?"))

    def test_agrupar_turnos_consecutivos_preserva_ordem(self):
        mensagens = [msg("user", "primeiro"), msg("user", "segundo"),
                     msg("assistant", "resposta"), msg("assistant", "proativo"), msg("user", "agora")]
        novas = adaptar_mensagens_alternadas(mensagens, CONTEXTO)
        self.assertEqual(novas, [msg("user", "primeiro\n\nsegundo"),
                                msg("assistant", "resposta\n\nproativo"), msg("user", "agora")])

    def test_sem_usuario_ou_com_contrato_especial_nao_inventa_conversa(self):
        for mensagens in ([], [msg("assistant", "proativo")],
                          [msg("user", "oi"), msg("system", "outras regras")],
                          [msg("user", [{"type": "text", "text": "oi"}])],
                          [{"role": "assistant", "content": "", "tool_calls": [{}]},
                           {"role": "tool", "content": "feito", "tool_call_id": "abc"}],
                          [msg("developer", "regra"), msg("user", "oi")]):
            with self.subTest(mensagens=mensagens):
                self.assertEqual(adaptar_mensagens_alternadas(mensagens, CONTEXTO), mensagens)

    def test_detector_exige_status_e_motivo_exatos(self):
        self.assertTrue(erro_alternancia_papeis(ErroRoles()))
        for erro in (RuntimeError(str(ErroRoles())), ValueError("context too long")):
            self.assertFalse(erro_alternancia_papeis(erro))
        erro = ErroRoles()
        erro.status_code = 500
        self.assertFalse(erro_alternancia_papeis(erro))


class TestaChamadaCompativel(unittest.TestCase):
    def setUp(self):
        self.criar = Mock()
        self.controle = SimpleNamespace(verificar=Mock(), contexto=SimpleNamespace(get=lambda: None))
        self.recuperar = Mock(return_value=False)
        self.registros = []
        from modulos import avaliacoes
        p = patch.object(avaliacoes, "registrar_chamada", side_effect=lambda modelo, parametros:
                         self.registros.append(deepcopy(parametros)))
        p.start()
        self.addCleanup(p.stop)
        escopo = {
            "controle": self.controle, "_ciclo_modelo": 1,
            "cliente": SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=self.criar))),
            "modelo": lambda: "modelo_teste", "erro_modelo_descarregado": self.recuperar,
            "erro_alternancia_papeis": erro_alternancia_papeis,
            "adaptar_mensagens_alternadas": adaptar_mensagens_alternadas,
            "_prompts": SimpleNamespace(CONTEXTO_HISTORICO_SEM_USUARIO=CONTEXTO),
            "cor": SimpleNamespace(amarelo=lambda texto: None),
        }
        fonte = ast.parse(Path("modulos/pensar.py").read_text(encoding="utf-8"))
        fonte.body = [n for n in fonte.body if isinstance(n, ast.FunctionDef) and n.name == "_chamar_llm"]
        exec(compile(fonte, "modulos/pensar.py", "exec"), escopo)
        self.chamar = escopo["_chamar_llm"]
        self.historico = [msg("assistant", "proativo"), msg("user", "olá")]

    def test_reenvia_uma_vez_preservando_ferramentas_e_parametros(self):
        self.criar.side_effect = [ErroRoles(), "resposta"]
        antes = deepcopy(self.historico)
        self.assertEqual(self.chamar(messages=self.historico, tools=[{"function": "teste"}],
                                     temperature=0, max_tokens=256), "resposta")
        self.assertEqual(self.historico, antes)
        self.assertEqual(self.criar.call_count, 2)
        a, b = self.registros
        self.assertEqual(a["messages"], antes)
        self.assertEqual([m["role"] for m in b["messages"]], ["user"])
        for campo in ("tools", "temperature", "max_tokens"):
            self.assertEqual(a[campo], b[campo])
        self.recuperar.assert_not_called()

    def test_modelo_permissivo_nao_recebe_adaptacao(self):
        self.criar.return_value = "normal"
        self.assertEqual(self.chamar(messages=self.historico), "normal")
        self.assertEqual(self.registros[0]["messages"], self.historico)
        self.assertEqual(self.criar.call_count, 1)

    def test_erro_persistente_nao_entra_em_loop(self):
        self.criar.side_effect = ErroRoles()
        with self.assertRaises(ErroRoles):
            self.chamar(messages=self.historico)
        self.assertEqual(self.criar.call_count, 2)

    def test_outro_erro_ou_historico_ja_alternado_nao_reenvia(self):
        for erro, mensagens in ((ValueError("context too long"), self.historico),
                                (ErroRoles(), [msg("user", "oi")])):
            with self.subTest(erro=erro):
                self.criar.reset_mock()
                self.criar.side_effect = erro
                with self.assertRaises(type(erro)):
                    self.chamar(messages=mensagens)
                self.assertEqual(self.criar.call_count, 1)

    def test_prioridade_do_usuario_interrompe_antes_da_retentativa(self):
        self.criar.side_effect = ErroRoles()
        self.controle.verificar.side_effect = [None, RuntimeError("cancelada")]
        with self.assertRaisesRegex(RuntimeError, "cancelada"):
            self.chamar(messages=self.historico)
        self.assertEqual(self.criar.call_count, 1)


if __name__ == "__main__":
    unittest.main()
