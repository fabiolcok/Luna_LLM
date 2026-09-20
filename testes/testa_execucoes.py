"""Concorrência real, sem engine, som, rede ou importação do main."""
import ast
from pathlib import Path
import threading
import unittest
from functools import wraps
from types import SimpleNamespace
from unittest.mock import patch

from modulos import execucoes
from modulos.execucoes import Coordenador, ExecucaoCancelada


class TestaExecucoes(unittest.TestCase):
    def test_fila_respeita_recebimento_mesmo_com_threads_invertidas(self):
        c = Coordenador(pausa=0)
        ordem = []
        a, b = c.reservar(), c.reservar()
        def atender(turno, texto):
            with c.executar(turno):
                ordem.append(texto)
        segundo = threading.Thread(target=atender, args=(b, "segunda"))
        segundo.start()
        atender(a, "primeira")
        segundo.join(2)
        self.assertFalse(segundo.is_alive())
        self.assertEqual(ordem, ["primeira", "segunda"])

    def test_usuario_cancela_radar_sem_efeitos_tardios(self):
        c = Coordenador(pausa=0)
        efeitos = []
        c.parar_audio = lambda: efeitos.append("stop")
        publicar = c.efeito(efeitos.append)
        with c.executar(proativa=True) as velho:
            with patch.object(execucoes, "controle", c):
                callback = execucoes.vincular(lambda: publicar("radar tardio"))
            usuario = c.reservar()
            self.assertTrue(velho.cancelada.is_set())
            publicar("legenda tardia")
            with self.assertRaises(ExecucaoCancelada):
                c.verificar()
        with c.executar(usuario):
            thread = threading.Thread(target=callback)
            thread.start(); thread.join(2)
            publicar("resposta atual")
        self.assertEqual(efeitos, ["stop", "resposta atual"])

    def test_nao_sobrepoe_engine_bloqueada_com_nova_chamada(self):
        c = Coordenador(pausa=0)
        entrou = threading.Event()
        liberar = threading.Event()
        respondeu = threading.Event()
        def radar():
            with c.executar(proativa=True):
                entrou.set()
                liberar.wait(2)
        t = threading.Thread(target=radar); t.start()
        self.assertTrue(entrou.wait(2))
        reserva = c.reservar()
        def usuario():
            with c.executar(reserva):
                respondeu.set()
        u = threading.Thread(target=usuario); u.start()
        self.assertFalse(respondeu.wait(.05))
        liberar.set(); t.join(2); u.join(2)
        self.assertTrue(respondeu.is_set())

    def test_proativo_aguarda_fila_e_intervalo_apos_conversa(self):
        c = Coordenador(pausa=30)
        reserva = c.reservar()
        with self.assertRaises(ExecucaoCancelada):
            with c.executar(proativa=True):
                self.fail("radar furou a fila")
        with c.executar(reserva):
            pass
        with self.assertRaises(ExecucaoCancelada):
            with c.executar(proativa=True):
                self.fail("radar interrompeu a pausa")
        c.retomar_em = 0
        with c.executar(proativa=True):
            c.verificar()

    def test_erro_libera_execucao_e_contexto(self):
        c = Coordenador(pausa=0)
        with self.assertRaises(ValueError):
            with c.executar():
                raise ValueError("falha simulada")
        self.assertIsNone(c.atual)
        self.assertIsNone(c.contexto.get())
        with c.executar():
            c.verificar()

    def test_reserva_web_e_aninhamento_nao_perdem_mensagens(self):
        c = Coordenador(pausa=0)
        entregues = []
        with patch.object(execucoes, "controle", c):
            @execucoes.conversa
            def responder(texto):
                with c.executar():
                    entregues.append(texto)
            a, b = responder.preparar("a"), responder.preparar("b")
            a(); b()
        self.assertEqual(entregues, ["a", "b"])

    def test_todas_as_tarefas_proativas_tem_reserva(self):
        fonte = Path("modulos/proativa.py").read_text(encoding="utf-8")
        for node in ast.parse(fonte).body:
            if isinstance(node, ast.FunctionDef) and node.name.startswith("_tarefa_"):
                self.assertIn(f"{node.name} = _execucao_proativa({node.name})", fonte)

    def carregar_funcao(self, arquivo, nome, escopo):
        arvore = ast.parse(Path(arquivo).read_text(encoding="utf-8"))
        nos = [n for n in arvore.body if isinstance(n, ast.FunctionDef) and n.name == nome]
        self.assertEqual(len(nos), 1)
        exec(compile(ast.Module(body=nos, type_ignores=[]), arquivo, "exec"), escopo)
        return escopo[nome]

    def test_tarefa_cancelada_reconsulta_dados_sem_consumir_intervalo(self):
        c = Coordenador(pausa=0)
        intervalos = {"radar_rss": 10}
        decorar = self.carregar_funcao("modulos/proativa.py", "_execucao_proativa", {
            "_wraps": wraps, "_execucoes": c, "ExecucaoCancelada": ExecucaoCancelada,
            "_ultima_execucao": intervalos,
        })
        @decorar
        def radar():
            intervalos["radar_rss"] = 999
            c.reservar()
            c.verificar()
        self.assertIsNone(radar())
        self.assertEqual(intervalos, {"radar_rss": 10})

    def test_stream_fecha_ao_cancelar_sem_entregar_token_atrasado(self):
        c = Coordenador(pausa=0)
        class Resposta:
            fechada = False
            def __iter__(self):
                yield "primeiro"
                c.reservar()
                yield "atrasado"
            def close(self):
                self.fechada = True
        resposta = Resposta()
        with c.executar(proativa=True):
            stream = c.vigiar_stream(resposta)
            self.assertEqual(next(stream), "primeiro")
            with self.assertRaises(ExecucaoCancelada):
                next(stream)
        self.assertTrue(resposta.fechada)

    def test_chamada_llm_descarta_resposta_cancelada_e_limita_retries(self):
        c = Coordenador(pausa=0)
        opcoes = {}
        def gerar(**kwargs):
            c.reservar()
            return "resposta velha"
        alvo = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=gerar)))
        def configurar(**kwargs):
            opcoes.update(kwargs)
            return alvo
        chamar = self.carregar_funcao("modulos/pensar.py", "_chamar_llm", {
            "controle": c, "ExecucaoCancelada": ExecucaoCancelada, "_ciclo_modelo": 1,
            "cliente": SimpleNamespace(with_options=configurar), "modelo": lambda: "teste",
            "erro_modelo_descarregado": lambda e: False,
        })
        with c.executar(proativa=True):
            with self.assertRaises(ExecucaoCancelada):
                chamar(messages=[])
        self.assertEqual(opcoes, {"timeout": 120.0, "max_retries": 0})

    def test_cancelamento_durante_sintese_nao_inicia_audio(self):
        c = Coordenador(pausa=0)
        efeitos = []
        def sintetizar(*args):
            c.reservar()
            return [1, 2]
        falar = self.carregar_funcao("modulos/falar.py", "falar_texto", {
            "controle": c, "_pipe": True, "_voz_padrao": "teste",
            "_VOZES_VALIDAS": {"teste"}, "_velocidade_padrao": 1,
            "limpar_texto_para_voz": lambda t: t,
            "_sintetizar_wav": sintetizar, "_tocar_com_volume": efeitos.append,
            "cor": SimpleNamespace(ciano=lambda t: None),
            "print": lambda *a: None,
        })
        with c.executar(proativa=True):
            falar("novidade", ao_iniciar=lambda: efeitos.append("falando"))
        self.assertEqual(efeitos, [])

    def test_servidor_nao_muda_estado_nem_broadcast_do_turno_cancelado(self):
        c = Coordenador(pausa=0)
        enviados = []
        escopo = {"controle": c, "_ultimo_estado_rosto": "dormindo",
                  "_ultima_fala_usuario": "", "_broadcast": enviados.append,
                  "cor": SimpleNamespace(cinza=lambda t: None)}
        nomes = {"atualizar_estado_rosto", "atualizar_usuario"}
        arvore = ast.parse(Path("servidor.py").read_text(encoding="utf-8"))
        nos = [n for n in arvore.body if
               (isinstance(n, ast.FunctionDef) and n.name in nomes) or
               (isinstance(n, ast.Assign) and isinstance(n.targets[0], ast.Name)
                and n.targets[0].id in nomes)]
        exec(compile(ast.Module(body=nos, type_ignores=[]), "servidor.py", "exec"), escopo)
        with c.executar(proativa=True):
            usuario = c.reservar()
            escopo["atualizar_estado_rosto"]("falando")
            escopo["atualizar_usuario"]("antigo")
        self.assertEqual(enviados, [])
        self.assertEqual(escopo["_ultimo_estado_rosto"], "dormindo")
        with c.executar(usuario):
            escopo["atualizar_estado_rosto"]("pensando")
        self.assertEqual(enviados, [{"estado": "pensando"}])


if __name__ == "__main__":
    unittest.main()
