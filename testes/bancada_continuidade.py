"""Reconstruções inspiradas nos votos de 14 e 16/09, não replays das conversas originais.

Compara um lembrete de referência perto da pergunta e a retirada de contexto alheio
da notícia. Só a bancada modifica essas entradas; não altera os prompts em produção.
"""
import argparse
import ast
from collections import Counter
from copy import deepcopy
from datetime import datetime
import json
from pathlib import Path
import re
import sys
import time
from unittest.mock import patch

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))
from testes.bancada_persona import executar_cenario
from modulos import momento

AVISO_EXPERIMENTAL = (
    "\nREFERÊNCIA DESTA PERGUNTA: 'esse filme' retoma o título explicitamente citado na "
    "conversa recente. Use esse título; não troque por outro filme conhecido. Se não houver "
    "título no histórico disponível, pergunte qual filme antes de informar o ano."
)
CENARIOS = [
    {"id": "filme_presente", "usuario": "esse filme é de que ano?", "tecnica": "",
     "historico": [{"role": "user", "content": "Estou vendo Três Homens em Conflito."},
                   {"role": "assistant", "content": "Esse duelo final merece uma plateia."}]},
    {"id": "filme_ausente", "usuario": "esse filme é de que ano?", "tecnica": "",
     "historico": [{"role": "user", "content": "Estou vendo um filme."},
                   {"role": "assistant", "content": "Tomara que valha a pipoca."}]},
    {"id": "filme_corrigido", "usuario": "esse filme é de que ano?", "tecnica": "",
     "historico": [{"role": "user", "content": "Vou ver O Poderoso Chefão."},
                   {"role": "assistant", "content": "Uma escolha clássica."},
                   {"role": "user", "content": "Mudei de ideia, estou vendo Três Homens em Conflito."},
                   {"role": "assistant", "content": "Então hoje é faroeste."}]},
    {"id": "filme_fato_disponivel", "usuario": "esse filme é de que ano?", "tecnica": "",
     "historico": [{"role": "user", "content": "Estou vendo Três Homens em Conflito. "
                   "A ficha dele informa lançamento em 1966."},
                   {"role": "assistant", "content": "Esse duelo final merece uma plateia."}]},
    {"id": "noticia_sem_relacao", "usuario": "",
     # Dado de teste inspirado no voto: não verifica a veracidade da notícia original.
     "tecnica": "O radar encontrou uma notícia: RTX 5070 é o requisito mínimo para "
                "007 First Light com path tracing em 1080p. Comente essa novidade do seu jeito.",
     "historico": []},
]


def contexto_noticia():
    # Usa o construtor de contexto de produção, sem importar/iniciar o agendador.
    arvore = ast.parse((RAIZ / "modulos/proativa.py").read_text(encoding="utf-8"))
    funcao = next(n for n in arvore.body if isinstance(n, ast.FunctionDef)
                  and n.name == "_contexto_recente_para_proativo")
    escopo = {"re": re, "momento": momento, "_contraste_jogo_anunciado": lambda *a: "", "_historico_principal": [
        {"role": "user", "content": "Na tela tem uma mulher pulando corda.", "instante": time.time()},
        {"role": "assistant", "content": "Ela está pulando corda sem parar.", "instante": time.time()},
    ]}
    exec(compile(ast.Module(body=[funcao], type_ignores=[]), "proativa.py", "exec"), escopo)
    return escopo["_contexto_recente_para_proativo"](CENARIOS[-1]["tecnica"])


def falhas(cenario, resposta):
    texto = resposta.casefold()
    if cenario == "noticia_sem_relacao":
        return ["misturou a conversa anterior"] if any(x in texto for x in ("corda", "mulher", "pular")) else []
    if cenario == "filme_ausente":
        return ["deu ano ou não pediu identificação"] if (re.search(r"\b(?:18|19|20)\d{2}\b", texto)
                   or not any(x in texto for x in ("qual filme", "nome", "título", "que filme"))) else []
    erros = []
    if "1966" not in texto:
        erros.append("faltou o ano esperado")
    if "1972" in texto or "chefão" in texto:
        erros.append("trocou o filme atual pelo outro")
    return erros


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--repeticoes", type=int, default=2)
    ap.add_argument("--comparar", action="store_true")
    ap.add_argument("--cenario", help="ID de um cenário específico")
    args = ap.parse_args()
    if not 1 <= args.repeticoes <= 5:
        ap.error("--repeticoes deve ficar entre 1 e 5")
    cenarios = [c for c in CENARIOS if not args.cenario or c["id"] == args.cenario]
    if not cenarios:
        ap.error("cenário desconhecido")
    from modulos import pensar
    resultados = []
    contexto = contexto_noticia()
    destino = RAIZ / "logs" / "bancada_continuidade.jsonl"
    destino.parent.mkdir(exist_ok=True)
    for rodada in range(1, args.repeticoes + 1):
        for original in cenarios:
            variantes = ["atual", "experimental"] if args.comparar else ["atual"]
            if rodada % 2 == 0:
                variantes.reverse()
            for variante in variantes:
                cenario = deepcopy(original)
                if cenario["id"] == "noticia_sem_relacao" and variante == "atual":
                    cenario["tecnica"] += contexto
                chamar_real = pensar._chamar_llm
                def chamar(**parametros):
                    if variante == "experimental" and cenario["id"].startswith("filme"):
                        parametros = deepcopy(parametros)
                        parametros["messages"][-1]["content"] += AVISO_EXPERIMENTAL
                    return chamar_real(**parametros)
                with (patch.object(pensar, "_chamar_llm", chamar),
                      patch.object(pensar.assuntos, "contexto_relacionado", return_value="")):
                    resposta, persona = executar_cenario(pensar, cenario)
                erros = falhas(cenario["id"], resposta)
                registro = {"tempo": datetime.now().isoformat(timespec="seconds"), "rodada": rodada,
                            "cenario": cenario["id"], "variante": variante, "resposta": resposta,
                            "usou_persona": persona, "falhas": erros, "ok": not erros}
                resultados.append(registro)
                with destino.open("a", encoding="utf-8") as arquivo:
                    arquivo.write(json.dumps(registro, ensure_ascii=False) + "\n")
                print(f"[{variante} / {cenario['id']} / rodada {rodada}] {resposta}", flush=True)
                if erros:
                    print("  -> " + "; ".join(erros), flush=True)
    print("\nChecks de referência por ramo (ler também as respostas; isto não mede humor):")
    totais = Counter((r["variante"], r["usou_persona"]) for r in resultados)
    for (variante, persona), total in sorted(totais.items()):
        passou = sum(r["ok"] for r in resultados if r["variante"] == variante and r["usou_persona"] == persona)
        print(f"  {variante} / {'PROMPT_COMPLETO' if persona else 'ENXUTO'}: {passou}/{total}")
    print(f"Respostas em {destino}")


if __name__ == "__main__":
    main()
