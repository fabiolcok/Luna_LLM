"""Transições, expiração e prioridade do piloto sem acessar jogo, GPU ou voz."""
import ast
from copy import deepcopy
import json
from pathlib import Path
import struct
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch, Mock

from integracoes.dark_souls.leitor import flag_offset, localizar, LeituraIndisponivel
from modulos import dark_souls, momento
from modulos.vozes_kokoro import vozes_para_web


def snapshot(mortes=13, chefe=False, fogo=0, sessao="processo:slot:ng", tempo=10000):
    return {"sessao": sessao, "jogo": "DARK SOULS REMASTERED", "mortes": mortes,
            "tempo_jogo_ms": tempo, "chefes": {"3": {"nome": "Bell Gargoyles", "derrotado": chefe}},
            "fogueiras": {"1011964": {"nome": "Undead Parish", "estado": fogo}}}


def confirmar(m, s, t):
    m.observar(s, t)
    return m.observar(s, t + 1)


def funcao(arquivo, nome, escopo):
    arvore = ast.parse(Path(arquivo).read_text(encoding="utf-8"))
    nos = [n for n in arvore.body if isinstance(n, ast.FunctionDef) and n.name == nome]
    exec(compile(ast.Module(body=nos, type_ignores=[]), arquivo, "exec"), escopo)
    return escopo[nome]


class TestaDarkSouls(unittest.TestCase):
    def setUp(self):
        self.m = dark_souls.Monitor()
        confirmar(self.m, snapshot(), 100)

    def test_baseline_nao_comemora_progresso_anterior(self):
        m = dark_souls.Monitor()
        self.assertEqual(confirmar(m, snapshot(400, True, 20), 100), [])
        self.assertIsNone(m.proximo(102))
        self.assertEqual(m.mortes_sessao, 0)

    def test_morte_confirmada_uma_vez_sem_tentativas_de_chefe(self):
        eventos = confirmar(self.m, snapshot(14), 102)
        self.assertEqual([e["tipo"] for e in eventos], ["morte"])
        self.assertEqual(eventos[0]["mortes_sessao"], 1)
        self.assertEqual(self.m.observar(snapshot(14), 104), [])
        self.assertEqual(self.m.proximo(104)["id"], eventos[0]["id"])
        self.assertIsNone(self.m.proximo(104))

    def test_chefes_e_fogueiras_so_na_transicao_sem_repetir_ao_recarregar(self):
        eventos = confirmar(self.m, snapshot(13, True, 10), 102)
        self.assertEqual([e["tipo"] for e in eventos], ["chefe", "fogueira"])
        self.assertEqual(self.m.proximo(104)["tipo"], "chefe")
        confirmar(self.m, snapshot(13, False, -1), 105)
        self.assertEqual(confirmar(self.m, snapshot(13, True, 20), 107), [])

    def test_estado_transitorio_nao_cria_conquista(self):
        self.m.observar(snapshot(14, True, 10), 102)
        self.assertEqual(confirmar(self.m, snapshot(), 103), [])

    def test_troca_de_personagem_ng_ou_processo_reinicia_referencia(self):
        for sessao in ("outro-slot", "ng+1", "novo-processo"):
            self.assertEqual(confirmar(self.m, snapshot(900, True, 40, sessao), 102), [])
            self.assertEqual(self.m.mortes_sessao, 0)

    def test_restaurar_save_nao_reproduz_mortes_ou_chefes(self):
        confirmar(self.m, snapshot(14, True, 10, tempo=20000), 102)
        self.assertEqual(confirmar(self.m, snapshot(13, False, 0, tempo=1000), 104), [])
        self.assertIsNone(self.m.proximo(106))

    def test_gap_longo_faz_baseline_e_loading_curto_preserva_diferenca(self):
        self.m.indisponivel()
        self.assertIsNone(self.m.contexto(102))
        self.assertEqual(confirmar(self.m, snapshot(14), 103)[0]["tipo"], "morte")
        self.m.indisponivel()
        self.assertEqual(confirmar(self.m, snapshot(15, True), 200), [])

    def test_evento_expira_sem_falar_atrasado(self):
        evento = confirmar(self.m, snapshot(14), 102)[0]
        self.m.observar(snapshot(14), 140)
        self.assertFalse(self.m.valido(evento, 140))
        self.assertIsNone(self.m.proximo(140))

    def test_vitoria_substitui_morte_inclusive_enquanto_gera(self):
        morte = confirmar(self.m, snapshot(14), 102)[0]
        self.m.proximo(104)
        confirmar(self.m, snapshot(14, True), 105)
        self.assertFalse(self.m.valido(morte, 107))
        self.assertEqual(self.m.proximo(107)["tipo"], "chefe")

    def test_intervalo_morte_nao_bloqueia_chefe(self):
        morte = confirmar(self.m, snapshot(14), 102)[0]
        self.m.proximo(104)
        self.m.entregue(morte, 104)
        confirmar(self.m, snapshot(15), 105)
        self.assertIsNone(self.m.proximo(107))
        confirmar(self.m, snapshot(15, True), 120)
        self.assertEqual(self.m.proximo(122)["tipo"], "chefe")

    def test_contexto_expira_e_telegram_nao_recebe(self):
        confirmar(self.m, snapshot(14, True), 102)
        dados = self.m.contexto(104)
        with patch.object(dark_souls, "contexto", return_value=dados), patch.object(momento, "_jogos", {}):
            web = momento.capturar(canal="web", agora=104)
            self.assertIn("Bell Gargoyles", web["dark_souls"])
            self.assertEqual(momento.jogo_unico(web), "DARK SOULS REMASTERED")
            self.assertNotIn("dark_souls", momento.capturar(canal="telegram", agora=104))
            formatar = funcao("modulos/prompts.py", "contexto_momento", {"LIMITE_CONTEXTO_MOMENTO": 800})
            self.assertLessEqual(len(formatar(web)), 800)
            self.assertIn("Bell Gargoyles", formatar(web))
        self.assertIsNone(self.m.contexto(110))

    def test_momento_proativo_sem_total_preserva_morte_e_contexto_reativo(self):
        confirmar(self.m, snapshot(14), 102)
        dados = self.m.contexto(104)
        with patch.object(dark_souls, "contexto", return_value=dados), patch.object(momento, "_jogos", {}):
            proativo = momento.capturar(canal="proativo", agora=104)
            self.assertIn("personagem morreu", proativo["dark_souls"])
            self.assertNotIn("mortes acompanhadas", proativo["dark_souls"])
            for canal in ("web", "voz"):
                self.assertIn("1 mortes acompanhadas", momento.capturar(canal=canal, agora=104)["dark_souls"])
            # O jogo ainda é reconhecido antes do primeiro evento, sem um total zero no prompt.
            dados["eventos"] = []
            proativo = momento.capturar(canal="proativo", agora=104)
            self.assertNotIn("dark_souls", proativo)
            self.assertEqual(momento.jogo_unico(proativo), "DARK SOULS REMASTERED")

    def test_desligado_ou_fora_de_foco_invalida_fala_em_andamento(self):
        servico = dark_souls.Servico(lambda: True, Mock())
        servico.monitor = self.m
        evento = confirmar(self.m, snapshot(14), 102)[0]
        with patch.object(dark_souls, "habilitado", return_value=True), patch.object(dark_souls.time, "time", return_value=104):
            self.assertFalse(servico._valido(evento))
            servico.em_foco = True
            self.assertTrue(servico._valido(evento))
            servico.stop.set()
            self.assertFalse(servico._valido(evento))

    def test_cancelamento_apos_geracao_nao_entrega(self):
        entregar = Mock()
        valido = Mock(side_effect=[True, False])
        alvo = funcao("modulos/proativa.py", "_comentar_evento_dark_souls", {
            "_gerar_fala_proativa": Mock(return_value="fala"), "_falar_proativamente": entregar,
            "_prompts": SimpleNamespace(prompt_dark_souls=lambda e: "briefing"),
            "_limpar_visual_proativo": Mock()})
        self.assertFalse(alvo({"tipo": "morte"}, valido))
        entregar.assert_not_called()

    def test_assinatura_relativa_e_ambiguidade(self):
        codigo = b"\x48\x8b\x05" + struct.pack("<i", 25) + b"\xc6\x40\x18\x00"
        self.assertEqual(localizar(codigo, 100, "48 8b 05 ? ? ? ? c6 40 18 00", 7), 132)
        with self.assertRaises(LeituraIndisponivel):
            localizar(codigo * 2, 100, "48 8b 05 ? ? ? ? c6 40 18 00", 7)

    def test_flags_de_chefe_e_catalogo_nao_inclui_enum_de_estados(self):
        self.assertEqual(flag_offset(3), (0, 0x10000000))
        self.assertEqual(flag_offset(11010902), (0x500 + 2 * 0x500 + 112, 0x02000000))
        catalogo = json.loads(Path("integracoes/dark_souls/catalogo.json").read_text(encoding="utf-8"))
        self.assertEqual(len(catalogo["chefes"]), 26)
        self.assertEqual(len(catalogo["fogueiras"]), 43)
        self.assertTrue(all(int(k) > 1000000 for k in catalogo["fogueiras"]))

    def test_log_explica_quando_a_fala_perde_foco(self):
        mensagens = []
        def falar(evento, validar):
            servico.em_foco = False
            return validar()
        servico = dark_souls.Servico(lambda: True, falar, mensagens.append)
        servico.monitor = self.m
        e = confirmar(self.m, snapshot(13, True), 102)[0]
        servico.em_foco = True
        with patch.object(dark_souls, "habilitado", return_value=True), patch.object(dark_souls.time, "time", return_value=104):
            servico._entregar(e)
        self.assertIn("jogo saiu do primeiro plano", mensagens[-1])
        self.assertNotIn("entregue]", mensagens[-1])

    def test_loading_e_expiracao_tem_motivos_distintos(self):
        e = confirmar(self.m, snapshot(13, True), 102)[0]
        self.m.indisponivel()
        self.assertIn("leitura", self.m.motivo_bloqueio(e, 104))
        self.assertIn("expirou", self.m.motivo_bloqueio(e, 200))


class TestaConfigDarkSouls(unittest.TestCase):
    def setUp(self):
        pasta = tempfile.TemporaryDirectory()
        self.addCleanup(pasta.cleanup)
        self.config = Path(pasta.name) / "piloto.json"
        for nome, valor in (("CONFIG", self.config), ("_servico", None)):
            p = patch.object(dark_souls, nome, valor)
            p.start()
            self.addCleanup(p.stop)
        self.mensagens = []
        self.salvar_geral = Mock()
        self.estado = {"proativo": True, "tarefas": {"jogos": True}}
        self.para_web = funcao("servidor.py", "_config_para_web", {
            "_estado_config": self.estado, "_config_handlers": {},
            "_personalidade_pendente": False, "_personalidade_erro": "",
            "vozes_para_web": vozes_para_web,
        })
        self.aplicar = funcao("servidor.py", "_aplicar_config", {
            "_estado_config": self.estado, "_config_handlers": {},
            "_config_para_web": self.para_web, "_broadcast": self.mensagens.append,
            "_salvar_config": self.salvar_geral,
        })

    def test_web_e_cli_compartilham_config_e_reabertura_mostra_estado_real(self):
        self.assertFalse(self.para_web()["dark_souls"])
        self.aplicar({"config": "dark_souls", "valor": True})
        self.assertTrue(dark_souls.habilitado())
        self.assertTrue(self.mensagens[-1]["estado"]["dark_souls"])
        from integracoes.dark_souls import piloto
        with patch("sys.argv", ["piloto", "desativar"]), patch("builtins.print"):
            piloto.main()
        self.assertFalse(self.para_web()["dark_souls"])
        self.assertNotIn("dark_souls", self.estado)
        self.salvar_geral.assert_not_called()

    def test_valor_invalido_ou_falha_na_gravacao_restaura_estado_no_painel(self):
        for valor in ("false", 1, None):
            self.aplicar({"config": "dark_souls", "valor": valor})
            self.assertFalse(self.mensagens[-1]["estado"]["dark_souls"])
            self.assertTrue(self.mensagens[-1]["estado"]["dark_souls_erro"])
        with patch.object(Path, "replace", side_effect=OSError("teste")):
            self.aplicar({"config": "dark_souls", "valor": True})
        self.assertFalse(dark_souls.habilitado())
        self.assertTrue(self.mensagens[-1]["estado"]["dark_souls_erro"])

    def test_desligar_e_religar_nao_ressuscita_comentario_em_geracao(self):
        servico = dark_souls.Servico(lambda: True, Mock())
        dark_souls.configurar(True)
        confirmar(servico.monitor, snapshot(), 100)
        antigo = confirmar(servico.monitor, snapshot(13, True), 102)[0]
        with patch.object(dark_souls, "_servico", servico):
            dark_souls.configurar(False)
            dark_souls.configurar(True)
            confirmar(servico.monitor, snapshot(13, True), 104)
            self.assertFalse(servico.monitor.valido(antigo, 106))


if __name__ == "__main__":
    unittest.main()
