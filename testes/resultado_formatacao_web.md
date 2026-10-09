# Apresentação das respostas na web — 08/10/2026

O Gemma já produzia Markdown, especialmente código. O ajuste orienta a escolha
da estrutura e melhora a apresentação no chat: títulos com hierarquia, negrito,
listas com subitens, citações, separadores, tabelas alinhadas e blocos identificados
pela linguagem. Tabelas e código largos rolam dentro da mensagem.

Tudo continua servido localmente, sem dependências novas. O HTML escrito pelo
modelo é escapado; links Markdown aceitam apenas HTTP(S), e código permanece literal.
O botão existente de copiar preserva o Markdown original.

## Prompt e canais

`CANAL_WEB` acrescenta uma orientação ao bloco de texto existente. Não altera
identidade, emoção nem ordem dos demais blocos. A seleção vale apenas quando
`responder_completo=True` e a presença é no PC; Telegram mantém `CANAL_TEXTO`
e voz mantém `CANAL_VOZ`. Os modos enxutos substituem o prompt completo e
continuam iguais. Respostas web conservam a formatação; a limpeza de voz
existente continua separada.

O diff entre o golden anterior a este trabalho e o atual contém apenas **13
linhas acrescentadas em 32 cenários**, todas a mesma orientação web. Nenhuma
linha anterior mudou. O acréscimo é de 533 caracteres, **121 tokens medidos
nesta bancada**, aproximadamente 4% da entrada média. Não há outra chamada
de modelo nem um modelo adicional carregado.

## Bancada no Gemma

Modelo carregado: Gemma 4 12B QAT Q4_0; TurboLLM 1.13.4, llama.cpp b9608 ROCm,
contexto 8192. Dados inteiramente sintéticos, sem notas pessoais ou ferramentas
reais. Pedidos capturados do caminho de produção, thinking desligado, cache
desativado, duas seeds nos quatro cenários principais e uma nos dois casos leves.
Modelo e configuração foram conferidos entre chamadas; respostas lidas manualmente.

A primeira orientação genérica produziu **0/2 tabelas** nas comparações. A
orientação final pede uma tabela quando há opções com vários atributos fornecidos.
A rodada final teve 20 respostas, dez antes e dez depois:

| Cenário | Antes | Depois |
| --- | --- | --- |
| Comparar duas opções, sem pedir tabela explicitamente | 0/2 tabelas | 2/2 tabelas, com os atributos fornecidos |
| Procedimento passo a passo | 0/2 listas numeradas | 2/2 listas numeradas |
| Exemplo de JSON em Python | 2/2 blocos de código | 2/2 blocos; uma resposta também usou título e passos |
| Histórico versus memória permanente | 2/2 em parágrafos | 2/2 em parágrafos; não forçou uma estrutura maior |
| Comentário leve sobre jogar | Sem título/lista | Sem título/lista |
| Saudação “eae” | Sem título/lista | Sem título/lista |

**Segmentação:** esses 20 pedidos acionaram `PROMPT_COMPLETO`. “eae” não é uma
saudação reconhecida pelo detector de núcleo enxuto. A fixture da bancada foi
corrigida para “oi, tudo bem?” e agora exige o ramo `ENXUTO_SAUDACAO`.
Um controle adicional com essa frase fez duas chamadas: pedidos idênticos antes
e depois, e a mesma resposta curta, sem títulos/listas. Assim, foram **20 respostas
no prompt completo e 2 no enxuto** na validação final. A variação no enxuto não
seria efeito desta mudança.

Na rodada de prompt completo, a entrada média passou de 3112,9 para 3233,9 tokens;
a saída, de 123,1 para 160,1. O tempo total médio observado passou de 5,61 para
6,29 segundos. São medidas pequenas deste conjunto, não uma previsão de latência.

## Limites observados

O ganho medido é de apresentação. Em uma comparação final, o modelo ainda disse
que 9 GB caberiam “com folga” junto do jogo, embora o consumo do jogo fosse
desconhecido; a premissa já aparecia nas respostas anteriores. Em outra, respeitou
a tabela mas a colocou depois da opinião. Não considerar o novo formato uma
correção de precisão factual ou garantia de obediência a toda instrução.

O renderizador continua um subconjunto de Markdown: não aceita HTML nem tenta
implementar todos os recursos de CommonMark. As estruturas usadas nas amostras
foram conferidas; código não recebe realce de sintaxe automático.

## Verificação

- `node testes/rodar.js`: 43 arquivos passaram antes e depois. O teste do chat
  executa títulos, listas aninhadas, tabelas, código e conteúdo parcial, e verifica
  escape de HTML, links executáveis, aspas na URL e Markdown literal dentro de código.
- `python -m unittest testes.testa_prompt_montagem`, no venv: 8 testes passaram,
  incluindo orientação visual apenas no canal web com prompt completo.
- Golden atualizado intencionalmente; diff incremental revisado. Voz, Telegram,
  Dark Souls e demais modos enxutos ficaram byte a byte iguais ao baseline.
- Prévia isolada aberta no Edge em 390 e 760 px. A tabela larga rola dentro do
  bloco, sem rolagem horizontal da página. A prévia usa renderer e CSS do projeto;
  não substitui uma inspeção da janela completa da Luna depois do reinício.

Snapshots, respostas completas, diff e prévia estão em
`logs/bancada_web/20261008-markdown-v2/`; a tentativa inicial foi preservada em
`logs/bancada_web/20261008-markdown/`. Esses arquivos ficam fora do Git.

Para experimentar na Luna, reinicie a instância e recarregue a página. Peça uma
comparação com atributos conhecidos, um procedimento ou um exemplo de código;
depois converse normalmente para julgar a apresentação no uso real.
