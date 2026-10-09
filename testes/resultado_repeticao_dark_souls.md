# Repetição nas falas de morte — 02/10/2026

O problema relatado foi copiar quase toda a abertura e trocar só o final. Os três exemplos reais
viraram casos de regressão. O ajuste está restrito a dark_souls_morte.

## O que mudou

A Luna guarda em RAM as cinco últimas falas de morte aceitas pela geração, completas.
Essa lista é separada dos começos usados pelas outras rotinas e recomeça ao reiniciar a Luna.
Uma fala que depois perder a janela de entrega também pode ficar nessa lista.

Antes de devolver uma fala, compara palavras sem diferenças de caixa, acento, pontuação e tag de
clima. Detecta igualdade, oito palavras iniciais iguais, trechos de pelo menos doze palavras,
similaridade alta e reaproveitamento de quase toda uma fala curta dentro de uma maior.
É uma heurística textual; pode rejeitar uma retomada deliberada e não entende equivalência de ideias.

Quando encontra cópia, tenta **uma vez** outra geração com o mesmo evento e personalidade,
retirando as citações antigas do pedido e pedindo outra abertura e ideia central.
Se repetir de novo, não publica aquele comentário. Não usa frases prontas.
Antes da nova tentativa, verifica interrupção e validade do evento. O chamador continua
verificando foco/prazo antes da entrega. Fora das mortes, esse filtro não se aplica.

## Experimento

Modelo verificado antes/depois das chamadas: Gemma 4 12B QAT Q4_0, engine llama.cpp b9608 ROCm,
contexto 8192, thinking desligado. Perfil e eventos sintéticos, sem áudio, interface ou jogo.
A primeira fala enviada pelo usuário foi usada como memória inicial.

Exploração: quatro mortes com o mecanismo anterior e quatro sem citar os começos antigos.
Os dois caminhos repetiram trechos; tirar as citações sozinho não demonstrou resolver.
Não é comparação cega de qualidade nem estimativa estatística de frequência em sessões reais.

A primeira versão do filtro deixou passar uma abertura reciclada com "acaba" trocado por
"acabou", seguida de um corte do resto da fala. Isso virou um teste adicional de cobertura
da frase curta. A rodada final já inclui essa correção:

| Resultado em oito mortes | Quantidade |
|---|---:|
| Aceitas na primeira geração | 5 |
| Repetições detectadas na primeira geração | 3 |
| Resolvidas na segunda geração | 2 |
| Descartadas após duas gerações repetidas | 1 |
| Falas finais utilizáveis | 7 |
| Chamadas ao modelo | 11 |

Mediana de geração por evento: 3,02 s; máximo: 5,16 s, somando as tentativas.
Não inclui TTS nem mede disputa de GPU com Dark Souls. O teste não altera o prazo do monitor.

Exemplo barrado nos eventos 5–7:
> A vida útil desse personagem acaba de ser reduzida a um frame de animação irrelevante.

A rodada final teve zero repetições aprovadas **pelo critério textual implementado**, mas ainda
reutilizou a ideia de virar um tapete em duas falas distintas. Também continuaram aparecendo
suposições sobre rapidez/golpes. Portanto, isto é proteção contra cópia, não demonstração de
criatividade, grounding ou qualidade de humor superiores. A personalidade e o prompt inicial
ficaram iguais; a instrução adicional só aparece na segunda tentativa.

## Verificação e reprodução

- 64 testes Python: detector, geração, bancada, monitor, cancelamento, radar e horas.
- 5 testes de montagem do prompt; golden preservado byte a byte.
- 39 arquivos de testes Node aprovados.
- O teste de montagem posterior usou o runtime isolado da bancada, executando montagem e
  limpeza de voz reais sem inicializar áudio, embeddings ou carregar/trocar modelo.

Sem subir a Luna:

    .\venv\Scripts\python.exe -X utf8 -m unittest testes.testa_repeticao_dark_souls

Com o Gemma já carregado, sem áudio:

    .\venv\Scripts\python.exe -X utf8 -m testes.bancada_repeticao_dark_souls

Brutos locais (ignorados pelo Git):
- logs/dark_souls/repeticao-20261002/exploracao.json
- logs/dark_souls/repeticao-20261002/corrigido.json — primeira versão, com o escape detectado
- logs/dark_souls/repeticao-20261002/corrigido-final.json — todas as tentativas e tempos

A bancada usa seeds 57–64 e soma 1000 na segunda tentativa, mantendo-a reprodutível.
A produção continua usando a amostragem normal do servidor, sem fixar seeds.
