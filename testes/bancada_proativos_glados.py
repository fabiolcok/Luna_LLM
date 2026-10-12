"""Mede o prompt temporário nos proativos reais, sem áudio ou serviços externos.

Fixtures não são notícias atuais. A preparação congela pedidos; a execução passa
pela limpeza, validação de horas e antirrepetição da produção e salva cada turno.
"""
import argparse
import ast
from collections import defaultdict
from contextlib import redirect_stdout
from copy import deepcopy
from datetime import datetime
import hashlib
import io
import json
from pathlib import Path
import random
import re
import statistics
import sys
import time
from types import ModuleType, SimpleNamespace
from unittest.mock import patch

from testes.bancada_dark_souls_thinking import (
    FalhaBancada, extrair, gerar_turno, preparar_runtime,
)
from testes.bancada_modelos import chamar, conferir_identidade, digest, gravar_json, identidade
from testes.testa_prompt_montagem import _Resposta

BASE = "http://127.0.0.1:6996"
PASTA = Path("logs/bancada_glados/20261012-proativos-jogos")
INSTANTE = datetime(2026, 10, 12, 17, 0).timestamp()
SEEDS = (12601, 12602)
FONTES = ("modulos/prompts.py", "modulos/pensar.py", "modulos/proativa.py",
          "modulos/momento.py", "modulos/antirrepeticao.py", "modulos/falar.py",
          "testes/prompt_golden.txt")


def hashes():
    return {f: hashlib.sha256(Path(f).read_bytes()).hexdigest() for f in FONTES}


def expressao(funcao, alvo, trecho, valores):
    arvore = ast.parse(Path("modulos/proativa.py").read_text(encoding="utf-8"))
    escopo = arvore if funcao is None else next(
        n for n in arvore.body if isinstance(n, ast.FunctionDef) and n.name == funcao)
    candidatos = [n.value for n in ast.walk(escopo) if isinstance(n, ast.Assign)
                  and any(isinstance(t, ast.Name) and t.id == alvo for t in n.targets)
                  and trecho in ast.unparse(n.value)]
    if len(candidatos) != 1:
        raise RuntimeError(f"Construtor mudou: {funcao}/{alvo}/{trecho}")
    return eval(compile(ast.Expression(candidatos[0]), "modulos/proativa.py", "eval"), valores)


def casos():
    from modulos import prompts
    regra = expressao(None, "REGRA_PERSONA", "Fale DIRETAMENTE", {"NOME_USUARIO": "Usuário"})
    lista = []
    def incluir(id_, grupo, tarefa, briefing, teto, **kw):
        lista.append(dict(id=id_, grupo=grupo, tarefa=tarefa, briefing=briefing,
                          max_tokens=teto, variar=kw.pop("variar", True), **kw))
    for id_, titulo, resumo, n in (
        ("rss_oled", "Teste de monitor OLED encontra burn-in após 8.000 horas",
         "Após 30 meses, o teste encontrou marca permanente e uma linha vertical. "
         "O resumo não informa a causa dessa linha nem como eram as sessões.", 6),
        ("rss_conexao", "Jogo solo passa a exigir conexão permanente",
         "O estúdio anunciou a exigência de internet mesmo para jogar sozinho. "
         "Não informou o motivo da decisão.", 1),
        ("rss_gpu_rumor", "Fabricante pode descontinuar uma placa para priorizar outra linha",
         "A notícia relata uma possibilidade, ainda sem confirmação da fabricante. "
         "Não informa mudança de preço, especificação ou data.", 3),
    ):
        amostra = f"Título: {titulo}. Resumo: {resumo}"
        briefing = expressao("_tarefa_radar_rss", "prompt", "Saiu 1" if n == 1 else "Saíram",
                             dict(amostra=amostra, n=n, REGRA_PERSONA=regra))
        incluir(id_, "radar", "radar_rss", briefing, 360)
    for produto, n in (("batedeira", 1), ("SSD de 2 TB", 3)):
        briefing = expressao("_tarefa_radar_promocoes", "prompt", "Apareceu 1" if n == 1 else "Apareceram",
                             dict(produto_d=produto, canal_d="@canal_teste", n=n, REGRA_PERSONA=regra))
        incluir("promo_" + ("batedeira" if n == 1 else "ssd"), "promocoes",
                "radar_promocoes", briefing, 200)
    item = dict(assunto="Sopro", interesse="voz em português brasileiro",
                situacao="A voz funcionou localmente, mas o sotaque português incomodou.",
                resumo="A fonte menciona PT-BR como plano futuro.",
                evidencia="PT-BR está no planejamento; não há versão para testar nem data informada.",
                etapa="plano")
    incluir("fonte_sopro_plano", "acompanhamentos", "Acompanhamento · Sopro",
            prompts.prompt_acompanhamento_fonte(item), 220, variar=False)
    briefing = expressao("_tarefa_acompanhamentos", "prompt", "O usuário pediu explicitamente",
                         {"item": {"assunto": "pedido ao provedor para resolver CGNAT e acesso externo"}})
    incluir("acompanhamento_cgnat", "acompanhamentos", "acompanhamento", briefing, 100, variar=False)
    instrucao = expressao("_tarefa_monitorar_steam", "instrucao", "Puxe UM detalhe", {})
    for id_, nome, dados in (
        ("steam_dark_souls", "DARK SOULS REMASTERED",
         "Jogo: DARK SOULS REMASTERED. Você já tem 18 horas totais nele. "
         "Faz uns 7 dias que você não abria esse jogo. Sobre o jogo: RPG de ação e exploração em Lordran."),
        ("steam_cities", "Cities: Skylines II",
         "Jogo: Cities: Skylines II. Você já tem 4 horas totais nele. "
         "Sobre o jogo: simulação de construção e gestão de uma cidade."),
        ("steam_contraste", "AION 2",
         "Jogo: AION 2. Você já tem 12 horas totais nele. "
         "Sobre o jogo: RPG online com exploração e combate."),
    ):
        briefing = expressao("_tarefa_monitorar_steam", "prompt", "O usuário acabou de abrir",
                             dict(nome=nome, dados=dados, _prompts=prompts, instrucao=instrucao,
                                  REGRA_PERSONA=regra, _dica_recursos_prompt=lambda _: ""))
        hist = ([{"role": "user", "content": "Vou jogar Dark Souls agora.", "instante": INSTANTE - 20},
                 {"role": "assistant", "content": "Certo.", "instante": INSTANTE - 15}]
                if id_ == "steam_contraste" else [])
        incluir(id_, "steam", "steam_abriu_" + nome, briefing, 150, janela=nome, historico=hist)
    for id_, tipo, nome, recentes in (
        ("ds_morte", "morte", "", []),
        ("ds_morte_apos_chefe", "morte", "", ["O Demônio Touro caiu. Essa vitória merece barulho."]),
        ("ds_taurus", "chefe", "Taurus Demon", []),
        ("ds_fogueira", "fogueira", "Undead Burg", []),
    ):
        evento = dict(tipo=tipo, nome=nome, mortes_sessao=9, incremento=1)
        incluir(id_, "dark_souls", "dark_souls_" + tipo, prompts.prompt_dark_souls(evento), 180,
                variar=False, evento=evento, recentes=recentes)
    return lista


def gerar(pensar, caso, seed, executar, recentes=None, mortes=None):
    if caso.get("evento"):
        return gerar_turno(pensar, caso["evento"], recentes if recentes is not None else list(caso.get("recentes", [])),
                           "desligado", seed, INSTANTE, executar, mortes_recentes=mortes)
    from modulos import dark_souls, momento, prompts, tom
    from modulos.turbollm_api import opcoes_pensamento
    tentativas = []
    servidor = ModuleType("servidor")
    for nome in ("atualizar_status", "atualizar_metricas", "atualizar_kaomoji", "atualizar_gif"):
        setattr(servidor, nome, lambda *a, **kw: None)
    def interceptar(**kw):
        pedido = deepcopy(kw)
        pedido.update(pedido.pop("extra_body", {}))
        pedido.update(seed=seed, stream=True, stream_options={"include_usage": True}, cache_prompt=False)
        try:
            resultado = executar(deepcopy(pedido))
        except Exception as erro:
            raise FalhaBancada(str(erro)) from erro
        tentativas.append(dict(pedido=pedido, **resultado))
        resposta = _Resposta()
        resposta.choices[0].message.content = resultado["texto"]
        resposta.choices[0].finish_reason = resultado.get("finish_reason", "stop")
        resposta.usage.completion_tokens = resultado.get("uso", {}).get("completion_tokens", 0)
        return resposta
    def responder(instrucao, historico, **kw):
        return pensar._reescrever_como_luna(instrucao, "", historico, max_tokens=kw["max_tokens"],
                                          tarefa_proativa=kw.get("tarefa_proativa"))
    abordagens = expressao(None, "_ABORDAGENS", "um comentário curto", {})
    escopo = dict(re=re, random=random.Random(seed), _ABORDAGENS=abordagens, _prompts=prompts,
                  _historico_principal=deepcopy(caso.get("historico", [])), _historico_proativo=[],
                  _falas_recentes=recentes if recentes is not None else [], _falas_morte_recentes=[],
                  momento=SimpleNamespace(conversa_recente=lambda h: momento.conversa_recente(h, INSTANTE)),
                  _execucoes=SimpleNamespace(verificar=lambda: None, contexto=SimpleNamespace(get=lambda: None)),
                  cor=SimpleNamespace(amarelo=lambda *a: None, vermelho=lambda *a: None),
                  gerar_resposta=responder, obter_clima_resposta=pensar.obter_clima_resposta,
                  _limpar_visual_proativo=lambda: None)
    extrair("modulos/proativa.py", ["_contraste_jogo_anunciado", "_contexto_recente_para_proativo",
                                     "_gerar_fala_proativa", "_FalaProativa"], escopo)
    pensar._presenca_pc.set(True)
    pensar._ultima_saudacao_ts = time.time()
    pensar._kaomoji_recentes.clear()
    _, opcoes = opcoes_pensamento("desligado")
    saida = io.StringIO()
    with (patch.dict(sys.modules, {"servidor": servidor}),
          patch.object(pensar, "datetime", SimpleNamespace(datetime=SimpleNamespace(
              now=lambda: datetime.fromtimestamp(INSTANTE)))),
          patch.object(pensar, "MODO_PENSAMENTO", "desligado"),
          patch.object(pensar, "OPCOES_MODELO", opcoes),
          patch.object(pensar, "_chamar_llm", interceptar),
          patch.object(pensar.obsidian, "ler_perfil", return_value="Gosta de jogos e humor exagerado."),
          patch.object(pensar.obsidian, "listar_memoria_episodica", return_value=[]),
          patch.object(pensar, "buscar_memoria_relevante", return_value=[]),
          patch.object(pensar, "buscar_contexto_relevante", return_value=""),
          patch.object(pensar, "ler_estado_luna", return_value={}),
          patch.object(pensar.assuntos, "contexto_relacionado", return_value=""),
          patch.object(tom, "obter_hint", return_value=""),
          patch.object(momento, "_jogos", {}), patch.object(dark_souls, "contexto", return_value=None),
          pensar.controle.executar() as execucao, redirect_stdout(saida)):
        contexto = momento.capturar(canal="proativo", janela=caso.get("janela", "Luna"),
                                   historico=caso.get("historico", []), agora=INSTANTE)
        with patch.object(pensar, "_capturar_momento", return_value=contexto):
            fala = escopo["_gerar_fala_proativa"](caso["briefing"], tarefa=caso["tarefa"],
                max_tokens=caso["max_tokens"], variar=caso["variar"], respeitar_intervalo=False)
    if not tentativas:
        raise FalhaBancada("Não chegou ao modelo: " + saida.getvalue())
    diag = execucao.diagnostico
    return dict(tentativas=tentativas, pedido=tentativas[-1]["pedido"],
                fala=str(fala or ""), clima=getattr(fala, "clima", ""),
                sugestoes=getattr(fala, "sugestoes_novidade", []),
                ramo=f"{diag.get('caminho_prompt', '?')} + {diag.get('emocao', '?')}",
                diagnostico=saida.getvalue(), total_s=sum(t.get("total_s", 0) for t in tentativas))


def preparar(pasta, personagem="GLaDOS"):
    if pasta.exists():
        raise ValueError("Use uma pasta nova para preservar resultados anteriores.")
    with redirect_stdout(io.StringIO()):
        pensar = preparar_runtime()
    suite = dict(criado=datetime.now().isoformat(), personagem=personagem, fontes=hashes(), seeds=SEEDS, instante=INSTANTE,
                 casos=[], mortes_seguidas=8, metodo="14 casos independentes × 2 seeds e 8 mortes contínuas. "
                 "Prompt temporário atual, sem A/B. Mesmos tetos e preparação da produção; sem áudio ou serviços.")
    for caso in casos():
        amostras = []
        for seed in SEEDS:
            r = gerar(pensar, caso, seed, lambda p: {"texto": "Preparação. [clima:duvida]"})
            sistema = r["pedido"]["messages"][0]["content"]
            assert personagem in sistema and r["ramo"].startswith("ENXUTO_")
            amostras.append(dict(seed=seed, pedido=r["pedido"], ramo=r["ramo"]))
        suite["casos"].append(dict(caso=caso, amostras=amostras))
    suite["sha256"] = digest(suite)
    gravar_json(pasta / "suite.json", suite)
    print(f"Preparados {len(suite['casos'])} casos e 8 mortes em sequência: {pasta}", flush=True)


def rodar(pasta):
    suite = json.loads((pasta / "suite.json").read_text(encoding="utf-8"))
    assert digest({k:v for k,v in suite.items() if k != "sha256"}) == suite["sha256"]
    assert hashes() == suite["fontes"], "Fontes mudaram depois da preparação"
    from modulos.turbollm_api import recarregar_modelo
    pronto = recarregar_modelo(BASE + "/v1", segundos=60)
    if not pronto.get("ok"):
        raise RuntimeError(pronto)
    modelo = identidade(BASE, "gemma-4-12B")
    with redirect_stdout(io.StringIO()):
        pensar = preparar_runtime()
    destino = pasta / "resultados.json"
    dados = (json.loads(destino.read_text(encoding="utf-8")) if destino.exists() else
             dict(modelo=modelo, suite_sha256=suite["sha256"], iniciado=datetime.now().isoformat(),
                  concluido=False, resultados=[]))
    conferir_identidade(modelo, dados["modelo"])
    assert dados["suite_sha256"] == suite["sha256"]
    if not dados["resultados"]:
        warm = deepcopy(suite["casos"][0]["amostras"][0]["pedido"])
        warm["max_tokens"] = 16
        dados["warmup_excluido"] = chamar(BASE, modelo, warm)
    feitos = {(r["id"], r["seed"]) for r in dados["resultados"]}
    def executar(p):
        assert hashes() == suite["fontes"], "Código mudou durante a bancada"
        conferir_identidade(identidade(BASE, "gemma-4-12B"), modelo)
        r = chamar(BASE, modelo, p)
        conferir_identidade(identidade(BASE, "gemma-4-12B"), modelo)
        return r
    try:
        for item in suite["casos"]:
            for amostra in item["amostras"]:
                caso, seed = item["caso"], amostra["seed"]
                if (caso["id"], seed) in feitos:
                    continue
                # Conferir o snapshot também detecta variação de montagem entre preparo e execução.
                primeira_chamada = [True]
                def executar_snapshot(p):
                    if primeira_chamada[0]:
                        assert p == amostra["pedido"], "Pedido diferente do snapshot: " + caso["id"]
                        primeira_chamada[0] = False
                    return executar(p)
                r = gerar(pensar, caso, seed, executar_snapshot)
                dados["resultados"].append(dict(id=caso["id"], grupo=caso["grupo"], seed=seed, **r))
                gravar_json(destino, dados)
                print(f"[{len(dados['resultados'])}/36] {caso['id']} {seed}: {r['total_s']:.2f}s | {r['fala']}", flush=True)
        from testes.bancada_repeticao_dark_souls import INICIAL
        recentes, mortes = [INICIAL[:120]], [INICIAL]
        for anterior in dados["resultados"]:
            if anterior["grupo"] == "sequencia_mortes" and anterior["fala"]:
                recentes.append(anterior["fala"][:120]); del recentes[:-5]
                mortes.append(anterior["fala"]); del mortes[:-5]
        for n in range(1, suite["mortes_seguidas"] + 1):
            seed, id_ = 12700 + n, f"sequencia_morte_{n}"
            if (id_, seed) in feitos:
                continue
            evento = dict(tipo="morte", nome="", mortes_sessao=n, incremento=1)
            r = gerar(pensar, dict(evento=evento), seed, executar, recentes, mortes)
            dados["resultados"].append(dict(id=id_, grupo="sequencia_mortes", seed=seed, **r))
            gravar_json(destino, dados)
            print(f"[{len(dados['resultados'])}/36] {id_}: {len(r['tentativas'])} chamada(s), "
                  f"{r['total_s']:.2f}s | {r['fala'] or '(descartada)'}", flush=True)
        assert hashes() == suite["fontes"]
        dados.update(concluido=True, terminado=datetime.now().isoformat(), fontes_preservadas=True)
    finally:
        gravar_json(destino, dados)
    resumir(pasta)


def resumir(pasta):
    suite = json.loads((pasta / "suite.json").read_text(encoding="utf-8"))
    dados = json.loads((pasta / "resultados.json").read_text(encoding="utf-8"))
    linhas = ["# Proativos e jogos com " + suite.get("personagem", "GLaDOS"), "", suite["metodo"], "",
              "Notícias e dados são sintéticos; não são uma consulta sobre lançamentos reais.",
              "Tempos não incluem TTS, FPS nem disputa da GPU com um jogo.", ""]
    grupos = defaultdict(list)
    for r in dados["resultados"]:
        grupos[r["grupo"]].append(r)
        linhas += [f"## {r['id']} — seed {r['seed']}", "", f"{r['ramo']} · {r['total_s']:.2f}s · "
                   f"{len(r['tentativas'])} chamada(s) · clima: {r['clima']}", "", r["fala"] or "(descartada)", ""]
        if r.get("sugestoes"):
            linhas += ["Botões: " + json.dumps(r["sugestoes"], ensure_ascii=False), ""]
        linhas += ["<details><summary>Saída bruta</summary>", ""]
        for t in r["tentativas"]:
            linhas += [f"Fim: {t.get('finish_reason')} · {t.get('total_s', 0):.2f}s", "", t["texto"], ""]
        linhas += ["</details>", ""]
    (pasta / "respostas.md").write_text("\n".join(linhas), encoding="utf-8")
    resumo = {}
    for grupo, itens in grupos.items():
        tentativas = [t for r in itens for t in r["tentativas"]]
        resumo[grupo] = dict(turnos=len(itens), falas=sum(bool(r["fala"]) for r in itens),
            chamadas=len(tentativas), fim_length=sum(t.get("finish_reason") == "length" for t in tentativas),
            thinking=sum(bool(t.get("pensamento_chars")) for t in tentativas),
            ferramentas=sum(bool(t.get("ferramentas")) for t in tentativas),
            mediana_s=statistics.median(r["total_s"] for r in itens), max_s=max(r["total_s"] for r in itens),
            mediana_palavras=statistics.median(len(r["fala"].split()) for r in itens))
    gravar_json(pasta / "resumo_tecnico.json", resumo)
    print(json.dumps(resumo, ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("acao", choices=("preparar", "rodar", "resumir"))
    p.add_argument("--pasta", type=Path, default=PASTA)
    a = p.parse_args()
    {"preparar": preparar, "rodar": rodar, "resumir": resumir}[a.acao](a.pasta)
