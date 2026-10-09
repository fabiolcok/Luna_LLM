"""Três falas do piloto pelo ramo proativo real; sem voz, jogo ou boot do modelo."""
import argparse
import json
import time
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

from testes.bancada_modelos import carregar_pensar, identidade, chamar
from testes.testa_prompt_montagem import _Resposta


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preparar", action="store_true", help="somente captura os prompts, sem chamar o modelo")
    args = parser.parse_args()
    with patch.dict("os.environ", {"USUARIO_NOME": "Usuário"}):
        pensar = carregar_pensar()
    pensar.limpar_texto_para_voz = lambda texto: texto
    from modulos import prompts, momento, dark_souls
    base = "http://127.0.0.1:6996"
    modelo = None if args.preparar else identidade(base, "")
    resultados = []
    for evento in [
        {"tipo": "morte", "nome": "", "mortes_sessao": 3, "incremento": 1},
        {"tipo": "chefe", "nome": "Bell Gargoyles", "mortes_sessao": 4},
        {"tipo": "fogueira", "nome": "Undead Parish", "mortes_sessao": 4},
    ]:
        capturado = {}
        def capturar(**kwargs):
            capturado.update(kwargs)
            return _Resposta()
        pensar._presenca_pc.set(True)
        pensar._ultima_saudacao_ts = time.time()
        with (patch.object(pensar, "_chamar_llm", capturar),
              patch.object(pensar.obsidian, "ler_perfil", return_value="Gosta de jogos e humor exagerado."),
              patch.object(pensar.obsidian, "listar_memoria_episodica", return_value=[]),
              patch.object(pensar, "buscar_memoria_relevante", return_value=[]),
              patch.object(pensar, "buscar_contexto_relevante", return_value=""),
              patch.object(pensar, "ler_estado_luna", return_value={}),
              patch.object(pensar.assuntos, "contexto_relacionado", return_value=""),
              patch.object(pensar, "obter_janela_em_foco", return_value="DARK SOULS REMASTERED"),
              patch.object(momento, "_jogos", {}), patch.object(dark_souls, "contexto", return_value=None)):
            pensar._reescrever_como_luna(prompts.prompt_dark_souls(evento), "", [], max_tokens=180,
                                        tarefa_proativa="dark_souls_" + evento["tipo"])
        pedido = {k: v for k, v in capturado.items() if k in {"messages", "temperature", "max_tokens", "top_p"}}
        pedido.update(stream=True, seed=42, cache_prompt=False,
                      chat_template_kwargs={"enable_thinking": False})
        resultado = {"texto": "(prompt capturado; não gerado)"} if args.preparar else chamar(base, modelo, pedido)
        resultados.append({"evento": evento, "ramo": "ENXUTO_DARK_SOULS + EMOCAO",
                           "pedido": pedido, **resultado})
        print(evento["tipo"] + ": " + resultado["texto"], flush=True)
    destino = Path("logs/dark_souls") / ("bancada-" + datetime.now().strftime("%Y%m%d-%H%M%S") + ".json")
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(json.dumps({"modelo": modelo, "resultados": resultados}, ensure_ascii=False, indent=2), encoding="utf-8")
    print("Todas as falas usam o modo enxuto; esta rodada não compara a persona completa.")
    print(destino)


if __name__ == "__main__":
    main()
