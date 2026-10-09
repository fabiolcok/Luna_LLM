# Conversa sobre jogos e resultado de pesquisa

Data: 08/10/2026.

O comentário sobre craft e extração no Aion estava entrando em `duvida_do_jogo` sem pedir uma pesquisa. O filtro aceitava o `como` de `conta como skill` como evidência de pergunta. Além disso, o retorno de uma pesquisa concluída começava com `SISTEMA:`, prefixo que a montagem da persona interpretava como falha.

## O que foi corrigido

- O trecho literal precisa pertencer a uma oração de pedido na mensagem original. Recortar `como skill` de uma declaração não fabrica uma pergunta. Pedidos sem `?`, pedidos indiretos e continuação de uma dúvida anterior têm regressões próprias.
- `duvida_do_jogo` distingue pesquisa concluída, falta de material sobre o jogo, erro de acesso e jogo não identificado. A ausência de material não vira falha de conexão; não identificar o jogo não permite alegar uma pesquisa.
- A persona recebe o estado da consulta separadamente dos dados. Quando menciona a busca, pode falar em primeira pessoa, como `dei uma olhada` ou `tentei conferir`, sem presumir que o usuário pediu uma pesquisa.
- O sucesso da consulta deixa de cair na instrução genérica `A ferramenta FALHOU`. As métricas reconhecem erro de acesso e ausência de contexto como falha.

Nenhuma alteração na EMOCAO, no proativo ou na ordem dos blocos centrais. O comentário vetado segue pelo caminho normal de conversa, sem resultado de pesquisa. Não há frases prontas substituindo a geração.

## Bancada real

Modelo: Gemma 4 12B QAT/Q4_0, engine `llama.cpp b9608 (rocm)`. A identidade do modelo, engine e configuração foi conferida antes de cada chamada. Thinking desligado.

Cinco situações independentes, duas seeds e histórico fixo: comentário, pergunta com dados úteis, pergunta sobre um motivo que os dados não explicam, busca vazia e erro de acesso. Perfil, memória e pesquisa são fixtures; não há acesso à memória real, pesquisa externa, reprodução de voz ou medição de FPS.

**A mecânica de coleta usada na fixture é inventada. Os resultados não validam o funcionamento do AION 2 real.**

A rodada inicial fez 20 gerações de persona em A/B intercalado e seis de roteador. Quatro rodadas exploratórias posteriores fizeram dez gerações cada. Total: 66 gerações reais, todas encerradas com `stop` ou `tool_calls`, sem corte pelo teto de tokens. O processo do engine reiniciou entre rodadas; arquivo do modelo, engine e parâmetros permaneceram iguais. A identidade foi estável dentro de cada rodada.

Separação dos resultados: a versão entregue usa `PROMPT_COMPLETO + EMOCAO` nos cinco cenários. Roteamento e fidelidade da persona foram examinados separadamente. A variante que substituía a persona por um núcleo curto com EMOCAO foi descartada: aumentou as extrapolações.

## Leitura manual da versão entregue

| Situação | Resultado observado |
| --- | --- |
| Comentário sobre Aion | O roteador não chamou ferramenta em 2/2 amostras. O teste de despacho também força uma chamada errada e confirma que o Python bloqueia a pesquisa. A persona ainda inventou explicações sobre simplificação em 2/2 falas. |
| Pergunta com dados úteis | 2/2 respostas preservaram os fatos sintéticos de aproximação, ativação de Coleta e consumo de um ponto de energia. Nenhuma tratou a consulta como falha. |
| Motivo não explicado pelos dados | 2/2 reconheceram que não conseguiram confirmar o motivo. Uma também levantou hipóteses sobre preguiça dos desenvolvedores e facilidade, sem evidência. |
| Busca vazia | 2/2 disseram em primeira pessoa que não encontraram informação concreta. Uma acrescentou uma provocação ao usuário sem apoio no contexto. |
| Erro de acesso | 2/2 disseram que não conseguiram acessar ou obter a informação, sem inventar o funcionamento da mecânica. A causa específica de conexão nem sempre apareceu na fala, embora esteja no retorno da ferramenta. |

Exemplo gerado na consulta com **dados fictícios**:

> Dei uma olhada aqui e o que eu consegui confirmar é que você precisa se aproximar do recurso e ativar a "Coleta", mas cada ação consome um ponto de energia.

A mudança de abertura funcionou nas amostras da consulta. Já impedir premissas inventadas no comentário espontâneo **não ficou resolvido**. Foram experimentadas orientações locais, exemplo de curiosidade, orientação no fim do sistema e núcleo curto com EMOCAO; nenhuma mostrou melhora consistente suficiente para substituir o caminho normal de conversa. Esses experimentos não ficaram na produção.

O resultado sustenta as correções do fluxo e a apresentação mais natural da consulta. Não sustenta afirmar que a criatividade ou a fidelidade factual da persona inteira foi corrigida. Duas amostras por situação não medem confiabilidade de uso prolongado.

## Verificação

- 23 testes Python: intenção, despacho real com roteador simulado, estados da consulta e montagem de prompt.
- `node testes/rodar.js`: 42 arquivos passaram.
- Golden: 28 ramos anteriores idênticos ao snapshot feito antes deste trabalho; quatro ramos de pesquisa acrescentados intencionalmente. EMOCAO e perfil continuam presentes.
- O golden gerado mantém os espaços finais de `Conversas anteriores: `, já existentes no formato anterior; `git diff --check` sinaliza essas linhas.

Artefatos locais em `logs/bancada_duvida_jogo/20261008-aion/`. A versão entregue conserva os pedidos de persona já medidos: comentário da rodada `depois`; demais situações da rodada `selecionado`. A equivalência dos pedidos completos foi verificada antes de reutilizar essas observações. Os resultados anteriores e os candidatos descartados foram preservados para auditoria.

Para executar uma nova rodada da versão atual, com o Gemma carregado:

```powershell
.\venv\Scripts\python.exe -X utf8 -m testes.bancada_duvida_jogo logs/bancada_duvida_jogo/NOVA_RODADA --preparar entrega
.\venv\Scripts\python.exe -X utf8 -m testes.bancada_duvida_jogo logs/bancada_duvida_jogo/NOVA_RODADA --rodada entrega
```

Reiniciar a Luna é necessário para carregar as alterações dos módulos.
