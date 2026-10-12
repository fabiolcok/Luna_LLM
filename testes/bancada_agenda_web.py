"""Persona da agenda com o modelo atual, eventos sintéticos e nenhuma chamada ao Google."""
import argparse
from contextlib import redirect_stdout
from copy import deepcopy
import io
from pathlib import Path
from unittest.mock import patch

from modulos import agenda_web, momento, tom
from testes.bancada_dark_souls_thinking import preparar_runtime
from testes.bancada_modelos import chamar, conferir_identidade, gravar_json, identidade
from testes.testa_prompt_montagem import _Resposta


EVENTOS = [
    dict(titulo='Reunião do projeto', inicio='2026-10-10T14:00:00-03:00', fim='2026-10-10T15:00:00-03:00', dia_inteiro=False),
    dict(titulo='Consulta', inicio='2026-10-10T19:00:00-03:00', fim='2026-10-10T20:00:00-03:00', dia_inteiro=False),
    dict(titulo='Viagem', inicio='2026-10-12', fim='2026-10-13', dia_inteiro=True),
]
TEXTO = ('Aqui estão os seus compromissos:\n- Reunião do projeto — sábado, 10 de outubro às 14h\n'
         '- Consulta — sábado, 10 de outubro às 19h\n- Viagem — segunda, 12 de outubro')
CASOS = [
    dict(id='consulta_web', pergunta='Como está minha agenda?', texto=TEXTO, eventos=EVENTOS),
    dict(id='periodo_web', pergunta='Tenho algum compromisso amanhã depois das 18h?', texto=TEXTO, eventos=EVENTOS),
    dict(id='vazia_web', pergunta='Como está minha agenda?', eventos=[],
         texto='A sua agenda está completamente vazia para os próximos 30 dias.'),
    dict(id='criacao_web', pergunta='Marque reunião do projeto amanhã às 14h.', eventos=EVENTOS[:1],
         texto="Sucesso! O evento 'Reunião do projeto' foi criado para sábado, 10 de outubro às 14h."),
    dict(id='consulta_voz', pergunta='Consulte minha agenda', texto=TEXTO, eventos=EVENTOS, completo=False),
    dict(id='consulta_telegram', pergunta='Consulte minha agenda', texto=TEXTO, eventos=EVENTOS, pc=False),
]


def capturar(pensar, caso, visual=True):
    pedidos = []
    def interceptar(**kw):
        pedidos.append(deepcopy(kw))
        return _Resposta()
    pensar._presenca_pc.set(caso.get('pc', True))
    pensar._ultima_saudacao_ts = 1e20
    pensar._kaomoji_recentes.clear()
    tecnico = agenda_web.resultado(caso['texto'], caso['eventos']) if visual else caso['texto']
    with patch.object(pensar, '_chamar_llm', interceptar), \
         patch.object(pensar.obsidian, 'ler_perfil', return_value='Gosta de jogos e humor exagerado.'), \
         patch.object(pensar.obsidian, 'listar_memoria_episodica', return_value=[]), \
         patch.object(pensar.obsidian, 'avaliar_relevancia', return_value=False), \
         patch.object(pensar, 'buscar_memoria_relevante', return_value=[]), \
         patch.object(pensar, 'buscar_contexto_relevante', return_value=''), \
         patch.object(pensar.assuntos, 'contexto_relacionado', return_value=''), \
         patch.object(pensar, 'ler_estado_luna', return_value={}), \
         patch.object(pensar, 'obter_janela_em_foco', return_value='bancada de teste'), \
         patch.object(momento, '_jogos', {}), patch.object(tom, 'obter_hint', return_value=''), \
         redirect_stdout(io.StringIO()):
        pensar._reescrever_como_luna(tecnico, caso['pergunta'], [], max_tokens=800,
                                    responder_completo=caso.get('completo', True))
    assert len(pedidos) == 1
    return pedidos[0]


def rodar(pasta):
    pensar = preparar_runtime()
    modelo = identidade('http://127.0.0.1:6996', 'gemma-4-12B')
    dados = dict(modelo=modelo, concluido=False, resultados=[],
                 metodo='6 cenários sintéticos + controle sem cartão; persona real; sem Google, áudio ou memória pessoal')
    gravar_json(pasta / 'resultados.json', dados)
    suites = [('controle_web', CASOS[0], False)] + [(c['id'], c, True) for c in CASOS]
    for nome, caso, visual in suites:
        pedido = capturar(pensar, caso, visual)
        pedido.update(pedido.pop('extra_body', {}))
        pedido.update(seed=901, stream=True, stream_options={'include_usage': True}, cache_prompt=False,
                      chat_template_kwargs={'enable_thinking': False})
        conferir_identidade(identidade('http://127.0.0.1:6996', 'gemma-4-12B'), modelo)
        print(nome, flush=True)
        resposta = chamar('http://127.0.0.1:6996', modelo, pedido)
        dados['resultados'].append(dict(caso=nome, pergunta=caso['pergunta'], pedido=pedido, **resposta))
        gravar_json(pasta / 'resultados.json', dados)
    dados['concluido'] = True
    gravar_json(pasta / 'resultados.json', dados)
    linhas = ['# Bancada: agenda visual', '', dados['metodo'], '']
    for r in dados['resultados']:
        linhas.extend([f"## {r['caso']}", '', r['texto'], '',
                       f"Tokens: {r['uso']}. Total: {r['total_s']:.2f}s. Finalização: {r['finish_reason']}.", ''])
    (pasta / 'amostras.md').write_text('\n'.join(linhas), encoding='utf8')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--pasta', type=Path, required=True)
    args = parser.parse_args()
    rodar(args.pasta)
