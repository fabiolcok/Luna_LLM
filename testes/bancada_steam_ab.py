r"""Compara a obrigação de detalhe + horas com dados opcionais, sem alterar a Luna.

Uso: venv\Scripts\python.exe -X utf8 testes/bancada_steam_ab.py --repeticoes 2
Reusa o executor isolado da bancada de persona. Resultados exigem leitura humana:
os checks de palavras não medem graça, nexo ou vontade de responder.
"""

import argparse
import ast
import json
import datetime

from bancada_persona import RAIZ, CENARIOS, executar_cenario, avaliar
from modulos.prompts import GOSTO_DE_JOGO


def instrucao_atual():
    # Lê a instrução vigente sem importar o monitor e seus serviços.
    arvore = ast.parse((RAIZ / 'modulos/proativa.py').read_text(encoding='utf-8'))
    for no in ast.walk(arvore):
        if isinstance(no, ast.Assign) and any(
            isinstance(t, ast.Name) and t.id == 'instrucao' for t in no.targets
        ) and isinstance(no.value, ast.Constant):
            if str(no.value.value).startswith('Puxe UM detalhe específico do jogo'):
                return no.value.value
    raise RuntimeError('A instrução de abertura mudou; revise esta bancada.')


EXPERIMENTO = (
    'Escolha o que merece uma reação sua nesta abertura. Os dados são apoio: '
    'não é obrigatório citar horas nem explicar um detalhe do jogo. '
    'Se houver uma lembrança pessoal relevante, você pode reagir a ela. '
    'Não invente acontecimentos da partida ou experiências do usuário.'
)

CASOS = [
    ('retorno', 'Hollow Knight',
     'Gênero: Ação, Indie, Aventura. Exploração de um reino subterrâneo em ruínas. '
     'Você já tem 42 horas totais nele. Faz 21 dias que você não abria esse jogo.'),
    ('memoria', 'Hades',
     'Gênero: Ação, Roguelike. Tentativas de escapar do submundo. '
     'Você já tem 35 horas totais nele. Nas últimas 2 semanas foram 8 horas. '
     'Memória pessoal relevante: ontem você disse que desistiu porque o loop cansou.'),
    ('habitual', 'Stardew Valley',
     'Gênero: RPG, Simulação. Cultivar uma fazenda e conhecer os moradores da vila. '
     'Você já tem 120 horas totais nele. Nas últimas 2 semanas foram 6 horas.'),
]


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--repeticoes', type=int, default=2, choices=range(1, 6))
    ap.add_argument('--semente-hades', action='store_true',
                    help='compara atual, dados opcionais e dados opcionais com semente')
    args = ap.parse_args()
    from modulos import pensar

    base = next(c for c in CENARIOS if c['id'] == 'proativo_jogo_aberto')
    instrucoes = {'atual': instrucao_atual(), 'opcional': EXPERIMENTO}
    casos = CASOS
    if args.semente_hades:
        casos = [c for c in CASOS if c[0] == 'memoria']
        instrucoes['semente'] = EXPERIMENTO + (
            '\nÂngulo para desenvolver: a desistência de ontem teve uma carreira curtíssima. '
            'Explore a curta duração dessa desistência numa imagem sua, mantendo o contraste '
            'entre o que ele disse ontem e o que abriu hoje. Não repita esta orientação como fala.'
        )
    destino = RAIZ / 'logs' / ('bancada_steam_' +
                              ('semente_' if args.semente_hades else 'ab_') +
                              datetime.datetime.now().strftime('%Y%m%d_%H%M%S') + '.json')
    destino.parent.mkdir(exist_ok=True)
    resultados = []
    for rodada in range(args.repeticoes):
        # Alterna a ordem para não deixar sempre a mesma versão com o modelo frio.
        nomes = list(instrucoes)
        deslocamento = rodada % len(nomes)
        ordem = nomes[deslocamento:] + nomes[:deslocamento]
        abordagem = ('um comentário curto e direto',
                     'uma provocação leve e bem-humorada (sem ofender)')[rodada % 2]
        for identificador, jogo, dados in casos:
            for variante in ordem:
                prompt = (
                    f'O usuário acabou de abrir {jogo} na Steam.\n'
                    f'DADOS DISPONÍVEIS: Jogo: {jogo}. {dados}\n'
                    f'{GOSTO_DE_JOGO}\n{instrucoes[variante]} Comente a abertura. '
                    'Fale diretamente com o usuário em segunda pessoa (você, seu, te). '
                    'Seja breve e natural: máximo 2 frases.'
                )
                # Espelha o corte do gerador; mantém a abordagem igual dentro do par.
                cortado = len(prompt) > 1500
                prompt = prompt[:1500] + '... [texto cortado]' if cortado else prompt
                prompt += f'\nDesta vez, faça isso como {abordagem}.'
                cenario = dict(base, tecnica=prompt, responder_completo=False)
                resposta, persona = executar_cenario(pensar, cenario)
                item = dict(cenario=identificador, rodada=rodada + 1, variante=variante,
                            abordagem=abordagem, prompt=prompt, cortado=cortado,
                            resposta=resposta, usou_persona=persona,
                            falhas=avaliar(cenario, resposta))
                resultados.append(item)
                destino.write_text(json.dumps(resultados, ensure_ascii=False, indent=2), encoding='utf-8')
                print(f'[{identificador}/{rodada + 1}/{variante}] {resposta}', flush=True)
                if item['falhas']:
                    print('  Checks: ' + '; '.join(item['falhas']), flush=True)
    destino.write_text(json.dumps(resultados, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'Resultados: {destino}')
    for variante in instrucoes:
        grupo = [r for r in resultados if r['variante'] == variante]
        print(f"{variante}: {sum(not r['falhas'] for r in grupo)}/{len(grupo)} checks; "
              f"{sum(r['usou_persona'] for r in grupo)} com persona completa; "
              f"{sum(r['cortado'] for r in grupo)} prompts cortados")


if __name__ == '__main__':
    main()
