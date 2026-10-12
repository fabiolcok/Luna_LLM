# Tom genérico da persona — causa e correções (11–12/10/2026)

Continuação de `diagnostico_mudanca_tom.md`. Aquele documento descartou mudança de código,
de modelo e de configuração. Este identifica, por ablação com o modelo real, o que de fato
decide o tom e registra o que foi alterado.

## Resumo

O bloco `EMOCAO` chegava inteiro ao modelo, mas **quase não influenciava** o papo curto.
Três fatores dominavam:

1. **O histórico da conversa (causa principal).** O Gemma 4 12B imita as próprias falas
   anteriores muito mais do que segue a descrição da persona. Depois de um reinício,
   `_historico_conversa = []`. A primeira resposta saía morna ("No que eu posso te ajudar
   agora?") e as seguintes copiavam esse tom. Isso explica a mudança "súbita": a sessão
   anterior ao reinício tinha falas ácidas que serviam de referência.
2. **Uma ordem de tom por horário no topo do prompt.** `periodo_atual()` em
   `modulos/falar.py` dizia "tom mais calmo, sem empolgação" (noite) e "fale bem tranquila e
   baixo, frases curtas" (madrugada), em todos os canais. As reclamações começaram depois
   das 18h.
3. **O próprio EMOCAO empurrava para o morno sem gancho.** "Sem graça concreta à vista, seja
   curta e SECA" e "a graça nasce de detalhe PRESENTE" deixam o modelo sem material em
   mensagens como "eae" ou "que bom", e a saída virava "Tô por aqui, só de boa".

## Evidência principal — ablação

Método: capturar o pedido real montado por `_reescrever_como_luna`, com `pensar._chamar_llm`
interceptado e perfil e memória reais, e reenviar ao TurboLLM trocando uma peça por vez.
Mensagens: "eae", "to bom e vc ?", "nada so conversando" e "que bom !", com as respostas mornas
reais do dia como histórico. 3 rodadas por variante.

| Variante | Efeito no tom |
|---|---|
| base | morno: "Boa noite. No que eu posso te ajudar agora?" |
| EMOCAO trocado por "Literalmente Glados" | igual à base |
| sem EMOCAO | igual à base |
| sem ESTRUTURA | levemente mais solto |
| instrução do turno reduzida à fala do usuário | igual à base |
| sem histórico | igual à base |
| **histórico com falas ácidas reais de 07 e 09/10** | **muda o tom:** "…ou se o seu teclado simplesmente decidiu economizar energia hoje." |

Conclusão: nessas mensagens, o histórico decide o tom e o texto do EMOCAO não decide.

Ordem de tom por horário (madrugada, 6 casos × 4): tirar só a ordem de tom e manter a
saudação deixou o "eae" mais solto e a agenda vazia com um pouco de graça. Despedidas e
"que bom" não mudaram.

## Mudanças aplicadas

Todas passaram por `testa_prompt_montagem` (golden regravado, diff conferido) e por
`node testes/rodar.js` (46 arquivos).

1. **`EXEMPLOS_TOM` em `modulos/prompts.py`:** 12 pares curtos ("Ele:" / "Você:"),
   **3 sorteados por turno**, anexados ao fim do `sistema_completo` (parâmetro `exemplos_tom`,
   chamado em `pensar.py`). `sortear_exemplos_tom(mensagem)` exclui o exemplo cuja fala é igual
   à mensagem atual, ignorando acento e pontuação. Sem isso, "eae" copiou o exemplo "eae"
   palavra por palavra em 2 de 3 rodadas. O golden fixa os 3 primeiros via patch em
   `testa_prompt_montagem.capturar`.
   - Resultado: "eae" passou de 0/3 para 3/3 `zoeira` sem cópia. Assunto concreto continuou
     ácido e pergunta séria continuou respondida.
   - Os modos enxutos não recebem os exemplos.
2. **Instrução do turno sem ferramenta (`pensar.py`, ramo `else` do `user_msg`):** saíram as
   frases que duplicavam a ESTRUTURA (validar genérico, fala cotidiana pequena, biscoito da
   sorte). **"Não puxe trabalho, família, jogos ou memória antiga…" foi mantida:** sem ela,
   puxar trabalho ou backlog sem relação com a mensagem foi de 2 para 11 em 33 respostas.
3. **Abertura:** saiu a lista fixa "[varie a abertura — nada de 'Pois é'…]" do `anti_rep`.
   Ficaram os avisos dinâmicos que citam a fala anterior. O bullet "VARIE" da ESTRUTURA foi
   encurtado (420 → 299 caracteres). Muletas: 0/24, igual à versão anterior.
4. **EMOCAO enxugado (1.853 → 1.057 caracteres):** saiu a técnica de escracho detalhada e o
   "sem graça concreta, seja curta e SECA". Entrou "…ou de você mesma" como fonte de graça.
   O grounding e o LIMITE de saúde/tristeza ficaram intactos. `bancada_persona` 41×3:
   persona 35/42 → 36/42, enxutos 80/81 → 80/81. "deixa terminar seca" chegou a sair, e
   `nao_fecha_com_pergunta` caiu de 3/3 para 1/3. A frase voltou e o cenário passou 6/6.
5. **`periodo_atual()` em `modulos/falar.py`:** o índice 1 agora só informa o período e a
   saudação certa. Decisão do dono do projeto: manter apenas bom dia, boa tarde e boa noite.

Comentários no código registram o motivo de cada item, com os números.

## Testado e rejeitado

- **Exemplos como turnos falsos no histórico:** o tom voltou, mas ela passou a citar as falas
  de exemplo como coisas que o usuário tinha dito ("O 'nada demais' ainda tá de pé?").
- **3 exemplos fixos sem sorteio:** cópia literal em 3/3 rodadas.
- **Exemplos de despedida e de "dado + reação":** sem efeito nas despedidas.
- **Instrução da agenda mais solta ("reaja com sua personalidade"):** na agenda vazia, 3 de 4
  respostas inventaram "mais vazia que o backlog de jogos que você compra e nunca abre".
- Uma calibração anterior com gatilhos por palavra-chave e assuntos fixos já tinha sido
  recusada pelo dono do projeto (ver `diagnostico_mudanca_tom.md`). Não reintroduzir.

## Comportamento que continua e por quê

- **Despedidas ("vou dormir", "vlww") saem `carinho` com qualquer versão do prompt.** O
  modelo aplica a regra do EMOCAO "cansaço cotidiano aceita mordida curta e carinhosa sobre
  descansar". O dono do projeto decidiu manter.
- **A resposta da agenda é neutra.** Vem do `prompt_agenda_web` ("naturalidade e concisão").
  Mantido por decisão do dono, porque dar mais solta trouxe invenção.
- **Depois de duas ou três respostas mornas no histórico, "to bom e vc?" e "que bom!" melhoram
  pouco.** O histórico continua sendo o fator mais forte.
- **No primeiro turno da sessão ela ainda abre com "Boa noite."**, seguido de provocação.
- **Luto com memória pertinente (`bancada_persona`):** 0/3 antes e depois. Ela acolhe sem
  cutucada, mas não conecta com a memória do tio internado. Problema anterior a este trabalho.

## Como medir mudanças futuras de tom

- O placar da `bancada_persona` mede regras, não tom. Para tom, use a técnica de ablação:
  interceptar `pensar._chamar_llm`, capturar `messages`, reenviar variantes via `_chamar_llm`
  sem `stream` e comparar a distribuição de `[clima:X]` mais a leitura das respostas.
- **Sempre inclua casos com histórico morno.** Medir sem histórico superestima o efeito de
  qualquer mudança no texto da persona.
- **Registre o horário da medição**, ou force um período fixo. Antes desta correção, a
  medição variava com a hora do dia.
- **Confira cópia de exemplo:** sequência de 5 palavras de algum `EXEMPLOS_TOM` na resposta.
- **Confira "puxou assunto":** Colibri, plantão, suporte, backlog, família quando a mensagem
  não trata disso.
- **Atenção a um bug de script:** um script que sobrescreve `sys.argv` antes de calcular o
  caminho de saída grava `1.json` na raiz do repositório.
