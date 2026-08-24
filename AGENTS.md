# Instruções pra agentes de IA neste repositório

Leia isto antes de mexer. Vale pra Claude Code, Codex, ou qualquer outro.
Não é burocracia: cada item aqui é um erro que **já aconteceu** e custou tempo.

---

## 1. Rode os testes. Sempre.

```bash
node testes/rodar.js
```

Sem dependência nenhuma — só Node. Leva 2 segundos.

**Rode antes e depois de qualquer mudança no `templates/Index.html`.** Esse arquivo tem ~4100
linhas e concentra CSS, HTML e todo o JS da interface. É onde tudo quebra.

O teste não é enfeite: ele **executa** o `<script>` da página com um DOM falso. É a única coisa
que pega o erro que mais dói aqui (ver item 2). `node --check` **não** pega — a sintaxe é
válida.

Se você mudou comportamento de propósito e um teste falhou, **atualize o teste** e diga isso na
mensagem do commit. Não apague asserção pra ficar verde.

---

## 2. As armadilhas deste projeto

Cada uma derrubou algo de verdade. Estão comentadas no código onde bateram, mas ficam aqui
juntas porque são o tipo de coisa que não se deduz lendo.

### `let`/`const` usado antes de declarar mata a página INTEIRA
Já aconteceu **quatro vezes**. `let`/`const` não são içados: usar antes da declaração levanta
`ReferenceError`, e como é tudo um `<script>` só, **nada** roda depois disso. A interface abre em
branco, sem mensagem, sem erro visível.

O `templates/Index.html` declara coisas ao longo de 4100 linhas, então é fácil escrever no topo
algo que só nasce lá embaixo. Cuidado especial com:
- `const X = [...OUTRA_COISA]` — a lista é avaliada **na declaração**, não no uso
- IIFE `(function(){...})()` que lê constante declarada depois

Padrão usado aqui pra resolver: adiar com `setTimeout(..., 0)`, ou virar função
(`const LISTA = () => [...]`, `function ehRostoInteiro()`).

### Animação de `transform` no CSS SUBSTITUI o atributo `transform` do SVG
Elemento SVG posicionado por `setAttribute('transform', 'translate(...)')` **perde a posição**
enquanto uma animação CSS de `transform` roda nele. O cometão piscava na origem do viewBox por
causa disso. Anime posição de SVG sempre pelo mesmo canal (o atributo, via `anime`).

### `offsetWidth` é `undefined` em SVG
Só existe em `HTMLElement`. O truque `void el.offsetWidth` pra reiniciar animação **não
funciona** em nó SVG — e falha calado. Em `#presenca` (uma `div`) funciona.

### `rx` só funciona em `<rect>`, não em `<circle>`
Por isso as bolinhas da órbita são `rect` com `rx` — é o que deixa virarem pixel quadrado no
modo jogo.

### anime.js aqui é a **v3.2.2**
`scrambleText`, `createAnimatable` e o resto da API v4 **não existem**. Confira na v3 antes de
usar qualquer coisa que você viu na documentação nova.

### NUNCA use CDN
A Luna roda offline, na máquina do usuário. Tudo é servido de `static/`. Hoje há **zero**
referências a CDN no projeto — mantenha assim.

---

## 3. Contratos que atravessam arquivos

### Texto de prompt mora no `prompts.py`, lógica de prompt mora no `pensar.py`
Todo o TEXTO dos prompts está em `modulos/prompts.py`, separado por eixo (identidade, emoção,
conduta, forma, saída) mais os 12 modos enxutos. O `pensar.py` decide QUAL usar e em que ordem
testa os gatilhos. Não escreva prompt novo dentro do `pensar.py`.

São cinco blocos: IDENTIDADE, EMOÇÃO, ESTRUTURA, LIMITES, SAÍDA. EMOÇÃO é o único pensado para
ser trocado inteiro um dia (raiva, soberba, compreensiva).

**A ordem das regras dentro do prompt é dado medido, não arrumação.** Num 12B a posição importa —
três vezes neste projeto uma regra forte foi desobedecida porque a guarda dela estava num bullet
distante, e colar as duas resolveu. Reordenar é experimento de bancada.

Antes e depois de mexer:

```bash
.\venv\Scripts\python.exe -X utf8 -m unittest testes.testa_prompt_montagem
```

Ele monta o prompt de 22 ramos (cada canal, cada modo enxuto) e compara byte a byte com
`testes/prompt_golden.txt`. Refatoração que não deveria mudar nada tem que passar sem tocar no
golden. Mudança de propósito: regrave com `-m testes.testa_prompt_montagem --atualizar` e leia o
`git diff` do golden — é ali que aparece o que realmente entrou e saiu.

E se a mudança for de comportamento, meça na bancada — **lendo o placar segmentado**. Metade dos
cenários roda em `modo_enxuto`, onde a persona nem entra; variação ali é temperatura, não a sua
mudança. A bancada imprime os dois números separados justamente por isso.

### Fala proativa pode demorar — não otimize latência ali
Decisão do dono do projeto, ago/2026: em tarefa proativa, **resposta rica vale mais que resposta
rápida**. O raciocínio é que ninguém está esperando essa fala — 15 segundos para algo que ele não
pediu e que tem graça é melhor que 1 segundo para uma frase que dá pra montar em Python puro.

Então não troque geração por template, não corte o prompt do proativo "pra ficar mais leve" e
desconfie de qualquer instrução do tipo "só a pergunta" ou "1 frase" numa tarefa proativa: foi
exatamente isso que fez a oferta de resumir vídeo sair sempre com a MESMA frase seca, anulando
a variação que o `_gerar_fala_proativa` já sorteava.

Em turno REATIVO a conta é outra — ali ele está esperando, e a latência conta.

### `[clima:X]` — Python escolhe a palavra, Python escolhe a cara
O modelo termina a fala com uma tag (`[clima:carinho]`, 12 opções fixas). O `pensar.py` traduz
num kaomoji do grupo `_ROSTOS` e manda pro front. **O modelo nunca desenha a carinha** — quando
deixávamos, ele inventava carinha com devanágari e viciava nas 3 do treino.

Se mexer na lista de climas do prompt (`prompts.py`), mexa no `_ROSTOS` junto. `testes/testa_rosto.js`
acusa se um clima ficar órfão.

### Toda cara passa por `pintarRosto()`
É o único lugar que escreve o rosto no DOM. Um `textContent =` solto em outro lugar já causou
brigas de quem escreve por cima de quem. Se precisar mexer no rosto, vá por lá.

### `NAO_PISCA` é curadoria humana
A lista de quais caras piscam foi escolhida uma a uma pelo dono do projeto. Não "melhore" por
conta própria. O teste exige que **toda** cara do projeto tenha decisão — cara nova sem decisão
falha.

### Whisper e embeddings rodam em **CPU de propósito**
`device="cpu"` em `ouvir.py` e `memoria.py`. Não é descuido: é pra deixar a VRAM inteira pro
LLM. Em placa de 12GB isso é a diferença entre rodar e não rodar.

### O `.env.example` é cheio de PLACEHOLDER
`seu_token_telegram`, `sua_chave_steam`... Leia chave de ambiente por `modulos/config_env.py`,
que trata placeholder e vazio como a mesma coisa. Um `int(os.getenv(...))` cru já derrubou o app
inteiro na importação por causa disso.

---

## 4. Regras de conteúdo

### Não estrague os easter eggs na documentação
`README.MD` e `PATCHNOTES.md` mencionam as surpresas **sem** dizer como funcionam ("de vez em
quando acontece alguma coisa com ela"). É decisão do dono. Não liste os eventos nem como
resolver cada um.

### Zero nome pessoal no código
O repositório é público. O nome do usuário vem de `USUARIO_NOME` no `.env`; no código é sempre
"o usuário".

### Comentários explicam POR QUE, não O QUE
O padrão do projeto é comentar a decisão e o que ela evita — de preferência citando o bug que
motivou. Comentário que repete o código não agrega.

---

## 5. Convivência entre agentes

Se mais de um agente mexe no projeto:

- **`templates/Index.html` é o ponto de colisão.** Combine quem está nele. Os outros arquivos são
  bem mais independentes.
- **Commits pequenos, `git pull` antes de começar.** `main` é o branch de trabalho.
- **Não suba a Luna sem avisar.** Duas instâncias brigam pela porta e pela sessão do Telegram
  (o Telethon só aceita um processo).
- **Não commite `.env`, `logs/`, `venv/`, `modelos/`** — já estão no `.gitignore`.

---

## 6. Ambiente

| | |
|---|---|
| SO | Windows 11 |
| Python | 3.12, em `venv/` na raiz |
| Node | v24 (só pros testes) |
| LLM | TurboLLM em `http://127.0.0.1:6996/v1`, Gemma-4-12B QAT |
| Subir | `Atalhos/Luna.bat` (com terminal) ou `Luna.vbs` (sem janela) |

Instalação do zero: `INSTALACAO.md`.

---

## 7. Rugosidade conhecida

Cada teste em `testes/` carrega o próprio DOM falso, e eles **não são idênticos** — cada um
precisa de uma fidelidade diferente (um rastreia atributos escritos, outro dispara timers na
mão, outro precisa de `classList` variádico). Consolidar num só já foi tentado mentalmente e
quebraria casos específicos. Se for mexer, rode os 9 depois.
