# modulos/obsidian.py
# Integração de leitura com o vault do Obsidian (o "cérebro co-editado" da Luna).
#   - perfil.md: núcleo sempre carregado no contexto da persona.
#   - resto do vault: lido sob demanda via ferramenta ler_obsidian.
# Pastas de "dev" (Luna/Criar, Luna/Talvez) e internas (.obsidian/.trash) são ignoradas.

import os
import re
import unicodedata

_VAULT = (os.getenv("OBSIDIAN_VAULT", "") or r"G:\Projetos\obisidian\Fabio").strip()

# Trechos de caminho que a Luna NÃO lê (notas meta/dev e internas do Obsidian)
_IGNORAR = (
    f"{os.sep}.obsidian{os.sep}",
    f"{os.sep}.trash{os.sep}",
    f"{os.sep}Luna{os.sep}Criar{os.sep}",
    f"{os.sep}Luna{os.sep}Talvez{os.sep}",
)


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9 ]", " ", s)


def _caminho_perfil() -> str:
    return os.path.join(_VAULT, "Luna", "perfil.md")


def ler_perfil() -> str:
    """Conteúdo do perfil.md (núcleo sempre-carregado). Vazio se não existir."""
    try:
        with open(_caminho_perfil(), encoding="utf-8") as f:
            return f.read().strip()
    except Exception:
        return ""


def secao_perfil(titulo: str) -> str:
    """Texto sob um header '## titulo' do perfil.md, até o próximo header.
    Usado para extrair Aparência / Estilo de desenho para o gerador de imagem."""
    txt = ler_perfil()
    if not txt:
        return ""
    m = re.search(
        r'^#{1,6}\s*' + re.escape(titulo) + r'[^\n]*\n(.*?)(?=^#{1,6}\s|\Z)',
        txt, re.IGNORECASE | re.MULTILINE | re.DOTALL,
    )
    if not m:
        return ""
    linhas = [l.strip(" -\t") for l in m.group(1).splitlines()
              if l.strip() and not l.strip().startswith(">")]
    return " ".join(linhas).strip()


def _listar_notas() -> list:
    """Caminhos das notas .md elegíveis (exclui ignoradas e o próprio perfil)."""
    if not os.path.isdir(_VAULT):
        return []
    perfil = os.path.normpath(_caminho_perfil())
    notas = []
    for raiz, _dirs, arquivos in os.walk(_VAULT):
        for a in arquivos:
            if not a.lower().endswith(".md"):
                continue
            caminho = os.path.join(raiz, a)
            if os.path.normpath(caminho) == perfil:
                continue
            if any(ig.lower() in caminho.lower() for ig in _IGNORAR):
                continue
            notas.append(caminho)
    return notas


def indice_notas() -> str:
    """Títulos das notas (sem extensão), para o roteador saber o que existe no vault."""
    titulos = sorted(os.path.splitext(os.path.basename(c))[0] for c in _listar_notas())
    return ", ".join(titulos)


def _limpar_md(texto: str) -> str:
    """Remove ruído do Obsidian que não serve pra leitura (embeds de imagem/vídeo, wikilinks)."""
    texto = re.sub(r'!\[\[[^\]]*\]\]', '', texto)              # ![[imagem.png]] (embed do Obsidian)
    texto = re.sub(r'!\[[^\]]*\]\([^)]*\)', '', texto)         # ![alt](img.png) (markdown)
    texto = re.sub(r'\[\[(?:[^\]|]*\|)?([^\]]*)\]\]', r'\1', texto)  # [[nota|texto]] -> texto
    texto = re.sub(r'\n{3,}', '\n\n', texto)                   # colapsa linhas em branco sobrando
    return texto.strip()


def buscar_nota(assunto: str) -> str:
    """Acha a nota cujo nome melhor casa com 'assunto' e devolve o conteúdo (fetch-only)."""
    notas = _listar_notas()
    if not notas:
        return "SISTEMA: Não há notas acessíveis no Obsidian (vault vazio ou caminho errado)."

    alvo = set(_norm(assunto).split())
    melhor, melhor_score = None, 0
    for c in notas:
        palavras = set(_norm(os.path.splitext(os.path.basename(c))[0]).split())
        score = len(alvo & palavras)
        if score > melhor_score:
            melhor, melhor_score = c, score

    if not melhor or melhor_score == 0:
        return f"SISTEMA: Não achei nenhuma nota sobre '{assunto}' nas suas anotações."
    try:
        with open(melhor, encoding="utf-8") as f:
            return _limpar_md(f.read())
    except Exception as e:
        return f"SISTEMA: Erro ao ler a nota: {e}"
