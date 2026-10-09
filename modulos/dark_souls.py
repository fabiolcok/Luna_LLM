"""Eventos confirmados do piloto, separados da leitura de memória e do LLM."""
from collections import deque
from copy import deepcopy
import json
from itertools import count
from pathlib import Path
import tempfile
import threading
import time

RAIZ = Path(__file__).resolve().parents[1]
CONFIG = RAIZ / "modelos/dark_souls_piloto.json"
TTL = {"morte": 30, "chefe": 90, "fogueira": 60}
PRIORIDADE = {"chefe": 3, "morte": 2, "fogueira": 1}
_monitores = count(1)


def habilitado():
    try:
        return json.loads(CONFIG.read_text(encoding="utf-8")).get("ativo") is True
    except (OSError, ValueError, AttributeError):
        return False


def configurar(ativo):
    if not isinstance(ativo, bool):
        raise ValueError("A ativação deve ser verdadeiro ou falso")
    mudou = ativo != habilitado()
    CONFIG.parent.mkdir(parents=True, exist_ok=True)
    # CLI e Web escrevem a mesma preferência; temporários únicos evitam disputa entre processos.
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=CONFIG.parent,
                                     prefix="dark_souls_", suffix=".tmp", delete=False) as f:
        temporario = Path(f.name)
        json.dump({"ativo": ativo}, f)
    try:
        temporario.replace(CONFIG)
    finally:
        temporario.unlink(missing_ok=True)
    if mudou and _servico:
        with _servico.lock:
            _servico.monitor = Monitor()
            _servico.em_foco = False


class Monitor:
    def __init__(self):
        self.identidade = next(_monitores)
        self.anterior = None
        self.candidato = None
        self.ultima_leitura = 0
        self.disponivel = False
        self.mortes_sessao = 0
        self.pendentes = deque(maxlen=8)
        self.recentes = deque(maxlen=3)
        self.fogueiras_vistas = set()
        self.chefes_vistos = set()
        self.ultima_fala = -1000
        self.ultima_morte_falada = -1000
        self.geracao = 0
        self.sequencia = 0

    def indisponivel(self):
        self.disponivel = False
        self.candidato = None

    def observar(self, snapshot, agora):
        s = deepcopy(snapshot)
        # Duas leituras iguais evitam tomar flags parcialmente carregadas por progresso.
        assinatura = {k: v for k, v in s.items() if k != "tempo_jogo_ms"}
        if assinatura != self.candidato:
            self.candidato = assinatura
            return []
        antes = self.anterior
        reiniciar = (antes is None or s["sessao"] != antes["sessao"]
                     or agora - self.ultima_leitura > 30
                     or s["tempo_jogo_ms"] + 2000 < antes["tempo_jogo_ms"]
                     or s["mortes"] < antes["mortes"])
        self.anterior, self.ultima_leitura, self.disponivel = s, agora, True
        chefes = {k for k, v in s["chefes"].items() if v["derrotado"]}
        fogueiras = {k for k, v in s["fogueiras"].items() if v["estado"] >= 10}
        if reiniciar:
            self.geracao += 1
            self.pendentes.clear()
            self.recentes.clear()
            self.mortes_sessao = 0
            self.chefes_vistos, self.fogueiras_vistas = chefes, fogueiras
            return []
        eventos = []
        novas_mortes = s["mortes"] - antes["mortes"]
        self.mortes_sessao += novas_mortes
        if novas_mortes:
            eventos.append(self._evento("morte", "", agora, incremento=novas_mortes))
        for id_ in sorted(chefes - self.chefes_vistos):
            eventos.append(self._evento("chefe", s["chefes"][id_]["nome"], agora))
        for id_ in sorted(fogueiras - self.fogueiras_vistas):
            eventos.append(self._evento("fogueira", s["fogueiras"][id_]["nome"], agora))
        self.chefes_vistos |= chefes
        self.fogueiras_vistas |= fogueiras
        for evento in eventos:
            self.recentes.append(evento)
            # Uma vitória simultânea ganha a fala. A morte continua disponível no contexto.
            if evento["tipo"] == "chefe":
                self.pendentes = deque((e for e in self.pendentes if e["tipo"] == "chefe"), maxlen=8)
            self.pendentes.append(evento)
        return eventos

    def _evento(self, tipo, nome, agora, **extra):
        self.sequencia += 1
        return {"id": self.sequencia, "monitor": self.identidade, "geracao": self.geracao, "tipo": tipo,
                "nome": nome, "instante": agora, "mortes_sessao": self.mortes_sessao, **extra}

    def valido(self, e, agora):
        return not self.motivo_bloqueio(e, agora)

    def motivo_bloqueio(self, e, agora):
        if e["monitor"] != self.identidade or e["geracao"] != self.geracao:
            return "a referência do personagem ou do monitor mudou"
        if not 0 <= agora - e["instante"] <= TTL[e["tipo"]]:
            return "o evento expirou"
        if not self.disponivel or agora - self.ultima_leitura > 5:
            return "a leitura do jogo está temporariamente indisponível"
        if e["tipo"] != "chefe" and any(r["tipo"] == "chefe" and r["id"] > e["id"] for r in self.recentes):
            return "uma vitória mais recente ganhou prioridade"
        return ""

    def proximo(self, agora):
        self.pendentes = deque((e for e in self.pendentes
                                if 0 <= agora - e["instante"] <= TTL[e["tipo"]]), maxlen=8)
        if agora - self.ultima_fala < 15:
            return None
        elegiveis = [e for e in self.pendentes if self.valido(e, agora)
                     and (e["tipo"] != "morte" or agora - self.ultima_morte_falada >= 120)
                     and (e["tipo"] != "fogueira" or agora - self.ultima_fala >= 90)]
        if not elegiveis:
            return None
        evento = max(elegiveis, key=lambda e: (PRIORIDADE[e["tipo"]], e["id"]))
        self.pendentes.remove(evento)
        return deepcopy(evento)

    def entregue(self, evento, agora):
        self.ultima_fala = agora
        if evento["tipo"] == "morte":
            self.ultima_morte_falada = agora

    def contexto(self, agora):
        if not self.disponivel or agora - self.ultima_leitura > 5:
            return None
        return {"jogo": self.anterior["jogo"], "mortes_sessao": self.mortes_sessao,
                "eventos": [dict(e, idade_s=int(agora - e["instante"]))
                            for e in self.recentes if 0 <= agora - e["instante"] <= 180]}


class Servico:
    def __init__(self, pode_falar, falar, registrar=print):
        self.monitor = Monitor()
        self.lock = threading.RLock()
        self.stop = threading.Event()
        self.pode_falar, self.falar, self.registrar = pode_falar, falar, registrar
        self.em_foco = False
        self.threads = []

    def iniciar(self):
        if self.threads:
            return
        for funcao in (self._coletar, self._comentar):
            t = threading.Thread(target=funcao, daemon=True, name="luna-dark-souls")
            self.threads.append(t)
            t.start()

    def contexto(self):
        with self.lock:
            return self.monitor.contexto(time.time()) if habilitado() else None

    def _coletar(self):
        from integracoes.dark_souls.leitor import LeitorRemastered
        leitor = LeitorRemastered()
        erro_anterior = None
        try:
            while not self.stop.is_set():
                if not habilitado():
                    leitor.close()
                    with self.lock:
                        self.monitor = Monitor()
                        self.em_foco = False
                    self.stop.wait(2)
                    continue
                try:
                    s = leitor.snapshot()
                    foco = leitor.em_foco()
                    with self.lock:
                        self.em_foco = foco
                        eventos = self.monitor.observar(s, time.time())
                    if erro_anterior is not False:
                        self.registrar("[Dark Souls: leitura conectada; progresso anterior é a referência]")
                    erro_anterior = False
                    for e in eventos:
                        rotulo = {"chefe": "chefe derrotado", "morte": "morte", "fogueira": "fogueira liberada"}[e["tipo"]]
                        self.registrar(f"[Dark Souls: {rotulo} | {e['nome'] or 'contador aumentou'}]")
                except Exception as exc:
                    erro = str(exc)
                    with self.lock:
                        self.em_foco = False
                        self.monitor.indisponivel()
                    if erro != erro_anterior:
                        self.registrar(f"[Dark Souls: aguardando leitura — {erro}]")
                        erro_anterior = erro
                self.stop.wait(1)
        finally:
            leitor.close()
            with self.lock:
                self.monitor.indisponivel()

    def _valido(self, evento):
        return not self._motivo_bloqueio(evento)

    def _motivo_bloqueio(self, evento):
        with self.lock:
            if self.stop.is_set() or not habilitado():
                return "o piloto foi desligado"
            motivo = self.monitor.motivo_bloqueio(evento, time.time())
            if motivo:
                return motivo
            if not self.em_foco:
                return "o jogo saiu do primeiro plano"
            if not self.pode_falar():
                return "a conversa tem prioridade ou os comentários foram pausados"
            return ""

    def _entregar(self, evento):
        def validar():
            validar.motivo = self._motivo_bloqueio(evento)
            return not validar.motivo
        validar.motivo = ""
        if self.falar(evento, validar):
            with self.lock:
                self.monitor.entregue(evento, time.time())
            self.registrar(f"[Dark Souls: comentário de {evento['tipo']} entregue]")
        else:
            motivo = validar.motivo or self._motivo_bloqueio(evento) or "geração/entrega não concluída; consulte o diagnóstico acima"
            self.registrar(f"[Dark Souls: comentário de {evento['tipo']} não entregue — {motivo}]")

    def _comentar(self):
        while not self.stop.wait(1):
            if not habilitado() or not self.pode_falar():
                with self.lock:
                    self.monitor.pendentes.clear()
                continue
            with self.lock:
                evento = self.monitor.proximo(time.time()) if self.em_foco else None
            if evento:
                try:
                    self._entregar(evento)
                except Exception as exc:
                    self.registrar(f"[Dark Souls: comentário descartado — {exc}]")


_servico = None


def iniciar(pode_falar, falar, registrar=print):
    global _servico
    if _servico is None:
        _servico = Servico(pode_falar, falar, registrar)
        _servico.iniciar()


def parar():
    global _servico
    if _servico:
        _servico.stop.set()
        _servico = None


def contexto():
    return _servico.contexto() if _servico else None
