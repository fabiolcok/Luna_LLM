"""Contratos de saída RSS e cliques contextualizados, sem gerar voz ou chamar LLM."""
import ast
import json
from pathlib import Path
import re
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

import servidor
from modulos import cartoes_web, novidades_web, prompts
from testes.bancada_sugestoes_novidades import executar_radar, gerar_persona
from testes.bancada_dark_souls_thinking import preparar_runtime, extrair


PERGUNTAS = ['Como fizeram esse teste?', 'Como reduzir o risco de burn-in?', 'OLED ainda vale a pena?']


class TestaSugestoesNovidades(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pensar = preparar_runtime()

    def test_persona_separa_metadados_antes_da_voz_e_preserva_clima(self):
        bruto = '**Comentário** natural. <sugestoes>' + json.dumps(PERGUNTAS) + '</sugestoes> [clima:zoeira]'
        for voz in (True, False):
            with self.subTest(voz=voz):
                fala, pedidos = gerar_persona(self.pensar, 'Notícia de teste.', bruto=bruto, voz=voz)
                self.assertEqual(str(fala), 'Comentário natural.' if voz else '**Comentário** natural.')
                self.assertEqual(fala.sugestoes_novidade, PERGUNTAS)
                self.assertEqual(self.pensar.obter_clima_resposta(), 'zoeira')
                self.assertEqual(len(pedidos), 1)
                self.assertIn(prompts.SUGESTOES_NOVIDADE_WEB, pedidos[0]['messages'][-1]['content'])
                self.assertIn(prompts.EMOCAO, pedidos[0]['messages'][0]['content'])

    def test_stream_nao_vaza_json_nem_tag_de_sugestoes(self):
        previas, finais = [], []
        def fragmento(t):
            previas.append(t)
        fragmento.finalizar = finais.append
        bruto = 'Comentário comprido para acompanhar a notícia. <sugestoes>' + json.dumps(PERGUNTAS) + '</sugestoes> [clima:zoeira]'
        fala, _ = gerar_persona(self.pensar, 'Notícia de teste.', bruto=bruto, fragmento=fragmento)
        self.assertTrue(previas)
        for t in previas + finais:
            self.assertNotIn('sugestoes', t)
            self.assertNotIn('OLED', t)
        self.assertEqual(finais, ['Comentário comprido para acompanhar a notícia.'])
        self.assertEqual(fala.sugestoes_novidade, PERGUNTAS)

    def test_json_invalido_ou_cortado_entrega_comentario_sem_botoes(self):
        for cauda in ('', '<sugestoes>["Como fizeram esse teste?', '<sugestoes', '<suges',
                      '<sugestoes>não é JSON</sugestoes> [clima:zoeira]',
                      '<sugestoes>{"acao":"apagar"}</sugestoes> [clima:zoeira]'):
            with self.subTest(cauda=cauda):
                fala, _ = gerar_persona(self.pensar, 'Notícia.', bruto='Comentário natural. ' + cauda)
                self.assertEqual(fala, 'Comentário natural.')
                self.assertEqual(fala.sugestoes_novidade, [])

    def test_outras_origens_nao_recebem_instrucao_nem_metadados(self):
        for tarefa in ('radar_promocoes', 'steam_abriu_Jogo', 'dark_souls_morte', None):
            with self.subTest(tarefa=tarefa):
                fala, pedidos = gerar_persona(self.pensar, 'Fato de teste.', tarefa=tarefa)
                self.assertNotIn(prompts.SUGESTOES_NOVIDADE_WEB, pedidos[0]['messages'][-1]['content'])
                self.assertFalse(hasattr(fala, 'sugestoes_novidade'))

    def test_filtro_limita_duplicadas_e_rejeita_acoes_html_links(self):
        valores = [None, {}, '<b>Como foi?</b>', 'https://exemplo.org?', 'Como foi?\nAgora?',
                   'Salve isto', 'x' * 101 + '?', PERGUNTAS[0], PERGUNTAS[0].upper(), PERGUNTAS[1], PERGUNTAS[2]]
        # O filtro limita a inspeção de uma saída excessiva; a lista normal é independente.
        self.assertEqual(novidades_web.normalizar_sugestoes(PERGUNTAS * 2), PERGUNTAS)
        self.assertEqual(novidades_web.normalizar_sugestoes(valores)[:2], PERGUNTAS[:2])
        self.assertEqual(novidades_web.normalizar_sugestoes({'perguntas': PERGUNTAS}), [])

    def test_wrapper_proativo_preserva_sugestoes_sem_incluir_na_string(self):
        fala = novidades_web.FalaComSugestoes('Comentário natural.', PERGUNTAS)
        e = {'_execucoes': Mock(), '_pode_falar_proativo': lambda: True, 'cor': Mock(),
             '_historico_proativo': [], '_historico_principal': [], '_falas_recentes': [],
             '_contexto_recente_para_proativo': lambda _: '', 're': re,
             'gerar_resposta': Mock(return_value=fala), 'obter_clima_resposta': lambda: 'zoeira'}
        e['_execucoes'].contexto.get.return_value = None
        extrair('modulos/proativa.py', {'_gerar_fala_proativa', '_FalaProativa'}, e)
        with patch.object(servidor, 'atualizar_status'):
            saida = e['_gerar_fala_proativa']('Notícia.', 'radar_rss', variar=False)
        self.assertEqual(str(saida), 'Comentário natural.')
        self.assertEqual(saida.origem_proativa, 'radar_rss')
        self.assertEqual(saida.sugestoes_novidade, PERGUNTAS)
        e['gerar_resposta'].assert_called_once()

    def test_radar_associa_sugestoes_a_noticia_sorteada_com_uma_chamada(self):
        fala = novidades_web.FalaComSugestoes('Comentário.', PERGUNTAS)
        # Usa a mesma classe que transporta origem/clima na produção.
        e = {}
        extrair('modulos/proativa.py', {'_FalaProativa'}, e)
        fala = e['_FalaProativa'](fala, 'radar_rss', 'zoeira')
        fala.sugestoes_novidade = PERGUNTAS
        gerar = Mock(return_value=fala)
        casos = [{'id': 'primeira', 'titulo': 'Monitor OLED', 'resumo': 'Resumo selecionado.'},
                 {'id': 'outra', 'titulo': 'Outra notícia', 'resumo': 'Outro resumo.'}]
        falas, _ = executar_radar(casos, gerar)
        gerar.assert_called_once()
        card = cartoes_web.normalizar(falas[0].cartoes_web)[0]
        self.assertEqual(card['titulo'], 'Monitor OLED')
        self.assertEqual(card['resumo'], 'Resumo selecionado.')
        self.assertEqual(card['sugestoes'], PERGUNTAS)
        self.assertEqual(card['url'], falas[0].links_novidades['noticia'])
        self.assertEqual(card['mais'], 1)

    def noticia_historica(self):
        return {'id': 'rss-antigo', 'origem_proativa': 'radar_rss', 'cartoes_web': [
            cartoes_web.noticia('Monitor OLED', 'Feed', 'https://example.org/oled',
                resumo='Teste após 30 meses.', sugestoes=PERGUNTAS)]}

    def test_clique_resolve_noticia_antiga_e_isola_contexto_de_mensagens_normais(self):
        historico = [self.noticia_historica(), {'id': 'recente', 'luna': 'Agora falando de jogos.'}]
        capturados = []
        def handler(texto):
            capturados.append((texto, novidades_web.contexto_novidade.get()))
        referencia = {'turno_id': 'rss-antigo', 'indice': 1}
        with patch.object(servidor, '_historico_web', historico), \
             patch.object(servidor, '_textos_web', {}), patch.object(servidor, '_handler_texto_web', handler), \
             patch.object(servidor, '_broadcast'), patch.object(servidor.threading, 'Thread') as thread:
            ws = Mock()
            servidor._receber_texto_web(ws, {'texto': 'Texto adulterado', 'novidade': referencia})
            worker_noticia = thread.call_args.kwargs['target']
            self.assertEqual(next(iter(servidor._textos_web.values()))['usuario'], PERGUNTAS[1])
            self.assertTrue(json.loads(ws.send.call_args.args[0])['ok'])
            servidor._receber_texto_web(ws, {'texto': 'Mensagem normal'})
            worker_normal = thread.call_args.kwargs['target']
            worker_noticia()
            worker_normal()
        self.assertEqual(capturados[0][0], PERGUNTAS[1])
        self.assertEqual(capturados[0][1]['titulo'], 'Monitor OLED')
        self.assertEqual(capturados[0][1]['resumo'], 'Teste após 30 meses.')
        self.assertEqual(capturados[1], ('Mensagem normal', None))
        self.assertIsNone(novidades_web.contexto_novidade.get())

    def test_clique_invalido_nao_gera_turno(self):
        for referencia in (None, {}, {'turno_id': 'removido', 'indice': 0},
                           {'turno_id': 'rss-antigo', 'indice': True}, {'turno_id': 'rss-antigo', 'indice': 4}):
            with self.subTest(referencia=referencia), patch.object(servidor, '_historico_web', [self.noticia_historica()]), \
                 patch.object(servidor, '_handler_texto_web', Mock()) as handler, \
                 patch.object(servidor.threading, 'Thread') as thread:
                ws = Mock()
                servidor._receber_texto_web(ws, {'texto': 'Pergunta', 'novidade': referencia})
                self.assertFalse(json.loads(ws.send.call_args.args[0])['ok'])
                thread.assert_not_called()
                handler.assert_not_called()

    def test_handler_entrega_referencia_ao_modelo_e_so_pergunta_na_tela(self):
        from modulos import execucoes, acompanhamentos, acompanhamento_sopro, conclusao_tarefas
        e = {'conversa': execucoes.conversa, '_interromper': Mock(), '_historico_conversa': [],
             'cor': Mock(), '_log': Mock(), 'atualizar_status': Mock(), 'registrar_interacao': Mock(),
             'marcar_luna_ocupada': Mock(), 'atualizar_usuario': Mock(), 'atualizar_estado_rosto': Mock(),
             'injetar_arquivo_pendente': lambda t: t, 'gerar_resposta': Mock(return_value='Resposta.'),
             'obter_clima_resposta': lambda: 'zoeira', 'atualizar_legenda': Mock(),
             '_mostrar_resposta_web_no_terminal': Mock(), 'atualizar_stream_resposta': Mock(),
             'atualizar_stream_interrompido': Mock(), 'GeracaoInterrompida': RuntimeError}
        extrair('main.py', {'responder_texto_web'}, e)
        noticia = self.noticia_historica()['cartoes_web'][0]
        referencias = []
        def gerar(*args, **kwargs):
            referencias.append(novidades_web.contexto_novidade.get())
            return 'Resposta.'
        e['gerar_resposta'].side_effect = gerar
        token = novidades_web.contexto_novidade.set(noticia)
        try:
            with patch.object(execucoes, 'controle', execucoes.Coordenador(pausa=0)), \
                 patch.object(acompanhamentos, 'interceptar_resposta', return_value=None), \
                 patch.object(acompanhamento_sopro, 'interceptar_pedido', return_value=None), \
                 patch.object(conclusao_tarefas, 'interceptar_resposta', return_value=None):
                e['responder_texto_web'](PERGUNTAS[1])
        finally:
            novidades_web.contexto_novidade.reset(token)
        e['atualizar_usuario'].assert_called_once_with(PERGUNTAS[1])
        pedido = e['gerar_resposta'].call_args.args[0]
        self.assertEqual(pedido, PERGUNTAS[1])
        self.assertEqual(referencias, [noticia])


class TestaContinuacaoNovidade(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pensar = preparar_runtime()

    def executar(self, pergunta, noticia, ferramenta=None, argumentos=None, retorno='Artigo de teste.', **opcoes):
        from contextlib import redirect_stdout
        import io
        p = self.pensar
        tool_calls = ([SimpleNamespace(function=SimpleNamespace(name=ferramenta,
                       arguments=json.dumps(argumentos or {})))] if ferramenta else None)
        resposta = SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(
            content='SEM_FERRAMENTA' if not ferramenta else '', tool_calls=tool_calls))],
            usage=SimpleNamespace(completion_tokens=7))
        historico = [{'role': 'user', 'content': 'Estou jogando outro jogo.'},
                     {'role': 'assistant', 'content': 'Vamos jogar.'}]
        consulta = Mock(return_value=retorno)
        token = novidades_web.contexto_novidade.set(noticia)
        try:
            with patch.object(p, '_chamar_llm', return_value=resposta) as roteador, \
                 patch.object(p, '_reescrever_como_luna', return_value='Resposta à pergunta.') as persona, \
                 patch.object(p, '_capturar_momento', return_value={'canal': 'web'}), \
                 patch.object(p, 'ATIVAR_MEMORIA_PERMANENTE', False), \
                 patch.object(p.obsidian, 'indice_notas', return_value=''), \
                 patch.dict(p.FUNCOES_DISPONIVEIS, {'resumir_site': consulta}), \
                 patch('modulos.metricas_ferramentas.registrar_uso'), redirect_stdout(io.StringIO()):
                saida = p.gerar_resposta(pergunta, historico, salvar=False,
                    responder_completo=opcoes.get('texto', True), presenca_pc=opcoes.get('no_pc', True))
        finally:
            novidades_web.contexto_novidade.reset(token)
        return saida, historico, roteador, persona, consulta

    def test_perguntas_reportadas_chegam_a_persona_sem_erro_de_acao(self):
        casos = [('O que acontece com quem já planejou a 5090?', 'NVIDIA pode mudar a linha RTX'),
                 ('Por que o GTA 6 não está ajudando nas vendas?', 'Vendas de hardware nos EUA')]
        for pergunta, titulo in casos:
            noticia = {'titulo': titulo, 'fonte': 'Feed', 'url': 'https://example.org/consultar',
                       'resumo': 'Texto de fonte com as palavras pesquisar e abrir.'}
            with self.subTest(pergunta=pergunta):
                saida, hist, roteador, persona, consulta = self.executar(pergunta, noticia)
                self.assertEqual(saida, 'Resposta à pergunta.')
                persona.assert_called_once()
                self.assertEqual(persona.call_args.args[1], pergunta)
                self.assertEqual(hist[-2]['content'], pergunta)
                msgs = roteador.call_args.kwargs['messages']
                self.assertEqual(len(msgs), 2)
                self.assertEqual(msgs[-1]['content'], pergunta)
                self.assertIn(titulo, msgs[0]['content'])
                self.assertEqual([t['function']['name'] for t in roteador.call_args.kwargs['tools']], ['resumir_site'])
                consulta.assert_not_called()

    def test_detalhes_leem_url_do_cartao_e_encaminham_artigo(self):
        noticia = {'titulo': 'Teste de OLED', 'url': 'https://example.org/oled', 'resumo': 'Teste prolongado.'}
        for args in ({}, {'url': 'https://example.org/outra-noticia'}):
            with self.subTest(args=args):
                saida, hist, roteador, persona, consulta = self.executar(
                    'Como fizeram esse teste?', noticia, 'resumir_site', args)
                consulta.assert_called_once_with(url=noticia['url'])
                self.assertEqual(persona.call_args.args[:2], ('Artigo de teste.', 'Como fizeram esse teste?'))
                self.assertTrue(persona.call_args.kwargs['tarefa_documento'])
                self.assertEqual(saida, 'Resposta à pergunta.')

    def test_falha_de_leitura_nao_e_apresentada_como_artigo_obtido(self):
        noticia = {'titulo': 'Teste OLED', 'url': 'https://example.org/oled'}
        _, _, _, persona, _ = self.executar('Como fizeram esse teste?', noticia, 'resumir_site',
                                            retorno='Erro: página indisponível.')
        self.assertEqual(persona.call_args.args[0], 'Erro: página indisponível.')
        self.assertIsNone(persona.call_args.kwargs.get('tarefa_documento'))

    def test_pedido_real_de_acao_sem_ferramenta_continua_protegido(self):
        for noticia in (None, {'titulo': 'Notícia', 'url': 'https://example.org/noticia'}):
            with self.subTest(noticia=noticia):
                saida, _, _, persona, consulta = self.executar('Pesquise os detalhes desta notícia.', noticia)
                self.assertIn('não consegui fazer isso agora', saida)
                persona.assert_not_called()
                consulta.assert_not_called()

    def test_rota_normal_voz_e_telegram_nao_recebem_contrato_de_noticia(self):
        for noticia, opcoes in ((None, {}), ({'titulo': 'Notícia antiga'}, {'texto': False}),
                                ({'titulo': 'Notícia antiga'}, {'no_pc': False})):
            with self.subTest(opcoes=opcoes):
                _, _, roteador, _, _ = self.executar('Gostei disso.', noticia, **opcoes)
                msgs = roteador.call_args.kwargs['messages']
                self.assertNotIn('O usuário clicou', msgs[0]['content'])
                self.assertIn('Estou jogando outro jogo.', msgs[1]['content'])

    def test_ferramenta_fora_da_leitura_nao_executa_em_clique_de_noticia(self):
        with patch.dict(self.pensar.FUNCOES_DISPONIVEIS, {'propor_acompanhamento': Mock()}) as funcoes:
            _, _, _, persona, consulta = self.executar('O que muda?',
                {'titulo': 'Notícia', 'url': 'https://example.org/noticia'}, 'propor_acompanhamento')
            funcoes['propor_acompanhamento'].assert_not_called()
            consulta.assert_not_called()
            persona.assert_called_once()


if __name__ == '__main__':
    unittest.main()
