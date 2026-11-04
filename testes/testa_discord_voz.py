import asyncio
import queue
import unittest
from types import SimpleNamespace, ModuleType
from unittest.mock import patch
from integracoes.discord import ponte as p


class DiscordVoz(unittest.TestCase):
    def setUp(self):
        p._parar.clear()
        for key, value in [('_fila', queue.Queue(maxsize=4)), ('_thread', None), ('_envios', {}),
                           ('_estado', {'estado':'desligado','mensagem':'','jogos':False,'canal':''})]:
            m=patch.object(p,key,value);m.start();self.addCleanup(m.stop)
        self.addCleanup(p._parar.clear)

    def test_opcional_sem_config_e_sem_token_na_interface(self):
        with patch.object(p.config_env,'texto',return_value=''), patch.object(p.config_env,'inteiro',return_value=0):
            self.assertFalse(p.estado()['configurado'])
            with self.assertRaises(ValueError): p.conectar()
        self.assertNotIn('token',p.estado())
        with self.assertRaises(ValueError): p.enviar(texto='oi')

    def test_fila_limitada_e_saida(self):
        p._atualizar(estado='conectado')
        for _ in range(4): p.enviar(texto='oi')
        with self.assertRaises(ValueError): p.enviar(texto='extra')
        p.desconectar()
        with self.assertRaises(ValueError): p.enviar(texto='depois')
        self.assertFalse(p.estado()['jogos'])

    def test_avisos_pessoais_nao_sao_enviados(self):
        p._atualizar(estado='conectado', jogos=True)
        with patch.object(p,'enviar') as enviar:
            self.assertFalse(p.compartilhar_jogo([],SimpleNamespace(comentario_jogo=False),None))
            enviar.assert_not_called()

    def test_cliente_simulado_pcm_sem_escuta(self):
        d=ModuleType('discord');d.version_info=(2,7,1);d.AudioSource=object
        d.Intents=SimpleNamespace(none=lambda:SimpleNamespace())
        capturas={}
        class Voz:
            def is_connected(self): return True
            def play(self,src,after):
                capturas['pcm']=src.read();capturas['fim']=src.read()
                after(None);p._parar.set()
        class Canal:
            name='Teste'
            guild=SimpleNamespace(me=SimpleNamespace(voice=None))
            def permissions_for(self, membro):return SimpleNamespace(speak=True)
            async def connect(self,**kw):capturas.update(kw);return Voz()
        class Client:
            def __init__(self,**kw):capturas['intents']=kw['intents']
            async def login(self,token):pass
            async def connect(self,**kw):await asyncio.Future()
            async def wait_until_ready(self):pass
            def get_channel(self,id):return Canal()
            async def close(self):capturas['fechou']=True
        d.Client=Client;d.VoiceChannel=Canal
        pcm=ModuleType('integracoes.discord.pcm');pcm.converter=lambda _:b'\x01'*100
        with patch.dict('sys.modules',{'discord':d,'davey':ModuleType('davey'),'integracoes.discord.pcm':pcm}):
            p._atualizar(estado='conectado')
            futuro=p.enviar(audio=[0])
            asyncio.run(p._rodar('segredo',123))
        self.assertTrue(futuro.result())
        self.assertEqual(p.estado()['envios'][futuro.envio_id], 'Reprodução finalizada.')
        self.assertEqual(p._estado['mensagem'], 'Reprodução finalizada no bot; recepção no canal não confirmada.')
        self.assertGreater(p._estado['diagnostico']['pico'], 0)
        self.assertTrue(capturas['self_deaf'])
        self.assertEqual(len(capturas['pcm']),3840)
        self.assertEqual(capturas['fim'],b'')
        self.assertTrue(capturas['fechou'])

    def test_falha_descarta_fila_sem_vazar_token(self):
        p._atualizar(estado='conectado')
        f=p.enviar(texto='privado')
        async def falha(*args):raise RuntimeError('TOKEN_SECRETO')
        with patch.object(p,'_rodar',falha):p._executar('TOKEN_SECRETO',123)
        self.assertNotIn('TOKEN_SECRETO',str(p.estado()))
        with self.assertRaises(RuntimeError):f.result()
        self.assertEqual(p.estado()['envios'][f.envio_id], 'Falha ou envio interrompido.')
        self.assertTrue(p._fila.empty())

    def test_pcm_taxa_estereo_e_limites(self):
        import numpy as np
        from integracoes.discord.pcm import converter
        audio = np.zeros(24000, dtype=np.float32)
        audio[500:1000] = .5
        dados = converter(audio)
        self.assertEqual(len(dados), 48000 * 2 * 2)
        amostras = np.frombuffer(dados, dtype='<i2').reshape(-1,2)
        np.testing.assert_array_equal(amostras[:,0],amostras[:,1])
        self.assertGreater(amostras[:,0].max(), 15000)
        with self.assertRaises(ValueError): converter([])


if __name__=='__main__':unittest.main()
