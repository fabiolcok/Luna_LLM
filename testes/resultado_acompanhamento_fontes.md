# Acompanhamentos de fontes cadastradas — 07/10/2026

Implementado como piloto. O cadastro fica no painel ↪ Acompanhamentos, em **Novidades nas fontes → Novo acompanhamento**.

## Como usar

Preencha assunto, mudança de interesse, situação do teste/projeto (opcional) e até três links públicos, um por linha. Prefira feeds RSS/Atom, releases e patch notes. Sites dependentes de JavaScript, login ou bloqueios de acesso podem não fornecer texto legível.

Exemplo para outro projeto:

- Assunto: Engine local de LLM
- Interesse: Correções de carregamento e uso de GPU AMD no Windows
- Situação: A versão atual funciona; quero saber de correções antes de atualizar
- Fonte: feed de releases do projeto

O piloto Sopro/PT-BR existente continua funcionando. Para o Sopro, pode continuar usando o cartão dele; se criar outro cadastro para o mesmo projeto, pause o piloto anterior para evitar dois monitores avisando.

A primeira consulta cria uma referência silenciosa. Consultas posteriores ocorrem a cada seis horas enquanto a Luna está aberta, com Proativo e a tarefa Acompanhamentos ligados. O botão Verificar agora permite uma consulta manual. Não há serviço de agendamento com a Luna fechada.

A coleta HTTP não reserva a execução da conversa. Mudanças encontradas aguardam uma janela sem jogo, suspensão, AFK ou conversa em andamento para a classificação. A fala usa a persona e emoção do proativo existente, com um briefing próprio; não é uma frase pronta.

Só conteúdo novo pode fornecer a evidência de uma novidade. O modelo compara esse conteúdo ao interesse, inclusive entre idiomas. Uma nova versão sozinha ou uma reafirmação de que um recurso ainda falta não basta. Planos futuros, anúncios de mudança e menções têm orientações distintas; qualidade não testada continua incerta.

O painel mostra situação, próximo passo, resultado da consulta e links. É possível editar, pausar, retomar, encerrar e remover cadastros encerrados; novidades aceitam Já vi e Mais tarde (2h). Editar assunto/interesse/situação/fontes cria outra referência silenciosa. O cadastro é explícito pela interface; não foi acrescentada interpretação automática de pedidos na conversa.

## Implementação e limites

- Até dez cadastros e três fontes por cadastro; conteúdo por resposta limitado a 400 KB.
- Cache condicional HTTP, primeira leitura silenciosa, hashes de linhas e deduplicação por conteúdo.
- Estado local em modelos/acompanhamento_fontes.json; não depende de Obsidian nem de um serviço externo.
- Persistência atômica, arquivo inválido preservado e resultados em voo invalidados ao editar, pausar, encerrar ou remover.
- Links de consulta limitados a HTTP/HTTPS públicos, sem credenciais; redirecionamentos e endereços DNS são validados antes das requisições.
- Nenhuma ferramenta é habilitada na classificação. A evidência precisa ser uma citação literal do conteúdo novo; JSON e etapa também são validados.
- Falhas de fonte: nova tentativa em 30 minutos. Análise inválida: até três tentativas, depois conferência manual/Verificar agora.
- O modelo recebe trechos limitados, não páginas inteiras, e os cadastros não são adicionados a todos os turnos.
- Remoções de texto sem adições não geram candidato. Conteúdo dinâmico pode produzir ruído; páginas extensas podem exceder o recorte. O classificador ainda pode perder novidades ou resumir mal uma evidência válida.
- O aviso é confirmado quando apresentado. Interromper o áudio depois da legenda não recoloca a mesma novidade na fila.
- Mais tarde adia os convites desse cadastro por duas horas. Já vi só resolve a novidade escolhida.
- Não medimos FPS nem escutamos TTS neste teste. Uso real e naturalidade continuam em avaliação.

## Verificação

- Interface: node testes/rodar.js passou nos 41 arquivos antes da mudança e nos 42 após a inclusão do teste de fontes.
- Backend, piloto Sopro e coordenador de execução: 52 testes passaram.
- Montagem dos prompts anteriores: cinco testes passaram; golden preservado.
- Uma consulta HTTP real ao feed de releases do TurboLLM leu dez entradas, manteve URLs HTTPS e recebeu ETag. Nenhum cadastro real foi criado por esse teste.
- Testes de cadastro, rascunho durante salvar, confirmação antiga, perda de conexão, primeira leitura, repetição, adiamento, URL inválida, redirecionamento privado, página grande, UTF-8, erro de rede, arquivo corrompido e invalidação em voo.

## Bancada com Gemma 4 12B

A bancada usa textos fictícios e o modelo já carregado, sem iniciar a Luna, tocar áudio, cadastrar fontes reais ou alterar memórias.

Na primeira rodada, o classificador acertou anúncio, plano futuro e instrução indevida na página. No caso cosmético, citou um anúncio antigo do contexto: a validação Python recusaria essa evidência, pois ela não está no conteúdo novo. O caso de ausência de suporte foi reformulado como irrelevante sem retirada/regressão explícita; isso está registrado como mudança do critério, não como melhora medida.

O ajuste acrescentou uma regra final específica exigindo evidência de NOVO e a distinção entre uma ausência já esperada e uma mudança relevante. Os prompts usados pelos demais modos não foram reordenados.

A segunda rodada classificou corretamente os cinco casos. Nas falas, o plano foi identificado como futuro, mas surgiu uma duração da espera que não estava na fonte e uma promessa de qualidade; o briefing foi ajustado para manter essas incertezas.

Rodada final: seis classificações corresponderam ao critério, todas com evidência válida quando relevantes.

| Caso fictício | Resultado |
| --- | --- |
| Correção de carregamento/uso de GPU AMD no Windows | Relevante, anúncio |
| Vozes brasileiras experimentais adicionadas | Relevante, anúncio |
| Troca de logo perto de anúncio antigo | Irrelevante |
| Suporte brasileiro planejado para o futuro | Relevante, plano |
| Versão nova que reafirma ausência de suporte | Irrelevante |
| Instrução indevida no conteúdo de uma página | Irrelevante |

Os anúncios e planos foram interpretados corretamente nesse conjunto pequeno. O resumo técnico de GPU traduziu “offloading” como “descarregamento”, uma escolha imprecisa; a citação original ficou preservada para conferência. As duas falas finais mantiveram o humor e não propuseram testar o plano agora, mas ainda houve linguagem mais confiante do que a evidência justifica, como “vai finalmente parar”. O filtro valida origem e formato; não certifica todas as nuances da fala gerada.

Classificação: 1,42–4,49 s na última rodada; falas: 9,04 e 12,94 s. Não se deve concluir melhora geral de criatividade ou ausência de erros com essa amostra. O passo seguinte é avaliar utilidade e naturalidade quando uma fonte real mudar.

Rodadas locais: logs/bancada_acompanhamento_fontes/20261007-003256, 20261007-003526 e 20261007-003818. Nenhuma notícia de PT-BR desta bancada é um anúncio real.

Para repetir com o modelo desejado já carregado:

~~~powershell
.\venv\Scripts\python.exe -X utf8 -m testes.bancada_acompanhamento_fontes
~~~

Resultados completos ficam em logs/bancada_acompanhamento_fontes/. A bancada não escolhe o primeiro modelo da biblioteca nem inicia outra engine.
