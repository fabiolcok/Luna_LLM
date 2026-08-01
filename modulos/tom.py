# tom.py — le o TOM da voz (arousal/energia) via SER acustico
# (audeering/wav2vec2-large-robust-12-ft-emotion-msp-dim), mantem uma BASELINE MOVEL do
# arousal tipico do usuario e arma uma DICA SUTIL pro prompt da persona SO quando o tom
# desvia NOTAVELMENTE do normal dele.
#
# - Roda na CPU, lazy-load (~660MB na RAM), em thread (nao trava a resposta).
# - SO no canal de VOZ (Telegram/web nao tem audio). Espera 16kHz mono float32.
# - Regra de ouro: colore o COMO, nunca vira o assunto (licao do Qwen que fissurou em emocao).
# - Decisao DETERMINISTICA (desvio da baseline + cooldown), o LLM nao decide nada aqui.
#
# PEGADINHA de load (transformers novo): a classe EmotionModel do model card quebra com
# 'AttributeError: all_tied_weights_keys'. Fix = os 2 atributos de classe + load na mao.

import collections
import threading
import numpy as np
import modelos.cores as cor

_MODELO = "audeering/wav2vec2-large-robust-12-ft-emotion-msp-dim"
_TAXA = 16000

_lock = threading.Lock()
_processor = None
_model = None          # None=nao carregado | False=falhou | objeto=ok
_torch = None

# Baseline movel do arousal tipico + regua de decisao
_hist = collections.deque(maxlen=40)
_MIN_AMOSTRAS = 6       # so avalia depois de N amostras (baseline confiavel)
_DESVIO_BAIXO = 0.12    # abaixo da mediana -> "mais pra baixo/cansado"
_DESVIO_ALTO = 0.15     # acima da mediana -> "mais animado/agitado"
_COOLDOWN = 4           # nao repete a dica dentro de N falas (anti-fissuracao)
_contador = 0
_ultima_dica_idx = -999

_hint_pendente = None   # dica pra proxima resposta (pensar.py le e limpa)


def _carregar():
    global _processor, _model, _torch
    if _model is not None:
        return
    with _lock:
        if _model is not None:
            return
        try:
            import torch
            import torch.nn as nn
            from transformers import Wav2Vec2Processor, Wav2Vec2Config
            from transformers.models.wav2vec2.modeling_wav2vec2 import Wav2Vec2Model, Wav2Vec2PreTrainedModel
            from safetensors.torch import load_file
            from huggingface_hub import hf_hub_download

            class RegressionHead(nn.Module):
                def __init__(self, config):
                    super().__init__()
                    self.dense = nn.Linear(config.hidden_size, config.hidden_size)
                    self.dropout = nn.Dropout(config.final_dropout)
                    self.out_proj = nn.Linear(config.hidden_size, config.num_labels)
                def forward(self, x):
                    x = self.dropout(x); x = self.dense(x); x = torch.tanh(x)
                    x = self.dropout(x); x = self.out_proj(x)
                    return x

            class EmotionModel(Wav2Vec2PreTrainedModel):
                all_tied_weights_keys = {}   # compat transformers novo (sem pesos amarrados)
                _tied_weights_keys = []
                def __init__(self, config):
                    super().__init__(config)
                    self.config = config
                    self.wav2vec2 = Wav2Vec2Model(config)
                    self.classifier = RegressionHead(config)
                    self.init_weights()
                def forward(self, input_values):
                    h = self.wav2vec2(input_values)[0]
                    h = torch.mean(h, dim=1)
                    return h, self.classifier(h)

            _processor = Wav2Vec2Processor.from_pretrained(_MODELO)
            config = Wav2Vec2Config.from_pretrained(_MODELO)
            m = EmotionModel(config)
            m.load_state_dict(load_file(hf_hub_download(_MODELO, "model.safetensors")), strict=False)
            m.eval()
            _torch = torch
            _model = m
            cor.magenta("[🎚️ Modulo de tom (SER) carregado]")
        except Exception as e:
            cor.vermelho(f"[⚠️ Tom: falhou ao carregar o modelo ({e}) — tom desativado]")
            _model = False   # nao tenta de novo


def _arousal(audio, taxa):
    """Roda o SER e devolve o arousal (energia) da fala, ou None se falhar."""
    _carregar()
    if not _model:
        return None
    try:
        if taxa != _TAXA:
            return None
        sig = np.asarray(audio, dtype="float32").squeeze()
        if sig.size < _TAXA // 2:          # < 0.5s: curto demais pra ler tom
            return None
        xt = _processor(sig, sampling_rate=_TAXA, return_tensors="pt").input_values
        with _torch.no_grad():
            _, logits = _model(xt)
        return float(logits[0][0].item())   # logits = [arousal, dominance, valence]
    except Exception as e:
        cor.vermelho(f"[⚠️ Tom: erro na inferencia ({e})]")
        return None


def observar(audio, taxa=_TAXA):
    """Le o arousal, atualiza a baseline e ARMA uma dica sutil (via _hint_pendente) SO
    quando o tom desvia notavelmente do normal. Roda em thread (nao bloqueia)."""
    global _contador, _ultima_dica_idx, _hint_pendente
    a = _arousal(audio, taxa)
    if a is None:
        return
    _contador += 1
    baseline = float(np.median(_hist)) if len(_hist) >= _MIN_AMOSTRAS else None
    _hist.append(a)
    if baseline is None:
        return                                  # ainda montando a baseline
    if _contador - _ultima_dica_idx < _COOLDOWN:
        return                                  # nao repete cedo demais

    dica = None
    if a < baseline - _DESVIO_BAIXO:
        dica = "A voz dele agora soa mais pra baixo / cansada que o normal dele."
    elif a > baseline + _DESVIO_ALTO:
        dica = "A voz dele agora soa mais animada / agitada que o normal dele."
    if dica:
        _hint_pendente = dica
        _ultima_dica_idx = _contador
        cor.cinza(f"[🎚️ Tom: {dica}  (arousal {a:.2f} vs base {baseline:.2f})]")


def observar_async(audio, taxa=_TAXA):
    """Dispara observar() numa thread — nao trava o retorno da transcricao."""
    try:
        buf = np.array(audio, copy=True)
    except Exception:
        return
    threading.Thread(target=observar, args=(buf, taxa), daemon=True).start()


def obter_hint():
    """Pega e LIMPA a dica de tom pendente (pensar.py chama ao montar o prompt de voz).
    Retorna str ou None."""
    global _hint_pendente
    h = _hint_pendente
    _hint_pendente = None
    return h
