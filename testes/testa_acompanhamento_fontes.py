"""Regressões do cadastro e consulta de fontes, sem iniciar Luna ou usar estado real."""
import ast
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import threading
import types
import unittest
from unittest.mock import Mock, patch

from modulos import acompanhamento_fontes as fontes, prompts
from modulos.execucoes import Coordenador, ExecucaoCancelada

URL = "https://example.com/releases.atom"
BASE = "Release 1\nPortuguese from Portugal only."
NOVO = "Added experimental Brazilian Portuguese voices."
PLANO = "Brazilian Portuguese support is planned for a future release."


class FontesTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.patches = [patch.object(fontes, "CAMINHO", Path(self.tmp.name)/"fontes.json"),
                        patch.object(fontes, "agendar_verificacao", return_value=True),
                        patch.object(fontes, "_notificar")]
        self.mocks = [p.start() for p in self.patches]
        self.agora = 1000
        r = fontes.agir("criar", cadastro={"assunto": "TTS de teste", "interesse": "Suporte a português brasileiro",
                                         "situacao": "A voz agradou, mas o sotaque não.", "fontes": [URL]})
        self.assertTrue(r["ok"])
        self.id = r["id"]

    def tearDown(self):
        for p in reversed(self.patches):
            p.stop()
        self.tmp.cleanup()

    def ler(self):
        return fontes._carregar()["itens"][0]

    def consultar(self, texto, agora=None, efeito=None):
        def http(url, anterior):
            if efeito:
                efeito()
            return [{"url": url, "texto": texto}], {"semeada": True, "etag": "abc"}
        return fontes.verificar(identificador=self.id, forcar=True,
                                agora=self.agora if agora is None else agora, consultar=http)

    def candidato(self, texto=NOVO):
        self.consultar(BASE)
        self.consultar(BASE+"\n"+texto, 1100)
        return fontes.proxima_analise(agora=1100)

    def classificar(self, p=None, relevante=True, evidencia=NOVO, etapa="anuncio"):
        return fontes.registrar_analise(p or self.candidato(), json.dumps({
            "relevante": relevante, "resumo": "Vozes brasileiras experimentais adicionadas.",
            "evidencia": evidencia, "etapa": etapa}))

    def test_primeira_leitura_e_repeticao_silenciosas(self):
        self.consultar(BASE+"\n"+NOVO)
        self.assertFalse(self.ler()["pendentes"])
        self.consultar(BASE+"\n"+NOVO, 1100)
        self.assertFalse(self.ler()["pendentes"])
        self.assertIsNone(fontes.proxima_novidade(agora=1100))

    def test_interesse_ingles_e_dedup_de_consultas(self):
        p = self.candidato()
        self.assertEqual(NOVO, p["novo"])
        self.assertIn("Portuguese from Portugal", p["trecho"])
        self.consultar(BASE+"\n"+NOVO, 1200)
        self.assertEqual(1, len(self.ler()["pendentes"]))
        self.classificar(p)
        n = fontes.proxima_novidade(agora=1200)
        self.assertEqual(URL, n["url"])
        self.assertTrue(fontes.registrar_apresentacao(n))
        self.assertIsNone(fontes.proxima_novidade(agora=1200))
        self.assertFalse(fontes.ainda_valido(n))
        self.assertTrue(fontes.agir("visto", identificador=self.id, novidade_id=n["id"])["ok"])

    def test_mudanca_irrelevante_nao_gera_aviso(self):
        p = self.candidato("Changed the README logo.")
        fontes.registrar_analise(p, '{"relevante":false}')
        self.assertFalse(self.ler()["pendentes"])
        self.assertFalse(self.ler()["novidades"])

    def test_plano_nao_vira_disponibilidade(self):
        p = self.candidato(PLANO)
        self.classificar(p, evidencia=PLANO, etapa="plano")
        n = fontes.proxima_novidade(agora=1200)
        self.assertEqual("plano", n["etapa"])
        self.assertIn("ainda não dá para testar", prompts.prompt_acompanhamento_fonte(n))
        self.assertLess(len(prompts.prompt_acompanhamento_fonte(n)), 1500)

    def test_briefing_preserva_orientacao_com_campos_maximos_e_aspas(self):
        d = {k: '"\\\n'*500 for k in ("assunto", "interesse", "situacao", "resumo", "evidencia")}
        for etapa in prompts.FONTE_ORIENTACOES:
            d["etapa"] = etapa
            briefing = prompts.prompt_acompanhamento_fonte(d)
            self.assertLess(len(briefing), 1500)
            self.assertIn(prompts.FONTE_ORIENTACOES[etapa], briefing)

    def test_json_invalido_e_evidencia_antiga_aguardam_nova_tentativa(self):
        p = self.candidato()
        for bruto in ['{"relevante":"true"}',
                      json.dumps({"relevante": True, "resumo": "Já funciona", "etapa": "anuncio",
                                  "evidencia": "Portuguese from Portugal only."}),
                      '{"relevante":true,"resumo":"bom","evidencia":"inventei","etapa":"anuncio"}']:
            fontes.registrar_analise(p, bruto)
        self.assertFalse(self.ler()["novidades"])
        self.assertEqual(3, self.ler()["pendentes"][0]["tentativas"])
        self.assertIsNone(fontes.proxima_analise(agora=10**12))
        self.consultar(BASE+"\n"+NOVO)
        self.assertIsNotNone(fontes.proxima_analise())

    def test_pausa_edicao_encerramento_invalidam_resultado_em_voo(self):
        p = self.candidato()
        for acao in ["pausar", "encerrar", "excluir"]:
            with self.subTest(acao=acao):
                original = deepcopy(fontes._carregar())
                fontes.agir(acao, identificador=self.id)
                self.assertFalse(fontes.ainda_valido(p))
                self.assertFalse(self.classificar(p))
                fontes._salvar(original)
        self.consultar(BASE+"\n"+PLANO, efeito=lambda: fontes.agir("editar", identificador=self.id,
                       cadastro={"assunto":"Outro TTS", "interesse":"Melhoria na velocidade de voz", "fontes":[URL]}))
        self.assertEqual("Outro TTS", self.ler()["assunto"])
        self.assertFalse(self.ler()["cache"])
        self.assertFalse(self.ler()["pendentes"])

    def test_http_nao_segura_a_trava_do_painel(self):
        concluido = threading.Event()
        def durante():
            t = threading.Thread(target=lambda: (fontes.agir("pausar", identificador=self.id), concluido.set()))
            t.start()
            self.assertTrue(concluido.wait(1), "HTTP segurou a trava da interface")
            t.join()
        self.consultar(BASE, efeito=durante)
        self.assertEqual("pausado", self.ler()["status"])
        self.assertFalse(self.ler()["cache"])

    def test_agendador_usa_thread_e_permite_pausar_durante_http(self):
        iniciou, liberar = threading.Event(), threading.Event()
        def consultar(url, anterior):
            iniciou.set()
            liberar.wait(3)
            return [{"url":url,"texto":BASE}], {"semeada":True}
        self.patches[1].stop()
        try:
            with patch.object(fontes,"consultar_fonte",side_effect=consultar):
                self.assertTrue(fontes.agendar_verificacao(identificador=self.id))
                self.assertTrue(iniciou.wait(1))
                self.assertTrue(fontes.agir("pausar",identificador=self.id)["ok"])
                self.assertEqual("pausado",fontes.estado_interface()["itens"][0]["status"])
                liberar.set()
                fontes._thread.join(3)
                self.assertFalse(fontes._thread.is_alive())
                self.assertFalse(self.ler()["cache"])
        finally:
            liberar.set()
            if fontes._thread:
                fontes._thread.join(3)
            self.patches[1].start()

    def test_duas_fontes_nao_duplicam_mesmo_conteudo_e_feed_antigo_nao_reaparece(self):
        fontes.agir("editar",identificador=self.id,cadastro={
            "assunto":"TTS de teste","interesse":"Suporte a português brasileiro",
            "fontes":[URL,"https://example.org/releases"]})
        def poll(texto):
            return fontes.verificar(forcar=True,agora=self.agora,consultar=lambda url,ref:
                ([{"url":"https://example.com/article","texto":texto}],{"semeada":True}))
        poll(BASE)
        poll(BASE+"\n"+NOVO)
        self.assertEqual(1,len(self.ler()["pendentes"]))
        original = self.ler()["pendentes"][0]["id"]
        poll("")  # A entrada antiga saiu da janela de leitura.
        poll(BASE+"\n"+NOVO)
        self.assertEqual(1,len(self.ler()["pendentes"]))
        self.assertEqual(original,self.ler()["pendentes"][0]["id"])

    def test_adiar_so_uma_vez_e_remover(self):
        self.classificar()
        n = fontes.proxima_novidade(agora=1200)
        with patch.object(fontes.time, "time", return_value=1200):
            fontes.agir("adiar", identificador=self.id, novidade_id=n["id"])
            self.assertIsNone(fontes.proxima_novidade(agora=1200))
        self.assertEqual(n["id"], fontes.proxima_novidade(agora=8500)["id"])
        fontes.agir("excluir", identificador=self.id)
        self.assertFalse(fontes.estado_interface()["itens"])

    def test_url_invalida_e_cadastro_invalido_nao_apagam_estado(self):
        for url in ["javascript:alert(1)", "http://127.0.0.1/x", "http://192.168.1.1/", "http://[::1]/",
                    "https://u:p@example.com/", "https://@example.com/", "https://example.com:8080", "https://a.local/x"]:
            with self.subTest(url=url), self.assertRaises(ValueError):
                fontes.validar_url(url)
        anterior = fontes.CAMINHO.read_bytes()
        r = fontes.agir("editar", identificador=self.id, cadastro={"assunto":"TTS", "interesse":"Português brasileiro",
                                                                "fontes":["https://example.com"]*4})
        self.assertFalse(r["ok"])
        self.assertEqual(anterior, fontes.CAMINHO.read_bytes())
        self.assertFalse(fontes.agir("criar", cadastro="inválido")["ok"])
        with patch.object(fontes.socket, "getaddrinfo", return_value=[(0,0,0,0,("10.0.0.1",80))]):
            with self.assertRaises(ValueError):
                fontes.validar_url(URL, resolver=True)

    def test_feed_html_e_texto(self):
        xml = '<rss version="2.0"><channel><title>Feed</title><item><title>New voice</title><link>https://example.com/new</link><description>Brazilian Portuguese added</description></item></channel></rss>'
        docs = fontes._documentos(xml, URL, "application/rss+xml")
        self.assertEqual("https://example.com/new", docs[0]["url"])
        self.assertIn("Brazilian Portuguese", docs[0]["texto"])
        html = '<nav>ruído</nav><main><h1>Notas</h1><p>Novidade</p><script>alert(1)</script></main>'
        self.assertEqual("Notas\nNovidade", fontes._documentos(html, URL, "text/html")[0]["texto"])
        self.assertEqual("Notas", fontes._documentos("Notas", URL, "text/plain")[0]["texto"])

    def test_erro_de_fonte_nao_apaga_referencia_e_tem_retentativa(self):
        self.consultar(BASE)
        cache = deepcopy(self.ler()["cache"])
        def falha(*a):
            raise ValueError("offline")
        fontes.verificar(forcar=True, agora=1200, consultar=falha)
        self.assertEqual(cache, self.ler()["cache"])
        self.assertEqual(1200+fontes.REPETIR_ERRO, self.ler()["proxima_verificacao"])
        self.assertTrue(self.ler()["erros"])

    def test_304_usa_etag_e_redirect_privado_e_pagina_grande_sao_recusados(self):
        r = Mock(status_code=304, headers={})
        r.__enter__ = Mock(return_value=r); r.__exit__ = Mock(return_value=False)
        sessao = Mock()
        sessao.__enter__ = Mock(return_value=sessao); sessao.__exit__ = Mock(return_value=False)
        sessao.get.return_value = r
        with patch.object(fontes.requests, "Session", return_value=sessao), \
             patch.object(fontes.socket, "getaddrinfo", return_value=[(0,0,0,0,("8.8.8.8",443))]):
            docs, _ = fontes.consultar_fonte(URL, {"etag":"abc", "semeada":True})
            self.assertIsNone(docs)
            self.assertEqual("abc", sessao.get.call_args.kwargs["headers"]["If-None-Match"])
            r.status_code = 302; r.headers = {"Location":"http://127.0.0.1/"}
            with self.assertRaises(ValueError):
                fontes.consultar_fonte(URL, {})
            r.status_code = 200; r.headers = {}
            r.iter_content.return_value = [b"x" * (fontes.MAX_BYTES+1)]
            with self.assertRaisesRegex(ValueError, "limite"):
                fontes.consultar_fonte(URL, {})

    def test_utf8_sem_charset_preserva_acentos(self):
        r = Mock(status_code=200, headers={"Content-Type":"text/html"}, encoding="ISO-8859-1")
        r.iter_content.return_value = ["<main>Português brasileiro</main>".encode()]
        r.__enter__ = Mock(return_value=r); r.__exit__ = Mock(return_value=False)
        s = Mock(); s.__enter__ = Mock(return_value=s); s.__exit__ = Mock(return_value=False); s.get.return_value=r
        with patch.object(fontes.requests, "Session", return_value=s), \
             patch.object(fontes.socket, "getaddrinfo", return_value=[(0,0,0,0,("8.8.8.8",443))]):
            self.assertIn("Português", fontes.consultar_fonte(URL, {})[0][0]["texto"])

    def test_estado_corrompido_e_preservado(self):
        fontes.CAMINHO.write_text("{", encoding="utf-8")
        self.assertTrue(fontes.estado_interface()["erro"])
        self.assertFalse(fontes.agir("criar", cadastro={})["ok"])
        self.assertEqual("{", fontes.CAMINHO.read_text())
        # Executa o agendador real, sem disparar thread, sobre o arquivo corrompido.
        self.patches[1].stop()
        try:
            self.assertFalse(fontes.agendar_verificacao())
        finally:
            self.patches[1].start()

    def contexto_proativo(self):
        arvore = ast.parse(Path("modulos/proativa.py").read_text(encoding="utf-8"))
        nomes = {"_tarefa_acompanhamento_fontes", "_FalaProativa", "_execucao_proativa"}
        funcoes = [n for n in arvore.body if isinstance(n,(ast.FunctionDef,ast.ClassDef)) and n.name in nomes]
        from functools import wraps
        contexto = {"_execucoes": Coordenador(pausa=0), "ExecucaoCancelada": ExecucaoCancelada, "_wraps": wraps,
                    "_ultima_execucao": {}, "_pode_falar_proativo": lambda:True, "luna_esta_livre":lambda:True,
                    "_proativo_ativo":True, "TAREFAS_ATIVAS":{"acompanhamentos":True}, "ESTADO_JOGOS":{},
                    "_STEAM_JOGANDO_AGORA":False, "esta_suspensa":lambda:False, "obter_tempo_afk":lambda:0,
                    "_prompts":prompts, "registrar_tentativa":Mock(), "cor":types.SimpleNamespace(amarelo=Mock())}
        exec(compile(ast.Module(body=funcoes,type_ignores=[]),"proativa-isolada","exec"),contexto)
        contexto["_gerar_fala_proativa"] = Mock(side_effect=lambda *a,**k: contexto["_FalaProativa"]("Convite gerado."))
        contexto["gerar_resposta"] = Mock(return_value=json.dumps({"relevante":True,"resumo":"Novas vozes",
                                                                  "evidencia":NOVO,"etapa":"anuncio"}))
        def falar(fala, *, ainda_valido, ao_apresentar):
            if fala and ainda_valido():
                ao_apresentar()
        contexto["_falar_proativamente"] = Mock(side_effect=falar)
        contexto["executar"] = contexto["_execucao_proativa"](contexto["_tarefa_acompanhamento_fontes"])
        return contexto

    def test_segmento_real_liga_classificacao_fala_link_e_entrega(self):
        self.candidato()
        c = self.contexto_proativo()
        with patch("modulos.dark_souls.contexto",return_value=None):
            c["executar"]()
            c["executar"]()
        self.assertEqual(1,c["gerar_resposta"].call_count)
        fala = c["_falar_proativamente"].call_args.args[0]
        self.assertEqual({"noticia":URL}, fala.links_novidades)
        self.assertEqual(self.id, fala.cartoes_web[0]["id"])
        self.assertEqual("fontes", fala.cartoes_web[0]["origem"])
        self.assertEqual(NOVO, fala.cartoes_web[0]["trecho"])
        self.assertEqual(1,c["_gerar_fala_proativa"].call_count)
        self.assertIsNone(fontes.proxima_novidade())

    def test_usuario_interrompe_classificacao_sem_consumir_novidade(self):
        self.candidato()
        c = self.contexto_proativo()
        def gerar(*a,**k):
            c["_execucoes"].avisar_usuario()
            return '{"relevante":false}'
        c["gerar_resposta"].side_effect = gerar
        with patch("modulos.dark_souls.contexto",return_value=None):
            c["executar"]()
        self.assertEqual(1,len(self.ler()["pendentes"]))
        c["_falar_proativamente"].assert_not_called()

    def test_jogo_e_pausa_impedem_llm_e_perda_de_janela_preserva_aviso(self):
        self.classificar()
        c = self.contexto_proativo()
        c["_STEAM_JOGANDO_AGORA"]=True
        with patch("modulos.dark_souls.contexto",return_value=None):
            c["executar"]()
            c["_gerar_fala_proativa"].assert_not_called()
            c["_STEAM_JOGANDO_AGORA"]=False
            def gerar(*a,**k):
                c["_STEAM_JOGANDO_AGORA"]=True
                return c["_FalaProativa"]("Aviso atrasado")
            c["_gerar_fala_proativa"].side_effect=gerar
            c["executar"]()
        self.assertIsNotNone(fontes.proxima_novidade())
        c["registrar_tentativa"].assert_not_called()

    def test_websocket_estado_e_feedback_com_request_id(self):
        arvore = ast.parse(Path("servidor.py").read_text(encoding="utf-8"))
        fn = next(n for n in arvore.body if isinstance(n,ast.FunctionDef) and n.name=="websocket")
        fn.decorator_list=[]
        mensagens=iter([json.dumps({"comando":"fonte_acao","acao":"pausar","id":self.id,"request_id":"a"}),
                        json.dumps({"comando":"fonte_acao","acao":"editar","id":self.id,"cadastro":{},"request_id":"b"})])
        enviados=[]
        from simple_websocket import ConnectionClosed
        def receber(**kwargs):
            mensagem = next(mensagens, None)
            if mensagem is None:
                raise ConnectionClosed()
            return mensagem
        ws=Mock(); ws.send=lambda s:enviados.append(json.loads(s)); ws.receive=receber
        c={"json":json,"request":types.SimpleNamespace(remote_addr="127.0.0.1"),"_clientes":set(),
           "_ClienteWeb":lambda ws:ws,"_fila_texto_web":lambda:[],
           "_clientes_lock":threading.Lock(),"_ultima_fala_usuario":"","_ultima_fala_luna":"",
           "_ultimo_pensamento":"","_ultimo_estado_rosto":None,"_ultimo_kaomoji":None,
           "_ultimo_status":"","_historico_web":[],"_config_para_web":lambda:{},
           "_memoria_estado":lambda:{"pendentes":[]},
           "_acompanhamentos_estado":lambda:{"fontes":fontes.estado_interface()},
           "notificar_acompanhamentos":Mock(), "ConnectionClosed":ConnectionClosed}
        exec(compile(ast.Module(body=[fn],type_ignores=[]),"websocket-isolado","exec"),c)
        c["websocket"](ws)
        respostas=[p for p in enviados if p.get("tipo")=="fonte_feedback"]
        self.assertEqual(["a","b"],[p["request_id"] for p in respostas])
        self.assertTrue(respostas[0]["ok"]); self.assertFalse(respostas[1]["ok"])
        self.assertTrue(next(p for p in enviados if p.get("tipo")=="acompanhamentos")["estado"]["fontes"]["itens"])


if __name__ == "__main__":
    unittest.main()
