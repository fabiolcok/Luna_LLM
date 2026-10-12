"""Entrega do texto e confirmação, sem iniciar a Luna nem chamar o modelo."""
import json
import ast
from pathlib import Path
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from simple_websocket import Client
from werkzeug.serving import make_server

import servidor
from modulos import execucoes


class TestaRecebimentoWeb(unittest.TestCase):
    def setUp(self):
        self.patch_textos = patch.object(servidor, '_textos_web', {})
        self.patch_textos.start()
        self.addCleanup(self.patch_textos.stop)

    def test_confirma_depois_de_iniciar_trabalho_reservado(self):
        ws = Mock()
        trabalho = Mock()
        handler = Mock(preparar=Mock(return_value=trabalho))
        ordem = []
        ws.send.side_effect = lambda payload: ordem.append(json.loads(payload))
        with patch.object(servidor, '_handler_texto_web', handler), \
             patch.object(servidor, '_broadcast') as broadcast, \
             patch.object(servidor.threading, 'Thread') as thread:
            thread.return_value.start.side_effect = lambda: ordem.append('thread iniciada')
            servidor._receber_texto_web(ws, {'texto': '  Olá  ', 'request_id': 'a'})
            fila = broadcast.call_args.args[0]['mensagens']
            self.assertEqual(fila[0]['usuario'], 'Olá')
            self.assertEqual(fila[0]['estado'], 'fila')
            self.assertNotIn('recebido_em', fila[0])
            trabalho.assert_not_called()
            thread.call_args.kwargs['target']()
            trabalho.assert_called_once_with()
            self.assertEqual(broadcast.call_args.args[0]['mensagens'], [])
            self.assertIsNone(servidor._texto_web_id.get())
        handler.preparar.assert_called_once_with('Olá')
        thread.assert_called_once()
        self.assertTrue(thread.call_args.kwargs['daemon'])
        self.assertEqual(ordem[0], 'thread iniciada')
        self.assertTrue(ordem[1]['ok'])
        self.assertEqual(ordem[1]['request_id'], 'a')

    def test_handler_sem_reserva_continua_funcionando(self):
        handler = Mock(spec=lambda texto: None)
        ws = Mock()
        with patch.object(servidor, '_handler_texto_web', handler), \
             patch.object(servidor, '_broadcast'), patch.object(servidor.threading, 'Thread') as thread:
            servidor._receber_texto_web(ws, {'texto': 'Olá'})
            thread.call_args.kwargs['target']()
        handler.assert_called_once_with('Olá')
        thread.assert_called_once()
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

    def test_proxima_mensagem_nao_espera_animacao_da_resposta_anterior(self):
        # Carrega só o handler: importar main iniciaria motores de voz e atalhos.
        from modulos import acompanhamentos, conclusao_tarefas, acompanhamento_sopro
        fn = next(n for n in ast.parse(Path('main.py').read_text(encoding='utf-8')).body
                  if isinstance(n, ast.FunctionDef) and n.name == 'responder_texto_web')
        sono = Mock(side_effect=AssertionError('Pausa visual segurou a fila do texto'))
        legenda = Mock()
        escopo = {
            'conversa': execucoes.conversa, '_interromper': threading.Event(),
            '_historico_conversa': [], 'time': SimpleNamespace(sleep=sono), 'cor': Mock(), '_log': Mock(),
            'atualizar_status': Mock(), 'registrar_interacao': Mock(), 'marcar_luna_ocupada': Mock(),
            'atualizar_usuario': Mock(), 'atualizar_estado_rosto': Mock(),
            'injetar_arquivo_pendente': lambda texto: texto,
            'gerar_resposta': Mock(return_value='Resposta'), 'obter_clima_resposta': lambda: 'zoeira',
            'atualizar_legenda': legenda, '_mostrar_resposta_web_no_terminal': Mock(),
            'atualizar_stream_resposta': Mock(), 'atualizar_stream_interrompido': Mock(),
            'GeracaoInterrompida': RuntimeError,
        }
        with patch.object(execucoes, 'controle', execucoes.Coordenador(pausa=0)), \
             patch.object(acompanhamentos, 'interceptar_resposta', return_value=None), \
             patch.object(conclusao_tarefas, 'interceptar_resposta', return_value=None), \
             patch.object(acompanhamento_sopro, 'interceptar_pedido', return_value=None):
            exec(compile(ast.Module(body=[fn], type_ignores=[]), 'handler-web-isolado', 'exec'), escopo)
            responder = escopo['responder_texto_web']
            primeira, segunda = responder.preparar('primeira'), responder.preparar('segunda')
            primeira()
            segunda()
        sono.assert_not_called()
        self.assertEqual([c.args[0] for c in escopo['atualizar_usuario'].call_args_list], ['primeira', 'segunda'])
        self.assertEqual([c.args[0] for c in legenda.call_args_list], ['Resposta', 'Resposta'])

    def test_resposta_recebe_id_da_mensagem_em_execucao(self):
        from modulos import avaliacoes
        capturados = []
        def handler(texto):
            servidor.atualizar_usuario(texto)
            servidor.atualizar_legenda('Resposta correta')
        with patch.object(servidor, '_handler_texto_web', handler), \
             patch.object(servidor, '_historico_web', []), \
             patch.object(servidor, '_ultima_fala_usuario', 'turno anterior'), \
             patch.object(servidor, '_ultima_fala_luna', ''), \
             patch.object(servidor, '_broadcast', side_effect=capturados.append), \
             patch.object(avaliacoes, 'capturar_turno', return_value='r1'), \
             patch.object(servidor.threading, 'Thread') as thread:
            servidor._receber_texto_web(Mock(), {'texto': 'primeira'})
            primeiro = thread.call_args.kwargs['target']
            id_primeiro = capturados[-1]['mensagens'][0]['id']
            servidor._receber_texto_web(Mock(), {'texto': 'segunda'})
            self.assertEqual(servidor._ultima_fala_usuario, 'turno anterior')
            primeiro()
            resposta = next(p['turno'] for p in capturados if p.get('tipo') == 'historico_novo')
            self.assertEqual(resposta['usuario'], 'primeira')
            self.assertEqual(resposta['request_id'], id_primeiro)
            self.assertEqual(capturados[-1]['mensagens'][0]['usuario'], 'segunda')

    def test_websocket_real_confirma_fila_antes_da_resposta(self):
        c = execucoes.Coordenador(pausa=0)
        atendidos = []
        terminou = threading.Event()
        with patch.object(execucoes, 'controle', c), patch.object(servidor, 'controle', c), \
             patch.object(servidor, '_config_para_web', return_value={}), \
             patch.object(servidor, '_memoria_estado', return_value={'pendentes': []}), \
             patch.object(servidor, '_acompanhamentos_estado', return_value={}), \
             patch.object(servidor, '_ultima_fala_usuario', 'turno anterior'):
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
                            fila = json.loads(client.receive(timeout=2))
                            self.assertEqual(fila['tipo'], 'fila_texto')
                            self.assertEqual([m['usuario'] for m in fila['mensagens']],
                                             [f'texto {i}' for i in range(numero + 1)])
                            self.assertTrue(all(m['estado'] == 'fila' for m in fila['mensagens']))
                            retorno = json.loads(client.receive(timeout=2))
                            self.assertEqual(retorno['tipo'], 'mensagem_texto_recebida')
                            self.assertEqual(retorno['request_id'], str(numero))
                            self.assertTrue(retorno['ok'])
                        self.assertEqual(atendidos, [])
                        self.assertEqual(servidor._ultima_fala_usuario, 'turno anterior')
                        # Outra janela recebe o mesmo estado, inclusive após reconexão.
                        outro = Client.connect(f'ws://127.0.0.1:{http.server_port}/ws')
                        try:
                            outro.receive(timeout=2)  # rosto/legenda
                            outro.receive(timeout=2)  # configuração
                            historico = json.loads(outro.receive(timeout=2))
                            self.assertEqual(len(historico['pendentes']), 3)
                        finally:
                            outro.close()
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
