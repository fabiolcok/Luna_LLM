"""Regras puras para extrair anotações sem pedir ao modelo que reescreva o usuário."""

import re


_RE_TIRA_COMANDO = re.compile(
    r'^\s*(anota|salva|registra|guarda|arquiva|toma\s+nota|lembra(r)?(\s+que)?)\w*\s*'
    r'(isso|a[íi]|aqui|essa\s+nota|pra\s+mim|no\s+obsidian)?\s*[:,\-–]?\s*', re.IGNORECASE)
_RE_TITULO = re.compile(r'(?im)^\s*t[íi]tulo\s*:\s*(.+?)\s*$')
_RE_CONTEUDO = re.compile(r'(?im)^\s*conte[uú]do(?:\s*:\s*|\s+)')
_TOKENS_REFERENCIA = re.compile(
    r'\b(beleza|blz|ok|okay|ent[ãa]o|obrigad\w*|valeu|vlw|favor|pfv|pf|'
    r'boa|ideia|gostei|curti|perfeit[oa]|[óo]tim[oa]|massa|legal|bacana|excelente|'
    r'acho|pode|[ée]|eh|deixa|dexa|isso|aquilo|a[íi]|aqui|ess[ae]s?|'
    r'anota\w*|anotad\w*|salva\w*|registra\w*|guarda\w*|guardad\w*|arquiva\w*|'
    r'lembra\w*|toma|nota|not[ae]|pra|mim|no|na|nas|obsidian|por|de|o|a|e|um|uma)\b',
    re.IGNORECASE)


def dados_para_anotar(prompt: str, titulo_modelo: str = "") -> tuple[str, str]:
    """Extrai título/conteúdo do envelope humano e preserva o texto real literalmente."""
    texto = (prompt or "").replace("\r\n", "\n").strip()
    titulo_match = _RE_TITULO.search(texto)
    conteudo_match = _RE_CONTEUDO.search(texto)
    titulo = (titulo_match.group(1).strip() if titulo_match else (titulo_modelo or "").strip())
    if conteudo_match:
        return texto[conteudo_match.end():].strip(), titulo
    return _RE_TIRA_COMANDO.sub('', texto).strip(), titulo


def pedido_anaforico(prompt: str) -> bool:
    """Pedido sem conteúdo próprio: a anotação é a fala substancial imediatamente anterior."""
    resto = _TOKENS_REFERENCIA.sub('', prompt or '')
    return not re.sub(r'[\s,.\-–!?:;]+', '', resto)


def ultima_fala(historico: list, prompt_atual: str) -> str:
    alvo = re.sub(r'\s+', ' ', (prompt_atual or '')).strip().lower()
    for mensagem in reversed(historico or []):
        conteudo = re.sub(r'\s+', ' ', str(mensagem.get('content', ''))).strip()
        if len(conteudo) > 15 and conteudo.lower() != alvo:
            return conteudo
    return ''


def origem(responder_completo: bool, presenca_pc: bool) -> str:
    if not responder_completo:
        return "voz"
    return "web" if presenca_pc else "telegram"
