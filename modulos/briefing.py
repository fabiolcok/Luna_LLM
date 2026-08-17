"""Briefing reativo: junta fontes existentes sem consumir estados dos proativos."""

import concurrent.futures
import datetime

from modulos import acompanhamentos, animes, obsidian
from modulos.habilidades import ler_agenda_google, obter_previsao_tempo


_LIMITE_FONTE = 1400


def _limitar(texto) -> str:
    texto = str(texto or "").strip()
    if len(texto) <= _LIMITE_FONTE:
        return texto
    return texto[:_LIMITE_FONTE].rsplit("\n", 1)[0].rstrip() + "\n[restante omitido]"


def _ler_nota(nome: str) -> str:
    return obsidian.buscar_nota(nome)


def _ler_acompanhamentos() -> str:
    ativos = acompanhamentos.estado_interface().get("ativos", [])
    if not ativos:
        return "Nenhum acompanhamento confirmado está pendente."
    linhas = []
    for item in ativos[:5]:
        quando = str(item.get("perguntar_em", ""))
        try:
            data = datetime.datetime.fromisoformat(quando)
            quando = data.strftime("%d/%m às %H:%M")
        except (TypeError, ValueError):
            quando = "horário não informado"
        linhas.append(f"- {item.get('assunto', 'assunto sem nome')} — perguntar em {quando}")
    return "Acompanhamentos confirmados:\n" + "\n".join(linhas)


def consultar() -> str:
    """Consulta as fontes em paralelo; falha isolada nunca derruba o restante do briefing."""
    coletores = {
        "CLIMA AGORA": obter_previsao_tempo,
        "AGENDA (PRÓXIMOS COMPROMISSOS)": ler_agenda_google,
        "ANIMES RECENTES": animes.consultar,
        "ACOMPANHAMENTOS": _ler_acompanhamentos,
        "NOVIDADES RECENTES": lambda: _ler_nota("Novidades"),
        "PROMOÇÕES RECENTES": lambda: _ler_nota("Promocoes"),
    }
    resultados = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(coletores)) as executor:
        futuros = {executor.submit(fn): nome for nome, fn in coletores.items()}
        for futuro, nome in [(f, futuros[f]) for f in futuros]:
            try:
                resultados[nome] = _limitar(futuro.result())
            except Exception as erro:
                resultados[nome] = f"SISTEMA: fonte indisponível ({type(erro).__name__})."

    agora = datetime.datetime.now().strftime("%d/%m/%Y às %H:%M")
    partes = [f"BRIEFING CONSULTADO EM {agora}"]
    for nome in coletores:  # ordem estável apesar das consultas paralelas
        partes.append(f"\n## {nome}\n{resultados.get(nome) or 'Sem informação.'}")
    return "\n".join(partes)
