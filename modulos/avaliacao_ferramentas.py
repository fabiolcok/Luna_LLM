"""Avaliação humana da ação, independente do voto sobre a resposta."""
import json
import threading
from pathlib import Path
from copy import deepcopy

ARQUIVO = Path(__file__).resolve().parents[1] / 'logs' / 'avaliacao_ferramentas.json'
_lock = threading.RLock()
MOTIVOS = {'desnecessaria', 'ferramenta_errada', 'parametros_errados', 'resultado_errado', 'faltou_ferramenta'}


def _ler():
    if not ARQUIVO.exists():
        return {}
    return json.loads(ARQUIVO.read_text(encoding='utf-8'))


def _gravar(dados):
    ARQUIVO.parent.mkdir(parents=True, exist_ok=True)
    temp = ARQUIVO.with_suffix('.tmp')
    temp.write_text(json.dumps(dados, ensure_ascii=False), encoding='utf-8')
    temp.replace(ARQUIVO)


def registrar(turno):
    ctx = turno.get('contexto', {})
    if not ctx.get('ferramenta'):
        return
    item = {k: deepcopy(turno.get(k)) for k in ('turno_id', 'usuario', 'luna', 'tempo_resposta')}
    item.update(ferramenta=deepcopy(ctx['ferramenta']), chamadas=deepcopy(ctx.get('chamadas', [])), voto=None)
    with _lock:
        dados = _ler()
        dados.setdefault(item['turno_id'], item)
        _gravar(dados)


def listar():
    with _lock:
        return list(_ler().values())


def votar(identificador, rating, motivo='', comentario='', snapshot=None):
    if rating not in ('bom', 'ruim') or motivo not in MOTIVOS | {''}:
        raise ValueError('Avaliação inválida.')
    if not isinstance(comentario, str) or len(comentario) > 1000:
        raise ValueError('Comentário inválido.')
    if rating == 'ruim' and not motivo:
        raise ValueError('Escolha um motivo.')
    with _lock:
        dados = _ler()
        if identificador not in dados:
            if not snapshot or motivo != 'faltou_ferramenta' or rating != 'ruim':
                raise ValueError('Resposta indisponível para avaliação.')
            dados[identificador] = {k: deepcopy(snapshot.get(k)) for k in ('turno_id', 'usuario', 'luna', 'tempo_resposta')}
            dados[identificador].update(ferramenta=None, chamadas=snapshot.get('contexto', {}).get('chamadas', []))
        item = dados[identificador]
        item['voto'] = {'rating': rating, 'motivo': motivo, 'comentario': comentario.strip()}
        _gravar(dados)
        return deepcopy(item)
