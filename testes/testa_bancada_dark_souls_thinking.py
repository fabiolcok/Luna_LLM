"""Garante comparação do thinking sem misturar histórico nem perder opções da produção."""
import unittest

from testes.bancada_dark_souls_thinking import gerar_turno, preparar_runtime


class TestaBancadaThinking(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pensar = preparar_runtime()

    def turno(self, modo, recentes, texto):
        return gerar_turno(self.pensar,
            {"tipo": "morte", "nome": "", "mortes_sessao": 2, "incremento": 1},
            recentes, modo, 43, 1790290800,
            lambda pedido: {"texto": texto, "total_s": 31, "finish_reason": "stop"})

    def test_entradas_iguais_diferem_so_no_thinking_e_orcamento(self):
        a = self.turno("desligado", [], "Frase A. [clima:zoeira]")
        b = self.turno("ligado", [], "Frase B. [clima:zoeira]")
        self.assertEqual(a["ramo"], "ENXUTO_DARK_SOULS + EMOCAO")
        for chave in ("messages", "temperature", "presence_penalty", "frequency_penalty", "seed"):
            self.assertEqual(a["pedido"][chave], b["pedido"][chave])
        self.assertEqual((a["pedido"]["max_tokens"], b["pedido"]["max_tokens"]), (180, 3000))
        self.assertIs(a["pedido"]["chat_template_kwargs"]["enable_thinking"], False)
        self.assertIs(b["pedido"]["chat_template_kwargs"]["enable_thinking"], True)
        self.assertTrue(a["excede_ttl_antes_do_tts"])
        self.assertEqual(a["fala"], "Frase A.")

    def test_antirrepeticao_recebe_so_falas_da_propria_sequencia_sem_tags(self):
        recentes_a, recentes_b = [], []
        self.turno("desligado", recentes_a, "Memória do braço A. [clima:zoeira]")
        self.turno("ligado", recentes_b, "Memória do braço B. [clima:zoeira]")
        a = self.turno("desligado", recentes_a, "Mais uma A. [clima:zoeira]")
        b = self.turno("ligado", recentes_b, "Mais uma B. [clima:zoeira]")
        texto_a = str(a["pedido"]["messages"])
        texto_b = str(b["pedido"]["messages"])
        self.assertIn("Memória do braço A.", texto_a)
        self.assertNotIn("Memória do braço B.", texto_a)
        self.assertIn("Memória do braço B.", texto_b)
        self.assertNotIn("Memória do braço A.", texto_b)
        self.assertNotIn("[clima:", recentes_a[0])

    def test_retentativa_preserva_pedidos_e_soma_tempo(self):
        from testes.testa_repeticao_dark_souls import FALAS, NOVA
        resultados = iter([FALAS[1], NOVA])
        r = gerar_turno(self.pensar,
            {"tipo": "morte", "nome": "", "mortes_sessao": 2}, [FALAS[0][:120]],
            "desligado", 43, 1790290800,
            lambda pedido: {"texto": next(resultados) + " [clima:zoeira]", "total_s": 17},
            mortes_recentes=[FALAS[0]])
        self.assertEqual(len(r["tentativas"]), 2)
        self.assertEqual(r["total_s"], 34)
        self.assertTrue(r["excede_ttl_antes_do_tts"])
        self.assertEqual(r["fala"], NOVA)
        self.assertEqual([t["pedido"]["seed"] for t in r["tentativas"]], [43, 1043])
        self.assertNotEqual(r["tentativas"][0]["pedido"]["messages"],
                            r["tentativas"][1]["pedido"]["messages"])

    def test_contagem_interna_nao_altera_prompt_completo_do_proativo(self):
        # Compara a chamada final: testar só o briefing deixaria vazar o total por MOMENTO.
        for tipo, nome in (("morte", ""), ("chefe", "Taurus Demon"), ("fogueira", "Firelink Shrine")):
            with self.subTest(tipo=tipo):
                mensagens = []
                for total, incremento in ((1, 1), (9876, 4321)):
                    evento = {"tipo": tipo, "nome": nome, "mortes_sessao": total,
                              "incremento": incremento}
                    r = gerar_turno(self.pensar, evento, [], "desligado", 43, 1790290800,
                        lambda pedido: {"texto": "Reação ao acontecimento. [clima:zoeira]"})
                    self.assertEqual(r["ramo"], "ENXUTO_DARK_SOULS + EMOCAO")
                    mensagens.append(r["pedido"]["messages"])
                self.assertEqual(*mensagens)
                texto = str(mensagens[0])
                for proibido in ("mortes_sessao", "incremento", "mortes acompanhadas", "contador"):
                    self.assertNotIn(proibido, texto)
                self.assertIn('"tipo": "' + tipo + '"', texto)
                if nome:
                    self.assertIn(nome, texto)
                else:
                    self.assertIn("personagem morreu", texto)


    def test_outros_proativos_nao_herdam_prompt_por_mencionar_o_jogo(self):
        from modulos import prompts
        for tarefa in ("", "noticias", "steam_abriu_DARK SOULS REMASTERED", "dark_souls_outro"):
            with self.subTest(tarefa=tarefa):
                r = gerar_turno(self.pensar,
                    {"tipo": "morte", "nome": "", "mortes_sessao": 1}, [], "desligado",
                    43, 1790290800, lambda pedido: {"texto": "Teste. [clima:zoeira]"},
                    tarefa=tarefa)
                self.assertEqual(r["ramo"], "ENXUTO_PROATIVO + EMOCAO")
                self.assertIn(prompts.ENXUTO_PROATIVO, r["pedido"]["messages"][0]["content"])
                self.assertNotIn(prompts.ENXUTO_DARK_SOULS, r["pedido"]["messages"][0]["content"])

    def test_desvio_proativo_encaminha_origem_para_persona(self):
        from unittest.mock import patch
        with (patch.object(self.pensar, "_capturar_momento", return_value={}),
              patch.object(self.pensar, "_reescrever_como_luna", return_value="Teste.") as persona):
            self.pensar.gerar_resposta("Evento", [], analisar=False, salvar=False,
                                      tarefa_proativa="dark_souls_chefe")
        self.assertEqual(persona.call_args.kwargs["tarefa_proativa"], "dark_souls_chefe")
        self.assertEqual(persona.call_args.args[1], "")

    def test_turno_reativo_nao_usa_variante_mesmo_com_origem_informada(self):
        from unittest.mock import patch
        from modulos import prompts
        original = self.pensar._reescrever_como_luna
        def reativo(tecnica, usuario, historico, **kw):
            return original(tecnica, "Quero conversar sobre Dark Souls.", historico, **kw)
        with patch.object(self.pensar, "_reescrever_como_luna", side_effect=reativo):
            r = self.turno("desligado", [], "Teste. [clima:zoeira]")
        self.assertEqual(r["ramo"], "PROMPT_COMPLETO + EMOCAO")
        self.assertNotIn(prompts.ENXUTO_DARK_SOULS, r["pedido"]["messages"][0]["content"])


if __name__ == "__main__":
    unittest.main()
