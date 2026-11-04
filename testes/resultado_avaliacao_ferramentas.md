# Avaliação humana das ferramentas — 01/11/2026

Ação e resposta têm votos independentes. Novos turnos com ferramenta recebem
"Foi o que você pediu?" abaixo da resposta; o negativo pede motivo e aceita
comentário opcional. Sem ferramenta, a opção de ação ausente fica recolhida.
As pendências e votos ficam em `logs/avaliacao_ferramentas.json`, com ID do turno,
pergunta, resposta, argumentos executados e informações das chamadas do modelo.
O menu permite revisar pendências com o contexto original após reiniciar.
Não há geração adicional pelo LLM nem cobrança por voz.

## Validação

- 18 testes Python: avaliações existentes, persistência, revisão sem duplicar,
  vínculo por ID, ausência de ferramenta, erro de gravação e contrato da rota.
  Executados com Python 3.14 local; esses módulos usam apenas biblioteca padrão.
- `node testes/rodar.js`: 47 arquivos passaram.
- Edge/Playwright com API e conversa fictícias: linha, motivo, comentário,
  falha de gravação, reenvio, confirmação e contagem de pendências passaram.
  Captura e roteiro locais em `agents/tmp/piloto-web/avaliacao-acao.png` e
  `avaliacao-ui.cjs`. Nenhum pedido enviado ao modelo e nenhum voto real gravado.

## Limites

Precisa reiniciar a Luna. Não migra diagnósticos antigos: os novos registros
começam após carregar a implementação. O estado técnico segue a classificação
existente do retorno da ferramenta, não comprova que o efeito externo ocorreu.
Thinking não explicitado nos parâmetros aparece como não informado.
Ação ausente pode ser reportada enquanto o snapshot da resposta estiver disponível;
após o voto, o registro persiste. Teste integrado no processo reiniciado e
avaliação visual do usuário ainda pendentes.
