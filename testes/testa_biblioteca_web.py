"""Arquivo persistente, referências confiáveis e consulta HTTP sem iniciar a Luna."""
import json
from contextlib import closing
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import Mock, patch

from modulos import biblioteca_web as b, novidades_web, obsidian
import servidor


class TestaBibliotecaWeb(unittest.TestCase):
    def setUp(self):
        self.pasta = tempfile.TemporaryDirectory()
        self.addCleanup(self.pasta.cleanup)
        self.arquivo = patch.object(b, 'ARQUIVO', Path(self.pasta.name) / 'biblioteca.json')
        self.arquivo.start()
        self.addCleanup(self.arquivo.stop)
        for nome, destino in [('LOG_ANTIGO', 'luna.log'), ('BANCO_ANTIGO', 'chroma.sqlite3'),
                              ('BACKUPS_ANTIGOS', 'backups')]:
            substituto = patch.object(b, nome, Path(self.pasta.name) / destino)
            substituto.start()
            self.addCleanup(substituto.stop)
        self.client = servidor.app.test_client()

    def noticia(self, indice=1):
        return ('Título ' + str(indice), f'https://example.org/{indice}', 'Fonte', 'Extração e memória', 'https://example.org/capa.jpg')

    def test_registra_todo_lote_e_busca_sem_acentos(self):
        b.registrar_itens([self.noticia(i) for i in range(35)], 'noticia')
        primeira = b.consultar(busca='EXTRACAO memoria')
        self.assertEqual(primeira['total'], 35)
        self.assertEqual(len(primeira['itens']), 30)
        self.assertTrue(primeira['mais'])
        self.assertEqual(len(b.consultar(inicio=30)['itens']), 5)
        self.assertEqual(b.consultar(busca='inexistente')['total'], 0)

    def test_leitura_persiste_sem_reabrir_item_duplicado(self):
        b.registrar_itens([self.noticia()], 'noticia')
        item = b.consultar()['itens'][0]
        self.assertTrue(b.marcar_leitura(item['id'], True))
        b.registrar_itens([self.noticia()], 'noticia')
        self.assertEqual(b.consultar()['nao_lidas'], 0)
        self.assertEqual(b.consultar(leitura='nao_lidas')['total'], 0)
        self.assertEqual(b.consultar(leitura='lidas')['total'], 1)
        self.assertFalse(b.marcar_leitura(item['id'], 'true'))

    def test_notas_atuais_importam_capa_fonte_resumo_e_imagem_local(self):
        raiz = Path(self.pasta.name)
        (raiz / 'Novidades.md').write_text('## 10/10/2026\n\n' + obsidian._cartao_novidade(self.noticia()), encoding='utf-8')
        (raiz / 'Promocoes.md').write_text('## 10/10/2026\n\n' + obsidian._cartao_novidade(
            ('Oferta', 'https://t.me/canal/1', '@canal', 'Descrição', 'canal_1.jpg')), encoding='utf-8')
        b.importar_notas(str(raiz))
        itens = b.consultar()['itens']
        self.assertEqual(len(itens), 2)
        noticia = next(i for i in itens if i['tipo'] == 'noticia')
        self.assertEqual(noticia['imagem'], self.noticia()[4])
        self.assertEqual(noticia['fonte'], 'Fonte')
        self.assertIn('Extração', noticia['resumo'])
        self.assertEqual(b.consultar(tipo='promocao')['itens'][0]['imagem'], '/imagens/promocoes/canal_1.jpg')
        b.importar_notas(str(raiz))
        self.assertEqual(b.consultar()['total'], 2)

    def test_noticias_funcionam_sem_obsidian_configurado(self):
        with patch.object(obsidian, '_VAULT', ''):
            obsidian.adicionar_novidades([self.noticia()])
            obsidian.adicionar_promocoes([('Oferta', 'https://t.me/canal/1', '@canal')])
        self.assertEqual(b.consultar()['total'], 2)

    def test_conversa_persiste_apos_sair_da_sessao(self):
        with patch.object(b, 'MAX_TURNOS', 2):
            for i in range(3):
                b.registrar_turno({'id': str(i), 'usuario': 'Qual memória?', 'luna': 'Resposta ' + str(i)})
        self.assertEqual(b.consultar(modo='historico')['total'], 2)
        self.assertIsNone(b.resolver_resposta({'turno_id': '0'}, []))
        contexto, noticia = b.resolver_resposta({'turno_id': '1'}, [])
        self.assertEqual(contexto['luna'], 'Resposta 1')
        self.assertIsNone(noticia)

    def test_busca_http_recupera_conversa_anterior_a_sessao(self):
        b.LOG_ANTIGO.write_text(
            '2026-08-22 10:00:00 [INFO] luna.main: [Web texto] Usuário: Por que o servidor não abre?\n'
            '2026-08-22 10:00:10 [INFO] luna.pensar: Luna: Não ligar esta cópia ao usuário.\n'
            '2026-08-22 10:00:11 [INFO] luna.main: [Web texto] Luna: O CGNAT estava impedindo o acesso.\n', encoding='utf-8')
        with patch.object(servidor, '_historico_web', []):
            resposta = self.client.get('/api/historico?busca=CGNAT')
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(resposta.json['total'], 1)
        turno = resposta.json['itens'][0]
        self.assertEqual(turno['data'], '2026-08-22T10:00:11')
        self.assertEqual(turno['usuario'], 'Por que o servidor não abre?')
        self.assertTrue(turno['incompleto'])
        contexto, _ = b.resolver_resposta({'turno_id': turno['id']}, [])
        self.assertTrue(contexto['trecho_incompleto'])
        b.importar_conversas()
        self.assertEqual(b.consultar(modo='historico')['total'], 1)

    def test_log_nao_liga_canais_reinicios_ou_respostas_sem_pergunta(self):
        b.LOG_ANTIGO.write_text(
            '2026-08-22 10:00:00 [INFO] luna.main: [Web texto] Usuário: Pergunta abandonada\n'
            '2026-08-22 10:00:10 [INFO] luna.main: [PC] Luna: Outro canal\n'
            '2026-08-22 10:00:20 [INFO] luna.main: Luna iniciando...\n'
            '2026-08-22 10:00:30 [INFO] luna.main: [Web texto] Luna: Depois do reinício\n'
            '2026-08-22 10:00:31 [INFO] luna.main: [PC] Usuário: Uma pergunta por voz\n'
            '2026-08-22 10:00:40 [INFO] luna.main: [PC] Luna: Resposta por voz\n', encoding='utf-8')
        b.importar_conversas()
        turnos = b.consultar(modo='historico')['itens']
        self.assertEqual(len(turnos), 1)
        self.assertEqual(turnos[0]['usuario'], 'Uma pergunta por voz')

    def test_backup_completo_prevalece_sobre_trecho_do_log(self):
        b.BACKUPS_ANTIGOS.mkdir()
        resposta = 'Uma resposta longa que já foi gravada integralmente e não deve perder nenhum detalhe. ' * 4
        (b.BACKUPS_ANTIGOS / 'historico-luna-teste.json').write_text(json.dumps({
            'documents': ['Usuário: Pergunta antiga\nLuna: ' + resposta],
            'metadatas': [{'data': '22/08/2026 10:00'}]}), encoding='utf-8')
        b.LOG_ANTIGO.write_text(
            '2026-08-22 09:59:58 [INFO] luna.main: [Web texto] Usuário: Pergunta antiga\n'
            '2026-08-22 10:00:01 [INFO] luna.main: [Web texto] Luna: ' + resposta[:200] + '\n', encoding='utf-8')
        b.importar_conversas()
        turnos = b.consultar(modo='historico')['itens']
        self.assertEqual(len(turnos), 1)
        self.assertFalse(turnos[0]['incompleto'])
        self.assertEqual(turnos[0]['luna'], resposta)

    def test_importacao_preserva_id_da_web_resposta_completa_e_ordem(self):
        resposta = 'Uma resposta extensa que permanece inteira na web e conserva o ID usado pelo botão de responder. ' * 3
        b.registrar_turno({'id': 'atual', 'usuario': 'Pergunta', 'luna': resposta, 'data': '2026-10-11T10:00:00'})
        b.LOG_ANTIGO.write_text(
            '2026-08-22 10:00:00 [INFO] luna.main: [Web texto] Usuário: Antiga\n'
            '2026-08-22 10:00:10 [INFO] luna.main: [Web texto] Luna: Uma resposta antiga\n'
            '2026-10-11 09:59:58 [INFO] luna.main: [Web texto] Usuário: Pergunta\n'
            '2026-10-11 10:00:00 [INFO] luna.main: [Web texto] Luna: ' + resposta[:200] + '\n', encoding='utf-8')
        b.importar_conversas()
        turnos = b.consultar(modo='historico')['itens']
        self.assertEqual(len(turnos), 2)
        self.assertEqual(turnos[0]['id'], 'atual')
        self.assertEqual(turnos[0]['luna'], resposta)
        b.registrar_turno({'id': 'depois', 'luna': 'Uma conversa depois de reiniciar.'})
        b.importar_conversas()
        self.assertEqual(b.consultar(modo='historico')['total'], 3)

    def test_banco_textual_recupera_sem_escrever_ou_carregar_embeddings(self):
        with closing(sqlite3.connect(b.BANCO_ANTIGO)) as db:
            db.executescript('''
                CREATE TABLE collections (id TEXT, name TEXT);
                CREATE TABLE segments (id TEXT, collection TEXT, scope TEXT);
                CREATE TABLE embeddings (id INTEGER, segment_id TEXT, embedding_id TEXT);
                CREATE TABLE embedding_metadata (id INTEGER, key TEXT, string_value TEXT, int_value INTEGER, float_value REAL);
                INSERT INTO collections VALUES ('c', 'historico_luna_embeddinggemma2_768_v1');
                INSERT INTO collections VALUES ('outra', 'memoria_permanente');
                INSERT INTO segments VALUES ('s', 'c', 'METADATA');
                INSERT INTO segments VALUES ('externa', 'outra', 'METADATA');
                INSERT INTO embeddings VALUES (1, 's', 'antiga');
                INSERT INTO embeddings VALUES (2, 'externa', 'fato');
                INSERT INTO embedding_metadata VALUES (1, 'chroma:document', 'Usuário: Servidor?\nLuna: Resposta completa do banco.', NULL, NULL);
                INSERT INTO embedding_metadata VALUES (1, 'data', '22/08/2026 10:00', NULL, NULL);
                INSERT INTO embedding_metadata VALUES (2, 'chroma:document', 'Usuário: Outro\nLuna: Não importar esta coleção.', NULL, NULL);
                INSERT INTO embedding_metadata VALUES (2, 'data', '22/08/2026 10:00', NULL, NULL);
            ''')
        antes = b.BANCO_ANTIGO.read_bytes()
        b.importar_conversas()
        turnos = b.consultar(modo='historico')['itens']
        self.assertEqual(len(turnos), 1)
        self.assertEqual(turnos[0]['luna'], 'Resposta completa do banco.')
        self.assertFalse(turnos[0]['incompleto'])
        self.assertEqual(b.BANCO_ANTIGO.read_bytes(), antes)

    def test_historico_antigo_respeita_retencao_sem_apagar_turno_recente(self):
        b.registrar_turno({'id': 'novo', 'luna': 'Resposta atual', 'data': '2026-10-11T10:00:00'})
        b.LOG_ANTIGO.write_text(''.join(
            f'2026-08-22 10:00:{i:02d} [INFO] luna.main: [Web texto] Usuário: Pergunta {i}\n'
            f'2026-08-22 10:00:{i+1:02d} [INFO] luna.main: [Web texto] Luna: Resposta {i}\n'
            for i in range(3)), encoding='utf-8')
        with patch.object(b, 'MAX_TURNOS', 2):
            b.importar_conversas()
        self.assertEqual([t['usuario'] for t in b.consultar(modo='historico')['itens']], ['', 'Pergunta 2'])

    def test_referencia_nao_aceita_texto_ou_url_do_navegador(self):
        recente = {'id': 'a', 'usuario': 'Oi', 'luna': 'Fala real'}
        for ref in [None, {}, {'turno_id': 'a', 'luna': 'Forjada'}, {'turno_id': 'a', 'item_id': 'b'}, {'turno_id': 1}]:
            self.assertIsNone(b.resolver_resposta(ref, [recente]))
        self.assertEqual(b.resolver_resposta({'turno_id': 'a'}, [recente])[0]['luna'], 'Fala real')

    def test_wishlist_inclui_todas_as_ofertas_mesmo_sem_cartoes(self):
        b.registrar_turno({'id': 'steam', 'usuario': '', 'luna': 'Há ofertas na sua lista.',
            'origem_proativa': 'steam_wishlist', 'links_novidades': {'ofertas': [
                {'url': f'https://store.steampowered.com/app/{i}/', 'rotulo': f'Jogo {i} — 50%'} for i in range(5)]}})
        ofertas = b.consultar(tipo='promocao')['itens']
        self.assertEqual(len(ofertas), 5)
        self.assertTrue(all(i['fonte'] == 'Steam' for i in ofertas))

    def test_responder_item_recupera_a_fonte_correta(self):
        b.registrar_itens([self.noticia()], 'noticia')
        item = b.consultar()['itens'][0]
        contexto, noticia = b.resolver_resposta({'item_id': item['id']}, [])
        self.assertEqual(noticia['url'], self.noticia()[1])
        self.assertEqual(contexto['referencia'], {'item_id': item['id']})

    def test_http_filtros_e_marcar_leitura(self):
        b.registrar_itens([self.noticia()], 'noticia')
        with patch.object(obsidian, '_VAULT', ''):
            r = self.client.get('/api/biblioteca?busca=memoria&tipo=noticia')
        self.assertEqual(r.status_code, 200)
        identificador = r.json['itens'][0]['id']
        self.assertEqual(self.client.post(f'/api/biblioteca/{identificador}/leitura', json={'lido': True}).status_code, 200)
        self.assertEqual(self.client.post(f'/api/biblioteca/{identificador}/leitura', json=[]).status_code, 400)
        self.assertEqual(self.client.post('/api/biblioteca/inexistente/leitura', json={'lido': False}).status_code, 404)
        self.assertEqual(self.client.get('/api/historico?inicio=abc').status_code, 400)

    def test_arquivo_completo_nunca_e_enviado_com_a_pergunta(self):
        b.registrar_turno({'id': 'a', 'usuario': 'como?', 'luna': 'Resposta escolhida'})
        recebidos = []
        def handler(texto):
            recebidos.append((texto, b.contexto_resposta.get(), novidades_web.contexto_novidade.get()))
        ws = Mock()
        with patch.object(servidor, '_handler_texto_web', handler), patch.object(servidor, '_broadcast'), \
             patch.object(servidor, '_historico_web', []), patch.object(servidor, '_textos_web', {}), \
             patch.object(servidor.threading, 'Thread') as thread:
            servidor._receber_texto_web(ws, {'texto': 'o que isso significa?', 'resposta_a': {'turno_id': 'a'}, 'request_id': 'x'})
            thread.call_args.kwargs['target']()
            self.assertTrue(json.loads(ws.send.call_args.args[0])['ok'])
        self.assertEqual(recebidos[0][0], 'o que isso significa?')
        self.assertEqual(recebidos[0][1]['luna'], 'Resposta escolhida')
        self.assertIsNone(b.contexto_resposta.get())

    def test_referencia_expirada_nao_aceita_envio(self):
        with patch.object(servidor, '_handler_texto_web', Mock()), patch.object(servidor, '_historico_web', []), \
             patch.object(servidor.threading, 'Thread') as thread:
            ws = Mock()
            servidor._receber_texto_web(ws, {'texto': 'pergunta', 'resposta_a': {'turno_id': 'inexistente'}})
        thread.assert_not_called()
        self.assertFalse(json.loads(ws.send.call_args.args[0])['ok'])

    def test_cada_mensagem_na_fila_guarda_sua_propria_referencia(self):
        recebidos = []
        def handler(texto):
            recebidos.append((texto, b.contexto_resposta.get()['luna']))
        recentes = [{'id': 'a', 'luna': 'Primeira'}, {'id': 'b', 'luna': 'Segunda'}]
        with patch.object(servidor, '_handler_texto_web', handler), patch.object(servidor, '_broadcast'), \
             patch.object(servidor, '_historico_web', recentes), patch.object(servidor, '_textos_web', {}), \
             patch.object(servidor.threading, 'Thread') as thread:
            servidor._receber_texto_web(Mock(), {'texto': 'um', 'resposta_a': {'turno_id': 'a'}})
            primeiro = thread.call_args.kwargs['target']
            servidor._receber_texto_web(Mock(), {'texto': 'dois', 'resposta_a': {'turno_id': 'b'}})
            segundo = thread.call_args.kwargs['target']
            segundo(); primeiro()
        self.assertEqual(recebidos, [('dois', 'Segunda'), ('um', 'Primeira')])
        self.assertIsNone(b.contexto_resposta.get())

    def test_roteador_recebe_so_referencia_escolhida_e_pergunta_atual(self):
        from testes.bancada_dark_souls_thinking import preparar_runtime
        from testes.testa_sugestoes_novidades import TestaContinuacaoNovidade
        teste = TestaContinuacaoNovidade()
        teste.pensar = preparar_runtime()
        token = b.contexto_resposta.set({'referencia': {'turno_id': 'rede'}, 'usuario': 'Não consigo abrir portas.',
            'luna': 'O CGNAT do provedor impede a abertura de portas.', 'cartoes': []})
        try:
            saida, _, roteador, persona, consulta = teste.executar('Isso ainda impediria o acesso externo?', None)
        finally:
            b.contexto_resposta.reset(token)
        mensagens = roteador.call_args.kwargs['messages']
        self.assertEqual(len(mensagens), 2)
        self.assertIn('CGNAT', mensagens[0]['content'])
        self.assertNotIn('Estou jogando outro jogo.', str(mensagens))
        self.assertEqual(mensagens[-1]['content'], 'Isso ainda impediria o acesso externo?')
        self.assertEqual(persona.call_args.args[1], 'Isso ainda impediria o acesso externo?')
        self.assertEqual(saida, 'Resposta à pergunta.')
        consulta.assert_not_called()


if __name__ == '__main__':
    unittest.main()
