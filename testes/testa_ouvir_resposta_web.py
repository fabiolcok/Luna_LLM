"""A leitura não muda a conversa e perde prioridade quando o usuário volta a falar."""
import json
import threading
import unittest
from unittest.mock import Mock, patch

import servidor
from modulos import execucoes
from testes.bancada_dark_souls_thinking import extrair, preparar_runtime


class TestaOuvirRespostaWeb(unittest.TestCase):
    def setUp(self):
        self.controle = execucoes.Coordenador(pausa=0)
        self.handler = Mock(side_effect=lambda texto, cb: cb())
        self.ws = Mock()
        for p in (patch.object(servidor, 'controle', self.controle),
                  patch.object(servidor, '_historico_web', [{'id':'antigo', 'luna':'**Uma resposta antiga.**'}]),
                  patch.object(servidor, '_audios_web', {}),
                  patch.object(servidor, '_handler_ouvir_web', self.handler),
                  patch.object(servidor, '_broadcast'), patch.object(servidor, 'atualizar_estado_rosto')):
            p.start(); self.addCleanup(p.stop)

    def test_texto_e_resolvido_no_servidor_sem_nova_resposta(self):
        with patch.object(servidor.threading, 'Thread') as thread, \
             patch.object(servidor, '_registrar_turno') as registrar:
            servidor._receber_ouvir_web(self.ws, {'turno_id':'antigo', 'request_id':'audio-1', 'texto':'Texto adulterado'})
            self.handler.assert_not_called()
            servidor._receber_ouvir_web(self.ws, {'turno_id':'antigo', 'request_id':'audio-1'})
            thread.assert_called_once()
            thread.call_args.kwargs['target']()
            self.handler.assert_called_once()
            self.assertEqual(self.handler.call_args.args[0], '**Uma resposta antiga.**')
            registrar.assert_not_called()
        self.assertEqual(servidor._audios_web, {})
        self.assertEqual([c.args[0]['estado'] for c in servidor._broadcast.call_args_list], ['fila','gerando','falando','fim'])

    def test_resposta_ausente_nao_reserva_nem_chama_tts(self):
        servidor._receber_ouvir_web(self.ws, {'turno_id':'inexistente', 'request_id':'audio-1'})
        self.handler.assert_not_called()
        self.assertFalse(self.controle.fila)
        self.assertEqual(json.loads(self.ws.send.call_args.args[0])['estado'], 'erro')

    def test_mensagem_nova_cancela_leitura_em_fila(self):
        with patch.object(servidor.threading, 'Thread') as thread:
            servidor._receber_ouvir_web(self.ws, {'turno_id':'antigo', 'request_id':'audio-1'})
            usuario = self.controle.reservar()
            thread.call_args.kwargs['target']()
        self.handler.assert_not_called()
        with self.controle.executar(usuario):
            self.controle.verificar()
        self.assertEqual(servidor._broadcast.call_args.args[0]['estado'], 'interrompido')

    def test_nova_conversa_para_audio_e_invalida_callback_tardio(self):
        stop = Mock(); self.controle.parar_audio = stop
        with self.controle.executar(self.controle.reservar(leitura=True)) as leitura:
            efeito = self.controle.efeito(Mock())
            novo = self.controle.reservar()
            self.assertTrue(leitura.cancelada.is_set())
            stop.assert_called_once()
            efeito(); efeito.__wrapped__.assert_not_called()
        with self.controle.executar(novo):
            self.controle.verificar()

    def test_parar_so_afeta_a_leitura_referenciada(self):
        with patch.object(servidor.threading, 'Thread') as thread:
            servidor._receber_ouvir_web(self.ws, {'turno_id':'antigo', 'request_id':'audio-1'})
            servidor._parar_leitura_web('outro')
            self.assertFalse(next(iter(servidor._audios_web.values()))['execucao'].cancelada.is_set())
            servidor._parar_leitura_web('audio-1')
            thread.call_args.kwargs['target']()
        self.handler.assert_not_called()

    def test_main_so_sintetiza_texto_limpo_sem_llm_e_sem_historico(self):
        p = preparar_runtime()
        callbacks = []
        env = dict(registrar_interacao=Mock(), marcar_luna_ocupada=Mock(), controle=self.controle,
            _interromper=threading.Event(), atualizar_estado_rosto=Mock())
        def fluxo(**kw):
            f = Mock(aguardar=Mock(return_value=True))
            def finalizar(texto):
                callbacks.append(p.limpar_texto_para_voz(texto)); kw['ao_iniciar']()
            f.finalizar.side_effect = finalizar
            return f
        env['FalaEmFluxo'] = fluxo
        extrair('main.py', {'ouvir_resposta_web'}, env)
        env['ouvir_resposta_web']('**Teste** com [fonte](https://example.org/).', Mock())
        self.assertEqual(callbacks, ['Teste com fonte.'])
        self.assertEqual(env['marcar_luna_ocupada'].call_args_list[-1].args, (False,))

    def test_sintese_lenta_nao_retem_fila_quando_chega_mensagem(self):
        novos = []
        def aguardar(timeout):
            novos.append(self.controle.reservar()); return False
        fluxo = Mock(aguardar=Mock(side_effect=aguardar))
        env = dict(registrar_interacao=Mock(), marcar_luna_ocupada=Mock(), controle=self.controle,
            _interromper=threading.Event(), atualizar_estado_rosto=Mock(), FalaEmFluxo=Mock(return_value=fluxo))
        extrair('main.py', {'ouvir_resposta_web'}, env)
        with self.controle.executar(self.controle.reservar(leitura=True)):
            env['ouvir_resposta_web']('Um texto longo.', None)
        fluxo.cancelar.assert_called_once()
        fluxo.aguardar.assert_called_once_with(.1)
        with self.controle.executar(novos[0]):
            self.controle.verificar()


if __name__ == '__main__':
    unittest.main()
