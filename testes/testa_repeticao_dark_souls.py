"""Regressoes da copia de comentarios de morte, sem rede, audio ou boot da Luna."""
import ast
from pathlib import Path
import re
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from modulos.antirrepeticao import repete_fala
from modulos.execucoes import Coordenador

BASE = ("Essa morte foi tão eficiente que parece que o personagem decidiu que a vida era "
        "opcional e resolveu apenas se retirar do plano físico ")
FALAS = [BASE + "por pura conveniência.",
         BASE + "com uma elegância quase profissional. Você está jogando ou apenas treinando "
                "a arte da desistência instantânea?",
         BASE + "com a elegância de um tijolo caindo de um prédio."]
NOVA = "Lordran devia pagar insalubridade pra você. Esse expediente tá um absurdo."


class TestaDeteccao(unittest.TestCase):
    def test_tres_exemplos_reais_com_finais_distintos(self):
        self.assertTrue(repete_fala(FALAS[1], [FALAS[0]]))
        self.assertTrue(repete_fala(FALAS[2], FALAS[:2]))
        self.assertTrue(repete_fala("Olha só! " + FALAS[2], [FALAS[0]]))

    def test_caixa_acentos_pontuacao_e_tag_nao_disfarcem_copia(self):
        self.assertTrue(repete_fala("VOCE, MORREU?! [clima:zoeira]", ["Você morreu."]))

    def test_quase_toda_frase_igual_com_pequenas_trocas(self):
        a = "O personagem pediu demissão da existência e foi procurar uma carreira melhor."
        b = "Seu personagem pediu demissão da existência e vai procurar uma carreira melhor."
        self.assertTrue(repete_fala(b, [a]))

    def test_repetir_so_primeira_frase_com_uma_troca_tambem_e_copia(self):
        anterior = ("A vida útil desse personagem acaba de ser reduzida a um frame de animação "
                    "irrelevante. É uma desintegração tão coordenada que parece que ele se "
                    "voluntariou para virar adubo do cenário.")
        atual = "A vida útil desse personagem acabou de ser reduzida a um frame de animação irrelevante."
        self.assertTrue(repete_fala(atual, [anterior]))

    def test_reacoes_diferentes_preservam_exagero_e_palavras_comuns(self):
        self.assertFalse(repete_fala(NOVA, FALAS))
        self.assertFalse(repete_fala("Essa morte foi um protesto contra a indústria do entretenimento.",
                                    ["Essa morte foi uma demissão com aviso prévio."]))
        self.assertFalse(repete_fala("", FALAS))
        self.assertFalse(repete_fala(NOVA, ["", "[clima:zoeira]"]))


class TestaGeracao(unittest.TestCase):
    def setUp(self):
        arvore = ast.parse(Path("modulos/proativa.py").read_text(encoding="utf-8"))
        nomes = {"_gerar_fala_proativa", "_FalaProativa"}
        nos = [n for n in arvore.body if isinstance(n, (ast.FunctionDef, ast.ClassDef))
               and n.name in nomes]
        prompts = ast.parse(Path("modulos/prompts.py").read_text(encoding="utf-8"))
        constante = next(n for n in prompts.body if isinstance(n, ast.Assign)
                        and any(isinstance(t, ast.Name) and t.id == "RETENTATIVA_MORTE_REPETIDA"
                                for t in n.targets))
        self.c = Coordenador(pausa=0)
        self.e = dict(re=re, _execucoes=self.c, _historico_proativo=[], _historico_principal=[],
                      _falas_recentes=[FALAS[0][:120]], _falas_morte_recentes=[FALAS[0]],
                      _contexto_recente_para_proativo=lambda s: "",
                      _prompts=SimpleNamespace(RETENTATIVA_MORTE_REPETIDA=ast.literal_eval(constante.value)),
                      _limpar_visual_proativo=Mock(), gerar_resposta=Mock(),
                      obter_clima_resposta=lambda: "zoeira",
                      cor=SimpleNamespace(amarelo=Mock(), vermelho=Mock()))
        exec(compile(ast.Module(body=nos, type_ignores=[]), "modulos/proativa.py", "exec"), self.e)
        self.servidor = patch.dict("sys.modules", {"servidor": SimpleNamespace(atualizar_status=Mock())})
        self.servidor.start()
        self.addCleanup(self.servidor.stop)

    def gerar(self, tarefa="dark_souls_morte", **kw):
        return self.e["_gerar_fala_proativa"]("Evento confirmado.", tarefa=tarefa,
                   variar=False, respeitar_intervalo=False, **kw)

    def test_copia_tenta_de_novo_sem_citar_texto_e_so_guarda_aceita(self):
        mock = self.e["gerar_resposta"]
        mock.side_effect = [FALAS[1], NOVA]
        self.assertEqual(self.gerar(), NOVA)
        self.assertEqual(mock.call_count, 2)
        self.assertIn(FALAS[0][:120], mock.call_args_list[0].args[0])
        self.assertNotIn(FALAS[0][:120], mock.call_args_list[1].args[0])
        self.assertNotIn(FALAS[1], mock.call_args_list[1].args[0])
        self.assertIn("mude a abertura e a ideia central", mock.call_args_list[1].args[0])
        self.assertEqual(self.e["_falas_morte_recentes"], [FALAS[0], NOVA])
        self.assertEqual(len(self.e["_falas_recentes"]), 2)

    def test_segunda_copia_descartada_sem_loop_nem_poluir_memoria(self):
        self.e["gerar_resposta"].side_effect = [FALAS[1], FALAS[2]]
        self.assertIsNone(self.gerar())
        self.assertEqual(self.e["gerar_resposta"].call_count, 2)
        self.assertEqual(self.e["_falas_morte_recentes"], [FALAS[0]])
        self.e["_limpar_visual_proativo"].assert_called_once()

    def test_memoria_de_morte_independe_das_ultimas_falas_do_radar(self):
        self.e["_falas_recentes"] = ["Notícia diferente."] * 5
        self.e["gerar_resposta"].side_effect = [FALAS[2], NOVA]
        self.assertEqual(self.gerar(), NOVA)
        self.assertEqual(self.e["gerar_resposta"].call_count, 2)

    def test_outros_proativos_nao_herdam_filtro(self):
        for tarefa in ("radar_rss", "steam_abriu_DARK SOULS", "dark_souls_chefe", "dark_souls_fogueira"):
            with self.subTest(tarefa=tarefa):
                self.e["gerar_resposta"].reset_mock()
                self.e["gerar_resposta"].return_value = FALAS[1]
                self.assertEqual(self.gerar(tarefa), FALAS[1])
                self.e["gerar_resposta"].assert_called_once()
                self.assertEqual(self.e["_falas_morte_recentes"], [FALAS[0]])

    def test_evento_expirado_nao_inicia_segunda_geracao(self):
        self.e["gerar_resposta"].return_value = FALAS[1]
        self.assertIsNone(self.gerar(ainda_valido=Mock(side_effect=[True, False])))
        self.e["gerar_resposta"].assert_called_once()

    def test_usuario_interrompe_antes_da_retentativa(self):
        def cancelar(*a, **kw):
            self.c.avisar_usuario()
            return FALAS[1]
        self.e["gerar_resposta"].side_effect = cancelar
        with self.c.executar(proativa=True):
            self.assertIsNone(self.gerar())
        self.e["gerar_resposta"].assert_called_once()
        self.assertEqual(self.e["_falas_morte_recentes"], [FALAS[0]])

    def test_guarda_falas_inteiras_com_limite_e_sem_chamada_extra(self):
        antigas = ["Assunto anterior " + str(i) for i in range(5)]
        self.e["_falas_morte_recentes"] = antigas.copy()
        self.e["gerar_resposta"].return_value = FALAS[0]
        self.assertEqual(self.gerar(), FALAS[0])
        self.assertEqual(self.e["_falas_morte_recentes"], antigas[1:] + [FALAS[0]])
        self.e["gerar_resposta"].assert_called_once()


if __name__ == "__main__":
    unittest.main()
