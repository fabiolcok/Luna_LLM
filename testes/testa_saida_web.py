"""Uma conexão que parou de receber não pode bloquear a conversa nem outras janelas."""
import threading
import unittest
from unittest.mock import Mock, patch

import servidor
from modulos.execucoes import Coordenador


class TestaSaidaWeb(unittest.TestCase):
    def test_cliente_lento_nao_segura_reserva_nem_outro_cliente(self):
        entrou = threading.Event()
        liberar = threading.Event()
        lento = Mock()
        lento.send.side_effect = lambda payload: (entrou.set(), liberar.wait(2))
        rapido = Mock()
        entregue = threading.Event()
        rapido.send.side_effect = lambda payload: entregue.set()
        canais = [servidor._ClienteWeb(lento), servidor._ClienteWeb(rapido)]
        c = Coordenador(pausa=0)
        publicar = c.efeito(servidor._broadcast)
        reservado = threading.Event()
        try:
            with patch.object(servidor, '_clientes', set(canais)):
                with c.executar(proativa=True) as turno:
                    publicar({'legenda': 'Rotina matinal'})
                    self.assertTrue(entrou.wait(1))
                    self.assertTrue(entregue.wait(1), 'Conexão travada bloqueou a outra janela.')
                    thread = threading.Thread(target=lambda: (c.reservar(), reservado.set()))
                    thread.start()
                    self.assertTrue(reservado.wait(1), 'Envio na rede segurou a reserva do chat.')
                    self.assertTrue(turno.cancelada.is_set())
                    thread.join(1)
                    self.assertFalse(liberar.is_set(), 'Teste liberou o cliente lento cedo demais.')
        finally:
            liberar.set()
            for canal in canais:
                canal.encerrar()

    def test_eventos_da_mesma_conexao_preservam_ordem(self):
        recebidos = []
        pronto = threading.Event()
        ws = Mock()
        def enviar(payload):
            recebidos.append(payload)
            if len(recebidos) == 4:
                pronto.set()
        ws.send.side_effect = enviar
        canal = servidor._ClienteWeb(ws)
        try:
            for payload in ('fila', 'confirmacao', 'usuario', 'resposta'):
                canal.send(payload)
            self.assertTrue(pronto.wait(1))
            self.assertEqual(recebidos, ['fila', 'confirmacao', 'usuario', 'resposta'])
        finally:
            canal.encerrar()

    def test_fila_cheia_desconecta_sem_crescimento_ilimitado(self):
        entrou = threading.Event()
        liberar = threading.Event()
        ws = Mock()
        ws.send.side_effect = lambda payload: (entrou.set(), liberar.wait(2))
        canal = servidor._ClienteWeb(ws)
        try:
            canal.send('ocupado')
            self.assertTrue(entrou.wait(1))
            for numero in range(128):
                canal.send(str(numero))
            with self.assertRaises(servidor.ConnectionClosed):
                canal.send('excedente')
            self.assertTrue(canal.encerrado.is_set())
            ws.sock.shutdown.assert_called_once()
            self.assertEqual(canal.fila.qsize(), 128)
        finally:
            liberar.set()
            canal.encerrar()


if __name__ == '__main__':
    unittest.main()
