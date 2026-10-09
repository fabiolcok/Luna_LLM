"""Migração e caminhos de memória sem modelos/rede ou notas privadas."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

import chromadb
import numpy as np

from modulos import embeddings, memoria
from modulos.indice_memoria import abrir_historico, COLECAO_ANTIGA, COLECAO_NOVA

RAIZ = Path(__file__).resolve().parents[1]


class EmbedderFake:
    def documentos(self, textos):
        v = np.zeros((len(textos), embeddings.DIMENSOES), dtype=np.float32)
        v[:, 0] = 1
        return v

    def consultas(self, textos):
        return self.documentos(textos)


class TestaMigracao(unittest.TestCase):
    def setUp(self):
        pasta = RAIZ / "logs/testes_embeddings"
        pasta.mkdir(parents=True, exist_ok=True)
        self.tmp = tempfile.TemporaryDirectory(dir=pasta)
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.cliente = chromadb.PersistentClient(path=str(self.base / "db"))
        self.addCleanup(self.cliente.close)
        self.antiga = self.cliente.create_collection(COLECAO_ANTIGA, embedding_function=None)
        self.embedder = EmbedderFake()

    def preencher(self, n=2):
        self.antiga.add(
            ids=[f"origem-{i}" for i in range(n)],
            documents=[f"Usuário: conversa {i}\nLuna: resposta {i}" for i in range(n)],
            metadatas=[{"timestamp": float(i), "data": "06/10/2026"} for i in range(n)],
            embeddings=np.ones((n, 384), dtype=np.float32),
        )

    def abrir(self):
        return abrir_historico(self.cliente, self.embedder, self.base / "backups")

    def test_copia_preserva_ids_textos_metadados_e_origem(self):
        self.preencher()
        antes = self.antiga.get(include=["documents", "metadatas", "embeddings"])
        nova, n = self.abrir()
        self.assertEqual(2, n)
        self.assertEqual("cosine", nova.configuration["hnsw"]["space"])
        atual = nova.get(include=["documents", "metadatas", "embeddings"])
        for chave in ("ids", "documents", "metadatas"):
            self.assertEqual(antes[chave], atual[chave])
        np.testing.assert_array_equal(
            antes["embeddings"], self.antiga.get(include=["embeddings"])["embeddings"])
        self.assertEqual((2, 768), atual["embeddings"].shape)
        self.assertEqual(1, len(list((self.base / "backups").glob("*.json"))))
        with patch.object(self.embedder, "documentos", side_effect=AssertionError("reindexou")):
            repetida, n = self.abrir()
        self.assertEqual(0, n)
        self.assertEqual(2, repetida.count())

    def test_retomada_apos_falha_nao_duplica_nem_marca_completa(self):
        self.preencher(10)
        normal = self.embedder.documentos
        tentativas = []
        def falhar(textos):
            tentativas.append(textos)
            if len(tentativas) == 2:
                raise RuntimeError("interrupção simulada")
            return normal(textos)
        with patch.object(self.embedder, "documentos", side_effect=falhar):
            with self.assertRaises(RuntimeError):
                self.abrir()
        parcial = self.cliente.get_collection(COLECAO_NOVA, embedding_function=None)
        self.assertEqual(8, parcial.count())
        self.assertFalse(parcial.metadata["migracao_concluida"])
        self.assertEqual(10, self.antiga.count())
        completa, n = self.abrir()
        self.assertEqual(10, n)
        self.assertEqual(10, completa.count())

    def test_nao_ressuscita_podadas_e_captura_fala_da_instancia_antiga(self):
        self.preencher()
        nova, _ = self.abrir()
        nova.delete(ids=["origem-0"])
        self.antiga.add(ids=["nova-na-origem"], documents=["Mais uma conversa"],
                        metadatas=[{"timestamp": 3.0}],
                        embeddings=np.ones((1, 384), dtype=np.float32))
        nova, n = self.abrir()
        self.assertEqual(1, n)
        self.assertEqual({"origem-1", "nova-na-origem"}, set(nova.get()["ids"]))

    def test_indice_incompativel_e_recusado(self):
        self.cliente.create_collection(COLECAO_NOVA, embedding_function=None,
                                        metadata={"embedding_model": "outro"})
        with self.assertRaises(ValueError):
            self.abrir()

    def test_novas_conversas_respeitam_limite_sem_alterar_origem(self):
        self.preencher()
        nova, _ = self.abrir()
        with patch.object(memoria, "_historico", return_value=nova), \
             patch.object(memoria, "_emb_mem", return_value=self.embedder), \
             patch.object(memoria, "NOME_USUARIO", "Usuário"):
            for i in range(35):
                memoria.salvar_conversa(f"Pergunta {i}", f"Resposta {i}")
        self.assertEqual(30, nova.count())
        self.assertEqual(2, self.antiga.count())
        self.assertNotIn("origem-0", nova.get()["ids"])
        reaberta, n = self.abrir()
        self.assertEqual(0, n)
        self.assertEqual(30, reaberta.count())

    def test_instalacao_nova_nao_carrega_pesos_sem_conversas(self):
        self.cliente.delete_collection(COLECAO_ANTIGA)
        with patch.object(self.embedder, "documentos", side_effect=AssertionError("carregou")):
            nova, n = self.abrir()
        self.assertEqual(0, n)
        self.assertEqual(0, nova.count())


class TestaPrefixos(unittest.TestCase):
    def test_um_modelo_atende_documentos_e_consultas(self):
        modelo = Mock()
        modelo.encode.side_effect = lambda textos, **kw: np.ones((len(textos), 768))
        e = embeddings.EmbeddingGemmaCPU()
        with patch.object(embeddings, "_carregar_modelo", return_value=modelo) as carga:
            e.documentos(["Lembrança"])
            e.consultas(["Pergunta"])
        carga.assert_called_once()
        self.assertEqual(["Document", "SearchQuery"],
                         [c.kwargs["prompt_name"] for c in modelo.encode.call_args_list])

    def test_vetor_invalido_nao_chega_ao_indice(self):
        e = embeddings.EmbeddingGemmaCPU()
        e._modelo = Mock()
        for retorno in (np.ones((1, 384)), np.full((1, 768), np.nan), np.zeros((1, 768))):
            e._modelo.encode.return_value = retorno
            with self.assertRaises(ValueError):
                e.documentos(["Fato"])

    def test_historico_filtra_distancia_e_usa_prefixo_consulta(self):
        colecao = Mock()
        colecao.count.return_value = 3
        colecao.query.return_value = {
            "documents": [["aceita", "rejeita", "inválida"]],
            "metadatas": [[None, {}, {}]],
            "distances": [[.25, .26, float("nan")]],
        }
        e = Mock()
        e.consultas.return_value = np.ones((1, 768))
        with patch.object(memoria, "_historico", return_value=colecao), \
             patch.object(memoria, "_emb_mem", return_value=e):
            texto = memoria.buscar_contexto_relevante("Uma pergunta")
        self.assertIn("aceita", texto)
        self.assertNotIn("rejeita", texto)
        self.assertNotIn("inválida", texto)
        e.consultas.assert_called_once_with(["Uma pergunta"])
        e.documentos.assert_not_called()
        self.assertIn("query_embeddings", colecao.query.call_args.kwargs)
        self.assertNotIn("query_texts", colecao.query.call_args.kwargs)


class TestaRecall(unittest.TestCase):
    def setUp(self):
        self.e = Mock()
        def vec(score):
            return np.array([score, np.sqrt(1 - score**2)], dtype=np.float32)
        self.e.documentos.side_effect = lambda textos: [vec(.9 if t == "ativa" else .8 if t == "fria forte" else .7) for t in textos]
        self.e.consultas.return_value = [[1, 0]]
        self.patches = [
            patch.object(memoria, "_emb_mem", return_value=self.e),
            patch.object(memoria, "_mem_emb_cache", {"assinatura": None, "fatos": [], "vecs": []}),
            patch("modulos.obsidian.listar_memoria_episodica", return_value=[("2026-10-01", "ativa")]),
            patch("modulos.obsidian.listar_memoria_arquivo", return_value=[
                ("2026-01-01", "fria forte"), ("2026-01-02", "fria fraca")]),
        ]
        for p in self.patches:
            p.start()
            self.addCleanup(p.stop)

    def test_so_esquenta_fria_selecionada_e_respeita_exclusao(self):
        with patch("modulos.obsidian.esquentar_memoria") as esquentar:
            resultado = memoria.buscar_memoria_relevante("Pergunta", excluir={"ativa"})
        self.assertEqual([("2026-01-01", "fria forte")], resultado)
        esquentar.assert_called_once_with("fria forte")

    def test_dedup_nao_esquenta_e_cache_e_invalidado_por_data_e_modelo(self):
        with patch("modulos.obsidian.esquentar_memoria") as esquentar:
            encontrados = memoria._memorias_semelhantes_para_dedup("Candidato")
        self.assertEqual(["ativa", "fria forte"], encontrados)
        esquentar.assert_not_called()
        memoria._memorias_semelhantes_para_dedup("Outro")
        self.assertEqual(1, self.e.documentos.call_count)
        with patch("modulos.obsidian.listar_memoria_episodica", return_value=[("2026-10-06", "ativa")]):
            memoria._memorias_semelhantes_para_dedup("Outro")
            self.assertEqual(2, self.e.documentos.call_count)
            with patch.object(embeddings, "IDENTIDADE_CACHE", ("nova-revisao",)):
                memoria._memorias_semelhantes_para_dedup("Outro")
            self.assertEqual(3, self.e.documentos.call_count)


if __name__ == "__main__":
    unittest.main()
