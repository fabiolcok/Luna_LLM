r"""
ferramentas/setup_telegram_promo.py — LOGIN ÚNICO do radar de promoções.

Roda UMA vez, da raiz:  venv\Scripts\python ferramentas\setup_telegram_promo.py

Ele loga na SUA conta do Telegram (pede o telefone e o código que chega no app) e gera
o arquivo modelos/luna_promo.session — a credencial que a Luna reusa depois, sem pedir
código de novo. O radar em si (modulos/radar_promo.py) só LÊ os canais que você segue.

Antes de rodar, preencha no .env:
    TELEGRAM_API_ID=...      (em my.telegram.org > API development tools)
    TELEGRAM_API_HASH=...

⚠️ O .session é login da sua conta — já está no .gitignore, NUNCA suba pro git.
"""

import os
import sys
from pathlib import Path

# O setup grava em modelos/ e lê o .env da raiz mesmo quando chamado por caminho absoluto.
RAIZ = Path(__file__).resolve().parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))
os.chdir(RAIZ)

from dotenv import load_dotenv

load_dotenv()

SESSION = "modelos/luna_promo"   # precisa bater com o SESSION de modulos/radar_promo.py

api_id = os.getenv("TELEGRAM_API_ID", "").strip()
api_hash = os.getenv("TELEGRAM_API_HASH", "").strip()

if not api_id or not api_hash:
    print("❌ Falta TELEGRAM_API_ID e/ou TELEGRAM_API_HASH no .env.")
    print("   Pegue as duas em https://my.telegram.org > API development tools.")
    raise SystemExit(1)

try:
    from telethon.sync import TelegramClient
except ImportError:
    print("❌ Telethon não instalado. Rode:  pip install telethon")
    raise SystemExit(1)

os.makedirs("modelos", exist_ok=True)

print("→ Vou te pedir o telefone (com DDI, ex: +5561...) e o código que chega no Telegram.")
with TelegramClient(SESSION, int(api_id), api_hash) as client:
    eu = client.get_me()
    nome = getattr(eu, "username", None) or getattr(eu, "first_name", "conta")
    print(f"✅ Logado como: {nome}")
    print(f"✅ Sessão salva em {SESSION}.session — a Luna já pode ler os canais.")
    print("   Agora entre nos canais de promoção pelo seu Telegram e liste os @ em")
    print("   Luna/RastrearPromocoes.md (no seu vault do Obsidian).")
