"""Resumo honesto da instalação exibido no terminal durante o boot da Luna."""

import os

from modulos import config_env
import modelos.cores as cor


_INTEGRACOES = (
    ("Gemini", ("GEMINI_API_KEY",)),
    ("Spotify", ("SPOTIPY_CLIENT_ID", "SPOTIPY_CLIENT_SECRET")),
    ("Gmail", ("EMAIL_USUARIO", "EMAIL_SENHA")),
    ("Overwatch", ("OW_BATTLETAG",)),
    ("Steam", ("STEAM_API_KEY", "STEAM_ID")),
    ("Hugging Face", ("HF_TOKEN",)),
    ("Telegram", ("TELEGRAM_TOKEN", "TELEGRAM_CHAT_ID")),
    ("Radar de promoções", ("TELEGRAM_API_ID", "TELEGRAM_API_HASH")),
)


def estado_integracao(chaves: tuple) -> str:
    """'preenchida', 'incompleta' ou 'ausente'; não promete que a API funciona."""
    preenchidas = sum(config_env.esta_configurado(chave) for chave in chaves)
    if preenchidas == len(chaves):
        return "preenchida"
    if preenchidas:
        return "incompleta"
    return "ausente"


def _ok(texto: str):
    cor.verde(f"[✅ {texto}]")


def _aviso(texto: str):
    cor.amarelo(f"[⚠️ {texto}]")


def _erro(texto: str):
    cor.vermelho(f"[❌ {texto}]")


def mostrar_diagnostico():
    """Mostra checks locais e presença das configs opcionais, sem chamar APIs externas."""
    from modulos import obsidian
    from modulos.pensar import estado_turbollm

    print("\n[🔧 Diagnóstico de inicialização]")

    if os.path.isfile(".env"):
        _ok(".env encontrado")
    else:
        _erro(".env não encontrado — copie .env.example para .env")

    if config_env.esta_configurado("USUARIO_NOME"):
        _ok("Nome do usuário configurado")
    else:
        _erro("USUARIO_NOME não configurado no .env")

    vault = obsidian.estado_vault()
    if not vault["configurado"]:
        _aviso("Obsidian — não configurado (opcional)")
    elif not vault["existe"]:
        _erro(f"Obsidian — pasta não encontrada: {vault['caminho']}")
    elif vault["presentes"] == vault["total"]:
        _ok(f"Obsidian — {vault['presentes']} notas de configuração disponíveis em {vault['caminho']}")
    else:
        _erro(f"Obsidian — só {vault['presentes']} de {vault['total']} notas puderam ser criadas")

    turbo = estado_turbollm()
    if not turbo["servidor"]:
        _erro("TurboLLM — servidor não respondeu")
    elif not turbo["modelo"]:
        _erro("TurboLLM — servidor respondeu, mas o modelo não carregou")
    else:
        _ok(f"TurboLLM — modelo carregado: {turbo['modelo_id']} "
            f"(thinking: {turbo.get('thinking', 'desligado')})")

    print("[Integrações opcionais — preenchimento, sem teste de API]")
    for nome, chaves in _INTEGRACOES:
        estado = estado_integracao(chaves)
        if estado == "preenchida":
            _ok(f"{nome} — campos preenchidos")
        elif estado == "incompleta":
            faltam = ", ".join(c for c in chaves if not config_env.esta_configurado(c))
            _aviso(f"{nome} — configuração incompleta; falta {faltam}")
        else:
            _aviso(f"{nome} — não configurado")

    print("[🌙 Inicialização concluída]\n")
