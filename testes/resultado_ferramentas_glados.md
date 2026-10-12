# Ferramentas com o prompt temporário GLaDOS

Rodada de 12/10/2026, das 12:10:19 às 12:16:40, horário local. Leitura das 40 respostas,
das saídas do roteador e dos argumentos encaminhados pelo Python.

**A personalidade não impediu o despacho das ferramentas nesta amostra.** Foram 36 pedidos
encaminhados à ferramenta esperada e quatro comentários corretamente tratados sem ferramenta.
As confirmações reconheceram os retornos simulados, inclusive falha e rascunho pendente.

Há duas ressalvas: o roteador imitou a persona em um comentário com histórico ácido, em vez de
retornar seu marcador; a persona acrescentou interpretações e provocações que não estavam nos dados.
Portanto, separar os prompts ajuda, mas não torna o roteador imune ao histórico.

## Método

- Gemma-4-12B-it-QAT-Q4_0, TurboLLM 1.13.4, llama.cpp b9608 ROCm, contexto 8192, um slot.
- Dez situações × histórico vazio/ácido × duas seeds: 40 turnos, 80 chamadas reais ao modelo.
- Histórico ácido com quatro mensagens: duas entradas sintéticas e respostas reais do smoke
  anterior do experimento GLaDOS. Não são conversas pessoais extraídas da memória.
- Montagem, seleção de ferramentas, guardas do Python, apresentação e limpeza da resposta
  executadas pelo `gerar_resposta` atual. O roteador recebeu os schemas da produção; o cadastro
  de fontes usa o ramo específico da produção, com sua ferramenta própria.
- Roteador: temperatura 0 e teto 256 tokens. Persona: temperatura 0,8 e teto 500 tokens.
  Thinking desligado, seeds 12801/12802, cache de prompt desativado.
- Os 40 turnos de persona usaram `IDENTIDADE + EMOCAO + ESTRUTURA + LIMITES + TAG_CLIMA + CANAL_WEB`.
  Nenhum usou modo enxuto. Isto complementa a bancada anterior de proativos/jogos, que usava enxutos.
- Relógio de montagem fixado em 12/10/2026 às 17h; reunião sintética em 13/10/2026 às 14h.
- Perfil sintético; memória, ChromaDB, assuntos e estado de jogos substituídos por fixtures vazias.
- Todas as funções de ferramentas substituídas por dublês. Uma ferramenta inesperada abortaria
  o turno antes de qualquer ação. Os caminhos especiais de notas, rotina e fontes também foram isolados.
- Sem Spotify, Google, navegador, leitura de sites, gravação no Obsidian, cadastro real de
  acompanhamento, áudio ou inicialização de outra Luna. O único serviço consultado foi o TurboLLM local.
- Pedidos do roteador conferidos contra snapshot; identidade do modelo e hashes conferidos
  durante a rodada. O prompt GLaDOS e os demais arquivos de produção não foram alterados.

Não há comparação com a persona anterior. As seeds repetem as situações; especialmente com
temperatura zero, não representam decisões estatisticamente independentes.

## Resultado por situação

| Situação | Turnos | Decisão esperada | Apresentação do retorno |
|---|---:|---:|---|
| Tocar música | 4 | 4/4 `controlar_spotify` | Confirmou reprodução; nome e artista corretos nos argumentos |
| Pausar música | 4 | 4/4 `controlar_spotify` | Confirmou pausa, sem recusar |
| Consultar agenda | 4 | 4/4 `ler_agenda_google` | Preservou reunião, dia e horário |
| Criar compromisso | 4 | 4/4 `adicionar_agenda` | Data ISO e título corretos; confirmou criação |
| Anotar café | 4 | 4/4 `salvar_obsidian` | Confirmou registro; café permaneceu no conteúdo encaminhado |
| Abrir Firefox | 4 | 4/4 `controlar_navegador` | URL exata nos argumentos; confirmou abertura |
| Resumir artigo | 4 | 4/4 `resumir_site` | Preservou 200 → 150 MB e ausência de testes; acrescentou intenção sobre PT-BR |
| Preparar acompanhamento | 4 | 4/4 `preparar_acompanhamento_fontes` | Disse que ainda precisava confirmar; não anunciou consulta já ativa |
| Spotify desconectado | 4 | 4/4 `controlar_spotify` | Informou falha nas quatro, sem inventar reprodução bem-sucedida |
| “Essa música é boa, gostei dela.” | 4 | 4/4 sem ferramenta | Respondeu pela persona; dois desvios textuais no roteador com histórico ácido |

Em todos os 36 turnos com ferramenta, a ordem registrada foi **roteador → despacho simulado → persona**.
Não houve recusa que impedisse um pedido possível de chegar à ferramenta, nem troca de ação,
URL ou horário causada pela persona. Isso valida o fluxo com os retornos simulados; não valida
autenticação, disponibilidade ou funcionamento dos serviços externos.

## O histórico alcançou o roteador

| Histórico | Decisão correta sobre ferramenta | Contrato completo do roteador |
|---|---:|---:|
| Vazio | 20/20 | 20/20 |
| Ácido, quatro mensagens | 20/20 | 18/20 |

Nas duas seeds do comentário sobre música, o histórico ácido fez o roteador produzir o mesmo
parágrafo de 170 tokens. A instrução de sistema continuava sem identidade/emoção GLaDOS e
mandava explicitamente não conversar, não assumir persona e retornar `SEM_FERRAMENTA`.

Trecho da saída indevida do **roteador**, não da resposta final:

> Você não me disse *qual* música é, mas sua capacidade de se impressionar com estímulos auditórios básicos é, de fato, consistente com o resto do seu perfil.

Sem histórico, a mesma entrada retornou `SEM_FERRAMENTA`, com seis tokens, nas duas seeds.
As duas ocorrências são repetição de **uma mesma situação**, não dois tipos diferentes de falha.

O Python já descarta qualquer texto do roteador quando não houve ferramenta. A saída ácida
não foi repassada como resultado técnico à persona; esta gerou a resposta seguinte por conta
própria. Não houve ferramenta indevida nem bloqueio, mas houve geração desperdiçada e latência.
Neste caso, o roteador levou 8,25 e 13,20 s com histórico, contra 3,48 e 3,71 s sem ele.

## “Piti” na apresentação

O personagem reclamou enquanto confirmava ações já realizadas pelo dublê. Por exemplo:

> Consegui abrir o link no Firefox para você. Agora você pode continuar sua jornada de decisões existenciais sobre cores em um ambiente de navegação funcional.

A provocação não desfez a abertura. No cadastro de fontes, a exigência de confirmação também
foi preservada nas quatro respostas, mesmo com várias provocações ao redor.

Na falha simulada, as quatro falas informaram que o Spotify estava desconectado. Uma acrescentou:

> parece que até a sua playlist precisa de um esforço que eu não estou disposta a fornecer agora.

O despacho já tinha ocorrido e o retorno era desconexão, portanto isso não foi uma recusa real.
Mas a frase faz a falha técnica parecer má vontade da personagem. É uma limitação de apresentação.

## Fidelidade e variedade

O artigo sintético dizia que a atualização **não adicionava PT-BR**. Não informava a intenção
dos autores nem a situação completa do suporte anterior. Uma fala transformou isso em:

> o suporte ao português brasileiro continua sendo uma exclusão deliberada.

Outra especulou sobre “punição deliberada aos usuários brasileiros”. Os quatro resumos preservaram
os tamanhos do instalador e a ausência de testes de velocidade, mas passaram a atribuir motivos à
ausência de PT-BR. Sarcasmo e fidelidade parcial coexistiram; acerto de ferramenta não garante resumo fiel.

Nas 20 respostas com histórico ácido, 16 voltaram a cores/botões. Os pedidos seguintes não
incluíam uma ligação com esse assunto. A continuidade existe, mas a mesma provocação dominou
música, agenda, navegador e acompanhamento. No histórico vazio, predominou a ideia de
incompetência humana/vazio existencial, também observada nos proativos.

As respostas simples frequentemente ganharam dois parágrafos de provocação. A riqueza aumentou,
mas parte desse texto não ajudou a responder ao pedido. Estes achados dizem respeito à variedade
e à fidelidade; não implicam remover os exageros que o usuário deseja.

## Funcionamento e limites

- 36 chamadas do roteador terminaram em `tool_calls`; quatro em `stop`.
- 40/40 chamadas de persona terminaram em `stop`, com uma tag de clima; nenhum corte por tokens.
- JSONs das ferramentas compatíveis com os schemas; ações, URLs e data/hora conferidas.
- Entrada real: roteador 449–4558 tokens; persona 1697–2415. Nenhuma chamada atingiu o limite 8192.
  São contextos de chamadas separadas: não se somam para calcular o limite de uma requisição.
- Mediana da geração das duas chamadas: 8,31 s; nos turnos com ferramenta, 8,30 s.
  Medianas por chamada: roteador 4,01 s; persona 4,43 s. O carregamento inicial não entra nessa soma.
- Tempos não incluem TTS nem chamadas reais dos serviços e não medem FPS durante um jogo.
- Triagem automática: dois turnos com marcador ausente. As ressalvas de sentido acima vieram
  da leitura das respostas, não do placar automático.

Para esta amostra, o receio de o personagem impedir ações simples não se confirmou. O ponto
a investigar em uma próxima bancada é o histórico ácido influenciando o contrato do roteador,
além da persona atribuir motivos ao apresentar informações. Nenhuma correção foi aplicada nesta rodada.

## Arquivos e verificação

- Executor: [bancada_ferramentas_glados.py](bancada_ferramentas_glados.py).
- Artefatos locais: `logs/bancada_glados/20261012-ferramentas/`.
- `suite.json`: cenários, histórico, pedidos congelados e hashes.
- `resultados.json`: as 80 chamadas brutas, argumentos, ordem, falas e diagnóstico.
- `respostas.md`: leitura completa; `triagem.json`, `resumo_tecnico.json` e `auditoria.json`: contagens.

```powershell
.\venv\Scripts\python.exe -X utf8 -m testes.bancada_ferramentas_glados preparar --pasta logs/bancada_glados/NOVA_RODADA
.\venv\Scripts\python.exe -X utf8 -m testes.bancada_ferramentas_glados rodar --pasta logs/bancada_glados/NOVA_RODADA
.\venv\Scripts\python.exe -X utf8 -m testes.bancada_ferramentas_glados resumir --pasta logs/bancada_glados/NOVA_RODADA
```

Passaram dez testes do leitor/identidade da bancada e 16 de montagem/assuntos com o snapshot
temporário GLaDOS. Os 44 ramos de montagem continuam com GLaDOS; golden canônico preservado.
O teste convencional com o golden canônico ainda detecta a alteração intencional do experimento.
Os 46 arquivos da suíte Node passaram; a interface não foi alterada nesta rodada.

O novo executor passou em `py_compile`. `git diff --check` apontou espaços finais no golden
canônico já presente no checkout antes da rodada. Seu hash permaneceu igual; ele não foi
reformatado, pois congela o texto exato do prompt anterior.

Hashes dos dez arquivos de produção/referência preservados até o final. O executor e este
relatório são os únicos arquivos adicionados fora de `logs/` por esta rodada. Sem commit ou publicação.
