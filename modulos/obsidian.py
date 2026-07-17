# modulos/obsidian.py
# Integração de leitura com o vault do Obsidian (o "cérebro co-editado" da Luna).
#   - perfil.md: núcleo sempre carregado no contexto da persona.
#   - resto do vault: lido sob demanda via ferramenta ler_obsidian.
# Pastas de "dev" (Luna/Criar, Luna/Talvez) e internas (.obsidian/.trash) são ignoradas.

import os
import re
import datetime
import unicodedata
from dotenv import load_dotenv

load_dotenv()
# Caminho do vault vem do .env (OBSIDIAN_VAULT). Sem ele, a integração fica inativa.
_VAULT = os.getenv("OBSIDIAN_VAULT", "").strip()

# A Luna lê TUDO, menos: pastas internas do Obsidian e a pasta de ignorados (você controla).
# Jogue em "0 Pasta ignorada" qualquer coisa que ela NÃO deva ler.
_PASTA_IGNORADA = "0 Pasta ignorada"
_IGNORAR = (
    f"{os.sep}.obsidian{os.sep}",
    f"{os.sep}.trash{os.sep}",
    f"{os.sep}{_PASTA_IGNORADA}{os.sep}",
)


def _norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9 ]", " ", s)


def _stem(p: str) -> str:
    """Stem mínimo: remove 's' final de plurais (ovos->ovo, contas->conta).
    Não é linguístico, só ajuda a busca por conteúdo a não errar por plural."""
    return p[:-1] if len(p) > 3 and p.endswith("s") else p


def _slug(texto: str, limite: int = 50) -> str:
    """Transforma um título em pedaço seguro de nome de arquivo (sem acento/pontuação)."""
    s = re.sub(r"\s+", "-", _norm(texto).strip())
    return s[:limite].strip("-") or "nota"


# Palavras vazias / de pergunta — ignoradas na busca por CONTEÚDO pra não casar à toa.
_STOPWORDS = {
    "de", "da", "do", "das", "dos", "na", "no", "nas", "nos", "em", "com", "por",
    "para", "pra", "e", "ou", "um", "uma", "uns", "umas", "que", "qual", "quais",
    "quanto", "quantos", "quanta", "quantas", "me", "meu", "minha", "seu", "sua",
    "tem", "ter", "ali", "aqui", "isso", "essa", "esse", "esta", "este",
}


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
    """Remove ruído do Obsidian e torna explícito o que o modelo fraco não interpreta."""
    texto = re.sub(r'!\[\[[^\]]*\]\]', '', texto)              # ![[imagem.png]] (embed do Obsidian)
    texto = re.sub(r'!\[[^\]]*\]\([^)]*\)', '', texto)         # ![alt](img.png) (markdown)
    texto = re.sub(r'\[\[(?:[^\]|]*\|)?([^\]]*)\]\]', r'\1', texto)  # [[nota|texto]] -> texto
    # Checkboxes -> texto explícito (o modelo não entende [x]/[ ] de forma confiável)
    texto = re.sub(r'(?m)^(\s*)[-*]\s*\[[xX]\]\s*(.+)$', r'\1- \2 (concluído)', texto)
    texto = re.sub(r'(?m)^(\s*)[-*]\s*\[\s*\]\s*(.+)$', r'\1- \2 (pendente)', texto)
    texto = re.sub(r'\n{3,}', '\n\n', texto)                   # colapsa linhas em branco sobrando
    return texto.strip()


def avaliar_relevancia(pergunta: str, conteudo: str, minimo: float = 0.5) -> bool:
    """PURA e reutilizável: o 'conteudo' RESPONDE à 'pergunta'? Heurística barata por
    sobreposição de palavras-chave (sem stopwords, com stem simples). SÓ julga — não
    decide o que fazer depois (isso é do caller: cair no conhecimento, ou falha honesta).
    Assim qualquer ferramenta que precise do mesmo cuidado é só chamar esta função.
    'minimo' = fração das palavras-chave da pergunta que precisa aparecer no conteúdo."""
    chaves = {_stem(p) for p in _norm(pergunta).split() if len(p) >= 3 and p not in _STOPWORDS}
    if not chaves:
        return True   # pergunta sem palavra-chave (ex: 'o que tem aqui') — não bloqueia
    corpo = {_stem(t) for t in _norm(conteudo).split() if len(t) >= 3}
    return len(chaves & corpo) / len(chaves) >= minimo


def buscar_nota(assunto: str) -> str:
    """Acha a nota mais relevante para 'assunto' e devolve o conteúdo (fetch-only).
    Estratégia em 2 etapas:
      1. Casa pelo NOME do arquivo (mais confiável e barato — comportamento de sempre).
      2. Fallback: se nenhum nome casar, procura as palavras no CORPO das notas.
    Antes de devolver, PASSA a nota por avaliar_relevancia: match fraco (ex: 1 palavra
    solta num radar gigante) vira 'SEM_NOTA_RELEVANTE' em vez de cuspir a nota errada."""
    notas = _listar_notas()
    if not notas:
        return "SISTEMA: Não há notas acessíveis no Obsidian (vault vazio ou caminho errado)."

    # Etapa 1 — nome do arquivo
    alvo = set(_norm(assunto).split())
    melhor, melhor_score = None, 0
    for c in notas:
        palavras = set(_norm(os.path.splitext(os.path.basename(c))[0]).split())
        score = len(alvo & palavras)
        if score > melhor_score:
            melhor, melhor_score = c, score

    # Etapa 2 — fallback no corpo (só palavras de conteúdo, sem stopwords).
    # Aplica um stem simples (tira 's' do plural) pra "ovos" casar com "ovo".
    if not melhor:
        alvo_corpo = {_stem(p) for p in alvo if len(p) >= 3 and p not in _STOPWORDS}
        if alvo_corpo:
            melhor_corpo = 0
            for c in notas:
                try:
                    with open(c, encoding="utf-8") as f:
                        corpo = {_stem(t) for t in _norm(f.read()).split() if len(t) >= 3}
                except Exception:
                    continue
                score = len(alvo_corpo & corpo)
                if score > melhor_corpo:
                    melhor, melhor_corpo = c, score

    if not melhor:
        return "SISTEMA: SEM_NOTA_RELEVANTE"
    try:
        with open(melhor, encoding="utf-8") as f:
            bruto = f.read()
    except Exception as e:
        return f"SISTEMA: Erro ao ler a nota: {e}"
    # Grade de relevância: a nota escolhida realmente responde ao que foi pedido?
    # (match fraco = coincidência de 1 palavra). Inclui o NOME do arquivo — notas como
    # Novidades.md casam pelo título e o corpo pode nem repetir a palavra. O caller
    # decide o que fazer com o 'não'.
    nome = os.path.splitext(os.path.basename(melhor))[0]
    if not avaliar_relevancia(assunto, nome + "\n" + bruto):
        return "SISTEMA: SEM_NOTA_RELEVANTE"
    return _limpar_md(bruto)


# Pasta de ESCRITA da Luna. Ela só CRIA notas aqui — nunca edita nota existente,
# nunca toca no perfil.md nem no resto do vault. É a "caixa de entrada" dela.
_PASTA_INBOX = ("Luna", "Inbox")


def salvar_nota(conteudo: str, titulo: str = None, origem: str = "") -> str:
    """Cria (nunca sobrescreve) uma nota em Luna/Inbox com o conteúdo dado.
    Retorna mensagem SISTEMA: de sucesso ou erro. O código decide pasta/template/nome;
    a LLM só fornece conteudo/titulo."""
    conteudo = (conteudo or "").strip()
    if not conteudo:
        return "SISTEMA: Erro — não havia conteúdo para anotar."
    if not os.path.isdir(_VAULT):
        return "SISTEMA: Erro — vault do Obsidian não encontrado."

    pasta = os.path.join(_VAULT, *_PASTA_INBOX)
    os.makedirs(pasta, exist_ok=True)

    agora = datetime.datetime.now()
    titulo = (titulo or "").strip() or conteudo.splitlines()[0].strip()
    titulo = titulo[:80]

    nome_base = f"{agora:%Y-%m-%d %H%M} - {_slug(titulo)}"
    caminho = os.path.join(pasta, nome_base + ".md")
    n = 2  # se já existir nota no mesmo minuto com mesmo título, não sobrescreve
    while os.path.exists(caminho):
        caminho = os.path.join(pasta, f"{nome_base} ({n}).md")
        n += 1

    fm_origem = f"origem: {origem}\n" if origem else ""
    corpo = (
        f"---\n"
        f"criado: {agora:%Y-%m-%d %H:%M}\n"
        f"{fm_origem}"
        f"tags: [luna]\n"
        f"---\n\n"
        f"# {titulo}\n\n"
        f"{conteudo}\n"
    )
    try:
        with open(caminho, "w", encoding="utf-8") as f:
            f.write(corpo)
        return f"SISTEMA: Nota salva no Obsidian (Luna/Inbox): '{titulo}'."
    except Exception as e:
        return f"SISTEMA: Erro ao salvar a nota: {e}"


def salvar_foto(dados_imagem: bytes, legenda: str = "", origem: str = "", ext: str = "jpg") -> str:
    """Arquiva uma imagem em Luna/Inbox/anexos e cria uma nota que a embute, usando a
    legenda como descrição. NÃO usa visão — é arquivamento puro (a legenda já descreve)."""
    if not dados_imagem:
        return "SISTEMA: Erro — imagem vazia."
    if not os.path.isdir(_VAULT):
        return "SISTEMA: Erro — vault do Obsidian não encontrado."

    pasta = os.path.join(_VAULT, *_PASTA_INBOX)
    pasta_anexos = os.path.join(pasta, "anexos")
    os.makedirs(pasta_anexos, exist_ok=True)

    agora = datetime.datetime.now()
    ext = (ext or "jpg").lstrip(".")
    legenda = (legenda or "").strip()
    titulo = (legenda.splitlines()[0].strip() if legenda else f"Foto {agora:%d-%m %H:%M}")[:80]
    base = f"{agora:%Y-%m-%d %H%M} - {_slug(titulo)}"

    nome_img = f"{base}.{ext}"
    caminho_img = os.path.join(pasta_anexos, nome_img)
    n = 2
    while os.path.exists(caminho_img):
        nome_img = f"{base} ({n}).{ext}"
        caminho_img = os.path.join(pasta_anexos, nome_img)
        n += 1

    caminho_nota = os.path.join(pasta, base + ".md")
    n = 2
    while os.path.exists(caminho_nota):
        caminho_nota = os.path.join(pasta, f"{base} ({n}).md")
        n += 1

    fm_origem = f"origem: {origem}\n" if origem else ""
    corpo = (
        f"---\n"
        f"criado: {agora:%Y-%m-%d %H:%M}\n"
        f"{fm_origem}"
        f"tags: [luna, foto]\n"
        f"---\n\n"
        f"# {titulo}\n\n"
        f"![[{nome_img}]]\n"
    )
    if legenda and legenda != titulo:   # evita repetir a legenda quando ela já é o título
        corpo += f"\n{legenda}\n"
    try:
        with open(caminho_img, "wb") as f:
            f.write(dados_imagem)
        with open(caminho_nota, "w", encoding="utf-8") as f:
            f.write(corpo)
        return f"SISTEMA: Foto salva no Obsidian (Luna/Inbox): '{titulo}'."
    except Exception as e:
        return f"SISTEMA: Erro ao salvar a foto: {e}"


# ── ANIMES (lista configurada pelo usuário no Obsidian) ──
def ler_lista_animes() -> list:
    """Lê os animes dos BULLETS da nota Luna/animes.md. Retorna [(nome_busca, apelido)]:
    '- Nome do anime'            -> apelido None (a Luna fala o título oficial em inglês)
    '- Nome do anime | apelido'  -> a Luna fala o APELIDO (útil pra títulos quilométricos)."""
    caminho = os.path.join(_VAULT, "Luna", "animes.md")
    animes = []
    try:
        em_comentario = False
        with open(caminho, encoding="utf-8") as f:
            for linha in f:
                s = linha.strip()
                if "<!--" in s:
                    em_comentario = True
                if "-->" in s:
                    em_comentario = False
                    continue
                if em_comentario or not s.startswith(("-", "*")):
                    continue
                nome = s[1:].strip().strip("[]").strip()
                if not nome or nome.startswith((">", "-")):
                    continue
                busca, _, apelido = nome.partition("|")
                animes.append((busca.strip(), apelido.strip() or None))
    except Exception:
        return []
    return animes


# ── RADAR (feeds RSS configurados pelo usuário no Obsidian) ──
def ler_feeds_radar() -> list:
    """Lê as URLs de RSS dos BULLETS da nota Luna/radar_rss.md. Só linhas que
    começam com '-' ou '*' contam — assim a dica com link de exemplo é ignorada."""
    caminho = os.path.join(_VAULT, "Luna", "radar_rss.md")
    feeds = []
    try:
        with open(caminho, encoding="utf-8") as f:
            for linha in f:
                if linha.lstrip().startswith(("-", "*")):
                    m = re.search(r'https?://[^\s`)\]>]+', linha)
                    if m:
                        feeds.append(m.group(0).rstrip('.,`'))
    except Exception:
        return []
    return feeds


# ── SEMEADURA (vault novo: cria as notas de CONFIG com template) ──
# Só cria o que NÃO existe — nunca toca em nota existente. As notas de escrita
# (Luna/Inbox, Novidades.md) a Luna já cria sozinha quando precisa.
_TEMPLATES_VAULT = {
    ("Luna", "perfil.md"): """# Perfil — quem a Luna acompanha

> Esta nota é o NÚCLEO da Luna: ela é carregada em TODA conversa.
> Mantenha ENXUTA — cada linha gasta contexto do modelo. Bullets curtos.
> (Aparência pra desenhos NÃO vai aqui — fica em modelos/desenho.json.)

## Sobre
- Trabalho: (ex: suporte do sistema X)
- Família: (ex: casado com Fulana)
- Gosta de: (jogos, séries, hobbies...)

## Agora (atualizo quando muda)
- Foco da semana:
- Humor/energia:
- Acompanhar:
  - [ ] exemplo de pendência (a Luna entende [ ] aberto e [x] feito)
""",
    ("Luna", "animes.md"): """# 🎌 Animes que a Luna acompanha

> A Luna te avisa quando sai episódio novo (fonte: AniList).
> Um anime por linha, em bullet:
>
> `- Nome do anime` → ela fala o título oficial (inglês)
> `- Nome do anime | apelido` → ela fala o APELIDO (bom pra título quilométrico)
>
> ⚠️ No NOME use o título completo (Crunchyroll em inglês OU japonês/romaji):
> ✅ `That Time I Got Reincarnated as a Slime`  ✅ `Kimetsu no Yaiba`
> ❌ `Demon Slayer` (nome curto pode achar o anime errado — apelido é só depois do `|`)
>
> Exemplos (copie pra fora da citação pra valer):
> `- One Piece`
> `- That Time I Got Reincarnated as a Slime | Anime do Slime`
""",
    ("Luna", "radar_rss.md"): """# Radar RSS — fontes que a Luna acompanha

Cole aqui links de feeds RSS, um por linha em bullet. A Luna lê os links,
te avisa quando sai novidade e anota tudo em **Novidades.md** (na raiz do vault).

> Dica: qualquer subreddit vira feed colocando `.rss` no fim
> (ex: `https://www.reddit.com/r/dota2/.rss`).
> Exemplo de linha ativa (tire da citação pra valer):
> `- https://www.adrenaline.com.br/feed/`
""",
}


def semear_vault() -> list:
    """Cria as notas de CONFIGURAÇÃO com template quando não existem (vault novo).
    Nunca sobrescreve nada. Retorna os caminhos criados (vazio se nada faltava)."""
    if not os.path.isdir(_VAULT):
        return []
    criadas = []
    for partes, conteudo in _TEMPLATES_VAULT.items():
        caminho = os.path.join(_VAULT, *partes)
        if os.path.exists(caminho):
            continue
        try:
            os.makedirs(os.path.dirname(caminho), exist_ok=True)
            with open(caminho, "w", encoding="utf-8") as f:
                f.write(conteudo)
            criadas.append("/".join(partes))
        except Exception:
            pass
    return criadas


def _trim_novidades(conteudo: str, max_horas: int) -> str:
    """Mantém só os blocos '## data hora' dentro de max_horas; descarta os mais velhos
    (janela rolante — a nota não cresce sem limite)."""
    limite = datetime.datetime.now() - datetime.timedelta(hours=max_horas)
    blocos = re.split(r'(?m)^(?=## \d{4}-\d{2}-\d{2} \d{2}:\d{2})', conteudo)
    mantidos = []
    for b in blocos:
        m = re.match(r'## (\d{4}-\d{2}-\d{2} \d{2}:\d{2})', b)
        if not m:
            continue
        try:
            dt = datetime.datetime.strptime(m.group(1), '%Y-%m-%d %H:%M')
        except ValueError:
            continue
        if dt >= limite:
            mantidos.append(b.strip())
    return "\n\n".join(mantidos)


def adicionar_novidades(itens: list, max_horas: int = 72) -> None:
    """Prepende um bloco datado de novidades em Novidades.md (raiz do vault).
    itens = lista de (titulo, link, fonte[, resumo[, imagem]]). Mantém só os blocos
    das últimas max_horas (janela rolante). A Luna só escreve nesse arquivo dedicado."""
    if not itens or not os.path.isdir(_VAULT):
        return
    caminho = os.path.join(_VAULT, "Novidades.md")
    agora = datetime.datetime.now()
    linhas = [f"## {agora:%Y-%m-%d %H:%M}\n"]
    for item in itens:
        t, l, fonte = item[0], item[1], item[2]
        resumo = item[3] if len(item) > 3 else ""
        imagem = item[4] if len(item) > 4 else ""
        linhas.append(f"**[{t}]({l})** — {fonte}\n")
        if imagem:
            # |200 = miniatura (largura em px). Sem isso o Obsidian renderiza a
            # imagem em largura cheia e "polui" a leitura da notícia.
            linhas.append(f"![|200]({imagem})\n")
        if resumo:
            linhas.append(f"> {resumo}\n")
        linhas.append("\n")
    bloco = "".join(linhas)
    try:
        antigo = ""
        if os.path.exists(caminho):
            with open(caminho, encoding="utf-8") as f:
                antigo = f.read()
        conteudo = _trim_novidades(bloco + "\n" + antigo, max_horas)
        with open(caminho, "w", encoding="utf-8") as f:
            f.write(conteudo + "\n")
    except Exception:
        pass
