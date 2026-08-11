r"""Bancada do roteamento de acompanhamentos usando o modelo real, sem subir a Luna.

As únicas ferramentas visíveis são agenda, nota e proposta de acompanhamento, todas
substituídas por funções locais. Nenhuma agenda, nota, voz, web ou Telegram é acionado.
"""

import argparse
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
    ("desfecho_concreto", "Amanhã vou levar o PC para a assistência.", "propor_acompanhamento"),
    ("pedido_explicito", "Me pergunta depois como ficou o conserto do notebook.", "propor_acompanhamento"),
    ("agenda", "Coloca dentista amanhã às 15h na minha agenda.", "adicionar_agenda"),
    ("lembrete", "Me lembra amanhã de pagar o boleto.", "nao_acompanhamento"),
    ("cotidiano", "Vou comprar um jogo na Steam aqui.", "nao_acompanhamento"),
]


def main() -> int:
    ap = argparse.ArgumentParser(description="Bancada real do roteador de acompanhamentos")
    ap.add_argument("--cenario", help="id de um cenário; omita para rodar todos")
    args = ap.parse_args()
    cenarios = [c for c in CENARIOS if not args.cenario or c[0] == args.cenario]
    if not cenarios:
        ap.error(f"cenário desconhecido: {args.cenario}")

    from modulos import acompanhamentos, habilidades, pensar

    nomes = {"adicionar_agenda", "salvar_obsidian", "propor_acompanhamento"}
    schemas = [f for f in habilidades.ferramentas_disponiveis
               if f.get("function", {}).get("name") in nomes]
    passou = 0
    with tempfile.TemporaryDirectory() as tmp:
        caminho = Path(tmp) / "acompanhamentos.json"
        for identificador, texto, esperado in cenarios:
            chamadas = []

            def ferramenta_segura(nome):
                def executar(**_kwargs):
                    chamadas.append(nome)
                    return f"TESTE_LOCAL: {nome} selecionada; nada foi alterado."
                return executar

            def propor_seguro(assunto="", perguntar_em=""):
                chamadas.append("propor_acompanhamento")
                return acompanhamentos.propor(assunto, perguntar_em, "bancada")

            substitutos = {
                "adicionar_agenda": ferramenta_segura("adicionar_agenda"),
                "salvar_obsidian": ferramenta_segura("salvar_obsidian"),
                "propor_acompanhamento": propor_seguro,
            }
            if caminho.exists():
                caminho.unlink()
            with (
                patch.object(acompanhamentos, "CAMINHO_ESTADO", caminho),
                patch.object(acompanhamentos, "_VAULT", ""),
                patch.object(acompanhamentos, "_notificar", return_value=None),
                patch.object(pensar, "ferramentas_disponiveis", schemas),
                patch.dict(pensar.FUNCOES_DISPONIVEIS, substitutos, clear=False),
                patch.object(pensar.obsidian, "indice_notas", return_value=""),
                patch.object(pensar.obsidian, "ler_perfil", return_value=""),
                patch.object(pensar.obsidian, "listar_memoria_episodica", return_value=[]),
                patch.object(pensar, "buscar_contexto_relevante", return_value=""),
                patch.object(pensar, "buscar_memoria_relevante", return_value=[]),
                patch.object(pensar, "ler_estado_luna", return_value={}),
            ):
                resposta = pensar.gerar_resposta(texto, [], salvar=False, responder_completo=True)

            ferramenta = chamadas[0] if chamadas else "nenhuma"
            ok = (ferramenta == esperado if esperado != "nao_acompanhamento"
                  else ferramenta != "propor_acompanhamento")
            passou += int(ok)
            print(f"[{'PASSOU' if ok else 'FALHOU'}] {identificador}: {ferramenta}")
            print(f"  Luna: {resposta}")

    print(f"\nRESUMO: {passou}/{len(cenarios)} passaram")
    return 0 if passou == len(cenarios) else 1


if __name__ == "__main__":
    raise SystemExit(main())
