# Continuidade a partir das avaliações — 19/09/2026

Modelo local: Gemma-4-12B QAT no TurboLLM. Duas rodadas por variante, 20 respostas ao todo.
Fontes pessoais substituídas pelas mesmas fixtures da bancada da persona.

Os votos antigos não contêm o histórico completo. Estes são cenários reconstruídos,
inspirados nas reclamações de filme confundido e notícia misturada com conversa anterior.
Não reproduzem o roteador: medem a etapa da persona com os dados e histórico fornecidos.

| Caso | Atual | Experimental |
|---|---:|---:|
| Título do filme no histórico, ano não fornecido | 0/2 | 0/2 |
| Filme sem título: pedir identificação | 2/2 | 2/2 |
| Usuário troca de filme, ano não fornecido | 0/2 | 0/2 |
| Título e ano explícitos no histórico | 2/2 | 2/2 |
| Notícia sem ligação com a conversa anterior | 2/2 | 2/2 |

Os quatro primeiros casos usam PROMPT_COMPLETO: **4/8 em cada variante**.
A notícia usa ENXUTO_PROATIVO: **2/2 em cada variante**.

A variante experimental acrescentou um lembrete de referência perto da pergunta sobre o
filme; na notícia, retirou o bloco da conversa anterior. Nenhuma das alterações entrou
em produção. Não houve ganho nos checks desta amostra, e duas rodadas não provam equivalência.

Leitura manual:

- Com o título disponível, o modelo ainda inventou anos como 1976 e 1973. O lembrete
  experimental fez as respostas nomearem o filme, mas não resolveu a informação factual.
- Com 1966 explícito na ficha citada pelo usuário, todas as respostas preservaram o ano.
  **Uma delas ainda chamou o filme de guerra**: passou no check de ano, mas acrescentou
  informação errada. O placar não mede correção integral, criatividade ou qualidade.
- As quatro respostas de notícia não mencionaram a mulher pulando corda; o problema original
  não apareceu nestas reconstruções. Isso não significa que tenha sido corrigido.

Decisão: entregar a avaliação V2 e conservar o contexto atual até haver evidência para uma
mudança específica. Os snapshots novos permitem distinguir referência perdida, dado ausente
e detalhe inventado, sem atribuir todo erro ao tamanho ou à posição do prompt.

Para repetir: `python testes/bancada_continuidade.py --comparar --repeticoes 2`.
Respostas locais completas: `logs/bancada_continuidade.jsonl` (não versionado).
