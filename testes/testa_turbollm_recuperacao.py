"""Testa o cold-start sem iniciar o TurboLLM nem carregar modelo real."""

import unittest

from modulos.turbollm_api import (
    erro_modelo_descarregado,
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
    def __init__(self):
        self.consultas_status = 0
        self.modelo_pedido = None

    def get(self, url, timeout):
        if url.endswith("/api/v1/models"):
            return _Resposta({"models": [
                {"key": "gemma-local-q4", "name": "Gemma 4 12B IT QAT"},
                {"key": "outro-modelo", "name": "Outro"},
            ]})
        self.consultas_status += 1
        if self.consultas_status == 1:
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
    def test_reconhece_somente_503_de_modelo_descarregado(self):
        self.assertTrue(erro_modelo_descarregado(
            Erro503("No model loaded. Load one in TurboLLM.")))
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
