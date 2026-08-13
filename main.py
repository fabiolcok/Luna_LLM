# main.py

import ctypes, sys

_mutex = ctypes.windll.kernel32.CreateMutexW(None, True, "Luna_LLM_SingleInstance")
if ctypes.windll.kernel32.GetLastError() == 183:   # ERROR_ALREADY_EXISTS
    ctypes.windll.user32.MessageBoxW(0, "Luna já está rodando.", "Luna", 0x30)
    sys.exit(0)

import modelos.log as _log_setup
_log_setup.configurar()

# Timestamp em TODA linha do console (.bat) — pra saber QUANDO cada coisa foi registrada.
# (o luna.log já tem hora via logging; isto é só pro terminal.) Envolve o print global,
# então pega tanto os cor.xxx() quanto os print() crus.
import builtins as _bi, datetime as _dt_ts
_print_orig = _bi.print
def _print_com_hora(*a, **k):
    _print_orig(_dt_ts.datetime.now().strftime("[%H:%M:%S]"), *a, **k)
_bi.print = _print_com_hora

import os
import logging
import subprocess
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
    injetar_arquivo_pendente, obter_e_limpar_imagem_anexada, carregar_e_aplicar_config,
    registrar_handler_texto_web, atualizar_mascote_solto
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

# Histórico da conversa — MÓDULO-level pra ser compartilhado entre a voz e a caixa de
# texto do web (é UMA conversa só). gerar_resposta cuida de append/trim in-place.
_historico_conversa = []


def _registrar_turno_direto(historico: list, usuario: str, luna: str):
    """Interceptadores também pertencem à conversa, mesmo sem passar pela LLM."""
    historico.extend([
        {"role": "user", "content": usuario},
        {"role": "assistant", "content": luna},
    ])
    if len(historico) > 12:
        del historico[:-12]


def _falar_atalho(texto: str):
    """TTS dos comandos locais também precisa fechar o ciclo visual do mascote."""
    falar_texto(
        texto,
        ao_iniciar=lambda: atualizar_estado_rosto("falando"),
        ao_terminar=lambda: atualizar_estado_rosto("dormindo"),
    )


def _mostrar_resposta_web_no_terminal(texto: str):
    """Texto web não usa TTS, mas a resposta precisa continuar observável no CMD."""
    if not texto or not texto.strip():
        return
    print("===================================")
    cor.ciano(f"[🌚💬 Luna respondeu] '{texto.strip()}'")
    print("===================================")


def responder_texto_web(texto: str):
    """Mensagem DIGITADA na caixa do web: mesmas regras do Telegram (desenvolve, SEM TTS),
    mas presença = no PC. Compartilha o histórico com a voz."""
    texto = (texto or "").strip()
    if not texto:
        return
    from modulos.proativa import luna_esta_livre
    _fim = time.time() + 120
    while not luna_esta_livre() and time.time() < _fim:   # espera a Luna ficar livre (voz/proativo)
        time.sleep(0.3)
    registrar_interacao()          # usuário ativo -> reseta suspensão do proativo
    marcar_luna_ocupada(True)
    try:
        cor.azul(f"[⌨️ Web] Você: {texto}")
        _log.info(f"[Web texto] Usuário: {texto}")
        atualizar_usuario(texto)                       # mostra "Você: ..." no web
        atualizar_estado_rosto("pensando")             # anima a presença (a lua) também no texto
        from modulos import acompanhamentos
        resposta_direta = acompanhamentos.interceptar_resposta(texto)
        if resposta_direta:
            _registrar_turno_direto(_historico_conversa, texto, resposta_direta)
            atualizar_legenda(resposta_direta)
            _mostrar_resposta_web_no_terminal(resposta_direta)
            _log.info(f"[Web texto] Luna [acompanhamento]: {resposta_direta}")
            return
        texto_modelo = injetar_arquivo_pendente(texto)
        resposta = gerar_resposta(texto_modelo, _historico_conversa,
                                  responder_completo=True, presenca_pc=True)
        resposta = (resposta or "").strip()
        atualizar_legenda(resposta)                    # mostra a resposta + registra o turno (SEM falar)
        if resposta:
            _mostrar_resposta_web_no_terminal(resposta)
            _log.info(f"[Web texto] Luna: {resposta[:200]}")
    except Exception as e:
        _log.exception(f"Erro no texto web: {e}")
        atualizar_legenda("Deu um erro aqui, tenta de novo.")
    finally:
        atualizar_estado_rosto("dormindo")
        marcar_luna_ocupada(False)


def loop_voz():
    historico = _historico_conversa
    try:
        # Falas proativas entram neste histórico — follow-ups ("quais são?") ganham contexto
        from modulos import proativa
        proativa.registrar_historico_principal(historico)
    except Exception:
        pass

    # O HTML já nasce em repouso; declarar o mesmo estado no backend mantém o debug e
    # clientes que conectarem neste momento coerentes antes do primeiro acionamento do PTT.
    atualizar_estado_rosto("dormindo")

    while True:
        _interromper.clear()

        try:
            # 1. OUVIR
            # O estado "ouvindo" nasce no on_press real do PTT. Marcá-lo aqui fazia a
            # mascote passar todo o tempo de espera atenta, sem nunca repousar entre falas.
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

                # Confirmação de acompanhamento é igual por botão, texto e STT. Resolve antes
                # do roteador para um simples "sim" não virar conversa ou evento de agenda.
                from modulos import acompanhamentos
                resposta_acomp = acompanhamentos.interceptar_resposta(texto_usuario)
                if resposta_acomp:
                    _registrar_turno_direto(historico, texto_usuario, resposta_acomp)
                    atualizar_legenda(resposta_acomp)
                    _log.info(f"[PC] Luna [acompanhamento]: {resposta_acomp}")
                    falar_texto(
                        resposta_acomp,
                        ao_iniciar=lambda: atualizar_estado_rosto("falando"),
                        ao_terminar=lambda: atualizar_estado_rosto("dormindo"),
                    )
                    continue

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
                    _falar_atalho("Modo jogo ativado. Pode jogar em paz, bot.")
                    continue

                elif any(p in texto_lower for p in ATIVAR_SPOTIFY_PAUSA):
                    cor.amarelo("⏸️ Pausando Spotify (Ativado por palavra)...")
                    pausar_spotify()
                    _falar_atalho("Pausado.")
                    continue

                elif any(p in texto_lower for p in ATIVAR_SPOTIFY_PROXIMA):
                    cor.amarelo("⏭️ Pulando música (Ativado por palavra)...")
                    proxima_musica_spotify()
                    _falar_atalho("Pulando.")
                    continue

                elif any(p in texto_lower for p in ATIVAR_TRADUCAO):
                    cor.amarelo("🌐 Traduzindo texto selecionado...")
                    texto_selecionado = ler_texto_selecionado()
                    if "Erro:" in texto_selecionado or not texto_selecionado.strip():
                        _falar_atalho("Nenhum texto selecionado para traduzir.")
                        continue
                    texto_usuario = f"Traduza para português do Brasil o seguinte texto:\n\n{texto_selecionado}"

                elif any(p in texto_lower for p in ATIVAR_MUTE_DESMUTAR) or \
                     any(p in texto_lower for p in ATIVAR_MUTE_PALAVRAS):
                    cor.amarelo("🔇 Alternando mute (Ativado por palavra)...")
                    vai_desmutar = any(p in texto_lower for p in ATIVAR_MUTE_DESMUTAR)
                    if not vai_desmutar:
                        _falar_atalho("Mutando.")
                    resultado = alternar_mute()
                    cor.amarelo(f"[🔇 {resultado}]")
                    if vai_desmutar:
                        _falar_atalho("Som ativado.")
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

                texto_usuario = injetar_arquivo_pendente(texto_usuario)

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

def _iniciar_bandeja(janela, api_interface):
    def abrir(_icon, _item):
        janela.show()

    def ver_logs(_icon, _item):
        log_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs", "luna.log")
        if os.path.exists(log_path):
            os.startfile(log_path)

    def fechar(_icon, _item):
        _icon.stop()
        api_interface.encerrar_widget()
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


class _ApiInterface:
    """Controla o processo visual do widget sem iniciar uma segunda instância da Luna."""

    def __init__(self):
        self._janela_principal = None
        self._processo_widget = None
        self._lock = threading.RLock()

    def _avisar_principal(self, solto):
        atualizar_mascote_solto(solto)
        janela = self._janela_principal
        if janela:
            try:
                janela.run_js(f"window.definirMascoteSolto({str(bool(solto)).lower()})")
            except Exception:
                pass

    def _vigiar_widget(self, processo):
        processo.wait()
        with self._lock:
            if self._processo_widget is processo:
                self._processo_widget = None
        self._avisar_principal(False)

    def soltar_mascote(self):
        with self._lock:
            if self._processo_widget and self._processo_widget.poll() is None:
                return True
            caminho = os.path.join(os.path.dirname(os.path.abspath(__file__)), "widget.py")
            flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
            processo = subprocess.Popen(
                [sys.executable, caminho], cwd=os.path.dirname(caminho), creationflags=flags
            )
            self._processo_widget = processo
            threading.Thread(
                target=self._vigiar_widget, args=(processo,), daemon=True
            ).start()

        self._avisar_principal(True)
        return True

    def recolher_mascote(self):
        self.encerrar_widget()
        self._avisar_principal(False)
        return True

    def encerrar_widget(self):
        with self._lock:
            processo = self._processo_widget
            self._processo_widget = None
        if processo and processo.poll() is None:
            processo.terminate()

def main():
    _log.info("Luna iniciando...")
    threading.Thread(target=_listener_global, daemon=True).start()
    iniciar_modo_proativo()
    iniciar_servidor_extensao()
    registrar_callback_interrupcao(ao_interromper)
    registrar_handler_texto_web(responder_texto_web)
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
    from modulos.diagnostico import mostrar_diagnostico
    mostrar_diagnostico()
    iniciar_servidor()
    iniciar_bot_telegram()
    threading.Thread(target=loop_voz, daemon=True).start()

    api_interface = _ApiInterface()
    janela = webview.create_window(
        "Luna", "http://localhost:5000", width=460, height=760, js_api=api_interface
    )
    api_interface._janela_principal = janela

    # Fechar o X esconde para a bandeja em vez de encerrar
    def ao_fechar_janela():
        janela.hide()
        return False  # cancela o fechamento real

    janela.events.closing += ao_fechar_janela

    # Bandeja inicia junto com o webview
    webview.start(func=_iniciar_bandeja, args=(janela, api_interface))

if __name__ == "__main__":
    main()
