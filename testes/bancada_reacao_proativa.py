"""A/B local do proativo; prepara sem rede e executa sem voz ou ferramentas."""
import argparse
from copy import deepcopy
from datetime import datetime
import hashlib
import json
from pathlib import Path
import random
import re
from unittest.mock import patch

from testes.bancada_modelos import chamar, conferir_identidade, digest, gravar_json, identidade
from testes.bancada_dark_souls_thinking import preparar_runtime, gerar_turno

BASE = "http://127.0.0.1:6996"
ESPERADO = "gemma-4-12B-it-QAT-Q4_0"
FONTES = ("modulos/prompts.py", "modulos/pensar.py", "modulos/proativa.py", "modulos/momento.py")

def fontes():
    return {p: hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in FONTES}

def trocar_bloco(pedido, atual, variante):
    novo = deepcopy(pedido)
    sistemas = [m for m in novo["messages"] if m["role"] == "system"]
    if len(sistemas) != 1 or sistemas[0]["content"].count(atual) != 1:
        raise ValueError("Bloco proativo ausente ou ambiguo; revise a montagem.")
    if atual == variante:
        raise ValueError("Variante igual ao controle.")
    sistemas[0]["content"] = sistemas[0]["content"].replace(atual, variante, 1)
    return novo

def preparar(pasta):
    if pasta.exists():
        raise ValueError("Use uma pasta nova para preservar a rodada anterior.")
    pensar = preparar_runtime()
    from modulos import prompts
    # Data fixa torna o preparo reproduzivel sem depender de logs privados anteriores.
    instante = 1790526252.4361274
    morte = {"tipo": "morte", "nome": "", "mortes_sessao": 1, "incremento": 1}
    casos = [
        {"id": "steam_celeste", "grupo": "steam", "fato":
         "O usuário acabou de abrir Celeste na Steam. Dados: 21 horas jogadas no total; última sessão há dois meses. Comente a abertura."},
        {"id": "steam_cities", "grupo": "steam", "fato":
         "O usuário acabou de abrir Cities: Skylines II na Steam. Dados: 4 horas jogadas no total; última sessão há um mês. Comente a abertura."},
        {"id": "rss_offline", "grupo": "radar", "fato":
         "Notícia sintética do radar: um estúdio anunciou que seu jogo para um jogador exigirá conexão permanente com a internet. Comente a novidade."},
        {"id": "rss_roupa", "grupo": "radar", "fato":
         "Notícia sintética do radar: um estúdio anunciou uma roupa cosmética por 30 reais para seu jogo. A roupa não muda atributos nem habilidades. Comente a novidade."},
        {"id": "morte_sem_causa", "grupo": "dark_souls", "evento": morte,
         "controle_repetido_do_piloto": True},
        {"id": "morte_apos_gargulas", "grupo": "dark_souls", "evento": morte,
         "recentes": ["As Gárgulas caíram! Essa vitória merece barulho."]},
        {"id": "chefe_gargulas", "grupo": "dark_souls",
         "evento": {"tipo": "chefe", "nome": "Bell Gargoyles", "mortes_sessao": 1}},
        {"id": "fogueira_burg", "grupo": "dark_souls",
         "evento": {"tipo": "fogueira", "nome": "Undead Burg", "mortes_sessao": 1}},
    ]
    pedidos = []
    for caso in casos:
        evento = caso.get("evento", morte)
        r = gerar_turno(pensar, evento, list(caso.get("recentes", [])), "desligado", 2901,
                        instante, lambda p: {"texto": "Preparação. [clima:duvida]"})
        # A produção agora seleciona Dark Souls; recupere o controle histórico do A/B.
        atual = trocar_bloco(r["pedido"], prompts.ENXUTO_DARK_SOULS, prompts.ENXUTO_PROATIVO)
        if "fato" in caso:
            texto = atual["messages"][-1]["content"]
            trecho = prompts.prompt_dark_souls(evento)
            assert texto.count(trecho) == 1
            atual["messages"][-1]["content"] = texto.replace(trecho, caso["fato"], 1)
        # Todos os braços recebem os mesmos parâmetros, sem depender do default da engine.
        atual.update(temperature=0.8, presence_penalty=0.3, frequency_penalty=0.3,
                     top_k=20, top_p=0.95, min_p=0.05, repeat_penalty=1.0, max_tokens=180)
        candidato = trocar_bloco(atual, prompts.ENXUTO_PROATIVO, prompts.ENXUTO_PROATIVO_REACAO_AB)
        pedidos.append({"caso": caso, "ramo": "ENXUTO_PROATIVO + EMOCAO",
                        "ramo_variante": "ENXUTO_DARK_SOULS + EMOCAO",
                        "pedidos": {"atual": atual, "reacao": candidato}})
    suite = {"criado": datetime.now().isoformat(), "fontes": fontes(), "casos": pedidos,
             "seeds": [2901, 2902], "instante_fixture": instante,
             "blocos": {"atual": prompts.ENXUTO_PROATIVO, "reacao": prompts.ENXUTO_PROATIVO_REACAO_AB},
             "metodo": "8 casos independentes x 2 seeds x 2 prompts; ordem alternada; historico fixo por par"}
    suite["sha256"] = digest(suite)
    gravar_json(pasta / "suite.json", suite)
    print(pasta / "suite.json", flush=True)

def carregar(pasta):
    suite = json.loads((pasta / "suite.json").read_text(encoding="utf8"))
    if digest({k:v for k,v in suite.items() if k != "sha256"}) != suite["sha256"]:
        raise ValueError("Snapshot alterado.")
    if fontes() != suite["fontes"]:
        raise ValueError("Fontes mudaram depois da preparacao.")
    return suite

def folha(pasta, suite, registro):
    linhas = ["# Avaliação do proativo: Gemma 4 12B", "",
              "16 pares: oito situações, duas amostras de cada. Todos os textos foram gerados pelo Gemma.",
              "As letras X/Y são embaralhadas por par; não identificam uma variante fixa.",
              "Cenários sintéticos. Sete situações diferem do piloto; morte sem causa é um controle repetido.",
              "Não é uma conversa contínua: cada par recebe o mesmo contexto fixo.",
              "A bancada não altera a configuração da Luna; compara o controle original com a variante.", "",
              "Marque **X / Y / empate bom / nenhum** e acrescente um motivo, se quiser.",
              "Julgue naturalidade, humor, coerência e vontade de ouvir a fala. Tags de clima foram",
              "ocultadas aqui; os textos completos e a chave estão nos registros técnicos locais.", ""]
    rng = random.Random(73929)
    chave = []
    numero = 0
    for item in suite["casos"]:
        c = item["caso"]
        for seed in suite["seeds"]:
            numero += 1
            ordem = ["atual", "reacao"]; rng.shuffle(ordem)
            contexto = c.get("fato") or {"morte": "Personagem morreu; causa desconhecida.",
                "chefe": "Chefe derrotado: " + c.get("evento",{}).get("nome",""),
                "fogueira": "Fogueira liberada: " + c.get("evento",{}).get("nome","")}[c["evento"]["tipo"]]
            if c.get("recentes"):
                contexto += " Fala anterior fixa: " + c["recentes"][0]
            linhas += [f"## {numero}. {c['id']} — amostra {suite['seeds'].index(seed)+1}", "", contexto, ""]
            for letra, variante in zip(("X", "Y"), ordem):
                r = next((r for r in registro["resultados"] if r["caso"] == c["id"] and
                          r["seed"] == seed and r["variante"] == variante), None)
                texto = re.sub(r"\s*\[clima:[^]]+\]", "", r["texto"]).strip() if r else "(pendente)"
                linhas += [f"**{letra}**", "", "> " + texto.replace("\n", "\n> "), ""]
                chave.append({"par": numero, "letra": letra, "variante": variante, "caso": c["id"], "seed": seed})
            linhas += ["Avaliação: pendente.", ""]
    destino = pasta / "avaliacao.md"
    if destino.exists():
        raise ValueError("Folha ja existe; nao sobrescrever avaliacoes humanas.")
    destino.write_text("\n".join(linhas), encoding="utf8")
    gravar_json(pasta / "chave.json", chave)

def executar(pasta):
    suite = carregar(pasta)
    modelo = identidade(BASE, ESPERADO)
    destino = pasta / "resultados.json"
    if destino.exists():
        raise ValueError("Resultados ja existem; use outra rodada, sem sobrescrever.")
    registro = {"modelo": modelo, "suite_sha256": suite["sha256"], "completo": False, "resultados": []}
    gravar_json(destino, registro)
    warm = deepcopy(suite["casos"][0]["pedidos"]["atual"]);warm["max_tokens"]=16
    registro["warmup_excluido"] = chamar(BASE, modelo, warm)
    try:
        for i,item in enumerate(suite["casos"]):
            for rodada,seed in enumerate(suite["seeds"]):
                ordem = ["atual", "reacao"] if (i+rodada)%2 == 0 else ["reacao", "atual"]
                for variante in ordem:
                    conferir_identidade(identidade(BASE, ESPERADO), modelo)
                    pedido = deepcopy(item["pedidos"][variante]);pedido["seed"]=seed
                    r = chamar(BASE, modelo, pedido)
                    conferir_identidade(identidade(BASE, ESPERADO), modelo)
                    r.update(caso=item["caso"]["id"], grupo=item["caso"]["grupo"], seed=seed,
                             variante=variante, pedido=pedido, pedido_sha256=digest(pedido))
                    registro["resultados"].append(r)
                    gravar_json(destino, registro)
                    print(f"[{len(registro['resultados'])}/32] {r['caso']} {variante}: {r['total_s']:.2f}s", flush=True)
        registro["completo"] = True
    finally:
        gravar_json(destino, registro)
    folha(pasta, suite, registro)
    print("Concluido: " + str(pasta / "avaliacao.md"), flush=True)

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("modo", choices=("preparar", "executar"))
    p.add_argument("--pasta", type=Path, required=True)
    a=p.parse_args()
    (preparar if a.modo=="preparar" else executar)(a.pasta)

if __name__=="__main__":
    main()
