# Responder, consultar e ampliar no modo Web

Implementado em 11/10/2026. Requer reiniciar a Luna e recarregar a página.

## Uso

- **↩ na resposta:** seleciona a mensagem. Escreva qualquer pergunta na caixa normal;
  o trecho aparece acima dela e pode ser removido pelo ×. Seu rascunho permanece.
- **Notícias e promoções**, no canto superior direito, ou **Ver todas** num cartão: abrem a
  biblioteca em uma tela que ocupa a janela, com cartões em grade. Use “Voltar à conversa”
  ou Escape para retornar. Filtre notícias/promoções, lidas/não lidas, ou busque um
  assunto. “Conversar sobre isso” seleciona esse item como referência da próxima pergunta.
  Abrir o painel não marca tudo como lido; abrir a fonte ou clicar “Marcar lida” marca um item.
- **Buscar conversa:** pesquisa texto de ambos os participantes, sem exigir acentos.
  O atalho fica no mesmo grupo de acompanhamentos, mascote e configurações, no topo à direita.
  A resposta aparece diretamente no resultado, sem prévia duplicada ou botão de expandir.
  “Ir à mensagem” aparece quando o turno ainda está na sessão. Uma conversa fora da sessão
  também pode ser lida e respondida na busca.
- **Imagem:** clique ou use Enter/Espaço com a miniatura selecionada. O arquivo original
  aparece sem o fade do cartão. Escape, × ou clique no fundo fecham a ampliação.

## Contexto e dados

A consulta não chama o modelo, lê sites nem inicia TTS. Os 40 turnos da sessão continuam
separados do arquivo de consulta, em `logs/biblioteca_web.json`: últimos 1.000 turnos e
300 notícias/promoções. O arquivo é local e ignorado pelo Git. Na primeira busca,
recupera conversas anteriores disponíveis em `modelos/chromadb/chroma.sqlite3`,
backups `historico-luna-*.json` e `logs/luna.log`. O banco é aberto somente para leitura
dos textos; o cliente Chroma, a migração e os embeddings não são carregados.
O log antigo corta respostas, por isso esses resultados são identificados como trechos.
Conversas que nunca foram gravadas ou cujos registros foram apagados não são recuperáveis.

As notas atuais `Novidades.md` e `Promocoes.md` são importadas uma vez, quando a biblioteca
é aberta com um vault configurado. Os próximos lotes do radar são gravados junto do fluxo
que já alimentava essas notas. A integração também funciona sem Obsidian; promoções da
wishlist são recuperadas dos links estruturados apresentados na conversa. As imagens
locais de promoções continuam sujeitas à limpeza de arquivos antiga do Obsidian.

O navegador envia somente o id da referência. O servidor busca o texto e a fonte,
rejeita referências vencidas ou forjadas e mantém o contexto separado da pergunta.
Responder a uma notícia reaproveita o fluxo de leitura da fonte já existente. Nas outras
mensagens, o trecho selecionado é limitado a 1.200 caracteres e a pergunta antiga a 300;
o arquivo inteiro nunca entra no prompt. Os 42 ramos anteriores do golden ficaram idênticos;
somente dois cenários novos exercitam resposta com referência e isolamento do canal de voz.

## Validação

- `node testes/rodar.js`: 46 arquivos passaram. O teste de inicialização executa também
  `static/consulta-web.js`, servido localmente. A mudança de “Ver todas” para a biblioteca
  foi incorporada às asserções dos cartões, mantendo a verificação de posição e duplicação.
- Testes Python do arquivo, referências, HTTP, recebimento, sugestões, cartões, links,
  promoções, áudio, agenda e golden: 83 testes em execução isolada, sem iniciar a Luna.
- A interface real e os endpoints Flask foram exercitados no Edge headless com dados de
  teste e WebSocket simulado: 1280×800, 1920×1080, 3440×1440 e 420×900. Sem erro JavaScript
  ou transbordamento horizontal. Biblioteca ocupa a janela, com 3, 5, 6 e 1 colunas,
  respectivamente; área de conteúdo limitada a 2.200px no ultrawide. A busca mantém
  sua largura de 780px. Filtros, consulta de uma conversa anterior à sessão, envio com
  referência confirmada e Escape em imagens de notícia e promoção foram exercitados.
- Node cobre confirmação atrasada, rascunho preservado na falha, mudança de referência
  durante o envio, paginação, respostas HTTP fora de ordem, erro de consulta e ausência
  de chamadas ao modelo ao navegar. Python cobre persistência, retenção, importação de
  notas, deduplicação, estado de leitura e rejeição de referência adulterada.

Na cópia temporária do arquivo local, a importação acrescentou 296 registros anteriores:
58 respostas completas do histórico/backups e 238 trechos do log, desde 22/08/2026.
Os quatro turnos já registrados na web foram preservados. O arquivo real não foi alterado
por essa verificação; a importação acontece na primeira busca após reiniciar com o código novo.
Os testes também cobrem preservação de IDs, deduplicação entre log e resposta completa,
isolamento de canais/reinícios, limite de retenção e ausência de escrita no banco da memória.
Esses registros ficam só no arquivo de consulta. Apenas a mensagem escolhida em “Responder”
entra no contexto do turno, dentro dos limites já descritos acima.

Artefatos locais: `logs/bancada_web/20261011-conversa-biblioteca/`.
A revisão da grade está em `grade/`, com capturas e métricas; `verificar_grade.py` reproduz a validação.

## Bancada com o Gemma

Concluída em 11/10/2026 com o Gemma 4 12B QAT Q4_0, llama.cpp b9608 ROCm,
contexto de 8.192 tokens e thinking desligado. Três referências × duas seeds,
com chamadas de roteador e persona registradas separadamente. O histórico recente
tratava de outro jogo; as referências eram uma piada de Dark Souls, uma conversa
sobre CGNAT e uma notícia sintética de monitor OLED. A leitura do artigo foi simulada;
não houve áudio, gravação de memória nem execução de outras ferramentas externas.

Na primeira rodada, a referência sobre CGNAT chegou ao modelo, mas ele inventou
um objetivo de isolamento do serviço. O ajuste ficou restrito à resposta com referência:
a persona recebe a orientação de preservar os fatos e o roteador recebe o assunto
escolhido sem as últimas mensagens de outro tema. O prompt desse roteador distingue
explicação de uma referência de um pedido concreto de ação ou consulta.

| Referência | Roteador na rodada final | Persona na rodada final |
| --- | --- | --- |
| Piada de Dark Souls | Não acionou ferramenta nas duas seeds. Escreveu explicações em vez de `SEM_FERRAMENTA`; esse texto foi descartado pelo fluxo existente. | Retomou Dark Souls e explicou a metáfora nas duas respostas. A leitura da piada variou entre física e peso da dificuldade. |
| CGNAT | Retornou `SEM_FERRAMENTA` nas duas seeds, sem tentar ler navegador ou código da Luna. | Retomou CGNAT e a abertura de portas nas duas respostas, sem repetir o objetivo inventado de isolamento. Ainda acrescentou detalhes imprecisos. |
| Notícia OLED da biblioteca | Acionou `resumir_site` com a URL selecionada nas duas seeds. | Explicou o uso diário, fotos de telas brancas/cinzas e as limitações de brilho e controle, conforme o artigo sintético. |

Não surgiu a resposta genérica de falha de ferramenta nos seis casos finais. Isso
valida o caminho de referência nesta amostra, não garante precisão factual geral.
No caso CGNAT, uma resposta falou em IP público **fixo** como se fosse necessário
para abrir portas; a referência dizia apenas IP público. A outra generalizou sobre
cobrança pelo provedor, e o modelo não preservou de forma consistente a condição de
que o estado atual pode ter mudado desde a conversa antiga. Esses pontos continuam
como limitações de qualidade do modelo, sem ampliar a calibração para o chat inteiro.

A queda de energia aconteceu depois de a rodada isolada de CGNAT terminar e antes
de registrar a conclusão. Após a retomada, os testes foram repetidos e a bancada
completa de seis respostas foi concluída com o mesmo modelo recarregado.

Artefatos: `respostas-gemma-antes.json` (primeira rodada),
`respostas-gemma-cgnat.json` (verificação isolada) e `respostas-gemma.json` (rodada final),
na pasta local indicada acima. Para reproduzir com o modelo carregado:
`python -X utf8 -m testes.bancada_resposta_mensagem`.
