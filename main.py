# main.py

import time
import threading
import webbrowser
import sounddevice as sd
from modulos.ouvir import escutar_usuario
from modulos.pensar import gerar_resposta
from modulos.falar import falar_texto
from modulos.habilidades import ler_agenda_google, capturar_tela_base64, iniciar_servidor_extensao, pausar_spotify, proxima_musica_spotify
from modulos.proativa import iniciar_modo_proativo, registrar_interacao, registrar_tentativa, MAX_TENTATIVAS, marcar_luna_ocupada
from servidor import (
    atualizar_estado_rosto, atualizar_legenda,
    atualizar_usuario, registrar_callback_interrupcao,
    iniciar_servidor
)

from pynput import keyboard as kb
import modelos.cores as cor

import logging
logging.getLogger("websockets.server").setLevel(logging.ERROR)





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

Gerenciamento de Threads:
- _listener_global: Escuta atalhos globais de teclado (Ctrl+F9 para interromper fala, Ctrl+F7 para Modo Jogo).
- iniciar_modo_proativo: Inicia a thread que roda o proativa.py.
- iniciar_servidor_extensao: Conecta a extensão do Firefox para ler abas.
- Interface Web (servidor.py): Sincroniza o "rosto" e as legendas da Luna.
"""








ATIVAR_MODO_AGENDA = ["veja minha agenda", "consulte na minha agenda"]

ATIVAR_VER_TELA = ["um print"]

ATIVAR_MODO_JOGO = ["modo jogo", "modo reunião", "modo hibernação"]

ATIVAR_SPOTIFY_PAUSA = ["luna pausa", "pausar música", "pausar spotify", "pausa a música", "pausa aí"]

ATIVAR_SPOTIFY_PROXIMA = ["próxima música", "pular música", "pula essa", "toca a próxima"]



TECLA_INTERROMPER = {kb.Key.ctrl_l, kb.Key.f9}

TECLA_MODO_JOGO = {kb.Key.ctrl_l, kb.Key.f7}





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
                cor.vermelho("Modo Suspenso.")
            else:
                _modo_jogo_ativo = False
                from modulos.proativa import registrar_interacao
                registrar_interacao()
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

    while True:
        _interromper.clear()

        try:
            # 1. OUVIR
            atualizar_estado_rosto("ouvindo")
            
            # AGORA DESEMPACOTAMOS AS DUAS VARIÁVEIS <--- NOVO
            texto_usuario = escutar_usuario()
            
            atualizar_usuario(texto_usuario) # <-- Isso faz o texto aparecer no topo do site

            if not texto_usuario.strip():
                atualizar_estado_rosto("dormindo")
                continue

            registrar_interacao()
            marcar_luna_ocupada(True)
            
            cor.azul(f"Você: {texto_usuario}\n")

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

            # 3. PENSAR
            cor.magenta("[🌚💭 Luna pensando...]")
            atualizar_estado_rosto("pensando")
            atualizar_legenda("")

            resposta_luna = gerar_resposta(texto_usuario, historico, imagem_base64=imagem_tela)
            atualizar_legenda(resposta_luna) # <-- Isso faz a resposta dela aparecer embaixo no site


            if "Contexto cheio" in resposta_luna:
                falar_texto(resposta_luna)
                atualizar_estado_rosto("dormindo")
                continue

            if not resposta_luna or not resposta_luna.strip():
                atualizar_estado_rosto("dormindo")
                continue

            # Interrompido durante o processamento?
            if _interromper.is_set():
                atualizar_estado_rosto("dormindo")
                continue

            # 4. FALAR
            falar_texto(
                resposta_luna,
                ao_iniciar  = lambda: (atualizar_estado_rosto("falando"),
                                       atualizar_legenda(resposta_luna)),
                ao_terminar = lambda: atualizar_estado_rosto("dormindo"),
            )

        except KeyboardInterrupt:
            break
        except Exception as e:
            cor.vermelho(f"Erro: {e}")
            atualizar_estado_rosto("dormindo")
            time.sleep(2)

def main():
    threading.Thread(target=_listener_global, daemon=True).start()  # adiciona isso
    #iniciar_modo_proativo()
    iniciar_servidor_extensao()
    registrar_callback_interrupcao(ao_interromper)
    #iniciar_servidor()
    #threading.Timer(1.5, lambda: webbrowser.open("http://localhost:5000")).start()
    loop_voz()

if __name__ == "__main__":
    main()