"""Entrega do texto e confirmação, sem iniciar a Luna nem chamar o modelo."""
import json
import threading
import unittest
from unittest.mock import Mock, patch

from simple_websocket import Client
from werkzeug.serving import make_server

import servidor
from modulos import execucoes


class TestaRecebimentoWeb(unittest.TestCase):
    def test_confirma_depois_de_iniciar_trabalho_reservado(self):
        ws = Mock()
        trabalho = Mock()
        handler = Mock(preparar=Mock(return_value=trabalho))
        ordem = []
        ws.send.side_effect = lambda payload: ordem.append(json.loads(payload))
        with patch.object(servidor, '_handler_texto_web', handler), patch.object(servidor.threading, 'Thread') as thread:
            thread.return_value.start.side_effect = lambda: ordem.append('thread iniciada')
            servidor._receber_texto_web(ws, {'texto': '  Olá  ', 'request_id': 'a'})
        handler.preparar.assert_called_once_with('Olá')
        thread.assert_called_once_with(target=trabalho, daemon=True)
        self.assertEqual(ordem[0], 'thread iniciada')
        self.assertTrue(ordem[1]['ok'])
        self.assertEqual(ordem[1]['request_id'], 'a')

    def test_handler_sem_reserva_continua_funcionando(self):
        def handler(texto):
            pass
        ws = Mock()
        with patch.object(servidor, '_handler_texto_web', handler), patch.object(servidor.threading, 'Thread') as thread:
            servidor._receber_texto_web(ws, {'texto': 'Olá'})
        thread.assert_called_once_with(target=handler, args=('Olá',), daemon=True)
        self.assertTrue(json.loads(ws.send.call_args.args[0])['ok'])

    def test_sem_handler_nao_confirma_envio(self):
        ws = Mock()
        with patch.object(servidor, '_handler_texto_web', None), patch.object(servidor.threading, 'Thread') as thread:
            servidor._receber_texto_web(ws, {'texto': 'Olá', 'request_id': 'a'})
        thread.assert_not_called()
        retorno = json.loads(ws.send.call_args.args[0])
        self.assertFalse(retorno['ok'])
        self.assertTrue(retorno['erro'])

    def test_texto_vazio_nao_entra_na_fila(self):
        ws = Mock()
        with patch.object(servidor, '_handler_texto_web', Mock()), patch.object(servidor.threading, 'Thread') as thread:
            servidor._receber_texto_web(ws, {'texto': '   ', 'request_id': 'a'})
        thread.assert_not_called()
        self.assertFalse(json.loads(ws.send.call_args.args[0])['ok'])

    def test_websocket_real_confirma_fila_antes_da_resposta(self):
        c = execucoes.Coordenador(pausa=0)
        atendidos = []
        terminou = threading.Event()
        with patch.object(execucoes, 'controle', c), patch.object(servidor, 'controle', c), \
             patch.object(servidor, '_config_para_web', return_value={}), \
             patch.object(servidor, '_memoria_estado', return_value={'pendentes': []}), \
             patch.object(servidor, '_acompanhamentos_estado', return_value={}), \
             patch.object(servidor, 'atualizar_status'):
            @execucoes.conversa
            def handler(texto):
                atendidos.append(texto)
                if len(atendidos) == 3:
                    terminou.set()

            with patch.object(servidor, '_handler_texto_web', handler):
                http = make_server('127.0.0.1', 0, servidor.app, threaded=True)
                thread = threading.Thread(target=http.serve_forever, daemon=True)
                thread.start()
                client = None
                try:
                    client = Client.connect(f'ws://127.0.0.1:{http.server_port}/ws')
                    for _ in range(6):
                        self.assertIsNotNone(client.receive(timeout=2))
                    # Simula uma tarefa proativa ocupando a execução. A fila confirma
                    # cada entrada sem aguardar o modelo, mas mantém a ordem das respostas.
                    with c.executar(proativa=True):
                        for numero in range(3):
                            client.send(json.dumps({'tipo': 'mensagem_texto', 'texto': f'texto {numero}',
                                                    'request_id': str(numero)}))
                            retorno = json.loads(client.receive(timeout=2))
                            self.assertEqual(retorno['tipo'], 'mensagem_texto_recebida')
                            self.assertEqual(retorno['request_id'], str(numero))
                            self.assertTrue(retorno['ok'])
                        self.assertEqual(atendidos, [])
                    self.assertTrue(terminou.wait(2))
                    self.assertEqual(atendidos, ['texto 0', 'texto 1', 'texto 2'])
                finally:
                    if client is not None:
                        client.close()
                    http.shutdown()
                    http.server_close()
                    thread.join(2)


if __name__ == '__main__':
    unittest.main()
