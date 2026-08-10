# 🛠️ Instalação da Luna — do zero ao "oi"

Guia passo a passo pra ligar a Luna numa máquina nova. Se você só quer entender
*como ela funciona por dentro*, o [`README.md`](README.MD) é o mapa da arquitetura.

> **Filosofia deste guia:** a Luna liga com **pouca coisa** (o cérebro local + o teu nome).
> Todo o resto — Spotify, Steam, Telegram, promoções… — é **opcional** e você liga uma
> feature de cada vez. Não precisa das 18 chaves pra começar.

---

## 1. Pré-requisitos

| O quê | Por quê | Onde |
|-------|---------|------|
| **Python 3.12** | roda a Luna | [python.org](https://www.python.org/downloads/) — marque *Add to PATH* |
| **Node.js + npm** | instala o TurboLLM (o servidor do LLM) | [nodejs.org](https://nodejs.org/) (LTS) |
| **Git** | clonar o projeto | [git-scm.com](https://git-scm.com/) |
| **Uma GPU** | acelera o LLM | AMD (ROCm) ou NVIDIA (CUDA). Sem GPU roda, mas lento. |

> 💡 O projeto foi feito e testado no **Windows 11** com **AMD RX 9060 XT (ROCm)**. Em
> NVIDIA você usa o engine **CUDA** no TurboLLM (mesma ideia, veja o passo 3). Em Linux/Mac
> os comandos mudam um pouco, mas a lógica é a mesma.

---

## 2. Base do projeto

```bash
git clone https://github.com/fabiolcok/Luna_LLM.git
cd Luna_LLM

python -m venv venv
venv\Scripts\activate            # Windows  (Linux/Mac: source venv/bin/activate)

pip install -r requirements.txt
```

> A 1ª execução ainda baixa sozinha alguns modelos leves de CPU (Whisper `small`, Kokoro TTS,
> e os embeddings de memória) — some MB, automático, só uma vez.

---

## 3. O cérebro: TurboLLM + Gemma-4-12B  ⭐ (a parte que mais importa)

A Luna **pensa** com um LLM local, servido pelo **TurboLLM** (uma camada OpenAI-compatível
em cima do llama.cpp). São 3 sub-passos:

### 3.1 Instale o TurboLLM

Siga o projeto oficial: **https://github.com/mohitsoni48/TurboLLM**

```bash
npm install -g turbollm
turbollm
```

O `turbollm` abre um **painel local** no navegador, onde você cadastra os modelos.

### 3.2 Baixe os modelos (Hugging Face)

| Modelo | Pra quê | Onde |
|--------|---------|------|
| **Gemma-4-12B QAT** — pegue a variante **Q4_0** | o cérebro (obrigatório) | [unsloth/gemma-4-12B-it-qat-GGUF](https://huggingface.co/unsloth/gemma-4-12B-it-qat-GGUF/tree/main) |
| **MTP drafter** *(opcional, dá velocidade)* | *speculative decoding* | `mtp-gemma-4-12B-it-Q8_0.gguf` (pasta `MTP/` dos GGUF da unsloth) |

Baixe os `.gguf` e salve numa pasta sua (ex.: `G:\Projetos\Modelos\...`).

> 💡 **Por que o 12B?** É o modelo que o código já espera (`MODELO_PERSONA` em `pensar.py`) e o
> mais leve que roda em mais gente. Dá pra usar um modelo maior (ex.: um 26B-A4B MoE), mas aí
> você troca o nome em `pensar.py` **e** precisa do drafter MTP **daquele** modelo — o MTP é
> casado com o modelo (o do 12B não serve pro 26B).

### 3.3 Cadastre o Gemma no TurboLLM

No painel do TurboLLM, adicione um modelo apontando pro `.gguf` do Gemma, com **atenção a 3 detalhes que quebram tudo se errar**:

- 🏷️ **Nome do modelo:** se a sua versão do TurboLLM deixar batizar, use **`gemma 4 12b it qat`**
  — com espaços. É o formato que o gateway JIT casa pra auto-carregar (com hífens dá **503**).
  **Não tem campo de nome?** Tudo bem: a Luna **descobre sozinha** qual id o servidor expõe.
  Só carregue o modelo na tela *Models* antes de abrir ela na primeira vez. Se mesmo assim
  reclamar, o log lista os ids disponíveis — copie o certo pra `MODELO_LLM=` no `.env`.
- 🔌 **Porta do gateway:** **6996** (é onde a Luna procura o LLM — veja `BASE_LOCAL` em
  `pensar.py`). O endpoint fica em `http://127.0.0.1:6996/v1`.
- ⚙️ **Engine:** llama.cpp **ROCm** (AMD) ou **CUDA** (NVIDIA). Vulkan é lento em AMD, evite.

> 💡 *Opcional — economizar VRAM:* mude o **KV cache** de `f16` pra **`q8_0`** nas opções do
> modelo (economiza ~700MB, quase sem perda). O "thinking" do Gemma **não** precisa de config
> aqui — a Luna já manda `enable_thinking:false` em toda chamada.

> ⚠️ **GPU de 12GB ou menos** (ex.: RTX 3060 12GB): aí a conta fica apertada — o Gemma Q4_0
> pesa ~7GB, o KV cache ~2GB, o drafter ~1GB, e o Windows come ~1GB. Duas recomendações que
> deixam de ser opcionais:
> - **KV cache em `q8_0`** (o item acima) — faça já, não depois.
> - **Suba primeiro SEM o drafter MTP** (passo 3.4). Confirme que ela conversa e só então
>   ligue o drafter. Assim, se faltar memória, você sabe exatamente o que causou.
>
> O resto do projeto **não disputa a GPU**: o Whisper e os embeddings de memória rodam em CPU
> de propósito (`device="cpu"` em `ouvir.py` e `memoria.py`), então a placa fica só pro LLM.

### 3.4 (Opcional) Ligar o drafter MTP — mais velocidade

O MTP (*speculative decoding*) acelera bastante a geração. No painel do TurboLLM, **no modelo
de 12B** (NÃO no arquivo MTP), campo **"Extra command-line flags"**, cole **um por linha**
(dando **Enter** entre cada — se colar tudo numa linha só, dá *"invalid argument"*):

```
--model-draft
G:\Projetos\Modelos\lmstudio-community\MTP\mtp-gemma-4-12B-it-Q8_0.gguf
--spec-type
draft-mtp
--spec-draft-n-max
4
```

*(Troque o caminho do `--model-draft` pelo lugar onde você salvou o `.gguf` do MTP.)*

> ✅ **Teste rápido:** com o `turbollm` rodando e o Gemma cadastrado, o chat do próprio
> painel do TurboLLM já deve responder. Se responder lá, a Luna vai conversar.

---

## 4. O mínimo pra ligar

```bash
copy .env.example .env           # Linux/Mac: cp .env.example .env
```

Abra o `.env` e preencha **só isto** pra começar:

```
USUARIO_NOME=SeuNome
```

Pronto — com o **TurboLLM rodando** + esse nome, a Luna já liga:

```bash
python main.py
```

- Segure **`Ctrl+Alt+F8`** pra falar (push-to-talk), solte pra enviar.
- Interface web em `http://localhost:5000` (abre sozinha como janela).
- A 1ª resposta depois de ociosa demora **~6s** (o TurboLLM carrega o modelo sob demanda).

> Também dá pra abrir pelos atalhos em `Atalhos/` (`Luna.bat` = com terminal, bom pra debug;
> `Luna.vbs` = sem janela). Eles descobrem a pasta do projeto sozinhos e avisam se o `venv`
> não existir — não precisa editar caminho nenhum.

---

## 5. Features opcionais (ligue as que quiser)

Cada uma é uma (ou duas) chave no `.env`. **Sem a chave, a feature só fica desligada** — nada
quebra. Todas as chaves e dicas também estão no `.env.example`.

| Feature | Chave(s) no `.env` | Onde pegar |
|---------|--------------------|------------|
| 👁️ **Ver tela / analisar imagem** | `GEMINI_API_KEY` | [aistudio.google.com](https://aistudio.google.com/app/apikey) |
| 🎨 **Gerar imagem** (FLUX) | `HF_TOKEN` | [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens) — permissão *"Make calls to Inference Providers"* |
| 🎞️ **GIFs na interface** | `GIPHY_API_KEY` | [developers.giphy.com](https://developers.giphy.com/) |
| 🎵 **Spotify** | `SPOTIPY_CLIENT_ID` / `SPOTIPY_CLIENT_SECRET` / `SPOTIPY_REDIRECT_URI` | [developer.spotify.com/dashboard](https://developer.spotify.com/dashboard) |
| 📧 **E-mail (Gmail)** | `EMAIL_USUARIO` / `EMAIL_SENHA` | senha de app de 16 letras ([myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)) |
| 📅 **Google Agenda** | *(OAuth — veja abaixo)* | `credentials.json` no Google Cloud Console |
| 🎮 **Overwatch** | `OW_BATTLETAG` | seu BattleTag (`Nome-1234`) |
| 🕹️ **Steam** (wishlist + jogos) | `STEAM_API_KEY` / `STEAM_ID` | [steamcommunity.com/dev/apikey](https://steamcommunity.com/dev/apikey) |
| 💬 **Bot do Telegram** | `TELEGRAM_TOKEN` / `TELEGRAM_CHAT_ID` | token no [@BotFather](https://t.me/BotFather); chat id no [@userinfobot](https://t.me/userinfobot) |
| 📓 **Obsidian** | `OBSIDIAN_VAULT` | caminho do seu vault (a Luna cria as notas que faltam) |
| ☁️ **Clima** | `CLIMA_LAT` / `CLIMA_LON` | sua lat/long em [latlong.net](https://www.latlong.net/) |
| 🌐 **Controle do Firefox** (resumir/comentar aba) | *(extensão — veja abaixo)* | já incluída em `modelos/Extensao_Luna/` |
| 🏷️ **Radar de promoções** | `TELEGRAM_API_ID` / `TELEGRAM_API_HASH` | veja a seção 6 |

**Google Agenda (OAuth2):** ative a *Google Calendar API* no [Google Cloud Console](https://console.cloud.google.com/),
crie uma credencial *OAuth Desktop*, baixe o `credentials.json` e coloque em `modelos/`. Na 1ª
vez a Luna abre o navegador pra você autorizar (gera `modelos/token.json`).

**Controle do Firefox (extensão):** as ferramentas `controlar_navegador` e `analisar_aba_atual`
(resumir/comentar a aba aberta) usam uma extensão que **já vem no repo**, em
`modelos/Extensao_Luna/`. Pra instalar no Firefox:

1. Abra `about:debugging` → **Este Firefox** → **Carregar extensão temporária…**
2. Escolha o **`manifest.json`** dentro de `modelos/Extensao_Luna/`.

Ela conecta na Luna por WebSocket (`127.0.0.1:8765`) — quando ligar, aparece
`[🌐 Firefox conectado à Luna]` no log.

> ⚠️ Extensão *temporária* sai quando você fecha o Firefox — recarregue por `about:debugging`
> na próxima sessão (ou instale de forma permanente numa versão *Developer/Nightly* do Firefox).

---

## 6. Radar de promoções (Telegram) — setup especial

Esta feature lê **canais de promoção** do Telegram como se fosse você (via Telethon) e te
avisa quando cai uma oferta do que você quer. Precisa de um **login único**:

1. **Chaves de cliente:** em [my.telegram.org](https://my.telegram.org/) → *API development
   tools* → crie um app → copie o **`api_id`** e o **`api_hash`** pro `.env`:
   ```
   TELEGRAM_API_ID=12345678
   TELEGRAM_API_HASH=abc123...
   ```
2. **Login único** (gera a sessão salva):
   ```bash
   venv\Scripts\python setup_telegram_promo.py
   ```
   Ele pede seu telefone (`+55…`) e o código que chega no Telegram. Cria
   `modelos/luna_promo.session` (é credencial da sua conta — **já está no `.gitignore`**).
3. **Configure o que caçar** (no Obsidian): a nota `Luna/RastrearPromocoes.md` é criada
   sozinha. Nela, liste em bullets os **@ dos canais** (que você já entrou) e as
   **palavras-chave** dos produtos. Os achados aparecem em `Promocoes.md`.

> ⚠️ A sessão do Telethon aceita **um processo por vez**: se a Luna está rodando e você tenta
> rodar o `setup`/um teste à parte, dá `database is locked` — feche a Luna primeiro.

---

## 7. Problemas comuns

| Sintoma | Causa provável |
|---------|----------------|
| Luna diz que o LLM está fora do ar | o **TurboLLM não está rodando** — rode `turbollm` |
| TurboLLM dá **503** ao carregar o modelo | nome do modelo com **hífen** — use `gemma 4 12b it qat` (espaços) |
| Flags do drafter dão *"invalid argument"* | flags **coladas numa linha** — uma por linha (Enter) |
| 1ª resposta demora ~6s | normal: o TurboLLM carrega o modelo sob demanda (JIT) e descarrega quando ocioso |
| Feature X "não faz nada" | falta a chave dela no `.env` (é opcional — veja seção 5) |

---

*Dúvida sobre a arquitetura (memória, persona, ferramentas, proativo)? Está tudo no
[`README.md`](README.MD). Histórico de mudanças no [`PATCHNOTES.md`](PATCHNOTES.md).*
