"""O cartão é um rascunho; chamadas, gravação definitiva e reenvio têm donos distintos."""
from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from modulos import fontes_conversa as chat, acompanhamento_fontes as monitor, cartoes_web
from testes.bancada_dark_souls_thinking import preparar_runtime
from testes.testa_prompt_montagem import _Resposta

PEDIDO = 'Acompanhe o TTS de teste e me avise quando tiver suporte a português brasileiro: https://example.org/releases.atom'


class TestaFontesConversa(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pensar = preparar_runtime()

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        for p in (patch.object(chat, 'CAMINHO', Path(tmp.name) / 'rascunhos.json'),
                  patch.object(monitor, 'CAMINHO', Path(tmp.name) / 'fontes.json'),
                  patch.object(monitor, 'agendar_verificacao'), patch.object(monitor, '_notificar')):
            p.start(); self.addCleanup(p.stop)

    def propor(self, interesse='quando tiver suporte a português brasileiro'):
        return chat.propor(PEDIDO, 'TTS de teste', interesse)

    def test_rascunho_nao_consulta_nem_cadastra_antes_de_confirmar(self):
        resultado = self.propor()
        self.assertEqual(monitor.estado_interface()['itens'], [])
        monitor.agendar_verificacao.assert_not_called()
        card = resultado.cartoes_web[0]
        self.assertEqual(card['fontes'], ['https://example.org/releases.atom'])
        self.assertEqual(str(resultado).count('https'), 0)
        resposta = chat.resolver('confirmar', card['id'], chat.estado_interface()['itens'][0]['cadastro'])
        self.assertTrue(resposta['ok'])
        self.assertEqual(len(monitor.estado_interface()['itens']), 1)
        monitor.agendar_verificacao.assert_called_once()

    def test_reenvio_e_queda_entre_as_duas_gravacoes_nao_duplicam(self):
        card = self.propor().cartoes_web[0]
        cadastro = chat.estado_interface()['itens'][0]['cadastro']
        with patch.object(chat, '_salvar', side_effect=OSError('queda')):
            self.assertFalse(chat.resolver('confirmar', card['id'], cadastro)['ok'])
        self.assertTrue(chat.resolver('confirmar', card['id'], cadastro)['ok'])
        self.assertTrue(chat.resolver('confirmar', card['id'], cadastro)['ok'])
        self.assertEqual(len(monitor.estado_interface()['itens']), 1)
        monitor.agendar_verificacao.assert_called_once()

    def test_edicao_erro_descarte_e_validade(self):
        card = self.propor('').cartoes_web[0]
        self.assertEqual(card['interesse'], '')
        cadastro = chat.estado_interface()['itens'][0]['cadastro']
        self.assertFalse(chat.resolver('confirmar', card['id'], cadastro)['ok'])
        cadastro.update(interesse='Melhorar o desempenho em CPU', fontes=['http://127.0.0.1/privado'])
        self.assertFalse(chat.resolver('confirmar', card['id'], cadastro)['ok'])
        self.assertTrue(chat.resolver('descartar', card['id'])['ok'])
        self.assertFalse(chat.resolver('confirmar', card['id'], cadastro)['ok'])
        novo = self.propor().cartoes_web[0]
        with patch.object(chat.time, 'time', return_value=1e12):
            self.assertFalse(chat.resolver('confirmar', novo['id'], cadastro)['ok'])
        self.assertEqual(monitor.estado_interface()['itens'], [])

    def test_pedido_literal_nao_e_citado_historico_opiniao_ou_negacao(self):
        for texto in ['O site acompanha as releases: https://example.org/',
                      'Não acompanhe o TTS: https://example.org/',
                      'Gostei de https://example.org/', 'Acompanhe suporte brasileiro',
                      'Me avisa o que esse site diz agora: https://example.org/',
                      'Acompanhe https://localhost/']:
            with self.subTest(texto=texto):
                self.assertFalse(chat.eh_pedido(texto))
        for texto in [PEDIDO, 'Luna, poderia acompanhar esse projeto? https://example.org/',
                      'Me avisa quando tiver novidade: https://example.org/']:
            self.assertTrue(chat.eh_pedido(texto))

    def test_rascunho_repetido_e_monitor_existente_sao_reusados(self):
        primeiro, segundo = self.propor(), self.propor()
        self.assertEqual(primeiro.cartoes_web[0]['id'], segundo.cartoes_web[0]['id'])
        item = chat.estado_interface()['itens'][0]
        chat.resolver('confirmar', item['id'], item['cadastro'])
        self.assertEqual(self.propor().cartoes_web[0]['tipo'], 'acompanhamento')

    def test_modelo_nao_completa_interesse_ausente_e_arquivo_invalido_e_preservado(self):
        r = chat.propor('Acompanhe esse projeto: https://example.org/releases.atom', 'Projeto',
                        'Acompanhar mudanças nas fontes públicas do projeto.')
        self.assertEqual(r.cartoes_web[0]['interesse'], '')
        self.assertIn('Falta a mudança', str(r))
        chat.CAMINHO.write_text('[{"id":"bad","status":{}}]', encoding='utf8')
        self.assertIn('erro', chat.estado_interface())
        self.assertEqual(chat.CAMINHO.read_text(encoding='utf8'), '[{"id":"bad","status":{}}]')

    def test_roteador_so_recebe_schema_neste_pedido_e_ignora_urls_inventadas(self):
        p = self.pensar
        r = _Resposta()
        r.choices[0].message.tool_calls = [SimpleNamespace(function=SimpleNamespace(
            name='preparar_acompanhamento_fontes', arguments=json.dumps({'assunto': 'TTS',
                'interesse': 'Suporte brasileiro', 'fontes': ['https://inventado.org/']})))]
        for texto, pc, completo, esperado in [(PEDIDO, True, True, True),
                ('Gostei de https://example.org/', True, True, False), (PEDIDO, False, True, False),
                (PEDIDO, True, False, False)]:
            with self.subTest(pc=pc, completo=completo, texto=texto), redirect_stdout(io.StringIO()), \
                 patch.object(p, '_capturar_momento', return_value={'canal':'web' if pc else 'telegram'}), \
                 patch.object(p, 'ATIVAR_MEMORIA_PERMANENTE', False), \
                 patch.object(p.obsidian, 'indice_notas', return_value=''), \
                 patch.object(p, '_chamar_llm', return_value=r) as chamar, \
                 patch.object(p, '_reescrever_como_luna', return_value='Confira o cartão.'), \
                 patch('modulos.metricas_ferramentas.registrar_uso'):
                resultado = p.gerar_resposta(texto, [], salvar=False, responder_completo=completo, presenca_pc=pc)
                schema = chamar.call_args.kwargs['tools']
                self.assertEqual(any(t['function']['name'] == 'preparar_acompanhamento_fontes' for t in schema), esperado)
                self.assertEqual(hasattr(resultado, 'cartoes_web'), esperado)
                if esperado:
                    self.assertEqual(resultado.cartoes_web[0]['fontes'], ['https://example.org/releases.atom'])

    def test_metadata_publica_rejeita_fontes_invalidas_e_nao_execucao_html(self):
        card = self.propor().cartoes_web[0]
        self.assertEqual(cartoes_web.normalizar([{**card, 'fontes': ['javascript:alert(1)']}]), [])
        self.assertEqual(cartoes_web.normalizar([{**card, 'id': 'outro-id'}]), [])

    def test_sopro_ptbr_existente_nao_ganha_um_segundo_monitor(self):
        from modulos import acompanhamento_sopro as sopro
        with patch.object(sopro, 'estado_interface', return_value={'status':'ativo', 'situacao':'Aguardando PT-BR'}):
            r = chat.propor('Acompanhe o Sopro quando tiver PT-BR: https://github.com/samuel-vitorino/sopro',
                           'Sopro', 'quando tiver PT-BR')
        self.assertEqual(r.cartoes_web[0]['origem'], 'sopro')
        self.assertFalse(chat.CAMINHO.exists())
        monitor.agendar_verificacao.assert_not_called()


if __name__ == '__main__':
    unittest.main()
