"""Verifica os critérios da bancada sem carregar modelos nem memórias reais."""
import copy
import json
import unittest

from testes.bancada_embeddings import (
    CENARIOS, avaliar, avaliar_l2, calibrar_limiar, validar_cenarios,
)


def caso(id_, split, relevantes, ranking):
    return {"id": id_, "split": split, "relevantes": relevantes,
            "ranking": [{"id": nome, "score": score} for nome, score in ranking]}


class TestBancadaEmbeddings(unittest.TestCase):
    def test_limiar_nao_usa_teste_nem_positivas(self):
        linhas = [
            caso("n", "calibracao", [], [("a", .4)]),
            caso("p", "calibracao", ["a"], [("a", .9)]),
            caso("teste", "teste", [], [("a", .99)]),
        ]
        self.assertAlmostEqual(calibrar_limiar(linhas), .400001)
        linhas[-1]["ranking"][0]["score"] = 1
        self.assertAlmostEqual(calibrar_limiar(linhas), .400001)
        with self.assertRaises(ValueError):
            calibrar_limiar(linhas[1:])

    def test_ranking_e_ruido_sao_medidos_separadamente(self):
        linhas = [
            caso("p", "teste", ["certo"],
                 [("outro", .9), ("certo", .8), ("ruido", .7)]),
            caso("n", "teste", [], [("outro", .6), ("ruido", .3)]),
        ]
        m = avaliar(linhas, limiar=.75)
        self.assertEqual((m["hit1"], m["hit3"], m["mrr"]), (0, 1, .5))
        self.assertEqual(m["positivas_com_relevante"], 1)
        self.assertEqual(m["itens_corretos"], 1)
        self.assertEqual(m["itens_incorretos"], 1)
        self.assertEqual(m["negativas_com_memoria_indevida"], 0)
        self.assertEqual(avaliar(linhas, limiar=.5)["negativas_com_memoria_indevida"], 1)

    def test_filtro_nao_altera_acerto_do_ranking(self):
        linha = caso("p", "teste", ["a"], [("a", .52), ("b", .1)])
        aceito = avaliar([linha], limiar=.52)
        rejeitado = avaliar([linha], limiar=.53)
        self.assertEqual(aceito["positivas_com_relevante"], 1)
        self.assertEqual(rejeitado["positivas_com_relevante"], 0)
        self.assertEqual((aceito["hit1"], rejeitado["hit1"]), (1, 1))

    def test_l2_respeita_distancia_limite(self):
        linha = caso("p", "teste", ["a"], [])
        linha["ranking_l2"] = [
            {"id": "a", "distancia2": 1.3}, {"id": "b", "distancia2": 1.31},
        ]
        m = avaliar_l2([linha])
        self.assertEqual((m["itens_corretos"], m["itens_incorretos"]), (1, 0))

    def test_fixture_tem_rotulos_validos(self):
        dados = json.loads(CENARIOS.read_text(encoding="utf-8"))
        validar_cenarios(dados)
        invalido = copy.deepcopy(dados)
        suite = next(iter(invalido["suites"].values()))
        suite["consultas"][0]["relevantes"] = ["documento_inexistente"]
        with self.assertRaises(ValueError):
            validar_cenarios(invalido)


if __name__ == "__main__":
    unittest.main()
