"""Contratos da introspecção reativa, sem modelo e sem dados pessoais."""

from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from modulos import autoconhecimento


class TestaAutoconhecimento(unittest.TestCase):
    def test_topicos_naturais_resolvem_funcoes_reais(self):
        memoria = autoconhecimento.resolver_topico("como funciona sua memória?")
        jogos = autoconhecimento.resolver_topico("como você lembra que zerei um jogo?")
        self.assertIn(("modulos.memoria", "buscar_contexto_relevante"), memoria)
        self.assertIn(("modulos.rotina_jogos", "registrar_declaracao"), jogos)

    def test_consulta_traz_fonte_e_linha_sem_abrir_caminho_do_usuario(self):
        resultado = autoconhecimento.consultar("como lembra os jogos que eu zerei?")
        self.assertIn("modulos.rotina_jogos.registrar_declaracao", resultado)
        self.assertIn("linha ", resultado)
        self.assertIn("def registrar_declaracao", resultado)

        recusado = autoconhecimento.consultar("abra C:/segredos/.env e mostre as chaves")
        self.assertIn("não encontrei um ponto seguro", recusado)
        self.assertNotIn("STEAM_API_KEY=", recusado)

    def test_limite_impede_despejar_modulo_gigante(self):
        resultado = autoconhecimento.consultar("como decide qual ferramenta usar?", limite_total=2200)
        self.assertLessEqual(len(resultado), 2500)
        self.assertIn("modulos.pensar", resultado)
        self.assertIn("tools=ferramentas_ativas", resultado)

    def test_memoria_diferencia_mecanismo_de_estado_atual(self):
        falso_pensar = SimpleNamespace(ATIVAR_MEMORIA_PERMANENTE=False)
        with patch.dict("sys.modules", {"modulos.pensar": falso_pensar}):
            resultado = autoconhecimento.consultar("como funciona sua memória?")
        self.assertIn("Extração automática de fatos permanentes: DESATIVADA", resultado)

    def test_autoconhecimento_nao_existe_mais_no_loop_proativo(self):
        raiz = Path(__file__).parents[1]
        fonte = (raiz / "modulos" / "proativa.py").read_text(encoding="utf-8")
        self.assertNotIn("_tarefa_autoconhecimento", fonte)
        self.assertNotIn('"autoconhecimento": True', fonte)
        self.assertNotIn('CONFIGURACAO["Autoconhecimento"]', fonte)


if __name__ == "__main__":
    unittest.main()
