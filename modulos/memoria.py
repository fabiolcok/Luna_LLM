# memoria.py
# Memória da Luna em duas camadas:
# 1. ChromaDB — histórico das últimas 30 conversas (busca semântica)
# 2. JSON     — memória permanente que ela mesma escreve

import os
import json
import uuid
import datetime
import chromadb
from dotenv import load_dotenv
import re
import warnings
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
import modelos.cores as cor



os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
warnings.filterwarnings("ignore")

load_dotenv()
# Nome do usuário vem do .env (privacidade — o nome real não fica no código)
NOME_USUARIO = os.getenv("USUARIO_NOME", "Usuário")

# ============================================================
# CONFIGURAÇÃO
# ============================================================
LIMITE_SESSOES      = 30        # máximo de conversas guardadas
RESULTADOS_BUSCA    = 3         # quantas memórias buscar por pergunta
LIMIAR_DISTANCIA    = 1.3       # descarta memórias acima dessa distância (0=idêntico, ~2=sem relação).
                                # Evita que conversas antigas/irrelevantes contaminem o contexto.
CAMINHO_MEMORIA     = "modelos/memoria_permanente.json"
CAMINHO_CHROMADB    = "modelos/chromadb"
MODELO_EMBEDDING    = "all-MiniLM-L6-v2"  # ~80MB, roda na CPU

# ============================================================
# INICIALIZAÇÃO
# ============================================================
_embedding_fn = SentenceTransformerEmbeddingFunction(
    model_name=MODELO_EMBEDDING,
    device="cpu"   # deixa GPU livre para jogos e LLM
)

_cliente_chroma = chromadb.PersistentClient(path=CAMINHO_CHROMADB)
_colecao = _cliente_chroma.get_or_create_collection(
    name="historico_luna",
    embedding_function=_embedding_fn
)

# ============================================================
# MEMÓRIA PERMANENTE (JSON)
# ============================================================

def _carregar_memoria_permanente() -> dict:
    if not os.path.exists(CAMINHO_MEMORIA):
        return {}
    try:
        with open(CAMINHO_MEMORIA, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _salvar_memoria_permanente(dados: dict):
    os.makedirs(os.path.dirname(CAMINHO_MEMORIA), exist_ok=True)
    with open(CAMINHO_MEMORIA, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)


def salvar_fato_importante(chave: str, valor: str):
    """
    Salva um fato importante na memória permanente.
    Chamada pela Luna via ferramenta quando ela decide que algo vale guardar.
    
    Exemplos:
        chave="jogo_favorito", valor="Overwatch"
        chave="pc_gpu", valor="RX 9060 XT 16GB"
        chave="prefere_respostas", valor="curtas e diretas"
    """
    dados = _carregar_memoria_permanente()
    dados[chave] = {
        "valor": valor,
        "salvo_em": datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
    }
    _salvar_memoria_permanente(dados)
    cor.magenta(f"[Memória permanente: '{chave}' = '{valor}']")
    return f"Memorizado: {chave} = {valor}"


def ler_memoria_permanente() -> str:
    """Retorna a memória permanente formatada para injetar no prompt."""
    dados = _carregar_memoria_permanente()
    if not dados:
        return ""
    
    linhas = [f"Fatos que você sabe sobre o {NOME_USUARIO}:"]
    for chave, info in dados.items():
        linhas.append(f"- {chave}: {info['valor']}")
    return "\n".join(linhas)


# ============================================================
# HISTÓRICO DE CONVERSAS (ChromaDB)
# ============================================================

def salvar_conversa(pergunta: str, resposta: str):
    """
    Salva um par pergunta/resposta no ChromaDB.
    Chama após cada resposta da Luna no pensar.py.
    Mantém apenas as últimas LIMITE_SESSOES conversas.
    """
    agora = datetime.datetime.now()
    agora_str = agora.strftime("%d/%m/%Y %H:%M")
    # Usa timestamp como ID para garantir ordem cronológica
    id_conversa = agora.strftime("%Y%m%d%H%M%S") + "_" + str(uuid.uuid4())[:8]
    documento = f"{NOME_USUARIO}: {pergunta}\nLuna: {resposta}"
    
    _colecao.add(
        documents=[documento],
        ids=[id_conversa],
        metadatas=[{"data": agora_str, "timestamp": agora.timestamp()}]
    )

    total = _colecao.count()
    if total > LIMITE_SESSOES:
        excesso = total - LIMITE_SESSOES
        # Pega todos e ordena por timestamp para deletar os mais antigos
        todos = _colecao.get(include=["metadatas"])
        pares = list(zip(todos["ids"], todos["metadatas"]))
        pares.sort(key=lambda x: x[1].get("timestamp", 0))
        ids_deletar = [id_ for id_, _ in pares[:excesso]]
        _colecao.delete(ids=ids_deletar)



def buscar_contexto_relevante(pergunta: str) -> str:
    """
    Busca conversas anteriores relevantes para a pergunta atual.
    Retorna string formatada para injetar no prompt.
    """
    total = _colecao.count()
    if total == 0:
        return ""

    try:
        resultados = _colecao.query(
            query_texts=[pergunta],
            n_results=min(RESULTADOS_BUSCA, total),
            include=["documents", "metadatas", "distances"],
        )

        documentos = resultados.get("documents", [[]])[0]
        metadatas  = resultados.get("metadatas",  [[]])[0]
        distancias = resultados.get("distances",  [[]])[0]

        if not documentos:
            return ""

        linhas = ["Conversas anteriores relevantes:"]
        for doc, meta, dist in zip(documentos, metadatas, distancias):
            if dist is not None and dist > LIMIAR_DISTANCIA:
                continue  # memória pouco relacionada — não injeta no contexto
            linhas.append(f"[{meta.get('data', '')}]\n{doc}")

        if len(linhas) == 1:   # nenhuma passou no limiar
            return ""
        return "\n\n".join(linhas)

    except Exception as e:
        cor.vermelho(f"[Memória: erro na busca — {e}]")
        return ""


# ============================================================
# ANÁLISE DE IMPORTÂNCIA (chamada após cada resposta)
# ============================================================

def analisar_e_salvar_fato(pergunta, resposta, gerar_resposta_fn):
    
    # A TRAVA DE SEGURANÇA
    if not pergunta or str(pergunta).strip() == "":
        return
    
    # 1. Carrega o que a Luna já sabe para comparar
    memoria_atual = ler_memoria_permanente() 
    
    # O parêntese abaixo é fundamental para o Python aceitar várias linhas de texto
    prompt = (
        "Você é um classificador lógico de memória estrito. Sua ÚNICA tarefa é extrair fatos NOVOS declarados na mensagem do usuário.\n\n"
        f"[FATOS JÁ CONHECIDOS - PROIBIDO EXTRAIR NOVAMENTE]:\n{memoria_atual}\n\n"
        f"[MENSAGEM DO USUÁRIO PARA ANALISAR]:\n{NOME_USUARIO}: {pergunta}\n\n"
        "REGRAS ABSOLUTAS:\n"
        "1. IGNORAR COMANDOS: Se a mensagem for um pedido ('toque música', 'pesquise', 'bom dia', 'abra o navegador'), retorne {\"salvar\": false}.\n"
        "2. IGNORAR FATOS CONHECIDOS: Se o assunto da mensagem já consta na lista de FATOS JÁ CONHECIDOS, retorne {\"salvar\": false}.\n"
        "3. SALVAR APENAS O NOVO: Se o usuário declarar explicitamente uma informação estrutural INÉDITA sobre seu hardware, trabalho, gostos ou vida pessoal, retorne um fato estruturado.\n\n"
        "FORMATO DE SAÍDA OBRIGATÓRIO (Escolha apenas UMA opção e não escreva mais nada):\n"
        'Opção A (Nada novo): {"salvar": false}\n'
        'Opção B (Fato novo): {"salvar": true, "chave": "categoria_da_informacao", "valor": "informacao resumida sobre o usuario"}\n'
    )
    
    try:
        # Chamada usando o modo_memoria=True que configuramos no pensar.py
        resposta_llm = gerar_resposta_fn(prompt, [], analisar=False, salvar=False, modo_memoria=True)
        
        import re
        match = re.search(r'\{.*?\}', resposta_llm, re.DOTALL)
        if not match:
            return
            
        dados = json.loads(match.group())

        if dados.get("salvar") and dados.get("chave") and dados.get("valor"):
            salvar_fato_importante(dados["chave"], dados["valor"])

    except Exception as e:
        cor.vermelho(f"[Memória: erro na análise — {e}]")

# ============================================================
# MEMÓRIA EPISÓDICA — leitura de conversas novas + fila de pendentes
# ============================================================
# A memória CONFIRMADA vive no Obsidian (Luna/Memoria.md). Aqui fica só a mecânica:
# ler conversas novas do ChromaDB (pra extrair) e a FILA de candidatos aguardando
# a confirmação do usuário no web (mais o lixo e o "não re-propor recusados").

def conversas_desde(marcador_ts: float, limite: int = 40) -> list:
    """Pares de conversa gravados APÓS marcador_ts, do mais antigo pro mais novo.
    Retorna [(timestamp, documento)]. Vazio se não houver novas."""
    try:
        if _colecao.count() == 0:
            return []
        todos = _colecao.get(include=["documents", "metadatas"])
        pares = []
        for doc, meta in zip(todos.get("documents", []), todos.get("metadatas", [])):
            ts = (meta or {}).get("timestamp", 0)
            if ts and ts > marcador_ts:
                pares.append((ts, doc))
        pares.sort(key=lambda x: x[0])
        return pares[-limite:]
    except Exception as e:
        cor.vermelho(f"[Memória: erro ao ler conversas novas — {e}]")
        return []


CAMINHO_MEM_PENDENTE = "modelos/memoria_pendente.json"
_MEM_LIXO_DIAS = 7   # quantos dias uma lembrança descartada fica recuperável

def _mem_norm(txt: str) -> str:
    # normaliza pra dedup: minúsculas + colapsa espaços (basta pra comparar fatos repetidos)
    return " ".join(txt.lower().split()) if txt else ""

def carregar_mem_pendente() -> dict:
    base = {"marcador_ts": 0.0, "pendentes": [], "lixo": [], "recusados": []}
    try:
        with open(CAMINHO_MEM_PENDENTE, encoding="utf-8") as f:
            base.update(json.load(f))
    except Exception:
        pass
    return base

def salvar_mem_pendente(d: dict):
    os.makedirs("modelos", exist_ok=True)
    with open(CAMINHO_MEM_PENDENTE, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=2)

def mem_marcador() -> float:
    return carregar_mem_pendente().get("marcador_ts", 0.0)

def mem_set_marcador(ts: float):
    d = carregar_mem_pendente()
    d["marcador_ts"] = max(ts, d.get("marcador_ts", 0.0))
    salvar_mem_pendente(d)

def mem_adicionar_candidatos(fatos: list) -> int:
    """Adiciona fatos à fila de pendentes, ignorando repetidos (já na fila ou já
    recusados antes). Retorna quantos entraram de fato."""
    d = carregar_mem_pendente()
    ja = {_mem_norm(p["fato"]) for p in d["pendentes"]} | {_mem_norm(r) for r in d["recusados"]}
    novos = 0
    for fato in fatos:
        fato = (fato or "").strip()
        n = _mem_norm(fato)
        if not n or n in ja:
            continue
        d["pendentes"].append({
            "id": datetime.datetime.now().strftime("%Y%m%d%H%M%S") + "_" + str(uuid.uuid4())[:6],
            "fato": fato,
            "data": datetime.datetime.now().strftime("%Y-%m-%d"),
        })
        ja.add(n)
        novos += 1
    if novos:
        salvar_mem_pendente(d)
    return novos

def mem_listar_pendentes() -> list:
    return carregar_mem_pendente()["pendentes"]

def mem_listar_lixo() -> list:
    return carregar_mem_pendente()["lixo"]

def mem_confirmar(id_: str, texto_editado: str = None) -> bool:
    """Confirma um pendente: grava no Obsidian (Luna/Memoria.md) e tira da fila.
    texto_editado permite o usuário corrigir a frase antes de salvar."""
    from modulos import obsidian
    d = carregar_mem_pendente()
    item = next((p for p in d["pendentes"] if p["id"] == id_), None)
    if not item:
        return False
    fato = (texto_editado or item["fato"]).strip()
    if not obsidian.adicionar_memoria(fato, item.get("data")):
        return False
    d["pendentes"] = [p for p in d["pendentes"] if p["id"] != id_]
    salvar_mem_pendente(d)
    return True

def mem_descartar(id_: str) -> bool:
    """Manda um pendente pro lixo (recuperável _MEM_LIXO_DIAS dias) e registra pra
    não propor de novo o mesmo fato."""
    d = carregar_mem_pendente()
    item = next((p for p in d["pendentes"] if p["id"] == id_), None)
    if not item:
        return False
    item["descartado_em"] = datetime.datetime.now().timestamp()
    d["lixo"].append(item)
    d["recusados"].append(item["fato"])
    d["pendentes"] = [p for p in d["pendentes"] if p["id"] != id_]
    salvar_mem_pendente(d)
    return True

def mem_restaurar(id_: str) -> bool:
    """Tira do lixo e devolve pra fila de pendentes (desfaz um descarte)."""
    d = carregar_mem_pendente()
    item = next((p for p in d["lixo"] if p["id"] == id_), None)
    if not item:
        return False
    d["recusados"] = [r for r in d["recusados"] if _mem_norm(r) != _mem_norm(item["fato"])]
    item.pop("descartado_em", None)
    d["lixo"] = [p for p in d["lixo"] if p["id"] != id_]
    d["pendentes"].append(item)
    salvar_mem_pendente(d)
    return True

def mem_limpar_lixo():
    """Remove do lixo o que passou de _MEM_LIXO_DIAS dias (chamado de vez em quando)."""
    d = carregar_mem_pendente()
    limite = datetime.datetime.now().timestamp() - _MEM_LIXO_DIAS * 86400
    antes = len(d["lixo"])
    d["lixo"] = [p for p in d["lixo"] if p.get("descartado_em", 0) >= limite]
    if len(d["lixo"]) != antes:
        salvar_mem_pendente(d)


CAMINHO_VISTOS = "modelos/vistos.json"

def carregar_vistos() -> dict:
    if not os.path.exists(CAMINHO_VISTOS):
        return {"steam": {}, "overwatch": []}
    try:
        with open(CAMINHO_VISTOS, "r") as f:
            return json.load(f)
    except:
        return {"steam": {}, "overwatch": []}

def salvar_vistos(dados: dict):
    os.makedirs("modelos", exist_ok=True)
    # 'radar' é o único que cresce muito (1 entrada por notícia vista). Escrevemos ele
    # por ÚLTIMO pra manter as entradas pequenas e legíveis (steam, animes, e o que for
    # entrando com o tempo) no TOPO do arquivo — fácil de achar e editar/limpar na mão.
    ordenado = {k: v for k, v in dados.items() if k != "radar"}
    if "radar" in dados:
        ordenado["radar"] = dados["radar"]
    with open(CAMINHO_VISTOS, "w") as f:
        json.dump(ordenado, f, ensure_ascii=False, indent=2)


# ============================================================
# ESTADO SITUACIONAL DA LUNA (JSON)
# ============================================================
CAMINHO_ESTADO_LUNA = "modelos/estado_luna.json"

def ler_estado_luna() -> dict:
    if not os.path.exists(CAMINHO_ESTADO_LUNA):
        return {}
    try:
        with open(CAMINHO_ESTADO_LUNA, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def atualizar_estado_luna(chave: str, valor):
    estado = ler_estado_luna()
    estado[chave] = valor
    estado["ultima_atualizacao"] = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
    os.makedirs("modelos", exist_ok=True)
    with open(CAMINHO_ESTADO_LUNA, "w", encoding="utf-8") as f:
        json.dump(estado, f, ensure_ascii=False, indent=2)