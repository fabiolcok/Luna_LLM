import json
import logging
import unittest
from unittest.mock import patch

from modulos import atividade


class TestaAtividade(unittest.TestCase):
    def setUp(self):
        self._linhas = atividade._linhas.copy()
        self._ouvintes = list(atividade._ouvintes)
        atividade._linhas.clear()

    def tearDown(self):
        atividade._linhas.clear()
        atividade._linhas.extend(self._linhas)
        atividade._ouvintes[:] = self._ouvintes

    def test_categorias_das_linhas_reais_do_cmd(self):
        casos = {
            "[⚠️ Horas divergentes dos dados Steam — fala descartada]": "erro",
            "[🎭 Estado visual: digitando → dormindo]": "visual",
            "[⌨️ Web] Você: e na agenda ?": "conversa",
            "[🌚⚙️ Motor Lógico ativando habilidade: ler_agenda_google]": "ferramenta",
            "[🌚 Proativo: hábito de jogo]": "proativo",
            "[🧩 Prompt: IDENTIDADE + EMOCAO · texto]": "modelo",
            "[📏 Chamada 2 — memória: perfil 507c]": "memoria",
            "Motor Kokoro (pt-BR) carregado com sucesso!": "voz",
            "algo sem tipo": "outros",
        }
        for texto, esperado in casos.items():
            self.assertEqual(atividade.categoria(texto), esperado, texto)

    def test_vermelho_do_cmd_vira_erro_e_cores_somem(self):
        atividade.registrar("\x1b[91mModo Suspenso.\x1b[0m", "10:00:00")
        linha = atividade.instantaneo()[-1]
        self.assertEqual(linha["texto"], "Modo Suspenso.")
        self.assertEqual(linha["categoria"], "erro")

    def test_separadores_e_vazios_nao_entram(self):
        for texto in ("===================================", "", "   ", "\x1b[90m\x1b[0m"):
            atividade.registrar(texto)
        self.assertEqual(atividade.instantaneo(), [])

    def test_guarda_so_as_ultimas_linhas(self):
        for i in range(atividade.LIMITE + 25):
            atividade.registrar(f"linha {i}")
        linhas = atividade.instantaneo()
        self.assertEqual(len(linhas), atividade.LIMITE)
        self.assertEqual(linhas[-1]["texto"], f"linha {atividade.LIMITE + 24}")

    def test_ouvinte_quebrado_nao_derruba_o_print(self):
        recebidas = []
        atividade.ouvir(lambda linha: 1 / 0)
        atividade.ouvir(recebidas.append)
        atividade.registrar("ok")
        self.assertEqual([l["texto"] for l in recebidas], ["ok"])

    def test_handler_pega_erro_do_logging(self):
        log = logging.getLogger("teste.atividade")
        handler = atividade.HandlerLog()
        log.addHandler(handler)
        self.addCleanup(log.removeHandler, handler)
        log.info("info não entra")
        try:
            raise ValueError("porta ocupada")
        except ValueError:
            log.exception("Falha na conexão")
        textos = [l["texto"] for l in atividade.instantaneo()]
        self.assertEqual(len(textos), 1)
        self.assertIn("ValueError: porta ocupada", textos[0])
        self.assertEqual(atividade.instantaneo()[-1]["categoria"], "erro")


class _Cliente:
    def __init__(self):
        self.enviados = []

    def send(self, payload):
        self.enviados.append(json.loads(payload))


class TestaAssinaturaServidor(unittest.TestCase):
    def test_so_assinante_recebe_linhas(self):
        import servidor
        assinante, outro = _Cliente(), _Cliente()
        with servidor._clientes_lock:
            servidor._clientes.update((assinante, outro))
        self.addCleanup(servidor._clientes.difference_update, (assinante, outro))
        with patch.object(atividade, "_linhas", atividade._linhas.__class__(maxlen=atividade.LIMITE)):
            atividade.registrar("antes de abrir")
            servidor._assinar_atividade(assinante, True)
            self.assertEqual(assinante.enviados[0]["tipo"], "atividade_inicio")
            self.assertEqual(assinante.enviados[0]["linhas"][-1]["texto"], "antes de abrir")
            atividade.registrar("ao vivo")
            self.assertEqual(assinante.enviados[-1]["linha"]["texto"], "ao vivo")
            servidor._assinar_atividade(assinante, False)
            atividade.registrar("depois de fechar")
            self.assertNotIn("depois de fechar", [m.get("linha", {}).get("texto") for m in assinante.enviados])
            self.assertEqual(outro.enviados, [])


if __name__ == "__main__":
    unittest.main()
