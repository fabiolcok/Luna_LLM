"""Contratos mínimos para futuros ajustes não apagarem as travas factuais da persona."""

from pathlib import Path
import unittest


class TestaGuardrailsPersona(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fonte = (Path(__file__).parents[1] / "modulos" / "pensar.py").read_text(encoding="utf-8")

    def test_zoeira_nao_inventa_a_premissa(self):
        self.assertIn("A zoeira pode exagerar o TOM, nunca inventar a PREMISSA", self.fonte)

    def test_momento_pequeno_pode_continuar_pequeno(self):
        self.assertIn("Nem todo momento pede profundidade", self.fonte)

    def test_memoria_precisa_ter_relacao_direta(self):
        self.assertIn("memória só quando tiver relação direta e inequívoca", self.fonte)

    def test_dado_nao_vira_intencao_inventada(self):
        self.assertIn("sem inventar causa, intenção", self.fonte)

    def test_referencia_vaga_nao_ganha_nome(self):
        self.assertIn("Se você mesma falou", self.fonte)
        self.assertIn("NUNCA preencha a lacuna", self.fonte)

    def test_momento_cotidiano_nao_ganha_historico(self):
        self.assertIn("MOMENTO COTIDIANO PEQUENO", self.fonte)
        self.assertIn("falta de autocontrole", self.fonte)

    def test_momento_cotidiano_nao_vira_atendente_neutra(self):
        self.assertIn("Uma alfinetada LEVE está liberada", self.fonte)
        self.assertIn("melhor que neutralidade de atendente", self.fonte)

    def test_cansaco_e_saude_tem_freios_diferentes(self):
        self.assertIn("Cansaço cotidiano pode receber uma mordida curta", self.fonte)
        self.assertIn("saúde, tristeza ou outro assunto realmente sensível", self.fonte)

    def test_correcao_admite_erro_sem_dobrar_aposta(self):
        self.assertIn("O usuário apontou um erro seu", self.fonte)
        self.assertIn("dobre a aposta no fato errado", self.fonte)

    def test_agradecimento_nao_vira_cobranca(self):
        self.assertIn("O usuário só agradeceu ou encerrou o assunto", self.fonte)
        self.assertIn("não puxe memória, trabalho ou tarefa nova", self.fonte)

    def test_elogio_foge_do_padrao_do_modelo(self):
        self.assertIn("ELOGIO também não pode ser carimbo", self.fonte)
        self.assertIn("parabéns pela dedicação", self.fonte)

    def test_humor_prioriza_contradicao_concreta_sem_muleta(self):
        self.assertIn("CONTRADIÇÃO CONCRETA é matéria-prima forte", self.fonte)
        self.assertIn("A piada precisa continuar clara", self.fonte)
        self.assertIn("não recorra automaticamente a Steam, backlog ou jogos", self.fonte)

    def test_deadpan_nao_e_meta_explicita(self):
        prompt = self.fonte.split("PROMPT_LUNA_PERSONA = (", 1)[1].split("_ROSTOS =", 1)[0]
        self.assertNotIn("deadpan", prompt.lower())

    def test_mudanca_de_ideia_nao_vira_defeito(self):
        self.assertIn("mudanca_ideia_explicita", self.fonte)
        self.assertIn("não como incoerência, falha, promessa quebrada ou procrastinação", self.fonte)

    def test_contradicao_declarada_fica_curta(self):
        self.assertIn("contradicao_declarada", self.fonte)
        self.assertIn("o centro de UMA frase curta e irônica", self.fonte)

    def test_prioridade_proativa_fica_no_fim_para_modelo_menor(self):
        self.assertIn("PRIORIDADE FINAL OBRIGATÓRIA", self.fonte)
        self.assertIn("não descreva passagem, sequência, salto", self.fonte)

    def test_proativo_nao_forca_ponte_sem_relacao(self):
        self.assertIn("Sem relação direta, não conecte os assuntos", self.fonte)
        self.assertNotIn("PONTE FINAL OBRIGATÓRIA", self.fonte)


if __name__ == "__main__":
    unittest.main()
