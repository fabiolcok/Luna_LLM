"""Testa o cold-start sem iniciar o TurboLLM nem carregar modelo real."""

import unittest

from modulos.turbollm_api import (
    erro_modelo_descarregado,
    listar_biblioteca,
    opcoes_pensamento,
    recarregar_modelo,
    selecionar_chave_modelo,
)


class _Resposta:
    def __init__(self, dados, status=200):
        self._dados = dados
        self.status_code = status

    def json(self):
        return self._dados

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


class _HttpFalso:
    def __init__(self, modelo_inicial=""):
        self.consultas_status = 0
        self.modelo_pedido = None
        self.modelo_inicial = modelo_inicial

    def get(self, url, timeout):
        if url.endswith("/api/v1/models"):
            return _Resposta({"models": [
                {"key": "gemma-local-q4", "name": "Gemma 4 12B IT QAT"},
                {"key": "outro-modelo", "name": "Outro"},
            ]})
        self.consultas_status += 1
        if self.consultas_status == 1:
            if self.modelo_inicial:
                return _Resposta({
                    "engine": {"state": "running"},
                    "model": {"key": self.modelo_inicial},
                    "lastLoaded": {"modelKey": self.modelo_inicial},
                })
            return _Resposta({
                "engine": {"state": "stopped"},
                "lastLoaded": {"modelKey": "gemma-local-q4"},
            })
        if self.consultas_status == 2:
            return _Resposta({"engine": {"state": "starting"}})
        return _Resposta({
            "engine": {"state": "running"},
            "model": {"key": "gemma-local-q4"},
        })

    def post(self, url, json, timeout):
        self.modelo_pedido = json["modelKey"]
        return _Resposta({"ok": True})


class Erro503(Exception):
    status_code = 503


class TestaRecuperacaoTurboLLM(unittest.TestCase):
    def test_lista_biblioteca_sem_expor_caminho_local(self):
        http = _HttpFalso(modelo_inicial="gemma-local-q4")
        estado = listar_biblioteca("http://127.0.0.1:6996/v1", cliente_http=http)
        self.assertTrue(estado["ok"])
        self.assertEqual("gemma-local-q4", estado["ativo"])
        self.assertEqual(
            [{"key": "gemma-local-q4", "name": "Gemma 4 12B IT QAT"},
             {"key": "outro-modelo", "name": "Outro"}],
            estado["modelos"],
        )
        self.assertNotIn("path", estado["modelos"][0])

    def test_modos_de_pensamento(self):
        self.assertEqual(("automatico", {}), opcoes_pensamento("automático"))
        self.assertEqual(True, opcoes_pensamento("ligado")[1]
                         ["chat_template_kwargs"]["enable_thinking"])
        self.assertEqual(False, opcoes_pensamento("desligado")[1]
                         ["chat_template_kwargs"]["enable_thinking"])

    def test_reconhece_somente_503_de_modelo_descarregado(self):
        self.assertTrue(erro_modelo_descarregado(
            Erro503("No model loaded. Load one in TurboLLM.")))
        self.assertTrue(erro_modelo_descarregado(
            Erro503("No model matching 'G:/Modelos/qwen.gguf' found.")))
        self.assertFalse(erro_modelo_descarregado(
            Erro503("ComfyUI is rendering — model swap paused.")))
        self.assertFalse(erro_modelo_descarregado(RuntimeError("No model loaded")))

    def test_env_tem_precedencia_sobre_ultimo_modelo(self):
        modelos = [
            {"key": "antigo", "name": "Modelo antigo"},
            {"key": "novo", "name": "Modelo escolhido"},
        ]
        self.assertEqual("novo", selecionar_chave_modelo(
            modelos, configurado="Modelo escolhido", ultimo="antigo"))

    def test_padrao_tem_precedencia_ao_desfazer_teste(self):
        modelos = [
            {"key": "gemma", "name": "Gemma 4 12B IT QAT"},
            {"key": "qwen", "name": "Qwen de teste"},
        ]
        self.assertEqual("gemma", selecionar_chave_modelo(
            modelos, ultimo="qwen", preferido="gemma 4 12b it qat"))

    def test_escolha_explicita_troca_modelo_que_ja_estava_rodando(self):
        http = _HttpFalso(modelo_inicial="outro-modelo")
        resultado = recarregar_modelo(
            "http://127.0.0.1:6996/v1",
            configurado="Gemma 4 12B IT QAT",
            cliente_http=http,
            dormir=lambda _: None,
        )
        self.assertTrue(resultado["ok"])
        self.assertEqual("gemma-local-q4", http.modelo_pedido)

    def test_volta_ao_padrao_mesmo_com_modelo_de_teste_rodando(self):
        http = _HttpFalso(modelo_inicial="outro-modelo")
        resultado = recarregar_modelo(
            "http://127.0.0.1:6996/v1",
            preferido="Gemma 4 12B IT QAT",
            aceitar_atual=False,
            cliente_http=http,
            dormir=lambda _: None,
        )
        self.assertTrue(resultado["ok"])
        self.assertEqual("gemma-local-q4", http.modelo_pedido)

    def test_carrega_ultimo_modelo_e_espera_ficar_pronto(self):
        http = _HttpFalso()
        resultado = recarregar_modelo(
            "http://127.0.0.1:6996/v1",
            preferido="gemma 4 12b it qat",
            cliente_http=http,
            dormir=lambda _: None,
        )
        self.assertTrue(resultado["ok"])
        self.assertEqual("gemma-local-q4", resultado["modelo"])
        self.assertEqual("gemma-local-q4", http.modelo_pedido)
        self.assertEqual(3, http.consultas_status)


if __name__ == "__main__":
    unittest.main()
