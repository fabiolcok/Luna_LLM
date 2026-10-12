"""Mede o caminho novo no Gemma selecionado; não cadastra monitor nem gera áudio."""
from contextlib import redirect_stdout
from copy import deepcopy
import io
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import modulos
from modulos import prompts, fontes_conversa
from testes.bancada_dark_souls_thinking import preparar_runtime
from testes.bancada_modelos import identidade, conferir_identidade, chamar, gravar_json
from testes.testa_prompt_montagem import _Resposta, capturar

PASTA = Path('logs/bancada_web/20261010-fontes-interesses-voz-v2')
CASOS = [
    {'id':'ptbr', 'usuario':'Acompanhe o TTS de teste e me avise quando tiver PT-BR: https://example.org/releases.atom',
     'interesse':'Suporte a português brasileiro'},
    {'id':'desempenho', 'usuario':'Luna, pode monitorar as releases de https://example.org/tts para melhorias de velocidade em CPU? A voz agradou, mas ficou lenta.',
     'interesse':'Melhorias na velocidade em CPU'},
    {'id':'duas_fontes', 'usuario':'Monitore o Projeto Voz em https://example.org/releases.atom e https://example.org/changelog para avisar quando corrigirem o sotaque brasileiro.',
     'interesse':'Correção do sotaque brasileiro'},
    {'id':'sem_interesse', 'usuario':'Acompanhe esse projeto: https://example.org/releases.atom', 'interesse':''},
]


def capturar_roteador(p, usuario):
    pedidos = []
    resposta = _Resposta()
    resposta.choices[0].message.tool_calls = [SimpleNamespace(function=SimpleNamespace(
        name='preparar_acompanhamento_fontes', arguments='{}'))]
    def interceptar(**kw):
        pedidos.append(deepcopy(kw)); return resposta
    with redirect_stdout(io.StringIO()), patch.object(p, '_capturar_momento', return_value={'canal':'web'}), \
         patch.object(p, 'ATIVAR_MEMORIA_PERMANENTE', False), patch.object(p.obsidian, 'indice_notas', return_value=''), \
         patch.object(p, '_chamar_llm', interceptar), patch.object(p, '_reescrever_como_luna', return_value='Confira o cartão.'), \
         patch.object(fontes_conversa, 'propor', return_value='Rascunho preparado.'), \
         patch('modulos.metricas_ferramentas.registrar_uso'):
        p.gerar_resposta(usuario, [], salvar=False, responder_completo=True)
    assert len(pedidos) == 1
    return pedidos[0]


def preparar(pedido):
    pedido = deepcopy(pedido)
    pedido.update(pedido.pop('extra_body', {}))
    pedido.update(stream=True, stream_options={'include_usage':True}, cache_prompt=False,
                  chat_template_kwargs={'enable_thinking':False})
    return pedido


def rodar():
    from modulos import turbollm_api
    import requests
    base = 'http://127.0.0.1:6996'
    status = requests.get(base + '/api/v1/status', timeout=5).json()
    if status['engine']['state'] != 'running':
        r = turbollm_api.recarregar_modelo(base+'/v1', configurado=status['lastLoaded']['modelKey'])
        if not r['ok']:
            raise RuntimeError(r)
    modelo = identidade(base, 'gemma-4-12B')
    p = preparar_runtime()
    dados = {'modelo':modelo, 'resultados':[], 'concluido':False,
             'metodo':'4 pedidos x 2 seeds no roteador; 4 confirmações persona; sem consulta de fontes ou TTS'}
    for caso in CASOS:
        pedido = preparar(capturar_roteador(p, caso['usuario']))
        for seed in (1001, 1002):
            conferir_identidade(identidade(base, 'gemma-4-12B'), modelo)
            resultado = chamar(base, modelo, {**pedido, 'seed':seed})
            dados['resultados'].append({'caso':caso['id'], 'ramo':'roteador', 'seed':seed,
                                        'pedido':pedido, **resultado})
            gravar_json(PASTA/'resultados.json', dados)
            print(caso['id'], seed, resultado['ferramentas'], flush=True)
        cenario = {'usuario':caso['usuario'], 'tecnica':'Rascunho preparado no cartão. A consulta só começa depois da confirmação.' +
                   (' Falta a mudança de interesse; preencha esse campo no cartão.' if caso['id'] == 'sem_interesse' else ''),
                   'tarefa_documento':'CONFIRMACAO_RASCUNHO_FONTES'}
        with patch.dict('sys.modules', {'modulos.pensar':p}), patch.object(modulos, 'pensar', p, create=True), redirect_stdout(io.StringIO()):
            pedido_persona = preparar(capturar(cenario, pedido_completo=True))
        conferir_identidade(identidade(base, 'gemma-4-12B'), modelo)
        resultado = chamar(base, modelo, {**pedido_persona, 'seed':1001})
        dados['resultados'].append({'caso':caso['id'], 'ramo':'persona', 'pedido':pedido_persona, **resultado})
        gravar_json(PASTA/'resultados.json', dados)
        print(caso['id'], 'persona', resultado['texto'], flush=True)
    dados['concluido'] = True
    gravar_json(PASTA/'resultados.json', dados)


if __name__ == '__main__':
    rodar()
