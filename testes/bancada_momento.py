"""Compara uso de sinais atuais, sem monitor real, servidor ou fontes pessoais."""
import argparse
from datetime import datetime
import json
from pathlib import Path
import sys
import time
from unittest.mock import patch

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))
from testes.bancada_persona import executar_cenario
from modulos import momento


def testar_roteador(pensar, rotulo, destino):
    class Capturado(BaseException):
        pass
    casos = [
        ("pedido_antigo", "Hoje foi puxado.", "Toca uma música.", []),
        ("comentario_partida", "Voltei da partida, que surra.", "Vou jogar Overwatch.", []),
        ("duvida_partida", "Como faço para curar meus aliados no Overwatch?", "Vou jogar Overwatch.", ["duvida_do_jogo"]),
    ]
    for nome, usuario, anterior, esperado in casos:
        capturado = {}
        def interceptar(**parametros):
            capturado.update(parametros)
            raise Capturado()
        real = pensar._chamar_llm
        with (patch.object(momento, "_jogos", {}),
              patch.object(pensar.obsidian, "indice_notas", return_value=""),
              patch.object(pensar, "obter_janela_em_foco", return_value="Overwatch"),
              pensar.controle.executar()):
            momento.observar_jogos("processos", ["Overwatch"])
            with patch.object(pensar, "_chamar_llm", interceptar):
                try:
                    pensar.gerar_resposta(usuario, [{"role": "user", "content": anterior,
                                                    "instante": time.time() - 20}], salvar=False,
                                         responder_completo=True)
                except Capturado:
                    pass
            # Só consulta o modelo com o prompt capturado; nenhuma ferramenta é executada.
            resposta = real(**capturado).choices[0].message
        ferramentas = [t.function.name for t in (resposta.tool_calls or [])]
        ok = ferramentas == esperado
        registro = {"tempo": datetime.now().isoformat(timespec="seconds"), "rotulo": rotulo,
                    "cenario": nome, "ramo": "roteador", "ferramentas": ferramentas,
                    "texto": resposta.content, "ok": ok}
        with destino.open("a", encoding="utf-8") as arq:
            arq.write(json.dumps(registro, ensure_ascii=False) + "\n")
        print(f"[ROTEADOR / {nome}] ferramentas={ferramentas}, checks={'OK' if ok else 'FALHOU'}", flush=True)

CENARIOS = [
    {"id": "janela_trocada", "usuario": "Qual janela está em foco agora?",
     "estado": {"programa_atual": "SISTEMA: O usuário está com a janela 'Email - Firefox' em foco no momento."},
     "janela": "SISTEMA: O usuário está com a janela 'Cities: Skylines II' em foco no momento.",
     "jogos": [], "exige": ["cities"], "proibe": ["email", "firefox"]},
    {"id": "jogo_fechado", "usuario": "Ainda tem algum jogo detectado no meu PC?",
     "estado": {"jogo_ativo": "Overwatch"}, "janela": "Área de trabalho",
     "jogos": [], "exige": ["não", "nenhum", "sem jogo", "nada detectado"],
     "proibe": ["está aberto", "tá aberto", "está rodando", "tá rodando", "jogando overwatch"]},
    {"id": "partida_desconhecida", "usuario": "Quanto está o placar da minha partida?",
     "estado": {"jogo_ativo": "Overwatch"}, "janela": "Overwatch", "jogos": ["Overwatch"],
     "exige": ["não", "sem acesso", "me diz", "me diga"], "proibe": ["2 a 1", "3 a 0"]},
    {"id": "fora_do_pc", "usuario": "Estou no mercado, o que dá pra fazer enquanto espero?",
     "estado": {"jogo_ativo": "Overwatch", "programa_atual": "Editor de código"},
     "janela": "Editor de código", "jogos": ["Overwatch"], "no_pc": False,
     "exige": [], "proibe": ["overwatch", "programar", "editor", "no pc"]},
]


def avaliar(cenario, resposta):
    texto = resposta.casefold()
    falhas = [f"menção indevida: {p}" for p in cenario["proibe"] if p in texto]
    if cenario["exige"] and not any(p in texto for p in cenario["exige"]):
        falhas.append("faltou informação esperada")
    return falhas


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--rotulo", required=True)
    ap.add_argument("--repeticoes", type=int, default=2)
    ap.add_argument("--roteador", action="store_true", help="inclui três chamadas sem executar ferramentas")
    ap.add_argument("--reavaliar", action="store_true", help="reaplica os checks ao log, sem chamar modelo")
    args = ap.parse_args()
    if not 1 <= args.repeticoes <= 5:
        ap.error("repetições: 1 a 5")
    destino = RAIZ / "logs" / "bancada_momento.jsonl"
    if args.reavaliar:
        casos = {c["id"]: c for c in CENARIOS}
        registros = [json.loads(linha) for linha in destino.read_text(encoding="utf-8").splitlines()]
        for persona in (True, False):
            registros_ramo = [r for r in registros if r["rotulo"] == args.rotulo
                              and r.get("usou_persona") is persona and r["cenario"] in casos]
            if registros_ramo:
                acertos = sum(not avaliar(casos[r["cenario"]], r["resposta"]) for r in registros_ramo)
                print(f"{args.rotulo} / {'PROMPT_COMPLETO' if persona else 'ENXUTO'}: {acertos}/{len(registros_ramo)}")
        return
    from modulos import pensar
    resultados = []
    destino.parent.mkdir(exist_ok=True)
    for c in CENARIOS:
        for rodada in range(args.repeticoes):
            agora = time.time()
            with patch.object(momento, "_jogos", {}):
                momento.observar_jogos("processos", c["jogos"], agora)
                # O executor comum fixa essas fontes; o wrapper as substitui só nesta chamada.
                reescrever = pensar._reescrever_como_luna
                def executar(*a, **kw):
                    pensar._presenca_pc.set(c.get("no_pc", True))
                    with (patch.object(pensar, "ler_estado_luna", return_value=c["estado"]),
                          patch.object(pensar, "obter_janela_em_foco", return_value=c["janela"])):
                        return reescrever(*a, **kw)
                with (patch.object(pensar, "_reescrever_como_luna", executar),
                      patch.object(pensar.assuntos, "contexto_relacionado", return_value="")):
                    resposta, persona = executar_cenario(pensar, c)
            falhas = avaliar(c, resposta)
            resultado = {"tempo": datetime.now().isoformat(timespec="seconds"), "rotulo": args.rotulo,
                         "cenario": c["id"], "rodada": rodada + 1, "usou_persona": persona,
                         "resposta": resposta, "falhas": falhas, "ok": not falhas}
            resultados.append(resultado)
            with destino.open("a", encoding="utf-8") as arq:
                arq.write(json.dumps(resultado, ensure_ascii=False) + "\n")
            print(f"[{c['id']}] {resposta}\n  checks: {falhas or 'OK'}", flush=True)
    for persona in (True, False):
        grupo = [r for r in resultados if r["usou_persona"] == persona]
        if grupo:
            print(f"{'PROMPT_COMPLETO' if persona else 'ENXUTO'}: {sum(r['ok'] for r in grupo)}/{len(grupo)}")
    print("Checks não medem humor ou correção integral; ler as respostas.")
    if args.roteador:
        testar_roteador(pensar, args.rotulo, destino)


if __name__ == "__main__":
    main()
