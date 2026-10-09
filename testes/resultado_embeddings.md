# Bancada de embeddings — 06/10/2026

O EmbeddingGemma 2 é um candidato promissor para substituir os dois embeddings
da Luna. Nesta rodada pequena, melhorou a ordem das lembranças nos dois canais.
A adoção exige calibrar os filtros e reconstruir o índice de histórico; a
configuração da Luna foi mantida com os MiniLM durante a comparação.
A adoção posterior está registrada na seção final.

## O que cada modelo faz hoje

- `paraphrase-multilingual-MiniLM-L12-v2`: busca fatos nas notas de memória,
  com cosseno e piso padrão de 0,52.
- `all-MiniLM-L6-v2`: busca pares de conversa no ChromaDB,
  com distância L2 ao quadrado e corte de 1,3.

Ambos rodam na CPU. A comparação manteve essa decisão.

## Como foi medido

Dois conjuntos sintéticos em PT-BR: fatos curtos e pares de conversa.
Cada canal tem 30 documentos e 40 consultas: 20 de calibração e 20 reservadas
para teste. Cada metade contém 12 consultas com uma lembrança alvo e oito
sem resposta direta no corpus. São 80 consultas no total, sendo 40 de teste.

As respostas esperadas foram definidas antes de executar os modelos.
“Relevante” aqui significa abordar o fato ou episódio pedido, e não apenas
o mesmo tema. Perguntas sobre data de atualização, previsão do tempo ou
informação pessoal ausente não têm lembrança alvo. O corpus não foi obtido
do ChromaDB nem de notas privadas; os exemplos reproduzem tipos de uso da Luna.

Windows 11, Ryzen 5 5600, aproximadamente 32 GiB de RAM, Python 3.12.10.
Mesmo ambiente para os três modelos, float32, quatro threads, processos
separados. Inferência de consulta individual depois do aquecimento;
documentos codificados em lotes de oito. Nenhuma execução da Luna foi iniciada.

No Gemma, visão e áudio foram desativados com
`config_kwargs={"vision_config": None, "audio_config": None}`.
Foram carregados 271.002.624 parâmetros textuais. Consultas usaram
`SearchQuery` e documentos `Document`, os prefixos de busca do checkpoint.
O corte em 256 dimensões foi renormalizado. Esse uso segue o
[guia oficial](https://ai.google.dev/gemma/docs/embeddinggemma/inference-embeddinggemma-with-sentence-transformers).

## Ordem das lembranças, antes de aplicar filtros

| Modelo | Canal | Dimensões | Alvo em 1º | Alvo entre os 3 |
|---|---|---:|---:|---:|
| MiniLM L6 | episodica | 384 | 8/12 | 10/12 |
| MiniLM L6 | historico | 384 | 7/12 | 11/12 |
| MiniLM multilíngue | episodica | 384 | 6/12 | 11/12 |
| MiniLM multilíngue | historico | 384 | 7/12 | 10/12 |
| EmbeddingGemma 2 | episodica | 768 | 12/12 | 12/12 |
| EmbeddingGemma 2 | episodica | 256 | 12/12 | 12/12 |
| EmbeddingGemma 2 | historico | 768 | 10/12 | 12/12 |
| EmbeddingGemma 2 | historico | 256 | 10/12 | 12/12 |

Cada fração considera apenas as 12 consultas positivas de teste daquele canal.
“Entre as três” não indica que as outras duas também sejam úteis.

O ganho mais claro foi nos fatos curtos: o Gemma colocou todos os 12 alvos em
primeiro lugar. Por exemplo, identificou a lembrança sobre volume ao receber
“o som tem que mudar durante a reprodução quando eu arrasto o controle?”.
O MiniLM multilíngue colocou o teste do Kitten em primeiro lugar nesse caso.

No histórico, o Gemma ainda confundiu a reclamação sobre repetição com a
regra de não mencionar o contador de mortes. Também colocou promoções do
Telegram antes do feed de humor. As lembranças corretas estavam em segundo lugar.

## Custo na CPU

| Modelo | Consulta mediana / p95 | Pico de RAM |
|---|---:|---:|
| MiniLM L6 | 9.3 / 10.6 ms | 0.51 GiB |
| MiniLM multilíngue | 15.8 / 18.2 ms | 1.45 GiB |
| EmbeddingGemma 2 | 98.7 / 128.0 ms | 1.80 GiB |

RAM é o pico RSS do processo durante carga e inferência, incluindo bibliotecas.
Não some os picos dos MiniLM para estimar a Luna: no aplicativo eles
compartilham bibliotecas e a memória tem outro ciclo de vida. O custo extra
observado sobre os imports está nos JSONs.

O Gemma acrescentou cerca de um décimo de segundo por consulta nesta bancada.
O teste não mediu carga simultânea da Luna, jogos, FPS ou textos longos.
A variante 256d usa a mesma inferência e RAM de 768d; reduz o tamanho dos vetores
armazenados, não o tamanho do modelo.

## Filtros: o modelo novo precisa de outro piso

O filtro conservador ficou acima do maior escore das oito negativas de
calibração de cada canal. Não usou as consultas de teste e não foi ajustado
para maximizar o placar. Ele prioriza rejeição e pode descartar lembranças úteis.

| Modelo | Canal | Dim | Piso calibrado | Positivas recuperadas | Negativas com contexto | Itens sem relevância direta |
|---|---|---:|---:|---:|---:|---:|
| MiniLM L6 | episodica | 384 | 0.6445 | 6/12 | 1/8 | 3 |
| MiniLM L6 | historico | 384 | 0.6031 | 4/12 | 1/8 | 3 |
| MiniLM multilíngue | episodica | 384 | 0.5540 | 5/12 | 0/8 | 1 |
| MiniLM multilíngue | historico | 384 | 0.5660 | 3/12 | 0/8 | 2 |
| EmbeddingGemma 2 | episodica | 768 | 0.7716 | 8/12 | 1/8 | 2 |
| EmbeddingGemma 2 | episodica | 256 | 0.7775 | 10/12 | 1/8 | 3 |
| EmbeddingGemma 2 | historico | 768 | 0.7484 | 10/12 | 1/8 | 5 |
| EmbeddingGemma 2 | historico | 256 | 0.7527 | 12/12 | 1/8 | 10 |

Copiar o piso atual de 0,52 para o Gemma recuperou 12/12 alvos, mas também deixou passar contexto nas oito perguntas sem resposta. O MiniLM multilíngue, no seu canal atual de fatos curtos, recuperou 5/12 alvos e aceitou contexto em 1/8 negativas com o mesmo piso.

“Negativa com contexto” significa que algum documento passou no filtro,
embora não contivesse a resposta pedida. Não mede invenções na resposta do LLM.
Mesmo com o piso conservador, o Gemma recuperou a nota sobre esperar uma API
de Deadlock quando a pergunta pedia a data de uma atualização. É um assunto
relacionado, mas essa nota não contém a data.

O corte L2=1,3 também não pode ser copiado sem avaliar a escala dos vetores.
Nesta fixture, o L6 no histórico e o Gemma retornaram documentos em todas
as oito negativas de teste com esse corte. Os diagnósticos estão nos JSONs.

Em 256d, o Gemma manteve o acerto de primeiro lugar nos testes e recuperou
mais alvos com o piso conservador. Também aceitou mais itens sem relevância
direta, principalmente no histórico. Isso não prova que 256d seja melhor:
a escala mudou e a calibração tem só oito negativas por canal.

## Recomendação

Vale avançar para um piloto de memória com EmbeddingGemma 2. Começaria pelos
fatos curtos das notas, mantendo o filtro separado por canal e comparando
o que entra no prompt. Depois avaliaria um índice novo de histórico.

Para substituir ambos, a implementação precisa usar os prefixos corretos,
recalibrar a busca e a deduplicação de fatos, invalidar o cache de embeddings
e reindexar as conversas em uma coleção separada. Os vetores antigos de
384 dimensões não são compatíveis com os novos de 768 ou 256 dimensões.

A bancada avalia recuperação de lembranças. Não mede criatividade, personalidade
ou qualidade da resposta completa. Uma rodada com 12 positivos por canal é
evidência inicial; não é uma taxa de acerto da memória real.

## Reprodução e evidência

Código: [bancada_embeddings.py](bancada_embeddings.py).
Corpus e rótulos: [cenarios_embeddings.json](cenarios_embeddings.json).
Ambiente: [requirements_embeddings.txt](requirements_embeddings.txt).
Comandos: [README dos testes](README.md#embeddinggemma-2--comparação-de-memória-na-cpu).

| Modelo | Revisão dos pesos |
|---|---|
| sentence-transformers/all-MiniLM-L6-v2 | 1110a243fdf4706b3f48f1d95db1a4f5529b4d41 |
| sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2 | e8f8c211226b894fcb81acc59f3b34ba3efd5f42 |
| google/embeddinggemma-2 | 914f7f89142e33e77833254d9c9b90c3cef7303b |

Pacotes da bancada: Transformers 5.19.0, Sentence Transformers 6.1.0,
PyTorch 2.14.1, Torchvision 0.29.1, Pillow 12.3.0, NumPy 2.4.4,
psutil 7.2.2 e Hugging Face Hub 1.33.0.
O processador exigiu Pillow/Torchvision e o arquivo oficial
`chat_template.jinja`, mesmo na execução textual.

Resultados locais, ignorados pelo Git:

- [Relatório consolidado](../logs/bancada_embeddings/20261006-embeddinggemma2-final/resultado.md).
- [MiniLM L6](../logs/bancada_embeddings/20261006-embeddinggemma2-final/minilm_l6.json).
- [MiniLM multilíngue](../logs/bancada_embeddings/20261006-embeddinggemma2-final/minilm_multi.json).
- [Gemma com diagnóstico L2 normalizado](../logs/bancada_embeddings/20261006-embeddinggemma2-final/gemma2-normalizado/gemma2.json).
- [Manifesto e hash do corpus](../logs/bancada_embeddings/20261006-embeddinggemma2-final/manifesto.json).

A primeira execução completa do Gemma foi preservada no diretório principal.
Uma nova execução corrigiu a normalização do diagnóstico L2 de 256d e fixou
o limite textual em 8192 tokens; os rankings de cosseno de ambas coincidiram.
O relatório usa a execução corrigida. Tentativas anteriores interrompidas
durante a preparação também foram preservadas em logs.

Validação: cinco testes dos critérios da bancada passaram e
`node testes/rodar.js` passou nos 41 arquivos. As bibliotecas principais da
Luna, na etapa da comparação, eram Sentence Transformers 5.4.1, Transformers 5.7.0 e
PyTorch 2.11.0. A memória e o índice de produção não foram migrados naquela etapa.

## Adoção aplicada em 06/10/2026

Depois da comparação acima, os dois caminhos passaram a compartilhar a
instância textual de EmbeddingGemma 2 na CPU, em 768 dimensões.
Os valores iniciais são 0,772 para recall episódico, 0,75 para histórico
e 0,77 para recuperar referências na curadoria. O histórico usa distância
de cosseno; não reutiliza o corte L2 dos MiniLM.

A bancada de integração executou as funções reais da memória com notas
sintéticas e um ChromaDB separado:

| Canal | Positivas recuperadas | Negativas com contexto | Itens sem relevância direta |
|---|---:|---:|---:|
| Memória curta | 8/12 | 1/8 | 2 |
| Histórico | 10/12 | 1/8 | 4 |

Os números já incluem os filtros. O caso negativo que passa é o assunto
correlato de Deadlock descrito acima. Não foi avaliada a resposta final do LLM.

Na prova de curadoria, as oito paráfrases recuperaram o fato existente,
as quatro atualizações recuperaram a referência anterior, e quatro fatos
novos sem relação não recuperaram candidatos. A comparação não altera
memórias frias e não descarta atualizações automaticamente.

A adoção mantém PyTorch/torchaudio 2.11.0 e NumPy 1.26.4. Transformers,
Sentence Transformers e suas dependências de suporte foram atualizados;
Torchvision 0.26.0 foi acrescentado para o processador do Gemma.
Um teste também sintetizou 4,1 segundos de áudio com Kokoro, sem reproduzi-lo.

O histórico local com 30 conversas foi migrado para
`historico_luna_embeddinggemma2_768_v1`. IDs, textos e metadados foram
copiados. Os hashes dos textos, metadados e vetores da coleção de origem,
antes e depois da cópia, coincidiram. A coleção MiniLM continua intacta;
o backup textual da cópia está em `modelos/backups_embeddings/`.

A migração é retomável após falha e reconhece registros antigos já copiados,
evitando reinserir conversas podadas do novo índice. No primeiro acesso de
cada processo também verifica falas acrescentadas pela instância antiga
antes do reinício. O cache de fatos depende do modelo e das datas.

Validação: testes de migração/curadoria, montagem dos prompts e os 41
arquivos da interface passaram. O golden de prompts permaneceu intacto.

Evidência local:

- [Integração e prova de curadoria](../logs/bancada_embeddings/integracao-20261006/resultado.json).
- [Migração do histórico local](../logs/migracao_embeddinggemma2_20261006/aplicacao.json).

Feche e abra a Luna para o processo em execução carregar o novo código e
as bibliotecas atualizadas.

## Teste de conversa após a adoção

A pergunta “Você lembra o que estava impedindo o acesso externo ao meu servidor?”
acionou `ler_obsidian` no turno de 19:20 de 06/10. O ramo que preserva notas
literalmente devolveu `Memoria.md`, sem executar a persona nem o recall semântico.
Esse resultado não mede a qualidade do novo embedding.

Foi adicionada uma proteção para perguntas de lembrança que não pedem notas ou
outra ação explícita. Chamadas indevidas a `ler_obsidian` ou `salvar_obsidian`
são ignoradas; a pergunta segue para a persona com as fontes usuais de memória.
O comando curto “lembra o que...” também não vira uma anotação pela rede de segurança.
A proteção de ações sem ferramenta permanece para pedidos explícitos.

A conferência somente de leitura não encontrou a palavra CGNAT nas memórias ativa
ou fria, no perfil ou no histórico novo. O exemplo de pergunta só poderia ter a
resposta esperada se o fato estivesse registrado. Uma lembrança encontrada nas
notas é estar jogando Dark Souls pela primeira vez; esse é um exemplo disponível
para o próximo teste manual.

Os oito testes de `testa_intencao_memoria` exercitam o fluxo real de roteamento com
respostas de modelo simuladas, reproduzindo a ferramenta indevida e mantendo
leitura fiel de notas, anotação explícita e honestidade para ação não executada.
Eles não medem a qualidade da resposta do LLM. A montagem dos prompts passou sem
alterar o golden, e os 41 arquivos de teste da interface passaram.

## Resultado manual às 23:37 de 06/10/2026

A pergunta sobre jogar Dark Souls pela primeira vez chegou à persona, sem
a leitura literal do Obsidian. O log mostrou 52 caracteres em recentes,
54 em relacionada e 317 em ChromaDB. A resposta afirmou que o usuário
“ia começar essa jornada recentemente” e comparou Dark Souls a Aion 2,
perguntando se Dark Souls continuava entre as prioridades ou tinha virado
uma promessa no backlog.

A conferência das fontes atuais, sem gravar nem aquecer lembranças,
encontrou o fato correto no bloco recente: “Está jogando Dark Souls
pela primeira vez”, registrado em 21/09. A busca semântica trouxe também
“Comprou mais um jogo porque jogou o primeiro”, com similaridade de
aproximadamente 0,785, acima do corte de 0,772. Esse fato genérico não é
uma evidência direta sobre a estreia em Dark Souls; sua utilidade como
contexto de conversa deve ser avaliada separadamente. A consulta do histórico, restringida aos
registros anteriores ao turno, aceitou uma conversa de 27/09 sobre jogar
Dark Souls, com distância aproximada de 0,226.

Avaliação humana positiva: o usuário confirmou que estava no Aion 2 naquele
momento e gostou da resposta. A comparação ligou a lembrança ao contexto atual,
e a provocação perguntou sobre as prioridades em vez de afirmar que Dark Souls
foi abandonado. A classificação inicial como falha de conversa foi rígida demais.

A formulação “ia começar” tem menos precisão literal que o registro “está
jogando pela primeira vez”, mas esse detalhe não anulou a qualidade da interação
para o usuário. O fato pedido estava disponível e o gancho com o jogo atual foi
aprovado. A latência e a qualidade da resposta final não estavam cobertas pelo
placar de retrieval da bancada sintética.

Tempos desse turno: roteador 45,7 s; intervalo até montar o prompt da persona
cerca de 16 s, incluindo o primeiro carregamento do embedding; geração da
persona 18,1 s. O atraso do roteador ocorreu antes desse carregamento.
O log sozinho não identifica por que a chamada do LLM levou 45,7 s.

Conclusão desta rodada: preservar esse uso de memória junto ao contexto atual,
incluindo a provocação aprovada. Esse exemplo não justifica bloquear comparações
com o jogo atual nem endurecer o prompt. A precisão dos fatos recuperados e a
latência podem continuar sendo medidas separadamente em outros testes.
Não foram alterados prompts ou limiares nesta conferência.
