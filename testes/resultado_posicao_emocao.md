# Posição de EMOCAO no proativo — 2026-09-04

## Contexto anterior

O TODO.md registra reorganização da persona (37/39 antes e depois), inclusão de
EMOCAO no proativo (14/15 antes, 13/15 depois, com diferença de tom) e variação de
placar entre execuções idênticas. Não foi encontrada ali uma comparação específica
de EMOCAO antes/depois de ENXUTO_PROATIVO. O comentário de nucleo_enxuto explica
que EMOCAO vem antes para a instrução da tarefa prevalecer.

## Experimento

Comando: `venv\Scripts\python.exe -X utf8 testes/bancada_emocao_proativa.py --experimento posicao --repeticoes 3`

Dados locais: `logs/bancada_emocao_posicao_20260904_231625.json`.
Modelo confirmado: Gemma 4 12B QAT Q4_0 no TurboLLM.

- Atual: identidade curta, EMOCAO, ENXUTO_PROATIVO, regras finais do núcleo.
- Candidata: identidade curta, ENXUTO_PROATIVO, EMOCAO, mesmas regras finais.
- Nenhuma palavra dos blocos foi alterada. A bancada valida a substituição única e
  a preservação da contagem de caracteres; salva os sistemas montados por geração.
- 30 respostas: três jogos, RSS e email; três rodadas por variante, ordem alternada.
- Instruções Steam e dados iguais dentro dos pares. Fontes pessoais substituídas
  por fixtures. Todos os turnos passaram pelo núcleo enxuto COM EMOCAO.
- Não houve mudança no prompt de produção. Não foi testado mover EMOCAO para depois
  de todas as regras, nem para outra mensagem. Amostra pequena, sem seed pareada.

## Leitura dos resultados

Checks: atual 14/15; emoção depois 15/15. A única diferença foi "Quatrocentos horas"
no controle: o check exige "400" ou "quatrocentas". Existe erro de concordância,
mas isso não mostra uma diferença de criatividade nem alteração do número 400.

A candidata produziu uma imagem compreensível no retorno a Hades após desistência:
"Esse seu ciclo de recaída é mais persistente que a própria imortalidade dos deuses gregos."
Também produziu "persistência quase arqueológica" em Hollow Knight. O controle
continuou tendo escracho: residência permanente no jogo e cartão chorando.

Os dois lados continuaram narrando horas, ausência e descrição dos jogos.
A candidata inventou 50 horas no lugar de 6 e 30 dias no lugar de 21. O controle
também corrompeu números em Hades: "Trêsessenta e cinco" e 3 horas no lugar de 8.
Na candidata apareceram obrigações "aqui fora" e dinheiro que o usuário "não tem";
o controle também inventou prioridades, progresso e dívidas.

Exageros figurativos não foram tratados como defeito por serem absurdos. O problema
é perder a conexão com a situação ou alterar a premissa factual. Não houve avaliação
cega ou placar humano quantitativo: esta é uma leitura editorial dos exemplos.

Conclusão: inverter estes dois blocos não mostrou ganho consistente que justifique
trocar a ordem na Luna. Isso não prova que posição nunca importe; só não confirmou
a hipótese nesta comparação. Manter a ordem atual.

Validação adicional: `node testes/rodar.js` passou nos 36 arquivos. Somente a bancada
e este relatório foram alterados neste teste; nenhum golden foi regravado.
