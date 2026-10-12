"""A/B do comentário RSS com sugestões na mesma chamada, sem voz, memória ou ferramentas."""
import argparse
from contextlib import redirect_stdout
from copy import deepcopy
import io
import json
from pathlib import Path
import re
import statistics
from types import ModuleType
from unittest.mock import patch

from testes.bancada_dark_souls_thinking import preparar_runtime, extrair
from testes.bancada_modelos import chamar, conferir_identidade, identidade, gravar_json
from testes.testa_prompt_montagem import _Resposta
from modulos.novidades_web import separar_sugestoes


CASOS = [
    {"id": "arc_raiders", "titulo": "Estúdio de ARC Raiders vai usar IA para combater cheaters",
     "resumo": "O estúdio anunciou uso de IA para identificar trapaças. O resumo não detalha o método nem taxas de erro."},
    {"id": "oled", "titulo": "Teste de 8.000 horas encontra burn-in em monitor QD-OLED da MSI",
     "resumo": "Após 30 meses, o teste registrou burn-in e uma linha vertical visível no branco."},
    {"id": "tts_sintetico", "titulo": "TTS de teste anuncia suporte experimental a português brasileiro",
     "resumo": "Fixture sintética: um projeto de voz publicou uma versão experimental PT-BR para CPU. Não há medições de qualidade."},
    {"id": "titulo_sem_resumo", "titulo": "Estúdio de teste anuncia novo jogo cooperativo", "resumo": ""},
]


def executar_radar(casos, gerar, preferencias=None):
    """Executa a seleção/cartão da produção usando exclusivamente feeds sintéticos."""
    from types import SimpleNamespace
    from unittest.mock import Mock
    import ast
    feed = 'https://example.org/rss'
    parser = ModuleType('feedparser')
    parser.parse = lambda *a, **k: SimpleNamespace(feed={'title': 'Feed de teste'}, entries=[
        {'id': c['id'], 'title': c['titulo'], 'summary': c['resumo'], 'link': f'https://example.org/{c["id"]}'}
        for c in casos])
    e = {
        'CONFIGURACAO': {'Radar_RSS': {'ativo': True, 'horario_silencio': (0, 0), 'intervalo_minutos': 30}},
        '_em_horario_silencio': lambda *a: False, '_passou_intervalo': lambda *a: True,
        'obsidian': SimpleNamespace(ler_feeds_radar=lambda: [feed],
            link_novidades=lambda: 'obsidian://open?path=Novidades.md', adicionar_novidades=Mock()),
        'carregar_vistos': lambda: {'radar': {}, 'radar_feeds': [feed]}, 'salvar_vistos': Mock(),
        '_RADAR_MAX_VISTOS': 1000, '_limpar_resumo': lambda s: s, '_extrair_imagem': lambda _: '',
        'random': SimpleNamespace(choice=lambda xs: xs[0],
            choices=lambda xs, weights, k: [xs[weights.index(max(weights))]]), 'REGRA_PERSONA': '',
        'registrar_tentativa': Mock(), 'cor': Mock(), '_ultima_execucao': {},
        '_execucoes': SimpleNamespace(contexto=SimpleNamespace(get=lambda: None)),
        '_gerar_fala_proativa': gerar,
    }
    # A instrução de tom é a mesma da produção, com nome neutro na fixture.
    regra = next(n for n in ast.parse(Path('modulos/proativa.py').read_text(encoding='utf8')).body
                 if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'REGRA_PERSONA' for t in n.targets))
    exec(compile(ast.Module(body=[regra], type_ignores=[]), 'regra-persona-rss', 'exec'),
         {'NOME_USUARIO': 'Usuário'}, e)
    extrair('modulos/proativa.py', {'_tarefa_radar_rss', '_FalaProativa'}, e)
    falas = []
    def falar(fala, **kw):
        falas.append(fala)
        kw['ao_apresentar']()
        return True
    e['_falar_proativamente'] = falar
    with patch.dict('sys.modules', {'feedparser': parser}), \
         patch('modulos.interesses_radar._carregar', return_value=preferencias or []):
        e['_tarefa_radar_rss']()
    return falas, e


def gerar_persona(pensar, instrucao, tarefa='radar_rss', bruto='Comentário. [clima:zoeira]', voz=True, fragmento=None):
    """Captura montagem e pós-processamento reais, substituindo só IO externo."""
    from modulos import momento, tom
    pedidos = []
    def interceptar(**kw):
        pedidos.append(deepcopy(kw))
        if kw.get('stream'):
            from types import SimpleNamespace
            return iter(SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content=bruto[i:i+5]),
                finish_reason=None)]) for i in range(0, len(bruto), 5))
        resposta = _Resposta()
        resposta.choices[0].message.content = bruto
        return resposta
    servidor = ModuleType('servidor')
    for nome in ('atualizar_metricas', 'atualizar_kaomoji', 'atualizar_gif'):
        setattr(servidor, nome, lambda *a, **k: None)
    pensar._ultima_saudacao_ts = 1e20
    pensar._kaomoji_recentes.clear()
    with (
        patch.object(pensar, '_chamar_llm', interceptar),
        patch.object(pensar.obsidian, 'ler_perfil', return_value='Gosta de jogos e humor exagerado.'),
        patch.object(pensar.obsidian, 'listar_memoria_episodica', return_value=[]),
        patch.object(pensar, 'ler_estado_luna', return_value={}),
        patch.object(pensar, 'obter_janela_em_foco', return_value='bancada de teste'),
        patch.object(momento, '_jogos', {}), patch.object(tom, 'obter_hint', return_value=''),
        patch.dict('sys.modules', {'servidor': servidor}), redirect_stdout(io.StringIO()),
    ):
        texto = pensar._reescrever_como_luna(instrucao, '', [], max_tokens=360,
            responder_completo=not voz, tarefa_proativa=tarefa, ao_fragmento=fragmento)
    return texto, pedidos


def rodar(pasta, controle=None):
    from modulos import prompts
    pensar = preparar_runtime()
    modelo = identidade('http://127.0.0.1:6996', 'gemma-4-12B')
    suites = []
    for caso in CASOS:
        capturados = []
        def gerar(instrucao, tarefa, **kw):
            _, pedidos = gerar_persona(pensar, instrucao, tarefa)
            capturados.extend(pedidos)
            return None
        executar_radar([caso], gerar)
        pedido = capturados[0]
        pedido.update(pedido.pop('extra_body', {}))
        pedido.update(stream=True, stream_options={'include_usage': True}, cache_prompt=False,
            chat_template_kwargs={'enable_thinking': False})
        pedido_controle = deepcopy(pedido)
        assert pedido_controle['messages'][-1]['content'].count(prompts.SUGESTOES_NOVIDADE_WEB) == 1
        pedido_controle['messages'][-1]['content'] = pedido_controle['messages'][-1]['content'].replace(prompts.SUGESTOES_NOVIDADE_WEB, '')
        pedido_controle['max_tokens'] = 220
        suites.append({'caso': caso, 'pedidos': {'antes': pedido_controle, 'botoes': pedido}})
    dados = {'modelo': modelo, 'metodo': '4 casos x 2 seeds x 2 variantes; ordem alternada; sem cache de prompt',
             'suite': suites, 'resultados': [], 'concluido': False}
    if controle:
        anterior = json.loads((controle / 'resultados.json').read_text(encoding='utf8'))
        conferir_identidade(modelo, anterior['modelo'])
        for atual, antes in zip(suites, anterior['suite'], strict=True):
            if atual['caso'] != antes['caso'] or atual['pedidos']['antes'] != antes['pedidos']['antes']:
                raise ValueError('O controle mudou; não é válido reaproveitar as chamadas anteriores.')
        dados['resultados'] = [r for r in anterior['resultados'] if r['variante'] == 'antes']
        if len(dados['resultados']) != 8:
            raise ValueError('Controle incompleto.')
        dados['controle_reaproveitado'] = str(controle)
        dados['metodo'] += '; controle idêntico reaproveitado da primeira rodada'
    gravar_json(pasta / 'resultados.json', dados)
    for i, suite in enumerate(suites):
        for seed in (901, 902):
            ordem = ('antes', 'botoes') if (i + seed) % 2 else ('botoes', 'antes')
            for variante in ordem:
                if controle and variante == 'antes':
                    continue
                conferir_identidade(identidade('http://127.0.0.1:6996', 'gemma-4-12B'), modelo)
                pedido = deepcopy(suite['pedidos'][variante])
                pedido['seed'] = seed
                print(f'{suite["caso"]["id"]} / {seed} / {variante}', flush=True)
                resultado = chamar('http://127.0.0.1:6996', modelo, pedido)
                limpo, sugestoes = separar_sugestoes(resultado['texto'])
                limpo = re.sub(r'\[clima:[^]]+\]', '', limpo).strip()
                dados['resultados'].append({'caso': suite['caso']['id'], 'seed': seed, 'variante': variante,
                    'comentario': limpo, 'sugestoes': sugestoes, **resultado})
                gravar_json(pasta / 'resultados.json', dados)
    dados['concluido'] = True
    gravar_json(pasta / 'resultados.json', dados)
    linhas = ['# Bancada: sugestões nas novidades', '',
        'Mesmo Gemma 4 12B e mesma persona; só o bloco adicional RSS difere.',
        'ARC Raiders e OLED usam os relatos fornecidos pelo usuário; os demais casos são sintéticos.',
        'Os checks de formato não medem humor; os comentários abaixo precisam ser lidos.', '']
    for variante in ('antes', 'botoes'):
        rs = [r for r in dados['resultados'] if r['variante'] == variante]
        validos = sum(2 <= len(r['sugestoes']) <= 3 for r in rs)
        linhas += [f'{variante}: {validos}/{len(rs)} com 2–3 sugestões; '
            f'total mediano {statistics.median(r["total_s"] for r in rs):.2f}s.', '']
    for suite in suites:
        linhas += [f'## {suite["caso"]["titulo"]}', '']
        for r in dados['resultados']:
            if r['caso'] != suite['caso']['id']:
                continue
            linhas += [f'### {r["variante"]} — seed {r["seed"]}', '', r['comentario'], '']
            linhas += ['- ' + s for s in r['sugestoes']] + ['']
    (pasta / 'amostras.md').write_text('\n'.join(linhas), encoding='utf8')
    print(pasta / 'amostras.md', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--pasta', type=Path, required=True)
    parser.add_argument('--controle', type=Path)
    args = parser.parse_args()
    if args.pasta.exists():
        raise ValueError('Use uma pasta nova para preservar os resultados anteriores.')
    rodar(args.pasta, args.controle)
