"""Consulta reativa das coisas ainda abertas, sem tratar agenda e tarefas como sinônimos."""

import concurrent.futures
import datetime

from modulos import acompanhamentos, obsidian
from modulos.habilidades import ler_agenda_google


def _acompanhamentos_abertos() -> str:
    ativos = acompanhamentos.estado_interface().get("ativos", [])
    if not ativos:
        return "Nenhum acompanhamento esperando desfecho."
    linhas = []
    for item in ativos[:10]:
        quando = str(item.get("perguntar_em", ""))
        try:
            quando = datetime.datetime.fromisoformat(quando).strftime("%d/%m às %H:%M")
        except (TypeError, ValueError):
            quando = "data não informada"
        linhas.append(f"- {item.get('assunto', 'assunto sem nome')} — retorno em {quando}")
    return "Acompanhamentos esperando desfecho:\n" + "\n".join(linhas)


def consultar(assunto: str = "") -> str:
    """Assunto específico procura checkboxes; consulta ampla também inclui agenda e retornos."""
    assunto = (assunto or "").strip()
    if assunto:
        return obsidian.listar_tarefas_pendentes(assunto)

    fontes = {
        "TAREFAS ABERTAS NO OBSIDIAN": lambda: obsidian.listar_tarefas_pendentes(),
        "COMPROMISSOS FUTUROS NA AGENDA": ler_agenda_google,
        "ACOMPANHAMENTOS ESPERANDO DESFECHO": _acompanhamentos_abertos,
    }
    resultados = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(fontes)) as executor:
        futuros = {executor.submit(fn): nome for nome, fn in fontes.items()}
        for futuro, nome in [(f, futuros[f]) for f in futuros]:
            try:
                resultados[nome] = str(futuro.result() or "Sem informação.").strip()
            except Exception as erro:
                resultados[nome] = f"SISTEMA: fonte indisponível ({type(erro).__name__})."

    partes = ["CONSULTA DE PENDÊNCIAS"]
    for nome in fontes:
        partes.append(f"\n## {nome}\n{resultados[nome]}")
    return "\n".join(partes)
