# Conversa mais desenvolvida — 11/10/2026

**Experimento rejeitado e revertido a pedido do usuário.** Os gatilhos por
palavras-chave, os assuntos predefinidos e as instruções extras foram removidos.
O placar restrito não demonstrou recuperação geral da personalidade nem
explicou a mudança súbita de tom. O restante registra o que foi testado,
não o comportamento atual da Luna.

O ajuste experimental entrou no caminho comum da persona. Quando o usuário convida a Luna
a bater papo sem pauta, ela recebe um ponto de partida concreto e desenvolve
uma ideia. Nos demais assuntos, a orientação permite completar o raciocínio
no texto, preservando respostas curtas para cumprimentos e despedidas.

Esta é uma calibração autorizada após a investigação; não comprova a causa
histórica da mudança súbita de tom descrita em
[diagnóstico](diagnostico_mudanca_tom.md).

## Comportamento e alcance

- O EMOCAO original e a ordem da persona continuam iguais. A orientação de
  conversa fica na mensagem atual, em `prompts.prompt_conversa`.
- Convites explícitos como `nada so conversando`, `vamos conversar` e
  `puxa um assunto` liberam um tema imaginário. `O que faremos?` só libera
  esse tema quando a última fala do usuário já era um convite para bater papo.
  Em uma conversa sobre um servidor, a mesma pergunta mantém o assunto.
- Há três pontos de partida: jogo imaginário, invenção doméstica e cidade
  fictícia. O histórico alterna o ponto de partida; são briefings para geração,
  não respostas prontas. O modelo inventa os detalhes dentro de uma hipótese
  explícita. Não há busca, ferramentas ou chamada extra ao LLM para escolhê-los.
- No texto, um ou dois parágrafos curtos podem desenvolver uma ideia. O canal
  de voz mantém sua orientação de concisão. O orçamento da geração não mudou.
- Proativos, ferramentas e modos enxutos mantêm suas instruções. O golden
  confirmou sistema idêntico nos 44 cenários existentes; somente a mensagem
  atual ganhou orientação em 12 deles. Foram adicionados três cenários para
  os convites e para distinguir o próximo passo de um projeto.

## Bancada segmentada

A rodada final usa Gemma 4 12B IT QAT Q4_0 e llama.cpp b9608 ROCm, contexto
8.192. São nove casos, duas seeds pareadas e duas variantes: **36 respostas**,
com 28 do prompt completo e oito dos controles enxutos. Histórico e fontes
sintéticas ficam fixos; modelo, engine e configuração são conferidos durante
a execução. As variantes alternam ordem entre seeds.

| Caso | Antes | Ajustado |
|---|---|---|
| Sem pedido e convite para começar | Contribuição concreta: 0/4 | Contribuição concreta: 4/4; invenções e cidades explicitamente imaginadas |
| Abertura e reciprocidade | Curtas, com disponibilidade e referências ao perfil | Continuam curtas; não houve melhora consistente da personalidade |
| Situação leve sobre escolher um jogo | Humor e explicação de motivos presumidos | Continua com humor, mas ainda presume mecanismos ou motivos não confirmados |
| Pergunta sobre o que faz uma conversa render | Explicação com culpa atribuída ao usuário | Mais desenvolvida, porém mantém interpretações psicológicas indevidas |
| Encerramento | Despedida misturada com conselhos | Mais curta; um dos exemplos ainda presumiu passeio/descanso |
| Controles: agradecimento e tristeza explícita | Quatro respostas | Mesmas quatro respostas, byte a byte nos pares |

Contribuição concreta significa já apresentar uma ideia que o usuário possa
comentar. Dizer que pode sugerir uma ideia ou entregar a escolha ao usuário
não conta. A contagem 0/4 versus 4/4 é leitura manual das falas, não julgamento
automático de humor. O melhor resultado está nos convites sem pauta;
**não houve recuperação uniforme de tom ou factualidade nos demais casos**.

Exemplo ajustado: a Luna imaginou um copo que reage por telepatia à paciência
de quem bebe e transforma uma mesa em um desastre de gelo. Em outro, decidiu
como administraria uma cidade fictícia e explorou o caos da própria decisão.
São brincadeiras hipotéticas, não afirmações sobre a vida real do usuário.

As 36 gerações terminaram sem corte, ferramenta ou raciocínio oculto; cada
resposta trouxe uma tag de clima válida. Nos casos completos, a entrada
passou de 3.282–3.389 para 3.532–3.769 tokens, ainda dentro do contexto 8.192.
A mediana do tempo da geração passou de 4,26 para 5,88 segundos. Esse tempo
não inclui o roteador, áudio ou carregamento inicial do modelo.

Os resultados finais estão em
`logs/bancada_casual/20261011-conversa-completa-v4/`. Houve três versões
anteriores: adicionar instruções genéricas de iniciativa prolongou a
disponibilidade; exigir mais acidez aumentou acusações e fatos inventados;
o ponto de partida concreto deu a melhora preservada na versão final.

## Verificação e uso

Passaram 17 testes Python de montagem/assuntos e os 46 arquivos do conjunto
Node. O golden foi atualizado intencionalmente para a calibração e os três
cenários novos. Espaços finais em `Conversas anteriores: ` reproduzem o
prompt de produção e foram preservados no golden.

É preciso reiniciar a Luna para carregar o código atualizado. Para observar
o caminho novo, converse normalmente e experimente `nada so conversando`;
depois comente a ideia que ela trouxe. Um problema ou dúvida com assunto
definido continua usando esse assunto. O ajuste não recarrega conversas
arquivadas, não muda memória nem o esfriamento do modelo.
