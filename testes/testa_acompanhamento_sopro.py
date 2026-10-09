"""Regressões do piloto sem rede, áudio, LLM ou inicialização da Luna."""
import ast
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import threading
import types
import unittest
from unittest.mock import Mock, patch

import requests
from modulos import acompanhamento_sopro as sopro


class PilotoSopro(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.patch_path = patch.object(sopro, "CAMINHO", Path(self.temp.name) / "sopro.json")
        self.patch_path.start()
        self.notify = patch.object(sopro, "_notificar").start()
        self.addCleanup(patch.stopall)
        self.addCleanup(self.temp.cleanup)
        self.agora = 100_000
        self.texto = "English and European Portuguese. Version 2.2.0."

    def fonte(self, fonte, cache):
        return [{"texto": self.texto, "url": fonte["url"]}], {"etag": "abc", "semeada": True}

    def verificar(self, texto=None, **kwargs):
        if texto is not None:
            self.texto = texto
        return sopro.verificar(agora=self.agora, forcar=True, consultar=self.fonte, **kwargs)

    def novidade(self):
        self.verificar()
        self.verificar("Roadmap: Brazilian Portuguese voice support is planned.")
        return sopro.proxima_novidade(agora=self.agora)

    def test_primeira_leitura_semeia_sem_notificar_historico(self):
        self.verificar("Brazilian Portuguese supported.")
        self.assertIsNone(sopro.proxima_novidade(agora=self.agora))
        self.assertEqual([], sopro.estado_interface()["novidades"])

    def test_versao_e_ptpt_nao_sao_ptbr(self):
        self.verificar()
        self.verificar("Version 2.3.0. English and European Portuguese. lang=pt.")
        self.assertIsNone(sopro.proxima_novidade(agora=self.agora))
        self.assertEqual([], sopro.estado_interface()["novidades"])

    def test_mencao_nova_cria_um_aviso_e_deduplica_as_fontes(self):
        item = self.novidade()
        self.assertIn("planned", item["trecho"])
        self.assertEqual(1, len(sopro.estado_interface()["novidades"]))
        self.verificar()
        self.assertEqual(1, len(sopro.estado_interface()["novidades"]))
        self.assertIn("falta validar", sopro.estado_interface()["resultado"])

    def test_reconhece_variantes_e_ignora_ausencia_explicita(self):
        for texto in ["PT-BR", "pt_BR", "Português brasileiro", "Portuguese (Brazil)", "Brazilian accent"]:
            with self.subTest(texto=texto):
                self.assertTrue(sopro.mencoes_ptbr(texto))
        for texto in ["PT-BR is not supported.", "Brazilian Portuguese is not yet supported.",
                      "Sem suporte a português brasileiro", "Português brasileiro não é suportado"]:
            with self.subTest(texto=texto):
                self.assertEqual([], sopro.mencoes_ptbr(texto))

    def test_apresentacao_persiste_mesmo_se_o_audio_for_cancelado(self):
        item = self.novidade()
        with patch.object(sopro.time, "time", return_value=self.agora):
            sopro.registrar_apresentacao(item["id"])
        self.assertIsNone(sopro.proxima_novidade(agora=self.agora))
        self.assertTrue(sopro._carregar()["novidades"][0]["avisado_em"])
        self.verificar()
        self.assertIsNone(sopro.proxima_novidade(agora=self.agora))

    def test_adiar_e_ja_vi_nao_operam_em_item_errado(self):
        item = self.novidade()
        with patch.object(sopro.time, "time", return_value=self.agora):
            sopro.agir("adiar", identificador=item["id"])
        self.assertIsNone(sopro.proxima_novidade(agora=self.agora + 1))
        self.assertIsNotNone(sopro.proxima_novidade(agora=self.agora + sopro.ADIAMENTO))
        self.assertIn("não está", sopro.agir("visto", identificador="id-antigo"))
        sopro.agir("visto", identificador=item["id"])
        self.assertIsNone(sopro.proxima_novidade(agora=self.agora + sopro.ADIAMENTO))

    def test_pausa_encerramento_e_retomada_preservam_estado(self):
        item = self.novidade()
        for acao in ["pausar", "encerrar"]:
            sopro.agir(acao)
            self.assertFalse(self.verificar())
            self.assertIsNone(sopro.proxima_novidade(agora=self.agora))
        sopro.agir("retomar")
        self.assertEqual(item["id"], sopro.proxima_novidade(agora=self.agora)["id"])

    def test_acao_durante_rede_invalida_resultado_sem_apagar_correcao(self):
        self.verificar()
        def consultar(fonte, cache):
            if fonte["id"] == sopro.FONTES[0]["id"]:
                sopro.agir("corrigir", situacao="Agora quero comparar a pronúncia de números.")
            return [{"texto": "Added Brazilian Portuguese.", "url": fonte["url"]}], {"semeada": True}
        self.assertFalse(sopro.verificar(agora=self.agora, forcar=True, consultar=consultar))
        self.assertEqual("Agora quero comparar a pronúncia de números.", sopro.estado_interface()["situacao"])
        self.assertEqual([], sopro.estado_interface()["novidades"])

    def test_falha_nao_vira_nenhuma_novidade_e_fonte_recuperada_semeia(self):
        def falhar(fonte, cache):
            if fonte["id"] == "hf_card":
                raise requests.Timeout("tempo esgotado")
            return self.fonte(fonte, cache)
        sopro.verificar(agora=self.agora, consultar=falhar)
        estado = sopro.estado_interface()
        self.assertIn("incompleta", estado["resultado"])
        self.assertEqual(self.agora + sopro.REPETIR_ERRO, estado["proxima_verificacao"])
        def recuperar(fonte, cache):
            return [{"texto": "PT-BR" if fonte["id"] == "hf_card" else self.texto,
                     "url": fonte["url"]}], {"semeada": True}
        sopro.verificar(agora=self.agora, forcar=True, consultar=recuperar)
        self.assertEqual([], sopro.estado_interface()["novidades"])

    def test_intervalo_e_304_preservam_a_referencia(self):
        self.verificar()
        consultar = Mock()
        self.assertFalse(sopro.verificar(agora=self.agora + 1, consultar=consultar))
        consultar.assert_not_called()
        sopro.verificar(agora=self.agora, forcar=True, consultar=lambda f,c: (None,c))
        self.assertEqual("abc", sopro._carregar()["fontes"]["github_readme"]["etag"])

    def test_pedidos_explicitos_sem_capturar_conversa_generica(self):
        for texto in ["mais tarde", "não gostei do Sopro", "acho que o Sopro não tem PT-BR",
                      "Estou acompanhando o Sopro", "Você acha que vale acompanhar o Sopro?"]:
            self.assertIsNone(sopro.interceptar_pedido(texto))
        self.assertIn("acompanhar", sopro.interceptar_pedido("Luna, acompanha o Sopro e me avisa sobre PT-BR"))
        self.assertIn("acompanhar", sopro.interceptar_pedido("Pode acompanhar o Sopro para mim?"))
        self.assertIn("pausado", sopro.interceptar_pedido("pausa o Sopro"))
        self.assertIn("encerrado", sopro.interceptar_pedido("não quero acompanhar o Sopro"))

    def test_rede_nao_bloqueia_pausa_e_nao_aceita_duas_consultas(self):
        entrou, sair = threading.Event(), threading.Event()
        def demorar(fonte, cache):
            entrou.set()
            self.assertTrue(sair.wait(3))
            return self.fonte(fonte, cache)
        with patch.object(sopro, "consultar_fonte", side_effect=demorar):
            self.assertTrue(sopro.agendar_verificacao(forcar=True))
            self.assertTrue(entrou.wait(3))
            self.assertTrue(sopro.estado_interface()["verificando"])
            self.assertFalse(sopro.agendar_verificacao(forcar=True))
            self.assertIn("pausado", sopro.agir("pausar"))
            sair.set()
            sopro._thread.join(3)
        self.assertFalse(sopro._thread.is_alive())
        self.assertFalse(sopro.estado_interface()["verificando"])
        self.assertEqual("pausado", sopro.estado_interface()["status"])

    def test_http_condicional_e_limite_de_tamanho(self):
        resposta = Mock()
        resposta.status_code = 304
        resposta.__enter__ = Mock(return_value=resposta)
        resposta.__exit__ = Mock(return_value=False)
        with patch.object(sopro.requests, "get", return_value=resposta) as get:
            documentos, cache = sopro.consultar_fonte(sopro.FONTES[0], {"etag": "abc", "semeada": True})
        self.assertIsNone(documentos)
        self.assertEqual("abc", get.call_args.kwargs["headers"]["If-None-Match"])
        self.assertEqual((3, 8), get.call_args.kwargs["timeout"])
        resposta.status_code = 200
        resposta.iter_content.return_value = [b"x" * (sopro.MAX_BYTES + 1)]
        with patch.object(sopro.requests, "get", return_value=resposta):
            with self.assertRaisesRegex(ValueError, "limite"):
                sopro.consultar_fonte(sopro.FONTES[0], {})

    def test_estagio_e_evidencia_com_mencao_no_fim_de_linha_longa(self):
        self.assertEqual("plano", sopro.mencoes_ptbr("Roadmap: PT-BR planned.")[0]["tipo"])
        self.assertEqual("anuncio", sopro.mencoes_ptbr("Added Brazilian Portuguese.")[0]["tipo"])
        item = sopro.mencoes_ptbr("x " * 400 + "PT-BR pronunciation notes.")[0]
        self.assertIn("PT-BR", item["trecho"])
        self.assertLessEqual(len(item["trecho"]), 600)

    def test_estado_corrompido_fica_pausado(self):
        sopro.CAMINHO.write_text("{", encoding="utf-8")
        self.assertEqual("pausado", sopro.estado_interface()["status"])

    def test_entrega_confirma_publicacao_e_preserva_link(self):
        item = self.novidade()
        arvore = ast.parse(Path("modulos/proativa.py").read_text(encoding="utf-8"))
        funcoes = [n for n in arvore.body if isinstance(n, (ast.FunctionDef, ast.ClassDef))
                   and n.name in {"_tarefa_acompanhamento_sopro", "_FalaProativa"}]
        from modulos import prompts
        contexto = {"luna_esta_livre": lambda: True, "_proativo_ativo": True,
                    "ESTADO_JOGOS": {}, "_STEAM_JOGANDO_AGORA": False,
                    "TAREFAS_ATIVAS": {"acompanhamentos": True}, "_prompts": prompts,
                    "registrar_tentativa": Mock()}
        exec(compile(ast.Module(body=funcoes, type_ignores=[]), "proativa-isolada", "exec"), contexto)
        gerar = Mock(side_effect=lambda *a,**k: contexto["_FalaProativa"]("Convite gerado pelo modelo."))
        contexto["_gerar_fala_proativa"] = gerar
        falas = []
        def falar(fala, *, ainda_valido, ao_apresentar):
            if ainda_valido():
                falas.append(fala)
                ao_apresentar()
            return False  # O áudio foi cancelado, depois da legenda.
        contexto["_falar_proativamente"] = falar
        with patch.object(sopro.time, "time", return_value=self.agora), \
                patch("modulos.dark_souls.contexto", return_value=None):
            contexto["_tarefa_acompanhamento_sopro"]()
        self.assertEqual({"noticia": item["url"]}, falas[0].links_novidades)
        self.assertEqual("sopro", falas[0].cartoes_web[0]["origem"])
        self.assertEqual("sopro_ptbr", falas[0].cartoes_web[0]["id"])
        self.assertEqual(item["trecho"], falas[0].cartoes_web[0]["trecho"])
        self.assertIsNone(sopro.proxima_novidade(agora=self.agora))
        contexto["_tarefa_acompanhamento_sopro"]()
        self.assertEqual(1, gerar.call_count)

    def test_loop_nao_entrega_enquanto_jogando_ou_no_aquecimento(self):
        arvore = ast.parse(Path("modulos/proativa.py").read_text(encoding="utf-8"))
        loop = next(n for n in arvore.body if isinstance(n, ast.FunctionDef) and n.name == "_loop_proativo")
        gate = next(n for n in ast.walk(loop) if isinstance(n, ast.If) and
                    isinstance(n.test, ast.UnaryOp) and isinstance(n.test.operand, ast.Name) and
                    n.test.operand.id == "jogando_agora")
        codigo = compile(ast.Module(body=[gate], type_ignores=[]), "gate-jogo", "exec")
        for jogando, boot, esperado in [(True,False,False),(False,True,False),(False,False,True)]:
            sopro_tarefa = Mock()
            contexto = {"jogando_agora": jogando, "_ja_imprimiu_jogando": False,
                        "_sessao_inicio": 99 if boot else 0, "time": types.SimpleNamespace(time=lambda:100),
                        "_GRACA_BOOT_S": 120, "TAREFAS_ATIVAS": {"acompanhamentos": True},
                        "cor": types.SimpleNamespace(amarelo=Mock()), "_tarefa_acompanhamentos": Mock(),
                        "_tarefa_acompanhamento_sopro": sopro_tarefa}
            for n in ast.walk(gate):
                if isinstance(n, ast.Call) and isinstance(n.func, ast.Name):
                    contexto.setdefault(n.func.id, Mock())
            exec(codigo, contexto)
            self.assertEqual(esperado, sopro_tarefa.called)


    def test_websocket_entrega_estado_inicial_e_processa_acoes_do_painel(self):
        arvore = ast.parse(Path("servidor.py").read_text(encoding="utf-8"))
        fn = next(n for n in arvore.body if isinstance(n, ast.FunctionDef) and n.name == "websocket")
        fn.decorator_list = []
        recebidos = iter([json.dumps({"comando": "sopro_acao", "acao": "pausar"}),
                          json.dumps({"comando": "sopro_acao", "acao": "corrigir", "situacao": "Esperando outro teste."})])
        enviados = []
        ws = Mock()
        ws.send = lambda msg: enviados.append(json.loads(msg))
        from simple_websocket import ConnectionClosed
        def receber(**kwargs):
            mensagem = next(recebidos, None)
            if mensagem is None:
                raise ConnectionClosed()
            return mensagem
        ws.receive = receber
        contexto = {"json": json, "request": types.SimpleNamespace(remote_addr="127.0.0.1"),
                    "_clientes": set(), "_clientes_lock": threading.Lock(),
                    "_ultima_fala_usuario": "", "_ultima_fala_luna": "",
                    "_ultimo_pensamento": "", "_ultimo_estado_rosto": None, "_ultimo_kaomoji": None,
                    "_ultimo_status": "", "_historico_web": [], "_config_para_web": lambda: {},
                    "_memoria_estado": lambda: {"pendentes": []},
                    "_acompanhamentos_estado": lambda: {"sopro": sopro.estado_interface()},
                    "notificar_acompanhamentos": Mock(), "ConnectionClosed": ConnectionClosed}
        exec(compile(ast.Module(body=[fn], type_ignores=[]), "websocket-isolado", "exec"), contexto)
        contexto["websocket"](ws)
        self.assertEqual("ativo", next(p for p in enviados if p.get("tipo") == "acompanhamentos")["estado"]["sopro"]["status"])
        self.assertEqual(2, len([p for p in enviados if p.get("tipo") == "acompanhamento_feedback"]))
        self.assertEqual("pausado", sopro.estado_interface()["status"])
        self.assertEqual("Esperando outro teste.", sopro.estado_interface()["situacao"])
        self.assertEqual(set(), contexto["_clientes"])

    def test_jogo_aberto_durante_geracao_nao_publica_e_preserva_novidade(self):
        item = self.novidade()
        arvore = ast.parse(Path("modulos/proativa.py").read_text(encoding="utf-8"))
        funcoes = [n for n in arvore.body if isinstance(n, (ast.FunctionDef, ast.ClassDef))
                   and n.name in {"_tarefa_acompanhamento_sopro", "_FalaProativa"}]
        from modulos import prompts
        publicar = Mock()
        contexto = {"luna_esta_livre": lambda: True, "_proativo_ativo": True,
                    "ESTADO_JOGOS": {}, "_STEAM_JOGANDO_AGORA": False,
                    "TAREFAS_ATIVAS": {"acompanhamentos": True}, "_prompts": prompts,
                    "registrar_tentativa": Mock()}
        exec(compile(ast.Module(body=funcoes, type_ignores=[]), "proativa-isolada", "exec"), contexto)
        def gerar(*args, **kwargs):
            contexto["_STEAM_JOGANDO_AGORA"] = True
            return contexto["_FalaProativa"]("Um convite que perdeu a janela de entrega.")
        def falar(fala, *, ainda_valido, ao_apresentar):
            if fala and ainda_valido():
                publicar()
                ao_apresentar()
        contexto["_gerar_fala_proativa"] = gerar
        contexto["_falar_proativamente"] = falar
        with patch.object(sopro.time, "time", return_value=self.agora), \
                patch("modulos.dark_souls.contexto", return_value=None):
            contexto["_tarefa_acompanhamento_sopro"]()
        publicar.assert_not_called()
        self.assertEqual(item["id"], sopro.proxima_novidade(agora=self.agora)["id"])


if __name__ == "__main__":
    unittest.main()
