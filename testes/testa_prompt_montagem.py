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
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch

RAIZ = Path(__file__).parents[1]
sys.path.insert(0, str(RAIZ))
GOLDEN = Path(__file__).parent / "prompt_golden.txt"

PERFIL = "- Mora em Brasília.\n- Trabalha com automação.\n- Tem duas filhas."
SEPARADOR = "\n\n" + "=" * 78 + "\n"
MARCA_USUARIO = "\n\n--- mensagem do usuário ---\n"
EVENTOS_AGENDA = [{'titulo': 'Reunião de teste', 'inicio': '2026-10-10T14:00:00-03:00',
                  'fim': '2026-10-10T15:00:00-03:00', 'dia_inteiro': False}]
NOTICIA = {'titulo': 'Fabricante pode mudar a linha de placas', 'fonte': 'Feed de teste',
           'url': 'https://example.org/noticia', 'resumo': 'Mudança possível, sem confirmação.'}


@contextmanager
def referencia_novidade(noticia):
    from modulos.novidades_web import contexto_novidade
    token = contexto_novidade.set(noticia)
    try:
        yield
    finally:
        contexto_novidade.reset(token)


@contextmanager
def referencia_resposta(resposta):
    from modulos.biblioteca_web import contexto_resposta
    token = contexto_resposta.set(resposta)
    try:
        yield
    finally:
        contexto_resposta.reset(token)


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
    {'id': 'resposta_mensagem_web', 'usuario': 'O que você quis dizer com isso?',
     'resposta_a': {'referencia': {'turno_id': 'turno-teste'}, 'usuario': 'Quero começar Dark Souls.',
                   'luna': 'A gravidade já pediu uma reunião com você.', 'cartoes': []}},
    {'id': 'resposta_mensagem_voz', 'usuario': 'O que você quis dizer com isso?', 'responder_completo': False,
     'resposta_a': {'referencia': {'turno_id': 'turno-teste'}, 'usuario': '', 'luna': 'Referência exclusiva da web.', 'cartoes': []}},
    {"id": "rascunho_fontes_web", "usuario": "Acompanhe suporte PT-BR em https://example.org/releases.atom",
     "tecnica": "Rascunho preparado no cartão. A consulta só começa após a confirmação.",
     "tarefa_documento": "CONFIRMACAO_RASCUNHO_FONTES"},
    {"id": "continuacao_novidade_web", "usuario": "O que muda para quem já planejou a compra?",
     "noticia": NOTICIA},
    {"id": "continuacao_novidade_artigo_web", "usuario": "Quais mudanças o artigo confirmou?",
     "noticia": NOTICIA, "tecnica": "Artigo sintético: o fabricante ainda não confirmou a mudança.",
     "tarefa_documento_texto": "Atenda exatamente ao pedido com base no conteúdo do artigo."},
    {"id": "texto_normal", "usuario": "tava pensando em trocar o roteador, o wifi cai direto"},
    {"id": "momento_com_jogo", "usuario": "qual jogo está detectado?", "janela": "Luna",
     "observacoes_jogos": {"processos": {"nomes": ["Overwatch"], "instante": 990}}},
    {"id": "momento_com_relato", "usuario": "e agora?", "janela": "Editor de código",
     "historico": [{"role": "user", "content": "Estou ajustando a Luna.", "instante": 980},
                   {"role": "assistant", "content": "Vamos nessa.", "instante": 985}]},
    {"id": "voz_normal", "usuario": "que horas são as reuniões amanhã?", "responder_completo": False},
    {"id": "primeiro_turno_do_dia", "usuario": "e aí, novidade?", "saudou_antes": False},
    {"id": "fora_do_pc", "usuario": "cheguei no mercado", "no_pc": False},
    {"id": "com_memoria_e_chroma", "usuario": "voltei pro projeto de ontem",
     "memorias": [("12/08", "terminou a refatoração do módulo de voz"),
                  ("14/08", "reclamou do calor em Brasília")],
     "chroma": "Ele comentou que o ventilador da sala faz barulho."},
    {"id": "com_assunto_em_andamento", "usuario": "voltei a mexer no Fluxer",
     "assuntos": "- [aberto] Fluxer no Ubuntu — instalado, mas ainda sem outros usuários"},
    {"id": "kaomoji_recente", "usuario": "consegui fazer funcionar", "kaomojis": ["(•‿•)", "ᗜ‿ᗜ"]},
    {"id": "com_ferramenta", "usuario": "que música tá tocando?",
     "tecnica": "Tocando agora: Comfortably Numb — Pink Floyd"},
    {"id": "ferramenta_falhou", "usuario": "abre minha agenda",
     "tecnica": "Erro: não foi possível conectar no Google Calendar"},
    {"id": "agenda_web", "usuario": "Como está minha agenda?", "agenda_eventos": EVENTOS_AGENDA,
     "tecnica": "Aqui estão os seus compromissos:\n- Reunião de teste — sábado, 10 de outubro às 14h"},
    {"id": "agenda_vazia_web", "usuario": "Como está minha agenda?", "agenda_eventos": [],
     "tecnica": "A sua agenda está completamente vazia para os próximos 30 dias."},
    {"id": "agenda_criada_web", "usuario": "Marque reunião de teste amanhã às 14h",
     "agenda_eventos": EVENTOS_AGENDA, "tecnica": "Sucesso! O evento 'Reunião de teste' foi criado para sábado, 10 de outubro às 14h."},
    {"id": "agenda_voz", "usuario": "Consulte minha agenda", "agenda_eventos": EVENTOS_AGENDA,
     "responder_completo": False, "tecnica": "Aqui estão os seus compromissos:\n- Reunião de teste — sábado, 10 de outubro às 14h"},
    {"id": "agenda_telegram", "usuario": "Consulte minha agenda", "agenda_eventos": EVENTOS_AGENDA,
     "no_pc": False, "tecnica": "Aqui estão os seus compromissos:\n- Reunião de teste — sábado, 10 de outubro às 14h"},
    {"id": "duvida_jogo_com_dados", "usuario": "Como funciona a coleta no jogo de teste?",
     "tecnica": "SISTEMA: Resultado da pesquisa sobre 'Jogo de teste':\nA fonte sintética informa: ative Coleta perto do recurso."},
    {"id": "duvida_jogo_sem_dados", "usuario": "Como funciona a coleta no jogo de teste?",
     "tecnica": "SISTEMA: PESQUISA_JOGO_SEM_DADOS: Não há material identificável desse jogo."},
    {"id": "duvida_jogo_erro", "usuario": "Como funciona a coleta no jogo de teste?",
     "tecnica": "SISTEMA: PESQUISA_JOGO_ERRO: Conexão indisponível."},
    {"id": "duvida_jogo_sem_contexto", "usuario": "Como funciona a coleta?",
     "tecnica": "SISTEMA: PESQUISA_JOGO_SEM_CONTEXTO: Nenhuma consulta foi realizada."},
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
    {"id": "radar_rss_voz", "usuario": "", "responder_completo": False,
     "tarefa_proativa": "radar_rss", "tecnica": "Notícia sintética: um estúdio anunciou combate a cheaters com IA."},
    {"id": "radar_rss_texto", "usuario": "", "tarefa_proativa": "radar_rss",
     "tecnica": "Notícia sintética: um teste prolongado de OLED encontrou burn-in."},
    {"id": "dark_souls_morte_voz", "usuario": "", "responder_completo": False,
     "tarefa_proativa": "dark_souls_morte", "evento_dark_souls": {"tipo": "morte", "nome": ""}},
    {"id": "dark_souls_chefe_voz", "usuario": "", "responder_completo": False,
     "tarefa_proativa": "dark_souls_chefe", "evento_dark_souls": {"tipo": "chefe", "nome": "Bell Gargoyles"}},
    {"id": "dark_souls_fogueira_voz", "usuario": "", "responder_completo": False,
     "tarefa_proativa": "dark_souls_fogueira", "evento_dark_souls": {"tipo": "fogueira", "nome": "Undead Burg"}},
    {"id": "enxuto_zoeira_backlog", "usuario": "quero comprar mais um jogo e meu backlog tá lotado"},
    {"id": "enxuto_sensivel", "usuario": "tô triste hoje"},
    {"id": "enxuto_cansaco", "usuario": "tô muito cansado dessa semana"},
]


def capturar(cenario: dict, *, pedido_completo=False):
    """Roda a persona de verdade com as fontes pessoais substituídas e devolve o system prompt."""
    from modulos import pensar
    from modulos import momento
    capturar_momento = momento.capturar

    capturado = {}

    def _dublê(**parametros):
        msgs = parametros["messages"]
        capturado.setdefault("sistema", msgs[0]["content"])
        capturado.setdefault("usuario", msgs[-1]["content"])
        capturado.setdefault('pedido', parametros)
        return _Resposta()

    pensar._ultima_saudacao_ts = time.time() if cenario.get("saudou_antes", True) else 0
    pensar._kaomoji_recentes.clear()
    pensar._kaomoji_recentes.extend(cenario.get("kaomojis", []))
    pensar._presenca_pc.set(cenario.get("no_pc", True))
    tecnica = cenario.get('tecnica', '')
    if 'agenda_eventos' in cenario:
        from modulos.agenda_web import resultado
        tecnica = resultado(tecnica, cenario['agenda_eventos'])
    with (
        referencia_novidade(cenario.get('noticia')),
        referencia_resposta(cenario.get('resposta_a')),
        patch.object(pensar, "_chamar_llm", _dublê),
        # Em produção os exemplos de tom são sorteados; o golden fixa os três primeiros.
        patch.object(pensar._prompts, "sortear_exemplos_tom",
                     side_effect=lambda mensagem="", qtd=3: pensar._prompts.EXEMPLOS_TOM[:qtd]),
        patch.object(pensar.obsidian, "ler_perfil", return_value=PERFIL),
        patch.object(pensar.obsidian, "listar_memoria_episodica",
                     return_value=list(cenario.get("memorias", []))),
        patch.object(pensar.obsidian, "avaliar_relevancia", return_value=True),
        patch.object(pensar, "buscar_memoria_relevante", return_value=[]),
        patch.object(pensar, "buscar_contexto_relevante", return_value=cenario.get("chroma", "")),
        patch.object(pensar.assuntos, "contexto_relacionado",
                     return_value=cenario.get("assuntos", "")),
        patch.object(pensar, "ler_estado_luna", return_value={}),
        patch.object(pensar, "obter_janela_em_foco", return_value=cenario.get("janela", "bancada de teste")),
        patch.object(momento, "_jogos", cenario.get("observacoes_jogos", {})),
        patch.object(momento, "capturar", side_effect=lambda **kw: capturar_momento(agora=1000, **kw)),
    ):
        pensar._reescrever_como_luna(
            (pensar._prompts.prompt_dark_souls(cenario["evento_dark_souls"])
             if "evento_dark_souls" in cenario else tecnica), cenario["usuario"],
            [dict(m) for m in cenario.get("historico", [])],
            max_tokens=220,
            responder_completo=cenario.get("responder_completo", True),
            tarefa_documento=(getattr(pensar._prompts, cenario['tarefa_documento'])
                              if cenario.get('tarefa_documento') else cenario.get('tarefa_documento_texto')),
            tarefa_proativa=cenario.get("tarefa_proativa"),
        )
    if "sistema" not in capturado:
        return "<<NENHUM PROMPT FOI MONTADO>>"
    return capturado['pedido'] if pedido_completo else capturado["sistema"] + MARCA_USUARIO + capturado["usuario"]


def normalizar(texto: str) -> str:
    """Tira o que muda a cada execução — data, hora e período do dia — sem tocar no resto."""
    from modulos import pensar
    texto = re.sub(r"^Hoje é .*$", "Hoje é <DATA/HORA/PERÍODO>", texto, count=1, flags=re.MULTILINE)
    texto = re.sub(r'("(?:hoje|amanha)":")\d{4}-\d{2}-\d{2}(?=")', r'\1<DATA>', texto)
    # O golden é público. Só normaliza os campos de nome: o padrão "Usuário" também
    # aparece em regras genéricas que precisam continuar sendo comparadas literalmente.
    nome = pensar._prompts.NOME_USUARIO
    if nome:
        for antes, depois in (("PERFIL DO ", " (a pessoa"),
                              ("amiga próxima do ", " (o usuário)"),
                              ("amiga próxima do ", ". Responda"),
                              ("falando com ", ". "),
                              ("o próprio ", " construiu")):
            padrao = "(" + re.escape(antes) + ")" + re.escape(nome) + "(?=" + re.escape(depois) + ")"
            texto = re.sub(padrao, r"\1<USUARIO>", texto, flags=re.IGNORECASE)
    return texto


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

    def test_referencia_so_entra_na_resposta_web(self):
        blocos = self._fatiar(self.atual)
        self.assertIn('A gravidade já pediu uma reunião com você.', blocos['resposta_mensagem_web'])
        self.assertNotIn('Referência exclusiva da web.', blocos['resposta_mensagem_voz'])

    def test_nome_padrao_nao_normaliza_regras_genericas(self):
        from modulos import pensar
        with patch.object(pensar._prompts, "NOME_USUARIO", "Usuário"):
            self.assertEqual(normalizar("PERFIL DO USUÁRIO (a pessoa); responda ao usuário."),
                             "PERFIL DO <USUARIO> (a pessoa); responda ao usuário.")
            self.assertEqual(normalizar("Você é Luna, falando com Usuário. Responda ao usuário."),
                             "Você é Luna, falando com <USUARIO>. Responda ao usuário.")

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

    def test_apresentacao_visual_so_na_web_com_prompt_completo(self):
        blocos = self._fatiar(self.atual)
        for cenario in CENARIOS:
            nome = cenario["id"]
            sistema = blocos[nome].split(MARCA_USUARIO)[0]
            e_web = cenario.get("responder_completo", True) and cenario.get("no_pc", True)
            e_completo = "CANAL DE TEXTO (Web ou Telegram)" in sistema
            with self.subTest(cenario=nome):
                self.assertEqual("APRESENTAÇÃO WEB:" in sistema, e_web and e_completo)

    def test_duvida_jogo_recebe_estado_sem_falha_generica(self):
        blocos = self._fatiar(self.atual)
        for nome in ("duvida_jogo_com_dados", "duvida_jogo_sem_dados", "duvida_jogo_erro",
                     "duvida_jogo_sem_contexto"):
            with self.subTest(cenario=nome):
                usuario = blocos[nome].split(MARCA_USUARIO)[1]
                self.assertIn("ESTADO CONFIRMADO DA CONSULTA:", usuario)
                self.assertNotIn("A ferramenta FALHOU", usuario)
                self.assertIn("causa, intenção dos criadores ou mecânica", usuario)
        self.assertIn("A ferramenta FALHOU", blocos["ferramenta_falhou"].split(MARCA_USUARIO)[1])

    def test_conversa_de_jogo_preserva_emocao_e_perfil(self):
        from modulos import prompts
        blocos = self._fatiar(self.atual)
        for nome in ("duvida_jogo_com_dados", "duvida_jogo_sem_dados", "duvida_jogo_erro",
                     "duvida_jogo_sem_contexto"):
            with self.subTest(cenario=nome):
                sistema = blocos[nome].split(MARCA_USUARIO)[0]
                self.assertEqual(sistema.count(prompts.EMOCAO), 1)
                self.assertIn(PERFIL, sistema)

    def test_sugestoes_so_entram_no_radar_rss_sem_reordenar_persona(self):
        from modulos import prompts
        blocos = self._fatiar(self.atual)
        for nome, corpo in blocos.items():
            with self.subTest(cenario=nome):
                self.assertEqual(prompts.SUGESTOES_NOVIDADE_WEB in corpo, nome.startswith('radar_rss_'))
                if nome.startswith('radar_rss_'):
                    sistema = corpo.split(MARCA_USUARIO)[0]
                    self.assertIn(prompts.ENXUTO_PROATIVO, sistema)
                    self.assertEqual(sistema.count(prompts.EMOCAO), 1)

    def test_agenda_visual_so_muda_instrucao_da_persona_na_web(self):
        blocos = self._fatiar(self.atual)
        for nome, corpo in blocos.items():
            with self.subTest(cenario=nome):
                self.assertEqual('já aparecem em um cartão na conversa' in corpo,
                                 nome in {'agenda_web', 'agenda_vazia_web', 'agenda_criada_web'})



if __name__ == "__main__":
    if "--atualizar" in sys.argv:
        GOLDEN.write_text(montar_tudo(), encoding="utf-8", newline="\n")
        print("golden regravado: %s (%d cenários)" % (GOLDEN.name, len(CENARIOS)))
    else:
        unittest.main()
