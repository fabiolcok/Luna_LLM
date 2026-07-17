# main.py

import ctypes, sys

_mutex = ctypes.windll.kernel32.CreateMutexW(None, True, "Luna_LLM_SingleInstance")
if ctypes.windll.kernel32.GetLastError() == 183:   # ERROR_ALREADY_EXISTS
    ctypes.windll.user32.MessageBoxW(0, "Luna já está rodando.", "Luna", 0x30)
    sys.exit(0)

import modelos.log as _log_setup
_log_setup.configurar()

import os
import logging
import time
import threading
import webview
import sounddevice as sd
import pystray
from PIL import Image, ImageDraw

_log = logging.getLogger("luna.main")
from modulos.ouvir import escutar_usuario
from modulos.pensar import gerar_resposta
from modulos.falar import falar_texto
from modulos.habilidades import ler_agenda_google, capturar_tela_base64, iniciar_servidor_extensao, pausar_spotify, proxima_musica_spotify, alternar_mute, ler_texto_selecionado
from modulos.proativa import iniciar_modo_proativo, registrar_interacao, registrar_tentativa, MAX_TENTATIVAS, marcar_luna_ocupada, configurar_proativo, configurar_tarefa
from modulos.telegram_bot import iniciar_bot_telegram
from modulos.falar import configurar_voz
from modulos.pensar import configurar_memoria
from servidor import (
    atualizar_estado_rosto, atualizar_legenda,
    atualizar_usuario, registrar_callback_interrupcao,
    iniciar_servidor, registrar_config_handler, sincronizar_config,
    obter_e_limpar_arquivo, obter_e_limpar_imagem_anexada, carregar_e_aplicar_config
)

from pynput import keyboard as kb
import modelos.cores as cor






"""
MÓDULO PRINCIPAL (ENTRY POINT & ORQUESTRADOR) DA LUNA
---------------------------------------------------------
Este é o arquivo raiz do projeto. Ele inicializa todas as threads 
em background e mantém o loop principal de interação por voz.

Arquitetura e Fluxo (loop_voz):
1. OUVIR: Usa o microfone para captar o áudio do usuário (ouvir.py).
2. INTERCEPTADOR: Verifica gatilhos rápidos (palavras-chave) para rodar 
   ações locais sem precisar acionar a LLM para interpretar intenção pura.
3. PENSAR: Envia o texto (e imagens) para o modelo local (pensar.py).
4. FALAR: Sintetiza e reproduz a resposta em áudio (falar.py).

Gatilhos Rápidos (Palavras de Ativação):
- Agenda ("veja minha agenda"): Injeta eventos direto no prompt.
- Visão ("um print"): Aciona a câmera/print e manda imagem em Base64.
- Modo Jogo ("modo jogo"): Silencia a assistente manualmente.
- Controle Spotify: Pausa ou avança a música instantaneamente.
- Mute ("muta o som" / "desmuta"): Alterna mute do sistema via pycaw, sem passar pelo LLM.
- Tradução ("traduz isso"): Faz Ctrl+C no texto selecionado e pede à LLM para traduzir para PT-BR.

Gerenciamento de Threads:
- _listener_global: Escuta atalhos globais de teclado (Ctrl+F9 para interromper fala, Ctrl+F7 para Modo Jogo).
- iniciar_modo_proativo: Inicia a thread que roda o proativa.py.
- iniciar_servidor_extensao: Conecta a extensão do Firefox para ler abas.
- Interface Web (servidor.py): Sincroniza o "rosto" e as legendas da Luna.
"""








ATIVAR_MODO_AGENDA = ["veja minha agenda", "consulte na minha agenda"]

ATIVAR_VER_TELA = [
    "um print", "tira um print", "tira o print",
    "olha minha tela", "olha a minha tela", "dá uma olhada na minha tela",
    "veja minha tela", "veja a minha tela",
    "o que você vê", "o que você está vendo", "o que está na tela",
    "me ajuda com isso aqui", "me ajuda com essa tela", "me ajuda com esse erro aqui",
]

ATIVAR_MODO_JOGO = ["modo jogo", "modo reunião", "modo hibernação"]

ATIVAR_SPOTIFY_PAUSA = ["luna pausa", "pausar música", "pausar spotify", "pausa a música", "pausa aí"]

ATIVAR_SPOTIFY_PROXIMA = ["próxima música", "pular música", "pula essa", "toca a próxima"]

ATIVAR_MUTE_PALAVRAS    = ["muta", "silencia", "desliga o som", "tira o som"]
ATIVAR_MUTE_DESMUTAR    = ["desmuta", "volta o som", "ativa o som", "liga o som"]

ATIVAR_TRADUCAO = [
    "traduz isso", "traduza isso", "traduz esse texto", "traduza esse texto",
    "traduz o que selecionei", "traduz o selecionado", "me traduz isso",
    "traduz isso aqui", "traduz para português",
]



TECLA_INTERROMPER = {kb.Key.ctrl_l, kb.Key.f9}

TECLA_MODO_JOGO = {kb.Key.ctrl_l, kb.Key.f7}

def configurar_tecla(nome, combo_txt):
    """Handler da config web (⌨ Teclas): troca os atalhos em runtime.
    O listener global lê as globais a cada tecla, então rebindar já vale."""
    global TECLA_INTERROMPER, TECLA_MODO_JOGO
    from modulos.ouvir import parsear_combo, configurar_tecla_ptt
    if nome == "ptt":
        return configurar_tecla_ptt(combo_txt)
    teclas = parsear_combo(combo_txt)
    if not teclas:
        return False
    if nome == "interromper":
        TECLA_INTERROMPER = teclas
    elif nome == "suspenso":
        TECLA_MODO_JOGO = teclas
    else:
        return False
    return True





_modo_jogo_ativo = False

def _listener_global():
    _pressionadas = set()
    def on_press(key):
        global _modo_jogo_ativo
        _pressionadas.add(key)
        if TECLA_INTERROMPER.issubset(_pressionadas):
            ao_interromper()
        if TECLA_MODO_JOGO.issubset(_pressionadas):
            if not _modo_jogo_ativo:
                _modo_jogo_ativo = True
                for _ in range(MAX_TENTATIVAS):
                    registrar_tentativa()
                sincronizar_config("proativo", False)
                cor.vermelho("Modo Suspenso.")
            else:
                _modo_jogo_ativo = False
                from modulos.proativa import registrar_interacao
                registrar_interacao()
                sincronizar_config("proativo", True)
                cor.verde("Modo Ativo.")
    def on_release(key):
        _pressionadas.discard(key)
    with kb.Listener(on_press=on_press, on_release=on_release) as listener:
        listener.join()


# Flag de interrupção — compartilhada entre threads
_interromper = threading.Event()

def ao_interromper():
    """Chamado pelo browser quando o usuário clica em interromper."""
    cor.vermelho("[🛑 Interrupção de Fala solicitada]")
    _interromper.set()
    sd.stop()  # para o áudio imediatamente

def loop_voz():
    historico = []
    try:
        # Falas proativas entram neste histórico — follow-ups ("quais são?") ganham contexto
        from modulos import proativa
        proativa.registrar_historico_principal(historico)
    except Exception:
        pass

    while True:
        _interromper.clear()

        try:
            # 1. OUVIR
            atualizar_estado_rosto("ouvindo")
            texto_usuario = escutar_usuario()
            atualizar_usuario(texto_usuario)

            if not texto_usuario.strip():
                atualizar_estado_rosto("dormindo")
                continue

            registrar_interacao()
            marcar_luna_ocupada(True)

            try:
                cor.azul(f"Você: {texto_usuario}\n")
                _log.info(f"[PC] Usuário: {texto_usuario}")

                # 2. INTERCEPTADOR DE HABILIDADES POR PALAVRAS DE ATIVAÇÃO
                texto_lower = texto_usuario.lower()
                imagem_tela = None

                if any(p in texto_lower for p in ATIVAR_MODO_AGENDA):
                    cor.amarelo("📅 Consultando Google Agenda...")
                    dados_agenda = ler_agenda_google()
                    pergunta_original = texto_usuario
                    texto_usuario = f"""O usuário perguntou: "{pergunta_original}"
                                        Dados da agenda:
                                        {dados_agenda}
                                        Responda diretamente, apenas o período pedido, de forma natural."""

                elif any(p in texto_lower for p in ATIVAR_VER_TELA):
                    cor.amarelo("📷 Luna está vendo a sua tela...")
                    imagem_tela = capturar_tela_base64()

                elif any(p in texto_lower for p in ATIVAR_MODO_JOGO):
                    for _ in range(MAX_TENTATIVAS):
                        registrar_tentativa()
                    falar_texto("Modo jogo ativado. Pode jogar em paz, bot.")
                    continue

                elif any(p in texto_lower for p in ATIVAR_SPOTIFY_PAUSA):
                    cor.amarelo("⏸️ Pausando Spotify (Ativado por palavra)...")
                    pausar_spotify()
                    falar_texto("Pausado.")
                    continue

                elif any(p in texto_lower for p in ATIVAR_SPOTIFY_PROXIMA):
                    cor.amarelo("⏭️ Pulando música (Ativado por palavra)...")
                    proxima_musica_spotify()
                    falar_texto("Pulando.")
                    continue

                elif any(p in texto_lower for p in ATIVAR_TRADUCAO):
                    cor.amarelo("🌐 Traduzindo texto selecionado...")
                    texto_selecionado = ler_texto_selecionado()
                    if "Erro:" in texto_selecionado or not texto_selecionado.strip():
                        falar_texto("Nenhum texto selecionado para traduzir.")
                        continue
                    texto_usuario = f"Traduza para português do Brasil o seguinte texto:\n\n{texto_selecionado}"

                elif any(p in texto_lower for p in ATIVAR_MUTE_DESMUTAR) or \
                     any(p in texto_lower for p in ATIVAR_MUTE_PALAVRAS):
                    cor.amarelo("🔇 Alternando mute (Ativado por palavra)...")
                    vai_desmutar = any(p in texto_lower for p in ATIVAR_MUTE_DESMUTAR)
                    if not vai_desmutar:
                        falar_texto("Mutando.")
                    resultado = alternar_mute()
                    cor.amarelo(f"[🔇 {resultado}]")
                    if vai_desmutar:
                        falar_texto("Som ativado.")
                    continue

                # 3. PENSAR
                # Imagem anexada no web → arquiva direto no Obsidian (Caminho A, sem visão).
                # A fala vira a legenda; tiramos o comando ("salva isso com o assunto") do começo.
                imagem_anexada = obter_e_limpar_imagem_anexada()
                if imagem_anexada:
                    import re as _re, random as _rnd
                    from modulos import obsidian
                    legenda = texto_usuario.strip()
                    legenda = _re.sub(r'^\s*(salva|guarda|anota|registra|arquiva)\w*', '', legenda, flags=_re.I)
                    legenda = _re.sub(r'^\s*(isso|a[íi]|essa imagem|essa foto|esse print|a imagem|o print)', '', legenda, flags=_re.I)
                    legenda = _re.sub(r'^\s*(com\s+o?\s*assunto|sobre|como|de)\b', '', legenda, flags=_re.I)
                    legenda = _re.sub(r'^[\s:,\.-]+', '', legenda).strip()
                    cor.ciano(f"[📎🖼️ Imagem anexada: {imagem_anexada['nome']} → legenda: '{legenda or '(sem)'}']")
                    res = obsidian.salvar_foto(imagem_anexada["dados"], legenda,
                                               origem="web", ext=imagem_anexada.get("ext", "jpg"))
                    if res.startswith("SISTEMA: Foto salva"):
                        m = _re.search(r"Inbox\): '(.+)'", res)
                        t = (m.group(1) if m else (legenda or "a imagem")).strip()
                        # Confirmação com a voz da persona; frases prontas só como fallback.
                        from modulos.pensar import frase_confirmacao
                        resposta_luna = frase_confirmacao(
                            f"Você acabou de arquivar no Inbox do Obsidian do usuário uma imagem que ele "
                            f"te mandou, com o título '{t}'. Confirme pra ele em 1 frase curta, do seu "
                            f"jeito, citando o título."
                        ) or _rnd.choice([
                            f'Salvei a imagem no seu Inbox: "{t}".',
                            f'Prontinho, guardei "{t}" nas suas notas.',
                            f'Imagem arquivada no seu Obsidian: "{t}".',
                        ])
                    else:
                        resposta_luna = "Não consegui salvar a imagem agora, tenta de novo?"
                    atualizar_legenda(resposta_luna)
                    _log.info(f"[PC] Luna [imagem web]: {resposta_luna}")
                    falar_texto(
                        resposta_luna,
                        ao_iniciar  = lambda: atualizar_estado_rosto("falando"),
                        ao_terminar = lambda: atualizar_estado_rosto("dormindo"),
                    )
                    continue

                arquivo = obter_e_limpar_arquivo()
                if arquivo:
                    cor.ciano(f"[📎 Arquivo injetado: {arquivo['nome']} ({len(arquivo['conteudo'])} chars)]")
                    texto_usuario = f"[Arquivo: {arquivo['nome']}]\n{arquivo['conteudo']}\n\n{texto_usuario}"

                cor.magenta("[🌚💭 Luna pensando...]")
                atualizar_estado_rosto("pensando")
                atualizar_legenda("")

                resposta_luna = gerar_resposta(texto_usuario, historico, imagem_base64=imagem_tela)
                atualizar_legenda(resposta_luna)
                if resposta_luna and resposta_luna.strip():
                    _log.info(f"[PC] Luna: {resposta_luna[:200]}")

                if "Contexto cheio" in resposta_luna:
                    falar_texto(resposta_luna)
                    atualizar_estado_rosto("dormindo")
                    continue

                if not resposta_luna or not resposta_luna.strip():
                    atualizar_estado_rosto("dormindo")
                    continue

                if _interromper.is_set():
                    atualizar_estado_rosto("dormindo")
                    continue

                # 4. FALAR
                falar_texto(
                    resposta_luna,
                    ao_iniciar  = lambda: atualizar_estado_rosto("falando"),
                    ao_terminar = lambda: atualizar_estado_rosto("dormindo"),
                )

            finally:
                marcar_luna_ocupada(False)

        except KeyboardInterrupt:
            break
        except Exception as e:
            _log.exception(f"Erro no loop principal: {e}")
            cor.vermelho(f"Erro: {e}")
            atualizar_estado_rosto("dormindo")
            time.sleep(2)

def _criar_icone_bandeja():
    img  = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.ellipse([4, 4, 60, 60],  fill=(180, 249, 248, 255))  # círculo azul claro
    draw.ellipse([18, 4, 74, 60], fill=(13,  13,  18,  255))  # corte → crescente
    return img

def _iniciar_bandeja(janela):
    def abrir(_icon, _item):
        janela.show()

    def ver_logs(_icon, _item):
        log_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs", "luna.log")
        if os.path.exists(log_path):
            os.startfile(log_path)

    def fechar(_icon, _item):
        _icon.stop()
        janela.destroy()
        os._exit(0)

    icone = pystray.Icon(
        "Luna",
        _criar_icone_bandeja(),
        "Luna",
        menu=pystray.Menu(
            pystray.MenuItem("Abrir interface", abrir, default=True),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Ver logs", ver_logs),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Fechar Luna", fechar),
        ),
    )
    icone.run_detached()
    return icone

def main():
    _log.info("Luna iniciando...")
    threading.Thread(target=_listener_global, daemon=True).start()
    iniciar_modo_proativo()
    iniciar_servidor_extensao()
    registrar_callback_interrupcao(ao_interromper)
    registrar_config_handler("proativo", configurar_proativo)
    registrar_config_handler("memoria", configurar_memoria)
    registrar_config_handler("voz", lambda v: configurar_voz(voz=v))
    registrar_config_handler("velocidade", lambda v: configurar_voz(velocidade=float(v)))
    registrar_config_handler("tarefa", configurar_tarefa)
    registrar_config_handler("tecla", configurar_tecla)
    carregar_e_aplicar_config()   # aplica voz/velocidade/proativo/tarefas/teclas salvos
    try:
        from modulos import obsidian
        _criadas = obsidian.semear_vault()   # vault novo: cria perfil/animes/radar com template
        if _criadas:
            cor.verde(f"[📓 Obsidian: notas de config criadas com template: {', '.join(_criadas)}]")
    except Exception:
        pass
    iniciar_servidor()
    iniciar_bot_telegram()
    threading.Thread(target=loop_voz, daemon=True).start()

    janela = webview.create_window("Luna", "http://localhost:5000", width=460, height=760)

    # Fechar o X esconde para a bandeja em vez de encerrar
    def ao_fechar_janela():
        janela.hide()
        return False  # cancela o fechamento real

    janela.events.closing += ao_fechar_janela

    # Bandeja inicia junto com o webview
    webview.start(func=_iniciar_bandeja, args=(janela,))

if __name__ == "__main__":
    main()