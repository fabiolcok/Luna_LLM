"""Separa texto incremental em frases estáveis para o TTS, sem depender do motor de voz."""

import re


_FIM_FRASE = re.compile(r'([.!?]+(?:["”’\)\]]+)?)(?=\s+)')
_ABREVIACOES = {
    "sr", "sra", "srta", "dr", "dra", "prof", "profa", "etc", "ex", "obs",
}


class SegmentadorFrases:
    """Recebe versões cumulativas do stream e devolve cada frase uma única vez."""

    def __init__(self):
        self._texto = ""
        self._corte = 0
        self._finalizado = False

    def receber(self, texto: str) -> list[str]:
        if self._finalizado:
            return []
        texto = texto or ""
        # O callback é cumulativo. Se um provedor recomeçar o texto, reancora sem repetir
        # o que já foi entregue; no fluxo normal este ramo nunca é necessário.
        if len(texto) < self._corte:
            return []
        self._texto = texto
        return self._extrair_completas()

    def finalizar(self, texto: str) -> list[str]:
        if self._finalizado:
            return []
        self._texto = texto or self._texto
        frases = self._extrair_completas()
        restante = self._texto[self._corte:].strip()
        if restante:
            frases.append(restante)
            self._corte = len(self._texto)
        self._finalizado = True
        return frases

    def _extrair_completas(self) -> list[str]:
        frases = []
        for achado in _FIM_FRASE.finditer(self._texto, self._corte):
            fim = achado.end(1)
            candidata = self._texto[self._corte:fim].strip()
            if not candidata or self._eh_abreviacao(candidata):
                continue
            frases.append(candidata)
            self._corte = fim
            while self._corte < len(self._texto) and self._texto[self._corte].isspace():
                self._corte += 1
        return frases

    @staticmethod
    def _eh_abreviacao(texto: str) -> bool:
        if not texto.endswith('.') or texto.endswith('..'):
            return False
        palavra = re.search(r'([A-Za-zÀ-ÿ]+)\.$', texto)
        if palavra and palavra.group(1).lower() in _ABREVIACOES:
            return True
        # Uma inicial isolada ("F. de Souza") também não encerra frase.
        return bool(re.search(r'(?:^|\s)[A-ZÀ-Ý]\.$', texto))
