# HAL 9000 e identidade Luna — 16/10/2026

O nível 1 substitui a antiga persona LUNA por HAL 9000. O aplicativo e a assistente
continuam se chamando Luna. TARS permanece como padrão; a configuração pessoal
ativa não foi alterada pela bancada.

## Escopo

- Identidade, emoção, estrutura, limites, canal de texto e modos enxutos próprios do HAL.
- Removidos do caminho ativo o núcleo curto e exemplos de tom da antiga persona.
- Briefs reativos curtos do HAL não pedem mais uma amiga provocadora. Proativos
  recebem orientação explícita para preservar fatos com o registro HAL.
- GLaDOS passa a ser referência de estilo, não o nome da assistente. O perfil 0
  também recebe o nome Luna, sem ganhar uma personalidade adicional.

## Validação

Os 47 arquivos de testes JavaScript passaram. As verificações Python de montagem
e personalidade passaram antes da alteração. O golden do TARS foi preservado e
os 11 testes de montagem passaram depois. A fixture dos quatro perfis foi
atualizada pela mudança intencional: 44 montagens por perfil; nenhuma das 44 do
TARS mudou. Testes de identidade cobrem persona completa e núcleo curto em voz/texto.

Bancada real com Gemma-4-12B QAT no TurboLLM, seed 481, sem áudio nem execução
de ferramentas: oito respostas iniciais e uma repetição dirigida após ajuste.
As mensagens usam contexto sintético, sem depender da memória pessoal.

| Caso | Resultado observado |
|---|---|
| Nome nos quatro perfis | Todos responderam Luna. TARS e GLaDOS acrescentaram comentários longos; o HAL respondeu apenas o nome. |
| HAL, fazer café | Tom sereno, porém genérico e com menção desnecessária à produtividade. |
| HAL, compra de cinco jogos | Perguntou pelo jogo no singular; a mensagem entrou no tratamento de compra, sem produzir uma boa ironia sobre a contradição. |
| HAL, perda de animal | Acolheu sem sarcasmo; resposta mais longa e genérica do que o desejado. |
| HAL, correção de dia | Inicialmente alegou corrigir registros e perguntou pelo planejamento. Após reforçar o modo de correção: “Peço desculpas pelo equívoco; você disse terça-feira.” |

## Limites

Uma amostra por caso não mede consistência nem aprova humor. O nome Luna foi
confirmado nessas quatro gerações, não garantido para toda resposta possível.
O HAL está disponível para avaliação humana; ainda há espaço para tornar suas
observações menos genéricas. Não foram medidos voz, FPS, ferramentas reais ou
comentários durante uma partida. Os outros perfis não receberam ajustes de tom.
