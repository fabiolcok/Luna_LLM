"""Protege comparação de modelo errado, stream incompleto e tool call inválido."""
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from testes.bancada_modelos import (
    amostragem_efetiva, avaliar, codigo_sem_boot, conferir_identidade, consumir_stream,
    digest, gravar_json, ler_suite, relatorio,
)


def sse(evento):
    return ("data: " + json.dumps(evento) + "\n").encode()


class TestaBancadaModelos(unittest.TestCase):
    def test_comparacao_considera_ajuste_por_chamada_sem_alterar_default(self):
        bonsai = {"modelo": {"amostragem_padrao": {"top_k": 20, "min_p": 0.05}}}
        gemma = {"modelo": {"amostragem_padrao": {"top_k": 64, "min_p": 0.05}},
                 "parametros_execucao": {"top_k": 20}}
        self.assertEqual(amostragem_efetiva(bonsai), amostragem_efetiva(gemma))
        self.assertEqual(gemma["modelo"]["amostragem_padrao"]["top_k"], 64)
        gemma["parametros_execucao"] = {}
        self.assertNotEqual(amostragem_efetiva(bonsai), amostragem_efetiva(gemma))

    def test_preparacao_nao_dispara_boot_mas_preserva_funcoes(self):
        fonte = ('def garantir_modelo_turbollm():\n    raise AssertionError("boot")\n'
                 'garantir_modelo_turbollm()\n'
                 'def prompt():\n    return "texto real"\n')
        escopo = {}
        exec(codigo_sem_boot(fonte, "teste.py"), escopo)
        self.assertEqual(escopo["prompt"](), "texto real")
        with self.assertRaisesRegex(AssertionError, "boot"):
            escopo["garantir_modelo_turbollm"]()

    def test_stream_reune_argumentos_e_separa_primeira_saida_do_thinking(self):
        linhas = [
            sse({"choices": [{"delta": {"reasoning_content": "pensando"}}]}),
            sse({"choices": [{"delta": {"tool_calls": [{"index": 0, "function": {
                "name": "tocar", "arguments": '{"mus'}}]}}]}),
            sse({"choices": [{"delta": {"tool_calls": [{"index": 0, "function": {
                "arguments": 'ica":"x"}'}}]}, "finish_reason": "tool_calls"}]}),
            sse({"choices": [], "usage": {"completion_tokens": 9}}),
            b"data: [DONE]\n",
        ]
        tempos = iter([13, 17])
        r = consumir_stream(linhas, 10, lambda: next(tempos))
        self.assertEqual(r["ferramentas"], [{"name": "tocar", "arguments": '{"musica":"x"}'}])
        self.assertEqual((r["ttft_s"], r["total_s"]), (3, 7))
        self.assertEqual(r["pensamento_chars"], 8)
        self.assertEqual(r["uso"]["completion_tokens"], 9)

    def test_stream_cortado_nao_vira_resposta_valida(self):
        with self.assertRaisesRegex(RuntimeError, "incompleto"):
            consumir_stream([sse({"choices": [{"delta": {"content": "começou"}}]})], 0)

    def test_erro_no_stream_nao_vira_silencio(self):
        with self.assertRaisesRegex(RuntimeError, "context full"):
            consumir_stream([sse({"error": "context full"})], 0)

    def test_troca_de_gguf_mesmo_com_nome_igual_interrompe(self):
        a = {"modelo_key": "hf", "arquivo": "PQ2_0.gguf"}
        b = {"modelo_key": "hf", "arquivo": "PTQ1_0.gguf"}
        with self.assertRaisesRegex(RuntimeError, "mudou"):
            conferir_identidade(b, a)

    def test_snapshot_editado_nao_compara_silenciosamente(self):
        with TemporaryDirectory() as pasta:
            path = Path(pasta) / "suite.json"
            suite = {"casos": [{"texto": "original"}]}
            suite["sha256"] = digest(suite)
            gravar_json(path, suite)
            self.assertEqual(ler_suite(path), suite)
            suite["casos"][0]["texto"] = "alterado"
            gravar_json(path, suite)
            with self.assertRaisesRegex(ValueError, "alterado"):
                ler_suite(path)

    def test_mesmo_nome_de_tool_com_argumentos_invalidos_falha(self):
        caso = {"ramo": "ROTEADOR", "cenario": {"ferramentas": ["tocar"]}}
        suite = {"schemas": {"tocar": {"type": "object", "required": ["musica"],
                                       "properties": {"musica": {"type": "string"}}}}}
        r = {"texto": "", "finish_reason": "tool_calls", "pensamento_chars": 0,
             "ferramentas": [{"name": "tocar", "arguments": "{}"}]}
        self.assertTrue(any("schema:" in f for f in avaliar(caso, r, suite)))
        r["ferramentas"][0]["arguments"] = '{"musica": "x"}'
        self.assertEqual(avaliar(caso, r, suite), [])

    def test_sem_tool_mas_conversando_falha_contrato_do_roteador(self):
        caso = {"ramo": "ROTEADOR", "cenario": {"ferramentas": []}}
        r = {"texto": "Já vou tocar", "finish_reason": "stop", "pensamento_chars": 0,
             "ferramentas": []}
        self.assertTrue(avaliar(caso, r, {}))
        r["texto"] = "SEM_FERRAMENTA"
        self.assertEqual(avaliar(caso, r, {}), [])

    def test_nao_compara_entradas_ou_seeds_diferentes(self):
        base = {"suite_sha256": "a", "repeticoes": 2, "seed_base": 1931}
        for campo, novo in [("suite_sha256", "b"), ("repeticoes", 1), ("seed_base", 7)]:
            with self.subTest(campo=campo), self.assertRaises(ValueError):
                relatorio([base, {**base, campo: novo}], Path("nao_deve_ser_criado.md"))


if __name__ == "__main__":
    unittest.main()
