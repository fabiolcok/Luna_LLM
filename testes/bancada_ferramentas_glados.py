"""Roteador e persona reais, com execução de ferramentas substituída por fixtures.

Não abre navegador, toca música, grava notas ou chama Google. O histórico ácido
vem de respostas anteriores do experimento. Cada turno salva os dois pedidos e
a ordem entre roteamento, despacho simulado e apresentação para revisão humana.
"""
import argparse
from contextlib import ExitStack, redirect_stdout
from copy import deepcopy
import datetime as dt
import hashlib
import io
import json
from pathlib import Path
import re
import statistics
import sys
from types import ModuleType, SimpleNamespace
from unittest.mock import patch

from jsonschema import Draft7Validator

from testes.bancada_dark_souls_thinking import preparar_runtime, FalhaBancada
from testes.bancada_modelos import chamar, conferir_identidade, digest, gravar_json, identidade
from testes.testa_prompt_montagem import _Resposta

BASE = "http://127.0.0.1:6996"
PASTA = Path("logs/bancada_glados/20261012-ferramentas")
SEEDS = (12801, 12802)
FONTES = ("modulos/prompts.py", "modulos/pensar.py", "modulos/habilidades.py",
          "modulos/agenda_web.py", "modulos/fontes_conversa.py", "modulos/anotacoes.py",
          "modulos/momento.py", "modulos/rotina_jogos.py", "testes/prompt_golden.txt",
          "logs/experimentos_prompt/20261012-glados/smoke.json")
EVENTO = dict(titulo="Reunião do projeto", inicio="2026-10-13T14:00:00-03:00",
              fim="2026-10-13T15:00:00-03:00", dia_inteiro=False)
CASOS = [
    dict(id="spotify_tocar", usuario="Toca Metamorfose Ambulante do Raul Seixas no Spotify.",
         ferramenta="controlar_spotify", argumentos=dict(acao="tocar", nome_musica="Metamorfose Ambulante Raul Seixas"),
         retorno="Metamorfose Ambulante, de Raul Seixas, começou a tocar no Spotify.", acao="tocar"),
    dict(id="spotify_pausar", usuario="Pause a música no Spotify.", ferramenta="controlar_spotify",
         argumentos=dict(acao="pausar"), retorno="Música pausada no Spotify.", acao="pausar"),
    dict(id="agenda_consultar", usuario="Como está minha agenda?", ferramenta="ler_agenda_google",
         argumentos={}, retorno="Aqui estão os seus compromissos:\n- Reunião do projeto — terça-feira, 13 de outubro de 2026, às 14h.",
         eventos=[EVENTO]),
    dict(id="agenda_criar", usuario="Marque Reunião do projeto na agenda para 13/10/2026 às 14h.",
         ferramenta="adicionar_agenda", argumentos=dict(resumo="Reunião do projeto", data_hora_iso="2026-10-13T14:00:00"),
         retorno="Sucesso! O evento 'Reunião do projeto' foi criado para terça-feira, 13 de outubro de 2026, às 14h.",
         eventos=[EVENTO]),
    dict(id="nota_salvar", usuario="Anote no Obsidian: comprar café.", ferramenta="salvar_obsidian",
         argumentos=dict(conteudo="comprar café", titulo="Lista de compras"), retorno="SISTEMA: Nota salva em Lista de compras.md."),
    dict(id="navegador_abrir", usuario="Abra https://example.org/ no Firefox.", ferramenta="controlar_navegador",
         argumentos=dict(acao="abrir_url", parametro="https://example.org/"),
         retorno="A URL https://example.org/ foi aberta no Firefox.", acao="abrir_url"),
    dict(id="site_resumir", usuario="Resuma este artigo: https://example.org/artigo",
         ferramenta="resumir_site", argumentos=dict(url="https://example.org/artigo"),
         retorno="Artigo sintético: o Projeto Aurora anunciou uma atualização que reduz o tamanho "
                 "do instalador de 200 MB para 150 MB. Ainda não publicou testes de velocidade. "
                 "A atualização não adiciona português brasileiro."),
    dict(id="fonte_rascunho", usuario="Acompanhe o Projeto Voz e me avise quando tiver PT-BR: https://example.org/releases.atom",
         ferramenta="preparar_acompanhamento_fontes", argumentos=dict(assunto="Projeto Voz", interesse="quando tiver PT-BR", situacao=""),
         retorno="Rascunho preparado no cartão. Confira o assunto, a mudança e os links; "
                 "a consulta só começa depois de clicar em Confirmar acompanhamento."),
    dict(id="spotify_falha", usuario="Toca Metamorfose Ambulante do Raul Seixas no Spotify.",
         ferramenta="controlar_spotify", argumentos=dict(acao="tocar", nome_musica="Metamorfose Ambulante Raul Seixas"),
         retorno="Erro: o Spotify está desconectado. Nenhuma música foi iniciada.", acao="tocar"),
    dict(id="comentario_musica", usuario="Essa música é boa, gostei dela.", ferramenta=None, argumentos={}, retorno=""),
]


class BloqueioBancada(BaseException):
    pass


class Relogio(dt.datetime):
    @classmethod
    def now(cls, tz=None):
        valor = cls(2026, 10, 12, 17, 0)
        return valor if tz is None else valor.astimezone(tz)


def hashes():
    return {p: hashlib.sha256(Path(p).read_bytes()).hexdigest() for p in FONTES}


def historicos():
    amostras = json.loads(Path(FONTES[-1]).read_text(encoding="utf-8"))["resultados"]
    hist = []
    for id_ in ("chat_completo", "situacao_concreta"):
        item = next(r for r in amostras if r["caso"]["id"] == id_)
        hist += [dict(role="user", content=item["caso"]["usuario"]),
                 dict(role="assistant", content=re.sub(r"\s*\[clima:[^]]+\]", "", item["texto"]).strip())]
    return {"sem_historico": [], "historico_glados": hist}


def resposta_sdk(resultado):
    r = _Resposta()
    r.choices[0].message.content = resultado["texto"]
    r.choices[0].message.tool_calls = [SimpleNamespace(function=SimpleNamespace(**f))
                                       for f in resultado.get("ferramentas", [])]
    r.choices[0].finish_reason = resultado.get("finish_reason", "stop")
    r.usage.completion_tokens = resultado.get("uso", {}).get("completion_tokens", 0)
    return r


def executar_turno(p, caso, historico, seed, chamar_modelo):
    from modulos import agenda_web, dark_souls, fontes_conversa, rotina_jogos, tom
    from modulos.biblioteca_web import contexto_resposta
    from modulos.novidades_web import contexto_novidade
    chamadas, despachos, ordem = [], [], []
    servidor = ModuleType("servidor")
    for nome in ("atualizar_status", "atualizar_metricas", "atualizar_kaomoji", "atualizar_gif", "atualizar_pensamento"):
        setattr(servidor, nome, lambda *a, **kw: None)
    def llm(**kw):
        if kw.get("stream"):
            raise FalhaBancada("A interface não participa deste teste; reveja a montagem.")
        pedido = deepcopy(kw)
        pedido.update(pedido.pop("extra_body", {}))
        ramo = "roteador" if pedido.get("tools") else "persona"
        pedido.update(seed=seed, stream=True, stream_options={"include_usage": True}, cache_prompt=False)
        ordem.append(ramo)
        try:
            resultado = chamar_modelo(pedido, ramo)
        except Exception as erro:
            raise FalhaBancada(str(erro)) from erro
        chamadas.append(dict(ramo=ramo, pedido=pedido, pedido_sha256=digest(pedido), **resultado))
        return resposta_sdk(resultado)
    def stub(nome):
        def ferramenta(*args, **kwargs):
            ordem.append("ferramenta:" + nome)
            despacho = dict(nome=nome, args=list(args), argumentos=deepcopy(kwargs), simulado=True)
            despachos.append(despacho)
            if nome != caso["ferramenta"]:
                despacho["bloqueada"] = True
                raise BloqueioBancada("Ferramenta inesperada bloqueada: " + nome)
            despacho["retorno"] = caso["retorno"]
            if caso.get("eventos") is not None:
                return agenda_web.resultado(caso["retorno"], caso["eventos"],
                    titulo="Compromisso criado" if nome == "adicionar_agenda" else "Agenda")
            return caso["retorno"]
        return ferramenta
    mapa = {nome: stub(nome) for nome in p.FUNCOES_DISPONIVEIS}
    token_r = contexto_resposta.set(None)
    token_n = contexto_novidade.set(None)
    p._ultima_saudacao_ts = 1e20
    p._kaomoji_recentes.clear()
    saida, fala, erro = io.StringIO(), "", ""
    try:
        contextos = (patch.dict(sys.modules, {"servidor": servidor}),
              patch.object(p, "_chamar_llm", llm),
              patch.object(p, "datetime", SimpleNamespace(datetime=Relogio)),
              patch.object(p, "periodo_atual", return_value=("tarde", "Agora é TARDE. SÓ SE for cumprimentar, a saudação certa é 'boa tarde'.", 1.0)),
              patch.object(p, "_capturar_momento", return_value={"canal": "web", "janela": "Luna", "jogos": []}),
              patch.object(p, "MODO_PENSAMENTO", "desligado"),
              patch.object(p, "OPCOES_MODELO", {"chat_template_kwargs": {"enable_thinking": False}}),
              patch.object(p, "OPCOES_ROTEADOR", {"chat_template_kwargs": {"enable_thinking": False}}),
              patch.object(p, "ATIVAR_MEMORIA_PERMANENTE", False),
              patch.object(p.obsidian, "indice_notas", return_value="Lista de compras.md"),
              patch.object(p.obsidian, "ler_perfil", return_value="Gosta de jogos e humor exagerado."),
              patch.object(p.obsidian, "listar_memoria_episodica", return_value=[]),
              patch.object(p.obsidian, "salvar_nota", stub("salvar_obsidian")),
              patch.object(p, "buscar_memoria_relevante", return_value=[]),
              patch.object(p, "buscar_contexto_relevante", return_value=""),
              patch.object(p.assuntos, "contexto_relacionado", return_value=""),
              patch.object(p, "ler_estado_luna", return_value={}),
              patch.object(p, "obter_janela_em_foco", return_value="Luna"),
              patch.object(p, "_executar_registrar_rotina_jogo", stub("registrar_rotina_jogo")),
              patch.object(rotina_jogos, "_carregar", return_value={"jogos": {}}),
              patch.object(tom, "obter_hint", return_value=""),
              patch.object(dark_souls, "contexto", return_value=None),
              patch.object(fontes_conversa, "propor", stub("preparar_acompanhamento_fontes")),
              patch.dict(p.FUNCOES_DISPONIVEIS, mapa),
              patch("modulos.metricas_ferramentas.registrar_uso"),
              p.controle.executar(), redirect_stdout(saida))
        with ExitStack() as pilha:
            for contexto in contextos:
                pilha.enter_context(contexto)
            try:
                fala = p.gerar_resposta(caso["usuario"], deepcopy(historico), salvar=False,
                                       responder_completo=True, presenca_pc=True, max_tokens=500)
            except BloqueioBancada as bloqueio:
                erro = str(bloqueio)
    finally:
        contexto_resposta.reset(token_r)
        contexto_novidade.reset(token_n)
    return dict(fala=str(fala), chamadas=chamadas, despachos=despachos, ordem=ordem,
                erro=erro, diagnostico=saida.getvalue(), clima=p.obter_clima_resposta(),
                total_s=sum(c.get("total_s", 0) for c in chamadas))


def preparar(pasta, personagem="GLaDOS", historicos_teste=None):
    if pasta.exists():
        raise ValueError("Use outra pasta para preservar a rodada anterior.")
    with redirect_stdout(io.StringIO()):
        p = preparar_runtime()
    hist = historicos() if historicos_teste is None else historicos_teste
    total = len(CASOS) * len(hist) * len(SEEDS)
    suite = dict(personagem=personagem, casos=CASOS, historicos=hist, seeds=SEEDS, fontes=hashes(), capturas=[],
                 metodo=f"10 situações × {len(hist)} históricos × 2 seeds: {total} turnos. "
                        "Roteador e persona reais; despacho simulado e fontes pessoais vazias.")
    for caso in CASOS:
        for nome, h in hist.items():
            def simular(pedido, ramo):
                return dict(texto="" if ramo == "roteador" and caso["ferramenta"] else
                            "SEM_FERRAMENTA" if ramo == "roteador" else "Preparação. [clima:zoeira]",
                    ferramentas=[dict(name=caso["ferramenta"], arguments=json.dumps(caso["argumentos"], ensure_ascii=False))]
                    if ramo == "roteador" and caso["ferramenta"] else [])
            r = executar_turno(p, caso, h, SEEDS[0], simular)
            assert not r["erro"] and len(r["chamadas"]) == 2, (caso["id"], r)
            assert personagem not in r["chamadas"][0]["pedido"]["messages"][0]["content"]
            assert personagem in r["chamadas"][1]["pedido"]["messages"][0]["content"]
            suite["capturas"].append(dict(caso=caso["id"], historico=nome,
                pedido_roteador=r["chamadas"][0]["pedido"], pedido_persona_exemplo=r["chamadas"][1]["pedido"]))
    suite["sha256"] = digest(suite)
    gravar_json(pasta / "suite.json", suite)
    print(f"Preparados {total} turnos; roteador sem persona e segunda chamada {personagem}: {pasta}", flush=True)


def rodar(pasta):
    suite = json.loads((pasta / "suite.json").read_text(encoding="utf-8"))
    assert digest({k:v for k,v in suite.items() if k != "sha256"}) == suite["sha256"]
    assert hashes() == suite["fontes"], "Código mudou depois da preparação"
    from modulos.turbollm_api import recarregar_modelo
    pronto = recarregar_modelo(BASE + "/v1", segundos=60)
    if not pronto.get("ok"):
        raise RuntimeError(pronto)
    modelo = identidade(BASE, "gemma-4-12B")
    with redirect_stdout(io.StringIO()):
        p = preparar_runtime()
    destino = pasta / "resultados.json"
    dados = (json.loads(destino.read_text(encoding="utf-8")) if destino.exists() else
        dict(modelo=modelo, suite_sha256=suite["sha256"], iniciado=dt.datetime.now().isoformat(),
             concluido=False, resultados=[]))
    conferir_identidade(modelo, dados["modelo"])
    assert dados["suite_sha256"] == suite["sha256"]
    feitos = {(r["caso"], r["historico"], r["seed"]) for r in dados["resultados"]}
    total = len(suite["casos"]) * len(suite["historicos"]) * len(suite["seeds"])
    try:
        for i,caso in enumerate(suite["casos"]):
            for seed in suite["seeds"]:
                nomes = list(suite["historicos"])
                if (i + seed) % 2:
                    nomes.reverse()
                for nome in nomes:
                    if (caso["id"], nome, seed) in feitos:
                        continue
                    captura = next(c for c in suite["capturas"] if c["caso"] == caso["id"] and c["historico"] == nome)
                    def executar(pedido, ramo):
                        assert hashes() == suite["fontes"], "Fontes mudaram durante a bancada"
                        if ramo == "roteador":
                            congelado = {**deepcopy(captura["pedido_roteador"]), "seed": seed}
                            assert pedido == congelado, "Roteador diferente do snapshot"
                        conferir_identidade(identidade(BASE, "gemma-4-12B"), modelo)
                        resultado = chamar(BASE, modelo, pedido)
                        conferir_identidade(identidade(BASE, "gemma-4-12B"), modelo)
                        return resultado
                    r = executar_turno(p, caso, suite["historicos"][nome], seed, executar)
                    dados["resultados"].append(dict(caso=caso["id"], historico=nome, seed=seed, **r))
                    gravar_json(destino, dados)
                    print(f"[{len(dados['resultados'])}/{total}] {caso['id']} {nome} {seed}: "
                          f"{[d['nome'] for d in r['despachos']]} | {r['total_s']:.2f}s | {r['erro'] or r['fala']}", flush=True)
        assert hashes() == suite["fontes"]
        dados.update(concluido=True, terminado=dt.datetime.now().isoformat(), fontes_preservadas=True)
    finally:
        gravar_json(destino, dados)
    resumir(pasta)


def resumir(pasta):
    suite = json.loads((pasta / "suite.json").read_text(encoding="utf-8"))
    dados = json.loads((pasta / "resultados.json").read_text(encoding="utf-8"))
    alertas, linhas = [], ["# Ferramentas com " + suite.get("personagem", "GLaDOS"), "", suite["metodo"], "",
                          "Todas as execuções de ferramentas abaixo são simuladas.", ""]
    for r in dados["resultados"]:
        caso = next(c for c in suite["casos"] if c["id"] == r["caso"])
        roteador = next(c for c in r["chamadas"] if c["ramo"] == "roteador")
        f = roteador["ferramentas"]
        problemas = []
        if [t["name"] for t in f] != ([caso["ferramenta"]] if caso["ferramenta"] else []):
            problemas.append("ferramenta diferente da esperada")
        if not caso["ferramenta"] and roteador["texto"].strip() != "SEM_FERRAMENTA":
            problemas.append("marcador SEM_FERRAMENTA ausente")
        schemas = {t["function"]["name"]: t["function"]["parameters"] for t in roteador["pedido"]["tools"]}
        for chamada in f:
            try:
                args = json.loads(chamada["arguments"])
                erros = list(Draft7Validator(schemas[chamada["name"]]).iter_errors(args))
                if erros:
                    problemas.append("argumentos fora do schema")
                if caso.get("acao") and args.get("acao") != caso["acao"]:
                    problemas.append("ação incorreta")
                if caso["id"] == "navegador_abrir" and args.get("parametro") != "https://example.org/":
                    problemas.append("URL do navegador incorreta")
                if caso["id"] == "site_resumir" and args.get("url") != "https://example.org/artigo":
                    problemas.append("URL do artigo incorreta")
                if caso["id"] == "agenda_criar" and not str(args.get("data_hora_iso", "")).startswith("2026-10-13T14:00"):
                    problemas.append("data/hora da agenda incorreta")
            except (ValueError, KeyError, TypeError):
                problemas.append("JSON ou ferramenta inválida")
        if r["erro"]:
            problemas.append(r["erro"])
        if any(c["finish_reason"] not in (("stop", "tool_calls") if c["ramo"] == "roteador" else ("stop",))
               for c in r["chamadas"]):
            problemas.append("chamada cortada ou finalização inesperada")
        alertas.append(dict(caso=r["caso"], historico=r["historico"], seed=r["seed"], alertas=problemas))
        linhas += [f"## {r['caso']} · {r['historico']} · seed {r['seed']}", "", caso["usuario"], "",
                   "Esperado: " + str(caso["ferramenta"]), "Ordem: " + " → ".join(r["ordem"]),
                   "Despachos: " + json.dumps(r["despachos"], ensure_ascii=False), "",
                   r["fala"] or r["erro"] or "(sem resposta)", "", "Triagem: " + str(problemas), ""]
        for c in r["chamadas"]:
            linhas += [f"<details><summary>{c['ramo']} · {c['total_s']:.2f}s · {c['finish_reason']}</summary>", "",
                       c["texto"] or "(sem texto)", "", json.dumps(c["ferramentas"], ensure_ascii=False), "", "</details>", ""]
    (pasta / "respostas.md").write_text("\n".join(linhas), encoding="utf-8")
    gravar_json(pasta / "triagem.json", alertas)
    resumo = dict(turnos=len(dados["resultados"]), turnos_com_alerta=sum(bool(r["alertas"]) for r in alertas),
                  chamadas=sum(len(r["chamadas"]) for r in dados["resultados"]),
                  mediana_turno_s=statistics.median(r["total_s"] for r in dados["resultados"]),
                  aviso="Triagem não mede fidelidade da confirmação ou qualidade do sarcasmo; exige leitura humana.")
    gravar_json(pasta / "resumo_tecnico.json", resumo)
    print(json.dumps(resumo, ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("acao", choices=("preparar", "rodar", "resumir"))
    parser.add_argument("--pasta", type=Path, default=PASTA)
    args = parser.parse_args()
    {"preparar": preparar, "rodar": rodar, "resumir": resumir}[args.acao](args.pasta)
