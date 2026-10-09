"""Distingue perguntas sobre conversas de pedidos para ler ou guardar notas."""
import re

_RE_LEMBRANCA = re.compile(
    r"\b(?:voc[êe]|vc|tu)\s+(?:ainda\s+)?(?:se\s+)?(?:lembra|recorda)\b|"
    r"^\s*(?:luna[,\s]+)?(?:se\s+)?(?:lembra|recorda)\s+"
    r"(?:d[eoas]\b|dos\b|das\b|o\s+que\b|qual\b|como\b|quando\b|por\s+que\b)|"
    r"^\s*(?:o\s+que|qual|como|quando|por\s+que)\b.*?"
    r"\b(?:te\s+(?:falei|contei|disse)|conversamos)\b",
    re.IGNORECASE,
)
_RE_NOTA = re.compile(
    r"\b(?:obsidian|notas?|anota[çc][õo]es|arquivo)\b|\.md\b",
    re.IGNORECASE,
)
_RE_ACAO_EXPLICITA = re.compile(
    r"\b(?:anota|anote|salva|salve|registra|registre|guarda|guarde|arquiva|arquive|"
    r"pesquise|busque|procure|resuma|transcreva|desenhe|toque|"
    r"pode\s+(?:pesquisar|buscar|procurar|abrir|salvar|anotar))\b",
    re.IGNORECASE,
)


def pergunta_de_lembranca(texto: str) -> bool:
    # "Você lembra?" foi roteado para ler_obsidian e devolveu Memoria.md inteiro.
    # Só protegemos a retomada da conversa; notas explícitas e ações continuam roteáveis.
    texto = texto or ""
    return bool(_RE_LEMBRANCA.search(texto)
                and not _RE_NOTA.search(texto)
                and not _RE_ACAO_EXPLICITA.search(texto))
