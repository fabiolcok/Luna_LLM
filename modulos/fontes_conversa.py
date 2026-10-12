"""Rascunhos do chat: só a confirmação do usuário cadastra uma consulta de fontes."""
from copy import deepcopy
import json
from pathlib import Path
import re
import threading
import time
import unicodedata
from urllib.parse import urlsplit
import uuid

from modulos import acompanhamento_fontes as monitor
from modulos.cartoes_web import TextoComCartoes, acompanhamento

CAMINHO = Path("modelos/propostas_fontes.json")
_trava = threading.RLock()
VALIDADE = 7 * 86400


def urls_do_pedido(texto):
    urls = []
    for u in re.findall(r'https?://[^\s<>"\[\]]+', texto or "", re.I):
        u = u.rstrip(".,;!?")
        while u.endswith(')') and u.count(')') > u.count('('):
            u = u[:-1]
        try:
            urls.append(monitor.validar_url(u))
        except ValueError:
            continue
    return list(dict.fromkeys(urls))


def eh_pedido(texto):
    # O histórico e os artigos não autorizam um monitor; a intenção vem deste turno.
    t = ''.join(c for c in unicodedata.normalize('NFKD', texto or '') if not unicodedata.combining(c)).lower()
    t = re.sub(r'https?://\S+', '', t)
    if re.search(r'\b(nao|nunca|pare de|parar de|cancel[ae]|desativ[ae])\b.{0,35}\b(acompanh\w*|monitor\w*|avis\w*)', t):
        return False
    acao = re.search(r'(?:^\s*(?:luna[,\s:]+)?|[.!?]\s*|\b(?:pode|poderia|quero|gostaria|preciso)\b.{0,30})'
                     r'(?:acompanha(?:r|sse)?|acompanhe|monitora(?:r)?|monitore|me avis[ae]|me avisar)\b', t)
    if acao and re.search(r'\bme avis', acao.group(0)) and not re.search(r'\bquando\b|assim que', t):
        return False
    return bool(acao and urls_do_pedido(texto))


def _carregar():
    if not CAMINHO.exists():
        return []
    try:
        itens = json.loads(CAMINHO.read_text(encoding='utf8'))
        if not isinstance(itens, list) or len(itens) > 31 or any(not isinstance(i, dict) or not
                {'id', 'status', 'criado_em', 'cadastro'}.issubset(i) or
                not isinstance(i['id'], str) or not re.fullmatch(r'[a-f0-9]{16}', i['id']) or
                i['status'] not in {'pendente', 'confirmado', 'descartado'} or
                type(i['criado_em']) not in {int, float} or not isinstance(i['cadastro'], dict) or
                not all(isinstance(i['cadastro'].get(k), str) for k in ('assunto', 'interesse', 'situacao')) or
                not isinstance(i['cadastro'].get('fontes'), list) or not 1 <= len(i['cadastro']['fontes']) <= 3 or
                any(u != monitor.validar_url(u) for u in i['cadastro']['fontes']) for i in itens):
            raise ValueError
        return itens
    except (ValueError, OSError, TypeError):
        raise ValueError("Não consegui ler os rascunhos salvos; o arquivo foi preservado.") from None


def _salvar(itens):
    CAMINHO.parent.mkdir(parents=True, exist_ok=True)
    tmp = CAMINHO.with_suffix('.tmp')
    tmp.write_text(json.dumps(itens, ensure_ascii=False, indent=2), encoding='utf8')
    tmp.replace(CAMINHO)


def _status(item):
    return 'expirado' if item['status'] == 'pendente' and time.time() - item['criado_em'] > VALIDADE else item['status']


def estado_interface():
    try:
        with _trava:
            return {'itens': [{**deepcopy(i), 'status': _status(i)} for i in _carregar()]}
    except ValueError as e:
        return {'itens': [], 'erro': str(e)}


def propor(pedido_usuario='', assunto='', interesse='', situacao=''):
    try:
        if not eh_pedido(pedido_usuario):
            raise ValueError('Peça para acompanhar uma mudança e informe o link público da fonte.')
        urls = urls_do_pedido(pedido_usuario)
        if len(urls) > 3:
            raise ValueError('Use no máximo três fontes por acompanhamento.')
        cadastro = {'assunto': monitor._texto(assunto, 120) or urlsplit(urls[0]).hostname,
                    'interesse': monitor._texto(interesse, 400),
                    'situacao': monitor._texto(situacao, 300), 'fontes': urls}
        if re.search(r'https?://', cadastro['assunto'], re.I):
            cadastro['assunto'] = urlsplit(urls[0]).hostname
        pedido_literal = monitor._texto(pedido_usuario, len(pedido_usuario)).casefold()
        for campo in ('interesse', 'situacao'):
            # O Gemma completou um interesse ausente com "acompanhar mudanças". O cartão
            # usa apenas trechos verificáveis, e deixa faltas para o usuário preencher.
            if cadastro[campo].casefold() not in pedido_literal or re.search(r'https?://', cadastro[campo], re.I):
                cadastro[campo] = ''
        if re.search(r'pt.?br|brasil|brasileir', cadastro['interesse'], re.I):
            from modulos import acompanhamento_sopro as sopro
            fontes_sopro = {f['url'].rstrip('/') for f in sopro.FONTES}
            if any(u.rstrip('/') in fontes_sopro for u in urls):
                existente = sopro.estado_interface()
                if existente['status'] in {'ativo', 'pausado'}:
                    return TextoComCartoes('O acompanhamento do Sopro para PT-BR já está cadastrado. Confira o cartão existente.',
                        [acompanhamento('sopro', {**existente, 'id': 'sopro_ptbr', 'assunto': 'Sopro · suporte PT-BR'})])
        with _trava:
            existentes = monitor.estado_interface()
            if existentes.get('erro'):
                raise ValueError(existentes['erro'])
            for existente in existentes['itens']:
                if (existente['status'] != 'encerrado' and set(existente['fontes']) == set(urls)
                        and existente['interesse'].casefold() == cadastro['interesse'].casefold()):
                    return TextoComCartoes('Esse acompanhamento já está cadastrado. Confira o cartão existente.',
                                           [acompanhamento('fontes', existente)])
            itens = _carregar()
            item = next((i for i in itens if _status(i) == 'pendente' and i['cadastro'] == cadastro), None)
            if not item:
                pendentes = [i for i in itens if _status(i) == 'pendente']
                if len(pendentes) >= 10:
                    raise ValueError('Confirme ou descarte um dos rascunhos antes de preparar outro.')
                itens = pendentes + [i for i in itens if _status(i) != 'pendente'][-20:]
                item = {'id': uuid.uuid4().hex[:16], 'status': 'pendente',
                        'criado_em': time.time(), 'cadastro': cadastro}
                itens.append(item)
                _salvar(itens)
        monitor._notificar()
        return TextoComCartoes('Rascunho preparado no cartão. Confira o assunto, a mudança e os links; '
                               'a consulta só começa depois de clicar em Confirmar acompanhamento.' +
                               (' Falta a mudança de interesse; preencha esse campo no cartão.' if not cadastro['interesse'] else ''),
            [{'tipo': 'proposta_fonte', 'id': item['id'], 'titulo': cadastro['assunto'], **cadastro}])
    except (ValueError, OSError) as e:
        return 'Erro: ' + str(e)


def resolver(acao, identificador, cadastro=None):
    try:
        with _trava:
            itens = _carregar()
            item = next((i for i in itens if i['id'] == identificador), None)
            if not item or _status(item) == 'expirado':
                raise ValueError('Esse rascunho expirou. Peça outro na conversa.')
            if item['status'] == 'confirmado':
                return {'ok': True, 'texto': 'Esse acompanhamento já foi confirmado.', 'id': identificador}
            if item['status'] != 'pendente':
                raise ValueError('Esse rascunho já foi descartado.')
            if acao == 'descartar':
                item['status'] = 'descartado'
                resposta = {'ok': True, 'texto': 'Rascunho descartado.', 'id': identificador}
            elif acao == 'confirmar':
                c = monitor.validar_cadastro(cadastro)
                resposta = monitor.agir('criar', cadastro=c, criacao_id='chat_' + identificador)
                if not resposta['ok']:
                    return {**resposta, 'id': identificador}
                salvo = next(i for i in monitor.estado_interface()['itens'] if i['id'] == resposta['id'])
                item.update(status='confirmado', cadastro={k: salvo[k] for k in c}, acompanhamento_id=resposta['id'])
                resposta['id'] = identificador
            else:
                raise ValueError('Ação de rascunho inválida.')
            _salvar(itens)
        monitor._notificar()
        return resposta
    except (ValueError, OSError) as e:
        return {'ok': False, 'texto': str(e), 'id': identificador}
