"""Agenda estruturada: Google simulado, fluxo real e horários, sem OAuth/LLM/áudio."""
from contextlib import redirect_stdout
import datetime as dt
import io
import json
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from modulos import agenda_web as agenda, cartoes_web
from testes.bancada_dark_souls_thinking import extrair, preparar_runtime
from testes.testa_prompt_montagem import _Resposta


def evento(titulo='Reunião', inicio='2026-10-09T10:20:00-03:00', fim='2026-10-09T11:20:00-03:00', **kw):
    return dict(titulo=titulo, inicio=inicio, fim=fim, dia_inteiro=False, **kw)


class Relogio(dt.datetime):
    @classmethod
    def now(cls, tz=None):
        return dt.datetime(2026, 10, 9, 10, tzinfo=dt.timezone(dt.timedelta(hours=-3))).astimezone(tz)


class TestaAgendaWeb(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pensar = preparar_runtime()

    def habilidades(self):
        e = dict(datetime=dt, cor=Mock(), build=Mock(), obter_creds_google=Mock(return_value='credencial-simulada'),
                 _MESES_PT=['janeiro', 'fevereiro', 'março', 'abril', 'maio', 'junho', 'julho', 'agosto', 'setembro', 'outubro', 'novembro', 'dezembro'],
                 _DIAS_PT=['segunda', 'terça', 'quarta', 'quinta', 'sexta', 'sábado', 'domingo'])
        extrair('modulos/habilidades.py', {'ler_agenda_google', 'adicionar_evento_google', '_data_falavel'}, e)
        return e

    def test_leitura_google_entrega_dado_e_texto_compativeis(self):
        e = self.habilidades()
        eventos = [dict(summary='Reunião', location='Sala', htmlLink='https://calendar.google.com/event?eid=x',
                       start={'dateTime': '2026-10-09T13:20:00Z'}, end={'dateTime': '2026-10-09T14:20:00Z'}),
                   dict(summary='Viagem', start={'date': '2026-10-10'}, end={'date': '2026-10-12'})]
        service = e['build'].return_value.events.return_value
        service.list.return_value.execute.return_value = {'items': eventos, 'nextPageToken': 'outra-pagina'}
        antes = dt.datetime.now(dt.timezone.utc)
        resposta = e['ler_agenda_google']()
        depois = dt.datetime.now(dt.timezone.utc)
        pedido = service.list.call_args.kwargs
        inicio = dt.datetime.fromisoformat(pedido['timeMin'])
        self.assertTrue(antes <= inicio <= depois)
        self.assertEqual(dt.datetime.fromisoformat(pedido['timeMax']) - inicio, dt.timedelta(days=30))
        self.assertEqual(inicio.utcoffset(), dt.timedelta(0))
        self.assertEqual(resposta.eventos_agenda[0]['inicio'], dt.datetime.fromisoformat('2026-10-09T13:20:00+00:00').astimezone().isoformat())
        self.assertIn('Reunião —', str(resposta))
        self.assertNotIn('cartoes_web', str(resposta))
        self.assertEqual(resposta.cartoes_web[0]['eventos'][1]['fim'], '2026-10-12')
        self.assertTrue(resposta.cartoes_web[0]['mais'])
        service.insert.assert_not_called()

    def test_vazia_tem_cartao_mas_falha_nao_finge_agenda_vazia(self):
        e = self.habilidades()
        e['build'].return_value.events.return_value.list.return_value.execute.return_value = {'items': []}
        vazia = e['ler_agenda_google']()
        self.assertEqual(vazia.cartoes_web[0]['total'], 0)
        e['build'].side_effect = RuntimeError('Sem conexão')
        falha = e['ler_agenda_google']()
        self.assertTrue(falha.startswith('Erro'))
        self.assertFalse(hasattr(falha, 'cartoes_web'))

    def test_criacao_usa_evento_confirmado_pelo_google(self):
        e = self.habilidades()
        service = e['build'].return_value.events.return_value
        service.insert.return_value.execute.return_value = dict(summary='Título confirmado',
            start={'dateTime': '2026-10-09T10:20:00-03:00'}, end={'dateTime': '2026-10-09T11:20:00-03:00'},
            htmlLink='https://calendar.google.com/event?eid=x')
        resposta = e['adicionar_evento_google']('Reunião', '2026-10-09T10:20:00-03:00')
        self.assertEqual(resposta.cartoes_web[0]['titulo'], 'Compromisso criado')
        self.assertEqual(resposta.cartoes_web[0]['eventos'][0]['titulo'], 'Título confirmado')
        self.assertEqual(service.insert.call_count, 1)
        service.list.assert_not_called()
        service.insert.return_value.execute.side_effect = RuntimeError('Falhou')
        self.assertFalse(hasattr(e['adicionar_evento_google']('Reunião', '2026-10-09T10:20:00-03:00'), 'cartoes_web'))

    def test_metadados_limitados_e_invalidos_nao_viram_comandos(self):
        resposta = agenda.resultado('Texto falável.', [evento(url='javascript:alert(1)', local='<img src=x>')] * 60)
        self.assertEqual(len(resposta.eventos_agenda), 60)
        card = json.loads(json.dumps(cartoes_web.normalizar(resposta.cartoes_web)))[0]
        self.assertEqual(len(card['eventos']), 50)
        self.assertEqual(card['total'], 60)
        self.assertEqual(card['eventos'][0]['url'], '')
        self.assertEqual(card['eventos'][0]['local'], '<img src=x>')
        self.assertEqual(agenda.normalizar_eventos([None, {}, evento(inicio='2026-02-31T10:20:00-03:00'),
                                                  evento(inicio='2026-10-09T10:20:00')]), [])
        self.assertEqual(agenda.eventos_google([{'status': 'cancelled'}, {'start': 'inválido'}]), [])
        self.assertEqual(cartoes_web.normalizar([{'tipo': 'agenda', 'titulo': 'Agenda', 'eventos': {}}]), [])

    def test_avisos_respeitam_fuso_limite_e_fim_exclusivo(self):
        agora = Relogio.now()
        eventos = agenda.normalizar_eventos([evento('Próximo'), evento('Passou', inicio='2026-10-09T09:59:00-03:00'),
            evento('Distante', inicio='2026-10-09T10:31:00-03:00'),
            dict(titulo='Viagem hoje', inicio='2026-10-08', fim='2026-10-10', dia_inteiro=True),
            dict(titulo='Viagem encerrada', inicio='2026-10-08', fim='2026-10-09', dia_inteiro=True)])
        proximos = agenda.proximos(eventos, agora, 30)
        self.assertEqual({(e['titulo'], quando) for e, quando in proximos}, {('Próximo', 'em 20 min'), ('Viagem hoje', 'hoje')})
        noturno = agenda.normalizar_eventos([evento('Noturno', inicio='2026-10-08T23:00:00-03:00', fim='2026-10-09T01:00:00-03:00')])
        self.assertEqual(len(agenda.eventos_do_dia(noturno, agora.date())), 1)

    def test_alerta_usa_estrutura_e_transporta_so_os_compromissos_proximos(self):
        e = self.proativa()
        eventos = [evento(), evento('Amanhã', inicio='2026-10-10T10:20:00-03:00', fim='2026-10-10T11:20:00-03:00')]
        e['ler_agenda_google'].return_value = agenda.resultado('Datas por extenso, sem pipe ou ISO.', eventos)
        e['_tarefa_checar_agenda']()
        fala = e['_falar_proativamente'].call_args.args[0]
        self.assertEqual([x['titulo'] for x in fala.cartoes_web[0]['eventos']], ['Reunião'])
        self.assertIn('Reunião (em 20 min)', e['_gerar_fala_proativa'].call_args.args[0])
        self.assertNotIn('Amanhã', e['_gerar_fala_proativa'].call_args.args[0])
        e['ler_agenda_google'].return_value = 'Erro: Sem conexão'
        e['_falar_proativamente'].reset_mock()
        e['_tarefa_checar_agenda']()
        e['_falar_proativamente'].assert_not_called()

    def proativa(self):
        e = dict(datetime=SimpleNamespace(datetime=Relogio, timedelta=dt.timedelta),
            CONFIGURACAO={'agenda': {'ativo': True, 'intervalo_minutos': 30, 'antecedencia_aviso_minutos': 30},
                          'bom_dia': {'ativo': True, 'horario_falar': (8, 11)}},
            _passou_intervalo=Mock(return_value=True), ler_agenda_google=Mock(),
            checar_emails_nao_lidos=Mock(return_value='Nenhum email novo.'),
            ler_estado_proativo=Mock(return_value={}), salvar_estado_proativo=Mock(),
            registrar_tentativa=Mock(), cor=Mock(), REGRA_PERSONA='')
        extrair('modulos/proativa.py', {'_tarefa_checar_agenda', '_tarefa_bom_dia', '_FalaProativa'}, e)
        e['_gerar_fala_proativa'] = Mock(side_effect=lambda *a, **kw: e['_FalaProativa']('Comentário natural.'))
        e['_falar_proativamente'] = Mock(return_value=True)
        return e

    def test_bom_dia_filtra_hoje_no_texto_e_no_cartao(self):
        e = self.proativa()
        e['ler_agenda_google'].return_value = agenda.resultado('Lista de 30 dias', [evento(),
            evento('Amanhã', inicio='2026-10-10T10:20:00-03:00', fim='2026-10-10T11:20:00-03:00')])
        with redirect_stdout(io.StringIO()):
            e['_tarefa_bom_dia']()
        self.assertNotIn('Amanhã', e['_gerar_fala_proativa'].call_args.args[0])
        fala = e['_falar_proativamente'].call_args.args[0]
        self.assertEqual([x['titulo'] for x in fala.cartoes_web[0]['eventos']], ['Reunião'])
        self.assertEqual(fala.cartoes_web[0]['titulo'], 'Agenda de hoje')

    def test_fluxo_roteador_persona_preserva_cartao_na_web_e_voz(self):
        p = self.pensar
        tecnico = agenda.resultado('Aqui estão os compromissos: Reunião às 10h20.', [evento()])
        resposta = _Resposta()
        resposta.choices[0].message.tool_calls = [SimpleNamespace(function=SimpleNamespace(name='ler_agenda_google', arguments='{}'))]
        for pc, completo in ((True, True), (True, False), (False, True)):
            with self.subTest(pc=pc, completo=completo), redirect_stdout(io.StringIO()), \
                 patch.object(p, '_capturar_momento', return_value={'canal': 'web' if pc else 'telegram'}), \
                 patch.object(p, 'ATIVAR_MEMORIA_PERMANENTE', False), \
                 patch.object(p.obsidian, 'indice_notas', return_value=''), \
                 patch.object(p, '_chamar_llm', return_value=resposta) as chamar, \
                 patch.object(p, '_reescrever_como_luna', return_value='Claro, está na sua agenda.') as persona, \
                 patch.dict(p.FUNCOES_DISPONIVEIS, {'ler_agenda_google': Mock(return_value=tecnico)}), \
                 patch('modulos.metricas_ferramentas.registrar_uso'):
                saida = p.gerar_resposta('Consulte minha agenda', [], salvar=False, responder_completo=completo, presenca_pc=pc)
                chamar.assert_called_once()
                persona.assert_called_once()
                self.assertIs(persona.call_args.args[0], tecnico)
                self.assertEqual(hasattr(saida, 'cartoes_web'), pc)
                self.assertNotIn('https', str(saida))

    def test_handler_web_nao_perde_metadados_ao_limpar_a_resposta(self):
        from modulos import execucoes, acompanhamentos, acompanhamento_sopro, conclusao_tarefas
        e = dict(conversa=execucoes.conversa, _interromper=Mock(), _historico_conversa=[],
            cor=Mock(), _log=Mock(), atualizar_status=Mock(), registrar_interacao=Mock(),
            marcar_luna_ocupada=Mock(), atualizar_usuario=Mock(), atualizar_estado_rosto=Mock(),
            injetar_arquivo_pendente=lambda t: t,
            gerar_resposta=Mock(return_value=agenda.resultado(' Resposta natural. ', [evento()])),
            obter_clima_resposta=lambda: 'zoeira', atualizar_legenda=Mock(),
            _mostrar_resposta_web_no_terminal=Mock(), atualizar_stream_resposta=Mock(),
            atualizar_stream_interrompido=Mock(), GeracaoInterrompida=RuntimeError)
        extrair('main.py', {'responder_texto_web'}, e)
        with patch.object(execucoes, 'controle', execucoes.Coordenador(pausa=0)), \
             patch.object(acompanhamentos, 'interceptar_resposta', return_value=None), \
             patch.object(acompanhamento_sopro, 'interceptar_pedido', return_value=None), \
             patch.object(conclusao_tarefas, 'interceptar_resposta', return_value=None):
            e['responder_texto_web']('Consulte minha agenda')
        fala = e['atualizar_legenda'].call_args.args[0]
        self.assertEqual(str(fala), 'Resposta natural.')
        self.assertEqual(fala.cartoes_web[0]['eventos'][0]['titulo'], 'Reunião')


if __name__ == '__main__':
    unittest.main()
