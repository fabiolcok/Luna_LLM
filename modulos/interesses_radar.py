"""Preferências explícitas por palavras: alteram o destaque, não a coleta do RSS."""
import json
import logging
from pathlib import Path
import random
import re
import threading
import unicodedata

CAMINHO = Path('modelos/interesses_radar.json')
_trava = threading.RLock()
_IGNORAR = set('a o as os um uma de do da dos das em no na nos nas e ou para por com the of in and to for'.split())


def _normalizar(texto):
    return ''.join(c for c in unicodedata.normalize('NFKD', texto.casefold()) if not unicodedata.combining(c))


def _termos(texto):
    return [t for t in re.findall(r'\w+', _normalizar(texto)) if t not in _IGNORAR]


def validar_assunto(assunto):
    if not isinstance(assunto, str):
        raise ValueError('Informe um assunto ou palavra-chave.')
    assunto = re.sub(r'\s+', ' ', assunto).strip()
    termos = _termos(assunto)
    if (not 2 <= len(assunto) <= 80 or not 1 <= len(termos) <= 8
            or re.search(r'[<>\[\]{}\x00-\x1f]|https?://', assunto, re.I)):
        raise ValueError('Use uma palavra-chave ou assunto curto, como OLED ou voz local.')
    return assunto


def _carregar():
    if not CAMINHO.exists():
        return []
    try:
        itens = json.loads(CAMINHO.read_text(encoding='utf8'))
        if (not isinstance(itens, list) or len(itens) > 20 or any(not isinstance(i, dict) or
                i.get('preferencia') not in {'mais', 'menos'} or validar_assunto(i.get('assunto')) != i['assunto']
                for i in itens)):
            raise ValueError
        return itens
    except (ValueError, OSError, TypeError):
        raise ValueError('Não consegui ler os interesses do radar; o arquivo foi preservado.') from None


def estado_interface():
    try:
        with _trava:
            return {'itens': _carregar()}
    except ValueError as e:
        return {'itens': [], 'erro': str(e)}


def agir(acao, assunto):
    try:
        assunto = validar_assunto(assunto)
        if acao not in {'mais', 'menos', 'remover'}:
            raise ValueError('Preferência inválida.')
        with _trava:
            itens = _carregar()
            chave = _termos(assunto)
            itens = [i for i in itens if _termos(i['assunto']) != chave]
            if acao != 'remover':
                if len(itens) >= 20:
                    raise ValueError('Remova um interesse antes de adicionar outro; o limite é vinte.')
                itens.append({'assunto': assunto, 'preferencia': acao})
            CAMINHO.parent.mkdir(parents=True, exist_ok=True)
            tmp = CAMINHO.with_suffix('.tmp')
            tmp.write_text(json.dumps(itens, ensure_ascii=False, indent=2), encoding='utf8')
            tmp.replace(CAMINHO)
        return {'ok': True, 'texto': f'Preferência removida: {assunto}.' if acao == 'remover' else
                f'{"Mais" if acao == "mais" else "Menos"} destaque para notícias com: {assunto}.'}
    except (ValueError, OSError) as e:
        return {'ok': False, 'texto': str(e)}


def pesos(novidades, preferencias):
    retorno = []
    for n in novidades:
        texto = set(_termos(n[0] + ' ' + n[3]))
        score = sum((1 if p['preferencia'] == 'mais' else -1) for p in preferencias
                    if set(_termos(p['assunto'])).issubset(texto))
        retorno.append(5 ** max(-2, min(2, score)))
    return retorno


def escolher(novidades, rng=random):
    estado = estado_interface()
    if estado.get('erro'):
        logging.getLogger(__name__).warning(estado['erro'])
    preferencias = estado['itens']
    # Sem interesses, mantém o sorteio anterior. Menos interesse nunca apaga notícias.
    return rng.choices(novidades, weights=pesos(novidades, preferencias), k=1)[0] if preferencias else rng.choice(novidades)
