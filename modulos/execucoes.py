"""Uma vez por turno; resultados de trabalhos cancelados não têm mais dono."""

from collections import deque
from contextlib import contextmanager
from contextvars import ContextVar, copy_context
from dataclasses import dataclass, field
from functools import wraps
import threading
import time


class ExecucaoCancelada(Exception):
    pass


@dataclass(eq=False)
class Execucao:
    numero: int
    proativa: bool
    cancelada: threading.Event = field(default_factory=threading.Event)
    # Avisos já apresentados não voltam à fila quando o usuário corta o áudio.
    intervalos_confirmados: dict = field(default_factory=dict)


class Coordenador:
    def __init__(self, pausa=30.0):
        self.condicao = threading.Condition(threading.RLock())
        self.atual = None
        self.fila = deque()
        self.numero = 0
        self.pausa = pausa
        self.retomar_em = 0.0
        self.parar_audio = None
        self.contexto = ContextVar("execucao_luna", default=None)

    def _nova(self, proativa):
        self.numero += 1
        return Execucao(self.numero, proativa)

    def _ceder(self):
        self.retomar_em = time.monotonic() + self.pausa
        if self.atual and self.atual.proativa:
            self.atual.cancelada.set()
            # Executado sob a mesma trava que autoriza o início do áudio: não pode
            # parar por engano a fala do turno seguinte.
            if self.parar_audio:
                try:
                    self.parar_audio()
                except Exception:
                    # Dispositivo de som ausente não pode impedir a reserva do chat.
                    pass

    def avisar_usuario(self):
        with self.condicao:
            self._ceder()

    def reservar(self):
        with self.condicao:
            turno = self._nova(False)
            self.fila.append(turno)
            self._ceder()
            return turno

    def valida(self, turno):
        return turno is None or (self.atual is turno and not turno.cancelada.is_set())

    def verificar(self):
        with self.condicao:
            if not self.valida(self.contexto.get()):
                raise ExecucaoCancelada("Execução substituída pela conversa do usuário")

    def vigiar_stream(self, resposta):
        try:
            for parte in resposta:
                self.verificar()
                yield parte
        finally:
            resposta.close()

    @contextmanager
    def executar(self, turno=None, *, proativa=False):
        anterior = self.contexto.get()
        if anterior is not None:
            self.verificar()
            yield anterior
            return
        with self.condicao:
            if proativa:
                if self.atual or self.fila or time.monotonic() < self.retomar_em:
                    raise ExecucaoCancelada("Conversa tem prioridade")
                turno = self._nova(True)
            else:
                turno = turno or self.reservar()
                try:
                    self.condicao.wait_for(lambda: self.atual is None and self.fila[0] is turno)
                except BaseException:
                    self.fila.remove(turno)
                    self.condicao.notify_all()
                    raise
                self.fila.popleft()
            self.atual = turno
        contexto = self.contexto.set(turno)
        try:
            yield turno
        finally:
            self.contexto.reset(contexto)
            with self.condicao:
                if self.atual is turno:
                    self.atual = None
                    if not turno.proativa:
                        self.retomar_em = time.monotonic() + self.pausa
                self.condicao.notify_all()

    def efeito(self, fn):
        @wraps(fn)
        def protegido(*args, **kwargs):
            with self.condicao:
                if self.valida(self.contexto.get()):
                    return fn(*args, **kwargs)
        return protegido


controle = Coordenador()


def vincular(fn):
    contexto = copy_context()
    return lambda *a, **k: contexto.run(fn, *a, **k)


def conversa(fn):
    @wraps(fn)
    def executar(*args, **kwargs):
        with controle.executar():
            return fn(*args, **kwargs)

    def preparar(*args, **kwargs):
        # A reserva nasce no recebimento Web, antes de a thread disputar a CPU.
        turno = controle.reservar()
        def reservado():
            with controle.executar(turno):
                return fn(*args, **kwargs)
        return reservado

    executar.preparar = preparar
    return executar
