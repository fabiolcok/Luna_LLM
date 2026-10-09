# Dark Souls — thinking ligado versus desligado

Rodada de 24/09/2026. **Nesta amostra, ligar thinking não trouxe um ganho convincente
de criatividade.** As falas continuaram repetindo catástrofes e destruição, a geração
ficou muito mais demorada e três chamadas esgotaram o orçamento sem resposta final.
A configuração de uso da Luna permanece com thinking desligado.

## Resultado medido

| Medida | Desligado | Ligado |
|---|---:|---:|
| Chamadas | 8 | 8 |
| Falas finais produzidas | 8 | 5 |
| Sem fala, limite de tokens atingido | 0 | 3 |
| Mediana da geração completa | 2,9 s | 58,7 s |
| Menor / maior tempo | 2,5 / 6,6 s | 39,6 / 71,7 s |
| Gerações acima dos 30 s do evento de morte | 0 | 8 |
| Total de tokens gerados, incluindo raciocínio | 407 | 19.432 |
| Números de mortes corretos nas falas produzidas, conferidos manualmente | 6/8 | 5/5 |

O modo ligado devolveu raciocínio em todas as oito chamadas; o parâmetro não foi
simplesmente ignorado pela engine. Os tempos acima **não incluem TTS**. Nesta rodada,
todas as chamadas com thinking já ultrapassariam a validade da morte antes da voz.
No modo desligado, ficar abaixo desse tempo não garante entrega: foco, leitura e
prioridade da conversa continuam sendo verificados pelo piloto.

## Leitura das falas

Esta avaliação é manual; os testes automáticos não dão nota de graça ou criatividade.

Com thinking, as duas primeiras falas giraram em torno de colapso estrutural e
sedimentos geológicos. Depois, a mesma estrutura voltou quase inteira:

> Quinta morte: “Chegar na quinta morte é uma tragédia de proporções geológicas que
> já deveria ter sido catalogada como um desastre de impacto permanente.”

> Sexta morte: “Essa sexta morte é uma catástrofe de proporções astronômicas que já
> deveria ter sido catalogada como um evento de extinção em massa.”

A oitava mudou para “selo de certificação para persistência nível industrial”,
mas não houve variedade consistente na sequência. As mortes 3, 4 e 7 consumiram os
3.000 tokens sem fala final; criatividade não pode ser avaliada nesses três casos.

Sem thinking, também houve repetição: as mortes 3 e 4 usaram “obra de arte abstrata”.
A quinta trouxe a imagem de equilibrar pratos sobre gelo com luvas de boxe, mas
a sexta voltou a “evento geológico”. Portanto, manter desligado não resolve o
problema de estilo que motivou o teste.

Houve um benefício limitado do thinking: todas as cinco falas produzidas citaram
o total correto. No modo desligado, o pedido continha `mortes_sessao: 2` e a resposta
disse “três”; depois recebeu 3 e disse “quarta”. **Nesses casos da bancada, o erro
foi na fala gerada, não no contador Python.** Isso não determina retroativamente
qual foi a causa dos números inconsistentes no log da jogatina.

## Como foi feito

- Modelo: `gemma-4-12B-it-QAT-Q4_0.gguf`, da biblioteca já carregada.
- TurboLLM 1.13.4; engine `llama.cpp b9608 (rocm)`; contexto 8192; um slot.
  Identidade conferida antes e depois de cada geração. A engine estava com MTP ativo.
- Oito eventos sintéticos por modo: totais 1 a 8, cada um com incremento 1.
  Perfil sintético: “Gosta de jogos e humor exagerado.”
- Todas as chamadas passaram por `ENXUTO_PROATIVO + EMOCAO`; não há comparação
  com `PROMPT_COMPLETO` ou outro modelo.
- Montagem real de `pensar.py`, instrução de `prompts.py`, preparação/antirrepetição
  de `proativa.py` e limpeza de voz. Sem inicializar áudio, Telegram ou outra Luna.
- Mesma data/hora no prompt, mesmos eventos e seed por par (43 a 50). Temperatura
  0,8; penalidades de presença e frequência 0,3; demais ajustes da engine preservados.
- A ordem alterna: desligado/ligado na primeira morte, ligado/desligado na segunda,
  e assim por diante. `cache_prompt=False`; a engine registrou zero tokens de cache.
- Cada modo guarda suas próprias últimas falas: três trechos de até 120 caracteres,
  como na produção. Os históricos divergem após a primeira resposta. Não é uma
  comparação de prompts byte a byte idênticos em todos os turnos posteriores.
- O teto reproduz a configuração atual: 180 tokens desligado, 3000 ligado, incluindo
  raciocínio. Testa o efeito de usar o toggle disponível, sem isolar o orçamento como
  variável independente. Não foram testados outros limites de raciocínio.
- O processo do Dark Souls estava aberto durante a rodada. Não houve controle de
  carga da máquina, medição de FPS ou reprodução automática de mortes reais.

## Decisão e próximo experimento

Manter thinking desligado para esse piloto por enquanto. Mesmo desconsiderando a
demora, as cinco respostas finais não mostraram a melhora de humor procurada.
Uma sequência curta não prova que thinking nunca ajuda, nem permite concluir que
o modelo atingiu seu limite em qualquer prompt.

Há uma hipótese concreta para outro teste: o bloco EMOCAO pede imagem física e
“tratar o pequeno como catástrofe”. Isso pode contribuir para a insistência em
destruição. Testar abordagens diferentes **só no briefing do piloto**, preservando
os exageros, permitiria avaliar essa hipótese. Os prompts de produção não foram
alterados nesta rodada.

## Reproduzir e conferir

```powershell
.\venv\Scripts\python.exe -X utf8 -m testes.bancada_dark_souls_thinking --mortes 8
```

Dados locais desta rodada:

- [Todas as falas e tempos](../logs/dark_souls/thinking-20260924-202827.md).
- [Pedidos, respostas e métricas originais](../logs/dark_souls/thinking-20260924-202827.json).

Esses arquivos em `logs/` são locais e ignorados pelo Git. A bancada salva cada
resposta antes de continuar e marca `concluido: true` ao terminar. Os testes com
respostas simuladas confirmam igualdade das entradas iniciais, separação dos
históricos, preservação das opções de geração e limpeza das tags de clima.

Validação: 32 testes Python da bancada e do piloto passaram; 39 arquivos de testes
da interface passaram. Nenhuma configuração persistente de modelo/thinking foi alterada.
