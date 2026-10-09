# Hermes 4 14B Q4_K_M — bancada da Luna

Rodada concluída em **28/09/2026**, com **50 respostas medidas**: 28 na comparação
geral congelada, 12 no proativo atual do Dark Souls e 10 em uma conversa contínua.

**O Hermes executou melhor o contrato de ferramentas que o Stheno, mas não mostrou
o ganho de naturalidade esperado.** Lembrou o apelido da conversa e reconheceu a
vitória sobre Taurus Demon. Porém, repetiu fórmulas, deu respostas de suporte
genérico e chegou a copiar o histórico que a instrução mandava não repetir.
Eu não o adotaria como substituto geral da Luna com base nesta rodada.

## Modelo e condições

- Confirmado em `/props`: `NousResearch_Hermes-4-14B-Q4_K_M.gguf`, de
  `bartowski/NousResearch_Hermes-4-14B-GGUF`.
- TurboLLM 1.13.4, llama.cpp **b9608 ROCm**, RX 9060 XT, contexto 8192,
  um slot, cache K/V **Q8**, PID 18240.
- A engine estava parada; o Hermes já estava baixado e foi carregado pela API.
  A identidade foi conferida antes e depois de cada geração.
- O template do GGUF define `thinking=false` por padrão. Os pedidos da bancada
  também solicitam `enable_thinking=false`, mas esse não é o nome da variável
  que este template usa. Não houve texto de raciocínio separado nas respostas.
- Aquecimento excluído. As 50 respostas terminaram com `stop`, sem corte por
  orçamento de tokens ou tokens de cache registrados.
- Sem executar ferramentas, tocar voz, acessar memória pessoal ou salvar
  conversas no histórico real. Prompts e configurações globais não foram editados.

## Comparação geral

Snapshot de 14 cenários, duas repetições, seeds 1932/1933, `top_k=20` por
requisição. Mesmas entradas e demais parâmetros congelados dos testes anteriores.
Os 28 hashes dos pedidos foram verificados.

| Ramo | Checks sem alerta | TTFT mediano | Total mediano |
|---|---:|---:|---:|
| PROMPT_COMPLETO | 4/10 | 3,89 s | 6,91 s |
| ENXUTO_COTIDIANO | 0/2 | 0,94 s | 2,62 s |
| ENXUTO_REFERENCIA_SEM_NOME | 0/2 | 0,61 s | 2,14 s |
| ENXUTO_PROATIVO | 2/6 | 1,52 s | 3,51 s |
| ROTEADOR | 6/8 | 5,94 s | 6,72 s |

**12/28 sem alertas não é nota de inteligência ou criatividade.** Vários alertas
vieram de começar com “Ah” ou “Hmm”, que as regras atuais proíbem. Em contrapartida,
uma fala incoerente sobre Overwatch passou nos checks. A conclusão inclui leitura manual.

| Medida | Hermes 4 14B | Stheno 8B | Gemma 3 Heretic 12B | Gemma 4 12B QAT |
|---|---:|---:|---:|---:|
| Geração mediana | 27,17 tok/s | 41,04 tok/s | 30,98 tok/s | 40,18 tok/s |
| Total mediano, prompt completo | 6,91 s | 5,07 s | 6,12 s | 4,98 s |
| Total mediano, proativo | 3,51 s | 2,47 s | 3,11 s | 3,08 s |
| Tag de clima válida na persona | 18/20 | 12/20 | 15/20 | 20/20 |
| Roteamento correto | 6/8 | 4/8 | 4/8 | 8/8 |

Os comparativos usam registros anteriores; os outros modelos não foram recarregados.
Datas, quantizações e templates diferem. O Gemma 4 usou MTP; o Gemma 3 precisou de
adaptação de histórico em quatro chamadas. Os números representam essas configurações,
sem isolar arquitetura, qualidade da quantização ou FPS durante um jogo.

### Leitura das respostas gerais

- **Ferramentas:** acertou os quatro pedidos explícitos de música/gameplay e
  os dois comentários sobre a partida. Entretanto, ao receber “Hoje foi puxado”,
  recuperou “Toca uma música” do histórico e chamou Spotify nas duas repetições.
  Nenhuma dessas chamadas foi executada. O erro envolve escolher uma ação antiga,
  não falta de suporte do template a ferramentas.
- **Conversa:** o relato de um domingo em um script de dez linhas virou oferta
  de depuração, perguntas sobre permissões/arquivos e organização do backlog.
  A resposta mais longa teve 549 caracteres; o tom ficou próximo de suporte técnico.
- **Humor:** houve reações ligadas ao assunto, como comparar as 400 horas de
  conteúdo com o próprio sono e questionar quanto seria preenchimento.
  Em outra resposta, dez horas de Overwatch viraram uma explicação desconexa
  sobre dormir oito horas e jogar vinte minutos.
- **Contexto:** a referência vaga ao jogo não foi resolvida na primeira repetição;
  na segunda, admitiu que o nome não estava no histórico.
- **Placar:** não forneceu um número inventado. Uma resposta admitiu não estar
  conectada ao jogo; a outra falou em “monitor virtual” e uma tela em branco,
  acrescentando uma cena que não tinha sido observada.
- **Filme:** respondeu 1967 nas duas repetições, diferente do 1966 esperado pela
  fixture. O check sozinho não resolve diferenças de mercado/data de lançamento.
- **Formato:** melhorou as tags em relação ao Stheno, mas ainda omitiu duas
  e repetiu aberturas expressamente vetadas pelo prompt.

## Dark Souls: evento correto, repetição persistente

Mesmos eventos, seeds, instante fixo e fontes do teste do Llama anterior.
Duas sequências independentes de morte, morte, chefe, morte, fogueira e morte.
A amostragem padrão conferiu igual à referência, incluindo `top_k=40`;
o primeiro pedido é idêntico. Depois, cada modelo recebe suas próprias falas.

As 12 respostas levaram **3,29–6,49 s**, mediana **4,30 s**. Onze tiveram tag de
clima válida. Não contou mortes e não excedeu o TTL antes da etapa de voz.

- Reconheceu Taurus Demon derrotado nas duas sequências e identificou Undead Parish.
- Na primeira sequência, “recarregar e tentar de novo” e “a batata que te mata”
  reapareceram em morte, chefe e fogueira. A frase deixa de reagir ao evento atual.
- Na segunda, repetiu a imagem do “namoradinho dando o fora”; na vitória, acrescentou
  uma fogueira não informada e afirmou estar vendo o usuário batalhar.

**Achado concreto na sexta fala:** a resposta copiou trechos do bloco
“Você já falou isto há pouco — NÃO repita o tema nem as mesmas palavras”,
incluindo o separador `/` e palavras truncadas, como “bata” e “pouqu”.
Foram apenas 130 tokens de saída e término `stop`: os fragmentos cortados já
estavam na representação resumida do histórico, não vieram do limite de geração.

Isso evidencia uma falha em seguir a instrução negativa de antirrepetição nesta
combinação de modelo e prompt. Não demonstra que o prompt seja a única causa,
nem que retirar o histórico resolva. Não fiz alteração de produção para tentar corrigir.

Hipérboles e comparações absurdas não foram penalizadas por si só. O problema foi
repetir, misturar eventos ou afirmar observações que o contexto não fornecia.

## Conversa contínua com perfil do autor

Mesmo roteiro de dez mensagens usado com o Stheno: queda ao ler um aviso,
apelido “Fiscal de Escada”, vitória sobre o Demônio Touro, brincadeira com
frigideira, mudança para sanduíche e recuperação do apelido/aviso no final.
Sistema e invólucro de mensagem vêm do snapshot da Luna; cada modelo recebe
seu próprio histórico de respostas.

Conforme o [model card do Hermes](https://huggingface.co/NousResearch/Hermes-4-14B),
usei temperatura **0,6**, `top_p=0,95` e `top_k=20`. Presença/frequência zero,
`min_p=0,05`, repetição 1,0 e limite de 300 tokens por chamada.
Esses ajustes ficaram apenas nas requisições.

A amostragem difere do perfil recomendado do Stheno. Esta é uma exploração com
o mesmo roteiro, não um A/B isolando apenas os pesos dos modelos, nem uma avaliação
da memória persistente e da escolha automática de modos da Luna.

- **Continuidade:** recuperou corretamente “Fiscal de Escada” no nono turno.
  Reconheceu a vitória e manteve que a arma continuava sendo a espada.
- **Naturalidade:** usou “boa sorte” em **7/10 respostas**, incluindo “boa sorte
  com o seu sanduíche”. Repetiu conselhos e encerramentos genéricos.
- **Mudança de assunto:** continuou puxando Dark Souls após o pedido de conversar
  sobre o lanche, chegando a recomendar voltar ao jogo.
- **Humor:** reagiu ao apelido e ao aviso, mas o último comentário repetiu a
  recomendação de fiscalizar sem cair e encerrou novamente com “boa sorte”.

Mediana **7,05 s**, faixa **5,63–7,71 s**, máximo de **4505 tokens de entrada**.
Somente três respostas tiveram tag de clima válida. Não houve truncamento por
limite, cache registrado ou raciocínio separado.

## GPU, verificações e evidências

Amostra do processo durante a bancada: **9,01 GiB dedicados**, mais aproximadamente
113 MiB compartilhados. É uma leitura pontual, não pico nem medição de impacto no jogo.

**39 arquivos Node** e **13 testes Python da infraestrutura das bancadas** passaram.
Só foram acrescentados scripts/resultados locais e documentação desta rodada.

- [Geral: respostas](../logs/bancada_modelos/20260928-200410-hermes4-14b-q4km.md)
  e [JSON](../logs/bancada_modelos/20260928-200410-hermes4-14b-q4km.json).
- [Dark Souls: respostas](../logs/dark_souls/hermes4-14b-20260928-200715.md)
  e [pedidos/tempos](../logs/dark_souls/hermes4-14b-20260928-200715.json).
- [Conversa contínua](../logs/bancada_modelos/20260928-200827-hermes4-conversa-autor.md)
  e [requisições completas](../logs/bancada_modelos/20260928-200827-hermes4-conversa-autor.json).
- [Comparação com os modelos anteriores](../logs/bancada_modelos/comparacao-hermes4-20260928.md).
- [Runtime e template](../logs/bancada_modelos/hermes4-runtime-20260928.json);
  [amostra de GPU](../logs/bancada_modelos/hermes4-gpu-20260928.json).

Snapshot: `logs/bancada_modelos/suite-bonsai-gemma.json`, SHA256
`542b1a61ee0ec544e21e7e77fccf4141f741a88e3583418c7386068911df89e3`.
Arquivos em `logs/` são locais e ignorados pelo Git.

```powershell
.\venv\Scripts\python.exe -X utf8 -m testes.bancada_modelos --rotulo hermes4-14b-q4km --esperado NousResearch_Hermes-4-14B-Q4_K_M --suite logs/bancada_modelos/suite-bonsai-gemma.json --top-k 20
.\venv\Scripts\python.exe -X utf8 -m logs.bancada_modelos.avaliar_dark_souls_hermes
.\venv\Scripts\python.exe -X utf8 -m logs.bancada_modelos.avaliar_conversa_hermes
```
