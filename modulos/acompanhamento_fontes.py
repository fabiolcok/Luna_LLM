"""Acompanhamentos de fontes cadastradas. HTTP não disputa o turno da conversa."""
from copy import deepcopy
from pathlib import Path
import hashlib
import ipaddress
import json
import re
import socket
import sys
import threading
import time
from urllib.parse import urljoin, urlsplit, urlunsplit
import uuid

from bs4 import BeautifulSoup
import feedparser
import requests

CAMINHO = Path("modelos/acompanhamento_fontes.json")
INTERVALO = 6 * 3600
REPETIR_ERRO = 30 * 60
ADIAMENTO = 2 * 3600
MAX_BYTES = 400_000
MAX_ITENS = 10
_trava = threading.RLock()
_consulta = threading.Lock()
_thread = None
_verificando = set()


def _texto(valor, limite):
    return re.sub(r"\s+", " ", str(valor or "")).strip()[:limite]


def _hash(texto):
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()[:24]


def validar_url(valor, *, resolver=False):
    try:
        p = urlsplit(str(valor or "").strip())
        porta = p.port
        if (p.scheme not in {"http", "https"} or not p.hostname or p.username is not None or p.password is not None
                or porta not in {None, 80, 443} or len(valor) > 2000):
            raise ValueError
        host = p.hostname.rstrip(".")
        if host.lower() in {"localhost", "localhost.localdomain"} or host.lower().endswith(".local"):
            raise ValueError
        try:
            endereco = ipaddress.ip_address(host)
        except ValueError:
            endereco = None
        if endereco is not None and not endereco.is_global:
            raise ValueError
        if resolver:
            enderecos = socket.getaddrinfo(host, porta or (443 if p.scheme == "https" else 80),
                                           type=socket.SOCK_STREAM)
            if not enderecos or any(not ipaddress.ip_address(e[4][0]).is_global for e in enderecos):
                raise ValueError
        return urlunsplit((p.scheme, p.netloc, p.path or "/", p.query, ""))
    except (ValueError, TypeError, OSError):
        raise ValueError("Use um link público HTTP/HTTPS, sem login ou porta personalizada.") from None


def _carregar():
    if not CAMINHO.exists():
        return {"versao": 1, "itens": []}
    try:
        dados = json.loads(CAMINHO.read_text(encoding="utf-8"))
        if dados.get("versao") != 1 or not isinstance(dados.get("itens"), list):
            raise ValueError
        obrigatorios = {"id", "revisao", "status", "assunto", "interesse", "situacao", "fontes",
                        "cache", "vistos", "pendentes", "novidades", "adiado_ate", "resultado",
                        "verificado_em", "proxima_verificacao", "erros"}
        for i in dados["itens"]:
            if (not isinstance(i, dict) or not obrigatorios.issubset(i)
                    or i["status"] not in {"ativo", "pausado", "encerrado"}
                    or not isinstance(i["fontes"], list) or not isinstance(i["cache"], dict)
                    or any(not isinstance(i[k], list) for k in ("vistos", "pendentes", "novidades", "erros"))):
                raise ValueError
        return dados
    except (ValueError, OSError, AttributeError):
        raise ValueError("Não consegui ler os acompanhamentos salvos; o arquivo foi preservado.") from None


def _salvar(dados):
    CAMINHO.parent.mkdir(parents=True, exist_ok=True)
    tmp = CAMINHO.with_suffix(".tmp")
    tmp.write_text(json.dumps(dados, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(CAMINHO)


def _notificar():
    servidor = sys.modules.get("servidor")
    if servidor and hasattr(servidor, "notificar_acompanhamentos"):
        servidor.notificar_acompanhamentos()


def _encontrar(dados, identificador):
    return next((i for i in dados["itens"] if i["id"] == identificador), None)


def validar_cadastro(cadastro):
    c = cadastro if isinstance(cadastro, dict) else {}
    assunto, interesse = _texto(c.get("assunto"), 120), _texto(c.get("interesse"), 400)
    if len(assunto) < 3 or len(interesse) < 8:
        raise ValueError("Preencha o assunto e explique qual mudança interessa.")
    fontes = c.get("fontes", [])
    if isinstance(fontes, str):
        fontes = [u.strip() for u in fontes.splitlines() if u.strip()]
    if not isinstance(fontes, list) or not 1 <= len(fontes) <= 3:
        raise ValueError("Informe de um a três links, um por linha.")
    return {"assunto": assunto, "interesse": interesse, "situacao": _texto(c.get("situacao"), 300),
            "fontes": list(dict.fromkeys(validar_url(u) for u in fontes))}


def agir(acao, *, identificador="", cadastro=None, novidade_id="", criacao_id=""):
    try:
        if acao == "verificar":
            ok = agendar_verificacao(identificador=identificador, forcar=True)
            return {"ok": ok, "texto": "Consultando as fontes." if ok else
                    "Consulta em andamento ou acompanhamento pausado.", "id": identificador}
        with _trava:
            dados = _carregar()
            item = _encontrar(dados, identificador)
            if acao in {"criar", "editar"}:
                # Uma confirmação reenviada após queda de conexão não cria outro monitor.
                if acao == "criar" and criacao_id:
                    anterior = _encontrar(dados, criacao_id)
                    if anterior:
                        return {"ok": True, "texto": "Esse acompanhamento já foi cadastrado.", "id": anterior["id"]}
                if acao == "editar" and not item:
                    raise ValueError("Esse acompanhamento não existe mais.")
                if acao == "criar" and len(dados["itens"]) >= MAX_ITENS:
                    raise ValueError("O limite é de dez acompanhamentos de fontes.")
                c = validar_cadastro(cadastro)
                assunto, interesse, fontes = c["assunto"], c["interesse"], c["fontes"]
                if not item:
                    item = {"id": criacao_id or uuid.uuid4().hex[:16], "revisao": 0, "status": "ativo",
                            "novidades": [], "verificado_em": 0, "adiado_ate": 0}
                    dados["itens"].append(item)
                item.update({"assunto": assunto, "interesse": interesse,
                             "situacao": _texto(c.get("situacao"), 300), "fontes": fontes,
                             "revisao": item["revisao"] + 1, "cache": {}, "vistos": [], "pendentes": [],
                             "proxima_verificacao": 0, "erros": [],
                             "resultado": "A próxima consulta cria uma referência; novidades antigas não serão anunciadas."})
                for n in item["novidades"]:
                    n["lido"] = True
            elif item and acao in {"pausar", "retomar", "encerrar", "excluir", "adiar", "visto"}:
                if acao in {"adiar", "visto"}:
                    n = next((n for n in item["novidades"] if n["id"] == novidade_id and not n["lido"]), None)
                    if not n:
                        raise ValueError("Essa novidade não está mais pendente.")
                    if acao == "adiar":
                        item["adiado_ate"] = time.time() + ADIAMENTO
                        n["avisado_em"] = 0
                    else:
                        n["lido"] = True
                else:
                    item["revisao"] += 1
                    if acao == "excluir":
                        dados["itens"].remove(item)
                    else:
                        item["status"] = {"pausar": "pausado", "retomar": "ativo", "encerrar": "encerrado"}[acao]
                        if acao == "retomar":
                            item["proxima_verificacao"] = 0
            else:
                raise ValueError("Ação inválida ou acompanhamento inexistente.")
            _salvar(dados)
            resposta = {"ok": True, "texto": {
                "criar": "Acompanhamento cadastrado. Vou criar a referência das fontes.",
                "editar": "Cadastro atualizado. Vou criar uma nova referência.",
                "pausar": "Acompanhamento pausado.", "retomar": "Acompanhamento retomado.",
                "encerrar": "Acompanhamento encerrado.", "excluir": "Acompanhamento removido.",
                "adiar": "Convite adiado por duas horas.", "visto": "Novidade marcada como vista.",
            }[acao], "id": item["id"]}
        _notificar()
        if acao in {"criar", "editar", "retomar"}:
            agendar_verificacao(identificador=item["id"])
        return resposta
    except (ValueError, OSError) as e:
        return {"ok": False, "texto": str(e), "id": identificador}


def _limpar_html(texto):
    soup = BeautifulSoup(texto, "html.parser")
    for tag in soup(["script", "style", "nav", "header", "footer", "form", "noscript"]):
        tag.decompose()
    principal = soup.find("main") or soup.find("article") or soup
    return principal.get_text("\n", strip=True)


def _documentos(texto, url, tipo):
    if "xml" in tipo or re.match(r"\s*(?:<\?xml[^>]*>\s*)?<(?:rss|feed)\b", texto):
        feed = feedparser.parse(texto)
        if not feed.entries:
            if not feed.get("version"):
                raise ValueError("O feed não pôde ser lido.")
            return []
        docs = []
        for e in feed.entries[:20]:
            conteudo = e.get("summary", "") + "\n" + "\n".join(c.get("value", "") for c in e.get("content", []))
            try:
                link = validar_url(urljoin(url, e.get("link") or url))
            except ValueError:
                link = url
            docs.append({"url": link, "texto": _texto(e.get("title", ""), 240) + "\n" + _limpar_html(conteudo)})
        return docs
    bruto = _limpar_html(texto) if "html" in tipo or re.search(r"<(?:html|body|article|main)\b", texto, re.I) else texto
    if not bruto.strip():
        raise ValueError("A página não forneceu texto legível.")
    return [{"url": url, "texto": bruto}]


def consultar_fonte(url, anterior):
    headers = {"User-Agent": "Luna-LLM-Acompanhamentos/1.0", "Accept": "text/html,application/atom+xml,application/rss+xml,text/plain"}
    if anterior.get("etag"):
        headers["If-None-Match"] = anterior["etag"]
    if anterior.get("modified"):
        headers["If-Modified-Since"] = anterior["modified"]
    atual = url
    with requests.Session() as sessao:
        # Links públicos cadastrados não devem usar cookies, credenciais ou proxies do PC.
        sessao.trust_env = False
        for _ in range(4):
            atual = validar_url(atual, resolver=True)
            with sessao.get(atual, headers=headers, timeout=(3, 8), stream=True, allow_redirects=False) as r:
                if r.status_code in {301, 302, 303, 307, 308}:
                    atual = urljoin(atual, r.headers.get("Location", ""))
                    continue
                if r.status_code == 304:
                    if not anterior.get("semeada"):
                        raise ValueError("Fonte sem referência para resposta 304.")
                    return None, anterior
                r.raise_for_status()
                if r.status_code != 200:
                    raise ValueError("Resposta HTTP inesperada.")
                partes, tamanho = [], 0
                for parte in r.iter_content(16384):
                    tamanho += len(parte)
                    if tamanho > MAX_BYTES:
                        raise ValueError("A página ultrapassou o limite de leitura.")
                    partes.append(parte)
                tipo = r.headers.get("Content-Type", "")
                encoding = r.encoding if "charset=" in tipo.lower() else "utf-8-sig"
                texto = b"".join(partes).decode(encoding or "utf-8", errors="replace")
                return _documentos(texto, atual, r.headers.get("Content-Type", "")), {
                    "etag": r.headers.get("ETag", ""), "modified": r.headers.get("Last-Modified", ""),
                    "semeada": True,
                }
    raise ValueError("A fonte redirecionou vezes demais.")


def _linhas(texto):
    return list(dict.fromkeys(_texto(l, 1200) for l in str(texto or "")[:60000].splitlines() if l.strip()))[:1000]


def _mudancas(documentos, anterior, cache, vistos, fonte):
    antigo = anterior.get("documentos", {})
    novo = {}
    pendentes = []
    for d in documentos:
        linhas = _linhas(d["texto"])
        hashes = [_hash(l) for l in linhas]
        novo[d["url"]] = hashes
        versao_documento = _hash("\n".join(linhas))
        if not anterior.get("semeada"):
            if versao_documento not in vistos:
                vistos.append(versao_documento)
            continue
        anteriores = set(antigo.get(d["url"], []))
        indices = [j for j, h in enumerate(hashes) if h not in anteriores]
        if not indices:
            continue
        # Um trecho novo precisa dos vizinhos para não perder negação, estágio ou cabeçalho.
        posicoes = sorted({p for j in indices[:10] for p in range(max(0, j-1), min(len(linhas), j+3))})
        trecho = "\n".join(linhas[p] for p in posicoes)[:6000]
        id_ = _hash("\n".join(linhas[j] for j in indices))
        if id_ not in vistos and versao_documento not in vistos:
            vistos.append(id_)
            if versao_documento != id_:
                vistos.append(versao_documento)
            pendentes.append({"id": id_, "trecho": trecho, "novo": "\n".join(linhas[j] for j in indices)[:4000],
                              "url": d["url"], "fonte": fonte,
                              "tentativas": 0, "analisar_apos": 0})
    cache["documentos"] = novo
    return pendentes


def verificar(*, identificador="", forcar=False, agora=None, consultar=None):
    agora = time.time() if agora is None else agora
    consultar = consultar or consultar_fonte
    if not _consulta.acquire(blocking=False):
        return False
    try:
        with _trava:
            itens = deepcopy(_carregar()["itens"])
        for antes in itens:
            if (antes["status"] != "ativo" or identificador and antes["id"] != identificador
                    or not forcar and agora < antes["proxima_verificacao"]):
                continue
            with _trava:
                _verificando.add(antes["id"])
            _notificar()
            cache, vistos = deepcopy(antes["cache"]), list(antes["vistos"])
            pendentes, erros = [], []
            for url in antes["fontes"]:
                anterior = cache.get(url, {})
                try:
                    docs, ref = consultar(url, anterior)
                    if docs is None:
                        continue
                    pendentes += _mudancas(docs, anterior, ref, vistos, url)
                    cache[url] = ref
                except (requests.RequestException, ValueError, UnicodeError, OSError) as e:
                    erros.append(f"{urlsplit(url).hostname}: {_texto(e, 180)}")
            with _trava:
                dados = _carregar()
                atual = _encontrar(dados, antes["id"])
                if atual and atual["status"] == "ativo" and atual["revisao"] == antes["revisao"]:
                    atual.update({"cache": cache, "vistos": vistos[-500:], "verificado_em": agora,
                                  "proxima_verificacao": agora + (REPETIR_ERRO if erros else INTERVALO),
                                  "erros": erros})
                    # Preserva decisões feitas durante HTTP; não restaura um item já lido.
                    atual["pendentes"] = (atual["pendentes"] + pendentes)[-30:]
                    if forcar:
                        for p in atual["pendentes"]:
                            if p["tentativas"] >= 3:
                                p.update({"tentativas": 0, "analisar_apos": 0})
                    atual["resultado"] = ("Consulta incompleta; vou tentar novamente." if erros else
                                          "Mudanças sem análise validada; confira a fonte ou use Verificar agora." if atual["pendentes"] and all(p["tentativas"] >= 3 for p in atual["pendentes"]) else
                                          "Mudanças encontradas; aguardando análise quando você estiver disponível." if atual["pendentes"] else
                                          "Fontes verificadas; nenhuma mudança nova para analisar.")
                    _salvar(dados)
                _verificando.discard(antes["id"])
            _notificar()
        return True
    finally:
        with _trava:
            _verificando.clear()
        _consulta.release()
        _notificar()


def agendar_verificacao(*, identificador="", forcar=False):
    global _thread
    with _trava:
        if _thread and _thread.is_alive():
            return False
        try:
            itens = _carregar()["itens"]
        except ValueError:
            return False  # O painel mostra o erro; não sobrescreva um cadastro ilegível.
        if not any(i["status"] == "ativo" and (not identificador or i["id"] == identificador)
                   and (forcar or time.time() >= i["proxima_verificacao"]) for i in itens):
            return False
        def consultar_em_fundo():
            try:
                verificar(identificador=identificador, forcar=forcar)
            except (ValueError, OSError):
                _notificar()
        _thread = threading.Thread(target=consultar_em_fundo, daemon=True, name="Luna-Fontes")
        _thread.start()
    return True


def estado_interface():
    with _trava:
        try:
            itens = deepcopy(_carregar()["itens"])
        except ValueError as e:
            return {"itens": [], "erro": str(e)}
        retorno = []
        for i in itens:
            novidades = [n for n in i["novidades"] if not n["lido"]]
            proximo = ("Conferir a novidade e decidir se vale retomar o assunto." if novidades else
                       "Conferir as fontes ou usar Verificar agora para tentar a análise novamente." if i["pendentes"] and all(p["tentativas"] >= 3 for p in i["pendentes"]) else
                       "Analisar as mudanças quando você estiver disponível." if i["pendentes"] else
                       "Aguardar mudanças ligadas ao interesse nas fontes.")
            retorno.append({k: i[k] for k in ("id", "assunto", "interesse", "situacao", "fontes", "status",
                                              "revisao", "resultado", "verificado_em", "proxima_verificacao", "erros")})
            retorno[-1].update({"verificando": i["id"] in _verificando, "proximo_passo": proximo,
                               "novidades": i["novidades"], "pendentes": len(i["pendentes"])})
        return {"itens": retorno, "erro": ""}


def proxima_analise(agora=None):
    agora = time.time() if agora is None else agora
    with _trava:
        for i in _carregar()["itens"]:
            if i["status"] != "ativo" or agora < i["adiado_ate"]:
                continue
            for p in i["pendentes"]:
                if p["tentativas"] < 3 and agora >= p["analisar_apos"]:
                    return {**deepcopy(p), "acompanhamento_id": i["id"], "revisao": i["revisao"],
                            "assunto": i["assunto"], "interesse": i["interesse"], "situacao": i["situacao"]}
    return None


def _item_valido(dados, ref):
    i = _encontrar(dados, ref["acompanhamento_id"])
    return i if i and i["status"] == "ativo" and i["revisao"] == ref["revisao"] else None


def registrar_analise(ref, bruto):
    with _trava:
        dados = _carregar()
        i = _item_valido(dados, ref)
        p = next((p for p in i["pendentes"] if p["id"] == ref["id"]), None) if i else None
        if not p:
            return False
        try:
            match = re.search(r"\{.*\}", bruto or "", re.S)
            d = json.loads(match.group()) if match else {}
            if type(d.get("relevante")) is not bool:
                raise ValueError
            if d["relevante"]:
                evidencia = _texto(d.get("evidencia"), 500)
                resumo = _texto(d.get("resumo"), 300)
                if (len(evidencia) < 12 or evidencia not in _texto(p.get("novo", p["trecho"]), 6000)
                        or not resumo or d.get("etapa") not in {"plano", "anuncio", "mencao"}):
                    raise ValueError
                i["novidades"].append({**p, "evidencia": evidencia, "resumo": resumo, "etapa": d["etapa"],
                                      "avisado_em": 0, "lido": False})
                i["novidades"] = i["novidades"][-20:]
                i["resultado"] = "Encontrei uma mudança ligada ao seu interesse; a fonte está disponível para conferir."
            else:
                i["resultado"] = "As mudanças analisadas não correspondem ao interesse cadastrado."
            i["pendentes"] = [n for n in i["pendentes"] if n["id"] != p["id"]]
        except (ValueError, TypeError, AttributeError):
            p["tentativas"] += 1
            p["analisar_apos"] = time.time() + REPETIR_ERRO
            i["resultado"] = ("Não consegui validar essa mudança em três tentativas. Confira a fonte ou use Verificar agora para tentar de novo."
                              if p["tentativas"] >= 3 else "Não consegui validar a análise da mudança; vou tentar novamente.")
        _salvar(dados)
    _notificar()
    return True


def proxima_novidade(agora=None):
    agora = time.time() if agora is None else agora
    with _trava:
        for i in _carregar()["itens"]:
            if i["status"] != "ativo" or agora < i["adiado_ate"]:
                continue
            for n in i["novidades"]:
                if not n["avisado_em"] and not n["lido"]:
                    return {**deepcopy(n), "acompanhamento_id": i["id"], "revisao": i["revisao"],
                            "assunto": i["assunto"], "interesse": i["interesse"], "situacao": i["situacao"]}
    return None


def ainda_valido(ref):
    with _trava:
        i = _item_valido(_carregar(), ref)
        if not i or time.time() < i["adiado_ate"]:
            return False
        return any(n["id"] == ref["id"] for n in i["pendentes"]) or any(
            n["id"] == ref["id"] and not n["lido"] and not n["avisado_em"] for n in i["novidades"])


def registrar_apresentacao(ref):
    with _trava:
        dados = _carregar()
        i = _item_valido(dados, ref)
        n = next((n for n in i["novidades"] if n["id"] == ref["id"] and not n["lido"]), None) if i else None
        if not n:
            return False
        n["avisado_em"] = time.time()
        _salvar(dados)
    _notificar()
    return True
