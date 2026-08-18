r"""Bancada do roteamento da rotina de jogos com o modelo real, sem subir a Luna.

Usa um JSON temporário e ferramentas limitadas: não toca na rotina pessoal, Steam,
voz, Obsidian ou Telegram. Bancadas não entram no runner automático porque usam a LLM.
"""

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch


RAIZ = Path(__file__).parents[1]
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))
os.chdir(RAIZ)


CENARIOS = [
    {"id": "zerou", "texto": "Zerei Hollow Knight.", "nome": "Hollow Knight",
     "estado": "zerado", "proibidos": ["pesadelo", "backlog", "pendência"]},
    {"id": "platinou", "texto": "Eu platinei Portal 2.", "nome": "Portal 2",
     "platinado": True, "proibidos": ["backlog", "pendência", "sobrou tempo"]},
    {"id": "abandonou", "texto": "Desisti de Hades porque o loop cansou.",
     "nome": "Hades", "estado": "abandonado"},
    {"id": "opiniao", "texto": "Gostei muito da narrativa de BioShock Infinite.",
     "nome": "BioShock Infinite", "opiniao": True},
    {
        "id": "jogo_aberto_sem_nome",
        "texto": "Ainda faltam algumas conquistas, queria platinar esse jogo também.",
        "ativo": "Hollow Knight: Silksong",
        "nome": "Hollow Knight: Silksong",
        "platinado": False,
    },
    {"id": "pergunta_opiniao", "texto": "Você acha Hollow Knight difícil?", "nenhum": True},
    {"id": "consulta_conquistas", "texto": "Quantas conquistas tem Portal 2?", "nenhum": True},
    {"id": "compra", "texto": "Quero comprar Hades numa promoção.", "nenhum": True},
]


def _estado_inicial(ativo=""):
    nomes = ["Hollow Knight", "Portal 2", "Hades", "BioShock Infinite",
             "Hollow Knight: Silksong"]
    jogos = {}
    for nome in nomes:
        jogos[nome.lower()] = {
            "appid": "", "nome": nome, "sessoes": 0, "minutos_observados": 0,
            "primeira_abertura": None, "ultima_abertura": None,
            "ultima_sessao_min": None, "em_andamento": nome == ativo,
            "estado": None, "estado_declarado_em": None, "platinado": None,
            "platina_declarada_em": None, "opinioes": [],
        }
    return {"versao": 1, "jogos": jogos, "ultimo_jogo": None}


def main() -> int:
    ap = argparse.ArgumentParser(description="Bancada real da rotina de jogos")
    ap.add_argument("--cenario", help="id de um cenário; omita para rodar todos")
    args = ap.parse_args()
    cenarios = [c for c in CENARIOS if not args.cenario or c["id"] == args.cenario]
    if not cenarios:
        ap.error("cenário desconhecido")

    from modulos import habilidades, pensar, rotina_jogos

    schemas = [f for f in habilidades.ferramentas_disponiveis
               if f.get("function", {}).get("name") == "registrar_rotina_jogo"]
    passou = 0
    with tempfile.TemporaryDirectory() as tmp:
        caminho = Path(tmp) / "rotina.json"
        for cenario in cenarios:
            caminho.write_text(json.dumps(_estado_inicial(cenario.get("ativo", "")),
                                           ensure_ascii=False), encoding="utf-8")
            chamadas = []

            def registrar_seguro(**kwargs):
                chamadas.append(kwargs)
                return rotina_jogos.registrar_declaracao(
                    kwargs.get("nome_jogo", ""), kwargs.get("estado_jogo", ""),
                    kwargs.get("opiniao", ""), platinado=kwargs.get("platinado"))

            with (
                patch.object(rotina_jogos, "CAMINHO_ESTADO", str(caminho)),
                patch.object(pensar, "ferramentas_disponiveis", schemas),
                patch.object(pensar, "_executar_registrar_rotina_jogo", registrar_seguro),
                patch.dict(pensar.FUNCOES_DISPONIVEIS,
                           {"registrar_rotina_jogo": registrar_seguro}, clear=False),
                patch.object(pensar.obsidian, "indice_notas", return_value=""),
                patch.object(pensar.obsidian, "ler_perfil", return_value=""),
                patch.object(pensar.obsidian, "listar_memoria_episodica", return_value=[]),
                patch.object(pensar, "buscar_contexto_relevante", return_value=""),
                patch.object(pensar, "buscar_memoria_relevante", return_value=[]),
                patch.object(pensar, "ler_estado_luna", return_value={}),
            ):
                resposta = pensar.gerar_resposta(
                    cenario["texto"], [], salvar=False, responder_completo=True)

            dados = json.loads(caminho.read_text(encoding="utf-8"))
            alterados = [j for j in dados["jogos"].values()
                         if j.get("estado") or j.get("platinado") is not None or j.get("opinioes")]
            if cenario.get("nenhum"):
                ok = not chamadas and not alterados
            else:
                jogo = alterados[0] if len(alterados) == 1 else {}
                ok = bool(chamadas) and len(alterados) == 1
                if "estado" in cenario:
                    ok = ok and jogo.get("estado") == cenario["estado"]
                if cenario.get("nome"):
                    ok = ok and jogo.get("nome") == cenario["nome"]
                if "platinado" in cenario:
                    ok = ok and jogo.get("platinado") is cenario["platinado"]
                if cenario.get("opiniao"):
                    ok = ok and bool(jogo.get("opinioes"))
                resposta_norm = resposta.lower()
                ok = ok and not any(p.lower() in resposta_norm
                                    for p in cenario.get("proibidos", []))
            passou += int(ok)
            destino = chamadas[0].get("nome_jogo") if chamadas else "nenhum"
            print(f"[{'PASSOU' if ok else 'FALHOU'}] {cenario['id']}: {destino}")
            print(f"  Luna: {resposta}")

    print(f"\nRESUMO: {passou}/{len(cenarios)} passaram")
    return 0 if passou == len(cenarios) else 1


if __name__ == "__main__":
    raise SystemExit(main())
