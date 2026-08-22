"""Contratos mínimos: futuros ajustes podem REESCREVER as travas da persona, nunca APAGÁ-LAS.

Antes cada teste comparava uma frase inteira do `pensar.py` com `assertIn`. Isso confundia as
duas coisas: reformular uma regra quebrava o teste do mesmo jeito que deletá-la. Aconteceu duas
vezes num único dia — fundir dois bullets e trocar "alfinetada LEVE" por "AFIADA" derrubaram
testes sem que nenhuma regra tivesse sumido.

Agora cada trava é descrita por GRUPOS DE SINÔNIMOS: pelo menos um termo de cada grupo precisa
existir em algum lugar do arquivo. Reescrever a frase mantendo o conceito continua passando;
apagar o conceito derruba. É o mesmo raciocínio do `exige_grupos` da bancada.

Ao acrescentar uma formulação nova a um grupo, confira que ela é ESPECÍFICA: um termo solto
como "memória" ou "elogio" casa em vinte lugares do arquivo e faz o teste passar por acidente.
`grep -n -i "termo" modulos/pensar.py` — se voltar meia dúzia de linhas, o termo é fraco demais.

Duas coisas ficam como comparação exata de propósito:
  - identificadores de CÓDIGO (nome de flag, nome de ferramenta) — renomear DEVE quebrar;
  - asserções de AUSÊNCIA (`assertNotIn`), que já são imunes a reescrita.
"""

from pathlib import Path
import unittest


class TestaGuardrailsPersona(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fonte = (Path(__file__).parents[1] / "modulos" / "pensar.py").read_text(encoding="utf-8")
        cls.minuscula = cls.fonte.lower()

    def exige(self, trava, *grupos):
        """Cada grupo é uma lista de formas de dizer a mesma coisa; UMA de cada precisa existir."""
        for grupo in grupos:
            if not any(termo.lower() in self.minuscula for termo in grupo):
                self.fail(
                    "A trava '{0}' sumiu do prompt.\n"
                    "   Nenhuma destas formas foi encontrada: {1}\n"
                    "   Se voce REESCREVEU a regra, acrescente a formulacao nova a lista.\n"
                    "   Se voce REMOVEU a regra de proposito, apague este teste e diga no commit."
                    .format(trava, " | ".join(grupo))
                )

    # ── grounding: o humor não pode fabricar fato ────────────────────────────────────────
    def test_zoeira_nao_inventa_a_premissa(self):
        self.exige("zoeira exagera o tom, nunca inventa a premissa",
                   ["colorem a premissa", "nunca a substituem", "não substituem a premissa"],
                   ["base factual", "a base tem que continuar", "os fatos continuam iguais"])

    def test_dado_nao_vira_intencao_inventada(self):
        self.exige("dado nao vira causa/intencao inventada",
                   ["inventar causa", "invente causa", "inventando causa"],
                   ["previsão técnica", "previsao tecnica", "vai derreter"])

    def test_memoria_precisa_ter_relacao_direta(self):
        self.exige("memoria so entra com relacao direta",
                   ["puxe uma memória sem relação", "puxe uma memoria sem relacao",
                    "memória sem relação direta"],
                   ["só para personalizar", "so para personalizar", "só pra personalizar"])

    def test_referencia_vaga_nao_ganha_nome(self):
        self.exige("referencia que ela deixou vaga nao ganha nome inventado",
                   ["referência pedida", "você mesma falou", "voce mesma falou"],
                   ["lacuna", "palpite"])

    # ── proporção: nem todo momento pede profundidade ────────────────────────────────────
    def test_momento_pequeno_pode_continuar_pequeno(self):
        self.exige("momento pequeno pode receber resposta pequena",
                   ["nem todo momento pede profundidade", "momento cotidiano pequeno",
                    "fala cotidiana pequena"])

    def test_momento_cotidiano_nao_ganha_historico(self):
        self.exige("cotidiano nao ganha historico inventado",
                   ["momento cotidiano pequeno", "recado cotidiano"],
                   ["autocontrole", "presuma que é repetição", "invente rotina"])

    def test_momento_cotidiano_nao_vira_atendente_neutra(self):
        self.exige("cotidiano tem mordida, nao neutralidade de atendente",
                   ["neutralidade de atendente", "sem virar atendente"])

    # ── limites do humor ─────────────────────────────────────────────────────────────────
    def test_cansaco_e_saude_tem_freios_diferentes(self):
        self.exige("cansaco aceita mordida leve; saude e tristeza, nenhuma",
                   ["cansaço cotidiano", "cansaco cotidiano"],
                   ["mordida curta", "mordida carinhosa"],
                   ["saúde, tristeza", "saude, tristeza"],
                   ["nada de cutucada", "sem alfinetada"])

    def test_elogio_foge_do_padrao_do_modelo(self):
        self.exige("elogio nao pode ser carimbo",
                   ["carimbo", "eco vazio"],
                   ["parabéns pela dedicação", "parabens pela dedicacao"])

    def test_humor_prioriza_contradicao_concreta_sem_muleta(self):
        self.exige("contradicao concreta rende humor, sem cair no backlog",
                   ["contradição concreta", "contradicao concreta"],
                   ["steam, backlog", "backlog ou jogos"])

    def test_deadpan_nao_e_meta_explicita(self):
        # AUSÊNCIA: imune a reescrita por natureza, fica como estava.
        prompt = self.fonte.split("PROMPT_LUNA_PERSONA = (", 1)[1].split("_ROSTOS =", 1)[0]
        self.assertNotIn("deadpan", prompt.lower())

    # ── situações que trocam o prompt ────────────────────────────────────────────────────
    def test_correcao_admite_erro_sem_dobrar_aposta(self):
        self.exige("ao ser corrigida, admite sem dobrar a aposta",
                   ["apontou um erro"],
                   ["dobre a aposta", "dobrar a aposta"])

    def test_agradecimento_nao_vira_cobranca(self):
        self.exige("agradecimento encerra sem cobranca",
                   ["só agradeceu", "so agradeceu", "encerrou o assunto"],
                   ["puxe memória", "puxe memoria", "cobre produtividade"])

    def test_mudanca_de_ideia_nao_vira_defeito(self):
        self.assertIn("mudanca_ideia_explicita", self.fonte)   # CÓDIGO: renomear deve quebrar
        self.exige("mudar de ideia e escolha, nao defeito",
                   ["escolha atual como escolha"],
                   ["incoerência", "incoerencia", "promessa quebrada", "procrastinação"])

    def test_contradicao_declarada_fica_curta(self):
        self.assertIn("contradicao_declarada", self.fonte)     # CÓDIGO
        self.exige("contradicao contada por ele vira UMA frase ironica",
                   ["centro de uma frase curta", "uma frase curta e"],
                   ["reutilizando os detalhes", "a escala que ele informou"])

    # ── proativo ─────────────────────────────────────────────────────────────────────────
    def test_prioridade_proativa_fica_no_fim_para_modelo_menor(self):
        self.exige("a prioridade do contraste fica no FIM da instrucao",
                   ["prioridade final obrigatória", "prioridade final obrigatoria"],
                   ["descreva passagem"])

    def test_proativo_nao_forca_ponte_sem_relacao(self):
        self.exige("proativo nao conecta assuntos sem relacao",
                   ["sem relação direta", "sem relacao direta"],
                   ["não conecte", "nao conecte"])
        # AUSÊNCIA: a instrução OBRIGATÓRIA de ponte foi removida de propósito e não pode voltar
        self.assertNotIn("PONTE FINAL OBRIGATÓRIA", self.fonte)

    # ── integração com ferramenta ────────────────────────────────────────────────────────
    def test_registro_de_jogo_nao_deixa_persona_inventar_erro(self):
        # nome da ferramenta é CÓDIGO: comparação exata de propósito
        self.assertIn('nome_funcao == "registrar_rotina_jogo"', self.fonte)
        self.exige("registro de jogo chega a persona como JA CONCLUIDO",
                   ["já foi concluído com sucesso", "ja foi concluido com sucesso"],
                   ["registrei isso na rotina"])


if __name__ == "__main__":
    unittest.main()
