"""Confere quantidades de horas, inclusive por extenso, sem reescrever a fala."""
import re
import unicodedata
from decimal import Decimal

_PALAVRAS = dict(zip(
    'zero um uma dois duas tres quatro cinco seis sete oito nove dez onze doze treze quatorze catorze quinze dezesseis dezessete dezoito dezenove vinte trinta quarenta cinquenta sessenta setenta oitenta noventa cem cento duzentos duzentas trezentos trezentas quatrocentos quatrocentas quinhentos quinhentas seiscentos seiscentas setecentos setecentas oitocentos oitocentas novecentos novecentas'.split(),
    [0,1,1,2,2,3,4,5,6,7,8,9,10,11,12,13,14,14,15,16,17,18,19,20,30,40,50,60,70,80,90,100,100,200,200,300,300,400,400,500,500,600,600,700,700,800,800,900,900]))


def quantidades_horas(texto):
    texto = unicodedata.normalize('NFKD', texto).encode('ascii', 'ignore').decode().lower()
    valores = []
    for m in re.finditer(r'\bhoras?\b', texto):
        antes = texto[:m.start()].rstrip()
        numero = re.search(r'(\d+(?:[.,]\d+)?)$', antes)
        if numero:
            valores.append(Decimal(numero[1].replace(',', '.')))
            continue
        palavras = re.findall(r'\w+', antes)
        partes = []
        for palavra in reversed(palavras):
            if palavra not in _PALAVRAS and palavra not in ('e', 'mil', 'virgula'):
                break
            partes.insert(0, palavra)
        decimal = []
        if 'virgula' in partes:
            indice = partes.index('virgula')
            decimal, partes = partes[indice + 1:], partes[:indice]
        total = parcial = 0
        for palavra in partes:
            if palavra == 'mil':
                total += (parcial or 1) * 1000
                parcial = 0
            else:
                parcial += _PALAVRAS.get(palavra, 0)
        if any(p in _PALAVRAS or p == 'mil' for p in partes):
            valor = Decimal(total + parcial)
            if decimal:
                fracao = str(sum(_PALAVRAS.get(p, 0) for p in decimal))
                valor += Decimal('0.' + fracao)
            valores.append(valor)
    return valores


def horas_conferem(dados, resposta):
    permitidas = set(quantidades_horas(dados))
    return not permitidas or all(v in permitidas for v in quantidades_horas(resposta))
