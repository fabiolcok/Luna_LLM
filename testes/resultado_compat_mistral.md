# Compatibilidade de histórico — Mistral NeMo, 26/09/2026

O erro `conversation roles must alternate user/assistant/...` foi reproduzido
com o **Mistral NeMo 12B ArliAI RPMax v1.1 Q4_K_M**, no TurboLLM 1.13.4 e
llama.cpp b9608 ROCm. A biblioteca e a configuração persistente não foram trocadas.

## Isolamento da causa

Chamadas sintéticas, sem executar ferramentas:

| Entrada | Resultado antes da adaptação |
|---|---|
| `system → user` | Respondeu |
| `system → user`, com ferramenta fictícia disponível | Respondeu |
| Mesmo caso com chamadas paralelas desativadas | Respondeu |
| `system → user → assistant → user`, com ferramenta disponível | Respondeu |
| `system → assistant → user` | Erro 400 idêntico ao relatado |

O teste simples da troca de modelo enviava apenas `user: oi` e, por isso, passava.
O histórico usado pelo chat pode começar com avisos proativos ou ter várias falas
consecutivas da Luna. O template carregado exige alternância e rejeita esse recorte.
Não foi necessário desativar ferramentas ou editar o template da engine.

## Correção

`_chamar_llm` reconhece somente o erro 400 específico de alternância. Nesse caso,
adapta mensagens textuais e repete uma vez:

- Falas iniciais da assistente passam para um bloco identificado como contexto na
  primeira mensagem real do usuário, preservando conteúdo e autoria.
- Mensagens consecutivas do mesmo autor são agrupadas, mantendo a ordem.
- O histórico original não é mutado; o prompt de sistema e as opções da chamada
  são preservados. Conteúdo multimodal e mensagens de ferramentas não são achatados.
- Sem mudança possível, ou se a retentativa também falhar, o erro é propagado.
  Outros erros não disparam essa adaptação. Modelos permissivos seguem pelo caminho original.

## Validação com prompts reais da Luna

Usamos a captura de prompts sem boot da bancada, perfil/contexto sintéticos e a
função `_chamar_llm` corrigida. Nenhuma ferramenta foi executada; não houve envio
para Web, voz ou Telegram. O modelo foi recarregado na mesma escolha após aparecer
descarregado no status do TurboLLM.

| Caso | Resultado da API | Observação |
|---|---|---|
| Roteador, `eae`, após dois proativos | Sem erro 400; 13,64 s | Repetiu o prompt e atingiu 256 tokens |
| Persona, `eae`, após dois proativos | Sem erro 400; 3,84 s | “Eae! Tudo joia? Que papo queremos dar hoje?” |
| Persona, conversa com duas falas consecutivas da assistente | Sem erro 400; 3,77 s | Produziu resposta textual |

**O formato foi corrigido; a qualidade do roteamento não foi validada.** O RPMax
descumpriu a saída `SEM_FERRAMENTA` no caso de saudação e gastou o orçamento repetindo
instruções. Esse texto é descartado pelo fluxo normal da Luna, que segue para a
persona quando não há pedido de ação. A amostra não comprova capacidade de executar
pedidos de música, pesquisa ou outras ferramentas.

O NeMo Abliterated não foi recarregado para este teste. A correção é acionada pelo
erro do template, mas a validação ao vivo acima foi feita somente no RPMax escolhido.

## Regressões

- 30 testes Python de histórico, execução e recuperação de modelo: passaram.
- 5 testes de montagem de prompt: passaram antes e depois, sem modificar o golden.
- 39 arquivos de testes da interface: passaram.

Evidência local: `logs/compat_mistral_nemo_20260926.json` (ignorada pelo Git).
É necessário reiniciar a Luna para carregar a correção no processo em uso.
