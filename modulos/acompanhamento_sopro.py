"""Piloto local: acompanhar mudanças oficiais do Sopro relacionadas a PT-BR.

As fontes são fixas. A coleta não chama LLM, não baixa modelos e não transforma
uma menção a PT-BR em prova de qualidade ou suporte. A voz só entra na entrega.
"""
from copy import deepcopy
from pathlib import Path
import hashlib
import json
import re
import sys
import threading
import time
import unicodedata

import requests

CAMINHO = Path("modelos/acompanhamento_sopro.json")
INTERVALO = 6 * 3600
REPETIR_ERRO = 30 * 60
ADIAMENTO = 2 * 3600
MAX_BYTES = 400_000
FONTES = (
    {"id": "github_readme", "nome": "GitHub · documentação",
     "consulta": "https://raw.githubusercontent.com/samuel-vitorino/sopro/main/README.md",
     "url": "https://github.com/samuel-vitorino/sopro", "tipo": "texto"},
    {"id": "github_releases", "nome": "GitHub · releases",
     "consulta": "https://api.github.com/repos/samuel-vitorino/sopro/releases?per_page=10",
     "url": "https://github.com/samuel-vitorino/sopro/releases", "tipo": "releases"},
    {"id": "hf_card", "nome": "Hugging Face · modelo",
     "consulta": "https://huggingface.co/samuel-vitorino/sopro-v2-turbo/raw/main/README.md",
     "url": "https://huggingface.co/samuel-vitorino/sopro-v2-turbo", "tipo": "texto"},
)
_trava = threading.RLock()
_consulta = threading.Lock()
_thread = None


def _norm(texto):
    texto = unicodedata.normalize("NFKD", str(texto or ""))
    return "".join(c for c in texto if not unicodedata.combining(c)).lower()


def _base():
    return {"versao": 1, "status": "ativo", "revisao": 0,
            "situacao": "Gostou da voz e da respiração; o sotaque PT-PT incomodou.",
            "verificado_em": 0, "proxima_verificacao": 0, "adiado_ate": 0,
            "resultado": "Aguardando a primeira consulta às fontes.",
            "erros": [], "fontes": {}, "vistos": [], "novidades": []}


def _carregar():
    if not CAMINHO.exists():
        return _base()
    try:
        dados = json.loads(CAMINHO.read_text(encoding="utf-8"))
        if not isinstance(dados, dict) or dados.get("status") not in {"ativo", "pausado", "encerrado"}:
            raise ValueError("Estado inválido")
        return {**_base(), **dados}
    except (OSError, ValueError):
        # Perder a referência não autoriza despejar o histórico como se fosse novo.
        return {**_base(), "status": "pausado",
                "resultado": "Não consegui ler o estado salvo. Retome o piloto para criar uma referência nova."}


def _salvar(dados):
    CAMINHO.parent.mkdir(parents=True, exist_ok=True)
    temporario = CAMINHO.with_suffix(".tmp")
    temporario.write_text(json.dumps(dados, ensure_ascii=False, indent=2), encoding="utf-8")
    temporario.replace(CAMINHO)


def _notificar():
    # A bancada importa só este módulo: não deve carregar voz, servidor ou LLM.
    servidor = sys.modules.get("servidor")
    if servidor and hasattr(servidor, "notificar_acompanhamentos"):
        servidor.notificar_acompanhamentos()


def mencoes_ptbr(texto):
    """Só trechos pertinentes; versão, idioma 'pt' e PT-PT sozinhos não bastam."""
    padrao = r"\b(?:pt[-_ ]br|brazilian portuguese|portugues brasileiro|portuguese\s*\(brazil\)|brazilian accent)(?!\w)"
    resultado = []
    for linha in str(texto or "").splitlines():
        normal = _norm(linha)
        if not re.search(padrao, normal):
            continue
        # Um aviso explícito de ausência de suporte não é um convite para retestar.
        if re.search(r"not (?:currently |yet )?(?:support(?:ed)?|available)|unsupported|no (?:.{0,25} )?support|nao .{0,25}suport|sem suporte", normal):
            continue
        limpo = re.sub(r"\s+", " ", linha).strip()
        achou = re.search(padrao, _norm(limpo))
        inicio = max(0, achou.start() - 160)
        trecho = limpo[inicio:inicio + 600]
        identificador = hashlib.sha256(_norm(trecho).encode()).hexdigest()[:20]
        if not any(i["id"] == identificador for i in resultado):
            tipo = ("plano" if re.search(r"roadmap|planned|planning|future release|coming soon|planejad|previst|em breve", _norm(trecho))
                    else "anuncio" if re.search(r"\b(?:added|released|available|now supports|adicionado|disponivel|lancado)\b", _norm(trecho))
                    else "mencao")
            resultado.append({"id": identificador, "trecho": trecho, "tipo": tipo})
    return resultado


def consultar_fonte(fonte, anterior):
    cabecalhos = {"User-Agent": "Luna-LLM-Sopro-pilot", "Accept": "application/json" if
                  fonte["tipo"] == "releases" else "text/plain"}
    if anterior.get("etag"):
        cabecalhos["If-None-Match"] = anterior["etag"]
    if anterior.get("modified"):
        cabecalhos["If-Modified-Since"] = anterior["modified"]
    with requests.get(fonte["consulta"], headers=cabecalhos, timeout=(3, 8),
                      stream=True, allow_redirects=False) as resposta:
        if resposta.status_code == 304:
            if not anterior.get("semeada"):
                raise ValueError("Fonte sem referência para resposta 304")
            return None, anterior
        resposta.raise_for_status()
        if resposta.status_code != 200:
            raise ValueError(f"Resposta HTTP inesperada: {resposta.status_code}")
        partes, tamanho = [], 0
        for parte in resposta.iter_content(16384):
            tamanho += len(parte)
            if tamanho > MAX_BYTES:
                raise ValueError("Resposta maior que o limite do piloto")
            partes.append(parte)
        texto = b"".join(partes).decode("utf-8")
        cache = {"etag": resposta.headers.get("ETag", ""),
                 "modified": resposta.headers.get("Last-Modified", ""), "semeada": True}
    if fonte["tipo"] == "texto":
        return [{"texto": texto, "url": fonte["url"]}], cache
    releases = json.loads(texto)
    if not isinstance(releases, list):
        raise ValueError("Formato inválido de releases")
    documentos = []
    for item in releases[:10]:
        if not isinstance(item, dict) or item.get("draft"):
            continue
        url = str(item.get("html_url") or "")
        if not url.startswith("https://github.com/samuel-vitorino/sopro/releases/tag/"):
            url = fonte["url"]
        documentos.append({"texto": str(item.get("body") or ""), "url": url})
    return documentos, cache


def verificar(*, forcar=False, agora=None, consultar=None):
    """Consulta fora da trava de estado; uma pausa durante a rede invalida o resultado."""
    agora = time.time() if agora is None else agora
    consultar = consultar or consultar_fonte
    if not _consulta.acquire(blocking=False):
        return False
    try:
        with _trava:
            antes = deepcopy(_carregar())
            if antes["status"] != "ativo" or (not forcar and agora < antes["proxima_verificacao"]):
                return False
        _notificar()
        fontes, vistos = deepcopy(antes["fontes"]), list(antes["vistos"])
        novidades, erros = [], []
        for fonte in FONTES:
            cache_anterior = fontes.get(fonte["id"], {})
            try:
                documentos, cache = consultar(fonte, cache_anterior)
                if documentos is None:
                    continue
                semeada = cache_anterior.get("semeada", False)
                for documento in documentos:
                    for mencao in mencoes_ptbr(documento["texto"]):
                        if mencao["id"] in vistos:
                            continue
                        vistos.append(mencao["id"])
                        if semeada:
                            novidades.append({**mencao, "fonte": fonte["nome"],
                                              "url": documento["url"], "detectado_em": agora,
                                              "avisado_em": 0, "lido": False})
                fontes[fonte["id"]] = {**cache, "semeada": True}
            except (requests.RequestException, ValueError, UnicodeError) as erro:
                erros.append(f'{fonte["nome"]}: {str(erro)[:180]}')
        with _trava:
            atual = _carregar()
            if atual["revisao"] != antes["revisao"] or atual["status"] != "ativo":
                return False
            atual.update({"fontes": fontes, "vistos": vistos[-300:], "verificado_em": agora,
                          "proxima_verificacao": agora + (REPETIR_ERRO if erros else INTERVALO),
                          "erros": erros})
            atual["novidades"] = (atual["novidades"] + novidades)[-20:]
            if novidades:
                atual["resultado"] = "Encontrei uma menção nova a PT-BR. Falta validar o alcance e ouvir a voz."
            elif erros:
                atual["resultado"] = "Consulta incompleta. Vou tentar novamente; isto não confirma ausência de novidades."
            elif any(not n["lido"] for n in atual["novidades"]):
                atual["resultado"] = "Nenhuma menção adicional. A anterior segue disponível; falta validar o alcance e ouvir a voz."
            else:
                atual["resultado"] = "Fontes verificadas; nenhuma menção nova a PT-BR."
            _salvar(atual)
        return True
    finally:
        _consulta.release()
        _notificar()


def agendar_verificacao(*, forcar=False):
    """Uma thread curta de HTTP, sem reservar o turno da conversa."""
    global _thread
    with _trava:
        estado = _carregar()
        if estado["status"] != "ativo" or (_thread and _thread.is_alive()):
            return False
        if not forcar and time.time() < estado["proxima_verificacao"]:
            return False
        _thread = threading.Thread(target=verificar, kwargs={"forcar": forcar}, daemon=True,
                                   name="Luna-Sopro-fontes")
        _thread.start()
    return True


def estado_interface():
    with _trava:
        estado = _carregar()
        pendente = any(not n["lido"] for n in estado["novidades"])
        proximo = ("Revisar a menção encontrada e comparar a voz com Kokoro quando quiser." if pendente
                   else "Aguardar uma menção nova a PT-BR nas fontes; depois comparar com Kokoro.")
        return {"id": "sopro_ptbr", "titulo": "Sopro · português brasileiro",
                "status": estado["status"], "situacao": estado["situacao"],
                "proximo_passo": proximo, "tem_novidade": pendente,
                "verificado_em": estado["verificado_em"],
                "proxima_verificacao": estado["proxima_verificacao"],
                "adiado_ate": estado["adiado_ate"], "resultado": estado["resultado"],
                "erros": estado["erros"], "verificando": _consulta.locked(),
                "fontes": [{"nome": f["nome"], "url": f["url"]} for f in FONTES],
                "novidades": deepcopy(estado["novidades"][-5:])}


def proxima_novidade(agora=None):
    agora = time.time() if agora is None else agora
    with _trava:
        estado = _carregar()
        if estado["status"] != "ativo" or agora < estado["adiado_ate"]:
            return None
        return next((deepcopy(n) for n in estado["novidades"]
                     if not n["avisado_em"] and not n["lido"]), None)


def ainda_valida(identificador):
    item = proxima_novidade()
    return item is not None and item["id"] == identificador


def registrar_apresentacao(identificador):
    # Publicação da legenda já conta: cortar a voz não deve repetir o convite.
    with _trava:
        estado = _carregar()
        item = next((n for n in estado["novidades"] if n["id"] == identificador), None)
        if not item:
            return False
        item["avisado_em"] = time.time()
        _salvar(estado)
    _notificar()
    return True


def agir(acao, *, identificador="", situacao=""):
    if acao == "verificar":
        return ("Consultando as fontes; o resultado aparecerá no painel." if
                agendar_verificacao(forcar=True) else "Consulta em andamento ou acompanhamento pausado.")
    with _trava:
        estado = _carregar()
        if acao == "pausar":
            estado["status"] = "pausado"
            resposta = "Acompanhamento do Sopro pausado."
        elif acao == "retomar":
            estado["status"] = "ativo"
            estado["proxima_verificacao"] = 0
            resposta = "Vou acompanhar as novidades do Sopro sobre PT-BR."
        elif acao == "encerrar":
            estado["status"] = "encerrado"
            resposta = "Acompanhamento do Sopro encerrado."
        elif acao == "corrigir":
            texto = str(situacao or "").strip()[:300]
            if not texto:
                return "Escreva onde o teste do Sopro parou."
            estado["situacao"] = texto
            resposta = "Situação do teste atualizada."
        elif acao in {"adiar", "visto"}:
            item = next((n for n in estado["novidades"] if n["id"] == identificador), None)
            if not item:
                return "Essa novidade não está mais disponível."
            if acao == "adiar":
                estado["adiado_ate"] = time.time() + ADIAMENTO
                item["avisado_em"] = 0
                resposta = "Deixo esse convite para daqui a duas horas."
            else:
                item["lido"] = True
                resposta = "Novidade marcada como vista."
        else:
            return "Ação desconhecida."
        estado["revisao"] += 1
        _salvar(estado)
    _notificar()
    return resposta


def interceptar_pedido(texto):
    """Só pedidos explícitos com o nome Sopro; 'mais tarde' solto pertence à conversa."""
    normal = _norm(texto).strip(" .!?")
    if not re.search(r"\bsopro\b", normal):
        return None
    if re.search(r"\b(?:nao|nem) (?:quero |precisa |preciso )?(?:acompanhar|acompanha|acompanhe|monitorar|monitora|monitore|verificar)\b", normal):
        return agir("encerrar")
    if re.search(r"\b(?:encerra|encerre|cancela|cancele|esquece|esqueca)\b|perdi o interesse", normal):
        return agir("encerrar")
    if re.search(r"\b(?:pausa|pause)\b", normal):
        return agir("pausar")
    if re.search(r"\b(?:verifica|verifique|confere|confira|consulta|consulte)\b", normal):
        return agir("verificar")
    if re.search(r"mais tarde|outra hora", normal):
        itens = [n for n in estado_interface()["novidades"] if not n["lido"]]
        if itens:
            return agir("adiar", identificador=itens[-1]["id"])
    if re.search(r"\b(?:acompanha|acompanhe|monitora|monitore|retoma|retome)\b|me avis[ae]\b|"
                 r"\b(?:pode|quero|preciso|gostaria de) (?:acompanhar|monitorar)\b", normal):
        return agir("retomar")
    return None
