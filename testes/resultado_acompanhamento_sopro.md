# Piloto de acompanhamento Sopro/PT-BR

Implementado em 05/10/2026. Este piloto reúne estado visível, consulta dirigida às
fontes e convite contextual no proativo. Kokoro continua sendo a voz da Luna.

## Como usar

Reinicie a Luna e atualize o modo web. Abra **Acompanhando: Sopro**, acima da entrada.
O painel mostra onde o teste parou, próximo passo, resultado da última consulta e fontes.

- **Salvar situação** corrige o registro do teste, sem editar memória nem agenda.
- **Verificar agora** consulta as fontes em uma thread de HTTP.
- **Pausar**, **Retomar** e **Encerrar** controlam o piloto.
- Na novidade, **Mais tarde (2h)** adia o convite e **Já vi** evita outro aviso daquele item.
- Pelo chat ou voz no PC: “acompanha o Sopro”, “pausa o Sopro”,
  “verifica o Sopro” e “cancela o acompanhamento do Sopro”.
- Para adiar pelo chat, mencione o assunto: “Sopro mais tarde”.
  “Mais tarde” solto continua pertencendo à conversa normal.

O acompanhamento começa ativo porque o piloto foi solicitado explicitamente.
Consultas automáticas precisam de Luna aberta, Proativo e Acompanhamentos ligados.
O botão de consulta manual serve para uma verificação explícita.
Sem rede, o painel mostra consulta incompleta e tenta novamente após 30 minutos.

## Fontes e regras

Fontes fixas, públicas e sem credenciais:

- [Documentação do Sopro](https://github.com/samuel-vitorino/sopro).
- [Releases do Sopro](https://github.com/samuel-vitorino/sopro/releases).
- [Card do sopro-v2-turbo](https://huggingface.co/samuel-vitorino/sopro-v2-turbo).

A coleta ocorre a cada seis horas, usa ETag/Last-Modified e não chama LLM, baixa
modelo nem captura tela. A primeira leitura de cada fonte cria uma referência
silenciosa; recuperar uma fonte antes indisponível também semeia seu histórico.

Versão nova, idioma `pt` e PT-PT sozinhos não geram aviso. O detector procura
menções explícitas a PT-BR/português brasileiro. Ausência explícita de suporte
é ignorada. Menção nova guarda trecho e endereço reais, com deduplicação entre fontes.

O briefing distingue plano futuro, anúncio de recurso adicionado e menção sem
alcance confirmado. Nenhum deles comprova que o sotaque ficou bom.
A voz é gerada pela persona existente com EMOCAO; não é uma frase pronta em Python.
Os endereços são dados estruturados do web e não entram no TTS.

A consulta pode ocorrer durante um jogo. O convite espera a disponibilidade
prevista no proativo, fora de jogos e após o período inicial da sessão.
Abrir um jogo durante a geração também invalida a entrega. Conversa do usuário
mantém prioridade pelo coordenador existente.

Publicação da legenda ou início da voz confirma a apresentação. Cortar o áudio
depois disso não recria a novidade. Se a geração perder a janela antes de publicar,
o item continua pendente. “Mais tarde” permite um novo convite após o adiamento.

Estado: `modelos/acompanhamento_sopro.json`, separado de assuntos, memória e agenda.

## Validação de 05/10

- Primeira consulta real: três fontes consultadas sem erro, nenhuma novidade
  apresentada. Referência em `logs/piloto_sopro_20261005/fontes.json`.
- **52 testes Python** do piloto, acompanhamentos existentes, prioridade de execução
  e radar após interrupção passaram.
- **40 arquivos Node**, incluindo carga do script inteiro e o novo painel, passaram.
- Os modos existentes passaram no teste de golden; o piloto não regravou
  `testes/prompt_golden.txt`.
- Testes do painel cobrem texto externo, links inválidos, ações identificadas,
  consulta em andamento e preservação de rascunho, inclusive quando o campo é apagado.
- Testes do backend cobrem pausa durante HTTP, falha parcial, 304, limite de resposta,
  histórico inicial, deduplicação, adiamento, WebSocket e abertura de jogo durante geração.

## Bancada de texto

Somente o novo segmento proativo foi avaliado: dois cenários fictícios, em três
rodadas, com Gemma 4 12B Q4_0 e thinking desligado. Núcleo ENXUTO_PROATIVO + EMOCAO,
sem memória, conversa anterior ou áudio. É uma avaliação isolada do briefing;
não mede FPS nem a entrega completa em uma sessão real.

Primeira rodada (`logs/bancada_acompanhamento_sopro/20261005-100126/`):
o plano futuro pediu que o usuário avisasse quando saísse; o anúncio de recurso
experimental foi tratado como ainda não funcional. Briefing ajustado.

Segunda rodada (`logs/bancada_acompanhamento_sopro/20261005-100622/`):
o anúncio passou a propor verificar a opção experimental. O plano ainda sugeriu
comparar antes de o recurso sair. As duas respostas inventaram críticas à
respiração, que tinha sido um ponto positivo no teste. Regras reforçadas junto
ao registro da avaliação e ao próximo passo.

Rodada final (`logs/bancada_acompanhamento_sopro/20261005-101112/`):

| Cenário | Tempo total | Leitura manual |
|---|---:|---|
| Plano futuro | 19,72 s | Preservou voz/respiração como pontos positivos e não convidou a testar imediatamente. |
| Opção experimental anunciada | 15,49 s | Propôs conferir disponibilidade e comparar, sem afirmar sotaque resolvido. |

Exemplo final para o recurso experimental, com fonte **fictícia**:

> O Sopro finalmente admitiu que o PT-BR existe, mas como a fonte diz que a qualidade
> do sotaque ainda precisa de avaliação, a gente não pode fingir que o problema do
> PT-PT foi resolvido por mágica. Vamos conferir se essa opção experimental já está
> liberada pra gente testar e ver se ela ainda soa como um turista perdido ou se
> finalmente dá pra ouvir algo decente comparando com a Kokoro.

O modelo ainda repetiu “finalmente admitiu que o PT-BR existe” nos dois cenários
e adicionou uma provocação editorial que a fonte não sustenta literalmente.
Não há aprovação humana do humor nem prova de que o ajuste generaliza.
A mecânica está validada; naturalidade e adequação da fala continuam em teste.

## Limites do piloto

A detecção é textual e conservadora. Pode perder anúncios sem os termos previstos,
mudanças de pesos sem documentação, comentários em issues, blog ou modelos futuros
com outro identificador. Uma frase editada que mencione PT-BR pode pedir revisão
mesmo sem mudança de suporte. O trecho e o link permitem conferir isso.

Não atualiza o TTS nem começa uma bancada de áudio automaticamente.
Não é um monitor genérico de todos os assuntos e não acrescenta contexto a cada
turno: apenas o aviso usa o resumo do teste e a evidência selecionada.
