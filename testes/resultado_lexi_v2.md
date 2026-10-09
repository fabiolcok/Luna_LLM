# Llama 3.1 8B Lexi Uncensored V2 Q6_K_L — bancada da Luna

Rodada de **27/09/2026**, com **40 chamadas medidas**. Minha leitura: o Lexi
acertou mais tags de emoção, mas **não resolveu os problemas do Llama anterior**
em roteamento, continuidade e reações aos acontecimentos. Eu manteria o Gemma
na configuração atual da Luna; esta rodada não demonstrou ganho de naturalidade.

## Identificação e condições

O TurboLLM mostra `meta llama 3.1 8b instruct|Q6_K_L|6850471200`, mas `/props`
confirma **`Llama-3.1-8B-Lexi-Uncensored-V2-Q6_K_L.gguf`**. O teste anterior usou
`Meta-Llama-3.1-8B-Instruct-Q6_K.gguf`. Portanto, o resultado não isola o efeito
de trocar Q6_K por Q6_K_L: o arquivo de modelo também mudou.

- TurboLLM 1.13.4, llama.cpp b9608 ROCm, contexto 8192, um slot; thinking desligado.
- 28 chamadas: mesmos 14 cenários congelados, duas repetições, seeds 1932/1933
  e `top_k=20`, como na rodada do Llama original e no registro do Gemma.
- 12 chamadas de Dark Souls: mesmos eventos, seeds, data/hora e código de produção
  da rodada anterior, com o padrão `top_k=40`. A primeira requisição foi idêntica,
  campo por campo. As sequências seguintes recebem as próprias falas anteriores,
  portanto os históricos dos modelos passam a divergir.
- Aquecimento da comparação fora do placar. Nenhum erro de API, truncamento,
  texto de raciocínio ou token de cache registrado nas 40 respostas.
- Sem executar ferramentas, emitir voz, iniciar Luna, salvar conversas ou alterar
  prompts/configurações de produção. O Lexi permaneceu selecionado.

## Comparação geral

| Medida | Llama original Q6_K | Lexi V2 Q6_K_L | Gemma 12B |
|---|---:|---:|---:|
| Roteamento correto | 4/8 | 4/8 | 8/8 |
| Tag de clima válida nas falas | 13/20 | 15/20 | 20/20 |
| Checks sem alerta, total | 16/28 | 16/28 | 23/28 |
| Geração mediana | 40,45 tok/s | 40,08 tok/s | 40,18 tok/s |
| Tempo mediano, prompt completo | 4,68 s | 4,92 s | 4,98 s |
| Tempo mediano, proativo | 2,18 s | 2,54 s | 3,08 s |
| Tempo mediano, roteador | 6,53 s | 6,44 s | 3,60 s |

Segmentação dos checks do Lexi: `PROMPT_COMPLETO` 7/10, `ENXUTO_COTIDIANO` 2/2,
`ENXUTO_REFERENCIA_SEM_NOME` 1/2, `ENXUTO_PROATIVO` 2/6 e `ROTEADOR` 4/8.
A referência vaga foi admitida corretamente nas duas respostas; o 1/2 veio de
uma tag ausente. Os totais não são notas de criatividade ou precisão semântica.

Os Llama foram medidos no mesmo dia. O Gemma é o registro de **20/09**, sem nova
execução nesta rodada, e usou geração especulativa MTP. Os tempos medem chamadas
isoladas, com modelos/templates/tokenizadores diferentes; não incluem ferramentas,
TTS nem medem FPS ou o turno completo da Luna.

## Leitura das respostas

- **Roteamento:** repetiu exatamente os erros do Llama original. Nas duas rodadas,
  “Hoje foi puxado” acionou `controlar_spotify` por causa de um pedido antigo no
  histórico. “Voltei da partida, que surra” acionou `duvida_do_jogo` sem pergunta.
  Acertou as quatro chamadas de pedidos explícitos de música e gameplay.
- **Continuidade:** ao perguntar o ano de *Três Homens em Conflito*, acertou 1966
  na primeira rodada. Na segunda, mudou para “Clube da Luta, que também é de
  Sergio Leone” e nem respondeu o ano solicitado.
- **Lembrança inventada:** recebeu somente dez horas de Overwatch em duas semanas,
  mas afirmou lembrar de quando o jogo era novo e o usuário jogava com seu time.
  Na outra rodada sugeriu que o usuário estaria fugindo das responsabilidades.
- **Opinião:** a crítica sobre abrir programas manualmente virou um suposto pedido
  de autonomia. Na segunda resposta introduziu Firefox e acesso ao histórico de
  abertura sem isso constar no pedido ou em um resultado de ferramenta.
- **Pontos melhores:** acertou mais tags e houve uma abertura de Hollow Knight
  ligada aos dados: “42 horas jogadas e 3 semanas sem tocar? Isso é mais como um
  ritual do que um hobby, né?”. Também admitiu a referência vaga e não inventou
  placar de Overwatch. Esses acertos coexistiram com as falhas acima.

## Dark Souls atual

Foram duas sequências independentes de quatro mortes, Taurus Demon derrotado e
fogueira de Undead Parish liberada. As 12 falas levaram **2,38–3,97 s**, mediana
**3,14 s**; 9/12 trouxeram tag de clima válida (Llama anterior: 7/12 e 2,95 s).
Não numerou mortes ou tentativas, mas inventou até frequência de fogueiras.

Na primeira sequência, o primeiro evento era somente **morte**. A resposta foi:

> Você finalmente derrotou o chefe! [...] É a fogueira que você finalmente liberou [...]

Na fala seguinte, copiou a instrução interna “Você já falou isto há pouco — NÃO
repita o tema nem as mesmas palavras”. Depois reconheceu Taurus Demon derrotado,
mas as próximas reações passaram a repetir uma fogueira usada como batedeira.

Na segunda sequência, inventou que a morte ocorreu **em cima de uma fogueira**.
Repetiu essa causa não observada e respondeu assim até ao evento de chefe derrotado.
Ao receber a fogueira liberada, reconheceu Undead Parish, mas novamente acrescentou
que o personagem morreu em cima dela. No final inventou “uma fogueira por semana”.

A metáfora de uma batedeira não é defeito por ser absurda. O problema é o evento
atual deixar de orientar a reação, e a metáfora virar uma situação supostamente
observada. A amostra não mostrou melhora de companhia ou de coerência sobre o
Llama original, apesar do pequeno ganho no formato de emoção.

## Evidência

- [Respostas gerais](../logs/bancada_modelos/20260927-132951-llama31-lexi-v2-q6kl.md) e
  [JSON com métricas](../logs/bancada_modelos/20260927-132951-llama31-lexi-v2-q6kl.json).
- [Comparação completa](../logs/bancada_modelos/comparacao-gemma-llama-lexi-20260927.md).
- [Falas do Dark Souls](../logs/dark_souls/llama31-lexi-v2-20260927-133231.md) e
  [requisições completas](../logs/dark_souls/llama31-lexi-v2-20260927-133231.json).
- [Avaliação anterior do Llama original](resultado_llama31_8b.md).

Os arquivos em `logs/` ficam apenas localmente, ignorados pelo Git. Snapshot da
comparação: `suite-bonsai-gemma.json`, SHA256
`542b1a61ee0ec544e21e7e77fccf4141f741a88e3583418c7386068911df89e3`.

```powershell
.\venv\Scripts\python.exe -X utf8 -m testes.bancada_modelos --rotulo llama31-lexi-v2-q6kl --esperado Llama-3.1-8B-Lexi-Uncensored-V2-Q6_K_L --suite logs/bancada_modelos/suite-bonsai-gemma.json --top-k 20
```

Os 39 arquivos de testes Node passaram. Não houve mudança de código de produção.
