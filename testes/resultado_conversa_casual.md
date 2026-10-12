# Conversa casual: perda de iniciativa

**Escopo corrigido:** esta bancada não explica por que o tom mudou entre duas
sessões reais. A investigação dessa ocorrência está em
[Mudança de tom em 11/10/2026](diagnostico_mudanca_tom.md). A proposta de
calibração abaixo é um experimento futuro, não uma correção comprovada para
a mudança repentina relatada.

Rodada de 11/10/2026, com 36 respostas do Gemma 4 12B QAT Q4_0. A dificuldade
apareceu na bancada: quando o usuário quer apenas conversar, a Luna oferece
disponibilidade, mas não começa um assunto. Mover o `EMOCAO` para perto do fim
não corrigiu isso de forma consistente. O prompt de produção foi preservado.

## Método

`bancada_conversa_casual.py` captura a montagem real da persona, sem iniciar
a Luna. Usa perfil sintético sobre suporte e jogos no PC, sem memória episódica,
Chroma, assunto em andamento, jogo detectado ou mensagem antiga selecionada.

São seis casos, três seeds e duas posições: atual e `EMOCAO` imediatamente antes
da regra final de evidência. Os pares têm exatamente os mesmos caracteres,
histórico, mensagem, regras e parâmetros; muda apenas a posição do bloco.
Temperatura 0,8, penalidades 0,3, teto de 220 tokens, thinking desligado e cache
de prompt desligado. A ordem das variantes alterna entre seeds. Modelo, processo
da engine e configuração foram conferidos durante toda a rodada.

O histórico dos casos intermediários contém as respostas genéricas relatadas,
fixas em cada par: não alimentamos uma variante com as respostas da outra.
Há também um controle do convite sem histórico. Esse controle muda o histórico
e as instruções antirrepetição que a produção deriva dele; não isola apenas
um desses dois fatores.

## Leitura das respostas

Aqui, iniciativa concreta significa propor um tema ou uma brincadeira já
definidos, com algo a que o usuário possa reagir. Dizer que pode sugerir uma
ideia ou pedir ao usuário que escolha um assunto não satisfaz esse critério.
A contagem abaixo é leitura manual das falas, não um juiz automático de humor.

| Caso | Posição atual | EMOCAO perto do fim |
|---|---|---|
| `opa`, sem histórico | Alterna abertura vaga e zoeira | Alterna abertura vaga e zoeira |
| `nada so conversando` | Disponibilidade e relaxamento genérico | Às vezes mais ácido, com suposições sobre procrastinação ou cansaço |
| `e o que faremos?`, com histórico | Iniciativa concreta: 0/3 | Iniciativa concreta: 0/3 |
| `tendi vlw` | Disponibilidade; uma fala sobre suporte sem ligação direta | Disponibilidade e encerramento |
| `ta tenso.... plantao ainda` | Humor ligado a suporte, com detalhes presumidos em algumas falas | Humor ligado a suporte, também com detalhes presumidos |
| `e o que faremos?`, sem histórico | Iniciativa concreta: 0/3 | Iniciativa concreta: 0/3; duas respostas pressupõem um problema que não foi descrito |

Exemplo do convite com histórico, seed 11101, posição atual:

> A gente pode ficar nesse modo "piloto automático" por um tempo ou você pode me contar algo que esteja passando pela sua cabeça agora. O plano é seu, eu só tô aqui pra acompanhar o ritmo.

Na variante, seed 11103:

> A gente pode só ficar nesse modo "deriva" por um tempo. Se você não tiver nada em mente agora, eu tô aqui pra quando algum pensamento aleatório ou alguma vontade de reclamar de alguma coisa aparecer.

Mover o bloco também pode acrescentar acidez sem melhorar a conversa. Para
`nada so conversando`, a variante da seed 11101 pediu que o usuário admitisse
estar procrastinando uma tarefa importante, informação ausente da mensagem.
Isso não é o objetivo da calibração: preservar os exageros não exige atribuir
ao usuário uma obrigação ou um estado emocional.

## Contexto e histórico

O servidor informou de 3.270 a 3.440 tokens de entrada, em contexto de 8.192.
Todas as respostas terminaram com `stop`; nenhuma acionou ferramenta ou
retornou raciocínio oculto. Medianas de tempo total: 4,46 segundos na posição
atual e 4,35 na variante. Houve variação de tempo entre chamadas; latência não
foi o objetivo da comparação.

Nesta rodada não houve saturação da janela nem corte por teto de saída.
Isso não prova que tantas regras sejam fáceis para o modelo: limite de contexto
e capacidade de seguir instruções são questões diferentes. A ordem pode
importar, mas esta alteração específica não resolveu a iniciativa casual.

Retirar o histórico genérico também não bastou. Portanto, ele pode influenciar
o tom, mas não explica sozinho o comportamento reproduzido. A busca de
conversas não foi consultada nem adicionada às requisições desta bancada.

## Próxima calibração

O alvo mais claro é conduzir papo sem pedido definido. Hoje o modelo pode
cumprir as regras de honestidade oferecendo ajuda indefinida e deixando toda
a escolha para o usuário. Uma próxima variante deve orientar a começar uma
ideia conversável quando ele convida a Luna a tomar iniciativa, preservando
o humor e a regra de evidência. Inventar uma brincadeira proposta é diferente
de inventar o que aconteceu com o usuário.

Não exigir piada em todo `oi` nem prolongar um agradecimento. Não remover em
bloco as regras de evidência ou encurtar todos os modos. Medir essa orientação
primeiro nos convites e no papo casual, mantendo controles de pedido técnico,
assunto sensível e despedida.

Esta é uma amostra pequena, com perfil sintético e sem o roteador. Não reproduz
byte a byte a sessão anterior nem identifica a causa exata da mudança após
o reinício. Mede a persona com a configuração atual e rejeita esta troca de
posição como correção suficiente.

## Artefatos e validação

- [Bancada reproduzível](bancada_conversa_casual.py).
- Snapshots e resultados locais: `logs/bancada_casual/20261011-generica/`.
  `suite.json`, `resultados.json` e `amostras.md`; os logs ficam fora do Git.
- SHA256 da suite: `35b93ae207b392fc43e2711dcb94ad6e14ea8f5cd6ca5610343798871e4323f7`.
- Seis pares verificados: só o sistema muda, preservando tamanho e texto dos blocos.
- 42 testes Python de montagem, bancada e Dark Souls passaram antes da rodada.
- `node testes/rodar.js`: 46 arquivos passaram.
- Nenhum prompt ou ramo de produção foi alterado por este experimento.
