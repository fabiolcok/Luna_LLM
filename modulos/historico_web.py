"""Recuperação textual de conversas anteriores; nunca abre o índice de embeddings."""
from contextlib import closing
from datetime import datetime
from hashlib import sha256
import json
import logging
import re
import sqlite3

_log = logging.getLogger(__name__)
_LINHA = re.compile(r'^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) \[INFO\] luna\.main: (.*)$')
_FALA = re.compile(r'^\[(Web texto|PC)\] (Usuário|Luna)(?: \[[^\]]+\])?: (.*)$')


def _turno(usuario, luna, data, origem, incompleto=False):
    if not luna.strip():
        return None
    assinatura = '\n'.join((data, usuario, luna))
    return {'id': 'recuperado-' + sha256(assinatura.encode()).hexdigest()[:24],
            'usuario': usuario[:4000], 'luna': luna[:16000], 'data': data,
            'tempo': data[11:16], 'cartoes_web': [], 'recuperado_de': origem,
            'incompleto': incompleto}


def _documento(texto, meta):
    if not isinstance(texto, str) or not isinstance(meta, dict):
        return None
    usuario, separador, luna = texto.partition('\nLuna: ')
    if not separador or ': ' not in usuario:
        return None
    usuario = usuario.partition(': ')[2]
    try:
        data = (datetime.fromtimestamp(float(meta['timestamp'])) if meta.get('timestamp') is not None
                else datetime.strptime(meta['data'], '%d/%m/%Y %H:%M'))
    except (ValueError, KeyError, TypeError, OSError, OverflowError):
        return None
    return _turno(usuario, luna, data.isoformat(timespec='seconds'), 'memoria')


def _do_banco(caminho):
    if not caminho.is_file():
        return []
    registros = {}
    try:
        # Usar o cliente Chroma aqui dispararia a migração e o carregamento do embedder.
        # A conexão somente leitura consulta apenas os textos já gravados, não os vetores.
        with closing(sqlite3.connect(caminho.resolve().as_uri() + '?mode=ro', uri=True, timeout=1)) as db:
            linhas = db.execute("""
                SELECT c.name, e.embedding_id, m.key, m.string_value, m.int_value, m.float_value
                FROM collections c JOIN segments s ON s.collection = c.id AND s.scope = 'METADATA'
                JOIN embeddings e ON e.segment_id = s.id
                JOIN embedding_metadata m ON m.id = e.id
                WHERE (c.name = 'historico_luna' OR c.name LIKE 'historico_luna_%')
                  AND m.key IN ('chroma:document', 'timestamp', 'data')
            """)
            for colecao, id_, chave, texto, inteiro, numero in linhas:
                registros.setdefault((colecao, id_), {})[chave] = (
                    texto if texto is not None else inteiro if inteiro is not None else numero)
    except sqlite3.Error:
        _log.warning('Não foi possível recuperar textos do histórico; os backups e o log continuam disponíveis', exc_info=True)
    return [t for meta in registros.values() if (t := _documento(meta.get('chroma:document'), meta))]


def _dos_backups(pasta):
    turnos = []
    for caminho in sorted(pasta.glob('historico-luna-*.json')):
        try:
            dados = json.loads(caminho.read_text(encoding='utf-8'))
            for doc, meta in zip(dados.get('documents', []), dados.get('metadatas', [])):
                turno = _documento(doc, meta)
                if turno:
                    turnos.append(turno)
        except (OSError, ValueError, AttributeError, TypeError):
            _log.warning('Não foi possível recuperar um backup textual de conversas', exc_info=True)
    return turnos


def _do_log(caminho):
    turnos, pendentes = [], {}
    if not caminho.is_file():
        return turnos
    # Só pares explicitamente escritos pelo main: a fala do pensar também aparece no log,
    # mas pode ser proativa ou de outro canal e não deve ser ligada à pergunta errada.
    with caminho.open(encoding='utf-8', errors='replace') as arquivo:
        for linha in arquivo:
            registro = _LINHA.match(linha.rstrip('\r\n'))
            if not registro:
                continue
            if registro[2] == 'Luna iniciando...':
                pendentes.clear()
                continue
            fala = _FALA.match(registro[2])
            if not fala:
                continue
            canal, autor, texto = fala.groups()
            if autor == 'Usuário':
                pendentes[canal] = (texto, datetime.fromisoformat(registro[1]))
                continue
            pendente = pendentes.pop(canal, None)
            data = datetime.fromisoformat(registro[1])
            if not pendente or not 0 <= (data - pendente[1]).total_seconds() <= 15 * 60:
                continue
            # As versões antigas cortavam respostas em 200 caracteres; não prometer texto completo.
            turno = _turno(pendente[0], texto, data.isoformat(timespec='seconds'), 'log', True)
            if turno:
                turnos.append(turno)
    return turnos


def recuperar_turnos(banco, backups, log):
    return _do_banco(banco) + _dos_backups(backups) + _do_log(log)
