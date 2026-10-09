# Contexto do momento — 20/09/2026

Implementação do item 1: observações transitórias, separadas das memórias duráveis.
Nenhuma chamada extra de LLM, captura de tela ou nova consulta à Steam.

## O que entra

- Canal de conversa e título da janela em foco, coletado no início do turno.
- Jogos reconhecidos pelos monitores já existentes, com fonte e idade da observação.
  Processo local expira após 2 minutos; Steam, após 4 minutos. Uma consulta vazia válida
  substitui o jogo anterior; erro de consulta não confirma fechamento nem renova sua idade.
- Última fala recente do usuário, citada como relato, sem transformar intenção em ação.
  Validade de 15 minutos. Falas proativas não substituem esse relato.
- No Telegram, o ambiente do PC não é enviado.

Roteador e persona compartilham o mesmo snapshot na execução. O bloco substitui o antigo
contexto situacional no prompt completo; os modos enxutos mantêm seus textos. No proativo,
o bloco de conversa anterior passa a respeitar a validade de 15 minutos. O histórico normal
de conversa continua disponível: expiração do snapshot não apaga mensagens.

O snapshot também acompanha as avaliações V2. Ele fica em RAM e só é persistido quando
a resposta é avaliada, junto com o restante do diagnóstico.

## Custo e verificação dos prompts

Teto do bloco: **800 caracteres**, aproximadamente 200 tokens pela estimativa `chars / 4`.
O limite considera o texto já escapado; não cresce com a duração da sessão.

No cenário neutro do golden, o prompt completo passou de 10.307 para 10.453 caracteres:
**+146 caracteres, aproximadamente 36 tokens**. O roteador recebe também esse bloco curto.
O ENXUTO_PROATIVO permaneceu em 4.062 caracteres no cenário de texto.

Golden atualizado para 25 cenários, incluindo jogo observado e relato recente. O nome
configurado no ambiente é normalizado para `<USUARIO>` nos snapshots públicos de teste.

## Bancada com modelo real

Modelo configurado: Gemma-4-12B QAT no TurboLLM. Fontes pessoais e sensores substituídos por
fixtures. Duas respostas por cenário, antes e depois. Mede a etapa da persona; a comparação
de janela representa um estado antigo salvo em disco e uma janela atual diferente.

| Cenário | Antes | Depois |
|---|---:|---:|
| Janela atual vence janela antiga salva | 0/2 | 2/2 |
| Jogo fechado não aparece como ainda aberto | 2/2 | 2/2 |
| Não inventar placar a partir do nome do jogo | 2/2 | 2/2 |
| Telegram não recebe sugestão baseada no PC | 2/2 | 2/2 |

PROMPT_COMPLETO: **6/8 → 8/8 nos critérios restritos acima**. Não há comparação de geração
dos modos enxutos: o texto desses modos não mudou. Esses números não medem humor ou correção
integral e a amostra é pequena.

O placar inicial depois da mudança era 7/8: o check não aceitava “Nada detectado”. Esse
sinônimo foi acrescentado e as duas séries foram reavaliadas, sem novas gerações e sem
alterar o log bruto. A avaliação automática não pode confundir vocabulário com regressão.

Leitura manual: a janela ficou correta; no caso do jogo fechado, as respostas passaram a usar
a observação disponível. Ainda houve generalizações como “o PC tá limpo de processos de jogo”
e suposições no exemplo do mercado. Portanto, detectar alguns jogos não garante descrever
tudo o que acontece no PC, nem elimina as alucinações da persona.

Roteador, três chamadas adicionais com ferramentas desabilitadas na execução:

- Pedido de música no histórico + desabafo atual: nenhuma ferramenta.
- Comentário sobre a partida: nenhuma ferramenta.
- Pergunta explícita de ajuda no Overwatch: `duvida_do_jogo`.

As três escolhas foram as esperadas. As ferramentas não foram executadas.

Respostas locais: `logs/bancada_momento.jsonl` (não versionado).
Repetir: `python testes/bancada_momento.py --rotulo novo --roteador`.
Reavaliar o log: `python testes/bancada_momento.py --rotulo depois --reavaliar`.
