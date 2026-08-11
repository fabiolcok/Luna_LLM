# Ferramentas manuais

Estes scripts ajudam a configurar ou diagnosticar partes da Luna. Eles não entram na suíte
automatizada de `testes/` e devem ser executados a partir da raiz do projeto.

| comando | para que serve |
|---|---|
| `venv\Scripts\python ferramentas\setup_telegram_promo.py` | faz o login único do radar de promoções; feche a Luna antes para não disputar a sessão do Telegram |
| `venv\Scripts\python ferramentas\testar_turbollm.py` | testa conexão, carregamento do modelo configurado, function calling e estabilidade do TurboLLM |
| `venv\Scripts\python ferramentas\teste_fala.py` | oficina interativa para ouvir e comparar pronúncias do Kokoro |
| `venv\Scripts\python ferramentas\debug_memoria.py` | imprime, sem alterar, o conteúdo guardado no ChromaDB |

O dicionário usado pela oficina web e pela voz real continua em `modelos/pronuncia.json`.
`teste_fala.py` apenas oferece outra interface para experimentar pelo terminal.
