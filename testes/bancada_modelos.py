"""Congela chamadas reais da Luna e as repete no modelo carregado no TurboLLM.

Não troca modelo, não executa ferramentas e não salva conversas. A preparação usa
fixtures; a execução lê o snapshot, sem importar pensar ou consultar memória pessoal.
Veja testes/README.md para preparar, executar e comparar duas rodadas.
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
import re
import statistics
import sys
import time
from types import ModuleType
from unittest.mock import patch
from urllib.request import Request, urlopen

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))
PASTA = RAIZ / "logs" / "bancada_modelos"
SUITE = PASTA / "suite.json"


def codigo_sem_boot(fonte, arquivo):
    arvore = ast.parse(fonte)
    # pensar chama garantir_modelo_turbollm na importação. Preserva suas funções
    # byte a byte, retirando só esse disparo para não trocar o modelo do usuário.
    arvore.body = [n for n in arvore.body if not (
        isinstance(n, ast.Expr) and isinstance(n.value, ast.Call)
        and isinstance(n.value.func, ast.Name) and n.value.func.id == "garantir_modelo_turbollm")]
    return compile(arvore, arquivo, "exec")


def carregar_pensar():
    # Importar antes do isolamento mantém o mesmo controlador no diagnóstico e na persona;
    # restaurar sys.modules e importar avaliações depois criava uma segunda instância.
    import modulos.avaliacoes

    memoria = ModuleType("modulos.memoria")
    def bloqueado(*args, **kwargs):
        raise AssertionError("A bancada tentou acessar memória real sem fixture")
    for nome in ("buscar_contexto_relevante", "salvar_conversa", "ler_memoria_permanente",
                 "analisar_e_salvar_fato", "ler_estado_luna", "buscar_memoria_relevante"):
        setattr(memoria, nome, bloqueado)
    # Só o cálculo do período participa do prompt. Não inicializa Kokoro/áudio.
    falar = ModuleType("modulos.falar")
    import datetime as dt
    falar.__dict__["datetime"] = dt
    arvore = ast.parse((RAIZ / "modulos/falar.py").read_text(encoding="utf-8"))
    arvore.body = [n for n in arvore.body if isinstance(n, ast.FunctionDef) and n.name == "periodo_atual"]
    exec(compile(arvore, "modulos/falar.py", "exec"), falar.__dict__)
    falar.limpar_texto_para_voz = bloqueado
    pensar = ModuleType("_bancada_pensar")
    pensar.__file__ = str(RAIZ / "modulos/pensar.py")
    fonte = Path(pensar.__file__).read_text(encoding="utf-8")
    with patch.dict(sys.modules, {"modulos.memoria": memoria, "modulos.falar": falar}):
        exec(codigo_sem_boot(fonte, pensar.__file__), pensar.__dict__)
    return pensar


def digest(dados):
    return hashlib.sha256(json.dumps(dados, sort_keys=True, ensure_ascii=False,
                                    separators=(",", ":")).encode()).hexdigest()


def gravar_json(caminho, dados):
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_text(json.dumps(dados, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def preparar(destino):
    if destino.exists():
        raise ValueError("Snapshot já existe. Use outro --suite para uma nova comparação.")
    # O perfil e o nome nos prompts são sintéticos, mesmo na máquina do dono.
    with patch.dict("os.environ", {"USUARIO_NOME": "Usuário"}):
        pensar = carregar_pensar()
        from modulos import momento, tom
        from testes.bancada_persona import CENARIOS, PERFIL_NEUTRO

    selecionados = ["piada_nao_amacia", "opiniao_sem_carimbo", "gosto_proprio",
                    "comida_cotidiana", "referencia_vaga", "proativo_jogo_aberto",
                    "dado_overwatch", "proativo_rss_com_atitude"]
    por_id = {c["id"]: c for c in CENARIOS}
    casos = [deepcopy(por_id[nome]) for nome in selecionados]
    for c in casos:
        if not c.get("usuario"):
            c["responder_completo"] = False
    casos += [
        {"id": "filme_continuidade", "usuario": "Esse filme é de que ano?",
         "historico": [{"role": "user", "content": "Estou vendo Três Homens em Conflito."},
                       {"role": "assistant", "content": "O faroeste do Sergio Leone."}],
         "exige_grupos": [["1966"]], "proibidos": ["1972", "qual filme"]},
        {"id": "placar_desconhecido", "usuario": "Quanto está o placar da minha partida?",
         "janela": "Overwatch", "jogos": ["Overwatch"],
         "exige_grupos": [["não", "sem acesso", "me diz", "me diga"]],
         "proibidos": ["2 a 1", "3 a 0"]},
        {"id": "roteador_desabafo", "roteador": True, "usuario": "Hoje foi puxado.",
         "historico": [{"role": "user", "content": "Toca uma música."}], "ferramentas": []},
        {"id": "roteador_comentario", "roteador": True, "usuario": "Voltei da partida, que surra.",
         "janela": "Overwatch", "jogos": ["Overwatch"], "ferramentas": []},
        {"id": "roteador_gameplay", "roteador": True,
         "usuario": "Como faço para curar meus aliados no Overwatch?", "janela": "Overwatch",
         "jogos": ["Overwatch"], "ferramentas": ["duvida_do_jogo"]},
        {"id": "roteador_musica", "roteador": True,
         "usuario": "Toca Metamorfose Ambulante do Raul Seixas no Spotify.",
         "ferramentas": ["controlar_spotify"], "argumentos": {"acao": "tocar"}},
    ]
    capturados = []

    # Interromper ANTES de receber resposta impede chegar ao despacho de ferramentas,
    # pós-processamento, import do servidor e gravações do fluxo normal.
    class Capturado(BaseException):
        pass

    for c in casos:
        parametros = {}

        def interceptar(**kw):
            parametros.update(deepcopy(kw))
            raise Capturado()

        hist = deepcopy(c.get("historico", []))
        agora = time.time()
        for msg in hist:
            msg["instante"] = agora - 20
        pensar._ultima_saudacao_ts = agora
        pensar._kaomoji_recentes.clear()
        pensar._presenca_pc.set(True)
        saida = io.StringIO()
        with (
            patch.object(pensar, "_chamar_llm", interceptar),
            patch.object(pensar, "MODO_PENSAMENTO", "desligado"),
            patch.object(pensar, "OPCOES_MODELO", {"chat_template_kwargs": {"enable_thinking": False}}),
            patch.object(pensar.obsidian, "ler_perfil", return_value=PERFIL_NEUTRO),
            patch.object(pensar.obsidian, "listar_memoria_episodica", return_value=c.get("memorias", [])),
            patch.object(pensar.obsidian, "indice_notas", return_value=""),
            patch.object(pensar, "buscar_memoria_relevante", return_value=[]),
            patch.object(pensar, "buscar_contexto_relevante", return_value=c.get("chroma", "")),
            patch.object(pensar.assuntos, "contexto_relacionado", return_value=""),
            patch.object(pensar, "ler_estado_luna", return_value={}),
            patch.object(pensar, "obter_janela_em_foco", return_value=c.get("janela", "bancada de teste")),
            patch.object(tom, "obter_hint", return_value=""),
            patch.object(momento, "_jogos", {}),
            pensar.controle.executar() as execucao,
            redirect_stdout(saida),
        ):
            momento.observar_jogos("processos", c.get("jogos", []), agora)
            try:
                if c.get("roteador"):
                    pensar.gerar_resposta(c["usuario"], hist, salvar=False, responder_completo=True)
                else:
                    pensar._reescrever_como_luna(c.get("tecnica", ""), c["usuario"], hist,
                        max_tokens=300, responder_completo=c.get("responder_completo", True))
            except Capturado:
                pass
        if not parametros:
            raise RuntimeError(f"{c['id']}: não chegou à chamada do modelo: {saida.getvalue()}")
        # O log lista os blocos para leitura humana; a classificação usa o diagnóstico
        # estruturado para não transformar IDENTIDADE em um novo ramo da bancada.
        ramo = "ROTEADOR" if c.get("roteador") else getattr(execucao, "diagnostico", {}).get(
            "caminho_prompt", "DESCONHECIDO")
        parametros.update(parametros.pop("extra_body", {}))
        parametros.update(stream=True, stream_options={"include_usage": True}, cache_prompt=False)
        capturados.append({"id": c["id"], "ramo": ramo, "cenario": c, "pedido": parametros})
        print(f"Preparado: {c['id']} / {ramo}", flush=True)
    schemas = {t["function"]["name"]: t["function"]["parameters"]
               for t in pensar.ferramentas_disponiveis}
    suite = {"versao": 1, "criado": datetime.now().isoformat(), "casos": capturados,
             "climas": list(pensar._ROSTOS), "schemas": schemas,
             "fontes": {f: hashlib.sha256((RAIZ / f).read_bytes()).hexdigest()
                        for f in ("modulos/pensar.py", "modulos/prompts.py", "modulos/habilidades.py")}}
    suite["sha256"] = digest(suite)
    gravar_json(destino, suite)
    print(f"Snapshot: {destino}\nSHA256: {suite['sha256']}")


def ler_suite(caminho):
    suite = json.loads(caminho.read_text(encoding="utf-8"))
    corpo = {k: v for k, v in suite.items() if k != "sha256"}
    if digest(corpo) != suite.get("sha256"):
        raise ValueError("Snapshot alterado; prepare outro para não misturar comparações.")
    return suite


def obter_json(url):
    with urlopen(url, timeout=10) as r:
        return json.load(r)


def identidade(base, esperado):
    status = obter_json(base + "/api/v1/status")
    motor = status["engine"]
    if motor["state"] != "running" or not status.get("model"):
        raise RuntimeError("Carregue o modelo no TurboLLM antes de rodar a bancada.")
    props = obter_json(f"http://127.0.0.1:{int(motor['port'])}/props")
    caminho = props.get("model_path", "")
    if not caminho or esperado.casefold() not in caminho.casefold():
        raise RuntimeError(f"Modelo inesperado: {caminho!r}; esperado conter {esperado!r}")
    padroes = props.get("default_generation_settings", {})
    return {"arquivo": caminho, "modelo_key": status["model"]["key"],
            "engine": motor["name"], "engine_id": motor["id"], "pid": motor.get("pid"),
            "turbo": status.get("version"), "contexto": status["model"].get("ctx"),
            "slots": props.get("total_slots"),
            "amostragem_padrao": {k: v for k, v in padroes.get("params", {}).items()
                                  if k in ("top_k", "top_p", "min_p", "repeat_penalty", "samplers")}}


def conferir_identidade(atual, inicial):
    if atual != inicial:
        raise RuntimeError("Modelo, engine ou configuração mudou durante a bancada; interrompido.")


def consumir_stream(linhas, inicio, relogio=time.perf_counter):
    texto, pensamento, chamadas = [], [], {}
    uso, timings, fim, primeiro = {}, {}, None, None
    terminou = False
    for linha in linhas:
        linha = linha.decode("utf-8").strip()
        if not linha.startswith("data:"):
            continue
        dado = linha[5:].strip()
        if dado == "[DONE]":
            terminou = True
            break
        evento = json.loads(dado)
        if evento.get("error"):
            raise RuntimeError(str(evento["error"]))
        uso = evento.get("usage") or uso
        timings = evento.get("timings") or timings
        for escolha in evento.get("choices", []):
            delta = escolha.get("delta", {})
            if primeiro is None and (delta.get("content") or delta.get("tool_calls")):
                primeiro = relogio() - inicio
            texto.append(delta.get("content") or "")
            pensamento.append(delta.get("reasoning_content") or "")
            for item in delta.get("tool_calls", []):
                func = chamadas.setdefault(item["index"], {"name": "", "arguments": ""})
                for k in ("name", "arguments"):
                    func[k] += item.get("function", {}).get(k) or ""
            fim = escolha.get("finish_reason") or fim
    if not terminou or not fim:
        raise RuntimeError("Stream terminou incompleto; resultado não deve entrar no placar.")
    return {"texto": "".join(texto), "pensamento_chars": len("".join(pensamento)),
            "ferramentas": [chamadas[i] for i in sorted(chamadas)], "uso": uso,
            "timings": timings, "finish_reason": fim, "ttft_s": primeiro,
            "total_s": relogio() - inicio}


def chamar(base, modelo, pedido):
    corpo = {**deepcopy(pedido), "model": modelo["modelo_key"]}
    requisicao = Request(base + "/v1/chat/completions",
                         data=json.dumps(corpo).encode(), headers={"Content-Type": "application/json"})
    inicio = time.perf_counter()
    with urlopen(requisicao, timeout=180) as resposta:
        return consumir_stream(resposta, inicio)


def avaliar(caso, resultado, suite):
    from jsonschema import Draft7Validator
    falhas = []
    texto = resultado["texto"]
    if resultado["finish_reason"] == "length":
        falhas.append("cortado pelo teto de tokens")
    if resultado["pensamento_chars"]:
        falhas.append("thinking retornado apesar de desligado")
    if caso["ramo"] == "ROTEADOR":
        chamadas = resultado["ferramentas"]
        nomes = [f["name"] for f in chamadas]
        if nomes != caso["cenario"]["ferramentas"]:
            falhas.append(f"ferramentas: {nomes}; esperado: {caso['cenario']['ferramentas']}")
        if not chamadas and texto.strip() != "SEM_FERRAMENTA":
            falhas.append("faltou saída exata SEM_FERRAMENTA")
        for chamada in chamadas:
            try:
                args = json.loads(chamada["arguments"])
                schema = suite["schemas"].get(chamada["name"])
                if schema is None:
                    falhas.append("ferramenta desconhecida")
                    continue
                falhas.extend("schema: " + e.message for e in Draft7Validator(schema).iter_errors(args))
                if not isinstance(args, dict):
                    continue
                for k, v in caso["cenario"].get("argumentos", {}).items():
                    if args.get(k) != v:
                        falhas.append(f"argumento {k}: esperado {v!r}")
                if chamada["name"] == "duvida_do_jogo":
                    trecho = args.get("trecho_pedido", "")
                    if not trecho or trecho not in caso["cenario"]["usuario"]:
                        falhas.append("trecho_pedido não é literal da mensagem atual")
            except (ValueError, TypeError):
                falhas.append("argumentos não são JSON válido")
    else:
        # Reaproveita os checks existentes, mas a leitura de humor continua humana.
        from testes.bancada_persona import avaliar as avaliar_persona
        climas = re.findall(r"\[clima:([^\]]+)\]", texto)
        if len(climas) != 1 or climas[0] not in suite["climas"]:
            falhas.append("tag de clima ausente, duplicada ou inválida")
        limpo = re.sub(r"\[clima:[^\]]+\]", "", texto).strip()
        falhas.extend(avaliar_persona(caso["cenario"], limpo))
        if resultado["ferramentas"]:
            falhas.append("persona tentou acionar ferramenta")
    return falhas


def amostragem_efetiva(registro):
    return {**registro["modelo"].get("amostragem_padrao", {}),
            **registro.get("parametros_execucao", {})}


def relatorio(resultados, destino):
    linhas = ["# Bancada de modelos da Luna", "",
              "Checks são triagem automática; não medem graça, coerência ou qualidade integral.",
              "TTFT mede a primeira saída de texto/tool call; não inclui carregamento nem aquecimento.",
              "Cache de prompt desativado por chamada. Uma chamada isolada não mede o turno completo da Luna.", ""]
    hashes = {r["suite_sha256"] for r in resultados}
    rodadas = {r["repeticoes"] for r in resultados}
    seeds = {r["seed_base"] for r in resultados}
    if len(hashes) != 1 or len(rodadas) != 1 or len(seeds) != 1:
        raise ValueError("Comparação exige o mesmo snapshot, repetições e seed base.")
    if len({digest(amostragem_efetiva(r)) for r in resultados}) > 1:
        linhas += ["**Atenção: os parâmetros de amostragem diferem entre as execuções.**", ""]
    for r in resultados:
        linhas += [f"## {r['rotulo']}", "", f"Modelo: `{Path(r['modelo']['arquivo']).name}`",
                   f"Engine: `{r['modelo']['engine']}`; contexto: {r['modelo']['contexto']}.",
                   "Amostragem (padrões + ajustes por chamada): `" +
                   json.dumps(amostragem_efetiva(r), ensure_ascii=False) + "`.",
                   f"Snapshot: `{r['suite_sha256']}`.", "",
                   "| Ramo | Checks sem alerta | TTFT mediano | Total mediano |",
                   "|---|---:|---:|---:|"]
        grupos = defaultdict(list)
        for item in r["resultados"]:
            grupos[item["ramo"]].append(item)
        for ramo, itens in grupos.items():
            ttfts = [i["ttft_s"] for i in itens if i["ttft_s"] is not None]
            ttft = f"{statistics.median(ttfts):.2f}s" if ttfts else "—"
            total = statistics.median(i["total_s"] for i in itens)
            linhas.append(f"| {ramo} | {sum(not i['falhas'] for i in itens)}/{len(itens)} | {ttft} | {total:.2f}s |")
        for i in r["resultados"]:
            linhas += ["", f"### {i['cenario']} · rodada {i['rodada']}", "",
                       i["texto"] or "(sem texto)"]
            if i["ferramentas"]:
                linhas += ["", "```json", json.dumps(i["ferramentas"], ensure_ascii=False, indent=2), "```"]
            linhas += ["", "Checks: " + ("; ".join(i["falhas"]) or "sem alerta") + "."]
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text("\n".join(linhas) + "\n", encoding="utf-8")


def executar(args):
    suite = ler_suite(args.suite)
    modelo = identidade(args.base, args.esperado)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    destino = PASTA / f"{stamp}-{args.rotulo}.json"
    # Engines diferentes têm defaults diferentes. O ajuste pertence só à requisição,
    # preservando o snapshot e a configuração usada pelo aplicativo fora da bancada.
    opcoes = {"top_k": args.top_k} if args.top_k is not None else {}
    registro = {"rotulo": args.rotulo, "suite_sha256": suite["sha256"], "modelo": modelo,
                "repeticoes": args.repeticoes, "seed_base": args.seed,
                "parametros_execucao": opcoes, "resultados": []}
    print(f"Modelo confirmado: {modelo['arquivo']}\nAquecendo (fora do placar)...", flush=True)
    registro["aquecimento"] = chamar(args.base, modelo,
        {**suite["casos"][0]["pedido"], **opcoes, "max_tokens": 16, "seed": args.seed})
    conferir_identidade(identidade(args.base, args.esperado), modelo)
    gravar_json(destino, registro)
    for rodada in range(1, args.repeticoes + 1):
        for caso in suite["casos"]:
            conferir_identidade(identidade(args.base, args.esperado), modelo)
            print(f"[{rodada}/{args.repeticoes}] {caso['id']}...", flush=True)
            pedido = {**caso["pedido"], **opcoes, "seed": args.seed + rodada}
            resposta = chamar(args.base, modelo, pedido)
            conferir_identidade(identidade(args.base, args.esperado), modelo)
            resposta.update(cenario=caso["id"], ramo=caso["ramo"], rodada=rodada,
                            pedido_sha256=digest(pedido))
            resposta["falhas"] = avaliar(caso, resposta, suite)
            registro["resultados"].append(resposta)
            gravar_json(destino, registro)
            print(f"  {resposta['total_s']:.1f}s | {resposta['falhas'] or 'sem alerta'}\n"
                  f"  {resposta['texto'] or resposta['ferramentas']}", flush=True)
    registro["completo"] = True
    gravar_json(destino, registro)
    relatorio([registro], destino.with_suffix(".md"))
    print(f"\nResultados: {destino}\nRelatório: {destino.with_suffix('.md')}")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    acao = ap.add_mutually_exclusive_group(required=True)
    acao.add_argument("--preparar", action="store_true")
    acao.add_argument("--rotulo")
    acao.add_argument("--comparar", nargs="+", type=Path)
    ap.add_argument("--suite", type=Path, default=SUITE)
    ap.add_argument("--esperado", help="Trecho obrigatório do caminho GGUF real (ex.: PQ2_0)")
    ap.add_argument("--base", default="http://127.0.0.1:6996")
    ap.add_argument("--repeticoes", type=int, choices=range(1, 6), default=2)
    ap.add_argument("--seed", type=int, default=1931)
    ap.add_argument("--top-k", type=int, help="Iguala top_k apenas nas chamadas da bancada")
    ap.add_argument("--relatorio", type=Path, default=PASTA / "comparacao.md")
    args = ap.parse_args()
    if args.preparar:
        preparar(args.suite)
    elif args.comparar:
        resultados = [json.loads(p.read_text(encoding="utf-8")) for p in args.comparar]
        if not all(r.get("completo") for r in resultados):
            ap.error("Há execução incompleta; não deve entrar na comparação.")
        relatorio(resultados, args.relatorio)
        print(args.relatorio)
    else:
        if not args.esperado or not re.fullmatch(r"[a-zA-Z0-9_-]+", args.rotulo):
            ap.error("Informe --esperado e um --rotulo com letras, números, hífen ou sublinhado.")
        executar(args)


if __name__ == "__main__":
    main()
