"""Arquivo local de consulta; não participa da memória nem do contexto automático do LLM."""
from contextvars import ContextVar
from copy import deepcopy
from datetime import datetime
from hashlib import sha256
import json
import logging
from pathlib import Path
import re
import threading
import unicodedata

from modulos.cartoes_web import normalizar, imagem_promocao

ARQUIVO = Path(__file__).resolve().parents[1] / 'logs' / 'biblioteca_web.json'
LOG_ANTIGO = ARQUIVO.parent / 'luna.log'
BANCO_ANTIGO = ARQUIVO.parents[1] / 'modelos' / 'chromadb' / 'chroma.sqlite3'
BACKUPS_ANTIGOS = ARQUIVO.parents[1] / 'modelos' / 'backups_embeddings'
MAX_TURNOS = 1000
MAX_ITENS = 300
_trava = threading.RLock()
contexto_resposta = ContextVar('contexto_resposta_web', default=None)


def _ler():
    try:
        dados = json.loads(ARQUIVO.read_text(encoding='utf-8'))
        if isinstance(dados, dict) and isinstance(dados.get('turnos'), list) and isinstance(dados.get('itens'), list):
            return dados
    except FileNotFoundError:
        pass
    except (OSError, ValueError):
        logging.getLogger(__name__).exception('Não foi possível ler o arquivo de consulta da web')
    return {'turnos': [], 'itens': [], 'notas_importadas': False}


def _gravar(dados):
    # A troca atômica evita um arquivo pela metade se a energia cair durante uma fala.
    ARQUIVO.parent.mkdir(parents=True, exist_ok=True)
    temporario = ARQUIVO.with_suffix('.tmp')
    temporario.write_text(json.dumps(dados, ensure_ascii=False), encoding='utf-8')
    temporario.replace(ARQUIVO)


def _texto(valor, limite):
    return valor[:limite] if isinstance(valor, str) else ''


def _chave(texto):
    return ''.join(c for c in unicodedata.normalize('NFKD', texto.casefold()) if not unicodedata.combining(c))


def _incluir_itens(dados, cartoes, data=None):
    for cartao in cartoes:
        if cartao.get('tipo') not in ('noticia', 'promocao'):
            continue
        identificador = sha256((cartao['tipo'] + '\n' + (cartao.get('url') or cartao['titulo'])).encode()).hexdigest()[:24]
        anterior = next((i for i in dados['itens'] if i['id'] == identificador), None)
        if anterior:
            # Atualizar o resumo ou a capa não transforma um item lido em novidade outra vez.
            anterior.update({k: v for k, v in cartao.items() if v and k not in ('mais', 'sugestoes')})
        else:
            dados['itens'].append({**cartao, 'id': identificador, 'lido': False,
                                   'data': data or datetime.now().isoformat(timespec='seconds')})
    dados['itens'].sort(key=lambda i: i.get('data', ''))
    dados['itens'] = dados['itens'][-MAX_ITENS:]


def registrar_itens(itens, tipo):
    if tipo not in ('noticia', 'promocao'):
        return
    cartoes = []
    for item in itens:
        if not isinstance(item, (list, tuple)) or len(item) < 3:
            continue
        imagem = item[4] if len(item) > 4 else ''
        if tipo == 'promocao' and imagem and not imagem.startswith(('https://', 'http://', '/imagens/')):
            imagem = imagem_promocao(imagem)
        cartoes.extend(normalizar([{'tipo': tipo, 'titulo': item[0], 'url': item[1], 'fonte': item[2],
                                   'resumo': item[3] if len(item) > 3 else '', 'imagem': imagem}]))
    with _trava:
        dados = _ler()
        _incluir_itens(dados, cartoes)
        _gravar(dados)


def registrar_turno(turno):
    if not isinstance(turno.get('id'), str) or not turno.get('luna'):
        return
    salvo = {k: _texto(turno.get(k), limite) for k, limite in
             [('id', 80), ('usuario', 4000), ('luna', 16000), ('tempo', 10), ('origem_proativa', 100), ('clima', 30)]}
    salvo['data'] = turno.get('data') or datetime.now().isoformat(timespec='seconds')
    salvo['cartoes_web'] = normalizar(turno.get('cartoes_web'))
    if turno.get('resposta_a'):
        salvo['resposta_a'] = deepcopy(turno['resposta_a'])
    with _trava:
        dados = _ler()
        dados['turnos'] = [t for t in dados['turnos'] if t['id'] != salvo['id']]
        dados['turnos'].append(salvo)
        dados['turnos'] = dados['turnos'][-MAX_TURNOS:]
        _incluir_itens(dados, salvo['cartoes_web'], salvo['data'])
        links = turno.get('links_novidades') or {}
        if isinstance(links, dict) and isinstance(links.get('ofertas'), list):
            for oferta in links['ofertas'][:100]:
                if isinstance(oferta, dict):
                    _incluir_itens(dados, normalizar([{'tipo': 'promocao', 'titulo': oferta.get('rotulo'),
                        'url': oferta.get('url'), 'fonte': 'Steam' if turno.get('origem_proativa') == 'steam_wishlist' else ''}]), salvo['data'])
        _gravar(dados)


def importar_notas(vault):
    """Recupera os callouts existentes, sem consultar sites ou reprocessar com o LLM."""
    if not vault or not Path(vault).is_dir():
        return
    with _trava:
        dados = _ler()
        if dados.get('notas_importadas'):
            return
        for nome, tipo in [('Novidades.md', 'noticia'), ('Promocoes.md', 'promocao')]:
            caminho = Path(vault) / nome
            if not caminho.is_file():
                continue
            with caminho.open(encoding='utf-8') as f:
                texto = f.read(2_000_000)
            data = datetime.now().isoformat(timespec='seconds')
            cartao = None
            importados = []
            for linha in texto.splitlines():
                if linha.startswith('## '):
                    try:
                        data = datetime.strptime(linha[3:13], '%d/%m/%Y').isoformat()
                    except ValueError:
                        pass
                elif linha.startswith('> [!tip]+ '):
                    cartao = None
                    bloco = linha[10:]
                    titulo = re.match(r'\[(.+)\]\((https?://[^\s]+)\)$', bloco)
                    if titulo:
                        cartao = {'tipo': tipo, 'titulo': titulo[1], 'url': titulo[2], 'fonte': '', 'resumo': '', 'imagem': ''}
                        importados.append((cartao, data))
                elif linha.startswith('> ') and cartao is not None:
                    corpo = linha[2:]
                    if corpo.startswith('`') and corpo.endswith('`'):
                        cartao['fonte'] = corpo.strip('`')
                    elif corpo.startswith('![|220](') and corpo.endswith(')'):
                        cartao['imagem'] = corpo[8:-1]
                    elif corpo.startswith('![[') and corpo.endswith('|220]]'):
                        cartao['imagem'] = imagem_promocao(corpo[3:-6])
                    elif not corpo.startswith('!['):
                        cartao['resumo'] += ' ' + corpo
            for cartao, data in reversed(importados):
                _incluir_itens(dados, normalizar([cartao]), data)
        dados['notas_importadas'] = True
        _gravar(dados)


def importar_conversas():
    """Importa uma vez os textos existentes, preservando IDs e falas completas da web."""
    from modulos.historico_web import recuperar_turnos
    with _trava:
        dados = _ler()
        if dados.get('conversas_importadas'):
            return
        recuperados = recuperar_turnos(BANCO_ANTIGO, BACKUPS_ANTIGOS, LOG_ANTIGO)
        # As fontes completas entram antes dos trechos do log. A mesma resposta foi registrada
        # no Chroma e no main; não transformar essa duplicação em duas conversas na busca.
        for turno in recuperados:
            duplicado = None
            for anterior in dados['turnos']:
                if anterior['id'] == turno['id']:
                    duplicado = anterior
                    break
                if anterior.get('usuario') != turno['usuario']:
                    continue
                fala = anterior.get('luna', '')
                coincide = fala == turno['luna'] or (turno['incompleto'] and len(turno['luna']) >= 60
                            and fala.startswith(turno['luna']))
                if not coincide:
                    continue
                try:
                    perto = abs((datetime.fromisoformat(anterior['data'])
                                 - datetime.fromisoformat(turno['data'])).total_seconds()) <= 10
                except (KeyError, ValueError, TypeError):
                    perto = False
                if perto:
                    duplicado = anterior
                    break
            if not duplicado:
                dados['turnos'].append(turno)
        dados['turnos'].sort(key=lambda t: t.get('data', ''))
        dados['turnos'] = dados['turnos'][-MAX_TURNOS:]
        dados['conversas_importadas'] = True
        _gravar(dados)


def consultar(*, modo='itens', tipo='', leitura='', busca='', inicio=0):
    with _trava:
        dados = _ler()
    termos = _chave(_texto(busca, 100)).split()
    registros = dados['turnos' if modo == 'historico' else 'itens']
    nao_lidas = sum(not i.get('lido') for i in dados['itens'])
    selecionados = []
    for item in reversed(registros):
        if modo != 'historico':
            if tipo in ('noticia', 'promocao') and item['tipo'] != tipo:
                continue
            if leitura == 'nao_lidas' and item.get('lido') or leitura == 'lidas' and not item.get('lido'):
                continue
        conteudo = _chave(' '.join(str(item.get(k, '')) for k in ('usuario', 'luna', 'titulo', 'fonte', 'resumo')))
        if all(t in conteudo for t in termos):
            selecionados.append(item)
    inicio = max(0, min(inicio, len(selecionados)))
    return {'itens': selecionados[inicio:inicio + 30], 'total': len(selecionados),
            'inicio': inicio, 'mais': inicio + 30 < len(selecionados), 'nao_lidas': nao_lidas}


def marcar_leitura(identificador, lido):
    if type(lido) is not bool:
        return False
    with _trava:
        dados = _ler()
        item = next((i for i in dados['itens'] if i['id'] == identificador), None)
        if not item:
            return False
        item['lido'] = lido
        _gravar(dados)
    return True


def resolver_resposta(referencia, recentes):
    """O navegador envia somente o id; texto, fonte e URL são recuperados no servidor."""
    if not isinstance(referencia, dict) or set(referencia) not in ({'turno_id'}, {'item_id'}):
        return None
    chave = next(iter(referencia))
    identificador = referencia[chave]
    if not isinstance(identificador, str) or not 1 <= len(identificador) <= 80:
        return None
    with _trava:
        dados = _ler()
    registros = [*recentes, *dados['turnos']] if chave == 'turno_id' else dados['itens']
    item = next((t for t in registros if t.get('id') == identificador), None)
    if not item:
        return None
    cartoes = normalizar(item.get('cartoes_web')) if chave == 'turno_id' else normalizar([item])
    noticia = next((c for c in cartoes if c['tipo'] == 'noticia'), None)
    contexto = {'referencia': dict(referencia), 'usuario': _texto(item.get('usuario'), 300),
                'luna': _texto(item.get('luna') or item.get('titulo'), 1200),
                'cartoes': [{k: c.get(k, '') for k in ('tipo', 'titulo', 'url', 'fonte', 'resumo')}
                            for c in cartoes if c['tipo'] in ('noticia', 'promocao')]}
    if item.get('incompleto'):
        contexto['trecho_incompleto'] = True
    return contexto, ({k: noticia.get(k, '') for k in ('titulo', 'fonte', 'url', 'resumo')} if noticia else None)
