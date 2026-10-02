"""Regressao do radar repetindo noticias depois de interromper audio; sem rede ou TTS."""
import ast
from copy import deepcopy
from functools import wraps
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from modulos.execucoes import Coordenador, ExecucaoCancelada


class TestaRadarInterrupcao(unittest.TestCase):
    def setUp(self):
        self.c = Coordenador(pausa=0)
        self.agora = 10000.0
        self.disk = {"radar": {}, "radar_feeds": ["feed"]}
        self.cards, self.legendas, self.geracoes = [], [], []
        self.tentativas = 0
        self.modo = "normal"
        self.feed = SimpleNamespace(entries=[{"id": "noticia", "link": "https://example.org/n",
                                               "title": "Noticia", "summary": "Resumo"}],
                                    feed={"title": "Teste"})
        def salvar(v):
            self.disk = deepcopy(v)
        def gerar(*args, **kwargs):
            self.geracoes.append(args)
            if self.modo == "geracao":
                self.c.avisar_usuario()
                self.c.verificar()
            if self.modo == "vazio":
                return None
            return self.e["_FalaProativa"]("Comentario.", "radar_rss", "zoeira")
        def tentar():
            self.tentativas += 1
        def livre():
            if self.modo == "espera":
                self.c.avisar_usuario()
            return True
        def falar(texto, ao_iniciar, ao_terminar):
            if self.modo == "sintese":
                self.c.avisar_usuario()
                return
            ao_iniciar()
            if self.modo == "audio":
                self.c.avisar_usuario()
            ao_terminar()
        self.e = dict(_execucoes=self.c, ExecucaoCancelada=ExecucaoCancelada, _wraps=wraps,
            time=SimpleNamespace(time=lambda:self.agora,sleep=lambda t:None),
            random=SimpleNamespace(choice=lambda xs:xs[0],uniform=lambda a,b:a),
            CONFIGURACAO={"Radar_RSS":{"ativo":True,"horario_silencio":(0,0),"intervalo_minutos":60}},
            obsidian=SimpleNamespace(ler_feeds_radar=lambda:["feed"],link_novidades=lambda:"obsidian://open",
                                     adicionar_novidades=lambda novos:self.cards.extend(novos)),
            carregar_vistos=lambda:deepcopy(self.disk),salvar_vistos=salvar,
            _em_horario_silencio=lambda *args:False,_RADAR_MAX_VISTOS=1000,
            _limpar_resumo=lambda s:s,_extrair_imagem=lambda e:"",
            _gerar_fala_proativa=gerar,registrar_tentativa=tentar,REGRA_PERSONA="",
            _ultima_execucao={"radar_rss":0},_ultima_fala_proativa_ts=0,_cd_proativo_atual=0,
            _CD_PROATIVO_MIN=60,_CD_PROATIVO_MAX=120,_pode_falar_proativo=lambda:True,
            luna_esta_livre=livre,_limpar_visual_proativo=lambda:None,_historico_principal=[],
            _iniciar_visual_fala_proativa=lambda:None,_terminar_visual_fala_proativa=lambda:None,
            falar_texto=falar,cor=SimpleNamespace(amarelo=lambda s:None,vermelho=lambda s:None))
        tree=ast.parse(Path("modulos/proativa.py").read_text(encoding="utf8"))
        names={"_FalaProativa","_falar_proativamente","_tarefa_radar_rss","_passou_intervalo","_execucao_proativa"}
        nodes=[n for n in tree.body if isinstance(n,(ast.FunctionDef,ast.ClassDef)) and n.name in names]
        self.assertEqual(len(nodes),len(names))
        exec(compile(ast.Module(body=nodes,type_ignores=[]),"modulos/proativa.py","exec"),self.e)
        self.radar=self.e["_execucao_proativa"](self.e["_tarefa_radar_rss"])
        self.servidor=SimpleNamespace(atualizar_usuario=lambda s:None,
            atualizar_legenda=self.c.efeito(lambda texto,**kw:self.legendas.append(texto)))
        self.modules=patch.dict("sys.modules",{"servidor":self.servidor,
                         "feedparser":SimpleNamespace(parse=lambda *a,**k:self.feed)})
        self.modules.start()
        self.addCleanup(self.modules.stop)

    def test_interromper_audio_nao_reanuncia_nem_duplica_nota(self):
        self.modo="audio"
        self.radar()
        self.assertTrue(self.disk["radar"].get("noticia"))
        self.assertEqual(self.e["_ultima_execucao"]["radar_rss"],10000)
        for segundos in (55,55,3601):
            self.agora+=segundos
            self.radar()
        self.assertEqual(len(self.geracoes),1)
        self.assertEqual(len(self.cards),1)
        self.assertEqual(len(self.legendas),1)
        self.assertEqual(self.tentativas,1)

    def test_cancelar_sintese_apos_exibir_preserva_aviso(self):
        self.modo="sintese"
        self.radar()
        self.assertEqual(len(self.legendas),1)
        self.assertTrue(self.disk["radar"].get("noticia"))
        self.assertEqual(len(self.cards),1)

    def test_cancelar_antes_da_publicacao_nao_consume_noticia(self):
        for modo in ("geracao","espera"):
            with self.subTest(modo=modo):
                self.modo=modo
                self.radar()
                self.assertFalse(self.disk["radar"].get("noticia"))
                self.assertEqual(self.legendas,[])
                self.assertEqual(self.cards,[])
                self.assertEqual(self.e["_ultima_execucao"]["radar_rss"],0)
        self.modo="normal"
        self.radar()
        self.assertTrue(self.disk["radar"].get("noticia"))

    def test_aviso_normal_persiste_uma_vez_entre_legenda_e_audio(self):
        self.radar()
        self.assertEqual(len(self.cards),1)
        self.assertEqual(self.tentativas,1)
        self.assertTrue(self.disk["radar"].get("noticia"))

    def test_sem_legenda_confirma_so_quando_audio_inicia(self):
        def falhar(*a,**k):
            raise RuntimeError("Web indisponivel")
        self.servidor.atualizar_legenda=falhar
        self.modo="sintese"
        self.radar()
        self.assertFalse(self.disk["radar"].get("noticia"))
        self.modo="audio"
        self.radar()
        self.assertTrue(self.disk["radar"].get("noticia"))
        self.assertEqual(len(self.cards),1)

    def test_fala_vazia_permanece_pendente(self):
        self.modo="vazio"
        self.radar()
        self.assertFalse(self.disk["radar"].get("noticia"))
        self.assertEqual(self.cards,[])
        self.assertEqual(self.e["_ultima_execucao"]["radar_rss"],0)

    def test_feed_novo_apenas_semeia(self):
        self.disk["radar_feeds"]=[]
        self.radar()
        self.assertTrue(self.disk["radar"].get("noticia"))
        self.assertEqual(self.geracoes,[])
        self.assertEqual(self.cards,[])


if __name__=="__main__":
    unittest.main()
