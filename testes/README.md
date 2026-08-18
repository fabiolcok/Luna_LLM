# Testes da presença

```bash
node testes/rodar.js
```

Sem dependência. Só Node. ~2 segundos.

Para validar também o backend Python antes de fechar uma mudança maior:

```bash
node testes/rodar_tudo.js
```

Esse segundo comando roda primeiro a suíte rápida acima e depois todos os `testa_*.py` como
módulos. Ele procura o Python do `venv` e tem fallback para o launcher do sistema. As bancadas
que usam modelo real ficam de fora de propósito.

## Por que existem

O `templates/Index.html` tem ~4100 linhas com CSS, HTML e todo o JS da interface num arquivo só.
O erro mais comum ali — usar `let`/`const` antes da declaração — **derruba o script inteiro** e
a página abre em branco, sem mensagem nenhuma. `node --check` não vê: a sintaxe é válida.

Estes testes **extraem o `<script>` do HTML na hora e executam** com um DOM falso. Foi assim que
apareceram, entre outros: quatro quebras de zona morta, o cometão pulando pra origem do viewBox,
`classList.remove` variádico, config morta em três tabelas, e um `<svg>` sendo destruído sem
reconstrução.

## O que cada um cobre

| arquivo | assunto |
|---|---|
| `checa.js` | carga: o script roda até o fim sem `ReferenceError` |
| `testa_rosto.js` | as caras, a curadoria dos climas e quem pisca |
| `testa_eixos.js` | estado / atividade / emoção não se combinam no CSS |
| `testa_ritmo.js` | as histórias não se amontoam (espaçamento e teto) |
| `testa_sujeira.js` | fuligem: nasce, esfrega, some |
| `testa_medo.js` | chuva de asteroides: atrapalhar estica, com teto e período frio |
| `testa_invasao.js` | invasão: a frota ronda, fecha o cerco, debanda |
| `testa_desistir.js` | 3 histórias por tempo demais → vira de costas |
| `testa_cometao.js` | a martelada nunca perde a posição do cometão |

## Escrevendo um teste novo

Copie o mais parecido e ajuste. O padrão é:

1. ler o `Index.html`, extrair o `<script>`
2. montar `global.document` e companhia com um DOM falso
3. `new Function(src + ';globalThis.__t = { ...o que você quer testar... }')()`
4. asserções com `diz(condição, 'frase que explica o que tem que valer')`

**Prefira asserção que descreve a regra, não o número.** `alt('T_T') < alt('ᵔ ᵕ ᵔ')` continua
valendo depois que alguém afinar os valores; `alt('T_T') === -0.22` vira manutenção.

Cada arquivo carrega o próprio DOM falso, e eles não são iguais — cada um precisa de uma
fidelidade diferente. Isso é proposital: já custou falha falsa três vezes o duble ser mais
pobre que o DOM de verdade (`classList` não-variádico, `className` fora de sincronia com
`classList`, `querySelector` inventando elemento em vez de devolver `null`).

## Bancada da persona (modelo real)

```bash
.\venv\Scripts\python.exe -X utf8 testes\bancada_persona.py --repeticoes 3 --rotulo nome-do-experimento
```

Não sobe a Luna, voz, web ou Telegram, mas usa o TurboLLM e o modelo configurado. A bancada chama
a mesma função de persona da aplicação com perfil, memória, ChromaDB e estado do PC substituídos
por cenários controlados. As memórias irrelevantes são intencionais: medem se a Luna força conexão
pessoal. Checks objetivos rodam automaticamente; as respostas completas ficam em
`logs/bancada_persona.jsonl` (ignorado pelo Git) para comparar versões.

## Bancada dos acompanhamentos (modelo real)

```bash
.\venv\Scripts\python.exe -X utf8 testes\bancada_acompanhamentos.py
```

Confere se o roteador oferece acompanhamento para um desfecho concreto sem confundir agenda,
lembrete e conversa cotidiana. As ferramentas são substituídas por versões locais: não cria evento,
nota ou acompanhamento real e não sobe voz, web ou Telegram.
