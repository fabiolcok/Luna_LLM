"""Compara sequências do piloto com thinking ligado/desligado, sem voz ou troca de modelo."""
import argparse
import ast
from contextlib import redirect_stdout
from copy import deepcopy
from datetime import datetime
import hashlib
import io
import json
from pathlib import Path
import re
import statistics
import sys
import time
from types import ModuleType, SimpleNamespace
from unittest.mock import patch

from testes.bancada_modelos import carregar_pensar, chamar, conferir_identidade, identidade
from testes.testa_prompt_montagem import _Resposta

RAIZ = Path(__file__).resolve().parents[1]
BASE = "http://127.0.0.1:6996"


def extrair(arquivo, nomes, escopo):
    arvore = ast.parse((RAIZ / arquivo).read_text(encoding="utf-8"))
    arvore.body = [n for n in arvore.body if isinstance(n, (ast.FunctionDef, ast.ClassDef))
                  and n.name in nomes]
    assert {n.name for n in arvore.body} == set(nomes), "Função da produção mudou; revise a bancada"
    exec(compile(arvore, arquivo, "exec"), escopo)


class FalhaBancada(BaseException):
    # O fallback de produção não pode transformar falha HTTP em resposta pontuada na bancada.
    pass


def preparar_runtime():
    with patch.dict("os.environ", {"USUARIO_NOME": "Usuário"}):
        pensar = carregar_pensar()
    escopo = {}
    extrair("modulos/falar.py", ["limpar_texto_para_voz"], escopo)
    pensar.limpar_texto_para_voz = escopo["limpar_texto_para_voz"]
    return pensar


def gerar_turno(pensar, evento, recentes, modo, seed, instante, executar, tarefa=None, mortes_recentes=None):
    from modulos import dark_souls, momento, prompts, tom
    from modulos.turbollm_api import opcoes_pensamento
    pedido, resultado = {}, {}
    tentativas = []
    servidor = ModuleType("servidor")
    for nome in ("atualizar_status", "atualizar_metricas", "atualizar_kaomoji", "atualizar_gif"):
        setattr(servidor, nome, lambda *a, **kw: None)

    def interceptar(**kw):
        pedido.clear()
        resultado.clear()
        pedido.update(deepcopy(kw))
        pedido.update(pedido.pop("extra_body", {}))
        pedido.update(seed=seed + len(tentativas) * 1000, stream=True, stream_options={"include_usage": True}, cache_prompt=False)
        try:
            resultado.update(executar(deepcopy(pedido)))
        except Exception as erro:
            raise FalhaBancada(str(erro)) from erro
        tentativas.append({"pedido": deepcopy(pedido), **deepcopy(resultado)})
        resposta = _Resposta()
        resposta.choices[0].message.content = resultado["texto"]
        resposta.choices[0].finish_reason = resultado.get("finish_reason", "stop")
        resposta.usage.completion_tokens = resultado.get("uso", {}).get("completion_tokens", 0)
        return resposta

    def responder(instrucao, historico, **kw):
        return pensar._reescrever_como_luna(instrucao, "", historico, max_tokens=kw["max_tokens"],
                                          tarefa_proativa=kw.get("tarefa_proativa"))

    escopo = {
        "re": re, "_historico_principal": [], "_historico_proativo": [],
        "_falas_recentes": recentes,
        "_falas_morte_recentes": mortes_recentes if mortes_recentes is not None else list(recentes),
        "_prompts": prompts,
        "_execucoes": SimpleNamespace(verificar=lambda: None, contexto=SimpleNamespace(get=lambda: None)),
        "cor": SimpleNamespace(amarelo=lambda *a: None, vermelho=lambda *a: None),
        "gerar_resposta": responder, "obter_clima_resposta": pensar.obter_clima_resposta,
        "_limpar_visual_proativo": lambda: None,
    }
    # Executa a preparação e a antirrepetição da produção sem importar proativa (áudio/threads).
    extrair("modulos/proativa.py", ["_contexto_recente_para_proativo", "_gerar_fala_proativa", "_FalaProativa"], escopo)
    data_fixa = SimpleNamespace(datetime=SimpleNamespace(now=lambda: datetime.fromtimestamp(instante)))
    _, opcoes = opcoes_pensamento(modo)
    pensar._presenca_pc.set(True)
    pensar._ultima_saudacao_ts = time.time()
    pensar._kaomoji_recentes.clear()
    contexto_jogo = {"jogo": "DARK SOULS REMASTERED", "mortes_sessao": evento["mortes_sessao"],
                    "eventos": [dict(evento, idade_s=0)]}
    saida = io.StringIO()
    with (
        patch.dict(sys.modules, {"servidor": servidor}),
        patch.object(pensar, "datetime", data_fixa),
        patch.object(pensar, "MODO_PENSAMENTO", modo),
        patch.object(pensar, "OPCOES_MODELO", opcoes),
        patch.object(pensar, "_chamar_llm", interceptar),
        patch.object(pensar.obsidian, "ler_perfil", return_value="Gosta de jogos e humor exagerado."),
        patch.object(pensar.obsidian, "listar_memoria_episodica", return_value=[]),
        patch.object(pensar, "buscar_memoria_relevante", return_value=[]),
        patch.object(pensar, "buscar_contexto_relevante", return_value=""),
        patch.object(pensar, "ler_estado_luna", return_value={}),
        patch.object(pensar.assuntos, "contexto_relacionado", return_value=""),
        patch.object(tom, "obter_hint", return_value=""),
        patch.object(momento, "_jogos", {}),
        patch.object(dark_souls, "contexto", return_value=contexto_jogo),
        redirect_stdout(saida),
    ):
        contexto = momento.capturar(canal="proativo", janela="DARK SOULS REMASTERED", agora=instante)
        with patch.object(pensar, "_capturar_momento", return_value=contexto):
            fala = escopo["_gerar_fala_proativa"](prompts.prompt_dark_souls(evento),
                tarefa=tarefa if tarefa is not None else "dark_souls_" + evento["tipo"],
                max_tokens=180, variar=False, respeitar_intervalo=False)
    if not pedido:
        raise FalhaBancada("Não chegou ao modelo: " + saida.getvalue())
    ramo = re.search(r"Prompt: ([^·\n]+)", saida.getvalue())
    total_s = sum(t.get("total_s", 0) for t in tentativas)
    return {"evento": evento, "thinking": modo, "pedido": pedido, **resultado,
            "tentativas": tentativas, "total_s": total_s,
            "fala": str(fala or ""), "clima": getattr(fala, "clima", ""),
            "ramo": ramo.group(1).strip() if ramo else "DESCONHECIDO",
            "diagnostico": saida.getvalue(),
            "excede_ttl_antes_do_tts": total_s > dark_souls.TTL[evento["tipo"]]}


def salvar(destino, dados):
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(json.dumps(dados, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    linhas = ["# Dark Souls: thinking ligado e desligado", "",
              "Sequências independentes, intercaladas; cada modo recebe suas próprias falas anteriores.",
              "Mesmo prompt-base, eventos e seeds. Histórico diverge após o primeiro turno.",
              "Tempos medem geração completa; não incluem TTS nem validam FPS durante o jogo.", ""]
    for modo in ("desligado", "ligado"):
        itens = [r for r in dados["resultados"] if r["thinking"] == modo]
        tempos = [r["total_s"] for r in itens if "total_s" in r]
        linhas += [f"## Thinking {modo}", ""]
        if tempos:
            linhas += [f"Geração: mediana {statistics.median(tempos):.1f}s; máximo {max(tempos):.1f}s. "
                       f"Acima do TTL antes do TTS: {sum(r['excede_ttl_antes_do_tts'] for r in itens)}/{len(itens)}.", ""]
        for r in itens:
            linhas += [f"### Morte {r['evento']['mortes_sessao']}", "",
                       f"{r.get('total_s', 0):.1f}s · {r.get('pensamento_chars', 0)} caracteres de raciocínio · "
                       f"fim: {r.get('finish_reason', 'preparação')}", "", r["fala"] or "(sem fala utilizável)", ""]
    destino.with_suffix(".md").write_text("\n".join(linhas), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preparar", action="store_true")
    parser.add_argument("--mortes", type=int, default=8)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    if not 1 <= args.mortes <= 20:
        parser.error("--mortes deve estar entre 1 e 20")
    pensar = preparar_runtime()
    modelo = None if args.preparar else identidade(BASE, "gemma-4-12B")
    instante = time.time()
    destino = RAIZ / "logs/dark_souls" / (datetime.now().strftime("thinking-%Y%m%d-%H%M%S")
                                         + ("-preparado" if args.preparar else "") + ".json")
    dados = {"modelo": modelo, "preparacao": args.preparar, "mortes": args.mortes,
             "seed_base": args.seed, "instante_prompt": instante, "concluido": False,
             "fontes_sha256": {f: hashlib.sha256((RAIZ / f).read_bytes()).hexdigest() for f in
                                ("modulos/proativa.py", "modulos/prompts.py", "modulos/pensar.py")},
             "resultados": []}
    recentes = {"desligado": [], "ligado": []}
    mortes_recentes = {"desligado": [], "ligado": []}
    print(f"Resultados: {destino}", flush=True)
    try:
        for n in range(1, args.mortes + 1):
            ordem = ("desligado", "ligado") if n % 2 else ("ligado", "desligado")
            for modo in ordem:
                if not args.preparar:
                    conferir_identidade(identidade(BASE, "gemma-4-12B"), modelo)
                print(f"Gerando morte {n}/{args.mortes}, thinking {modo}...", flush=True)
                def executar(pedido):
                    if args.preparar:
                        return {"texto": "Amostra de preparação. [clima:zoeira]"}
                    return chamar(BASE, modelo, pedido)
                r = gerar_turno(pensar, {"tipo": "morte", "nome": "", "mortes_sessao": n, "incremento": 1},
                                recentes[modo], modo, args.seed + n, instante, executar, mortes_recentes=mortes_recentes[modo])
                dados["resultados"].append(r)
                if not args.preparar:
                    conferir_identidade(identidade(BASE, "gemma-4-12B"), modelo)
                salvar(destino, dados)
                print(f"{r.get('total_s', 0):.1f}s | raciocínio {r.get('pensamento_chars', 0)} chars | "
                      f"{r['fala']}", flush=True)
        dados["concluido"] = True
    except (Exception, FalhaBancada) as erro:
        dados["erro"] = str(erro)
        raise
    finally:
        salvar(destino, dados)
    print(f"Concluído: {destino.with_suffix('.md')}", flush=True)


if __name__ == "__main__":
    main()
