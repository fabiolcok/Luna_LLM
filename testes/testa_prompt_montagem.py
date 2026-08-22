"""Congela a montagem do prompt de sistema, ramo por ramo.

Existe para uma coisa só: permitir MEXER na estrutura dos prompts sem mudar o comportamento.
A bancada mede comportamento com modelo real e tem variância — ela não consegue provar que uma
refatoração foi neutra. Este teste consegue: ele captura o `prompt_sistema` que sairia de verdade
e compara BYTE A BYTE com um golden. Se a string final é idêntica, o modelo não tem como notar.

Não sobe modelo nenhum. O `_chamar_llm` é substituído por um dublê que grava as mensagens.

Quando a mudança no prompt for INTENCIONAL (passo 3: cortar regra duplicada), atualize o golden:

    venv\\Scripts\\python.exe -X utf8 -m testes.testa_prompt_montagem --atualizar

e leia o diff do `git diff` antes de commitar — é lá que se vê o que realmente mudou.
"""

import re
import sys
import time
import unittest
from pathlib import Path
from unittest.mock import patch

RAIZ = Path(__file__).parents[1]
sys.path.insert(0, str(RAIZ))
GOLDEN = Path(__file__).parent / "prompt_golden.txt"

PERFIL = "- Mora em Brasília.\n- Trabalha com automação.\n- Tem duas filhas."
SEPARADOR = "\n\n" + "=" * 78 + "\n"
MARCA_USUARIO = "\n\n--- mensagem do usuário ---\n"


class _Resposta:
    """Dublê do retorno do cliente OpenAI: só o suficiente para a função terminar."""
    class _Uso:
        completion_tokens = 7

    class _Msg:
        content = "Beleza. [clima:zoeira]"
        reasoning_content = ""

    class _Escolha:
        message = None
        finish_reason = "stop"

    def __init__(self):
        esc = self._Escolha()
        esc.message = self._Msg()
        self.choices = [esc]
        self.usage = self._Uso()


# Cada cenário existe para acender UM ramo da montagem. Ao criar um `modo_enxuto` novo,
# acrescente um cenário aqui — senão ele nasce sem rede.
CENARIOS = [
    {"id": "texto_normal", "usuario": "tava pensando em trocar o roteador, o wifi cai direto"},
    {"id": "voz_normal", "usuario": "que horas são as reuniões amanhã?", "responder_completo": False},
    {"id": "primeiro_turno_do_dia", "usuario": "e aí, novidade?", "saudou_antes": False},
    {"id": "fora_do_pc", "usuario": "cheguei no mercado", "no_pc": False},
    {"id": "com_memoria_e_chroma", "usuario": "voltei pro projeto de ontem",
     "memorias": [("12/08", "terminou a refatoração do módulo de voz"),
                  ("14/08", "reclamou do calor em Brasília")],
     "chroma": "Ele comentou que o ventilador da sala faz barulho."},
    {"id": "kaomoji_recente", "usuario": "consegui fazer funcionar", "kaomojis": ["(•‿•)", "ᗜ‿ᗜ"]},
    {"id": "com_ferramenta", "usuario": "que música tá tocando?",
     "tecnica": "Tocando agora: Comfortably Numb — Pink Floyd"},
    {"id": "ferramenta_falhou", "usuario": "abre minha agenda",
     "tecnica": "Erro: não foi possível conectar no Google Calendar"},
    # a partir daqui, um cenário por modo_enxuto — na mesma ordem em que o pensar.py testa
    {"id": "enxuto_saudacao", "usuario": "oi, tudo bem?"},
    {"id": "enxuto_saudacao_voz", "usuario": "oi, tudo bem?", "responder_completo": False},
    {"id": "enxuto_mudanca_ideia", "usuario": "mudei de ideia, vou jogar Hades em vez de Elden Ring"},
    {"id": "enxuto_contradicao", "usuario": "falei que ia jogar meia hora mas acabei virando a noite"},
    {"id": "enxuto_compra_jogo", "usuario": "vou comprar um jogo na steam hoje"},
    {"id": "enxuto_cotidiano", "usuario": "vou comprar comida"},
    {"id": "enxuto_referencia_sem_nome", "usuario": "qual é o nome dele?",
     "historico": [{"role": "user", "content": "o que você andou vendo?"},
                   {"role": "assistant", "content": "tava de olho em aquele jogo novo"}]},
    {"id": "enxuto_correcao", "usuario": "você errou, não foi isso que eu disse"},
    {"id": "enxuto_agradecimento", "usuario": "valeu"},
    {"id": "enxuto_proativo", "usuario": "",
     "tecnica": "A placa de vídeo está em 82°C há quarenta minutos."},
    {"id": "enxuto_proativo_contraste", "usuario": "",
     "tecnica": "CONTRASTE DE ABERTURA CONFIRMADO PELO SISTEMA: anunciou The Last of Us, abriu Silksong."},
    {"id": "enxuto_zoeira_backlog", "usuario": "quero comprar mais um jogo e meu backlog tá lotado"},
    {"id": "enxuto_sensivel", "usuario": "tô triste hoje"},
    {"id": "enxuto_cansaco", "usuario": "tô muito cansado dessa semana"},
]


def capturar(cenario: dict) -> str:
    """Roda a persona de verdade com as fontes pessoais substituídas e devolve o system prompt."""
    from modulos import pensar

    capturado = {}

    def _dublê(**parametros):
        msgs = parametros["messages"]
        capturado.setdefault("sistema", msgs[0]["content"])
        capturado.setdefault("usuario", msgs[-1]["content"])
        return _Resposta()

    pensar._ultima_saudacao_ts = time.time() if cenario.get("saudou_antes", True) else 0
    pensar._kaomoji_recentes.clear()
    pensar._kaomoji_recentes.extend(cenario.get("kaomojis", []))
    pensar._presenca_pc.set(cenario.get("no_pc", True))
    with (
        patch.object(pensar, "_chamar_llm", _dublê),
        patch.object(pensar.obsidian, "ler_perfil", return_value=PERFIL),
        patch.object(pensar.obsidian, "listar_memoria_episodica",
                     return_value=list(cenario.get("memorias", []))),
        patch.object(pensar.obsidian, "avaliar_relevancia", return_value=True),
        patch.object(pensar, "buscar_memoria_relevante", return_value=[]),
        patch.object(pensar, "buscar_contexto_relevante", return_value=cenario.get("chroma", "")),
        patch.object(pensar, "ler_estado_luna", return_value={}),
        patch.object(pensar, "obter_janela_em_foco", return_value="bancada de teste"),
    ):
        pensar._reescrever_como_luna(
            cenario.get("tecnica", ""), cenario["usuario"],
            [dict(m) for m in cenario.get("historico", [])],
            max_tokens=220,
            responder_completo=cenario.get("responder_completo", True),
        )
    if "sistema" not in capturado:
        return "<<NENHUM PROMPT FOI MONTADO>>"
    return capturado["sistema"] + MARCA_USUARIO + capturado["usuario"]


def normalizar(texto: str) -> str:
    """Tira o que muda a cada execução — data, hora e período do dia — sem tocar no resto."""
    return re.sub(r"^Hoje é .*$", "Hoje é <DATA/HORA/PERÍODO>", texto, count=1, flags=re.MULTILINE)


def montar_tudo() -> str:
    partes = []
    for cenario in CENARIOS:
        partes.append("### %s\n%s" % (cenario["id"], normalizar(capturar(cenario))))
    return SEPARADOR.join(partes) + "\n"


class TestaMontagemDoPrompt(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.atual = montar_tudo()
        cls.esperado = GOLDEN.read_text(encoding="utf-8") if GOLDEN.exists() else ""

    def _fatiar(self, texto: str) -> dict:
        blocos = {}
        for bloco in texto.split(SEPARADOR.strip("\n")):
            bloco = bloco.strip("\n")
            if bloco.startswith("### "):
                nome, _, corpo = bloco.partition("\n")
                blocos[nome[4:].strip()] = corpo
        return blocos

    def test_golden_existe(self):
        self.assertTrue(GOLDEN.exists(),
                        "Falta o golden. Gere com: python -m testes.testa_prompt_montagem --atualizar")

    def test_todo_cenario_montou_um_prompt(self):
        for nome, corpo in self._fatiar(self.atual).items():
            with self.subTest(cenario=nome):
                self.assertNotIn("<<NENHUM PROMPT", corpo)

    def test_proibicao_de_emoji_e_markdown_so_existe_na_voz(self):
        """No texto a proibição não faz sentido e só gastava contexto — ver TODO/persona."""
        blocos = self._fatiar(self.atual)
        for nome, corpo in blocos.items():
            sistema = corpo.split(MARCA_USUARIO)[0]
            e_voz = "voz" in nome
            with self.subTest(cenario=nome):
                if e_voz:
                    self.assertIn("emoji", sistema.lower(),
                                  "canal de voz sem a proibição de emoji: ela vira áudio")
                else:
                    self.assertNotIn("emoji", sistema.lower(),
                                     "canal de texto gastando prompt com proibição de emoji")

    def test_prompt_de_cada_ramo_nao_mudou(self):
        atuais, esperados = self._fatiar(self.atual), self._fatiar(self.esperado)
        self.assertEqual(sorted(esperados), sorted(atuais),
                         "A lista de cenários mudou — rode com --atualizar.")
        for nome in esperados:
            with self.subTest(cenario=nome):
                self.assertEqual(
                    esperados[nome], atuais[nome],
                    "\nO prompt de sistema do ramo '%s' mudou.\n"
                    "   Se foi SEM QUERER, a refatoração não foi neutra: desfaça.\n"
                    "   Se foi DE PROPÓSITO, rode:\n"
                    "     python -m testes.testa_prompt_montagem --atualizar\n"
                    "   e confira o `git diff` do golden antes de commitar." % nome)


if __name__ == "__main__":
    if "--atualizar" in sys.argv:
        GOLDEN.write_text(montar_tudo(), encoding="utf-8", newline="\n")
        print("golden regravado: %s (%d cenários)" % (GOLDEN.name, len(CENARIOS)))
    else:
        unittest.main()
