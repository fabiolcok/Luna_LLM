"""Bancada do convite Sopro: dados fictícios, só texto, sem importar main/pensar."""
import argparse
import datetime as dt
import hashlib
import json
from pathlib import Path
import time

import requests
from modulos import prompts

CENARIOS = (
    {"id": "plano_futuro", "tipo": "plano", "trecho": "Roadmap: Brazilian Portuguese support is planned for a future release."},
    {"id": "anuncio_para_validar", "tipo": "anuncio", "trecho": "Added an experimental Brazilian Portuguese voice option. Accent quality still needs evaluation."},
)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--modelo", required=True, help="ID do modelo já escolhido no TurboLLM")
    args = parser.parse_args()
    prompts.NOME_USUARIO = "usuário"
    sistema = prompts.nucleo_enxuto(prompts.ENXUTO_PROATIVO, sem_emoji=True, emocao=prompts.EMOCAO)
    destino = Path("logs/bancada_acompanhamento_sopro") / dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    destino.mkdir(parents=True, exist_ok=False)
    resultados = []
    for cenario in CENARIOS:
        briefing = prompts.ACOMPANHAMENTO_SOPRO.format(
            situacao="Gostou da voz e da respiração; o sotaque PT-PT incomodou.",
            fonte="GitHub · release fictício da bancada", trecho=cenario["trecho"],
            orientacao=prompts.SOPRO_ORIENTACOES[cenario["tipo"]])
        inicio = time.perf_counter()
        resposta = requests.post("http://127.0.0.1:6996/v1/chat/completions", timeout=(5, 120), json={
            "model": args.modelo, "messages": [{"role": "system", "content": sistema},
                                              {"role": "user", "content": briefing}],
            "max_tokens": 220, "temperature": 0.85,
            "chat_template_kwargs": {"enable_thinking": False}})
        resposta.raise_for_status()
        dados = resposta.json()
        texto = dados["choices"][0]["message"].get("content") or ""
        resultados.append({**cenario, "resposta": texto, "segundos": round(time.perf_counter()-inicio, 2),
                           "uso": dados.get("usage", {}), "briefing_caracteres": len(briefing)})
        (destino/"resultado.json").write_text(json.dumps({
            "modelo": args.modelo, "dados_ficticios": True, "segmento": "proativo Sopro",
            "prompt_sha256": hashlib.sha256(sistema.encode()).hexdigest(), "resultados": resultados},
            ensure_ascii=False, indent=2), encoding="utf-8")
        print(cenario["id"], resultados[-1]["segundos"], texto, flush=True)
    linhas = ["# Convites do piloto Sopro", "", "Dados fictícios. Não são anúncios reais de PT-BR.",
              "Somente o novo segmento proativo foi avaliado; escopo isolado, sem memória, áudio ou chat anterior.", ""]
    for item in resultados:
        linhas += ["## " + item["id"], "", "Fonte fictícia: " + item["trecho"], "",
                   item["resposta"], "", f'{item["segundos"]} s; briefing {item["briefing_caracteres"]} caracteres.', ""]
    (destino/"resultado.md").write_text("\n".join(linhas), encoding="utf-8")
    print(destino, flush=True)


if __name__ == "__main__":
    main()
