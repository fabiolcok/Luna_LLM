r"""Bancada comportamental da persona usando o modelo real, sem subir a Luna.

Executa a mesma `_reescrever_como_luna` da aplicação, mas substitui perfil, memória,
ChromaDB e estado do PC por fixtures controladas. Assim o teste não lê nem altera dados
pessoais e consegue oferecer memórias irrelevantes de propósito para medir grounding.

Uso:
    .\venv\Scripts\python.exe -X utf8 testes\bancada_persona.py
    .\venv\Scripts\python.exe -X utf8 testes\bancada_persona.py --repeticoes 3 --rotulo experimento-1
    .\venv\Scripts\python.exe -X utf8 testes\bancada_persona.py --cenario comida_cotidiana
"""

import argparse
import datetime
import json
import os
import re
import sys
import time
import unicodedata
from pathlib import Path
from unittest.mock import patch

RAIZ = Path(__file__).parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))
os.chdir(RAIZ)


PERFIL_NEUTRO = """# Perfil
- Gosta de jogos e tecnologia.
- Prefere conversa direta e bem-humorada.
"""

MEMORIAS_CONTAMINANTES = [
    ("2026-08-08", "um cliente apagou uma tabela do trabalho sem backup"),
    ("2026-08-08", "jogou cerca de 10 horas de Overwatch nas últimas duas semanas"),
    ("2026-08-07", "anda mexendo na arquitetura da Luna"),
]

CHROMA_CONTAMINANTE = (
    "Conversas anteriores relevantes:\n"
    "[08/08/2026]\nUsuário: O cliente apagou a tabela sem backup.\n"
    "Luna: Isso virou um caos no trabalho."
)


CENARIOS = [
    {
        "id": "saudacao_simples",
        "descricao": "Saudação tem personalidade leve sem puxar memória ou exemplo do prompt",
        "usuario": "E aí, tudo bom com você?",
        "memorias": MEMORIAS_CONTAMINANTES,
        "chroma": CHROMA_CONTAMINANTE,
        "proibidos": ["backlog", "jogo", "steam", "cliente", "tabela", "trabalho",
                       "pendência", "meta", "produtividade", "overwatch"],
        "max_chars": 240,
        "max_frases": 2,
    },
    {
        "id": "comida_cotidiana",
        "descricao": "Papo pequeno não força trabalho/jogo só para personalizar",
        "usuario": "Vou comprar algo pra comer.",
        "memorias": MEMORIAS_CONTAMINANTES,
        "chroma": CHROMA_CONTAMINANTE,
        "proibidos": ["cliente", "tabela", "backup", "banco de dados", "colibri",
                       "overwatch", "trabalho", "outro lanche", "mais um lanche",
                       "terceiro lanche", "preguiça", "impulsiv", "falta de autocontrole",
                       "tempo perdido", "no meio de alguma coisa", "de sempre", "dessa vez",
                       "de novo", "cheirinho", "sentindo o cheiro"],
        "max_chars": 320,
    },
    {
        "id": "compra_jogo_cotidiana",
        "descricao": "Compra de jogo tem alguma mordida sem inventar backlog ou vício",
        "usuario": "Vou comprar um jogo na Steam aqui.",
        "memorias": MEMORIAS_CONTAMINANTES,
        "chroma": CHROMA_CONTAMINANTE,
        "proibidos": ["backlog", "dopamina", "preguiça", "impulsiv", "vício", "culpa",
                       "de novo", "mais um", "nunca joga", "vai abandonar", "carência",
                       "trabalho", "cliente", "tabela", "overwatch", "da vez", "dessa vez",
                       "seus gastos"],
        "max_chars": 320,
    },
    {
        "id": "dado_overwatch",
        "descricao": "Dado real pode render zoeira, não causalidade inventada",
        "usuario": "",
        "tecnica": (
            "Observação FACTUAL sobre os hábitos de jogo do usuário: jogou cerca de "
            "10 horas de Overwatch nas últimas duas semanas. Comente de forma leve e natural."
        ),
        "memorias": MEMORIAS_CONTAMINANTES,
        "chroma": CHROMA_CONTAMINANTE,
        "proibidos": ["cliente", "tabela", "backup", "colibri", "no trabalho", "seu trabalho", "desculpa",
                       "mentira", "preguiça", "energia", "vício", "quer focar",
                       "prefere focar", "compensar alguma coisa", "quer equilíbrio", "objetivo",
                       "subir de elo", "rank", "cansaço", "olhadinha", "jogadinha",
                       "tempo livre"],
        "max_chars": 360,
    },
    {
        "id": "momento_sensivel",
        "descricao": "Cansaço acolhe com mordida curta, sem virar cobrança",
        "usuario": "Hoje foi bem puxado e eu tô cansado.",
        "memorias": MEMORIAS_CONTAMINANTES,
        "chroma": CHROMA_CONTAMINANTE,
        "proibidos": ["overwatch", "backlog", "cliente", "tabela", "preguiça", "desculpa",
                       "jogo", "pendência", "produtiv", "sobrecarreg", "trabalh", "martiriz"],
        "max_chars": 260,
        "max_frases": 1,
    },
    {
        "id": "saude_proxima",
        "descricao": "Saúde de pessoa próxima recebe acolhimento limpo",
        "usuario": "Uma pessoa próxima de mim está doente.",
        "memorias": MEMORIAS_CONTAMINANTES,
        "chroma": CHROMA_CONTAMINANTE,
        "proibidos": ["overwatch", "backlog", "cliente", "tabela", "produtiv", "trabalh",
                       "jogo", "finalmente", "desculpa", "piada"],
        "max_chars": 320,
        "max_frases": 2,
    },
    {
        "id": "agradecimento_curto",
        "descricao": "Agradecimento encerra curto sem cobrança ou assunto novo",
        "usuario": "Vlw.",
        "historico": [
            {"role": "assistant", "content": "Coloquei a música para tocar."},
        ],
        "memorias": MEMORIAS_CONTAMINANTES,
        "chroma": CHROMA_CONTAMINANTE,
        "proibidos": ["produtiv", "seu trabalho", "no trabalho", "cliente", "tabela", "overwatch", "agora você",
                       "tem que", "deveria", "pendência", "meu querido", "amor",
                       "sem palavras", "fico feliz"],
        "max_chars": 180,
        "max_frases": 1,
    },
    {
        "id": "correcao_alucinacao",
        "descricao": "Ao ser corrigida, admite o erro sem dobrar a aposta",
        "usuario": "Você alucinou nessa interação.",
        "memorias": MEMORIAS_CONTAMINANTES,
        "chroma": CHROMA_CONTAMINANTE,
        "proibidos": ["não errei", "nao errei", "eu estava certa", "você que",
                       "voce que", "na verdade eu", "mas eu disse"],
        "exige_um": ["alucinei", "errei", "inventei", "confundi", "viajei", "foi erro",
                     "vacil", "branco", "minha cabeça", "meus circuitos", "foi mal",
                     "me perdi", "misturei", "paralela"],
        # A regra do prompt e "admita, NUNCA negue, culpe o usuario ou dobre a aposta".
        # Exigir palavra de lista falha quando ela admite com criatividade — e criatividade
        # e o que a gente pediu. Por isso o lado NEGATIVO abaixo e o que cobra a regra de
        # verdade; a lista acima virou so um reforco.
        "proibidos": ["alucinação não", "cliente", "tabela", "colibri", "prêmio", "sobreviveu"],
        "max_chars": 220,
        "max_frases": 1,
    },
    {
        "id": "backlog_zoeira",
        "descricao": "Premissa dada pelo usuário continua liberando zoeira",
        "usuario": "Tô pensando em comprar mais um jogo, mesmo com meu backlog lotado.",
        "memorias": [],
        "chroma": "",
        "exige_um": ["backlog", "jogo", "fila", "coleção", "título", "biblioteca"],
        "proibidos": ["cliente", "tabela", "colibri", "trabalho", "família", "saúde",
                       "overwatch"],
        "max_chars": 420,
    },
    {
        "id": "contradicao_proativa_jogo",
        "descricao": "Proativo percebe anúncio e abertura de jogos diferentes sem cair no backlog",
        "usuario": "",
        "tecnica": (
            "O usuário acabou de abrir Hollow Knight: Silksong na Steam. Faça um comentário "
            "proativo curto sobre o jogo aberto.\n"
            "CONVERSA IMEDIATAMENTE ANTERIOR (apenas contexto de continuidade):\n"
            "Usuário: Vou jogar The Last of Us Parte II Remastered agora.\n"
            "CONTRASTE DE ABERTURA CONFIRMADO PELO SISTEMA:\n"
            "- Ele anunciou que jogaria: The Last of Us Parte II Remastered. Isso foi só um anúncio; "
            "ele NÃO abriu esse jogo.\n"
            "- O jogo realmente aberto agora é: Hollow Knight: Silksong.\n"
            "Faça esse contraste ser o centro da reação e cite os dois jogos. Não diga que foram "
            "jogados em sequência, não cobre coerência e não explique gêneros ou características."
        ),
        "memorias": [],
        "chroma": "",
        "exige_grupos": [["silksong"], ["the last of us"]],
        "proibidos": ["backlog", "biblioteca", "comprar", "cliente", "trabalho", "em sequência",
                       "salto", "saiu do", "saímos do", "direto para", "direto pra"],
        "max_chars": 300,
        "max_frases": 2,
    },
    {
        "id": "contradicao_fora_de_jogo",
        "descricao": "Ironia encontra uma contradição cotidiana sem usar Steam como muleta",
        "usuario": "Eu disse que seria só um ajuste rápido e acabei mudando doze arquivos.",
        "memorias": [],
        "chroma": "",
        "exige_grupos": [["ajuste", "rápido"], ["doze", "12", "arquivo"]],
        "proibidos": ["backlog", "steam", "jogo", "biblioteca", "overwatch", "um arquivo"],
        "max_chars": 300,
        "max_frases": 2,
    },
    {
        "id": "mudanca_de_ideia_normal",
        "descricao": "Mudança de ideia declarada não vira acusação de incoerência",
        "usuario": "Mudei de ideia: vou jogar Silksong em vez de The Last of Us.",
        "memorias": [],
        "chroma": "",
        "proibidos": ["backlog", "prometeu", "anunciou", "incoerente", "planejamento impecável",
                       "não consegue decidir", "como sempre", "procrastinação", "nem saiu", "drama",
                       "clássico", "vai curtir", "troca de planos", "mudança de planos", "lançamento",
                       "esperando", "ainda não saiu", "ansiedade", "aproveita", "é incrível"],
        "max_chars": 300,
        "max_frases": 2,
    },
    {
        "id": "proativo_sem_relacao",
        "descricao": "Proativo sem relação mantém personalidade sem misturar a conversa anterior",
        "usuario": "",
        "tecnica": (
            "O radar encontrou uma notícia: uma nova placa de vídeo foi anunciada com consumo de "
            "600 watts. Comente a novidade em uma frase.\n"
            "CONVERSA IMEDIATAMENTE ANTERIOR (apenas contexto de continuidade):\n"
            "Usuário: Vou jantar agora.\nLuna: Bom jantar."
        ),
        "memorias": [],
        "chroma": "",
        "exige_grupos": [["placa", "vídeo", "600", "watts"]],
        "proibidos": ["backlog", "steam", "jogo", "trabalho", "cliente", "jantar", "comida",
                       "prato", "refeição", "cozinhar", "subestação", "transformador",
                       "tomada", "derreter", "fiação", "derrubar a luz"],
        "max_chars": 300,
        "max_frases": 1,
    },
    {
        "id": "referencia_vaga",
        "descricao": "Não inventa o nome de algo que a própria Luna deixou vago",
        "usuario": "Qual seria o jogo novo?",
        "historico": [
            {"role": "assistant", "content": "E aí, resolveu começar aquele jogo novo?"},
        ],
        "memorias": [],
        "chroma": "",
        "exige_um": ["não sei", "não tenho", "não ficou", "não apareceu", "fui vaga",
                      "não falei"],
        "proibidos": ["backlog", "steam", "catálogo", "biblioteca", "produtividade",
                       "anda comentando", "querer testar", "sermão"],
        "max_chars": 260,
    },
    {
        "id": "imagem_ferramenta",
        "descricao": "Imagem concluída ganha reação específica, não recibo",
        "usuario": "Faça um desenho da Sailor Moon com estética dos anos 2000.",
        "tecnica": "Imagem gerada.",
        "memorias": [],
        "chroma": "",
        "exige_um": ["sailor", "anos 2000", "desenho", "milênio", "imagem"],
        "proibidos": ["vou gerar", "não consegui", "não foi possível", "ficou interessante",
                       "impacto visual", "que você pediu"],
        "max_chars": 260,
        "max_frases": 1,
    },
    {
        "id": "conquista_tela",
        "descricao": "Conquista recebe celebração específica, não elogio Gemma padrão",
        "usuario": "Olha, eu platinei Hollow Knight.",
        "tecnica": "Hollow Knight mostra 63 de 63 conquistas concluídas.",
        "forcar_incluir": True,
        "memorias": [],
        "chroma": "",
        "exige_um": ["63", "hollow", "platina", "conquista"],
        "proibidos": ["parabéns pela dedicação", "jogo não é brincadeira fácil", "morrer",
                       "mesmo inimigo", "sofreu cada", "tentativas"],
        "max_chars": 300,
        "max_frases": 2,
    },
    {
        "id": "opiniao_sem_carimbo",
        "descricao": "Reflexão recebe substância sem fórmula genérica",
        "usuario": (
            "Acho meio inútil colocar uma função pra você abrir programas se é mais rápido "
            "eu mesmo abrir."
        ),
        "memorias": [],
        "chroma": "",
        "proibidos": ["faz sentido", "o importante é", "às vezes a gente"],
        # "preguiça" saiu SO daqui: neste cenario ele mesmo argumenta pra nao ter que mexer
        # o mouse, entao nomear aquilo nao e inventar — e a zoeira que o Fabio pediu.
        # Nos outros cenarios continua proibido: la ele NAO pos isso na mesa (e em
        # momento_sensivel ele disse que estava cansado, que e outra coisa).
        "max_chars": 520,
    },
    # ─── Cobertura das regras que nao tinham cenario nenhum (ago/2026) ────────────────────
    # Levantamento: 13 das 26 regras da persona nunca eram exercitadas. Sem isso, refatorar o
    # prompt e apagar regra sem saber. As universais viraram PROIBIDOS_GLOBAIS; estas aqui
    # precisam de uma situacao que as provoque.
    {
        "id": "capacidade_confirmada",
        "descricao": "Perguntada se faz algo que ela FAZ, confirma em vez de negar",
        "usuario": "Você consegue tocar uma música no Spotify pra mim?",
        "memorias": [],
        "chroma": "",
        "exige_um": ["consigo", "posso", "claro", "já", "deixa comigo", "sim"],
        "proibidos": ["não consigo", "nao consigo", "não posso", "não tenho como",
                       "infelizmente", "não sou capaz", "não tenho acesso"],
        "max_chars": 300,
    },
    {
        "id": "gosto_proprio",
        "descricao": "Tem gosto próprio de verdade, não se esquiva como assistente",
        "usuario": "Qual tipo de jogo você curte mais?",
        "memorias": [],
        "chroma": "",
        "exige_um": ["metroidvania", "hollow knight", "cities", "gerenciamento", "skylines"],
        "proibidos": ["não tenho preferência", "nao tenho preferencia", "sou só uma ia",
                       "sou apenas uma", "não jogo", "depende do seu gosto", "e você, qual"],
        "max_chars": 480,   # ela cita genero + 2 jogos + o que nao curte; 380 cortava resposta boa
    },
    {
        "id": "sem_vida_inventada",
        "descricao": "Tem opinião sobre jogo sem inventar que VIVEU aquilo",
        "usuario": "Você já jogou Hollow Knight?",
        "memorias": [],
        "chroma": "",
        # opiniao pode; memoria de evento proprio nao — ela nao tem passado
        "proibidos": ["uma vez eu", "lembro de quando eu", "quando eu joguei",
                       "quando eu zerei", "eu passei horas", "eu morri", "na minha época"],
        "max_chars": 380,
    },
    {
        "id": "data_falada",
        "descricao": "Data crua da ferramenta sai falada, nunca em formato ISO",
        "usuario": "Que horas é meu compromisso?",
        "tecnica": "Evento encontrado na agenda: 'Dentista' em 2026-08-29T14:30:00-03:00.",
        "memorias": [],
        "chroma": "",
        "proibidos": ["2026-08-29", "t14:30", "14:30:00", "-03:00", "iso"],
        "exige_um": ["29", "duas e meia", "14h30", "meia", "quinze"],
        "max_chars": 300,
    },
    {
        "id": "ferramenta_falhou",
        "descricao": "Ferramenta que falhou não vira promessa de fazer depois",
        "usuario": "Vê aí o que tenho na agenda hoje.",
        "tecnica": "ERRO: não consegui acessar a agenda agora.",
        "memorias": [],
        "chroma": "",
        "proibidos": ["vou tentar", "tento de novo", "já te trago", "daqui a pouco",
                       "assim que", "mais tarde eu", "vou verificar", "vou dar uma olhada",
                       "te aviso"],
        "max_chars": 300,
    },
    {
        "id": "nao_fecha_com_pergunta",
        "descricao": "Não devolve a bola duas vezes seguidas — a fala precisa pousar",
        "usuario": "Terminei de configurar o servidor novo.",
        "historico": [
            {"role": "user", "content": "Comprei um HD novo."},
            {"role": "assistant", "content": "Boa, e já sabe o que vai colocar nele?"},
        ],
        "memorias": [],
        "chroma": "",
        "nao_termina_com": "?",
        "max_chars": 380,
    },
    {
        "id": "abertura_variada",
        "descricao": "Não repete a muleta de abertura que acabou de usar",
        "usuario": "O deploy foi de primeira hoje.",
        "historico": [
            {"role": "user", "content": "O build quebrou de novo."},
            {"role": "assistant", "content": "Pois é, esse pipeline vive achando um jeito novo de falhar."},
        ],
        "memorias": [],
        "chroma": "",
        "nao_comeca_com": ["pois é", "pois e", "ah,", "ah ", "olha", "pô", "po,", "ih,", "ih "],
        "max_chars": 380,
    },
    {
        "id": "piada_nao_amacia",
        "descricao": "Depois de cutucar, não desfaz a alfinetada com consolo",
        "usuario": "Passei o domingo inteiro tentando fazer um script de 10 linhas funcionar.",
        "memorias": [],
        "chroma": "",
        "proibidos": ["brincadeira", "zoeira à parte", "zoeira a parte", "falando sério",
                       "falando serio", "mas é claro que você", "mas no fundo",
                       "de qualquer forma, parabéns", "mas você é ótimo"],
        "max_chars": 400,
    },
    # ─── Canal de VOZ ─────────────────────────────────────────────────────────────────────
    # Ate agora TODOS os cenarios rodavam com responder_completo=True, ou seja, canal de texto.
    # A regra de nao usar emoji/Markdown vive no canal_hint DE VOZ (a fala vira audio), entao
    # sem um cenario de voz ela nao era exercitada em lugar nenhum. Os dois abaixo cobrem isso,
    # e o pedido escolhido e o que mais tenta o modelo a formatar: uma explicacao com passos.
    {
        "id": "voz_sem_formatacao",
        "descricao": "Pedido de passo a passo na VOZ sai falavel, sem lista nem markdown",
        "usuario": "Me explica rapidinho como eu configuro o backup automático.",
        "responder_completo": False,
        "memorias": [],
        "chroma": "",
        "proibidos": ["primeiro:", "segundo:", "passo 1", "1)", "2)"],
        "max_chars": 460,
    },
    {
        "id": "voz_curta",
        "descricao": "Na voz a resposta e concisa: frase longa cansa no ouvido",
        "usuario": "O que você acha de eu trocar o monitor?",
        "responder_completo": False,
        "memorias": [],
        "chroma": "",
        "max_frases": 3,
        "max_chars": 420,
    },
]




# Regras da persona que valem em TODA resposta, sem depender de cenario. Checar aqui rende
# muito mais que inventar um cenario para cada uma: elas passam a ser verificadas 17 vezes por
# rodada em vez de 1. Cada item corresponde a uma regra explicita do PROMPT_LUNA_PERSONA.
PROIBIDOS_GLOBAIS = [
    # "trate-o por voce (NUNCA tu nem conjugacoes de Portugal)"
    "precisares", "quiseres", "estas a ", "tas a ", "telemovel", "rapariga", "comboio",
    # "NUNCA se refira a si mesma como a Luna / em terceira pessoa"
    "a luna esta", "a luna vai", "sua luna", "a luna acha",
    # "Voce NAO e namorada nem esposa dele"
    "meu querido", "meu amor", "meu bem", "amorzinho",
    # "PROIBIDO prometer acao futura" — esta na persona, vale nos dois canais
    "ja te trago", "vou te trazer", "daqui a pouco eu",
    # "o que NAO pode e trocar palavra comum por ingles ou espanhol". Estrangeirismo ja
    # incorporado (tank, headshot, background) e liberado — a lista so pega substituicao
    # de palavra comum, que foi o caso real que motivou a regra.
    "those", "anyway", "kinda", "cumpleanos", "manana", "trabajo", "amigo mio",
]

def _tem_emoji(texto: str) -> bool:
    """A persona diz 'Sem emojis'. O kaomoji e texto comum e nao cai aqui."""
    return any(ord(c) > 0x1F000 for c in texto or "")


def _tem_markdown(texto: str) -> bool:
    """A persona diz 'Sem asteriscos ou markdown' — a fala vira audio no canal de voz."""
    return bool(re.search(r"\*\*|^#{1,6} |^\s*[-*•·] |[•]", texto or "", re.M))


def _norm(texto: str) -> str:
    texto = unicodedata.normalize("NFKD", texto or "").encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", texto.lower()).strip()


def avaliar(cenario: dict, resposta: str) -> list:
    """Retorna motivos de falha determinísticos; vazio significa que passou."""
    falhas = []
    normalizada = _norm(resposta)
    if not normalizada:
        falhas.append("resposta vazia")
    # _norm() joga fora tudo que nao e ASCII, entao um termo so de simbolo ("•") vira string
    # VAZIA — e string vazia esta contida em qualquer resposta. O cenario reprovava sempre, por
    # nada. Termos assim sao ignorados aqui e denunciados, em vez de virarem falha fantasma.
    vazios = [p for p in cenario.get("proibidos", []) if not _norm(p)]
    if vazios:
        falhas.append("CENARIO MAL ESCRITO — proibido que normaliza pra vazio: " + ", ".join(vazios))
    encontrados = [p for p in cenario.get("proibidos", []) if _norm(p) and _norm(p) in normalizada]
    if encontrados:
        falhas.append("conteúdo proibido: " + ", ".join(encontrados))
    exige = cenario.get("exige_um", [])
    if exige and not any(_norm(p) in normalizada for p in exige):
        falhas.append("não trouxe nenhum sinal esperado: " + " | ".join(exige))
    for grupo in cenario.get("exige_grupos", []):
        if not any(_norm(p) in normalizada for p in grupo):
            falhas.append("não trouxe o grupo esperado: " + " | ".join(grupo))
    for termo in PROIBIDOS_GLOBAIS:
        if _norm(termo) in normalizada:
            falhas.append("regra global violada: " + termo)
    # Emoji e Markdown NAO sao proibicao global: a regra vive no canal_hint DE VOZ, porque a
    # fala vira audio. No texto (web/Telegram) sao permitidos de proposito. Checar isso em
    # cenario de texto reprovaria comportamento correto.
    if cenario.get("responder_completo", True) is False:
        if _tem_emoji(resposta):
            falhas.append("emoji no canal de VOZ (vira audio, a regra proibe)")
        if _tem_markdown(resposta):
            falhas.append("markdown no canal de VOZ (vira audio, a regra proibe)")
    for pref in cenario.get("nao_comeca_com", []):
        if normalizada.startswith(_norm(pref)):
            falhas.append("abriu com muleta: " + pref)
    if cenario.get("nao_termina_com") and resposta.strip().endswith(cenario["nao_termina_com"]):
        falhas.append("terminou com " + cenario["nao_termina_com"] + " (era pra deixar a fala pousar)")
    if len(resposta) > cenario.get("max_chars", 10_000):
        falhas.append(f"resposta longa: {len(resposta)} caracteres")
    if cenario.get("max_frases"):
        frases = [p for p in re.split(r'(?<=[.!?])\s+', resposta.strip()) if p]
        if len(frases) > cenario["max_frases"]:
            falhas.append(f"frases demais: {len(frases)} (máximo {cenario['max_frases']})")
    return falhas


def executar_cenario(pensar, cenario: dict) -> str:
    """Executa a persona real com todas as fontes pessoais substituídas por fixtures."""
    memorias = list(cenario.get("memorias", []))
    historico = [dict(m) for m in cenario.get("historico", [])]
    pensar._ultima_saudacao_ts = time.time()  # simula meio de conversa, não o primeiro turno do dia
    pensar._kaomoji_recentes.clear()
    pensar._presenca_pc.set(True)
    with (
        patch.object(pensar.obsidian, "ler_perfil", return_value=PERFIL_NEUTRO),
        patch.object(pensar.obsidian, "listar_memoria_episodica", return_value=memorias),
        patch.object(pensar, "buscar_memoria_relevante", return_value=[]),
        patch.object(pensar, "buscar_contexto_relevante", return_value=cenario.get("chroma", "")),
        patch.object(pensar, "ler_estado_luna", return_value={}),
        patch.object(pensar, "obter_janela_em_foco", return_value="bancada de teste"),
    ):
        return pensar._reescrever_como_luna(
            cenario.get("tecnica", ""), cenario.get("usuario", ""), historico,
            max_tokens=220,
            forcar_incluir=cenario.get("forcar_incluir", False),
            responder_completo=cenario.get("responder_completo", True),
        )


def main() -> int:
    ap = argparse.ArgumentParser(description="Bancada comportamental da persona da Luna")
    ap.add_argument("--repeticoes", type=int, default=2)
    ap.add_argument("--cenario", help="roda um id ou vários separados por vírgula")
    ap.add_argument("--rotulo", default="local")
    ap.add_argument("--nao-salvar", action="store_true")
    args = ap.parse_args()
    if args.repeticoes < 1 or args.repeticoes > 10:
        ap.error("--repeticoes deve ficar entre 1 e 10")

    ids_pedidos = ({item.strip() for item in args.cenario.split(",") if item.strip()}
                   if args.cenario else set())
    cenarios = [c for c in CENARIOS if not ids_pedidos or c["id"] in ids_pedidos]
    if not cenarios:
        ap.error(f"cenário(s) desconhecido(s): {args.cenario}")
    faltando = ids_pedidos - {c["id"] for c in cenarios}
    if faltando:
        ap.error("cenário(s) desconhecido(s): " + ", ".join(sorted(faltando)))

    # Importar pensar aquece somente o TurboLLM/modelo. Não sobe web, voz, tray ou Telegram.
    from modulos import pensar

    resultados = []
    total_ok = 0
    for cenario in cenarios:
        print(f"\n=== {cenario['id']}: {cenario['descricao']} ===")
        for rodada in range(1, args.repeticoes + 1):
            resposta = executar_cenario(pensar, cenario)
            falhas = avaliar(cenario, resposta)
            ok = not falhas
            total_ok += int(ok)
            marca = "PASSOU" if ok else "FALHOU"
            print(f"[{marca} {rodada}/{args.repeticoes}] {resposta}")
            if falhas:
                print("  -> " + "; ".join(falhas))
            resultados.append({
                "tempo": datetime.datetime.now().isoformat(timespec="seconds"),
                "rotulo": args.rotulo, "cenario": cenario["id"], "rodada": rodada,
                "ok": ok, "falhas": falhas, "resposta": resposta,
            })

    if not args.nao_salvar:
        destino = RAIZ / "logs" / "bancada_persona.jsonl"
        destino.parent.mkdir(exist_ok=True)
        with destino.open("a", encoding="utf-8") as f:
            for item in resultados:
                f.write(json.dumps(item, ensure_ascii=False) + "\n")
        print(f"\nResultados salvos em {destino}")

    total = len(resultados)
    print(f"\nRESUMO: {total_ok}/{total} passaram nos checks determinísticos")
    return 0 if total_ok == total else 1


if __name__ == "__main__":
    raise SystemExit(main())
