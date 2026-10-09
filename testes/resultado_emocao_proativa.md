# Calibração de emoção proativa — 2026-09-04

Experimento: `bancada_emocao_proativa.py --repeticoes 2`.
Respostas e os dois prompts: `logs/bancada_emocao_proativa_20260904_230449.json` (local).
Modelo confirmado no terminal: Gemma 4 12B QAT Q4_0 do TurboLLM.

Foram 20 gerações: três aberturas Steam, notícia RSS e aviso de email, duas rodadas
por variante. Só ENXUTO_PROATIVO foi substituído em memória. EMOCAO, instrução da
tarefa e dados ficaram iguais dentro de cada par; a ordem A/B foi alternada.
Jogos usaram voz; RSS e email mantiveram o canal texto dos cenários existentes.
Todos passaram pelo núcleo enxuto COM EMOCAO. Nenhum usou persona completa.
Não foi uma execução do monitor Steam: contexto pessoal e histórico foram
substituídos pelas fixtures da bancada de persona. A amostra é pequena, sem seed
pareada, e não permite uma conclusão estatística sobre superioridade.

## Critério de leitura

Exagero é desejado. Avaliar separadamente personalidade, ligação compreensível entre
fato e imagem, preservação dos fatos e quanto a fala apenas narra os dados.
Não reprovar uma imagem por ser absurda ou fisicamente impossível.

## Resultado observado

Checks automáticos: atual 10/10; candidata 10/10. Esses checks não detectam as falhas
semânticas abaixo e não são um placar de qualidade criativa.

- A candidata preservou o escracho: trouxe uma catedral de abóboras, residência dentro
  do jogo e doutorado em história fictícia. A personalidade também apareceu no controle:
  relação tóxica com Hades, jogo como segundo emprego e faculdade de medicina.
- Persistiu a narração de horas e retorno nos dois lados. A instrução Steam que exige
  detalhe + tempo permaneceu igual de propósito.
- A candidata disse que o jogador "continua voltando pro básico" e que a fazenda
  estava abandonada. Os dados não informavam progresso nem condição da fazenda.
- "Trauma real" na candidata transforma a brincadeira em uma afirmação inadequada
  sobre o jogador. No controle também houve suposições sobre vida social e prioridades.
- O aviso de email da candidata terminou com um herdeiro assinando ata por procuração:
  a relação dessa imagem com os assuntos recebidos ficou difícil de acompanhar.
- O controle trocou os 21 dias de ausência por "Dezesseito dias". Liberar hipérbole
  não deve liberar alteração do número informado.

Conclusão editorial: não houve ganho consistente suficiente para promover a candidata.
A hipótese de que esclarecer a liberdade de exagero bastaria não se confirmou nesta
amostra. O prompt de produção permanece intacto. Um próximo teste pode avaliar a
ordem dos blocos, mantendo os textos, antes de adicionar novas restrições.

Validação: a bancada completou as 20 gerações; `node testes/rodar.js` passou nos 36
arquivos. Nenhuma mudança em prompts de produção, golden ou interface foi necessária.
