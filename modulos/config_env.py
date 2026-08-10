# modulos/config_env.py
"""Leitura do .env tolerante a PLACEHOLDER.

Por que isso existe: o INSTALACAO.md manda copiar o `.env.example` e preencher só
`USUARIO_NOME` pra começar — o resto é opcional. Só que o exemplo vem cheio de
`seu_token_telegram`, `sua_chave_steam` e afins, e o código lia esses valores como se
fossem reais. Deu dois problemas numa instalação nova:

  1. `int(os.getenv("TELEGRAM_CHAT_ID"))` estourava com 'seu_chat_id' e derrubava o
     main.py inteiro na importação — uma feature OPCIONAL matando o app.
  2. `if not TELEGRAM_TOKEN` não pegava nada, porque 'seu_token_telegram' é truthy:
     o bot subia e ficava tentando conectar com um token inventado.

Aqui placeholder e vazio são a mesma coisa: NÃO CONFIGURADO.
"""

import os

# Prefixos que o .env.example usa nos exemplos. Comparados em minúsculas.
_PLACEHOLDERS = ("seu_", "sua_", "seu ", "sua ")
_EXATOS = {"seunome", "c:\\caminho\\para\\seu\\vault", "seunome-0000"}


def esta_configurado(nome: str) -> bool:
    """True só se a chave tem valor de verdade (nem vazio, nem exemplo do .env.example)."""
    return texto(nome) != ""


def texto(nome: str, padrao: str = "") -> str:
    """Valor do .env como texto — devolve `padrao` se estiver vazio ou for placeholder."""
    v = (os.getenv(nome) or "").strip()
    baixo = v.lower()
    if not v or baixo in _EXATOS or baixo.startswith(_PLACEHOLDERS):
        return padrao
    return v


def inteiro(nome: str, padrao: int = 0) -> int:
    """Valor do .env como int, sem estourar. Texto não-numérico vira `padrao`.

    Nunca levanta: uma chave opcional mal preenchida não pode derrubar a Luna.
    """
    v = texto(nome)
    if not v:
        return padrao
    try:
        return int(v)
    except ValueError:
        return padrao
