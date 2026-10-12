"""Eventos confirmados pelo Google Calendar para os cartões e avisos da Luna."""
import datetime as dt


def data(valor, dia_inteiro=False):
    if not isinstance(valor, str):
        return ''
    try:
        if dia_inteiro:
            return dt.date.fromisoformat(valor).isoformat()
        instante = dt.datetime.fromisoformat(valor.replace('Z', '+00:00'))
        if instante.tzinfo is None:
            return ''
        return instante.astimezone().isoformat()
    except ValueError:
        return ''


def normalizar_eventos(eventos):
    from modulos.cartoes_web import _texto, _url
    if not isinstance(eventos, list):
        return []
    retorno = []
    for evento in eventos:
        if not isinstance(evento, dict):
            continue
        inteiro = evento.get('dia_inteiro') is True
        inicio = data(evento.get('inicio'), inteiro)
        if not inicio:
            continue
        fim = data(evento.get('fim'), inteiro)
        if fim and fim <= inicio:
            fim = ''
        retorno.append({'titulo': _texto(evento.get('titulo'), 240) or 'Sem título',
            'inicio': inicio, 'fim': fim, 'dia_inteiro': inteiro,
            'local': _texto(evento.get('local'), 240), 'url': _url(evento.get('url'))})
    return sorted(retorno, key=lambda e: (e['inicio'][:10], not e['dia_inteiro'], e['inicio']))


def eventos_google(eventos):
    dados = []
    for evento in eventos if isinstance(eventos, list) else []:
        if not isinstance(evento, dict) or evento.get('status') == 'cancelled':
            continue
        inicio, fim = evento.get('start') or {}, evento.get('end') or {}
        if not isinstance(inicio, dict) or not isinstance(fim, dict):
            continue
        dados.append({'titulo': evento.get('summary'), 'local': evento.get('location'),
            'url': evento.get('htmlLink'), 'dia_inteiro': bool(inicio.get('date')),
            'inicio': inicio.get('date') or inicio.get('dateTime'),
            'fim': fim.get('date') or fim.get('dateTime')})
    return normalizar_eventos(dados)


def resultado(texto, eventos, titulo='Agenda', inicio='', fim='', mais=False):
    from modulos import cartoes_web
    todos = normalizar_eventos(eventos)
    fala = cartoes_web.TextoComCartoes(texto, [{'tipo': 'agenda', 'titulo': titulo,
        'eventos': todos[:50], 'total': len(todos), 'mais': mais,
        'inicio_periodo': inicio, 'fim_periodo': fim}])
    # A interface é limitada; o monitor ainda precisa de todos os eventos recebidos.
    fala.eventos_agenda = todos
    return fala


def eventos_do_dia(eventos, dia):
    retorno = []
    for evento in eventos:
        inicio = evento['inicio'][:10]
        if evento['dia_inteiro']:
            fim = evento['fim'] or (dt.date.fromisoformat(inicio) + dt.timedelta(days=1)).isoformat()
            if inicio <= dia.isoformat() < fim:
                retorno.append(evento)
        else:
            # Um compromisso que cruza meia-noite também ocupa parte do dia seguinte.
            fim = evento['fim'] or evento['inicio']
            fim_dia = dt.datetime.fromisoformat(fim)
            if evento['fim']:
                fim_dia -= dt.timedelta(microseconds=1)
            if inicio <= dia.isoformat() <= fim_dia.date().isoformat():
                retorno.append(evento)
    return retorno


def proximos(eventos, agora, antecedencia):
    agora = agora.astimezone()
    retorno = []
    for evento in eventos:
        if evento['dia_inteiro']:
            if eventos_do_dia([evento], agora.date()):
                retorno.append((evento, 'hoje'))
        else:
            minutos = (dt.datetime.fromisoformat(evento['inicio']) - agora).total_seconds() / 60
            if 0 <= minutos <= antecedencia:
                retorno.append((evento, f'em {int(minutos)} min'))
    return retorno
