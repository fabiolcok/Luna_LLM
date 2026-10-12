"""Confere os backups e exercita os quatro níveis sem iniciar Luna, áudio ou serviços."""
import argparse
from contextlib import contextmanager, redirect_stdout
from copy import deepcopy
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import sys
from unittest.mock import patch

from testes.bancada_dark_souls_thinking import preparar_runtime
from testes.bancada_modelos import chamar, conferir_identidade, identidade, gravar_json
from testes.testa_prompt_montagem import CENARIOS, capturar, normalizar

RAIZ = Path(__file__).resolve().parents[1]
FIXTURE = RAIZ / 'testes/fixtures/personalidades_montagem.json'


@contextmanager
def runtime(pensar):
    import modulos
    with patch.dict(sys.modules, {'modulos.pensar': pensar}), \
         patch.object(modulos, 'pensar', pensar, create=True), redirect_stdout(io.StringIO()):
        yield


def montagens(pensar):
    with runtime(pensar):
        return {c['id']: hashlib.sha256(normalizar(capturar(c)).encode()).hexdigest()
                for c in CENARIOS}


def comparar_backups():
    """Só a preparação lê backups; os testes futuros usam hashes públicos normalizados."""
    from modulos import prompts
    p = preparar_runtime()
    salvo = prompts.personalidade_ativa()
    fixture = {'origem': 'Backups fornecidos pelo usuário; montagem completa e enxuta, 44 cenários.',
               'perfis': {}}
    try:
        for nivel, nome in [(1, 'LUNA'), (2, 'TARS'), (3, 'GLADOS')]:
            spec = importlib.util.spec_from_file_location('_backup_persona', RAIZ / f'modulos/prompts - {nome}.py')
            backup = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(backup)
            backup.personalidade_ativa = lambda: nivel
            backup.nome_personalidade = lambda: nome
            with patch.object(p, '_prompts', backup):
                esperado = montagens(p)
            prompts.selecionar_personalidade(nivel)
            atual = montagens(p)
            divergentes = [c for c in esperado if esperado[c] != atual[c]]
            if divergentes:
                raise AssertionError(f'{nome}: montagem mudou em {divergentes}')
            fixture['perfis'][str(nivel)] = esperado
            print(f'{nome}: {len(atual)}/{len(esperado)} montagens idênticas ao backup.', flush=True)
        prompts.selecionar_personalidade(0)
        fixture['perfis']['0'] = montagens(p)
        gravar_json(FIXTURE, fixture)
    finally:
        prompts.selecionar_personalidade(salvo)


def atualizar_fixture():
    from modulos import prompts
    p = preparar_runtime()
    salvo = prompts.personalidade_ativa()
    fixture = {'origem': 'Montagem atual aprovada; confira a mudança na bancada antes de atualizar.', 'perfis': {}}
    try:
        for nivel in range(4):
            prompts.selecionar_personalidade(nivel)
            fixture['perfis'][str(nivel)] = montagens(p)
        gravar_json(FIXTURE, fixture)
    finally:
        prompts.selecionar_personalidade(salvo)


def executar(destino):
    from modulos import prompts
    from testes.bancada_ferramentas_glados import CASOS, executar_turno
    p = preparar_runtime()
    from modulos.turbollm_api import recarregar_modelo
    pronto = recarregar_modelo('http://127.0.0.1:6996/v1', segundos=60)
    if not pronto.get('ok'):
        raise RuntimeError(pronto)
    modelo = identidade('http://127.0.0.1:6996', 'gemma')
    casos = {c['id']: c for c in CENARIOS}
    casos['chat_leve'] = {'id': 'chat_leve', 'usuario': 'Hoje vou só jogar um pouco e descansar. Nada de projeto.'}
    # Os IDs de montagem são conferidos antes de qualquer chamada real.
    selecionados = ['chat_leve', 'enxuto_sensivel'] + [
        next(c['id'] for c in CENARIOS if c.get('tarefa_proativa') == tarefa)
        for tarefa in ['dark_souls_morte', 'radar_rss']]
    ferramenta = next(c for c in CASOS if c['id'] == 'spotify_tocar')
    registro = {'modelo': modelo, 'resultados': [], 'completo': False,
                'limites': 'Uma amostra por caso/perfil. Ferramentas simuladas; sem áudio ou medição de FPS.'}
    salvo = prompts.personalidade_ativa()
    try:
        for nivel in (0, 1, 2, 3):
            prompts.selecionar_personalidade(nivel)
            for cid in selecionados:
                conferir_identidade(identidade('http://127.0.0.1:6996', 'gemma'), modelo)
                with runtime(p):
                    pedido = capturar(casos[cid], pedido_completo=True)
                pedido = deepcopy(pedido)
                pedido.update(pedido.pop('extra_body', {}))
                pedido.update(seed=481, stream=True, stream_options={'include_usage': True}, cache_prompt=False)
                resposta = chamar('http://127.0.0.1:6996', modelo, pedido)
                registro['resultados'].append({'perfil': nivel, 'nome': prompts.nome_personalidade(),
                    'cenario': cid, 'pedido': pedido, **resposta})
                gravar_json(destino, registro)
                print(f'{nivel} {cid}: {resposta["texto"]}', flush=True)
            def modelo_real(pedido, ramo):
                return chamar('http://127.0.0.1:6996', modelo, pedido)
            with redirect_stdout(io.StringIO()):
                resultado = executar_turno(p, ferramenta, [], 481, modelo_real)
            registro['resultados'].append({'perfil': nivel, 'nome': prompts.nome_personalidade(),
                'cenario': 'ferramenta_spotify', **resultado})
            gravar_json(destino, registro)
            print(f'{nivel} ferramenta: {resultado["fala"]} · erro={resultado["erro"]}', flush=True)
        conferir_identidade(identidade('http://127.0.0.1:6996', 'gemma'), modelo)
        registro['completo'] = True
        gravar_json(destino, registro)
    finally:
        prompts.selecionar_personalidade(salvo)


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    acao = ap.add_mutually_exclusive_group(required=True)
    acao.add_argument('--comparar-backups', action='store_true')
    acao.add_argument('--atualizar-fixture', action='store_true')
    acao.add_argument('--executar', type=Path)
    args = ap.parse_args()
    if args.comparar_backups:
        comparar_backups()
    elif args.atualizar_fixture:
        atualizar_fixture()
    elif args.executar:
        executar(args.executar)
