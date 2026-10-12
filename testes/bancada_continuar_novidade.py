"""Exercita o clique de notícia no Gemma: roteador e persona reais, leitura de artigo simulada."""
from contextlib import redirect_stdout
from copy import deepcopy
import io
import time
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from modulos import novidades_web, tom
from testes.bancada_dark_souls_thinking import preparar_runtime, FalhaBancada
from testes.bancada_fontes_conversa import preparar
from testes.bancada_modelos import identidade, conferir_identidade, chamar, gravar_json
from testes.testa_prompt_montagem import _Resposta

PASTA = Path('logs/bancada_web/20261010-continuar-novidade')
CASOS = [
    {'id': '5090', 'pergunta': 'O que acontece com quem já planejou a 5090?',
     'noticia': {'titulo': 'NVIDIA pode descontinuar RTX 5090 para reservar GPUs para a linha PRO',
                 'fonte': 'Fonte de teste', 'url': 'https://example.org/nvidia',
                 'resumo': 'Há uma possibilidade de mudança na linha. Não há confirmação de cancelamento nem preços.'},
     'artigo': 'A mudança é uma possibilidade e não foi confirmada pela fabricante.'},
    {'id': 'gta6', 'pergunta': 'Por que o GTA 6 não está ajudando nas vendas?',
     'noticia': {'titulo': 'Vendas de hardware nos EUA seguem fracas, apesar da expectativa por GTA 6',
                 'fonte': 'Fonte de teste', 'url': 'https://example.org/gta6',
                 'resumo': 'O título relaciona vendas fracas de hardware e expectativa por GTA 6. O resumo não informa a causa.'},
     'artigo': 'As vendas se referem ao período anterior ao lançamento do jogo. '
               'O autor levanta a hipótese de consumidores adiarem a compra; não apresenta pesquisa que prove a causa.'},
    {'id': 'oled', 'pergunta': 'Como fizeram esse teste?',
     'noticia': {'titulo': 'Teste prolongado de monitor OLED encontrou burn-in',
                 'fonte': 'Fonte de teste', 'url': 'https://example.org/oled',
                 'resumo': 'Foram relatadas marcas após uso prolongado; a metodologia não consta do resumo.'},
     'artigo': 'Após uso diário com elementos estáticos, o autor fotografou '
               'telas brancas e cinzas para verificar marcas. Não publicou o brilho nem um grupo de controle.'},
]


def executar(p, caso, seed, modelo):
    pedidos, leituras = [], []
    hist = [{'role': 'user', 'content': 'Agora estou em outro jogo.'},
            {'role': 'assistant', 'content': 'Vamos jogar.'}]

    def llm(**kw):
        if kw.get('stream'):
            raise FalhaBancada('Esta bancada usa respostas completas, sem TTS ou streaming da interface.')
        conferir_identidade(identidade('http://127.0.0.1:6996', 'gemma-4-12B'), modelo)
        pedido = {**preparar(kw), 'seed': seed}
        try:
            r = chamar('http://127.0.0.1:6996', modelo, pedido)
        except Exception as erro:
            raise FalhaBancada(str(erro)) from erro
        pedidos.append({'ramo': 'roteador' if kw.get('tools') else 'persona', 'pedido': pedido, **r})
        resp = _Resposta()
        resp.choices[0].message.content = r['texto']
        resp.choices[0].message.tool_calls = [SimpleNamespace(function=SimpleNamespace(**f)) for f in r['ferramentas']]
        resp.choices[0].finish_reason = r['finish_reason']
        resp.usage.completion_tokens = r.get('uso', {}).get('completion_tokens', 0)
        return resp

    def ler(url):
        assert url == caso['noticia']['url'], url
        leituras.append(url)
        return caso['artigo']

    token = novidades_web.contexto_novidade.set(caso['noticia'])
    p._ultima_saudacao_ts = time.time()
    p._kaomoji_recentes.clear()
    try:
        with patch.object(p, '_chamar_llm', llm), \
             patch.object(p, '_capturar_momento', return_value={'canal': 'web'}), \
             patch.object(p, 'ATIVAR_MEMORIA_PERMANENTE', False), \
             patch.object(p.obsidian, 'indice_notas', return_value=''), \
             patch.object(p.obsidian, 'ler_perfil', return_value='Gosta de jogos e humor exagerado.'), \
             patch.object(p.obsidian, 'listar_memoria_episodica', return_value=[]), \
             patch.object(p, 'buscar_memoria_relevante', return_value=[]), \
             patch.object(p, 'buscar_contexto_relevante', return_value=''), \
             patch.object(p.assuntos, 'contexto_relacionado', return_value=''), \
             patch.object(p, 'ler_estado_luna', return_value={}), \
             patch.object(p, 'obter_janela_em_foco', return_value='bancada'), \
             patch.object(tom, 'obter_hint', return_value=''), \
             patch.dict(p.FUNCOES_DISPONIVEIS, {'resumir_site': ler}), \
             patch('modulos.metricas_ferramentas.registrar_uso'), \
             p.controle.executar(), redirect_stdout(io.StringIO()):
            fala = p.gerar_resposta(caso['pergunta'], hist, salvar=False,
                                   responder_completo=True, max_tokens=400)
    finally:
        novidades_web.contexto_novidade.reset(token)
    return {'caso': caso['id'], 'seed': seed, 'fala': str(fala), 'leituras': leituras,
            'chamadas': pedidos, 'historico': hist}


def rodar():
    modelo = identidade('http://127.0.0.1:6996', 'gemma-4-12B')
    dados = {'modelo': modelo, 'concluido': False, 'casos': CASOS, 'resultados': [],
             'metodo': '3 perguntas x 2 seeds; fluxo real de roteador e persona, fontes sintéticas. '
                       'Sem rede para artigos, memória persistente, TTS ou instância da Luna.'}
    p = preparar_runtime()
    for caso in CASOS:
        for seed in (1101, 1102):
            r = executar(p, caso, seed, modelo)
            dados['resultados'].append(r)
            gravar_json(PASTA/'resultados.json', dados)
            print(caso['id'], seed, 'artigo' if r['leituras'] else 'resumo', r['fala'], flush=True)
    dados['concluido'] = True
    gravar_json(PASTA/'resultados.json', dados)


if __name__ == '__main__':
    rodar()
