"""Avaliações sem servidor, modelo, som ou gravação no log do usuário."""
import ast
from collections import OrderedDict
import json
from pathlib import Path
import re
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from modulos import avaliacoes, metricas_ferramentas
from modulos.execucoes import Coordenador


class TestaAvaliacoes(unittest.TestCase):
    def setUp(self):
        pasta = tempfile.TemporaryDirectory()
        self.addCleanup(pasta.cleanup)
        self.arquivo = Path(pasta.name) / "avaliacoes.jsonl"
        self.controle = Coordenador(pausa=0)
        for nome, valor in (("ARQUIVO", self.arquivo), ("_turnos", OrderedDict()),
                            ("_revisoes", {}), ("controle", self.controle)):
            p = patch.object(avaliacoes, nome, valor)
            p.start()
            self.addCleanup(p.stop)
        p = patch.object(metricas_ferramentas, "vincular_avaliacao", return_value=None)
        p.start()
        self.addCleanup(p.stop)
        # Importar o servidor inteiro carrega integrações que este contrato não usa.
        raiz = Path(__file__).resolve().parents[1]
        arvore = ast.parse((raiz / "servidor.py").read_text(encoding="utf-8"))
        nos = [n for n in arvore.body if isinstance(n, ast.FunctionDef)
               and n.name in ("_registrar_avaliacao", "_registrar_turno")]
        self.escopo = dict(_historico_web=[], _clima_turno_pendente="", _broadcast=lambda x: None,
                           cor=SimpleNamespace(cinza=lambda x: None))
        exec(compile(ast.Module(body=nos, type_ignores=[]), "servidor.py", "exec"), self.escopo)
        self.votar = self.escopo["_registrar_avaliacao"]

    def capturar(self, usuario="primeira pergunta", luna="primeira resposta", **kwargs):
        return avaliacoes.capturar_turno({"usuario": usuario, "luna": luna}, **kwargs)

    def test_motivo_continua_na_resposta_escolhida(self):
        primeiro = self.capturar()
        self.votar("ruim", turno_id=primeiro)
        segundo = self.capturar("segunda pergunta", "segunda resposta")
        self.escopo["_historico_web"].append({"id": segundo})
        self.votar("ruim", "perdeu o filme", turno_id=primeiro, categorias=["perdeu_assunto"])
        registros = avaliacoes.ler_consolidadas()
        self.assertEqual(len(registros), 1)
        self.assertEqual(registros[0]["usuario"], "primeira pergunta")
        self.assertEqual(registros[0]["luna"], "primeira resposta")
        self.assertEqual(registros[0]["revisao"], 2)
        self.assertEqual(registros[0]["categorias"], ["perdeu_assunto"])

    def test_snapshot_independe_de_mutacoes_posteriores(self):
        historico = [{"role": "user", "content": "vou ver um filme"}]
        with self.controle.executar():
            avaliacoes.registrar_contexto(historico_modelo=historico, caminho_prompt="PROMPT_COMPLETO")
            avaliacoes.registrar_chamada("modelo-teste", {"messages": [{"role": "system", "content": "abc"}]})
            identificador = self.capturar()
            avaliacoes.registrar_contexto(caminho_prompt="outro")
        historico[0]["content"] = "trocou"
        snapshot = avaliacoes.obter_turno(identificador)
        self.assertEqual(snapshot["contexto"]["historico_modelo"][0]["content"], "vou ver um filme")
        self.assertEqual(snapshot["contexto"]["caminho_prompt"], "PROMPT_COMPLETO")
        self.assertEqual(snapshot["contexto"]["chamadas"][0]["prompt_sistema_chars"], 3)
        snapshot["luna"] = "alterada"
        self.assertEqual(avaliacoes.obter_turno(identificador)["luna"], "primeira resposta")
        with self.controle.executar():
            outro = self.capturar()
        self.assertNotIn("caminho_prompt", avaliacoes.obter_turno(outro)["contexto"])

    def test_id_expirado_ou_canal_errado_nao_avalia_ultima(self):
        identificador = self.capturar()
        self.escopo["_historico_web"].append({"id": identificador})
        self.assertIsNone(self.votar("ruim", turno_id="expirado"))
        self.assertIsNone(self.votar("ruim", turno_id=identificador, canal="telegram"))
        self.assertFalse(self.arquivo.exists())

    def test_voto_repetido_nao_duplica_e_troca_rating_vira_revisao(self):
        identificador = self.capturar()
        self.votar("bom", turno_id=identificador)
        self.votar("bom", turno_id=identificador)
        self.assertEqual(len(self.arquivo.read_text(encoding="utf-8").splitlines()), 1)
        self.votar("ruim", turno_id=identificador)
        self.assertEqual(avaliacoes.ler_consolidadas()[0]["rating"], "ruim")
        self.assertEqual(avaliacoes.ler_consolidadas()[0]["revisao"], 2)

    def test_preserva_metadados_ferramenta_ao_complementar(self):
        identificador = self.capturar()
        with patch.object(metricas_ferramentas, "vincular_avaliacao", return_value={"nome": "buscar"}):
            self.votar("ruim", turno_id=identificador)
        self.votar("ruim", "resultado errado", turno_id=identificador)
        self.assertEqual(avaliacoes.ler_consolidadas()[0]["ferramenta"], {"nome": "buscar"})

    def test_legado_preservado_e_linha_quebrada_ignorada(self):
        legado = {"rating": "ruim", "motivo": "antigo"}
        self.arquivo.write_text(json.dumps(legado) + "\n{quebrado\n", encoding="utf-8")
        identificador = self.capturar()
        self.votar("bom", turno_id=identificador)
        self.votar("bom", "humor bom", turno_id=identificador)
        registros = avaliacoes.ler_consolidadas()
        self.assertEqual(len(registros), 2)
        self.assertEqual(registros[0], legado)
        self.assertTrue(self.arquivo.read_text(encoding="utf-8").startswith(json.dumps(legado)))

    def test_filtra_categorias_e_limita_texto(self):
        identificador = self.capturar()
        self.votar("ruim", "x" * 2000, turno_id=identificador,
                   categorias=["inventou_informacao", "inventou_informacao", "qualquer", {}, "humor_bom"])
        registro = avaliacoes.ler_consolidadas()[0]
        self.assertEqual(registro["categorias"], ["inventou_informacao", "humor_bom"])
        self.assertEqual(len(registro["motivo"]), 1000)

    def test_todos_motivos_da_interface_sao_salvos(self):
        html = (Path(__file__).resolve().parents[1] / "templates/Index.html").read_text(encoding="utf-8")
        opcoes = re.findall(r'data-categoria="([^"]+)" data-voto="([^"]+)"', html)
        self.assertTrue(opcoes)
        for rating in ("bom", "ruim"):
            categorias = [categoria for categoria, voto in opcoes if voto == rating]
            with self.subTest(rating=rating):
                identificador = self.capturar()
                self.votar(rating, turno_id=identificador, categorias=categorias)
                registro = avaliacoes.ler_consolidadas()[-1]
                self.assertEqual(registro["categorias"], categorias)
                self.assertEqual(registro["rating"], rating)

    def test_cache_limitado_e_contexto_truncado(self):
        with patch.object(avaliacoes, "_LIMITE", 2):
            antigo = self.capturar()
            self.capturar()
            novo = self.capturar(anteriores=[{"usuario": "x" * 1000}] * 6)
        self.assertIsNone(avaliacoes.obter_turno(antigo))
        contexto = avaliacoes.obter_turno(novo)["contexto"]["conversa_anterior"]
        self.assertEqual(len(contexto), 3)
        self.assertEqual(len(contexto[0]["usuario"]), 700)

    def test_respostas_iguais_em_execucoes_distintas_tem_ids_distintos(self):
        registrar = self.escopo["_registrar_turno"]
        with self.controle.executar():
            registrar("oi", "olá")
            registrar("oi", "olá")
        with self.controle.executar():
            registrar("oi", "olá")
        turnos = self.escopo["_historico_web"]
        self.assertEqual(len(turnos), 2)
        self.assertNotEqual(turnos[0]["id"], turnos[1]["id"])

    def test_telegram_usa_mesmo_formato_sem_contexto_web(self):
        identificador = self.capturar(canal="telegram")
        self.votar("bom", turno_id=identificador, canal="telegram")
        self.assertEqual(avaliacoes.ler_consolidadas()[0]["canal"], "telegram")

    def test_botoes_telegram_vinculam_e_expiram_juntos(self):
        raiz = Path(__file__).resolve().parents[1]
        arvore = ast.parse((raiz / "modulos/telegram_bot.py").read_text(encoding="utf-8"))
        funcao = next(n for n in arvore.body if isinstance(n, ast.FunctionDef)
                      and n.name == "_registrar_exchange")
        escopo = dict(_aval_seq=0, _avaliacoes={}, _aval_ids={})
        exec(compile(ast.Module(body=[funcao], type_ignores=[]), "telegram_bot.py", "exec"), escopo)
        for i in range(41):
            aid = escopo["_registrar_exchange"](str(i), "resposta")
        self.assertNotIn("1", escopo["_aval_ids"])
        self.assertEqual(len(escopo["_aval_ids"]), 40)
        self.assertEqual(len(escopo["_avaliacoes"]), 40)
        snapshot = avaliacoes.obter_turno(escopo["_aval_ids"][aid])
        self.assertEqual(snapshot["usuario"], "40")
        self.assertEqual(snapshot["canal"], "telegram")


if __name__ == "__main__":
    unittest.main()
