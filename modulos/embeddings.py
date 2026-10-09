"""EmbeddingGemma textual compartilhado; CPU e revisão fixadas para a memória."""
from pathlib import Path
import os
import threading

import numpy as np

MODELO = "google/embeddinggemma-2"
REVISAO = "914f7f89142e33e77833254d9c9b90c3cef7303b"
DIMENSOES = 768
IDENTIDADE_CACHE = (MODELO, REVISAO, DIMENSOES, "Document")
CAMINHO_MODELO = Path(__file__).resolve().parents[1] / "modelos/embeddings" / REVISAO
_ARQUIVOS = (
    "model.safetensors", "chat_template.jinja", "config.json", "modules.json",
    "config_sentence_transformers.json", "tokenizer.json", "tokenizer_config.json",
    "processor_config.json", "preprocessor_config.json", "sentence_bert_config.json",
    "1_Pooling/config.json", "2_Normalize/config.json",
)


def _snapshot():
    if not all((CAMINHO_MODELO / nome).is_file() for nome in _ARQUIVOS):
        from huggingface_hub import snapshot_download
        snapshot_download(MODELO, revision=REVISAO, token=False,
                          local_dir=CAMINHO_MODELO,
                          allow_patterns=["*.json", "*.safetensors", "*.model", "*.jinja"])
    return str(CAMINHO_MODELO)


def _carregar_modelo():
    os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")
    import torch
    from sentence_transformers import SentenceTransformer

    # PyTorch compartilha esse limite com o TTS; evita ocupar todos os núcleos no jogo.
    torch.set_num_threads(4)
    modelo = SentenceTransformer(
        _snapshot(), device="cpu", local_files_only=True, trust_remote_code=False,
        config_kwargs={"vision_config": None, "audio_config": None},
        model_kwargs={"dtype": torch.float32},
    )
    # O tokenizer traz um sentinela enorme; o limite textual publicado é 8192 tokens.
    modelo.max_seq_length = 8192
    if (any(p.device.type != "cpu" for p in modelo.parameters())
            or any(p.dtype != torch.float32 for p in modelo.parameters() if p.is_floating_point())
            or any("vision" in nome or "audio" in nome for nome, _ in modelo.named_parameters())
            or not {"SearchQuery", "Document"} <= set(modelo.prompts)):
        raise RuntimeError("EmbeddingGemma não carregou no modo textual CPU esperado")
    return modelo


class EmbeddingGemmaCPU:
    def __init__(self):
        self._modelo = None
        self._lock = threading.RLock()

    def _encode(self, textos, prefixo):
        textos = list(textos)
        if not textos:
            return np.empty((0, DIMENSOES), dtype=np.float32)
        # Recall, histórico e curadoria podem vir de threads diferentes; um único modelo
        # e uma inferência por vez evitam carga duplicada e picos concorrentes de RAM.
        with self._lock:
            if self._modelo is None:
                self._modelo = _carregar_modelo()
            vetores = np.asarray(self._modelo.encode(
                textos, prompt_name=prefixo, batch_size=8, show_progress_bar=False,
                convert_to_numpy=True, normalize_embeddings=True,
            ), dtype=np.float32)
        if (vetores.shape != (len(textos), DIMENSOES)
                or not np.isfinite(vetores).all()
                or np.any(np.linalg.norm(vetores, axis=1) == 0)):
            raise ValueError("Embeddings inválidos; índice não será atualizado")
        return vetores

    def documentos(self, textos):
        return self._encode(textos, "Document")

    def consultas(self, textos):
        return self._encode(textos, "SearchQuery")


_compartilhado = EmbeddingGemmaCPU()


def obter_embedder():
    return _compartilhado
