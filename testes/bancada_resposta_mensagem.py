"""Gemma real com referência antiga; fontes sintéticas, sem memória, áudio ou ações externas."""
from pathlib import Path
from unittest.mock import patch

from modulos.biblioteca_web import contexto_resposta
from testes.bancada_continuar_novidade import executar, CASOS as NOTICIAS
from testes.bancada_dark_souls_thinking import preparar_runtime, FalhaBancada
from testes.bancada_modelos import identidade, gravar_json

PASTA = Path('logs/bancada_web/20261011-conversa-biblioteca')
CASOS = [
    {'id': 'piada_antiga', 'pergunta': 'O que você quis dizer com isso?', 'noticia': None,
     'resposta': {'referencia': {'turno_id': 'piada'}, 'usuario': 'Comecei Dark Souls.',
                  'luna': 'A gravidade já pediu uma reunião com você.', 'cartoes': []}},
    {'id': 'conversa_antiga', 'pergunta': 'Isso ainda impediria o acesso externo?', 'noticia': None,
     'resposta': {'referencia': {'turno_id': 'servidor'}, 'usuario': 'Não consigo abrir portas.',
                  'luna': 'Você está atrás do CGNAT do provedor. Ainda não conseguiu um IP público.', 'cartoes': []}},
    {**NOTICIAS[2], 'id': 'noticia_da_biblioteca',
     'resposta': {'referencia': {'item_id': 'noticia'}, 'usuario': '', 'luna': NOTICIAS[2]['noticia']['titulo'], 'cartoes': []}},
]


def rodar():
    modelo = identidade('http://127.0.0.1:6996', 'gemma-4-12B')
    p = preparar_runtime()
    dados = {'modelo': modelo, 'concluido': False, 'resultados': [],
             'metodo': '3 referências x 2 seeds; roteador e persona separados no relatório. '
                       'Histórico atual fala de outro jogo; a resposta deve retomar só a referência escolhida.'}
    def bloqueado(nome):
        def impedir(*args, **kwargs):
            dados.setdefault('bloqueadas', []).append({'caso': caso['id'], 'seed': seed,
                'ferramenta': nome, 'argumentos': kwargs})
            gravar_json(PASTA / 'respostas-gemma.json', dados)
            raise FalhaBancada('A bancada tentou uma ferramenta externa: ' + nome)
        return impedir
    for caso in CASOS:
        for seed in (1111, 1112):
            token = contexto_resposta.set(caso['resposta'])
            try:
                with patch.dict(p.FUNCOES_DISPONIVEIS,
                    {nome: bloqueado(nome) for nome in p.FUNCOES_DISPONIVEIS}):
                    resultado = executar(p, caso, seed, modelo)
            finally:
                contexto_resposta.reset(token)
            dados['resultados'].append(resultado)
            gravar_json(PASTA / 'respostas-gemma.json', dados)
            print(caso['id'], seed, resultado['fala'], flush=True)
    dados['concluido'] = True
    gravar_json(PASTA / 'respostas-gemma.json', dados)


if __name__ == '__main__':
    rodar()
