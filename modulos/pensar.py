#pensar.py

import os
import logging
import threading
import json
import time
import re
import datetime
import subprocess
import contextvars
from openai import OpenAI

_log = logging.getLogger("luna.pensar")
import modelos.cores as cor
from modulos.habilidades import (
    obter_transcricao, adicionar_evento_google, ler_agenda_google,
    obter_previsao_tempo, gerenciador_spotify, pesquisar_na_web,
    enviar_mensagem_whatsapp, checar_emails_nao_lidos, controlar_firefox_via_extensao,
    obter_contexto_navegador, listar_processos_pesados,
    obter_janela_em_foco, analisar_imagem_gemini, capturar_tela_base64, ler_texto_selecionado,
    desenhar_imagem, executar_analise_aba, alternar_mute,
    ler_url_especifica, ler_link_copiado, consultar_overwatch, consultar_jogo_steam,
    duvida_do_jogo, ferramentas_disponiveis, NOME_USUARIO)
from modulos.memoria import (
    buscar_contexto_relevante, salvar_conversa,
    ler_memoria_permanente, analisar_e_salvar_fato, ler_estado_luna,
    buscar_memoria_relevante
)
from modulos.falar import limpar_texto_para_voz, periodo_atual
from modulos.intencao_gameplay import contexto_gameplay_anterior, validar_pedido_gameplay
from modulos import (obsidian, config_env, animes, briefing, pendencias,
                     conclusao_tarefas, anotacoes, autoconhecimento)
from modulos.turbollm_api import (
    erro_modelo_descarregado, listar_biblioteca,
    opcoes_pensamento, recarregar_modelo,
)
import httpx

from modulos import config_env
from modulos import prompts as _prompts

"""
MÓDULO DE PENSAR DA LUNA (MOTOR DE INFERÊNCIA)
---------------------------------------------------------
Responsável por todo o ciclo de raciocínio da Luna: recebe o texto do usuário,
decide se aciona uma ferramenta, executa a ferramenta e gera a resposta final
com personalidade via LLM de persona.

MODO MONO (jul/2026): um único modelo local no TurboLLM faz TUDO: roteia as
ferramentas E gera a resposta com persona. Gemma é o padrão, mas MODELO_LLM permite
testar outra opção sem alterar este arquivo.

Configurações principais (topo do arquivo):
  BASE_LOCAL             — endpoint OpenAI-compatível do TurboLLM (porta 6996)
  MODELO_PERSONA         — modelo padrão quando MODELO_LLM não foi preenchido
  OPCOES_MODELO          — controla o thinking conforme MODELO_THINKING no .env
  ATIVAR_MEMORIA_PERMANENTE — True: extrai e salva fatos sobre o usuário em background
                              False: desativado (ChromaDB de conversas ainda funciona)

Fluxo principal (gerar_resposta):
  1. Busca contexto relevante no ChromaDB (semântica)
  2. Chamada 1: o modelo decide se aciona ferramenta (tool calling) → executa
  3. Chamada 2: o modelo gera a resposta com persona (_reescrever_como_luna)
  4. Salva conversa no ChromaDB
  5. Se ATIVAR_MEMORIA_PERMANENTE: extrai fatos em background (thread separada)

Ferramentas com lógica interna de LLM (definidas aqui, não em habilidades.py):
  _executar_resumir_youtube() — pega URL da aba ativa via extensão Firefox, baixa transcrição
  _executar_resumir_url()     — pega URL do Firefox ou clipboard, faz fetch via ler_url_especifica

Prompts:
  O TEXTO todo mora em modulos/prompts.py, separado por eixo (identidade, emoção, conduta,
  forma, saída) mais os 12 modos enxutos. Aqui fica a LÓGICA: quem escolhe qual prompt, em
  que ordem testa os gatilhos e o que entra como ajuste do turno.
  PROMPT_LUNA_PERSONA — alias de prompts.PERSONA, mantido pelo resto do arquivo.
"""

# Servidor local de inferência: TurboLLM (OpenAI-compatível na porta 6996).
# MODO MONO: um único modelo faz TUDO — roteia ferramentas e gera a persona.
# O Gemma continua sendo o padrão conhecido, mas a escolha explícita vive no .env.
BASE_LOCAL     = "http://127.0.0.1:6996/v1"
# NOME COM ESPAÇOS (não hífens!): é o único formato que o TurboLLM casa na biblioteca
# pra AUTO-CARREGAR (JIT) quando o modelo não está carregado. Com hífens dá 503.
# Assim o idle-unload é seguro: descarregou por ociosidade → a próxima chamada recarrega.
MODELO_PERSONA = "gemma 4 12b it qat"   # faz roteamento (tools) + persona, sozinho
_MARCA_MODELO  = "gemma-4-12b"          # substring p/ conferir qual GGUF o TurboLLM serviu

def _norm(t: str) -> str:
    """Só letras e números, minúsculo. O TurboLLM batiza os modelos com o que veio do arquivo
    — 'gg hf qat_gemma 4 12b it qat q4_0 unquantized|Q4_0|6975878560' — então comparar com
    'gemma-4-12b' na unha nunca casava: hífen contra espaço. Normalizado, casa."""
    return "".join(c for c in (t or "").lower() if c.isalnum())

# ── O ID QUE VAI NO CAMPO `model` ────────────────────────────────────────────────────────
# MODELO_PERSONA acima é só o nome PREFERIDO (o que o JIT do TurboLLM casa). Nem toda versão
# do TurboLLM deixa batizar o modelo: em algumas o id sai do nome do arquivo, e aí o nome com
# espaços nunca casa — foi o que aconteceu na máquina do meu irmão, que teve que carregar o
# modelo na mão antes de abrir a Luna.
# Então, em vez de EXIGIR um nome, a Luna DESCOBRE: pergunta ao /v1/models qual id o TurboLLM
# realmente expõe e passa a usar esse. Se nada estiver carregado, cai no nome preferido (que é
# o que dispara o auto-load). E dá pra cravar um id no .env com MODELO_LLM, pra quem usa outro
# modelo ou outra versão do servidor.
def _preferencia_local_salva() -> tuple[str, str]:
    """Lê só a escolha local antes de o servidor carregar o restante da configuração."""
    caminho = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                           "modelos", "config_luna.json")
    try:
        with open(caminho, encoding="utf-8") as arquivo:
            dados = json.load(arquivo)
        return (str(dados.get("modelo_local") or "").strip(),
                str(dados.get("modelo_thinking") or "desligado").strip())
    except Exception:
        return "", "desligado"


_modelo_local_salvo, _thinking_local_salvo = _preferencia_local_salva()
_modelo_env = config_env.texto("MODELO_LLM")
_modelo_preferencia = _modelo_env or _modelo_local_salvo
_modelo_ativo = _modelo_preferencia   # chave estável; nunca o caminho devolvido pelo engine
_turbollm_pronto = False
_modelo_pronto = False
_ciclo_modelo = 0
_trava_recarregamento = threading.Lock()

def modelo() -> str:
    """Id a mandar no campo `model`. Prefere o que o TurboLLM REALMENTE expõe."""
    return _modelo_ativo or MODELO_PERSONA

# Alguns modelos entendem enable_thinking; outros preferem decidir pelo próprio template.
# O padrão desligado preserva o Gemma atual. "automatico" não envia parâmetro nenhum.
MODO_PENSAMENTO, OPCOES_MODELO = opcoes_pensamento(
    (config_env.texto("MODELO_THINKING", "desligado")
     if _modelo_env else _thinking_local_salvo)
)
# O roteador precisa apenas escolher uma ferramenta. Thinking aqui duplica a latência e pode
# consumir o teto curto antes de emitir o tool call; a escolha do painel vale só para a persona.
OPCOES_ROTEADOR = {"chat_template_kwargs": {"enable_thinking": False}}


def _orcamento_persona(max_tokens: int) -> int:
    """Dá espaço ao raciocínio oculto sem alongar respostas quando thinking está desligado."""
    return max(max_tokens, 3000) if MODO_PENSAMENTO == "ligado" else max_tokens

# True  = analisa conversas e salva fatos na memória permanente em background
# False = desativa completamente (útil enquanto o modelo estiver salvando lixo)
ATIVAR_MEMORIA_PERMANENTE = False

def configurar_memoria(ativo: bool):
    global ATIVAR_MEMORIA_PERMANENTE
    ATIVAR_MEMORIA_PERMANENTE = bool(ativo)


cliente = OpenAI(base_url=BASE_LOCAL, api_key="turbollm")


class GeracaoInterrompida(Exception):
    """Controle de fluxo: o usuário cancelou uma resposta Web ainda em streaming."""


def _recarregar_modelo_esfriado() -> bool:
    """Religa pela API de gerenciamento quando o idle-unload venceu."""
    global _modelo_ativo, _modelo_pronto, _ciclo_modelo
    cor.amarelo("[🧊 O modelo esfriou; pedindo ao TurboLLM para carregá-lo novamente...]")
    resultado = recarregar_modelo(
        BASE_LOCAL,
        configurado=_modelo_preferencia,
        preferido=MODELO_PERSONA,
        marca=_MARCA_MODELO,
    )
    if not resultado["ok"]:
        cor.vermelho(f"[⚠️ O TurboLLM não conseguiu reaquecer o modelo: {resultado['erro']}]")
        return False
    _modelo_ativo = resultado["modelo"]
    _modelo_pronto = True
    _ciclo_modelo += 1
    print(f"[🔥 Modelo recarregado como '{_modelo_ativo}'; repetindo a solicitação]")
    return True


def _chamar_llm(**parametros):
    """Repete uma vez somente quando o TurboLLM confirma que descarregou por ociosidade."""
    ciclo_antes = _ciclo_modelo

    def chamar():
        return cliente.chat.completions.create(model=modelo(), **parametros)

    try:
        return chamar()
    except Exception as erro:
        if not erro_modelo_descarregado(erro):
            raise
        with _trava_recarregamento:
            # Outra thread pode ter recebido o mesmo 503 e terminado o cold-start enquanto
            # esta aguardava a trava. Nesse caso, basta usar o modelo que ela já acordou.
            if ciclo_antes == _ciclo_modelo and not _recarregar_modelo_esfriado():
                raise erro
        return chamar()

def _listar_modelos_turbollm() -> list | None:
    """Ids expostos pelo daemon, ou None quando ele ainda não está respondendo."""
    try:
        r = httpx.get(f"{BASE_LOCAL}/models", timeout=2)
        r.raise_for_status()
        return [m["id"] for m in r.json().get("data", [])]
    except Exception:
        return None


def _iniciar_e_esperar_turbollm(segundos: int = 25) -> list | None:
    """Sobe o daemon oculto pelo launcher do projeto e espera a porta ficar pronta.

    O login do Windows e a Luna podem arrancar quase juntos. Esperar a API evita que
    uma máquina mais lenta receba um falso "TurboLLM desligado" durante o boot.
    """
    launcher = os.path.join(os.path.dirname(os.path.dirname(__file__)), "iniciar_turbollm.vbs")
    if not os.path.isfile(launcher):
        return None
    try:
        subprocess.Popen(
            ["wscript.exe", launcher],
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except Exception as e:
        _log.warning("Não consegui iniciar o TurboLLM: %s", e)
        return None
    limite = time.time() + segundos
    while time.time() < limite:
        time.sleep(0.5)
        ativos = _listar_modelos_turbollm()
        if ativos is not None:
            return ativos
    return None


def garantir_modelo_turbollm():
    # MONO: só precisa do Gemma-4-12B carregado. Ordem: (1) id fixado no .env manda; (2) se o
    # Gemma já está na lista do servidor, adota o id EXATO que ele deu; (3) senão tenta acordar
    # pelo nome preferido (auto-load); (4) falhou, mostra o que o servidor TEM — porque
    # "não carreguei" sem a lista vira adivinhação, que foi o que travou meu irmão.
    global _modelo_ativo, _turbollm_pronto, _modelo_pronto
    _turbollm_pronto = False
    _modelo_pronto = False
    ativos = _listar_modelos_turbollm()
    if ativos is None:
        cor.amarelo("[⏳ TurboLLM não respondeu; tentando iniciar o servidor...]")
        ativos = _iniciar_e_esperar_turbollm()
    if ativos is None:
        cor.vermelho(f"[⚠️ TurboLLM não respondeu em {BASE_LOCAL}. Rode 'turbollm' no CMD e veja o erro.]")
        return
    _turbollm_pronto = True

    if _modelo_preferencia:
        origem = ".env" if _modelo_env else "configurações"
        print(f"[⏳ Pedindo ao TurboLLM pra carregar o modelo escolhido nas {origem}: {_modelo_ativo}...]")
        resultado = recarregar_modelo(
            BASE_LOCAL,
            configurado=_modelo_preferencia,
            preferido=MODELO_PERSONA,
            marca=_MARCA_MODELO,
        )
        if not resultado["ok"]:
            cor.vermelho(f"[⚠️ Não consegui selecionar o modelo escolhido '{_modelo_ativo}' "
                         f"({resultado['erro']})]")
            cor.amarelo("[   Confira a escolha nas configurações ou MODELO_LLM no .env.]")
            return
        _modelo_ativo = resultado["modelo"]
        try:
            w = cliente.chat.completions.create(
                model=_modelo_ativo, messages=[{"role": "user", "content": "oi"}],
                max_tokens=1, extra_body=OPCOES_MODELO, timeout=60)
            # O llama-server devolve o CAMINHO do GGUF em `w.model`. Esse caminho funciona
            # enquanto o processo está quente, mas não é uma chave da biblioteca: após o
            # idle-unload o gateway responde "No model matching <caminho>". Preserve a chave
            # estável escolhida pela API de gerenciamento.
            _modelo_pronto = True
            print(f"[✅ Modelo carregado no TurboLLM como '{_modelo_ativo}']")
        except Exception as e:
            cor.vermelho(f"[⚠️ O modelo '{_modelo_ativo}' carregou, mas não respondeu ao teste ({e})]")
            cor.amarelo("[   Confira a escolha nas configurações ou MODELO_LLM no .env.]")
        return

    # MODELO_LLM vazio significa voltar ao padrão, não "usar o que ficou carregado no
    # último teste". A API de gerenciamento permite fazer isso mesmo com autoSwap desligado.
    padrao = recarregar_modelo(
        BASE_LOCAL,
        preferido=MODELO_PERSONA,
        marca=_MARCA_MODELO,
        aceitar_atual=False,
    )
    if padrao["ok"]:
        _modelo_ativo = padrao["modelo"]
        try:
            w = cliente.chat.completions.create(
                model=_modelo_ativo, messages=[{"role": "user", "content": "oi"}],
                max_tokens=1, extra_body=OPCOES_MODELO, timeout=60)
            # Não adota w.model: nessa engine ele pode ser o caminho local do GGUF, que
            # deixa de ser roteável assim que o modelo é descarregado por ociosidade.
            _modelo_pronto = True
            print(f"[✅ Modelo padrão carregado no TurboLLM como '{_modelo_ativo}']")
            return
        except Exception as e:
            cor.amarelo(f"[⚠️ A seleção automática do modelo padrão não respondeu ({e}); "
                        "tentando a descoberta compatível...]")

    # Achou o Gemma na lista? Usa o id EXATO que o servidor deu, seja ele qual for.
    # O TurboLLM expõe cada modelo DUAS vezes (o id e uma cópia com prefixo 'claude-'), então
    # a escolha não pode depender da ordem da lista: prefere o sem prefixo, e o mais curto.
    alvo = _norm(_MARCA_MODELO)
    candidatos = sorted((a for a in ativos if alvo in _norm(a)),
                        key=lambda a: (a.lower().startswith("claude-"), len(a)))
    casou = candidatos[0] if candidatos else None
    if casou:
        _modelo_ativo = casou
        _modelo_pronto = True
        print(f"[✅ Gemma-4-12B já carregado no TurboLLM como '{casou}']")
        return

    print(f"[⏳ Pedindo ao TurboLLM pra carregar {MODELO_PERSONA}...]")
    try:
        w = cliente.chat.completions.create(
            model=MODELO_PERSONA, messages=[{"role": "user", "content": "oi"}],
            max_tokens=1, extra_body=OPCOES_MODELO)
        servido = _norm(w.model)
        if _norm(_MARCA_MODELO) in servido:
            _modelo_ativo = w.model            # o auto-load funcionou: fica com o id real
            _modelo_pronto = True
            print(f"[✅ Gemma-4-12B carregado como '{w.model}']")
        else:
            cor.vermelho(f"[⚠️ TurboLLM serviu '{w.model}' em vez do Gemma-4-12B. "
                         f"Carregue o Gemma 4 12B QAT na tela Models do TurboLLM.]")
    except Exception as e:
        # Mensagem que RESOLVE: mostra o que o servidor tem, pra não virar adivinhação.
        cor.vermelho(f"[⚠️ Não consegui carregar o Gemma pelo nome '{MODELO_PERSONA}' ({e})]")
        if ativos:
            cor.amarelo(f"[   O TurboLLM está expondo: {', '.join(ativos)}]")
            cor.amarelo(f"[   Se um desses é o Gemma, ponha no .env:  MODELO_LLM=<o id exato>]")
        else:
            cor.amarelo("[   Nenhum modelo carregado. Abra a tela Models do TurboLLM e "
                        "carregue o Gemma 4 12B QAT — em algumas versões não dá pra "
                        "renomear, e aí o auto-load por nome não funciona.]")


def estado_turbollm() -> dict:
    """Estado já apurado no warm-up; não faz nova chamada nem tenta carregar nada."""
    return {"servidor": _turbollm_pronto, "modelo": _modelo_pronto,
            "modelo_id": modelo() if _modelo_pronto else "",
            "thinking": MODO_PENSAMENTO}


def estado_seletor_modelos() -> dict:
    """Estado público do seletor web; não expõe caminhos locais dos GGUFs."""
    biblioteca = listar_biblioteca(BASE_LOCAL)
    biblioteca.update({
        "selecionado": _modelo_preferencia,
        "thinking": MODO_PENSAMENTO,
        "bloqueado_env": bool(_modelo_env),
    })
    return biblioteca


def trocar_modelo_local(chave: str, thinking: str = "desligado") -> dict:
    """Troca o cérebro em tempo de execução quando o .env não fixou uma escolha."""
    global _modelo_preferencia, _modelo_ativo, _modelo_pronto
    global _ciclo_modelo, MODO_PENSAMENTO, OPCOES_MODELO
    if _modelo_env:
        return {"ok": False, "erro": "MODELO_LLM está preenchido no .env"}

    chave = str(chave or "").strip()
    novo_modo, novas_opcoes = opcoes_pensamento(thinking)
    with _trava_recarregamento:
        resultado = recarregar_modelo(
            BASE_LOCAL,
            configurado=chave,
            preferido=MODELO_PERSONA,
            marca=_MARCA_MODELO,
            aceitar_atual=bool(chave),
        )
        if not resultado["ok"]:
            return resultado
        chave_estavel = resultado["modelo"]
        try:
            cliente.chat.completions.create(
                model=chave_estavel,
                messages=[{"role": "user", "content": "oi"}],
                max_tokens=1, extra_body=novas_opcoes, timeout=60,
            )
        except Exception as erro:
            return {"ok": False, "erro": f"o modelo carregou, mas não respondeu: {erro}"}

        _modelo_preferencia = chave
        _modelo_ativo = chave_estavel
        _modelo_pronto = True
        MODO_PENSAMENTO = novo_modo
        OPCOES_MODELO = novas_opcoes
        _ciclo_modelo += 1
        print(f"[🧠 Modelo trocado para '{_modelo_ativo}' (thinking: {MODO_PENSAMENTO})]")
        return {"ok": True, "modelo": _modelo_ativo, "thinking": MODO_PENSAMENTO}

def aquecer_modelo():
    """Cutucão mínimo (max_tokens=1) que RESETA o idle-unload do TurboLLM — mantém o
    modelo quente. Usado durante a partida de LoL pra o comentário de morte sair na hora
    (senão cada fala paga cold-start de ~15s). Silencioso e barato."""
    try:
        _chamar_llm(
            messages=[{"role": "user", "content": "oi"}],
            max_tokens=1, extra_body=OPCOES_MODELO, timeout=8)
    except Exception:
        pass

garantir_modelo_turbollm()


# ==========================================
# Ferramentas com lógica interna de LLM
# ==========================================

def _executar_resumir_youtube(url=None):
    # Se o usuário mandou uma URL (ex: pelo Telegram), usa ela; senão pega da aba ativa do Firefox (voz no PC).
    if url and url.strip():
        url_atual = url.strip()
    else:
        url_atual = controlar_firefox_via_extensao("obter_url")
        if "Erro:" in url_atual:
            return url_atual
    if "youtu" not in url_atual:
        return f"SISTEMA: Isso não parece um link do YouTube (URL: {url_atual})."

    cor.amarelo(f"[Luna baixando transcrição: {url_atual}]")
    transcricao = obter_transcricao(url_atual)
    if transcricao.startswith("ERRO"):
        return f"SISTEMA: Não consegui pegar a transcrição (o vídeo pode não ter legenda). {transcricao}"
    # Fetch-only: devolve a transcrição crua. Quem resume/transforma é a persona (ver gerar_resposta).
    return transcricao


def _executar_resumir_url(url=None):
    # Se o usuário mandou um link (ex: pelo Telegram), usa ele; senão pega do Firefox e, por fim, do clipboard.
    if url and url.strip().startswith("http"):
        url = url.strip()
    else:
        url = controlar_firefox_via_extensao("obter_url")
        if "Erro:" in url or not url.startswith("http"):
            url = ler_link_copiado().strip()
    if not url.startswith("http"):
        return "SISTEMA: Nenhuma URL válida encontrada na aba ativa nem no clipboard. LUNA, peça ao usuário para copiar o link ou abrir o site no Firefox."

    cor.amarelo(f"[Luna lendo site: {url}]")
    conteudo = ler_url_especifica(url)
    if conteudo.startswith("Erro"):
        return conteudo
    # Fetch-only: devolve o conteúdo cru. Quem resume/transforma é a persona.
    return conteudo


def _executar_ler_obsidian(assunto=""):
    # Fetch-only: acha a nota no vault e devolve o conteúdo cru; a persona processa.
    return obsidian.buscar_nota(assunto)

def _executar_salvar_obsidian(conteudo="", titulo="", origem=""):
    # Create-only em Luna/Inbox. A confirmação é determinística (ver gerar_resposta) —
    # não passa pela persona, então é rápida e à prova do modelo inventar bobagem.
    return obsidian.salvar_nota(conteudo, titulo or None, origem)


def _executar_registrar_rotina_jogo(nome_jogo="", estado_jogo="", opiniao="", platinado=None):
    from modulos import rotina_jogos
    return rotina_jogos.registrar_declaracao(
        nome_jogo, estado_jogo, opiniao, platinado=platinado)


def _executar_consultar_proprio_codigo(assunto=""):
    return autoconhecimento.consultar(assunto)


def _executar_propor_acompanhamento(assunto="", perguntar_em=""):
    from modulos import acompanhamentos
    origem = "pc" if _presenca_pc.get() else "telegram"
    return acompanhamentos.propor(assunto, perguntar_em, origem)

# Detecta "anota/salva/..." no começo da mensagem e extrai o conteúdo (texto ORIGINAL,
# fiel — não a reprodução do roteador 4B, que mangla textos longos).
_RE_INICIO_SALVAR = re.compile(
    r'^\s*(anota|salva|registra|guarda|arquiva|'
    r'(escreve|grava|aponta|coloca)\w*(?=\s+(?:isso|a[íi]|aqui|pra\s+mim|nas?\s+notas?|no\s+obsidian))|'
    r'toma\s+nota|lembra(r)?(\s+que)?)\b', re.IGNORECASE)
# Intenção EXPLÍCITA de anotar (em qualquer lugar da fala) — usada como guard: o roteador
# às vezes fira salvar_obsidian num comentário casual ('vou fazer a VM pendente'). Sem uma
# destas palavras, não salva (avaliação 👎: salvou algo que já estava no perfil).
_RE_INTENCAO_SALVAR = re.compile(
    r'\b(anota\w*|salva\w*|registra\w*|guarda\w*|arquiva\w*|'
    r'(?:escreve|grava|aponta|coloca)\w*\s+(?:isso|a[íi]|aqui|pra\s+mim|nas?\s+notas?|no\s+obsidian)|'
    r'toma\s+nota|lembra\w*|'
    r'anot[ae]|not[ae]\s+a[íi]|não\s+esque[çc]\w*|nao\s+esque[çc]\w*)\b', re.IGNORECASE)
# Pergunta que se refere a uma anotação PESSOAL do usuário (posse). Quando o ler_obsidian
# não acha nota relevante: se É pessoal → honesto ("não tenho isso anotado"); se NÃO é
# (pergunta de conhecimento geral, ex: "receita de mousse") → responde do que ela sabe.
_RE_REF_NOTA_PESSOAL = re.compile(
    r'\b(anotei|salvei|guardei|minhas?\s+(notas?|anota\w*)|meu\s+obsidian|na\s+minha\s+nota|'
    r'que\s+eu\s+(salvei|anotei|guardei)|nas\s+minhas\s+anota\w*)\b', re.IGNORECASE)
_RE_DECLARACAO_JOGO = re.compile(
    r'\b(zerei|terminei|finalizei|platin\w*|desisti|abandonei|estou\s+jogando|comecei\s+a\s+jogar|'
    r'gostei|curti|(?:estou|t[oô])\s+gostando|gostando|n[aã]o\s+(?:estou\s+)?gostando|'
    r'n[aã]o\s+gostei|n[aã]o\s+curti|achei)\b', re.IGNORECASE)
_RE_AUTOCONHECIMENTO = re.compile(
    r'\b(luna|voc(?:ê|e)|seu|sua|teu|tua|próprio\s+código|proprio\s+codigo|por\s+dentro)\b',
    re.IGNORECASE,
)


def _conteudo_para_anotar(prompt):
    return anotacoes.dados_para_anotar(prompt)[0]


def _dados_para_anotar(prompt: str, titulo_modelo: str = "") -> tuple[str, str]:
    """Extrai o envelope humano sem resumir nem parafrasear o conteúdo real."""
    return anotacoes.dados_para_anotar(prompt, titulo_modelo)

def _so_comando_salvar(prompt: str) -> bool:
    """True se o pedido é só reação/comando/referência (ex: 'boa ideia, deixa anotado')
    — aí o conteúdo real está na mensagem anterior, não no comando."""
    return anotacoes.pedido_anaforico(prompt)


def _origem_salvamento(responder_completo: bool) -> str:
    return anotacoes.origem(responder_completo, _presenca_pc.get())

def _ultima_fala_do_historico(historico, prompt_atual) -> str:
    """O que 'anota isso' referencia: a última troca substancial, sem o comando atual."""
    return anotacoes.contexto_anterior(historico, prompt_atual)

def _confirmar_salvamento(res, conteudo, prompt_usuario, historico, max_tokens,
                          responder_completo, ao_fragmento=None):
    """Confirma um save de nota: salvou → a persona confirma COMENTANDO o assunto (rico),
    já sabendo que guardou — não pode mentir, o save já é fato. Falhou → mensagem honesta."""
    if not res.startswith("SISTEMA: Nota salva"):
        return "Hmm, não consegui anotar isso. Tenta de novo, ou cola direto no Obsidian?"
    tarefa = ("Você ACABOU de guardar esta anotação nas notas dele (Obsidian) — já está salva. "
              "Confirme que guardou, de forma curta e natural, e faça um comentário leve sobre o "
              "ASSUNTO da nota, se couber. Não invente que fez outra coisa além de guardar.")
    return _reescrever_como_luna(conteudo, prompt_usuario, historico, max_tokens,
                                 tarefa_documento=tarefa, responder_completo=responder_completo,
                                 ao_fragmento=ao_fragmento)

# FONTE ÚNICA das capacidades reativas (o que ela faz A PEDIDO). Usada em DOIS lugares —
# a ferramenta listar_capacidades (quando ele pergunta 'o que você faz') e o PROMPT da persona
# (pra ela nunca NEGAR uma capacidade). Adicionou ferramenta nova? Atualiza SÓ aqui.
_CAPACIDADES_REATIVAS = _prompts.CAPACIDADES_REATIVAS   # texto em modulos/prompts.py

def _listar_capacidades():
    return (
        f"O que consigo fazer: {_CAPACIDADES_REATIVAS}. "
        "E por conta própria (proativo): comento quando você abre ou fecha seus jogos (Steam, Overwatch, LoL), "
        "aviso promoção na sua wishlist da Steam, acompanho seus feeds RSS e anoto as novidades no Obsidian, "
        "e te dou bom dia com agenda, emails e clima."
    )

FUNCOES_DISPONIVEIS = {
    "listar_capacidades": _listar_capacidades,
    "resumir_youtube": _executar_resumir_youtube,
    "resumir_site": _executar_resumir_url,
    "adicionar_agenda": adicionar_evento_google,
    "controlar_spotify": gerenciador_spotify,
    "pesquisar_web": pesquisar_na_web,
    #"enviar_whatsapp": enviar_mensagem_whatsapp,
    "checar_emails": checar_emails_nao_lidos,
    "controlar_navegador": controlar_firefox_via_extensao,
    "analisar_aba_atual": executar_analise_aba,
    "listar_processos_pesados": listar_processos_pesados,
    "ver_tela": capturar_tela_base64,
    "ler_selecionado": ler_texto_selecionado,
    "desenhar_imagem": desenhar_imagem,
    "ler_agenda_google": ler_agenda_google,
    "obter_clima": obter_previsao_tempo,
    "alternar_mute": alternar_mute,
    "consultar_overwatch": consultar_overwatch,
    "consultar_animes": animes.consultar,
    "briefing_diario": briefing.consultar,
    "consultar_pendencias": pendencias.consultar,
    "concluir_tarefa_obsidian": conclusao_tarefas.propor,
    "consultar_jogo_steam": consultar_jogo_steam,
    "duvida_do_jogo": duvida_do_jogo,
    "ler_obsidian": _executar_ler_obsidian,
    "salvar_obsidian": _executar_salvar_obsidian,
    "registrar_rotina_jogo": _executar_registrar_rotina_jogo,
    "consultar_proprio_codigo": _executar_consultar_proprio_codigo,
    "propor_acompanhamento": _executar_propor_acompanhamento,
}


# ==========================================
# LLM PERSONA
# ==========================================

# O texto da persona mora em modulos/prompts.py, separado por eixo (identidade, emoção,
# conduta, forma, saída). O alias mantém o nome usado no resto do arquivo e nos testes.
PROMPT_LUNA_PERSONA = _prompts.PERSONA

# O clima vira ROSTO aqui no Python, não no modelo (ideia do Fábio, ago/2026). O 12B só escolhe
# uma PALAVRA — tarefa trivial, que ele já fazia bem no tempo do [gif:]. Deixar ele escrever o
# kaomoji dava: carinha quebrada ('= कर_ω_', devanágari), parênteses de volta, 4 formatos
# diferentes e vício nas 3 caras mais comuns do treino. Agora a saída é sempre válida.
# CURADORIA (ago/2026): a cara é desenhada INTEIRA, como uma string só. Chegamos a tentar
# separar olho e boca (boca vetorial, depois glifo de 2-3 quadros) e as duas tentativas foram
# abortadas — ver TODO.md, seção "Decidido NÃO fazer". O que ficou da tentativa foi esta poda:
# saíram as caras cujos "olhos" não se sustentavam sozinhos — acento combinante solto
# (•̀ ᴗ -, ╭ರ_•́), dois acentos no lugar de olhos (´ཀ`) e três curvas sem olho nenhum (︶︹︺).
# Nenhum clima ficou sem cara. Quem pisca e quem não pisca: NAO_PISCA no Index.html.
_ROSTOS = {
    "zoeira":   ["ᗒᗜᗕ"],
    "revolta":  ["Ò﹏Ó"],
    "facepalm": ["ಠ_ಠ"],
    "choque":   ["O_O"],
    "carinho":  ["ᵔ ᵕ ᵔ"],
    "cansaco":  ["╥‸╥", "◞_◟"],
    "festa":    ["◉‿◉"],
    "orgulho":  ["ꈍ◡ꈍ"],
    "suspeita": ["ㆆ_ㆆ", "≖_≖"],
    "duvida":   ["⚈₋⚈"],
    "tedio":    ["￢_￢"],
    "tristeza": ["T_T"],
}

# O Telegram lê _kaomoji_pendente e cola o rosto no fim do texto; no web ele vai grande,
# dentro do círculo (que é a cabeça dela).
import random as _rnd
_kaomoji_recentes = []
_kaomoji_pendente = None
_clima_da_resposta = contextvars.ContextVar("clima_da_resposta", default="")

_RE_CLIMA = re.compile(r'\[\s*clima\s*:\s*([A-Za-zÀ-ÿ]+)\s*\]', re.IGNORECASE)

def _sem_acento_min(s: str) -> str:
    import unicodedata
    s = unicodedata.normalize("NFKD", s or "")
    return "".join(c for c in s if not unicodedata.combining(c)).lower()

_ROSTOS_NORM = {_sem_acento_min(k): v for k, v in _ROSTOS.items()}

# Sobra de kaomoji no fim da fala: mesmo com a tag [clima:X], o 12B às vezes solta um
# pedaço de carinha por conta própria (resquício do treino) — vazou um 'ω' solto pro TEXTO
# e pra VOZ. Tira um rabicho CURTO de caracteres que não são letra latina/número/pontuação,
# e só quando ele vem separado por espaço (pra não comer o fim de uma palavra).
_RE_LIXO_FIM = re.compile(r'(?<=[\s.!?…])[^A-Za-zÀ-ÿ0-9.,!?;:%()\[\]"\'\s…-]{1,14}\s*$')

def _limpar_sobra_kaomoji(t: str) -> str:
    novo = _RE_LIXO_FIM.sub('', t or '').rstrip()
    if novo != (t or '').rstrip():
        cor.cinza(f"[🧹 Sobra de kaomoji removida do fim da fala]")
    return novo


def _extrair_clima(texto: str):
    """Tira o [clima:X] do fim -> (rosto|None, clima, texto_limpo). O Python escolhe o
    rosto: sempre um do grupo daquele clima, evitando os usados há pouco (variedade
    garantida sem depender da obediência do modelo)."""
    t = texto or ""
    m = _RE_CLIMA.search(t)
    if not m:
        _clima_da_resposta.set("")
        return None, "", _limpar_sobra_kaomoji(t)  # sem tag, ainda pode ter sobrado carinha
    t = _limpar_sobra_kaomoji(_RE_CLIMA.sub("", t).strip())
    clima = _sem_acento_min(m.group(1))
    faces = _ROSTOS_NORM.get(clima)
    if not faces:                                   # inventou um clima fora da lista
        _clima_da_resposta.set("")
        cor.vermelho(f"[⚠️ Clima desconhecido: {m.group(1)!r}]")
        return None, "", t
    # Evita os 3 últimos; se o grupo é pequeno e todos já saíram, garante ao menos não
    # repetir o IMEDIATAMENTE anterior (senão dava '╥‸╥ ╥‸╥' seguido em grupo de 3).
    ultimo = _kaomoji_recentes[-1] if _kaomoji_recentes else None
    recentes = set(_kaomoji_recentes[-3:])
    novas = ([f for f in faces if f not in recentes]
             or [f for f in faces if f != ultimo]
             or faces)
    _clima_da_resposta.set(clima)
    return _rnd.choice(novas), clima, t


def obter_clima_resposta() -> str:
    """Clima da resposta gerada nesta thread, sem depender do timing dos broadcasts."""
    return _clima_da_resposta.get()

def obter_e_limpar_kaomoji():
    """Pega e LIMPA o kaomoji da última resposta (o Telegram cola no texto). str ou None."""
    global _kaomoji_pendente
    k = _kaomoji_pendente
    _kaomoji_pendente = None
    return k

# Anti-"boa noite" em toda resposta: o prompt sozinho não segura (o 12B não sabe
# o que é "primeiro contato"). Rastreamos QUANDO a Luna cumprimentou por último e,
# se foi há menos de _JANELA_SAUDACAO_H horas, o prompt PROÍBE saudar de novo.
_ultima_saudacao_ts = 0.0
_JANELA_SAUDACAO_H = 6
_RE_SAUDACAO = re.compile(r'\b(bom dia|boa tarde|boa noite|ol[áa])\b|(?:^|[.!?]\s*)oi\b', re.IGNORECASE)

# Imagem produzida por uma ferramenta para canais que enviam mídia (ex: Telegram).
# Só é populada quando responder_completo=True, evitando vazamento entre canais (voz/web não usam).
_imagem_pendente = None

def obter_e_limpar_imagem_pendente():
    """Retorna {'tipo': 'b64'|'url', 'dado': str} da última ferramenta visual e limpa o buffer."""
    global _imagem_pendente
    img = _imagem_pendente
    _imagem_pendente = None
    return img


def frase_confirmacao(instrucao: str, max_tokens: int = 120) -> str:
    """UMA fala curta da Luna a partir de uma instrução direta (sem ferramentas nem histórico).
    Usada por fluxos determinísticos (ex: arquivar foto no Obsidian) pra confirmação sair
    com a voz da persona em vez de frase pronta em Python. Retorna '' se o LLM falhar —
    o chamador deve ter um fallback."""
    try:
        r = _chamar_llm(
            messages=[
                {"role": "system", "content": PROMPT_LUNA_PERSONA},
                {"role": "user", "content": instrucao},
            ],
            temperature=0.65,
            max_tokens=max_tokens,
            extra_body=OPCOES_MODELO,
        )
        texto = (r.choices[0].message.content or "").strip()
        texto = re.sub(r'\[gif:[^\]]*\]', '', texto).strip()   # este fluxo não usa o GIF
        if texto.startswith("Luna:"):
            texto = texto[5:].lstrip()
        return texto
    except Exception as e:
        _log.warning(f"frase_confirmacao falhou: {e}")
        return ""


# Trava anti-estouro de contexto (o modelo tem n_ctx=8192): trunca cada mensagem do
# histórico e pega só as N últimas, pra um arquivo colado/nota gigante não inflar o prompt.
def _hist_curto(historico: list, n: int, cap: int = 1500) -> list:
    return [{"role": m.get("role", "user"), "content": str(m.get("content", ""))[:cap]}
            for m in historico[-n:]]


def _recentes_diretamente_relacionadas(prompt: str, itens: list) -> list:
    """Mantém no bloco recente só fatos com ligação textual concreta ao assunto atual.

    Sinônimos continuam cobertos pelo retrieval multilíngue; recência sozinha não pode
    transformar todo fato recente em assunto disponível para a persona puxar.
    """
    if not prompt or not prompt.strip():
        return []
    return [(data, fato) for data, fato in itens
            if obsidian.avaliar_relevancia(prompt, fato, minimo=0.34)]


import contextvars as _cv
# Presença física do usuário: True = no PC (voz/web), False = fora (Telegram, provável celular).
# ContextVar é thread-safe: voz, Telegram e web (threads diferentes) não se atropelam.
_presenca_pc = _cv.ContextVar("presenca_pc", default=True)

def _reescrever_como_luna(resposta_tecnica: str, prompt_usuario: str, historico: list,
                          max_tokens=300, forcar_incluir=False, responder_completo=False,
                          tarefa_documento=None, ao_fragmento=None) -> str:
    global _ultima_saudacao_ts, _kaomoji_pendente
    _clima_da_resposta.set("")
    resposta_tecnica = re.sub(r'<think>.*?</think>', '', resposta_tecnica, flags=re.DOTALL).strip()

    data_hoje = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
    memoria_permanente = obsidian.ler_perfil() or ler_memoria_permanente()   # perfil.md é o núcleo
    # Memória episódica em 2 fatias: RECENTES (continuidade) + RELEVANTES ao assunto
    # (recall por tema, mesmo antigo — v2). O relevante exclui o que já vai no recente.
    _mem_recentes_todas = obsidian.listar_memoria_episodica()[:15]
    _mem_recentes = _recentes_diretamente_relacionadas(prompt_usuario, _mem_recentes_todas)
    memoria_episodica = "\n".join(obsidian.fmt_memoria(d, f) for d, f in _mem_recentes)
    _mem_relevantes = (buscar_memoria_relevante(prompt_usuario, excluir={f for _, f in _mem_recentes})
                       if prompt_usuario else [])
    memoria_relacionada = "\n".join(obsidian.fmt_memoria(d, f) for d, f in _mem_relevantes)
    # Proativo já recebe seu fato completo; recall paralelo só contamina e consultar com texto
    # vazio ainda faria embedding sem qualquer benefício.
    contexto_db = buscar_contexto_relevante(prompt_usuario) if prompt_usuario else ""
    # Em recado curto, um match vetorial fraco é mais perigoso que útil: foi assim que
    # "vou comprar comida" recebeu uma história aleatória sobre SQL. Conversa desenvolvida
    # preserva o recall semântico mesmo quando usa palavras diferentes.
    if (contexto_db and len((prompt_usuario or "").split()) <= 8
            and not obsidian.avaliar_relevancia(prompt_usuario, contexto_db, minimo=0.34)):
        contexto_db = ""
    if contexto_db and len(contexto_db) > 2000:        # anti-estouro: nota/conversa gigante
        contexto_db = contexto_db[:2000] + " […]"

    # Diagnóstico opcional: quanto cada bloco de memória ocupa no prompt da Chamada 2 —
    # pra decidir COM DADO o que enxugar (recentes fixos vs ChromaDB). Liga de 2 jeitos:
    # env var LUNA_DIAG_PROMPT=1, OU criando o arquivo modelos/diag_prompt.flag (sem terminal).
    if os.getenv("LUNA_DIAG_PROMPT") or os.path.exists("modelos/diag_prompt.flag"):
        _blocos = [("perfil", memoria_permanente), ("recentes", memoria_episodica),
                   ("relacionada", memoria_relacionada), ("chromadb", contexto_db or "")]
        _det = " · ".join(f"{n} {len(t)}c≈{len(t)//4}tok" for n, t in _blocos if t)
        _tot = sum(len(t) for _, t in _blocos)
        cor.cinza(f"[📏 Chamada 2 — memória: {_det} · TOTAL {_tot}c≈{_tot//4}tok]")

    estado = ler_estado_luna()
    programa_em_uso = estado.get("programa_atual") or obter_janela_em_foco()
    horas_sessao = estado.get("horas_na_sessao", 0)
    jogo_ativo = estado.get("jogo_ativo")

    partes_situacao = []
    if not _presenca_pc.get():
        # Ele está falando pelo CELULAR (Telegram): o estado do PC é irrelevante e ENGANA
        # (dizer "Programa em uso: firefox" faz a Luna achar que ele está sentado no PC).
        contexto_situacional = ("ELE NÃO ESTÁ NO COMPUTADOR — está te escrevendo pelo CELULAR, longe do PC "
                                "(pode estar na rua, no trabalho ou em outro cômodo). LOGO: é IMPOSSÍVEL pra ele "
                                "mexer no PC agora — NÃO sugira nem pergunte se ele vai programar, revisar código, "
                                "mexer no Colibri/sistema, jogar ou olhar a tela. Qualquer sugestão sua tem que "
                                "caber no celular ou fora de casa")
    else:
        if jogo_ativo:
            partes_situacao.append(f"MODO GAMER ATIVO — jogo: {jogo_ativo}")
        else:
            partes_situacao.append("MODO NORMAL")
        partes_situacao.append(f"Programa em uso: {programa_em_uso}")
        if horas_sessao > 0.1:
            partes_situacao.append(f"sessão ativa há {horas_sessao:.1f}h")
        programa_desde = estado.get("programa_desde")
        if programa_desde and programa_em_uso:
            mins = (time.time() - programa_desde) / 60
            if mins >= 1:
                label = f"{int(mins)}min" if mins < 60 else f"{mins / 60:.1f}h"
                partes_situacao.append(f"há {label} nesse programa")
        contexto_situacional = " | ".join(partes_situacao)

    # Já cumprimentou nas últimas horas? Então é PROIBIDO saudar de novo (determinístico).
    aviso_saudacao = ""
    if _ultima_saudacao_ts and (time.time() - _ultima_saudacao_ts) < _JANELA_SAUDACAO_H * 3600:
        aviso_saudacao = (
            "\n- ATENÇÃO: você JÁ cumprimentou o usuário há pouco. PROIBIDO qualquer saudação agora "
            "('boa noite', 'bom dia', 'boa tarde', 'oi', 'olá') — comece a resposta DIRETO no assunto."
        )

    # Comprimento e formatação pelo canal: voz vira áudio; Web digitado e Telegram são texto.
    canal_hint = _prompts.CANAL_TEXTO if responder_completo else _prompts.CANAL_VOZ

    # Tom da voz (SER acústico) — SÓ no canal de voz. Palpite SUTIL que colore o COMO.
    dica_tom = ""
    if not responder_completo:
        try:
            from modulos import tom as _tom
            _th = _tom.obter_hint()
            if _th:
                dica_tom = ("\n- TOM DE VOZ (sinal SUTIL do áudio, PODE errar — trate como PALPITE que "
                            "COLORE o jeito de responder; NÃO comente isso diretamente a não ser que caiba "
                            f"muito natural, e NUNCA vire bordão): {_th}")
        except Exception:
            pass

    # Presença: voz/web = no PC; Telegram = provavelmente fora (não sugerir tarefa de PC).
    presenca_hint = ("" if _presenca_pc.get() else
        "\n- ONDE ELE ESTÁ: ele provavelmente NÃO está no computador agora (te falando pelo celular / fora de casa). "
        "NÃO sugira nada que dependa do PC (abrir/revisar um programa, olhar a tela, mexer no sistema) — ele não "
        "pode fazer isso agora. Se for sugerir algo, que dê pra fazer no celular ou na cabeça.")

    # Anti-repetição do kaomoji: proíbe explicitamente os últimos usados (o modelo sozinho vicia)
    aviso_kaomoji = ""
    if _kaomoji_recentes:
        aviso_kaomoji = ("\n- KAOMOJI: você acabou de usar estes — escolha um DIFERENTE agora: "
                         + "   ".join(_kaomoji_recentes[-3:]))

    aviso_referencia = ""
    referencia_sem_nome = False
    if re.search(r'\b(qual|quem|que jogo|nome (?:dele|dela|disso))\b', prompt_usuario or "",
                 re.IGNORECASE):
        ultima_assistente = next(
            (str(m.get("content", "")) for m in reversed(historico or [])
             if m.get("role") == "assistant"), "")
        referencia_sem_nome = bool(re.search(
            r'\b(?:aquele|esse|um) jogo(?: novo)?\s*[?.!]*$|\b(?:isso|aquilo)\s*[?.!]*$',
            ultima_assistente, re.IGNORECASE))
        aviso_referencia = (
            "\n- REFERÊNCIA PEDIDA: só dê nome/identidade se ela estiver ESCRITA explicitamente "
            "na mensagem, histórico, memória relacionada ou resultado atual. Se você mesma falou "
            "'aquele jogo/isso' sem registrar o nome, admita que foi vaga e que não tem o nome — "
            "NUNCA preencha a lacuna com backlog, Steam ou um palpite."
        )

    aviso_cotidiano = ""
    if re.search(
        r'^\s*(?:eu\s+)?(?:vou|tô indo|estou indo)\s+(?:comprar|comer|buscar|tomar|dormir|sair)\b',
        prompt_usuario or "", re.IGNORECASE,
    ):
        aviso_cotidiano = (
            "\n- MOMENTO COTIDIANO PEQUENO: reaja só à ação literal que ele contou, de forma "
            "curta, viva e com personalidade de sobra. Uma alfinetada AFIADA está liberada quando "
            "nascer da própria ação ou escolha que ele acabou de contar; mire a situação, não o caráter "
            "dele. Curiosidade genuína ou uma pergunta curta também estão liberadas. Não presuma "
            "que é repetição: PROIBIDO 'de novo', 'dessa vez', 'outro', 'mais um', "
            "'terceiro' e qualquer coisa que sugira que isso já aconteceu antes — você não "
            "tem esse dado. Não invente "
            "preguiça, impulso, falta de autocontrole, compromisso pendente ou motivo oculto. "
            "Pode brincar com a situação presente, não com um histórico que não foi dado."
        )

    momento_cansaco = bool(re.search(
        r'\b(?:cansad[oa]?|cansando|canseira|exaust[oa]?|esgotad[oa]?|estressad[oa]?)\b',
        prompt_usuario or "", re.IGNORECASE,
    ))
    momento_sensivel = bool(re.search(
        r'\b(?:triste|doente|doença|dor|luto|morreu|falecimento)\b',
        prompt_usuario or "", re.IGNORECASE,
    ))
    correcao_luna = bool(re.search(
        r'\b(?:você|voce|vc)\s+(?:alucin\w*|err\w*|(?:se\s+)?confundi\w*)\b',
        prompt_usuario or "", re.IGNORECASE,
    ))
    agradecimento_curto = bool(re.match(
        r'^\s*(?:(?:beleza|blz)(?:\s+então)?[, ]*)?'
        r'(?:vlw|valeu|obrigad[oa]?|brigad[oa]?|não precisa(?: não)?)[.! ]*$',
        prompt_usuario or "", re.IGNORECASE,
    ))
    saudacao_simples = bool(re.fullmatch(
        r'\s*(?:(?:oi|olá|opa|e\s+aí|bom\s+dia|boa\s+tarde|boa\s+noite)[,!?. ]*)?'
        r'(?:tudo\s+(?:bem|bom|certo)(?:\s+com\s+(?:você|voce|vc))?'
        r'|como\s+(?:você|voce|vc)\s+(?:está|esta|tá|ta|vai))\s*[!?., ]*',
        prompt_usuario or "", re.IGNORECASE,
    ))
    zoeira_backlog = bool(
        re.search(r'\bbacklog\b', prompt_usuario or "", re.IGNORECASE)
        and re.search(r'\b(?:comprar|compra|jogo|lotad[oa])\b', prompt_usuario or "", re.IGNORECASE)
    )
    compra_jogo_sem_contexto = bool(
        re.search(r'\b(?:comprar|compra)\b', prompt_usuario or "", re.IGNORECASE)
        and re.search(r'\b(?:jogo|steam)\b', prompt_usuario or "", re.IGNORECASE)
        and not zoeira_backlog
    )
    mudanca_ideia_explicita = bool(re.search(
        r'\b(?:mudei|mudamos|mudou)\s+de\s+ideia\b|\b(?:em\s+vez\s+de|ao\s+inv[eé]s\s+de)\b',
        prompt_usuario or "", re.IGNORECASE,
    ))
    contradicao_declarada = bool(
        not mudanca_ideia_explicita
        and re.search(
            r'\b(?:disse|falei|achei)\b.{0,180}\b(?:mas|e)\b.{0,100}'
            r'\b(?:acabei|termin(?:ei|ou)|virou)\b',
            prompt_usuario or "", re.IGNORECASE | re.DOTALL,
        )
    )

    prompt_sistema = _prompts.sistema_completo(
        agora=f"Hoje é {data_hoje}. {periodo_atual()[1]}",
        contexto=contexto_situacional,
        perfil=memoria_permanente,
        memoria_recente=memoria_episodica,
        memoria_relacionada=memoria_relacionada,
        conversas_anteriores=contexto_db,
        # avisos que valem só neste turno, na ordem em que entram depois da persona
        ajustes=[aviso_saudacao, canal_hint, dica_tom, presenca_hint,
                 aviso_kaomoji, aviso_referencia, aviso_cotidiano],
    )

    is_proativo = (prompt_usuario == "")
    modo_enxuto = ""
    if saudacao_simples:
        modo_enxuto = _prompts.ENXUTO_SAUDACAO
    elif mudanca_ideia_explicita:
        modo_enxuto = _prompts.ENXUTO_MUDANCA_DE_IDEIA
    elif contradicao_declarada:
        modo_enxuto = _prompts.ENXUTO_CONTRADICAO
    elif compra_jogo_sem_contexto:
        modo_enxuto = _prompts.ENXUTO_COMPRA_DE_JOGO
    elif aviso_cotidiano:
        modo_enxuto = _prompts.ENXUTO_COTIDIANO
    elif referencia_sem_nome:
        modo_enxuto = _prompts.ENXUTO_REFERENCIA_SEM_NOME
    elif correcao_luna:
        modo_enxuto = _prompts.ENXUTO_CORRECAO
    elif agradecimento_curto:
        modo_enxuto = _prompts.ENXUTO_AGRADECIMENTO
    elif is_proativo:
        modo_enxuto = _prompts.ENXUTO_PROATIVO
    elif zoeira_backlog:
        modo_enxuto = _prompts.ENXUTO_ZOEIRA_BACKLOG
    elif momento_sensivel:
        modo_enxuto = _prompts.ENXUTO_SENSIVEL
    elif momento_cansaco:
        modo_enxuto = _prompts.ENXUTO_CANSACO

    if modo_enxuto:
        # O prompt completo incentiva ousadia e modelos menores tendem a priorizá-la sobre as
        # exceções de grounding. Turnos de risco usam o mesmo núcleo curto em vez de somar remendos.
        prompt_sistema = _prompts.nucleo_enxuto(modo_enxuto, sem_emoji=not responder_completo)

    resultado_longo = len(resposta_tecnica) > 200 and not is_proativo and not forcar_incluir
    resultado_imagem = bool(re.match(r'^\s*imagem gerada\b', resposta_tecnica, re.IGNORECASE))
    resultado_acompanhamento = resposta_tecnica.startswith("ACOMPANHAMENTO_PROPOSTO:")
    resultado_acompanhamento_confirmado = resposta_tecnica.startswith("ACOMPANHAMENTO_CONFIRMADO:")
    resultado_acompanhamento_descartado = resposta_tecnica.startswith("ACOMPANHAMENTO_DESCARTADO:")
    _falhou = bool(re.match(r'^\s*(erro|falha|nenhum|não foi possível)\b|^\s*sistema:',
                            resposta_tecnica, re.IGNORECASE))

    ultima_resp = next((m["content"] for m in reversed(historico) if m["role"] == "assistant"), "")
    # A lista parava em 'Ih' — logo antes das que mais aparecem. Medido em 875 respostas de modo
    # enxuto: 22% abriam com poxa/nossa/putz/eita/puxa, nenhuma delas coberta aqui.
    anti_rep = "" if is_proativo else (
        " [varie a abertura — nada de 'Pois é', 'Ah', 'Olha', 'Pô', 'Ih', 'Nossa', "
        "'Poxa', 'Puxa', 'Putz', 'Eita']")
    if ultima_resp and not is_proativo:
        primeira = re.split(r'[.\n]', ultima_resp)[0].strip()
        if len(primeira) > 15:
            anti_rep += f" [não repita: '{primeira[:80]}']"
        # Muleta de abertura da última fala: proíbe explicitamente repetir (o 'Pois é' vive
        # voltando; a instrução estática sozinha não segura o viés do modelo).
        m_mul = re.match(r"\s*(pois é|pois e|ah|olha|pô|po|ih|hmm|nossa|então|entao|eita|opa|vish"
                         r"|poxa|puxa|putz)\b",
                         ultima_resp, re.IGNORECASE)
        if m_mul:
            anti_rep += f" [NÃO abra com '{m_mul.group(1)}' de novo — varie]"

    if tarefa_documento:
        # Ferramenta de conteúdo (YouTube/site): a persona processa o texto cru diretamente.
        user_msg = (
            f"O usuário pediu: '{prompt_usuario}'\n\n"
            f"Conteúdo obtido (use só isto, não invente):\n\"\"\"\n{resposta_tecnica[:6000]}\n\"\"\"\n\n"
            f"Tarefa: {tarefa_documento}\n"
            f"Responda na sua voz, em português do Brasil, de forma natural.{anti_rep}"
        )
    elif is_proativo:
        user_msg = (
            f"MODO AUTÔNOMO — você está falando por iniciativa própria, o usuário não pediu nada.\n"
            f"Instrução: {resposta_tecnica}\n"
            f"REGRAS CRÍTICAS: Siga exatamente o que a instrução pede em quantidade de frases e tom. "
            f"NÃO mencione 'Janela aberta', 'Sessão ativa' ou contexto de sistema como relatório. "
            f"NÃO recite dados como relatório: reaja a eles, mas sem inventar causa, intenção, "
            f"desculpa ou estado emocional que o dado não demonstra. "
            f"Toda fala proativa tem um PONTO concreto ancorado SOMENTE na instrução recebida. "
            f"Conexão pessoal e provocação são opcionais: nunca importe uma memória sem relação direta "
            f"só para deixar a fala mais afiada. NUNCA recheio vazio ('tô aqui', 'o que manda?') nem descrição pura da tela. "
            f"Frequência de uso não prova vício; um número não prova meta, intenção ou prioridade que a instrução não declarou. "
            f"PROIBIDO inventar resultados de ferramentas que você não executou."
        )
        if "CONTRASTE DE ABERTURA CONFIRMADO PELO SISTEMA" in resposta_tecnica:
            user_msg += (
                "\nPRIORIDADE FINAL OBRIGATÓRIA: escreva UMA frase cuja graça seja que ele ANUNCIOU "
                "um jogo, mas ABRIU o outro. Cite os dois nomes. Ele não iniciou nem jogou o primeiro: "
                "não descreva passagem, sequência, salto, saída ou troca entre os mundos dos jogos. "
                "Não explique gênero, clima ou lançamento."
            )
    elif forcar_incluir and resposta_tecnica:
        user_msg = (
            f"O usuário disse: '{prompt_usuario}'\n\n"
            f"Você analisou a tela e viu: {resposta_tecnica}\n\n"
            f"Responda o pedido com base no que viu. "
            f"Fale como se você tivesse observado diretamente — sem mencionar 'ferramenta' ou 'sistema'. "
            f"NÃO seja narradora: é PROIBIDO só descrever o que aparece na tela ('vi que você está mexendo em X, testando Y'). "
            f"REAJA ao que viu — conecte com o que você sabe dele, tenha um ponto, uma opinião ou uma cutucada. "
            f"A descrição da tela é só matéria-prima pro seu comentário, nunca a resposta em si. "
            f"Pegue UMA coisa que chama atenção e reaja a ela — não faça inventário do que está aberto. "
            f"Se for conquista, fuja de 'parabéns pela dedicação': comemore o feito ESPECÍFICO com "
            f"uma imagem, opinião ou zoeira que só serviria para aquela conquista, em no máximo duas "
            f"frases. Use apenas o feito visto: não invente quantas vezes ele morreu, sofreu ou tentou.{anti_rep}"
        )
    elif resposta_tecnica:
        if resultado_acompanhamento_confirmado:
            user_msg = (
                f"O usuário clicou em 'Acompanhar resultado' para este assunto: '{prompt_usuario}'.\n"
                f"O sistema confirmou: '{resposta_tecnica}'\n"
                "Responda em UMA frase curta e natural confirmando que ficou combinado. Pode reagir "
                "brevemente ao assunto, mas não invente resultado, não faça outra pergunta e não ofereça "
                f"acompanhamento de novo.{anti_rep}"
            )
        elif resultado_acompanhamento_descartado:
            user_msg = (
                f"O usuário clicou em 'Só comentei' sobre este assunto: '{prompt_usuario}'.\n"
                "Use a conversa recente para retomar o comentário original e REAGIR ao assunto em uma "
                "ou duas frases. Não fale de botão, sistema, acompanhamento, agenda ou lembrete; não responda "
                f"apenas 'beleza' e não pergunte novamente se deve guardar.{anti_rep}"
            )
        elif resultado_acompanhamento:
            user_msg = (
                f"O usuário disse: '{prompt_usuario}'\n"
                f"O sistema identificou este possível acompanhamento: '{resposta_tecnica}'\n"
                "Em UMA frase curta e natural, pergunte se ele quer que você acompanhe o RESULTADO. "
                "Não diga que já salvou, não prometa lembrar ainda e não chame de agenda ou lembrete. "
                "O botão e a próxima resposta dele farão a confirmação."
            )
        elif _falhou:
            user_msg = (
                f"O usuário disse: '{prompt_usuario}'\n\n"
                f"A ferramenta FALHOU e retornou: '{resposta_tecnica}'\n"
                f"SUA TAREFA: 1 frase informando, de forma direta, que NÃO deu certo e o motivo. "
                f"PROIBIDO dizer que funcionou, que foi concluído ou que teve sucesso.{anti_rep}"
            )
        elif resultado_imagem:
            user_msg = (
                f"O usuário pediu: '{prompt_usuario}'\n"
                f"A ferramenta confirmou: '{resposta_tecnica}'\n"
                f"Responda em UMA frase: confirme com 'Pronto —' e emende uma reação visual ou "
                f"zoeira ESPECÍFICA ao desenho pedido. Não reconte o pedido, não diga só que ficou "
                f"interessante/bonito e não descreva o ato de gerar.{anti_rep}"
            )
        elif responder_completo:
            # Canal de texto (Telegram): não há painel pra exibir dados — a Luna responde de fato.
            user_msg = (
                f"O usuário perguntou: '{prompt_usuario}'\n\n"
                f"A ferramenta retornou estes dados:\n{resposta_tecnica}\n\n"
                f"Responda à pergunta de forma direta e conversacional, resumindo os dados de forma útil. "
                f"Pode usar mais de uma frase se precisar. Fidelidade vem primeiro, mas resultado curto, "
                f"criação concluída ou conquista NÃO precisa soar como recibo: acrescente uma reação "
                f"breve e específica quando houver material, sem forçar piada. Fuja de elogio genérico "
                f"como 'parabéns pela dedicação'. NÃO cole o texto bruto da ferramenta — explique com suas palavras.{anti_rep}"
            )
        elif resultado_longo:
            max_tokens = max(max_tokens, 450)   # lista completa precisa de fôlego
            user_msg = (
                f"O usuário disse: '{prompt_usuario}'\n\n"
                f"A ferramenta retornou estes dados:\n{resposta_tecnica[:4000]}\n\n"
                f"Apresente esses dados a ele do seu jeito, conversando. "
                f"Inclua TODOS os itens fielmente — não omita, não invente e não julgue nenhum. "
                f"Se for lista (agenda, emails), um item por linha. Aqui pode passar de 4 frases: fidelidade vem primeiro. "
                f"NÃO cole o texto bruto da ferramenta: reescreva natural, com datas e horários falados.{anti_rep}"
            )
        else:
            user_msg = (
                f"O usuário disse: '{prompt_usuario}'\n\n"
                f"A ferramenta retornou: '{resposta_tecnica}'\n"
                f"SUA TAREFA: 1 frase direta informando o resultado. Pode deixar uma marca curta da "
                f"personalidade se ela nascer do pedido ou do resultado; não transforme sucesso em recibo. "
                f"Os FATOS do resultado (nome de música, artista, valores) são a ÚNICA verdade — "
                f"cite-os EXATOS, NUNCA invente outros no lugar. "
                f"NÃO copie o texto da ferramenta literalmente — reformule. Não force elogio nem crítica.{anti_rep}"
            )
    elif referencia_sem_nome:
        user_msg = (
            f"O usuário perguntou: '{prompt_usuario}'\n"
            "No histórico, você só disse 'aquele jogo novo' e não registrou nome nenhum. "
            "Responda em uma frase assumindo que foi vaga e que não tem o nome. Pare aí."
        )
    elif correcao_luna:
        user_msg = (
            f"O usuário disse exatamente: '{prompt_usuario}'\n"
            "Ele está corrigindo você. Admita em UMA frase curta que você errou/alucinou e, se quiser, "
            "zoe a sua própria confusão. Não use 'mas' para se defender e não repita o fato inventado."
        )
    elif agradecimento_curto:
        user_msg = (
            f"O usuário disse somente: '{prompt_usuario}'\n"
            "Responda em UMA frase curta e deixe a conversa pousar. Comece com 'Disponha', 'De nada' "
            "ou 'Por nada'; uma microvaidade seca está liberada. Não use 'fico feliz', carinho "
            "romântico, cobrança, conselho ou assunto novo."
        )
    elif mudanca_ideia_explicita:
        user_msg = (
            f"O usuário disse exatamente: '{prompt_usuario}'\n"
            "Reaja em uma ou duas frases ao que ele escolheu AGORA. Não comente que trocar de planos é clássico "
            "ou repentino, não diga que ele fez drama, não dê ordem e não fabrique características das opções. "
            "A personalidade deve aparecer na reação à escolha atual, não numa crítica à mudança. "
            "Como ele afirmou que vai jogar o título, trate o jogo como disponível agora: não fale de "
            "esperar lançamento, hype futuro ou dúvida sobre ele ter saído. Não encerre com 'aproveita' "
            "nem diga apenas que o jogo é incrível; isso é aprovação genérica, não personalidade."
        )
    elif contradicao_declarada:
        user_msg = (
            f"O usuário disse exatamente: '{prompt_usuario}'\n"
            "Responda com UMA tirada irônica curta construída com a contradição e os números/palavras concretos "
            "da frase. Não explique o efeito, não narre consequências, não acrescente outro assunto e não "
            "invente uma quantidade inicial que ele não informou."
        )
    elif compra_jogo_sem_contexto:
        user_msg = (
            f"O usuário disse exatamente: '{prompt_usuario}'\n"
            "Responda em uma ou duas frases: alfinete levemente a carteira/carrinho desta compra e "
            "termine exatamente com 'Qual é o jogo?'. Existe somente esta compra; não crie passado "
            "nem hábito e não use 'da vez'/'dessa vez'. Use "
            "[clima:zoeira] ou [clima:duvida]."
        )
    elif aviso_cotidiano:
        user_msg = (
            f"O usuário disse exatamente: '{prompt_usuario}'\n"
            "Esse é o único fato disponível. Reaja com naturalidade em uma ou duas frases. "
            "Soa como uma amiga próxima, não como atendente: faça uma provocação leve sobre a escolha "
            "literal ou pergunte o detalhe com curiosidade afiada. Baseie tudo somente "
            "nas palavras dessa frase. Fale apenas do presente/futuro, sem comparar com ocasiões "
            "anteriores (nada de 'de sempre', 'dessa vez', 'de novo', 'outro' ou 'mais um'). "
            "Não complete a cena nem imagine o que aconteceu antes ou depois."
        )
    elif momento_sensivel:
        user_msg = (
            f"O usuário disse exatamente: '{prompt_usuario}'\n"
            "Acolha o que ele expressou sem tentar fazer graça, sem dizer por que aconteceu e sem "
            "inventar o que ele fez ou ainda precisa fazer. Responda em uma ou duas frases curtas."
        )
    elif momento_cansaco:
        user_msg = (
            f"O usuário disse exatamente: '{prompt_usuario}'\n"
            "Acolha em UMA frase. Uma cutucada carinhosa sobre descansar está liberada, mas não fale "
            "de produtividade, trabalho, pendência ou causa que ele não informou."
        )
    elif zoeira_backlog:
        user_msg = (
            f"O usuário disse exatamente: '{prompt_usuario}'\n"
            "Faça uma alfinetada adulta e criativa baseada na contradição que ele próprio contou: "
            "comprar mais um jogo com o backlog lotado. Pode exagerar sem dó — cemitério, caixão, "
            "dopamina, vazio existencial e promessas abandonadas são linguagem de zoeira válida aqui. "
            "Seja específica e memorável, não uma explicação psicológica séria."
        )
    else:
        user_msg = (
            f"O usuário disse: '{prompt_usuario}'\n"
            f"Responda de forma natural, usando o contexto da conversa anterior e o que você já sabe. "
            f"Se for uma pergunta de acompanhamento, conecte com o que já foi falado. "
            f"SE ele afirmou uma conclusão, desabafou ou tomou uma decisão: é PROIBIDO validar genérico "
            f"('faz sentido, às vezes a gente...', 'é isso mesmo, o importante é focar no que faz diferença'). "
            f"Traga um ângulo ESPECÍFICO do que ele acabou de dizer, um contraponto ou uma pergunta afiada. "
            f"Se for uma fala cotidiana pequena, pode só reagir com naturalidade e brevidade. Não puxe "
            f"trabalho, família, jogos ou memória antiga sem relação direta com a mensagem atual. "
            f"Concordar tudo bem — mas com substância específica, nunca fórmula de biscoito da sorte. "
            f"Só diga que não tem a informação se ela realmente exigir dados externos que você não consultou.\n"
            f"ATENÇÃO: NENHUMA ferramenta foi executada agora — você NÃO realizou ação nenhuma "
            f"(não salvou, não marcou, não editou, não agendou, não tocou nada). Se o pedido era pra "
            f"VOCÊ FAZER algo, seja honesta: diga que NÃO fez. Ex: você não consegue editar notas "
            f"existentes do Obsidian (marcar concluído, riscar item) — só criar notas novas.{anti_rep}"
        )

    if referencia_sem_nome:
        user_msg += (
            "\nFATO OBRIGATÓRIO PARA ESTA RESPOSTA: você introduziu uma referência vaga e o "
            "histórico não contém o nome. Assuma isso em primeira pessoa ('eu fui vaga/não tenho "
            "o nome'), sem culpar o usuário e sem trocar por uma generalização sobre backlog."
        )
    if aviso_cotidiano:
        user_msg += (
            f"\nFATO DISPONÍVEL NESTE MOMENTO: somente isto — '{prompt_usuario}'. Reaja sem "
            "acrescentar número, repetição, hábito, causa, compromisso ou estado do PC que não "
            "esteja nessa frase. Dê um pouco de personalidade à reação, mas não fabrique uma premissa."
        )

    try:
        msgs = [{"role": "system", "content": prompt_sistema}]
        if not is_proativo:
            msgs.extend(_hist_curto(historico, 8))
        msgs.append({"role": "user", "content": user_msg})
        _t0 = time.time()
        _parametros_persona = {
            "messages": msgs,
            "temperature": 0.8,   # Fase 2: +variância pra ela ser menos previsível
            "presence_penalty": 0.3,
            "frequency_penalty": 0.3,
            "max_tokens": _orcamento_persona(max_tokens),
            "extra_body": OPCOES_MODELO,
        }
        _raciocinio_persona = ""
        _finish_reason = "?"
        _tk = 0
        if ao_fragmento:
            # Segura poucos caracteres no fim: é ali que chegam [clima:X] e [gif:X]. A prévia
            # continua fluida, mas o usuário nunca vê metadados que só o Python deve consumir.
            _partes = []
            _ultimo_envio = 0.0
            _ultimo_visivel = ""
            resposta = _chamar_llm(stream=True, **_parametros_persona)
            for _pedaco in resposta:
                _cancelado = getattr(ao_fragmento, "cancelado", None)
                if callable(_cancelado) and _cancelado():
                    try:
                        resposta.close()
                    except Exception:
                        pass
                    raise GeracaoInterrompida()
                _escolhas = getattr(_pedaco, "choices", None) or []
                if _escolhas:
                    _delta = getattr(_escolhas[0], "delta", None)
                    _conteudo = getattr(_delta, "content", None) or ""
                    if _conteudo:
                        _partes.append(_conteudo)
                    _raciocinio_persona += getattr(_delta, "reasoning_content", None) or ""
                    _finish_reason = getattr(_escolhas[0], "finish_reason", None) or _finish_reason
                _uso = getattr(_pedaco, "usage", None)
                if _uso:
                    _tk = getattr(_uso, "completion_tokens", 0) or _tk
                _bruto = "".join(_partes)
                _visivel = _bruto[:-20] if len(_bruto) > 20 else ""
                _agora = time.monotonic()
                if (_visivel and _visivel != _ultimo_visivel
                        and (_agora - _ultimo_envio >= .055 or _visivel.endswith("\n"))):
                    ao_fragmento(_visivel)
                    _ultimo_visivel = _visivel
                    _ultimo_envio = _agora
            texto_luna = "".join(_partes)
            if not _tk:
                _tk = max(1, len(texto_luna.encode("utf-8")) // 4)
        else:
            resposta = _chamar_llm(**_parametros_persona)
            _msg_persona = resposta.choices[0].message
            texto_luna = _msg_persona.content or ""
            _raciocinio_persona = getattr(_msg_persona, 'reasoning_content', None) or ""
            _finish_reason = getattr(resposta.choices[0], 'finish_reason', '?')
            try:
                _tk = resposta.usage.completion_tokens
            except Exception:
                pass
        _dur = time.time() - _t0
        # DIAGNÓSTICO: se veio vazio, revela a causa — pensou escondido (reasoning_content)
        # ou foi cortado pelo limite (finish_reason=length).
        if not texto_luna.strip():
            cor.vermelho(f"[⚠️ Persona VAZIA — finish_reason={_finish_reason} | "
                         f"reasoning_content={len(_raciocinio_persona)} chars]")
            if _raciocinio_persona:
                cor.amarelo(f"[🧠 (pensamento escondido): {_raciocinio_persona[:160]}...]")
        try:
            if _dur > 0 and _tk:
                print(f"[🎭 Persona: {_tk} tokens em {_dur:.1f}s = {_tk/_dur:.1f} tok/s]")
                import servidor as _srv
                _srv.atualizar_metricas(persona={"tokens": _tk, "tps": round(_tk / _dur, 1), "segundos": round(_dur, 1)})
        except Exception:
            pass

        # Rede de segurança: remove blocos de raciocínio que o modelo às vezes vaza.
        texto_luna = re.sub(r'<think>.*?</think>', '', texto_luna, flags=re.DOTALL | re.IGNORECASE).strip()
        texto_luna = re.sub(r'</?think>', '', texto_luna, flags=re.IGNORECASE).strip()

        if texto_luna.startswith("Luna:"):
            texto_luna = texto_luna[5:].lstrip()

        # Limpa tags HTML que modelos locais às vezes injetam
        texto_luna = re.sub(r'<br\s*/?>', ' ', texto_luna, flags=re.IGNORECASE).strip()

        # ROSTO primeiro: o apanha-tudo do GIF logo abaixo (\[palavra\]$, feito pra [streak])
        # engolia o [clima:X] antes da hora. Extrair aqui resolve na ordem.
        _ult, _clima_escolhido, texto_luna = _extrair_clima(texto_luna)

        # Extrai [gif:termo] — aceita variantes mal-formatadas de modelos locais
        gif_termo = None
        m = re.search(r'\[gif:\s*([^\]]+)\]', texto_luna)          # [gif:termo]
        if m:
            gif_termo = m.group(1).strip().rstrip('<').strip()
            texto_luna = re.sub(r'\[gif:[^\]]*\]', '', texto_luna)
        else:
            m = re.search(r'<gif:\s*([^>\[<\n]+)', texto_luna)     # <gif:termo>
            if m:
                gif_termo = m.group(1).strip().rstrip('<').strip()
                texto_luna = re.sub(r'<gif:[^>]*>?', '', texto_luna)
            else:
                m = re.search(r'\[([a-zA-Z][^\]]{1,35})\]\s*$', texto_luna)  # [streak], [thinking emoji]
                if m:
                    gif_termo = m.group(1).strip()
                    texto_luna = re.sub(r'\[[^\]]{1,37}\]\s*$', '', texto_luna)
        texto_luna = texto_luna.strip()
        if gif_termo:
            cor.ciano(f"[🎞️ GIF: {gif_termo}]")
            try:
                import servidor as _srv
                _srv.atualizar_gif(gif_termo)
            except Exception:
                pass

        # KAOMOJI: última linha, curta e SEM palavra de verdade (kaomoji não tem palavras).
        # Sai do texto -> a voz nunca lê e o web mostra grande; o Telegram pega pelo getter.
        texto_luna = texto_luna.strip()
        if _ult:
            _kaomoji_pendente = _ult
            _kaomoji_recentes.append(_ult)
            if len(_kaomoji_recentes) > 6:
                _kaomoji_recentes.pop(0)
            cor.ciano(f"[🎭 Rosto: {_ult}]")
            try:
                import servidor as _srv
                _srv.atualizar_kaomoji(_ult, _clima_escolhido)
            except Exception:
                pass

        # Saiu saudação na resposta? Marca o relógio — as próximas ficam proibidas
        # de cumprimentar pelas próximas horas (ver _JANELA_SAUDACAO_H).
        if _RE_SAUDACAO.search(texto_luna):
            _ultima_saudacao_ts = time.time()

        _finalizar_stream = getattr(ao_fragmento, "finalizar", None)
        if callable(_finalizar_stream):
            _finalizar_stream(texto_luna)

        # Web/Telegram precisam receber o Markdown que a persona gerou. A limpeza pesada
        # existe para o Kokoro e removia títulos, listas, links e código no fechamento do
        # stream — por isso a formatação aparecia enquanto digitava e virava texto cru no fim.
        return texto_luna if responder_completo else limpar_texto_para_voz(texto_luna)

    except GeracaoInterrompida:
        raise
    except Exception as e:
        _log.exception(f"LLM Persona falhou: {e}")
        cor.vermelho(f"[LLM Persona falhou: {e}]")
        return resposta_tecnica if responder_completo else limpar_texto_para_voz(resposta_tecnica)


def continuar_apos_acompanhamento(acao: str, assunto: str, resposta_sistema: str,
                                  historico: list) -> str:
    """Dá voz ao resultado determinístico do botão sem passar outra vez pelo roteador."""
    confirmou = acao == "confirmar"
    marcador = "ACOMPANHAMENTO_CONFIRMADO" if confirmou else "ACOMPANHAMENTO_DESCARTADO"
    detalhe = resposta_sistema if confirmou else "nenhum acompanhamento foi criado"
    return _reescrever_como_luna(
        f"{marcador}: {detalhe}",
        assunto,
        historico,
        max_tokens=100,
        responder_completo=True,
    )


# ==========================================
# LLM ROTEADORA
# ==========================================

_GATILHOS_AUTORRETRATO = (
    "me desenh", "desenha eu", "desenhe eu", "me retrat", "meu retrato",
    "como eu sou", "como sou", "que eu sou", "como vc acha que eu",
    "como você acha que eu", "como voce acha que eu", "quem eu sou",
)

def _extrair_url_youtube(texto: str):
    """Extrai uma URL do YouTube de um texto (para o guard do resumir_youtube)."""
    m = re.search(r'https?://[^\s]*(?:youtube\.com|youtu\.be)/[^\s]+', texto or "")
    return m.group(0) if m else None


def _extrair_url(texto: str):
    """Extrai qualquer URL http(s) de um texto (para o guard do resumir_site)."""
    m = re.search(r'https?://[^\s]+', texto or "")
    return m.group(0) if m else None


def _args_do_json_torto(bruto: str) -> dict:
    """O 12B às vezes gera o JSON dos argumentos malformado (típico com URLs, que têm ?=&).
    Em vez de perder tudo, pesca os pares 'chave: valor' via regex (tolera aspas simples,
    faltando ou JSON não fechado). Vazio se não achar nada — aí os guards abaixo assumem."""
    d = {}
    for k, v in re.findall(r'["\']?([a-zA-Z_]\w*)["\']?\s*:\s*["\']?([^"\',}\n]+?)["\']?\s*(?:[,}\n]|$)',
                           bruto or ""):
        d[k] = v.strip()
    return d


# Verbos que indicam pedido de AÇÃO (mapeiam a ferramentas). Usado para impedir alucinação:
# se o usuário pede uma ação e o roteador NÃO aciona ferramenta, não deixamos a persona
# inventar resposta a partir da memória — devolvemos uma resposta honesta.
_PADRAO_ACAO = re.compile(
    r'\b(resum|transcrev|pesquis|busca|busque|procur|abr[ae]|abrir|'
    r'toc[ae]|toque|desenh|consult|qual o (?:preço|valor|custo)|quanto custa)',
    re.IGNORECASE,
)

def _parece_pedido_de_acao(texto: str) -> bool:
    return bool(_PADRAO_ACAO.search(texto or ""))


def _carregar_perfil_desenho():
    """Lê aparência/estilo do usuário para autorretratos (config da ferramenta de desenho).
    Fica em modelos/desenho.json — fora do perfil de conversa e fora do git (privado)."""
    try:
        with open("modelos/desenho.json", encoding="utf-8") as f:
            d = json.load(f)
        return d.get("aparencia", ""), d.get("estilo", "")
    except Exception:
        return "", ""


def _montar_prompt_imagem(pedido_usuario: str, dica: str = "") -> str:
    """Decide o prompt da imagem. Para autorretrato ('me desenhe'), monta a partir da
    config de desenho (aparência + estilo). Para pedidos explícitos (ex: 'gato astronauta'),
    mantém o que o roteador gerou."""
    pedido_low = (pedido_usuario or "").lower()
    if not any(g in pedido_low for g in _GATILHOS_AUTORRETRATO):
        return dica or pedido_usuario   # pedido explícito — o roteador já resolve bem

    aparencia, estilo = _carregar_perfil_desenho()
    if not aparencia and not estilo:
        return dica or pedido_usuario   # sem config de aparência — não há o que montar

    partes = ["portrait of a person"]
    if aparencia:
        partes.append(aparencia)
    if estilo:
        partes.append(estilo)
    return ", ".join(partes)


def gerar_resposta(prompt_usuario, historico, imagem_base64=None, analisar=True, salvar=True,
                   modo_memoria=False, max_tokens=800, responder_completo=False,
                   presenca_pc=True, ao_fragmento=None):
    global _imagem_pendente
    _presenca_pc.set(presenca_pc)   # onde ele está (voz/web = no PC; Telegram = fora) — colore o prompt
    if responder_completo:
        _imagem_pendente = None   # começa limpo a cada turno do Telegram

    # DESVIO GEMINI
    if imagem_base64 and not modo_memoria:
        from modulos.habilidades import analisar_imagem_gemini
        resultado_gemini = analisar_imagem_gemini(imagem_base64, prompt_usuario)
        return _reescrever_como_luna(resultado_gemini, prompt_usuario, historico, max_tokens,
                                     forcar_incluir=True, ao_fragmento=ao_fragmento)

    # DESVIO PROATIVO
    if not analisar and not modo_memoria:
        cor.amarelo("[🎭 Passando direto para LLM persona (Modo Proativo)...]")
        return _reescrever_como_luna(prompt_usuario, "", historico, max_tokens,
                                     ao_fragmento=ao_fragmento)

    try:
        inicio = time.time()

        ferramentas_ativas = ferramentas_disponiveis if not imagem_base64 and not modo_memoria else None

        if modo_memoria:
            prompt_ferramenta = (
                "Você é um extrator de dados estruturados. Retorne EXCLUSIVAMENTE um objeto JSON válido. "
                "Use ASPAS DUPLAS (\") obrigatoriamente para envolver todas as chaves e valores. "
                "Nunca use aspas simples. Nunca envolva a resposta em blocos de código markdown."
            )
        else:
            _agora = datetime.datetime.now()
            _dias_semana = ["segunda-feira", "terça-feira", "quarta-feira", "quinta-feira",
                            "sexta-feira", "sábado", "domingo"]
            _data_ctx = f"{_dias_semana[_agora.weekday()]}, {_agora.strftime('%d/%m/%Y %H:%M')}"
            prompt_ferramenta = (
                f"Data e hora atuais: {_data_ctx}. "
                "Use SEMPRE esta data como referência para resolver 'hoje', 'amanhã', 'dia 8', 'sexta' etc. "
                "ao gerar qualquer data no formato ISO — nunca chute o ano. "
                "Você é um motor lógico e de roteamento invisível. "
                "Sua ÚNICA função é acionar a ferramenta correta quando o usuário pediu EXPLICITAMENTE por uma ação ou informação. "
                "NÃO converse. NÃO assuma persona. NÃO justifique. "
                "REGRA CRÍTICA: Estados emocionais ('estou cansado', 'estou entediado'), saudações e comentários genéricos NÃO ativam ferramentas. "
                "Acione ferramenta SOMENTE se o usuário pediu uma ação ou informação específica. "
                "EXCEÇÃO CONTROLADA: você pode acionar 'propor_acompanhamento' quando o usuário "
                "contar uma situação CONCRETA em aberto com desfecho futuro claro (assistência, "
                "entrevista, exame, tentativa de resolver algo), mesmo sem pedir. Isso apenas oferece; "
                "não salva. NUNCA use essa exceção para agenda, compromisso, lembrete para FAZER algo "
                "ou ação cotidiana como comer, dormir, comprar e jogar. "
                "Se nenhuma ferramenta for necessária (saudação, papo, desabafo), NÃO chame ferramenta e "
                "responda EXATAMENTE SEM_FERRAMENTA. Essa é a única saída textual permitida: não converse, "
                "não responda ao usuário e não acrescente pontuação nem explicação. Outro modelo cuida da conversa."
            )

            _idx_obsidian = obsidian.indice_notas()
            if _idx_obsidian:
                prompt_ferramenta += (
                    f"\nNotas do usuário no Obsidian: {_idx_obsidian}. "
                    "Se ele pedir para ler/ver algo que esteja nessas notas (receita, lista, etc.), "
                    "use a ferramenta 'ler_obsidian' com o assunto."
                )

            # Jogo ativo no contexto do roteador: sem isto ele não sabe que uma dúvida
            # vaga de gameplay ('como faço o trem andar?') é sobre o jogo em andamento.
            _jogo_ativo = ler_estado_luna().get("jogo_ativo")
            if _jogo_ativo:
                prompt_ferramenta += (
                    f"\nO usuário está JOGANDO '{_jogo_ativo}' AGORA. Se ele fizer uma pergunta de "
                    "gameplay/how-to que faça sentido nesse jogo (como fazer algo, onde achar, como "
                    "passar de uma parte), MESMO sem citar o jogo, use 'duvida_do_jogo' com a pergunta dele."
                )
            prompt_ferramenta += (
                "\nPara 'duvida_do_jogo', copie em 'trecho_pedido' o trecho LITERAL da mensagem "
                "ATUAL que pede ajuda ou informação. O histórico pode identificar qual é o jogo, "
                "mas nunca transforma comentário, progresso ou opinião em pergunta. Sem essa prova "
                "literal, retorne SEM_FERRAMENTA."
            )

        if prompt_usuario.startswith('[Arquivo:'):
            prompt_ferramenta += (
                "\nATENÇÃO: O conteúdo do arquivo já está incluído na mensagem do usuário. "
                "NÃO acione 'ler_selecionado' nem qualquer ferramenta de leitura de texto/arquivo. "
                "Retorne texto vazio."
            )

        mensagens_ferramenta = [{"role": "system", "content": prompt_ferramenta}]
        mensagens_ferramenta.extend(_hist_curto(historico, 4))  # contexto mínimo para calibrar tool calling
        mensagens_ferramenta.append({"role": "user", "content": prompt_usuario})

        # MONO: o mesmo modelo (Gemma-4-12B) roteia as ferramentas. Thinking fica desligado
        # somente nesta chamada para não gastar o orçamento antes de decidir a ferramenta.
        # O teto da persona não pertence ao roteador. Deixá-lo herdar os 800 tokens fez o
        # Gemma escrever conversa descartada até o limite quando não havia ferramenta.
        _max_tokens_roteador = max_tokens if modo_memoria else min(max_tokens, 256)
        resposta_ferramenta = _chamar_llm(
            messages=mensagens_ferramenta,
            temperature=0.0,
            tools=ferramentas_ativas,
            max_tokens=_max_tokens_roteador,
            extra_body=OPCOES_ROTEADOR,
        )
        fim = time.time()

        # Imprime a métrica do roteador AGORA (ele rodou primeiro) — ordem de leitura natural.
        try:
            tokens_gerados = resposta_ferramenta.usage.completion_tokens
            segundos = fim - inicio
            if segundos > 0:
                tps_r = tokens_gerados / segundos
                print(f"[⚡ Roteador: {tokens_gerados} tokens em {segundos:.1f}s = {tps_r:.1f} tok/s]")
                import servidor as _srv
                _srv.atualizar_metricas(roteador={"tokens": tokens_gerados, "tps": round(tps_r, 1), "segundos": round(segundos, 1)})
        except Exception:
            pass

        mensagem_modelo = resposta_ferramenta.choices[0].message
        lembranca_oculta = ""
        resultado_ferramenta = ""
        ferramenta_chamada = False
        inicio_ferramenta = None

        raciocinio = getattr(mensagem_modelo, 'reasoning_content', None) or ""
        if raciocinio:
            print(f"\n\033[90m[🧠 LÓGICA INTERNA]:\n{raciocinio.strip()}\033[0m\n")

        _tool_calls = getattr(mensagem_modelo, 'tool_calls', None)
        conteudo_salvo_turno = ""
        _jogo_contexto_guard = ""
        _contexto_gameplay = contexto_gameplay_anterior(historico) or {}
        # Guard anti-salvamento indevido: se o roteador firou salvar_obsidian num comentário
        # casual (sem intenção explícita de anotar), ignora a ferramenta e responde normal.
        if (_tool_calls and _tool_calls[0].function.name == "salvar_obsidian"
                and not _RE_INTENCAO_SALVAR.search(prompt_usuario or "")):
            cor.vermelho("[⚠️ salvar_obsidian sem intenção de anotar — ignorado, respondendo normal]")
            _tool_calls = None
        if (_tool_calls and _tool_calls[0].function.name == "registrar_rotina_jogo"
                and not _RE_DECLARACAO_JOGO.search(prompt_usuario or "")):
            cor.vermelho("[⚠️ rotina de jogo sem declaração explícita — ignorada]")
            _tool_calls = None
        if (_tool_calls and _tool_calls[0].function.name == "consultar_proprio_codigo"
                and not _RE_AUTOCONHECIMENTO.search(prompt_usuario or "")):
            cor.vermelho("[⚠️ introspecção sem referência à própria Luna — ignorada]")
            _tool_calls = None
        if _tool_calls and _tool_calls[0].function.name == "duvida_do_jogo":
            try:
                _args_guard = json.loads(_tool_calls[0].function.arguments or "{}")
            except (json.JSONDecodeError, TypeError):
                _args_guard = _args_do_json_torto(_tool_calls[0].function.arguments or "")
            _jogo_contexto_guard = str(
                _args_guard.get("nome_jogo") or _contexto_gameplay.get("nome_jogo") or ""
            ).strip()
            if not validar_pedido_gameplay(
                    prompt_usuario, _args_guard.get("trecho_pedido", ""), historico):
                cor.vermelho("[⚠️ dúvida de jogo sem evidência literal de pedido — ignorada]")
                _tool_calls = None
        if _tool_calls and _tool_calls[0].function.name == "propor_acompanhamento":
            from modulos import acompanhamentos as _acomp
            if not _acomp.pode_propor(prompt_usuario or ""):
                cor.vermelho("[⚠️ acompanhamento confundido com agenda/cotidiano — ignorado]")
                _tool_calls = None

        if _tool_calls:
            ferramenta_chamada = True
            inicio_ferramenta = time.time()
            tool_call = _tool_calls[0]
            nome_funcao = tool_call.function.name
            _log.info(f"Ferramenta: {nome_funcao}")
            cor.amarelo(f"[🌚⚙️ Motor Lógico ativando habilidade: {nome_funcao}]")
            try:
                import servidor as _srv
                _srv.atualizar_status(f"▸ Usando: {nome_funcao}")
            except Exception:
                pass

            if nome_funcao in FUNCOES_DISPONIVEIS:
                argumentos_json = tool_call.function.arguments

                try:
                    argumentos_dit = json.loads(argumentos_json) if argumentos_json else {}
                except json.JSONDecodeError:
                    # o 12B errou o JSON (comum com URLs). Tenta salvar o que der; o essencial
                    # (url etc) ainda é recuperado pelos guards abaixo — não é falha real.
                    argumentos_dit = _args_do_json_torto(argumentos_json)
                    cor.amarelo(f"[JSON dos argumentos veio torto do roteador — recuperado: "
                                f"{argumentos_dit or 'nada, deixando com os guards'}]")

                if nome_funcao == "controlar_navegador":
                    if "url" in argumentos_dit and "parametro" not in argumentos_dit:
                        argumentos_dit["parametro"] = argumentos_dit.pop("url")
                    if "texto" in argumentos_dit and "parametro" not in argumentos_dit:
                        argumentos_dit["parametro"] = argumentos_dit.pop("texto")
                    if "query" in argumentos_dit and "parametro" not in argumentos_dit:
                        argumentos_dit["parametro"] = argumentos_dit.pop("query")

                if nome_funcao == "duvida_do_jogo":
                    # O histórico resolve apenas QUAL jogo. A intenção já foi provada por
                    # trecho literal da mensagem atual no guard acima.
                    argumentos_dit.pop("trecho_pedido", None)
                    if not argumentos_dit.get("nome_jogo") and _contexto_gameplay.get("nome_jogo"):
                        argumentos_dit["nome_jogo"] = _contexto_gameplay["nome_jogo"]

                if nome_funcao == "ver_tela":
                    imagem_b64 = FUNCOES_DISPONIVEIS["ver_tela"]()
                    if responder_completo:   # Telegram: guarda o print para enviar como foto
                        _imagem_pendente = {"tipo": "b64", "dado": imagem_b64}
                    from modulos.habilidades import analisar_imagem_gemini
                    # Se tem jogo aberto, avisa o Gemini QUAL é — ele reconhece o jogo e a
                    # tela muito melhor (o contexto vai pro Gemini, não incha o prompt local).
                    _jogo_tela = ler_estado_luna().get("jogo_ativo")
                    _pergunta_tela = (f"[Contexto: o usuário está jogando '{_jogo_tela}' agora.] {prompt_usuario}"
                                      if _jogo_tela else prompt_usuario)
                    resultado_ferramenta = analisar_imagem_gemini(imagem_b64, _pergunta_tela)
                    cor.amarelo(f"[🖥️ Gemini ver_tela retornou: {str(resultado_ferramenta)[:200]}]")
                else:
                    if nome_funcao == "desenhar_imagem":
                        # Reescreve o prompt da imagem com a memória (evita o roteador reusar desenhos antigos)
                        argumentos_dit["prompt_imagem"] = _montar_prompt_imagem(
                            prompt_usuario, argumentos_dit.get("prompt_imagem", "")
                        )
                    if nome_funcao == "resumir_youtube" and not argumentos_dit.get("url"):
                        # Guard: se o usuário mandou um link e o roteador esqueceu de passar, injeta na mão
                        _yt = _extrair_url_youtube(prompt_usuario)
                        if _yt:
                            argumentos_dit["url"] = _yt
                    if nome_funcao == "resumir_site" and not argumentos_dit.get("url"):
                        _u = _extrair_url(prompt_usuario)
                        if _u:
                            argumentos_dit["url"] = _u
                    if nome_funcao == "propor_acompanhamento":
                        # O 12B inventou 10h para uma frase que dizia apenas "amanhã". A data do
                        # acompanhamento é resolvida deterministicamente a partir da fala ORIGINAL;
                        # o modelo só escolhe qual é o assunto cujo desfecho vale acompanhar.
                        argumentos_dit["perguntar_em"] = prompt_usuario
                    if nome_funcao == "concluir_tarefa_obsidian":
                        argumentos_dit["origem"] = "telegram" if not _presenca_pc.get() else "pc"
                    if nome_funcao == "salvar_obsidian":
                        argumentos_dit["origem"] = _origem_salvamento(responder_completo)
                        # Usa o texto ORIGINAL do usuário como conteúdo (fiel), não a
                        # reprodução do roteador — que trunca/parafraseia textos longos.
                        _bruto, _titulo = _dados_para_anotar(
                            prompt_usuario, argumentos_dit.get("titulo", ""))
                        # "deixa isso anotado" / "anota aí": o comando não tem conteúdo próprio —
                        # o "isso" aponta pra fala ANTERIOR (senão salva o eco do comando).
                        if _so_comando_salvar(prompt_usuario):
                            _ant = _ultima_fala_do_historico(historico, prompt_usuario)
                            if _ant:
                                _bruto = _ant
                        conteudo_salvo_turno = _bruto
                        if len(_bruto) >= 3:
                            argumentos_dit["conteudo"] = _bruto
                        if _titulo:
                            argumentos_dit["titulo"] = _titulo
                    if nome_funcao == "registrar_rotina_jogo" and argumentos_dit.get("opiniao"):
                        # A classificação é do roteador; a opinião guardada é a frase REAL do usuário.
                        argumentos_dit["opiniao"] = prompt_usuario.strip()
                    if argumentos_dit:
                        cor.amarelo(f"[Argumentos enviados: {argumentos_dit}]")
                    resultado_ferramenta = FUNCOES_DISPONIVEIS[nome_funcao](**argumentos_dit)
                    if responder_completo and nome_funcao == "desenhar_imagem":
                        # Telegram: pega os bytes já baixados pela ferramenta e envia como foto
                        from modulos.habilidades import obter_ultima_imagem_bytes
                        _b = obter_ultima_imagem_bytes()
                        if _b:
                            _imagem_pendente = {"tipo": "bytes", "dado": _b}

                _log.info(f"Resultado ({nome_funcao}): {str(resultado_ferramenta)[:300]}")
                lembranca_oculta = f"\n[MEMÓRIA DA FERRAMENTA: A ferramenta {nome_funcao} retornou: {resultado_ferramenta}]"
            else:
                resultado_ferramenta = "Erro: habilidade desconhecida."
        else:
            # Router não chamou ferramenta — descarta o marcador do contrato e qualquer desvio.
            # EXCEÇÃO: no modo_memoria não há ferramentas — a resposta DIRETA do modelo (o JSON) É o resultado.
            resultado_ferramenta = (mensagem_modelo.content or "") if modo_memoria else ""
            if not modo_memoria:
                from modulos import rotina_jogos as _rotina_jogos
                _declaracao = _rotina_jogos.detectar_declaracao(
                    prompt_usuario, nome_contexto=_jogo_contexto_guard)
                if _declaracao:
                    ferramenta_chamada = True
                    inicio_ferramenta = time.time()
                    nome_funcao = "registrar_rotina_jogo"
                    argumentos_dit = _declaracao
                    cor.amarelo("[🎮 Rotina: declaração explícita recuperada pela rede de segurança]")
                    cor.amarelo(f"[Argumentos enviados: {argumentos_dit}]")
                    resultado_ferramenta = _executar_registrar_rotina_jogo(**argumentos_dit)
                    _log.info("Resultado (%s): %s", nome_funcao, resultado_ferramenta)
                    lembranca_oculta = (
                        f"\n[MEMÓRIA DA FERRAMENTA: A ferramenta {nome_funcao} retornou: "
                        f"{resultado_ferramenta}]"
                    )

        if modo_memoria:
            texto_resposta = str(resultado_ferramenta).strip()
            texto_resposta = re.sub(r'^```(?:json)?\s*(.*?)\s*```$', r'\1', texto_resposta, flags=re.DOTALL | re.MULTILINE).strip()
            if texto_resposta.startswith("{'") or texto_resposta.startswith("{ '"):
                texto_resposta = texto_resposta.replace("'", '"')
        else:
            # Broadcast pensamento para interface web
            try:
                import servidor as _srv
                # A caixa "Pensamento" é o RAIO-X da 1ª chamada (o roteador) — serve pra entender
                # POR QUE ela fez o que fez (ex: um "Legal demais!" que virou ler_obsidian à toa).
                partes = []
                if raciocinio:
                    partes.append(f"🧠 Raciocínio:\n{raciocinio.strip()[:600]}")
                if ferramenta_chamada:
                    partes.append(f"⚙️ Ferramenta: {nome_funcao}")
                    try:
                        if argumentos_dit:
                            partes.append(f"📥 Argumentos: {argumentos_dit}")
                    except NameError:
                        pass
                    partes.append(f"📤 Retorno:\n{str(resultado_ferramenta)[:400]}")
                else:
                    partes.append("💭 Nenhuma ferramenta acionada — resposta direta da persona.")
                    # SEM_FERRAMENTA é o encerramento normal e barato. Qualquer outro texto é
                    # desvio útil no diagnóstico, mas continua descartado da resposta.
                    _cru = (getattr(mensagem_modelo, "content", "") or "").strip()
                    if _cru and _cru != "SEM_FERRAMENTA":
                        partes.append(f"🗣️ Roteador falou (descartado):\n{_cru[:300]}")
                _srv.atualizar_pensamento("\n\n".join(partes))
            except Exception:
                pass

            eh_ver_tela = getattr(mensagem_modelo, 'tool_calls', None) and mensagem_modelo.tool_calls[0].function.name == "ver_tela"
            resultado_str = str(resultado_ferramenta)

            # Ferramentas de conteúdo: a persona processa o texto cru (transcrição/artigo) conforme o pedido.
            eh_documento = (ferramenta_chamada and nome_funcao in ("resumir_youtube", "resumir_site", "ler_obsidian")
                            and not resultado_str.startswith(("SISTEMA:", "ERRO", "Erro")))

            if (not ferramenta_chamada) and (not modo_memoria) and _RE_INICIO_SALVAR.match(prompt_usuario or ""):
                # O usuário claramente pediu pra ANOTAR, mas o roteador não firou salvar_obsidian
                # (comum com texto longo). Salva na mão, com o texto fiel, sem depender do 4B.
                _cont, _titulo = _dados_para_anotar(prompt_usuario)
                if _so_comando_salvar(prompt_usuario):
                    _ant = _ultima_fala_do_historico(historico, prompt_usuario)
                    if _ant:
                        _cont = _ant
                _res = (obsidian.salvar_nota(_cont, _titulo or None,
                                             origem=_origem_salvamento(responder_completo))
                        if len(_cont) >= 3 else "SISTEMA: Erro")
                cor.amarelo("[📝 Obsidian: salvo pela rede de segurança (roteador não firou)]")
                texto_resposta = _confirmar_salvamento(
                    _res, _cont, prompt_usuario, historico, max_tokens, responder_completo,
                    ao_fragmento=ao_fragmento,
                )
                lembranca_oculta = ""
            elif (not ferramenta_chamada) and _parece_pedido_de_acao(prompt_usuario):
                # Pedido de ação que o roteador NÃO roteou: resposta honesta determinística,
                # sem deixar a persona inventar a partir da memória recuperada (anti-alucinação).
                cor.vermelho("[⚠️ Pedido de ação sem ferramenta acionada — resposta honesta]")
                texto_resposta = "Hmm, não consegui fazer isso agora. Pode reformular o pedido, ou me mandar o link/detalhe direto?"
            elif eh_documento:
                _quer_resumo = bool(re.search(r'\bresum', prompt_usuario, re.IGNORECASE))
                # Sinais de que a pergunta exige FILTRAR/calcular (ex: "quais NÃO paguei", "quanto falta")
                _quer_filtrar = bool(re.search(r'\b(quais|n[aã]o|quanto|quantos|falta|pendent|pague|pago|apenas|filtr)\b',
                                               prompt_usuario, re.IGNORECASE))
                # As notas de CARD (Novidades.md do radar RSS, Promocoes.md do radar de promoções)
                # NUNCA vêm cruas — são feitas pra ser CONTADAS conversando, senão a Luna "metralha"
                # o markdown com links (avaliações 👎). Detecta pela ASSINATURA da nota (frontmatter
                # do grid ou os callouts), não pela data: o formato do cabeçalho já mudou uma vez
                # (era '## 2026-08-08 15:03', virou '## 08/08/2026') e o guarda parou de pegar.
                _eh_novidades = bool(
                    re.search(r'cssclasses:\s*\n\s*-\s*novidades-grid', resultado_str)
                    or re.search(r'(?m)^>\s*\[!tip\]', resultado_str)
                    or re.search(r'(?m)^##\s*(?:\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}|\d{2}/\d{2}/\d{4})', resultado_str)
                )

                if nome_funcao == "ler_obsidian" and not _quer_resumo and not _quer_filtrar and not _eh_novidades:
                    # Nota do próprio usuário, sem resumo/filtro: devolve FIEL e determinístico
                    # (o 8B parafraseia/garble se deixar ele reescrever — vide "iogue"/"martelo de cozinha").
                    cor.amarelo("[📓 Obsidian: nota devolvida fielmente]")
                    texto_resposta = "Aqui está, do seu Obsidian:\n\n" + resultado_str
                    lembranca_oculta = ""
                else:
                    cor.amarelo("[🎭 Passando para LLM persona...]")
                    if _eh_novidades:
                        tarefa = ("Conte pro usuário as novidades que estão nesta nota, CONVERSANDO — "
                                  "uma frase curta por novidade, no seu tom. NÃO cole o markdown, NÃO "
                                  "despeje links nem títulos crus. Se forem muitas, resuma as principais "
                                  "e diga quantas tem no total.")
                    elif _quer_resumo:
                        tarefa = "Resuma o conteúdo em poucas frases, em português do Brasil."
                    elif re.search(r'transcre', prompt_usuario, re.IGNORECASE):
                        tarefa = "Mostre o conteúdo EXATAMENTE como está, sem reescrever nem inventar."
                    else:
                        tarefa = (
                            "Atenda exatamente ao que o usuário pediu, com base no conteúdo. "
                            "Se ele pediu detalhes (receita, passo a passo, ingredientes COM as quantidades, dados), "
                            "inclua-os fielmente e por completo. Nunca invente o que não está no conteúdo."
                        )
                    texto_resposta = _reescrever_como_luna(
                        resultado_str, prompt_usuario, historico, max_tokens,
                        tarefa_documento=tarefa, responder_completo=responder_completo,
                        ao_fragmento=ao_fragmento,
                    )
                    lembranca_oculta = ""   # não guarda o texto cru na memória
            elif ferramenta_chamada and nome_funcao == "ler_obsidian" and resultado_str.startswith("SISTEMA: SEM_NOTA_RELEVANTE"):
                # A nota não bate com a pergunta (ou não havia nota). Balde A:
                # - pergunta sobre anotação PESSOAL → honesto que não tem;
                # - pergunta de conhecimento geral → responde do que ela sabe (chamada
                #   LIMPA, sem contexto de ferramenta = mesmo caminho de "sem ferramenta").
                if _RE_REF_NOTA_PESSOAL.search(prompt_usuario or ""):
                    cor.amarelo("[📓 Obsidian: sem nota relevante → honestidade]")
                    texto_resposta = "Não achei essa anotação nas suas notas. Quer que eu procure com outras palavras?"
                else:
                    cor.amarelo("[📓 Obsidian: sem nota relevante → resposta de conhecimento]")
                    texto_resposta = _reescrever_como_luna("", prompt_usuario, historico, max_tokens,
                                                           responder_completo=responder_completo,
                                                           ao_fragmento=ao_fragmento)
                lembranca_oculta = ""
            elif ferramenta_chamada and nome_funcao == "salvar_obsidian":
                # O save já aconteceu (determinístico). A persona confirma COMENTANDO o
                # assunto — rico, mas sem poder mentir (o save é fato, não invenção).
                _cont_salvo = conteudo_salvo_turno or _conteudo_para_anotar(prompt_usuario)
                texto_resposta = _confirmar_salvamento(
                    resultado_str, _cont_salvo, prompt_usuario, historico, max_tokens,
                    responder_completo, ao_fragmento=ao_fragmento,
                )
                lembranca_oculta = ""
            elif ferramenta_chamada and nome_funcao == "registrar_rotina_jogo":
                # O registro é fato decidido pelo Python. O 12B já transformou um sucesso real
                # em "deu erro"; ele pode reagir ao conteúdo, mas não auditar a ferramenta.
                if resultado_str.startswith("SISTEMA: rotina de "):
                    _nome_real = re.match(r'^SISTEMA: rotina de (.+) atualizada \(', resultado_str)
                    _nome = (_nome_real.group(1) if _nome_real
                             else str(argumentos_dit.get("nome_jogo") or "jogo").strip())
                    confirmacao = f"Registrei isso na rotina de {_nome}."
                    if argumentos_dit.get("opiniao"):
                        reacao = _reescrever_como_luna(
                            prompt_usuario, prompt_usuario, historico, min(max_tokens, 140),
                            tarefa_documento=(
                                "O registro local JÁ FOI CONCLUÍDO COM SUCESSO e outra frase confirmará isso. "
                                "Reaja somente à opinião ou motivo literal do usuário, em uma frase natural. "
                                "Não invente dificuldade anterior, tempo sobrando, pendência, backlog, promessa, "
                                "hábito ou motivo. Não mencione sistema, ferramenta, rotina, acesso ou registro."
                            ),
                            responder_completo=responder_completo,
                        ).strip()
                        if re.search(r'\b(n[aã]o\s+consegui|deu\s+erro|erro\s+no|n[aã]o\s+registr)',
                                     reacao, re.IGNORECASE):
                            reacao = ""
                    elif argumentos_dit.get("platinado") is True:
                        reacao = "Aí você não deixou nem as conquistas escaparem."
                    elif argumentos_dit.get("platinado") is False:
                        reacao = "A platina continua na mira."
                    elif argumentos_dit.get("estado_jogo") == "zerado":
                        reacao = "Esse entrou oficialmente na lista dos finalizados."
                    elif argumentos_dit.get("estado_jogo") == "abandonado":
                        reacao = "Esse fica na lista dos abandonados."
                    elif argumentos_dit.get("estado_jogo") == "jogando":
                        reacao = "Esse entrou na rotação."
                    else:
                        reacao = ""
                    texto_resposta = confirmacao + (f" {reacao}" if reacao else "")
                else:
                    texto_resposta = "Não consegui registrar isso na rotina do jogo desta vez."
                lembranca_oculta = ""
            elif ferramenta_chamada and nome_funcao == "propor_acompanhamento":
                # A proposta é estado temporário, não um fato ocorrido nem memória de ferramenta.
                texto_resposta = _reescrever_como_luna(
                    resultado_str, prompt_usuario, historico, max_tokens,
                    responder_completo=responder_completo,
                    ao_fragmento=ao_fragmento,
                )
                lembranca_oculta = ""
            elif ferramenta_chamada and nome_funcao == "consultar_animes" and not resultado_str.startswith("SISTEMA:"):
                # O 12B recebeu episódios válidos e mesmo assim respondeu que houve erro.
                # A persona pode dar o tom, mas não reinterpretar nem omitir o placar factual.
                texto_resposta = _reescrever_como_luna(
                    resultado_str, prompt_usuario, historico, max_tokens,
                    tarefa_documento=(
                        "Conte quais episódios saíram e, quando informado, quando sai o próximo. "
                        "Inclua TODOS os animes e números recebidos. A consulta FUNCIONOU: é PROIBIDO "
                        "alegar erro, lista incompleta ou falta de acesso. Seja breve e natural."
                    ),
                    responder_completo=responder_completo,
                    ao_fragmento=ao_fragmento,
                )
                lembranca_oculta = ""
            elif ferramenta_chamada and nome_funcao == "consultar_proprio_codigo":
                texto_resposta = _reescrever_como_luna(
                    resultado_str,
                    prompt_usuario,
                    historico,
                    max_tokens=min(max_tokens, 280),
                    tarefa_documento=(
                        "Responda em primeira pessoa como a Luna, explicando o funcionamento pedido com "
                        "base SOMENTE nos trechos reais fornecidos. Cite os nomes dos módulos ou funções "
                        "que sustentam a resposta, mas não despeje o código inteiro. Separe claramente o "
                        "que o código confirma do que for inferência. Nunca revele nem alegue ter lido "
                        "tokens, `.env`, dados pessoais ou arquivos fora dos trechos. Se o sistema disser "
                        "que o assunto não é seguro/suportado, explique essa limitação honestamente. "
                        "Se houver estado atual em execução, diferencie mecanismo existente de recurso "
                        "ativo. Não cumprimente. PRIORIDADE FINAL: no máximo 140 palavras em dois "
                        "parágrafos curtos, terminando a última frase por completo."
                    ),
                    responder_completo=responder_completo,
                    ao_fragmento=ao_fragmento,
                )
                lembranca_oculta = ""
            elif ferramenta_chamada and nome_funcao == "briefing_diario":
                texto_resposta = _reescrever_como_luna(
                    resultado_str,
                    prompt_usuario,
                    historico,
                    max_tokens=min(max_tokens, 320),
                    tarefa_documento=(
                        "Monte um briefing pessoal CONVERSANDO, não um relatório. Escolha de dois a quatro "
                        "destaques realmente úteis entre as fontes; não precisa citar seção vazia nem fonte "
                        "isoladamente indisponível. Preserve nomes, datas, horários, episódios e valores. "
                        "Não diga que algo acontece hoje se o dado só informa uma data futura. Termine com "
                        "UMA pergunta curta e específica baseada em um dos destaques, oferecendo aprofundar "
                        "aquele assunto. Clima é informação, não pretexto para cobrar foco, produtividade ou "
                        "mandar o usuário sair de casa. Não use listas, títulos ou markdown e não invente "
                        "recomendação que os dados não sustentem."
                    ),
                    responder_completo=responder_completo,
                    ao_fragmento=ao_fragmento,
                )
                lembranca_oculta = ""
            elif ferramenta_chamada and nome_funcao == "consultar_pendencias":
                texto_resposta = _reescrever_como_luna(
                    resultado_str,
                    prompt_usuario,
                    historico,
                    max_tokens=min(max_tokens, 320),
                    tarefa_documento=(
                        "Responda somente com o que continua aberto. Diferencie tarefa do Obsidian, "
                        "compromisso futuro da agenda e acompanhamento esperando desfecho; não chame "
                        "aniversário ou outro compromisso de tarefa atrasada. Omita categorias vazias e "
                        "fontes isoladamente indisponíveis. Preserve nomes, datas e horários. Se a consulta "
                        "foi específica, responda só sobre aquele assunto. Use blocos curtos no canal de "
                        "texto e não invente urgência, prazo ou pendência ausente nos dados."
                    ),
                    responder_completo=responder_completo,
                    ao_fragmento=ao_fragmento,
                )
                lembranca_oculta = ""
            elif ferramenta_chamada and nome_funcao == "concluir_tarefa_obsidian":
                # A pergunta exata vem do Python porque contém a linha que será editada.
                # Reescrevê-la com o 12B poderia trocar o item depois de ele já estar travado no estado.
                texto_resposta = resultado_str
                lembranca_oculta = ""
            else:
                cor.amarelo("[🎭 Passando para LLM persona...]")
                texto_resposta = _reescrever_como_luna(
                    resultado_str, prompt_usuario, historico, max_tokens,
                    forcar_incluir=eh_ver_tela, responder_completo=responder_completo,
                    ao_fragmento=ao_fragmento,
                )

                # Resultados CURTOS (ex: "música pausada"): garante UMA frase da persona.
                # Resultados LONGOS (agenda, emails): a persona apresenta os dados por completo
                # (mesmo caminho do Telegram) — NÃO cola mais o texto cru da ferramenta.
                if ferramenta_chamada and not eh_ver_tela and not responder_completo and len(resultado_str) <= 200:
                    match = re.search(r'[^.!?]*[.!?]+', texto_resposta)
                    frase_luna = match.group(0).strip() if match and len(match.group(0).strip()) > 10 else texto_resposta.split('\n')[0]
                    texto_resposta = frase_luna

        texto_para_memoria = texto_resposta + lembranca_oculta

        historico.append({"role": "user", "content": prompt_usuario})
        _turno_assistente = {"role": "assistant", "content": texto_resposta}
        if (ferramenta_chamada and nome_funcao == "duvida_do_jogo"
                and str(resultado_ferramenta).startswith("SISTEMA: Resultado da pesquisa")):
            # Metadado local: autoriza um follow-up curto somente após uma consulta que
            # realmente funcionou. _hist_curto não envia essas chaves extras ao modelo.
            _turno_assistente["_ferramenta"] = "duvida_do_jogo"
            _turno_assistente["_jogo"] = str(argumentos_dit.get("nome_jogo") or "").strip()
        historico.append(_turno_assistente)

        if len(historico) > 12:
            del historico[:-12]   # corta in-place — reatribuir não cortaria a lista do chamador

        _log.info(f"Luna: {texto_resposta[:200]}")
        if salvar:
            salvar_conversa(prompt_usuario, texto_para_memoria)

        if analisar and ATIVAR_MEMORIA_PERMANENTE:
            threading.Thread(
                target=analisar_e_salvar_fato,
                args=(prompt_usuario, texto_para_memoria, gerar_resposta),
                daemon=True
            ).start()

        if ferramenta_chamada:
            try:
                from modulos import metricas_ferramentas
                _resultado = str(resultado_ferramenta).lstrip()
                _sucesso = not _resultado.startswith(("Erro", "ERRO", "SISTEMA: Erro", "SISTEMA: Não consegui"))
                metricas_ferramentas.registrar_uso(
                    nome_funcao, _sucesso, time.time() - inicio_ferramenta,
                    prompt_usuario, texto_resposta,
                    "telegram" if responder_completo else "web",
                )
            except Exception:
                _log.exception("Não foi possível registrar a métrica da ferramenta")

        return texto_resposta

    except GeracaoInterrompida:
        raise
    except Exception as e:
        _msg = str(e).lower()
        if any(s in _msg for s in ("context size", "context_size", "exceeds the available context",
                                    "exceed_context")):
            historico.clear()
            cor.vermelho("[Memória: histórico limpo por contexto cheio]")
            _log.warning("Contexto da LLM cheio — histórico limpo")
            return "Opa, minha memória de curto prazo encheu — limpei ela. Manda de novo?"
        _log.exception(f"Erro no motor de raciocínio: {e}")
        return f"Desculpe, deu um curto-circuito na minha conexão: {e}"
