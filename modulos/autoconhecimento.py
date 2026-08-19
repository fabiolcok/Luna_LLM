"""Introspecção reativa e limitada ao código público da própria Luna."""

import ast
import importlib.util
import inspect
import re
import sys
import unicodedata


_TOPICOS = (
    ({"memoria", "lembrar", "lembra", "chromadb", "fato"},
     (("modulos.memoria", "buscar_contexto_relevante"),
      ("modulos.memoria", "analisar_e_salvar_fato"),
      ("modulos.memoria", "mem_filtrar_candidatos"))),
    ({"roteador", "roteamento", "ferramenta", "ferramentas", "decide", "decidir", "raciocinio"},
     (("modulos.pensar", "gerar_resposta"),)),
    ({"persona", "personalidade", "prompt", "responde", "resposta"},
     (("modulos.pensar", "_reescrever_como_luna"),
      ("modulos.pensar", "_extrair_clima"))),
    ({"voz", "fala", "falar", "kokoro", "pronuncia", "sintese", "tts", "transformacao"},
     (("modulos.falar", "falar_texto"),
      ("modulos.falar", "_corrigir_pronuncia"),
      ("modulos.falar", "limpar_texto_para_voz"))),
    ({"ouve", "ouvir", "audio", "microfone", "stt", "whisper"},
     (("modulos.ouvir", "transcrever_bytes"),
      ("modulos.ouvir", "escutar_usuario"))),
    ({"proativo", "proativa", "sozinha", "automatico", "radar"},
     (("modulos.proativa", "_gerar_fala_proativa"),
      ("modulos.proativa", "_loop_proativo"))),
    ({"steam", "jogo", "jogos", "platina", "platinei", "zerado", "zerei",
      "conquista", "conquistas", "rotina"},
     (("modulos.rotina_jogos", "registrar_declaracao"),
      ("modulos.rotina_jogos", "contexto_pessoal"),
      ("modulos.proativa", "_tarefa_monitorar_steam"))),
    ({"obsidian", "nota", "notas", "vault", "anotacao"},
     (("modulos.obsidian", "buscar_nota"),
      ("modulos.obsidian", "salvar_nota"))),
    ({"rosto", "cara", "clima", "kaomoji", "expressao"},
     (("modulos.pensar", "_extrair_clima"),
      ("modulos.pensar", "obter_e_limpar_kaomoji"))),
    ({"modelo", "turbollm", "esfria", "esfriou", "carregar"},
     (("modulos.pensar", "modelo"),
      ("modulos.pensar", "_chamar_llm"),
      ("modulos.pensar", "_recarregar_modelo_esfriado"))),
)


def _normalizar(texto: str) -> set[str]:
    base = unicodedata.normalize("NFKD", str(texto or ""))
    base = "".join(c for c in base if not unicodedata.combining(c)).lower()
    return set(re.findall(r'[a-z0-9]+', base))


def resolver_topico(assunto: str):
    palavras = _normalizar(assunto)
    candidatos = [(len(palavras & chaves), alvos) for chaves, alvos in _TOPICOS]
    pontos, alvos = max(candidatos, key=lambda item: item[0], default=(0, ()))
    return alvos if pontos else ()


def _fonte(alvo, limite: int) -> str:
    modulo_nome, atributo = alvo
    modulo = sys.modules.get(modulo_nome)
    if modulo is not None and hasattr(modulo, atributo):
        codigo, linha = inspect.getsourcelines(getattr(modulo, atributo))
        texto = "".join(codigo).strip()
    else:
        # Importar pensar.py apenas para inspecioná-lo aquece modelo, voz e integrações.
        # O alvo continua vindo da lista fechada acima; o fallback AST lê a mesma fonte
        # sem executar o módulo. Dentro da Luna, os módulos já carregados usam inspect.
        spec = importlib.util.find_spec(modulo_nome)
        if not spec or not spec.origin or not spec.origin.endswith(".py"):
            raise ImportError(modulo_nome)
        with open(spec.origin, encoding="utf-8") as arquivo:
            fonte = arquivo.read()
        arvore = ast.parse(fonte)
        no = next((item for item in arvore.body
                   if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))
                   and item.name == atributo), None)
        if no is None:
            raise AttributeError(atributo)
        texto = ast.get_source_segment(fonte, no).strip()
        linha = no.lineno
    if atributo == "gerar_resposta" and "tools=ferramentas_ativas" in texto:
        linhas = texto.splitlines()
        indice = next(i for i, item in enumerate(linhas) if "tools=ferramentas_ativas" in item)
        inicio = max(0, indice - 22)
        texto = "\n".join(linhas[inicio:indice + 38])
        linha += inicio
    if len(texto) > limite:
        texto = texto[:limite].rsplit("\n", 1)[0] + "\n# ... trecho limitado pela introspecção"
    return f"### {modulo_nome}.{atributo} (linha {linha})\n```python\n{texto}\n```"


def consultar(assunto: str, limite_total: int = 4800) -> str:
    """Retorna somente fontes de uma lista segura; nunca abre caminho fornecido pelo usuário."""
    alvos = resolver_topico(assunto)
    if not alvos:
        return (
            "SISTEMA: não encontrei um ponto seguro do meu código para esse assunto. "
            "Posso consultar memória, roteador, persona, voz, escuta, proativos, jogos/Steam, "
            "Obsidian, rosto/clima ou modelo/TurboLLM."
        )
    blocos = []
    restante = limite_total
    for alvo in alvos:
        if restante < 500:
            break
        try:
            bloco = _fonte(alvo, min(1800, restante))
        except (AttributeError, ImportError, OSError, TypeError):
            continue
        blocos.append(bloco)
        restante -= len(bloco)
    if not blocos:
        return "SISTEMA: o ponto existe, mas não consegui inspecionar seu código agora."
    fatos_execucao = []
    if any(modulo == "modulos.memoria" for modulo, _ in alvos):
        pensar = sys.modules.get("modulos.pensar")
        if pensar is not None:
            ativo = bool(getattr(pensar, "ATIVAR_MEMORIA_PERMANENTE", False))
            fatos_execucao.append(
                "Extração automática de fatos permanentes: " + ("ATIVA" if ativo else "DESATIVADA")
            )
    runtime = (("\n\n### Estado atual em execução\n" + "\n".join(fatos_execucao))
               if fatos_execucao else "")
    return (
        "SISTEMA: trechos reais e atuais do meu próprio código. "
        "Explique apenas o que eles sustentam; diferencie fato de inferência.\n\n"
        + "\n\n".join(blocos) + runtime
    )
