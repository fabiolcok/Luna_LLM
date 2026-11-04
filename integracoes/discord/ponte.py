"""Saída opcional de voz; não recebe áudio nem mensagens do Discord."""
import asyncio
from concurrent.futures import Future
import importlib.util
import logging
import queue
import threading
import time
import uuid
from modulos import config_env

_lock = threading.RLock()
_log = logging.getLogger('luna.discord')
_thread = None
_parar = threading.Event()
_fila = queue.Queue(maxsize=4)
_estado = {'estado': 'desligado', 'mensagem': '', 'jogos': False, 'canal': ''}
_envios = {}


def estado():
    with _lock:
        return {**_estado, 'envios': dict(_envios), 'configurado': bool(config_env.texto('DISCORD_BOT_TOKEN') and
                config_env.inteiro('DISCORD_VOICE_CHANNEL_ID') > 0),
                'instalado': importlib.util.find_spec('discord') is not None}


def _atualizar(**dados):
    with _lock: _estado.update(dados)


def jogos(valor):
    if type(valor) is not bool: raise ValueError('Opção inválida.')
    _atualizar(jogos=valor)


def conectar():
    global _thread
    with _lock:
        if _thread and _thread.is_alive(): return
        token = config_env.texto('DISCORD_BOT_TOKEN')
        canal = config_env.inteiro('DISCORD_VOICE_CHANNEL_ID')
        if not token or canal <= 0:
            raise ValueError('Configure DISCORD_BOT_TOKEN e DISCORD_VOICE_CHANNEL_ID no .env e reinicie a Luna.')
        if importlib.util.find_spec('discord') is None:
            raise ValueError('Instale integracoes/discord/requirements.txt no ambiente da Luna.')
        _parar.clear()
        _estado.update(estado='conectando', mensagem='Conectando…')
        _thread = threading.Thread(target=_executar, args=(token, canal), daemon=True, name='luna-discord')
        _thread.start()


def desconectar():
    _parar.set()
    _atualizar(estado='desligando' if _thread and _thread.is_alive() else 'desligado',
               jogos=False, mensagem='')


def enviar(texto=None, audio=None, cancelado=None):
    with _lock:
        if _estado['estado'] != 'conectado' or _parar.is_set():
            raise ValueError('Conecte a Luna ao Discord primeiro.')
        futuro = Future()
        futuro.envio_id = uuid.uuid4().hex
        try: _fila.put_nowait((texto, audio, cancelado, futuro, time.monotonic()))
        except queue.Full: raise ValueError('Fila de voz cheia. Aguarde a fala terminar.') from None
        _envios[futuro.envio_id] = 'Na fila…'
        def terminou(f):
            with _lock:
                _envios[f.envio_id] = 'Falha ou envio interrompido.' if f.exception() else 'Reprodução finalizada.'
                for chave in list(_envios):
                    if len(_envios) <= 30: break
                    if _envios[chave] in ('Falha ou envio interrompido.', 'Reprodução finalizada.'):
                        del _envios[chave]
        futuro.add_done_callback(terminou)
        _log.info('Fala enfileirada: %s', 'audio de jogo' if audio is not None else 'resposta manual')
        return futuro


def compartilhar_jogo(audio, execucao, controle):
    if not execucao or not execucao.comentario_jogo: return False
    if not _estado['jogos'] or _estado['estado'] != 'conectado':
        _log.info('Comentario local: compartilhamento=%s, conexao=%s', _estado['jogos'], _estado['estado'])
        return False
    try: futuro = enviar(audio=audio.copy(), cancelado=lambda: not _estado['jogos'] or not controle.valida(execucao))
    except ValueError: return False
    while not futuro.done(): time.sleep(.05)
    try: futuro.result()
    except Exception: pass  # Evita repetir no fone uma fala parcialmente transmitida.
    return True


def _executar(token, canal):
    try: asyncio.run(_rodar(token, canal))
    except Exception:
        # Nunca repassar exceções de rede ou tokens ao painel/log.
        _atualizar(estado='erro', mensagem='Falha na conexão. Confira token, dependências de voz/DAVE e permissões do canal.')
    finally:
        while True:
            try:
                item = _fila.get_nowait()
                if not item[3].done(): item[3].set_exception(RuntimeError('Conexão encerrada.'))
            except queue.Empty: break
        if _parar.is_set(): _atualizar(estado='desligado', mensagem='', canal='')
        elif _estado['estado'] != 'erro':
            _atualizar(estado='erro', mensagem='Conexão encerrada. Conecte novamente.', canal='')


async def _rodar(token, canal_id):
    import discord
    import davey
    if discord.version_info < (2, 7, 1): raise RuntimeError('Atualize discord.py.')
    intents = discord.Intents.none()
    intents.guilds = True
    intents.voice_states = True
    client = discord.Client(intents=intents)
    tarefa = None
    try:
        await asyncio.wait_for(client.login(token), 20)
        tarefa = asyncio.create_task(client.connect(reconnect=True))
        ready = asyncio.create_task(client.wait_until_ready())
        try:
            for _ in range(300):
                if _parar.is_set(): return
                if tarefa.done(): await tarefa
                if ready.done(): break
                await asyncio.sleep(.1)
            else: raise TimeoutError('Conexão indisponível.')
            await ready
        finally:
            if not ready.done(): ready.cancel()
        canal = client.get_channel(canal_id) or await client.fetch_channel(canal_id)
        if not isinstance(canal, discord.VoiceChannel): raise ValueError('Use canal de voz de servidor.')
        voz = await canal.connect(self_deaf=True, timeout=20, reconnect=True)
        if _parar.is_set(): return
        _atualizar(estado='conectado', mensagem='', canal=canal.name)
        while not _parar.is_set():
            if tarefa.done(): await tarefa
            if not voz.is_connected(): raise ConnectionError('Conexão perdida.')
            try: texto, audio, cancelado, futuro, criado = _fila.get_nowait()
            except queue.Empty:
                await asyncio.sleep(.1)
                continue
            try:
                etapa = 'validacao'
                with _lock: _envios[futuro.envio_id] = 'Preparando voz…'
                if time.monotonic() - criado > 60 or (cancelado and cancelado()):
                    raise RuntimeError('Fala expirada ou interrompida.')
                membro = canal.guild.me
                if not canal.permissions_for(membro).speak:
                    _atualizar(mensagem='O bot está sem permissão Falar neste canal.')
                    raise PermissionError()
                if membro.voice and membro.voice.mute:
                    _atualizar(mensagem='O bot foi silenciado pelo servidor. Remova o silenciamento no Discord.')
                    raise PermissionError()
                if audio is None:
                    etapa = 'sintese'
                    _atualizar(mensagem='Gerando voz para o Discord…')
                    from modulos.falar import sintetizar_para_discord
                    audio = await asyncio.to_thread(sintetizar_para_discord, texto)
                if _parar.is_set() or (cancelado and cancelado()): raise RuntimeError('Interrompida.')
                etapa = 'conversao PCM'
                from integracoes.discord.pcm import converter
                dados = converter(audio)
                import numpy as np
                amostras = np.frombuffer(dados, dtype='<i2').astype(float)
                pico = float(np.max(np.abs(amostras))) / 32768
                rms = float(np.sqrt(np.mean(amostras ** 2))) / 32768
                conexao = getattr(voz, '_connection', None)
                diagnostico = {'pico': round(pico, 5), 'rms': round(rms, 5),
                               'dave_versao': getattr(conexao, 'dave_protocol_version', None),
                               'dave_pronto': getattr(conexao, 'can_encrypt', None)}
                _atualizar(diagnostico=diagnostico)
                _log.info('Audio Discord: %s', diagnostico)
                if pico == 0:
                    raise ValueError('Audio silencioso')
                etapa = 'negociacao de criptografia DAVE'
                if diagnostico['dave_versao'] and not diagnostico['dave_pronto']:
                    _atualizar(mensagem='Aguardando criptografia de voz do Discord…')
                    for _ in range(100):
                        if _parar.is_set() or (cancelado and cancelado()):
                            raise RuntimeError('Interrompida.')
                        if conexao.can_encrypt:
                            break
                        await asyncio.sleep(.1)
                    else:
                        raise TimeoutError('Criptografia de voz indisponivel')
                    _atualizar(diagnostico={**diagnostico, 'dave_pronto': True})

                class PCM(discord.AudioSource):
                    def __init__(self): self.pos = 0
                    def read(self):
                        bloco = dados[self.pos:self.pos+3840]; self.pos += 3840
                        return bloco.ljust(3840, b'\0') if bloco else b''
                    def is_opus(self): return False

                acabou = threading.Event()
                erros = []
                def fim(erro):
                    if erro: erros.append(type(erro).__name__)
                    acabou.set()
                etapa = 'reproducao'
                with _lock: _envios[futuro.envio_id] = 'Falando no Discord…'
                _atualizar(mensagem='Transmitindo voz no Discord…')
                voz.play(PCM(), after=fim)
                limite = time.monotonic() + len(dados) / 192000 + 10
                while not acabou.is_set():
                    if _parar.is_set() or (cancelado and cancelado()) or not voz.is_connected() or time.monotonic() > limite:
                        voz.stop()
                        raise RuntimeError('Fala interrompida ou conexão perdida.')
                    await asyncio.sleep(.05)
                if erros:
                    _log.warning('Player Discord falhou: %s', erros[0])
                    raise RuntimeError('Falha na transmissão.')
                _atualizar(mensagem='Reprodução finalizada no bot; recepção no canal não confirmada.')
                _log.info('Transmissao concluida: %.1f s', len(dados) / 192000)
                futuro.set_result(True)
            except Exception as erro:
                # Só classe e etapa: exceções externas podem conter credenciais.
                _log.warning('Falha na voz Discord: etapa=%s, tipo=%s', etapa, type(erro).__name__)
                if not isinstance(erro, PermissionError):
                    _atualizar(mensagem=f'Falha na voz: {etapa} ({type(erro).__name__}). Consulte o log da Luna.')
                futuro.set_exception(RuntimeError('Não foi possível transmitir esta fala.'))
    finally:
        await client.close()
        if tarefa:
            tarefa.cancel()
            await asyncio.gather(tarefa, return_exceptions=True)
