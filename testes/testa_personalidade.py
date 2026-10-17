"""Seleção entre turnos, persistência e separação de contexto sem modelo ou áudio."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import Mock, patch

import servidor
from modulos import execucoes, prompts
from testes.bancada_personalidades import FIXTURE, montagens
from testes.bancada_dark_souls_thinking import preparar_runtime
from testes.testa_prompt_montagem import _Resposta


class TestaPersonalidade(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.p = preparar_runtime()

    def setUp(self):
        self.anterior = prompts.personalidade_ativa()
        self.addCleanup(prompts.selecionar_personalidade, self.anterior)
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.config = Path(self.tmp.name) / 'config.json'
        self.envios = []
        self.configuracao_aplicada = threading.Event()
        def registrar_envio(dados):
            self.envios.append(deepcopy(dados))
            if dados.get('tipo') == 'config_estado' and not dados['estado']['personalidade_pendente']:
                self.configuracao_aplicada.set()
        self.c = execucoes.Coordenador(pausa=0)
        mudancas = [
            patch.object(execucoes, 'controle', self.c),
            patch.object(self.p, '_historicos_personalidade', []),
            patch.object(servidor, '_CAMINHO_CONFIG', str(self.config)),
            patch.object(servidor, '_estado_config', deepcopy(servidor._estado_config)),
            patch.object(servidor, '_config_handlers', {'personalidade': self.p.configurar_personalidade}),
            patch.object(servidor, '_trava_personalidade', threading.Lock()),
            patch.object(servidor, '_personalidade_pendente', False),
            patch.object(servidor, '_personalidade_erro', ''),
            patch.object(servidor, '_broadcast', side_effect=registrar_envio),
        ]
        for m in mudancas:
            m.start()
            self.addCleanup(m.stop)
        prompts.selecionar_personalidade(2)
        servidor._estado_config['personalidade'] = 2

    def test_montagens_dos_quatro_perfis(self):
        fixture = json.loads(FIXTURE.read_text(encoding='utf8'))
        for nivel in range(4):
            with self.subTest(nivel=nivel):
                prompts.selecionar_personalidade(nivel)
                self.assertEqual(montagens(self.p), fixture['perfis'][str(nivel)])

    def test_valor_invalido_nao_muda_aliases_nem_historico(self):
        hist = [{'role': 'assistant', 'content': 'Histórico preservado'}]
        self.p.registrar_historico_personalidade(hist)
        for valor in (None, True, False, -1, 4, 1.0, '', 'glados', [], {}):
            with self.subTest(valor=valor):
                with self.assertRaises(ValueError):
                    self.p.configurar_personalidade(valor)
                self.assertEqual(prompts.personalidade_ativa(), 2)
                self.assertEqual(len(hist), 1)

    def test_nome_luna_em_todos_os_perfis_e_canais(self):
        for nivel in range(4):
            prompts.selecionar_personalidade(nivel)
            for voz in (False, True):
                with self.subTest(nivel=nivel, voz=voz):
                    self.assertIn('Você é Luna', prompts.persona())
                    self.assertIn('Você é Luna', prompts.nucleo_enxuto(prompts.ENXUTO_SAUDACAO, voz))
                    self.assertIn('Luna', prompts.INTRO_PERFIL)
                    self.assertNotIn('Você é GLaDOS', prompts.persona())
                    self.assertEqual(prompts.sortear_exemplos_tom('oi'), [])
        prompts.selecionar_personalidade(1)
        self.assertEqual(prompts.nome_personalidade(), 'HAL 9000')
        self.assertNotIn('amiga calorosa', prompts.nucleo_enxuto(prompts.ENXUTO_COTIDIANO, False))

    def test_selecao_isola_os_textos_e_atualiza_confirmacao(self):
        for nivel, marco in [(1, 'HAL 9000'), (2, 'TARS'), (3, 'GLaDOS'), (0, '')]:
            prompts.selecionar_personalidade(nivel)
            captura = []
            def chamar(**kw):
                captura.append(kw)
                return _Resposta()
            with patch.object(self.p, '_chamar_llm', side_effect=chamar):
                self.p.frase_confirmacao('Confirme somente o resultado fornecido.')
            sistema = captura[0]['messages'][0]['content']
            self.assertEqual(sistema, prompts.persona())
            if marco:
                self.assertIn(marco, sistema)
            for outro in ('HAL 9000', 'TARS', 'GLaDOS'):
                if outro != marco:
                    self.assertNotIn(outro, sistema)
            self.assertEqual(prompts.CANAL_WEB, prompts.CANAL_TEXTO + prompts.APRESENTACAO_WEB)
            if nivel != 1:
                self.assertEqual(prompts.sortear_exemplos_tom('ola'), [])
                self.assertEqual(prompts.bloco_exemplos_tom(prompts.EXEMPLOS_TOM[:3]), '')

    def test_troca_limpa_so_listas_registradas_sem_acesso_a_memoria(self):
        chat, telegram, proativo, recentes = [[{'content': 'Tom anterior'}] for _ in range(4)]
        for hist in (chat, telegram, proativo, recentes, chat):
            self.p.registrar_historico_personalidade(hist)
        self.assertEqual(len(self.p._historicos_personalidade), 4)
        visivel = [{'luna': 'Tom anterior'}]
        memoria = Path(self.tmp.name) / 'memoria.txt'
        memoria.write_text('Lembrança permanente', encoding='utf8')
        with patch.object(servidor, '_historico_web', visivel), \
             patch.object(self.p, 'salvar_conversa') as salvar:
            self.p.configurar_personalidade(3)
            salvar.assert_not_called()
            self.assertEqual(servidor._historico_web, [{'luna': 'Tom anterior'}])
        self.assertTrue(all(not h for h in (chat, telegram, proativo, recentes)))
        self.assertEqual(memoria.read_text(encoding='utf8'), 'Lembrança permanente')

    def test_mesmo_perfil_nao_limpa_conversa(self):
        hist = ['Tom atual']
        self.p.registrar_historico_personalidade(hist)
        self.p.configurar_personalidade(2)
        self.assertEqual(hist, ['Tom atual'])
        with patch.object(servidor.threading, 'Thread') as thread:
            servidor._aplicar_config({'config': 'personalidade', 'valor': 2})
            thread.assert_not_called()

    def test_web_salva_zero_e_reaplica_no_inicio(self):
        with patch.object(servidor.threading, 'Thread') as thread:
            servidor._aplicar_config({'config': 'personalidade', 'valor': 0})
            self.assertTrue(self.envios[-1]['estado']['personalidade_pendente'])
            self.assertEqual(self.envios[-1]['estado']['personalidade'], 2)
            thread.call_args.kwargs['target']()
        self.assertEqual(json.loads(self.config.read_text(encoding='utf8'))['personalidade'], 0)
        self.assertEqual(prompts.personalidade_ativa(), 0)
        self.assertFalse(self.envios[-1]['estado']['personalidade_pendente'])
        prompts.selecionar_personalidade(2)
        servidor._estado_config['personalidade'] = 2
        servidor.carregar_e_aplicar_config()
        self.assertEqual(prompts.personalidade_ativa(), 0)

    def test_config_antiga_e_invalida_mantem_tars(self):
        for salvo in ({'voz': 'jf_alpha'}, {'personalidade': 99}, {'personalidade': True}):
            self.config.write_text(json.dumps(salvo), encoding='utf8')
            servidor._estado_config['personalidade'] = 2
            servidor.carregar_e_aplicar_config()
            self.assertEqual(prompts.personalidade_ativa(), 2)
            self.assertEqual(servidor._estado_config['personalidade'], 2)

    def test_web_rejeita_invalido_e_erro_sem_salvar_sucesso(self):
        with patch.object(servidor.threading, 'Thread') as thread:
            servidor._aplicar_config({'config': 'personalidade', 'valor': 'qualquer'})
            thread.assert_not_called()
        self.assertFalse(self.config.exists())
        def falhar(nivel):
            raise RuntimeError('Falha simulada')
        servidor._config_handlers['personalidade'] = falhar
        with patch.object(servidor.threading, 'Thread') as thread, patch.object(servidor._log, 'exception'):
            servidor._aplicar_config({'config': 'personalidade', 'valor': 3})
            thread.call_args.kwargs['target']()
        self.assertEqual(servidor._estado_config['personalidade'], 2)
        self.assertFalse(self.config.exists())
        self.assertFalse(self.envios[-1]['estado']['personalidade_pendente'])
        self.assertTrue(self.envios[-1]['estado']['personalidade_erro'])

    def test_troca_espera_turno_e_precede_mensagem_seguinte(self):
        entrou, liberar, terminou, nova_pronta = [threading.Event() for _ in range(4)]
        hist, observado = [], []
        self.p.registrar_historico_personalidade(hist)
        def resposta_antiga():
            with self.c.executar():
                entrou.set()
                liberar.wait(3)
                hist.append('Resposta do perfil antigo')
            terminou.set()
        antiga = threading.Thread(target=resposta_antiga, daemon=True)
        antiga.start()
        try:
            self.assertTrue(entrou.wait(2))
            servidor._aplicar_config({'config': 'personalidade', 'valor': 3})
            self.assertTrue(servidor._personalidade_pendente)
            self.assertEqual(prompts.personalidade_ativa(), 2)
            turno = self.c.reservar()
            def mensagem_nova():
                with self.c.executar(turno):
                    observado.append((prompts.personalidade_ativa(), list(hist)))
                    hist.append('Resposta do perfil novo')
                nova_pronta.set()
            nova = threading.Thread(target=mensagem_nova, daemon=True)
            nova.start()
            # Uma segunda troca pendente não pode ocupar mais um lugar na fila.
            servidor._aplicar_config({'config': 'personalidade', 'valor': 1})
            self.assertEqual(len(self.c.fila), 2)
            liberar.set()
            self.assertTrue(terminou.wait(2))
            self.assertTrue(nova_pronta.wait(2))
            nova.join(2)
            self.assertEqual(observado, [(3, [])])
            self.assertEqual(hist, ['Resposta do perfil novo'])
        finally:
            liberar.set()
            antiga.join(2)
            self.assertTrue(self.configuracao_aplicada.wait(3), 'O worker não terminou a persistência da troca.')
            # O worker deve terminar antes de devolver os módulos reais aos outros testes.
            self.c.condicao.acquire()
            try:
                self.c.condicao.wait_for(lambda: not self.c.atual and not self.c.fila, timeout=2)
            finally:
                self.c.condicao.release()


if __name__ == '__main__':
    unittest.main()
