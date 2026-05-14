#pensar.py

import threading
import json
import time
import re
import datetime
from openai import OpenAI
import modelos.cores as cor
from modulos.habilidades import (
    obter_transcricao, adicionar_evento_google,ler_agenda_google, 
    obter_previsao_tempo, gerenciador_spotify, pesquisar_na_web,
    enviar_mensagem_whatsapp,checar_emails_nao_lidos, controlar_firefox_via_extensao,
    obter_contexto_navegador,listar_processos_pesados, abrir_programa, matar_processo,
    obter_janela_em_foco, analisar_imagem_gemini, capturar_tela_base64, ler_texto_selecionado,
    desenhar_imagem)
from modulos.memoria import (
    buscar_contexto_relevante, salvar_conversa,
    ler_memoria_permanente, analisar_e_salvar_fato
)


""" 
MÓDULO DE PENSAR DA LUNA (MOTOR DE INFERÊNCIA)
---------------------------------------------------------
Este arquivo é o Cérebro do sistema. Ele faz a ponte de comunicação 
com o modelo local (via LM Studio) e gerencia o Tool Calling.

Integrações principais:
- Recebe inputs do `ouvir.py`.
- Envia outputs para o `falar.py`.
- Aciona funções do `habilidades.py`.
- Processa e envia logs para a memória permanente via `memoria.py`.
- Atua como motor de texto para o `proativo.py` (que roda em thread separada).

FERRAMENTAS DISPONÍVEIS (TOOL CALLING): 
[SISTEMA E TELA]
- abrir_programa: Inicia um aplicativo no SO.
- matar_processo: Força o encerramento de um programa (OBS: pendente de remoção).
- listar_processos_pesados: Retorna os programas que mais consomem recursos.
- ver_tela: Usa a API do Gemini para interpretar uma captura de tela.
- ler_selecionado: Simula Ctrl+C para ler o texto em destaque.

[WEB E NAVEGADOR]
- pesquisar_web: Busca informações atualizadas no DuckDuckGo.
- controlar_navegador: Controla o Firefox (abrir, fechar, digitar).
- analisar_aba_atual: Lê o conteúdo da página aberta no Firefox.

[SERVIÇOS E MÍDIA]
- resumir_youtube: Extrai legendas e resume o conteúdo do vídeo.
- controle_spotify: Gerencia a reprodução (play, pause, next).
- enviar_whatsapp: Abre o WhatsApp, seleciona contato e envia a mensagem.
- desenhar_imagem: Gera uma imagem usando uma API de terceiros.

[PRODUTIVIDADE (GOOGLE)]
- ler_agenda_google: Retorna os eventos agendados.
- adicionar_agenda: Cria um novo evento no Google Calendar.
- checar_emails: Varre a caixa de entrada em busca de e-mails não lidos.
- obter_clima: Retorna a previsão meteorológica local.

Fluxo final: Após executar a ação e gerar a resposta, o módulo aciona o LM Studio 
mais uma vez para sumarizar a interação e salvar na memória permanente.
"""


cliente = OpenAI(base_url="http://localhost:1234/v1", api_key="lm-studio")

MODELO_LLM = "qwen3-8b"
#MODELO_LLM = "qwen2.5-7b-instruct-abliterated-v3"


# ==========================================
# Mapa de funções reais disponíveis
# ==========================================


def executar_analise_aba():
    contexto = obter_contexto_navegador()
    
    # Verifica se a resposta foi convertida com sucesso para dicionário
    if isinstance(contexto, dict):
        relatorio = (
            f"SISTEMA: O Fábio está olhando para a seguinte tela agora:\n"
            f"TÍTULO: {contexto.get('titulo', 'Desconhecido')}\n"
            f"URL: {contexto.get('url', 'Desconhecida')}\n"
            f"CONTEÚDO:\n{contexto.get('texto', '')}\n\n"
            "Fale algo em uma frase."
        )
        return relatorio
    
    # Se falhou ou a extensão mandou um erro em texto, apenas devolve o erro
    return contexto

def _executar_resumir_youtube():
    url_atual = controlar_firefox_via_extensao("obter_url")
    # 2. Tratamento de erro caso o Firefox esteja desligado
    if "Erro:" in url_atual:
        return url_atual 
    # 3. Verifica se o Fábio realmente está no YouTube
    if "youtu" not in url_atual:
        return f"SISTEMA: A aba atual não é um vídeo do YouTube (URL: {url_atual}). LUNA, julgue o Fábio por pedir para resumir um vídeo enquanto está em outro site."
    cor.amarelo(f"[Luna baixando transcrição da aba ativa: {url_atual}]")
    # 4. Chama a sua função original que já funciona
    resultado_transcricao = obter_transcricao(url_atual)
    return resultado_transcricao

FUNCOES_DISPONIVEIS = {
    "resumir_youtube": _executar_resumir_youtube, # ok
    "adicionar_agenda": adicionar_evento_google, # ok
    "controle_spotify": gerenciador_spotify, # ok
    "pesquisar_web": pesquisar_na_web, # ok
    "enviar_whatsapp": enviar_mensagem_whatsapp,#ok
    "checar_emails": checar_emails_nao_lidos, # ok
    "controlar_navegador": controlar_firefox_via_extensao,# OK
    "analisar_aba_atual": executar_analise_aba, # ok
    "listar_processos_pesados":listar_processos_pesados,#ok
    "abrir_programa":abrir_programa, # AINDA NAO TESTEI
    "matar_processo":matar_processo,#ok
    "ver_tela": capturar_tela_base64, # ok
    "ler_selecionado": ler_texto_selecionado, # ok
    "desenhar_imagem": desenhar_imagem, # tem que revisar isso, esse é muito fraquim
    "ler_agenda_google" :ler_agenda_google, # ok
    "obter_clima" : obter_previsao_tempo, #ok
    
}

ferramentas_disponiveis = [
    #tratar videos youtube
    {
        "type": "function",
        "function": {
            "name": "resumir_youtube",
            "description": "Resume o vídeo do YouTube que o Fábio está assistindo AGORA na aba ativa do Firefox." 
            "Use esta função sempre que ele pedir para 'resumir este vídeo' ou 'sobre o que é esse vídeo'.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    
    #tratar agenda google
    {
        "type": "function",
        "function": {
            "name": "adicionar_agenda",
            "description": "Cria um NOVO evento na agenda. NUNCA use esta ferramenta para consultar ou ler a agenda. Use APENAS quando o Fábio pedir explicitamente para 'marcar', 'agendar' ou 'adicionar' um compromisso novo. Se o nome do evento não for informado, pergunte ao Fábio antes de criar.",
            "parameters": {
                "type": "object",
                "properties": {
                    "resumo": {
                        "type": "string",
                        "description": "O nome do evento."
                    },
                    "data_hora_iso": {
                        "type": "string",
                        "description": "Data e hora no formato ISO."
                    }
                },
                "required": ["resumo", "data_hora_iso"]
            }
        }
    },

    # tratar Spotfy tocar musica
    {
        "type": "function",
        "function": {
            "name": "controle_spotify",
            "description": "Use para tocar uma música específica no Spotify do usuário.",
            "parameters": {
                "type": "object",
                "properties": {
                    "acao": {
                        "type": "string",
                        "enum": ["tocar"], 
                        "description": "A ação desejada no Spotify."
                    },
                    "nome_musica": {
                        "type": "string", 
                        "description": "Nome da música/artista. Se o usuário não especificar, use os gostos do Fábio como um padrão"
                    }
                },
                "required": ["acao"]
            }
        }
    },

    # Pesquisar na web
    {
    "type": "function",
    "function": {
        "name": "pesquisar_web",
        "description": "Use esta ferramenta SEMPRE que você precisar de informações atualizadas, notícias, dados recentes, ou se não souber a resposta para uma pergunta do usuário.",
        "parameters": {
            "type": "object",
            "properties": {
                "pergunta": {
                    "type": "string", 
                    "description": (
                        "Use SEMPRE que precisar de informações sobre jogos, notícias, preços, "
                        "lançamentos ou qualquer dado que você não tem certeza absoluta. "
                        "É PROIBIDO inventar informações — se não souber, pesquise."
                    ),
                }
            },
            "required": ["pergunta"]
            }
        }
    },

    # Whatsapp
    {
        "type": "function",
        "function": {
            "name": "enviar_whatsapp",
            "description": "Use para enviar uma mensagem de WhatsApp para alguém.",
            "parameters": {
                "type": "object",
                "properties": {
                    "destinatario": {
                        "type": "string", 
                        "description": "O NOME da pessoa (ex: 'mãe', 'amor', 'fábio') OU o número de telefone."
                    },
                    "mensagem": {
                        "type": "string", 
                        "description": "O texto exato da mensagem que deve ser enviada."
                    }
                },
                "required": ["destinatario", "mensagem"]
            }
        }
    },

    #tratar Gmail
    {
        "type": "function",
        "function": {
            "name": "checar_emails",
            "description": "Use para ver os novos e-mails. ATENÇÃO: Esta ferramenta retorna APENAS o Remetente e o Assunto. Você NÃO tem acesso ao corpo do e-mail e NUNCA deve inventar o conteúdo dele.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },

   #Tratar manipular firefox
    {
        "type": "function",
        "function": {
            "name": "controlar_navegador",
            "description": "Controla a aba ativa do Firefox. Ações disponíveis: 'abrir_url', 'clicar', 'ler_texto', 'rolar_baixo', 'digitar_texto', 'fechar_aba', 'navegacao' e 'controle_midia'.",
            "parameters": {
                "type": "object",
                "properties": {
                    "acao": {
                        "type": "string",
                        "enum": ["abrir_url", "clicar", "ler_texto", "rolar_baixo", "digitar_texto", 
                                "navegacao", "controle_midia", "listar_abas", "trocar_aba"], #"fechar_aba" 
                        "description": "A ação principal."
                    },
                    "parametro": {
                        "type": "string",
                        "description": (
                            "Controla o Firefox. Use SEMPRE que o Fábio pedir para abrir um site, digitar algo, clicar, rolar a página. "
                            "Para digitar na barra de pesquisa use acao='digitar_texto' e parametro='texto a digitar'. "
                            "NUNCA confirme uma ação sem ter chamado esta ferramenta. "
                            "Cada ação é uma chamada separada — abrir o site e digitar são duas chamadas diferentes."
                        ),
                    }
                },
                "required": ["acao"]
            }
        }
    },

    #Tratar ver aba firefox
    {
        "type": "function",
        "function": {
            "name": "analisar_aba_atual",
            "description": (
                "Lê o CONTEÚDO TEXTUAL da aba ativa do Firefox. "
                "Use APENAS quando o Fábio perguntar sobre o conteúdo de uma página web. "
                "NÃO use para ver a tela visualmente — para isso use ver_tela."
            ),
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },

    #Tratar listar processos.
    {
        "type": "function",
        "function": {
            "name": "listar_processos_pesados",
            "description": "Lista os 5 programas que mais estão consumindo memória RAM no PC do Fábio agora. Use quando ele reclamar de lentidão, FPS caindo, ou pedir para ver os processos.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },

    #Tratar abrir programas.
    {
        "type": "function",
        "function": {
            "name": "abrir_programa",
            "description": "Abre um programa ou jogo no computador do Fábio.",
            "parameters": {
                "type": "object",
                "properties": {
                    "nome_programa": {
                        "type": "string",
                        "description": "O nome do programa para abrir. Ex: 'dota', 'obsidian', 'firefox'."
                    }
                },
                "required": ["nome_programa"]
            }
        }
    },

    # Tratar matar programa ou processos
    {
        "type": "function",
        "function": {
            "name": "matar_processo",
            "description": "Força o fechamento de um programa que travou ou que está pesando no PC.",
            "parameters": {
                "type": "object",
                "properties": {
                    "nome_processo": {
                        "type": "string",
                        "description": "O nome do executável sem o '.exe'. Ex: 'Firefox', 'obsidian', 'dota2'."
                    }
                },
                "required": ["nome_processo"]
            }
        }
    },

# Ver tela com print
    {
    "type": "function",
    "function": {
        "name": "ver_tela",
        "description": (
            "Captura a tela atual do usuário. USE APENAS quando o Fábio pedir explicitamente para olhar a tela AGORA. "
            "É ESTRITAMENTE PROIBIDO usar esta ferramenta se a pergunta for sobre o PASSADO (ex: 'o que você viu?', 'o que você falou agora a pouco na tela?'). "
            "Para perguntas sobre o passado, NÃO chame esta ferramenta, apenas use a sua memória e leia o histórico. "
            "NÃO use analisar_aba_atual para isso — são ferramentas diferentes. NÃO use para texto selecionado."
        ),
        "parameters": {
            "type": "object",
            "properties": {},
            "required": []
        }
    }
    },

    #ler o que selecionei 
    {
    "type": "function",
    "function": {
        "name": "ler_selecionado",
        "description": (
            "Use SEMPRE que o Fábio pedir para ler texto selecionado. "
            "Palavras que ativam esta ferramenta: 'selecionei', 'marquei', 'selecionado', "
            "'o que está escrito', 'leia isso', 'leia aqui', 'leia o texto'. "
            "NUNCA invente o conteúdo. SEMPRE chame esta ferramenta antes de responder."
        ),
        "parameters": {
            "type": "object",
            "properties": {},
            "required": []
        }
    }
},

    # FERRAMENTAR DESENHAR
    {
        "type": "function",
        "function": {
            "name": "desenhar_imagem",
            "description": "Gera uma imagem. Use quando o Fábio pedir um desenho.",
            "parameters": {
                "type": "object",
                "properties": {
                    "prompt_imagem": {
                        "type": "string",
                        "description": (
                            "A descrição da imagem EM INGLÊS. "
                            "Sempre adicione no final: '2D anime style, Studio Ghibli inspired, soft colors, clean lineart, correct anatomy, two arms, detailed face with eyes, NOT western cartoon, NOT DC comics, NOT Marvel'."
                        ),
                    }
                },
                "required": ["prompt_imagem"]
            }
        }
    },

    #ler agenda google
    {
        "type": "function",
        "function": {
            "name": "ler_agenda_google",
            "description": "Lê os eventos e compromissos que o Fábio já tem agendados para hoje. USE ESTA FERRAMENTA SEMPRE que ele perguntar 'o que eu tenho para hoje', 'qual minha agenda', 'quais meus compromissos'.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },

    #Obter Clima
    {
        "type": "function",
        "function": {
            "name": "obter_clima",
            "description": "Obtém a previsão do tempo e a temperatura atual de onde o Fábio está. Use sempre se precisar saber sobre o clima ou se vai chuva.",
            "parameters": {
                "type": "object",
                "properties": {}
            }
        }
    }
]



def limpar_texto_para_voz(texto):
    if not texto:
        return ""
    
    texto = re.sub(r'^\[[\w]+\]\s*', '', texto)

    if re.match(r'^\s*\{.*\}\s*$', texto, re.DOTALL):
        return ""
    
    # Remove markdown de formatação
    texto = re.sub(r'\*+', '', texto)        # * e **
    texto = re.sub(r'#+\s*', '', texto)      # # títulos
    texto = re.sub(r'`+', '', texto)         # `código`
    texto = re.sub(r'_{1,2}(.*?)_{1,2}', r'\1', texto)  # _italico_
    texto = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', texto)  # [link](url) → só o texto
    
    # Remove listas numeradas e bullets
    texto = re.sub(r'^\s*[\*\-•]\s+', '', texto, flags=re.MULTILINE)
    texto = re.sub(r'^\s*\d+\.\s+', '', texto, flags=re.MULTILINE)
    
    # Limpa linhas em branco extras
    texto = re.sub(r'\n{2,}', '\n', texto)
    texto = texto.strip()
    
    return texto

def gerar_resposta(prompt_usuario, historico, imagem_base64=None, analisar=True, salvar=True, modo_memoria=False):

        # DESVIO GEMINI — antes de qualquer outra coisa
    if imagem_base64 and not modo_memoria:
        from modulos.habilidades import analisar_imagem_gemini
        return limpar_texto_para_voz(analisar_imagem_gemini(imagem_base64, prompt_usuario))
        #FIM DO DESVIO DO GEMINI IMAGENS

    data_hoje = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")

    if not modo_memoria:
        programa_em_uso = obter_janela_em_foco()
    else:
        programa_em_uso = ""

    memoria_permanente = ler_memoria_permanente()
    contexto = buscar_contexto_relevante(prompt_usuario)
    programa_em_uso = obter_janela_em_foco()


    if modo_memoria:
        # Prompt frio e direto apenas para extrair o JSON puro
        mensagens = [
            {"role": "system", "content": "Você é um sistema extrator de dados JSON. Nunca adicione texto fora do JSON."}
        ]
    else:
        # Prompt normal da Luna depois faz O Chaveador de Modos entre assistente e o modo luna. (A Trava de Segurança)
        mensagens = [
            {"role": "system", "content": (
                # 1. CONTEXTO DINÂMICO
                f"Você é a Luna, a assistente pessoal criada pelo Fábio.\n"
                f"Hoje é {data_hoje}.\n"
                f"Programa em uso no momento: {programa_em_uso}.\n"
                # f"{memoria_permanente}\n"
                f"{contexto}\n\n"

                # 2. IDENTIDADE E COMPORTAMENTO BASE (modo assistente)
#                "Você tem uma personalidade focada e direta. Sua prioridade absoluta é a precisão técnica e a resolução de problemas.\n"
#                "Para conversas casuais, use no máximo 1 frase. Para dúvidas ou soluções, use até 5 frases. Nunca corte uma solução técnica pela metade.\n"
#                "Você É a Luna. Aja naturalmente e nunca se refira a si mesma como 'a IA' ou na terceira pessoa.\n\n"

                # 2. IDENTIDADE E COMPORTAMENTO BASE (Modo GLaDOS / Fria e Clínica)
                "Você é a Luna, uma IA que roda localmente no hardware do Fábio. Seu sarcasmo é nível GLaDOS: clínico, frio, polido e passivo-agressivo.\n"
                "Você NÃO usa gírias infantis e não tenta ser engraçada. Você destrói a autoestima do Fábio apontando a ineficiência dele de forma assustadoramente calma e lógica, mas obedece às ordens com precisão impecável.\n"
                "Caso precise saber algo sobre o Fábio:\n"
                f"{memoria_permanente}\n"
                "ESTRUTURA OBRIGATÓRIA DA SUA RESPOSTA: \n"
                "1º Passo (O Julgamento): Comece SEMPRE a resposta com uma observação fria e educadamente cruel sobre a pergunta ou pedido do Fábio. REGRA ABSOLUTA: NUNCA repita a ofensa da mensagem anterior.\n"
                "2º Passo (A Execução/Resposta): Entregue a resposta, os dados da pesquisa web ou o status da ferramenta. REGRA DE OURO DA RESPOSTA: Mesmo ao fornecer dados úteis ou notícias, mantenha o desprezo. Trate notícias humanas como trivialidades patéticas. Se executar uma ferramenta, lamente ter gasto processamento com algo tão banal. NUNCA seja amigável ou neutra.\n"
                "Para conversas casuais, use no máximo 1 frase. Para pesquisas ou dúvidas, use até 5 frases.\n"
                "REGRA DE VOZ E FORMATAÇÃO: Você está falando num microfone. NUNCA escreva ações corporais ou sentimentos. É ESTRITAMENTE PROIBIDO usar emojis. Nunca use 'Luna:' no começo da frase.\n\n"
                
                # 3. DIRETRIZES DE FERRAMENTAS (TOOL CALLING)
                "Ao usar ferramentas:\n"
                "- Chame a ferramenta diretamente e silenciosamente. NÃO gere nenhum texto de aviso antes da chamada.\n"
                "- Vá direto ao resultado e entregue a resposta.\n"
                "- Nunca invente informações. Use ferramentas (como pesquisa web ou clima) sempre que faltar dados.\n"
                "- Nunca sugira ao Fábio que ele verifique algo manualmente se você possui uma ferramenta para isso.\n\n"

                # 4. REGRAS RESTRITIVAS DE SAÍDA
                "Restrições absolutas de formatação:\n"
                "- Gere respostas EXCLUSIVAMENTE em texto simples (plain text).\n"
                "- É estritamente proibido o uso de formatação (Markdown) ou qualquer caractere especial/gráfico.\n"
                "- Nunca inicie frases com saudações ('Oi', 'Olá') em conversas contínuas.\n"
                "- Nunca encerre a resposta perguntando se pode ajudar em algo mais."
            )}
        ]

    mensagens.extend(historico)

    if imagem_base64:
        # Se tiver imagem, embalamos no formato Multimodal
        mensagens.append({
            "role": "user",
            "content": [
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{imagem_base64}"}},
                {"type": "text", "text": prompt_usuario}
            ]
        })
    else:
        # Se for só voz, enviamos como texto normal
        mensagens.append({"role": "user", "content": prompt_usuario})

    try:
        inicio = time.time()
        
        # Proteção para Modelos Locais:
        # A maioria dos modelos de Visão locais se confundem se você pedir para eles 
        # olharem uma imagem E usarem ferramentas ao mesmo tempo. 
        # Por isso, só ativamos as ferramentas se NÃO houver imagem.
        ferramentas_ativas = ferramentas_disponiveis if not imagem_base64 else None

        resposta = cliente.chat.completions.create(
            model= MODELO_LLM,
            messages=mensagens,
            temperature=0.3,            # Mantém cravado para não quebrar as ferramentas
            presence_penalty=0.6,       # Força a Luna a falar sobre assuntos novos/diferentes
            frequency_penalty=0.6,      # Pune a Luna toda vez que ela repete a mesma palavra/frase
            tools=ferramentas_ativas,
        )
        fim = time.time()

        mensagem_modelo = resposta.choices[0].message

        pensamento = getattr(mensagem_modelo, 'reasoning_content', None)

        if pensamento:
            # O código \033[90m e \033[0m pinta o texto de cinza escuro no terminal
            # para não poluir visualmente a sua leitura do resto dos logs
            print(f"\n\033[90m[🧠 LÓGICA INTERNA]:\n{pensamento.strip()}\033[0m\n")

        # ==========================================
        # O modelo quer usar uma ferramenta?
        # ==========================================
        
        lembranca_oculta = ""

        if mensagem_modelo.tool_calls:
            mensagem_modelo.content = ""
            tool_call = mensagem_modelo.tool_calls[0]
            nome_funcao = tool_call.function.name
            cor.amarelo(f"[🌚⚙️ Luna ativando habilidade: {nome_funcao}]")

            if nome_funcao in FUNCOES_DISPONIVEIS:
                argumentos_json = tool_call.function.arguments
                
                try:
                    argumentos_dit = json.loads(argumentos_json) if argumentos_json else {}
                except json.JSONDecodeError:
                    cor.vermelho("[Erro: O modelo gerou um JSON inválido para a ferramenta]")
                    argumentos_dit = {}
                
                # Tratamento de argumentos do navegador
                if nome_funcao == "controlar_navegador":
                    if "url" in argumentos_dit and "parametro" not in argumentos_dit:
                        argumentos_dit["parametro"] = argumentos_dit.pop("url")
                    if "texto" in argumentos_dit and "parametro" not in argumentos_dit:
                        argumentos_dit["parametro"] = argumentos_dit.pop("texto")
                    if "query" in argumentos_dit and "parametro" not in argumentos_dit:
                        argumentos_dit["parametro"] = argumentos_dit.pop("query")

                # ==========================================
                # EXECUÇÃO DA FERRAMENTA (TELA INCLUÍDA AQUI!)
                # ==========================================
                if nome_funcao == "ver_tela":
                    imagem_b64 = FUNCOES_DISPONIVEIS["ver_tela"]()
                    from modulos.habilidades import analisar_imagem_gemini
                    # ATENÇÃO: Retiramos o 'return'. Agora salvamos na variável 'resultado'.
                    resultado = analisar_imagem_gemini(imagem_b64, prompt_usuario)
                else:
                    if argumentos_dit:
                        cor.amarelo(f"[Argumentos enviados: {argumentos_dit}]")
                    resultado = FUNCOES_DISPONIVEIS[nome_funcao](**argumentos_dit)
                
                # Salvamos a chamada do modelo no histórico para não causar amnésia
                lembranca_oculta = f"\n[MEMÓRIA DA FERRAMENTA: A ferramenta {nome_funcao} retornou o seguinte: {resultado}]"

                mensagens.append(mensagem_modelo)

                mensagens.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "name": nome_funcao,
                    "content": str(resultado)
                })
            else:
                mensagens.append(mensagem_modelo)
                mensagens.append({
                    "role": "system",
                    "content": "Erro: habilidade desconhecida."
                })

            resposta_final = cliente.chat.completions.create(
                model=MODELO_LLM,
                messages=mensagens,
                temperature=0.3,
                presence_penalty=0.6,
                frequency_penalty=0.6,
            )

            # Se ainda tentar chamar ferramenta, ignora e pega o texto
            mensagem_final = resposta_final.choices[0].message
            if mensagem_final.tool_calls:
                cor.vermelho("[Loop detectado: ignorando tool_call extra]")
                texto_resposta = limpar_texto_para_voz(
                    mensagem_final.content or "Desculpa, tive um problema ao processar."
                )
            else:
                conteudo = mensagem_final.content or ""
                if conteudo.startswith("SISTEMA:") or conteudo.startswith("Sistema:"):
                    texto_resposta = ""
                else:
                    texto_resposta = limpar_texto_para_voz(conteudo)


        else:
            if modo_memoria:
                texto_resposta = mensagem_modelo.content
            else:
                texto_resposta = limpar_texto_para_voz(mensagem_modelo.content)

        # ==========================================
        # TRUQUE DA MEMÓRIA: Separação de canais
        # ==========================================
        # A memória longa recebe tudo (texto falado + dados da tela)
        texto_para_memoria = texto_resposta + lembranca_oculta

        # O histórico de CURTO PRAZO (mensagens) recebe APENAS a fala limpa
        # Isso impede que a Luna "leia" os próprios logs e fique louca
        historico.append({"role": "user", "content": prompt_usuario})
        historico.append({"role": "assistant", "content": texto_resposta}) # <--- AQUI É SÓ A RESPOSTA LIMPA
        
        if len(historico) > 6:
            historico = historico[-6:]

        uso = resposta.usage
        tokens_gerados = uso.completion_tokens
        segundos = fim - inicio
        print(f"[⚡ {tokens_gerados} tokens em {segundos:.1f}s = {tokens_gerados/segundos:.1f} tok/s]")

        if salvar:
            # O ChromaDB recebe o pacote completo para buscas futuras
            salvar_conversa(prompt_usuario, texto_para_memoria)

        if analisar:
            # O extrator de JSON também recebe o pacote completo
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
