"""A/B do ENXUTO_PROATIVO; mantém EMOCAO e instruções da tarefa intactas."""

import argparse
import datetime
import json
from unittest.mock import patch

from bancada_persona import RAIZ, CENARIOS, executar_cenario, avaliar
from bancada_steam_ab import CASOS, instrucao_atual
from modulos import prompts


def inverter_blocos(montador, instrucao, sem_emoji, emocao=''):
    original = montador(instrucao, sem_emoji, emocao)
    if not emocao:
        return original
    trecho = emocao + '\n' + instrucao
    if original.count(trecho) != 1:
        raise RuntimeError('A montagem mudou; revise a inversão experimental.')
    invertido = original.replace(trecho, instrucao + '\n' + emocao, 1)
    # A comparação precisa mudar só a ordem, sem perder nem duplicar instruções.
    from collections import Counter
    assert Counter(original) == Counter(invertido)
    return invertido


def candidato(atual):
    antigo = (
        'Faça uma ou duas frases e use somente a dimensão do próprio dado. Uma comparação pode mostrar '
        'essa escala, mas precisa ser obviamente figurativa e não pode afirmar consequência física, '
        'risco, equipamento necessário ou efeito técnico que a observação não informou. '
    )
    novo = (
        'Faça uma ou duas frases no registro de humor descrito acima. '
        'Os fatos são o ponto de partida; a imagem da piada pode ser desproporcional, '
        'física e absurda: o pequeno pode virar catástrofe e o comum pode virar épico. '
        'A ligação entre o detalhe real e a imagem precisa ser compreensível. '
        'Preserve os números e acontecimentos reais; amplie a imagem, não os fatos. '
        'Entregue a hipérbole com seriedade, sem explicar a piada. '
        'Uma cena figurativa não é um acontecimento real nem uma previsão técnica: '
        'não apresente risco, efeito técnico ou equipamento necessário como informação factual. '
    )
    if atual.count(antigo) != 1:
        raise RuntimeError('O prompt mudou; revise a substituição experimental.')
    return atual.replace(antigo, novo).replace(
        'seja curiosa em vez de inventar magnitude.',
        'seja curiosa sem inventar fatos para sustentar a piada.')


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--repeticoes', type=int, default=2, choices=range(1, 6))
    ap.add_argument('--experimento', choices=('hiperbole', 'posicao'), default='hiperbole')
    args = ap.parse_args()
    from modulos import pensar

    base = next(c for c in CENARIOS if c['id'] == 'proativo_jogo_aberto')
    cenarios = []
    for identificador, jogo, dados in CASOS:
        tecnica = (
            f'O usuário acabou de abrir {jogo} na Steam.\n'
            f'DADOS DISPONÍVEIS: Jogo: {jogo}. {dados}\n'
            f'{prompts.GOSTO_DE_JOGO}\n{instrucao_atual()} Comente a abertura. '
            'Fale diretamente com o usuário em segunda pessoa (você, seu, te). '
            'Seja breve e natural: máximo 2 frases.'
        )
        cenarios.append(dict(base, id=identificador, tecnica=tecnica, responder_completo=False))
    # Controles fora de jogos: este bloco também governa outras tarefas proativas.
    cenarios.extend(dict(c) for c in CENARIOS if c['id'] in (
        'proativo_rss_com_atitude', 'proativo_email_com_atitude'))
    atual = prompts.ENXUTO_PROATIVO
    variantes = ({'atual': atual, 'emocao_depois': atual} if args.experimento == 'posicao'
                 else {'atual': atual, 'hiperbole': candidato(atual)})
    montador = prompts.nucleo_enxuto
    destino = RAIZ / 'logs' / (f'bancada_emocao_{args.experimento}_' +
                              datetime.datetime.now().strftime('%Y%m%d_%H%M%S') + '.json')
    destino.parent.mkdir(exist_ok=True)
    resultados = []
    for rodada in range(args.repeticoes):
        ordem = list(variantes) if rodada % 2 == 0 else list(reversed(variantes))
        for cenario in cenarios:
            for variante in ordem:
                teste = dict(cenario)
                if cenario['id'] in {c[0] for c in CASOS}:
                    abordagem = ('um comentário curto e direto',
                                 'uma provocação leve e bem-humorada (sem ofender)')[rodada % 2]
                    teste['tecnica'] += f'\nDesta vez, faça isso como {abordagem}.'
                sistemas = []

                def montar(instrucao, sem_emoji, emocao=''):
                    sistema = (inverter_blocos(montador, instrucao, sem_emoji, emocao)
                               if variante == 'emocao_depois'
                               else montador(instrucao, sem_emoji, emocao))
                    sistemas.append(sistema)
                    return sistema

                with (patch.object(prompts, 'ENXUTO_PROATIVO', variantes[variante]),
                      patch.object(prompts, 'nucleo_enxuto', montar)):
                    resposta, persona = executar_cenario(pensar, teste)
                item = dict(cenario=cenario['id'], rodada=rodada + 1, variante=variante,
                            resposta=resposta, falhas=avaliar(teste, resposta),
                            usou_persona=persona, tecnica=teste['tecnica'], sistemas=sistemas)
                resultados.append(item)
                destino.write_text(json.dumps(dict(prompts=variantes, resultados=resultados),
                                              ensure_ascii=False, indent=2), encoding='utf-8')
                print(f"[{cenario['id']}/{rodada + 1}/{variante}] {resposta}", flush=True)
                if item['falhas']:
                    print('  Checks: ' + '; '.join(item['falhas']), flush=True)
    print(f'Resultados: {destino}')
    for variante in variantes:
        grupo = [r for r in resultados if r['variante'] == variante]
        print(f"{variante}: {sum(not r['falhas'] for r in grupo)}/{len(grupo)} checks; "
              f"{sum(r['usou_persona'] for r in grupo)} com persona completa")


if __name__ == '__main__':
    main()
