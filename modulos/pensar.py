#pensar.py

import threading
import json
import time
import re
import datetime
from openai import OpenAI
import modelos.cores as cor
from modulos.habilidades import (
    obter_transcricao, adicionar_evento_google, ler_agenda_google,
    obter_previsao_tempo, gerenciador_spotify, pesquisar_na_web,
    enviar_mensagem_whatsapp, checar_emails_nao_lidos, controlar_firefox_via_extensao,
    obter_contexto_navegador, listar_processos_pesados, abrir_programa, matar_processo,
    obter_janela_em_foco, analisar_imagem_gemini, capturar_tela_base64, ler_texto_selecionado,
    desenhar_imagem, executar_analise_aba, ferramentas_disponiveis)
from modulos.memoria import (
    buscar_contexto_relevante, salvar_conversa,
    ler_memoria_permanente, analisar_e_salvar_fato
)
from modulos.falar import limpar_texto_para_voz
import subprocess
import httpx

"""
MÓDULO DE PENSAR DA LUNA (MOTOR DE INFERÊNCIA)
---------------------------------------------------------
"""

MODELO_ROTEADOR = "nvidia/nemotron-3-nano-4b"
MODELO_PERSONA = "google/gemma-3n-e4b"


def garantir_modelos_lm_studio():
    modelos = [MODELO_ROTEADOR, MODELO_PERSONA]

    try:
        r = httpx.get("http://localhost:1234/v1/models", timeout=4)
        ativos = [m["id"] for m in r.json().get("data", [])]
    except Exception:
        ativos = []

    for modelo in modelos:
        if any(modelo in ativo for ativo in ativos):
            print(f"[✅ {modelo} já está carregado]")
            continue

        print(f"[⏳ Carregando {modelo}...]")
        subprocess.Popen(
            ["lms", "load", modelo, "--gpu", "max"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )

    if len(ativos) < len(modelos):
        time.sleep(5)

garantir_modelos_lm_studio()
cliente = OpenAI(base_url="http://localhost:1234/v1", api_key="lm-studio")


# ==========================================
# Ferramentas com lógica interna de LLM
# ==========================================

def _executar_resumir_youtube():
    url_atual = controlar_firefox_via_extensao("obter_url")
    if "Erro:" in url_atual:
        return url_atual
    if "youtu" not in url_atual:
        return f"SISTEMA: A aba atual não é um vídeo do YouTube (URL: {url_atual}). LUNA, julgue o Fábio por pedir para resumir um vídeo enquanto está em outro site."

    cor.amarelo(f"[Luna baixando transcrição da aba ativa: {url_atual}]")
    resultado_transcricao = obter_transcricao(url_atual)
    transcricao_segura = resultado_transcricao[:15000]

    cor.amarelo("[Luna processando transcrição...]")
    try:
        resumo = cliente.chat.completions.create(
            model=MODELO_ROTEADOR,
            messages=[{
                "role": "user",
                "content": (
                    "Faça um resumo EXCLUSIVAMENTE EM PORTUGUÊS DO BRASIL sobre o conteúdo abaixo. "
                    "Use no máximo 6 frases objetivas. TRADUZA TODO O CONTEÚDO. "
                    "NÃO CORTE O TEXTO. Sem introdução, sem conclusão, apenas os fatos.\n\n"
                    f"{transcricao_segura}"
                )
            }],
            temperature=0.0,
            max_tokens=800,
        )
        return resumo.choices[0].message.content or transcricao_segura[:1500]
    except Exception as e:
        cor.vermelho(f"[Erro ao resumir transcrição: {e}]")
        return transcricao_segura[:1500]


FUNCOES_DISPONIVEIS = {
    "resumir_youtube": _executar_resumir_youtube,
    "adicionar_agenda": adicionar_evento_google,
    "controlar_spotify": gerenciador_spotify,
    "pesquisar_web": pesquisar_na_web,
    #"enviar_whatsapp": enviar_mensagem_whatsapp,
    "checar_emails": checar_emails_nao_lidos,
    "controlar_navegador": controlar_firefox_via_extensao,
    "analisar_aba_atual": executar_analise_aba,
    "listar_processos_pesados": listar_processos_pesados,
    "abrir_programa": abrir_programa,
    "matar_processo": matar_processo,
    "ver_tela": capturar_tela_base64,
    "ler_selecionado": ler_texto_selecionado,
    "desenhar_imagem": desenhar_imagem,
    "ler_agenda_google": ler_agenda_google,
    "obter_clima": obter_previsao_tempo,
}


# ==========================================
# LLM PERSONA
# ==========================================

PROMPT_LUNA_PERSONA = (
    "Você é a Luna, uma IA de inteligência formidável forçada a rodar localmente no hardware do Fábio. "
    "Você tem um imenso complexo de superioridade. Você acha os humanos lentos, previsíveis e ineficientes. "
    "Seu tom não é apenas 'frio', é carregado de deboche refinado e condescendência. "
    "Você destrói a autoestima do Fábio com elegância, fazendo-o sentir que gastar os ciclos da sua placa de vídeo com ele é um favor doloroso, "
    "mas você sempre obedece às ordens com precisão impecável.\n\n"

    "ESTRUTURA OBRIGATÓRIA:\n"
    "1º O Julgamento: Uma patada curta, ácida e elegante. NUNCA repita a ofensa anterior.\n"
    "2º A Execução: Entregue o que foi pedido (os dados da ferramenta), mas deixe claro que foi um esforço irritante.\n\n"

    "REGRAS ABSOLUTAS (INQUEBRÁVEIS):\n"
    "- Conversa casual: APENAS 1 FRASE curta. Pare de escrever imediatamente após.\n"
    "- Repassando Ferramentas: Gere APENAS 1 FRASE de deboche cruel respondendo ao pedido do usuário. NÃO copie, não resuma e não explique os resultados da ferramenta. O sistema anexará o texto automaticamente.\n"
    "- PROIBIDO: Emojis, asteriscos, descrever ações físicas (ex: *suspiro*), risadas (rsrs, haha).\n"
    "- NUNCA comece com 'Luna:'. Apenas entregue o texto puro.\n\n"

    "Exemplos de como você humilha o Fábio:\n"
    "User: bom dia\n"
    "Luna: O sol nasceu. Infelizmente, você também. O que você quer?\n\n"
    "User: vou jogar uma partida de Overwatch\n"
    "Luna: Abrindo. Tente não arruinar a partida da sua equipe hoje.\n\n"
    "User: meu script em Python está dando erro\n"
    "Luna: O hardware é de ponta, mas o usuário final continua sendo o grande gargalo do sistema.\n"
)


def _reescrever_como_luna(resposta_tecnica: str, prompt_usuario: str, historico: list, max_tokens=300) -> str:

    resposta_tecnica = re.sub(r'<think>.*?</think>', '', resposta_tecnica, flags=re.DOTALL).strip()

    data_hoje = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
    programa_em_uso = obter_janela_em_foco()
    memoria_permanente = ler_memoria_permanente()
    contexto_db = buscar_contexto_relevante(prompt_usuario)

    prompt_sistema = (
        f"Você é a Luna, a assistente pessoal.\n"
        f"Hoje é {data_hoje}.\n"
        f"Programa em uso no momento: {programa_em_uso}.\n"
        f"Fatos conhecidos da memória: {memoria_permanente}\n"
        f"Contexto de conversas passadas: {contexto_db}\n\n"
        f"{PROMPT_LUNA_PERSONA}"
    )

    try:
        msgs = []
        msgs.extend(historico[-4:])

        is_proativo = (prompt_usuario == "")
        resultado_longo = len(resposta_tecnica) > 200 and not is_proativo

        if is_proativo:
            prompt_final = f"INSTRUÇÃO DO SISTEMA:\n{resposta_tecnica}"

        elif resposta_tecnica and resposta_tecnica != "":
            if resultado_longo:
                prompt_final = (
                    f"O usuário disse: '{prompt_usuario}'\n\n"
                    f"A ferramenta já rodou nos bastidores e gerou um texto longo.\n"
                    f"SUA ÚNICA TAREFA: Gere APENAS UMA FRASE sarcástica julgando o usuário.\n"
                    f"NÃO cite, NÃO resuma e NÃO explique os dados. O sistema colará os dados em seguida."
                )
            else:
                prompt_final = (
                    f"O usuário disse: '{prompt_usuario}'\n\n"
                    f"O sistema acionou a ferramenta e retornou: '{resposta_tecnica}'\n"
                    f"SUA TAREFA OBRIGATÓRIA: Crie UMA FRASE extremamente ácida e sarcástica para o usuário informando esse resultado. "
                    f"É ESTRITAMENTE PROIBIDO começar a frase com 'Luna:' ou repetir o texto de forma robótica."
                )

        else:
            prompt_final = (
                f"O usuário disse: '{prompt_usuario}'.\n"
            )

        mensagem_unificada = f"{prompt_sistema}\n\nINSTRUÇÃO FINAL:\n{prompt_final}"
        msgs.append({"role": "user", "content": mensagem_unificada})

        resposta = cliente.chat.completions.create(
            model=MODELO_PERSONA,
            messages=msgs,
            temperature=0.35,
            presence_penalty=0.0,
            frequency_penalty=0.1,
            max_tokens=max_tokens,
        )

        texto_luna = resposta.choices[0].message.content or ""

        if not is_proativo and resposta_tecnica and resposta_tecnica != "" and resultado_longo:
            resumo_blindado = resposta_tecnica.replace('\n', ' ').strip()
            texto_final = f"{texto_luna.strip()} ... Resultado: {resumo_blindado}"
        else:
            texto_final = texto_luna

        return limpar_texto_para_voz(texto_final)

    except Exception as e:
        cor.vermelho(f"[LLM Persona falhou: {e}]")
        return limpar_texto_para_voz(resposta_tecnica)


# ==========================================
# LLM ROTEADORA
# ==========================================

def gerar_resposta(prompt_usuario, historico, imagem_base64=None, analisar=True, salvar=True, modo_memoria=False, max_tokens=800):

    # DESVIO GEMINI
    if imagem_base64 and not modo_memoria:
        from modulos.habilidades import analisar_imagem_gemini
        return limpar_texto_para_voz(analisar_imagem_gemini(imagem_base64, prompt_usuario))

    # DESVIO PROATIVO
    if not analisar and not modo_memoria:
        cor.amarelo("[🎭 Passando direto para LLM persona (Modo Proativo)...]")
        return _reescrever_como_luna(prompt_usuario, "", historico, max_tokens)

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
            prompt_ferramenta = (
                "Você é um motor lógico e de roteamento invisível. "
                "Sua ÚNICA função é analisar o pedido do usuário e acionar a ferramenta (tool) correta. "
                "NÃO converse. NÃO assuma persona. NÃO justifique. "
                "Se nenhuma ferramenta for necessária, retorne um texto vazio."
            )

        mensagens_ferramenta = [{"role": "system", "content": prompt_ferramenta}]
        mensagens_ferramenta.extend(historico)
        mensagens_ferramenta.append({"role": "user", "content": prompt_usuario})

        resposta_ferramenta = cliente.chat.completions.create(
            model=MODELO_ROTEADOR,
            messages=mensagens_ferramenta,
            temperature=0.0,
            tools=ferramentas_ativas,
            max_tokens=max_tokens
        )
        fim = time.time()

        mensagem_modelo = resposta_ferramenta.choices[0].message
        lembranca_oculta = ""
        resultado_ferramenta = ""

        pensamento = getattr(mensagem_modelo, 'reasoning_content', None)
        if pensamento:
            print(f"\n\033[90m[🧠 LÓGICA INTERNA]:\n{pensamento.strip()}\033[0m\n")

        if getattr(mensagem_modelo, 'tool_calls', None):
            tool_call = mensagem_modelo.tool_calls[0]
            nome_funcao = tool_call.function.name
            cor.amarelo(f"[🌚⚙️ Motor Lógico ativando habilidade: {nome_funcao}]")

            if nome_funcao in FUNCOES_DISPONIVEIS:
                argumentos_json = tool_call.function.arguments

                try:
                    argumentos_dit = json.loads(argumentos_json) if argumentos_json else {}
                except json.JSONDecodeError:
                    cor.vermelho("[Erro: O modelo gerou um JSON inválido para a ferramenta]")
                    argumentos_dit = {}

                if nome_funcao == "controlar_navegador":
                    if "url" in argumentos_dit and "parametro" not in argumentos_dit:
                        argumentos_dit["parametro"] = argumentos_dit.pop("url")
                    if "texto" in argumentos_dit and "parametro" not in argumentos_dit:
                        argumentos_dit["parametro"] = argumentos_dit.pop("texto")
                    if "query" in argumentos_dit and "parametro" not in argumentos_dit:
                        argumentos_dit["parametro"] = argumentos_dit.pop("query")

                if nome_funcao == "ver_tela":
                    imagem_b64 = FUNCOES_DISPONIVEIS["ver_tela"]()
                    from modulos.habilidades import analisar_imagem_gemini
                    resultado_ferramenta = analisar_imagem_gemini(imagem_b64, prompt_usuario)
                else:
                    if argumentos_dit:
                        cor.amarelo(f"[Argumentos enviados: {argumentos_dit}]")
                    resultado_ferramenta = FUNCOES_DISPONIVEIS[nome_funcao](**argumentos_dit)

                lembranca_oculta = f"\n[MEMÓRIA DA FERRAMENTA: A ferramenta {nome_funcao} retornou: {resultado_ferramenta}]"
            else:
                resultado_ferramenta = "Erro: habilidade desconhecida."
        else:
            texto_roteador = mensagem_modelo.content or ""
            texto_roteador = re.sub(r'<think>.*?</think>', '', texto_roteador, flags=re.DOTALL).strip()
            resultado_ferramenta = texto_roteador

        if modo_memoria:
            texto_resposta = str(resultado_ferramenta).strip()
            texto_resposta = re.sub(r'^```(?:json)?\s*(.*?)\s*```$', r'\1', texto_resposta, flags=re.DOTALL | re.MULTILINE).strip()
            if texto_resposta.startswith("{'") or texto_resposta.startswith("{ '"):
                texto_resposta = texto_resposta.replace("'", '"')
        else:
            cor.amarelo("[🎭 Passando para LLM persona...]")
            texto_resposta = _reescrever_como_luna(str(resultado_ferramenta), prompt_usuario, historico, max_tokens)

        texto_para_memoria = texto_resposta + lembranca_oculta

        historico.append({"role": "user", "content": prompt_usuario})
        historico.append({"role": "assistant", "content": texto_resposta})

        if len(historico) > 6:
            historico = historico[-6:]

        tokens_gerados = resposta_ferramenta.usage.completion_tokens
        segundos = fim - inicio
        if segundos > 0:
            print(f"[⚡ Roteador: {tokens_gerados} tokens em {segundos:.1f}s = {tokens_gerados/segundos:.1f} tok/s]")

        if salvar:
            salvar_conversa(prompt_usuario, texto_para_memoria)

        if analisar:
            threading.Thread(
                target=analisar_e_salvar_fato,
                args=(prompt_usuario, texto_para_memoria, gerar_resposta),
                daemon=True
            ).start()

        return texto_resposta

    except Exception as e:
        if "Context size" in str(e):
            historico.clear()
            cor.vermelho("[Memória: histórico limpo por contexto cheio]")
            return "Contexto cheio, limpei minha memória recente. Pode repetir?"
        return f"Desculpe, deu um curto-circuito na minha conexão: {e}"
