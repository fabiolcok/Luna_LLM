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


# ── MEMÓRIA EPISÓDICA (o que anda acontecendo — datado, o usuário confirma) ──
# Duas notas: Memoria.md = ATIVO (entra no prompt como "recentes" + no retrieval);
# Memoria_arquivo.md = FRIO (evento velho que esfriou — NÃO entra como recente, mas
# CONTINUA no retrieval, pra poder "esquentar" e voltar pro ativo se o assunto voltar).
_TEMPLATE_MEMORIA = """# 🧠 Memória da Luna

> O que a Luna lembra do que anda acontecendo com você — eventos, assuntos em aberto,
> humor. Ela PROPÕE e você confirma no modo web; mas pode editar/apagar à vontade aqui.
> Formato: uma por linha, com data — `- [AAAA-MM-DD] o que aconteceu`.
> A Luna usa as MAIS RECENTES; se algo mudar, o mais novo manda.
> Eventos antigos que ninguém toca vão pro **Memoria_arquivo.md** (mas ela ainda lembra
> deles se o assunto voltar).

"""

_TEMPLATE_MEMORIA_ARQ = """# 🧊 Memória da Luna — arquivo (frio)

> Eventos antigos que esfriaram (a Luna não usa mais pro dia a dia), mas que ela ainda
> PUXA se o assunto voltar à tona — aí a lembrança "esquenta" e volta pro Memoria.md.
> Mesmo formato: `- [AAAA-MM-DD] o que aconteceu`. Pode apagar o que não quiser guardar.

"""

_RE_MEM_LINHA = re.compile(r'^\s*[-*]\s*\[(\d{4})-(\d{2})-(\d{2})\]\s*(.+?)\s*$')

_MEM_ATIVO   = ("Luna", "Memoria.md")
_MEM_ARQUIVO = ("Luna", "Memoria_arquivo.md")


def _listar_memoria_de(partes) -> list:
    """Lê uma nota de memória (ativo ou arquivo) e devolve [(data 'AAAA-MM-DD', fato)]
    do MAIS RECENTE pro mais antigo."""
    caminho = os.path.join(_VAULT, *partes)
    itens = []
    try:
        with open(caminho, encoding="utf-8") as f:
            for linha in f:
                m = _RE_MEM_LINHA.match(linha)
                if m:
                    a, mes, d, fato = m.groups()
                    itens.append((f"{a}-{mes}-{d}", fato.strip()))
    except Exception:
        return []
    itens.sort(key=lambda x: x[0], reverse=True)   # mais recente primeiro
    return itens


def listar_memoria_episodica() -> list:
    """Fatos ATIVOS [(data, fato)] (Memoria.md), do mais recente pro mais antigo.
    Base pra formatar os recentes do prompt e pra embeddar no retrieval."""
    return _listar_memoria_de(_MEM_ATIVO)


def listar_memoria_arquivo() -> list:
    """Fatos FRIOS [(data, fato)] (Memoria_arquivo.md) — não entram como recentes, mas
    ainda são embeddados no retrieval pra poderem 'esquentar'."""
    return _listar_memoria_de(_MEM_ARQUIVO)


def fmt_memoria(data: str, fato: str) -> str:
    """'2026-07-24','fato' -> '- [24/07] fato' (formato enxuto pro prompt)."""
    p = data.split("-")
    return f"- [{p[2]}/{p[1]}] {fato}" if len(p) == 3 else f"- {fato}"


def ler_memoria_episodica(limite: int = 15) -> str:
    """Os `limite` fatos mais RECENTES, já formatados ('- [DD/MM] fato'). Recência
    resolve conflito: o novo manda. '' se não houver nota/itens."""
    itens = listar_memoria_episodica()
    return "\n".join(fmt_memoria(d, f) for d, f in itens[:limite]) if itens else ""


def adicionar_memoria(fato: str, data: str = None) -> bool:
    """Anexa uma lembrança datada em Luna/Memoria.md (cria com template se não existir).
    'data' no formato AAAA-MM-DD (hoje, se None). Só cria/escreve; nunca reescreve o resto."""
    fato = (fato or "").strip()
    if not fato or not os.path.isdir(_VAULT):
        return False
    data = data or datetime.datetime.now().strftime("%Y-%m-%d")
    caminho = os.path.join(_VAULT, "Luna", "Memoria.md")
    linha = f"- [{data}] {fato}\n"
    try:
        os.makedirs(os.path.dirname(caminho), exist_ok=True)
        existe = os.path.exists(caminho)
        with open(caminho, "a", encoding="utf-8") as f:
            if not existe:
                f.write(_TEMPLATE_MEMORIA)
            f.write(linha)
        return True
    except Exception:
        return False


def _idade_dias(data_iso: str) -> int:
    """Dias entre a data (AAAA-MM-DD) e hoje. 0 se não parsear."""
    try:
        d = datetime.datetime.strptime(data_iso, "%Y-%m-%d").date()
        return (datetime.date.today() - d).days
    except Exception:
        return 0


def arquivar_antigas(dias: int = 45) -> int:
    """ESFRIAR: move do ativo (Memoria.md) pro frio (Memoria_arquivo.md) os fatos com
    mais de `dias` dias. Preserva cabeçalho e formatação — só tira as LINHAS de fato
    vencidas. Devolve quantas esfriaram. Escrita segura: anexa no frio PRIMEIRO (pior
    caso = duplicata, nunca perda), depois reescreve o ativo de forma atômica."""
    if not os.path.isdir(_VAULT):
        return 0
    caminho = os.path.join(_VAULT, *_MEM_ATIVO)
    if not os.path.exists(caminho):
        return 0
    try:
        with open(caminho, encoding="utf-8") as f:
            linhas = f.readlines()
    except Exception:
        return 0
    manter, esfriar = [], []
    for linha in linhas:
        m = _RE_MEM_LINHA.match(linha)
        if m and _idade_dias(f"{m.group(1)}-{m.group(2)}-{m.group(3)}") > dias:
            esfriar.append((f"{m.group(1)}-{m.group(2)}-{m.group(3)}", m.group(4).strip()))
        else:
            manter.append(linha)
    if not esfriar:
        return 0
    arq = os.path.join(_VAULT, *_MEM_ARQUIVO)
    try:                                            # 1) frio primeiro (append seguro)
        os.makedirs(os.path.dirname(arq), exist_ok=True)
        existe = os.path.exists(arq)
        with open(arq, "a", encoding="utf-8") as f:
            if not existe:
                f.write(_TEMPLATE_MEMORIA_ARQ)
            for data, fato in esfriar:
                f.write(f"- [{data}] {fato}\n")
    except Exception:
        return 0
    try:                                            # 2) reescreve o ativo (atômico)
        tmp = caminho + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            f.writelines(manter)
        os.replace(tmp, caminho)
    except Exception:
        return 0
    return len(esfriar)


def esquentar_memoria(fato: str) -> bool:
    """ESQUENTAR: o assunto de um fato frio voltou à tona — tira ele do Memoria_arquivo.md
    e devolve pro Memoria.md com data de HOJE (relevante de novo). Devolve True se moveu.
    Adiciona no ativo ANTES de tirar do frio (pior caso = duplicata, nunca perda)."""
    fato = (fato or "").strip()
    if not fato or not os.path.isdir(_VAULT):
        return False
    arq = os.path.join(_VAULT, *_MEM_ARQUIVO)
    if not os.path.exists(arq):
        return False
    try:
        with open(arq, encoding="utf-8") as f:
            linhas = f.readlines()
    except Exception:
        return False
    achou, resto = False, []
    for linha in linhas:
        m = _RE_MEM_LINHA.match(linha)
        if m and not achou and m.group(4).strip() == fato:
            achou = True
        else:
            resto.append(linha)
    if not achou or not adicionar_memoria(fato):    # adiciona no ativo (data hoje)
        return False
    try:                                            # tira do frio (atômico)
        tmp = arq + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            f.writelines(resto)
        os.replace(tmp, arq)
    except Exception:
        return False
    return True


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
    ("Luna", "Memoria.md"): _TEMPLATE_MEMORIA,
    ("Luna", "Memoria_arquivo.md"): _TEMPLATE_MEMORIA_ARQ,
    ("Luna", "radar_rss.md"): """# Radar RSS — fontes que a Luna acompanha

Cole aqui links de feeds RSS, um por linha em bullet. A Luna lê os links,
te avisa quando sai novidade e anota tudo em **Novidades.md** (na raiz do vault).

> Dica: qualquer subreddit vira feed colocando `.rss` no fim
> (ex: `https://www.reddit.com/r/dota2/.rss`).
> Exemplo de linha ativa (tire da citação pra valer):
> `- https://www.adrenaline.com.br/feed/`
""",
}


# Snippet de CSS que deixa a nota Novidades em colunas (cards lado a lado).
# É instalado junto com as notas — quem clonar o projeto ganha o layout também.
# Só age em notas com 'cssclasses: novidades-grid' (ou seja, só o Novidades.md).
_SNIPPET_NOVIDADES = """/* Luna — Novidades em colunas
   Só afeta notas com  cssclasses: novidades-grid  (ou seja: só o Novidades.md).
   Ligue em: Configurações → Aparência → Snippets de CSS → luna-novidades */

/* Colunas ADAPTATIVAS: cria quantas couberem (~340px cada).
   Janela pequena = 1-2 colunas; maximizado = 3-4. Sem número fixo. */
.novidades-grid .markdown-preview-section {
  column-width: 340px;
  column-gap: 18px;
}

/* cada notícia (callout) nunca é cortada no meio entre as colunas */
.novidades-grid .markdown-preview-section .callout {
  break-inside: avoid;
  -webkit-column-break-inside: avoid;
  page-break-inside: avoid;
  margin: 0 0 14px 0;
}

/* o cabeçalho da data atravessa todas as colunas */
.novidades-grid .markdown-preview-section h2 {
  column-span: all;
  margin-top: 18px;
}

/* CAPA: ocupa a largura do card, mas com ALTURA TRAVADA — não vira outdoor
   quando você maximiza. object-fit: cover corta bonito, sem distorcer. */
.novidades-grid .markdown-preview-section .callout img {
  width: 100%;
  max-height: 170px;
  object-fit: cover;
  border-radius: 6px;
  display: block;
}
"""


def semear_vault() -> list:
    """Cria as notas de CONFIGURAÇÃO e o snippet de CSS quando não existem (vault novo).
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

    # Snippet de CSS do Novidades (o usuário ainda precisa LIGAR em Aparência)
    snippet = os.path.join(_VAULT, ".obsidian", "snippets", "luna-novidades.css")
    if not os.path.exists(snippet):
        try:
            os.makedirs(os.path.dirname(snippet), exist_ok=True)
            with open(snippet, "w", encoding="utf-8") as f:
                f.write(_SNIPPET_NOVIDADES)
            criadas.append(".obsidian/snippets/luna-novidades.css")
        except Exception:
            pass
    return criadas


def _data_cabecalho_novidade(bloco: str):
    """Data/hora do cabeçalho de um bloco de novidades. Aceita o formato NOVO
    ('## 22/07/2026 · 12:16') e o ANTIGO ('## 2026-07-22 12:16'), pra não perder
    o que já estava na nota quando o formato mudou."""
    m = re.match(r'##\s*(\d{2}/\d{2}/\d{4})(?:\s*·\s*(\d{2}:\d{2}))?', bloco)   # hora opcional (dia agrupado)
    if m:
        try:
            return datetime.datetime.strptime(f"{m.group(1)} {m.group(2) or '00:00'}", "%d/%m/%Y %H:%M")
        except ValueError:
            return None
    m = re.match(r'##\s*(\d{4}-\d{2}-\d{2})(?:\s+(\d{2}:\d{2}))?', bloco)       # formato antigo (ISO)
    if m:
        try:
            return datetime.datetime.strptime(f"{m.group(1)} {m.group(2) or '00:00'}", "%Y-%m-%d %H:%M")
        except ValueError:
            return None
    return None


def _trim_novidades(conteudo: str, max_horas: int) -> str:
    """Mantém só os blocos datados dentro de max_horas; descarta os mais velhos
    (janela rolante — a nota não cresce sem limite)."""
    limite = datetime.datetime.now() - datetime.timedelta(hours=max_horas)
    blocos = re.split(r'(?m)^(?=##\s*(?:\d{4}-\d{2}-\d{2}|\d{2}/\d{2}/\d{4}))', conteudo)
    mantidos = []
    for b in blocos:
        dt = _data_cabecalho_novidade(b)
        if dt and dt >= limite:
            mantidos.append(b.strip())
    return "\n\n".join(mantidos)


def _inline_seguro(txt: str) -> str:
    """Texto seguro pra uma linha de callout: sem quebras e sem colchete que quebre o link."""
    return re.sub(r'\s+', ' ', (txt or '').strip()).replace('[', '(').replace(']', ')')


# Marca a nota pro snippet de CSS que joga as novidades em 2 colunas (só esta nota é
# afetada). O snippet fica em .obsidian/snippets/luna-novidades.css — ligue em
# Configurações → Aparência → Snippets de CSS.
_FRONTMATTER_NOVIDADES = "---\ncssclasses:\n  - novidades-grid\n---\n\n"
# Frontmatter que sobrou GRUDADO no corpo (bug antigo: era reanexado a cada novidade).
# Removido antes de recompor — o frontmatter válido é só o do topo, escrito uma vez.
_RE_FM_NOVIDADES = re.compile(r'(?m)^---\ncssclasses:\n  - novidades-grid\n---\n+')


def _cartao_novidade(item) -> str:
    """Uma novidade -> um callout [!tip] (capa + fonte + resumo)."""
    titulo = _inline_seguro(item[0]) or "(sem título)"
    link, fonte = item[1], _inline_seguro(item[2])
    resumo = item[3] if len(item) > 3 else ""
    imagem = item[4] if len(item) > 4 else ""
    cx = [f"> [!tip]+ [{titulo}]({link})"]
    if imagem:
        cx.append(f"> ![|220]({imagem})")   # |220 = miniatura; sem isso vem em largura cheia
    if fonte:
        cx.append(f"> `{fonte}`")
    for ln in (resumo or "").strip().splitlines():
        if ln.strip():
            cx.append(f"> {ln.strip()}")
    return "\n".join(cx)


def _reagrupar_novidades(conteudo: str) -> str:
    """Tira frontmatters do corpo e agrupa TODOS os callouts por DIA sob um único
    '## DD/MM/YYYY' (mais recente primeiro). É isso que faz o snippet de colunas funcionar:
    vários cards sob um cabeçalho fluem em colunas — um cabeçalho por card (com hora) forçava
    faixa full-width e virava 'uma por linha'. Consolida também os blocos com hora legados."""
    conteudo = _RE_FM_NOVIDADES.sub("", conteudo)
    blocos = re.split(r'(?m)^(?=##\s*(?:\d{4}-\d{2}-\d{2}|\d{2}/\d{2}/\d{4}))', conteudo)
    por_dia = {}                       # 'YYYY-MM-DD' -> [dt_do_dia, [cards...]]
    for b in blocos:
        dt = _data_cabecalho_novidade(b)
        if not dt:
            continue
        corpo = b.split("\n", 1)[1].strip() if "\n" in b else ""
        chave = dt.strftime("%Y-%m-%d")
        por_dia.setdefault(chave, [dt, []])
        if corpo:
            por_dia[chave][1].append(corpo)
    partes = []
    for chave in sorted(por_dia, reverse=True):        # dia mais recente primeiro
        dt, cards = por_dia[chave]
        if cards:
            partes.append(f"## {dt:%d/%m/%Y}\n\n" + "\n\n".join(cards))
    return "\n\n".join(partes)


def adicionar_novidades(itens: list, max_horas: int = 72) -> None:
    """Prepende novidades em Novidades.md (raiz do vault), AGRUPADAS POR DIA (um '## dia'
    com vários callouts — pro snippet de colunas funcionar). itens = lista de
    (titulo, link, fonte[, resumo[, imagem]]). Mantém só as últimas max_horas (janela rolante)."""
    if not itens or not os.path.isdir(_VAULT):
        return
    caminho = os.path.join(_VAULT, "Novidades.md")
    agora = datetime.datetime.now()
    novos = f"## {agora:%d/%m/%Y}\n\n" + "\n\n".join(_cartao_novidade(i) for i in itens)
    try:
        antigo = ""
        if os.path.exists(caminho):
            with open(caminho, encoding="utf-8") as f:
                antigo = f.read()
        conteudo = _reagrupar_novidades(novos + "\n\n" + antigo)   # junta hoje c/ hoje, tira FMs
        conteudo = _trim_novidades(conteudo, max_horas).strip()
        with open(caminho, "w", encoding="utf-8") as f:
            f.write(_FRONTMATTER_NOVIDADES + conteudo + "\n")
    except Exception:
        pass
