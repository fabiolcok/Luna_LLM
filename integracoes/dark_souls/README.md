# Piloto: Luna no Dark Souls Remastered

Primeira versão para **Windows 64 bits + Dark Souls Remastered**. Não ativa DS1
Prepare to Die, DS2 ou DS3: esses jogos precisam de leitores próprios.

Morte, chefe derrotado e fogueira liberada podem provocar uma fala da Luna.
Os acontecimentos recentes também entram no contexto do chat Web/voz; não vão
para conversas no Telegram. A leitura não identifica causa da morte, inimigo,
tentativas contra um chefe, combate atual ou estado emocional.

## Usar

No modo Web, abra **⚙ Configurações → Tarefas proativas → Jogos** e ligue
**Dark Souls Remastered (piloto)**. **Proativo** e **Monitorar jogos** também
precisam estar ligados para os comentários saírem. Os controles continuam visíveis
com o proativo desligado; o painel explica quando as falas estão pausadas.

Depois de atualizar o código, reinicie a Luna uma vez e recarregue a página para
carregar o novo controle. Depois disso, ativar/desativar pelo painel vale na hora.
Abra o Remastered e carregue o personagem. As falas só saem com o jogo em primeiro
plano e cedem à conversa. O piloto passa a observar sozinho; não precisa abrir
DSDeaths ou instalar .NET.

O **Não Perturbe** automático durante o jogo pausa os avisos gerais da Luna;
os comentários do piloto continuam permitidos.

Como alternativa, na raiz do projeto:

```powershell
.\venv\Scripts\python.exe -X utf8 -m integracoes.dark_souls.piloto ativar
```

```powershell
.\venv\Scripts\python.exe -X utf8 -m integracoes.dark_souls.piloto desativar
.\venv\Scripts\python.exe -X utf8 -m integracoes.dark_souls.piloto status
```

Painel e terminal usam a mesma configuração em `modelos/dark_souls_piloto.json`,
ignorado pelo Git. Sem esse arquivo o piloto fica desligado. Desativar descarta
eventos pendentes; reativar toma o progresso atual como referência.

## Comportamento

- Duas leituras consecutivas confirmam cada estado. A primeira leitura estável
  reconhece o progresso existente; não dispara falas sobre conquistas anteriores.
- Mudança de processo, slot, NG ou regressão de save cria uma referência nova.
  Ausência de leitura por mais de 30 segundos também cria uma referência nova.
- Mortes têm intervalo mínimo de 120 segundos entre falas. Chefes têm prioridade;
  fogueiras aguardam 90 segundos desde a última fala do piloto. Há um mínimo de
  15 segundos entre falas do piloto, inclusive vitórias.
- As falas espontâneas recebem o acontecimento da morte, sem total ou incremento
  do contador, inclusive no bloco MOMENTO. O prompt pede uma reação sem numerar
  mortes ou tentativas. A contagem interna continua detectando novas mortes.
- Eventos expiram: morte em 30 segundos, chefe em 90, fogueira em 60. Conversa,
  leitura indisponível, perda de foco ou desativação podem descartar comentários.
  A geração também é revalidada antes de publicar legenda/voz.
- O contexto guarda até três eventos por até três minutos e envia um resumo
  curto dentro do orçamento de 800 caracteres do bloco MOMENTO. Dados de jogo
  indisponível não são apresentados como atuais.
- Apenas mudanças observadas geram eventos. O leitor não mede mortes por chefe.
  Nomes de chefes/fogueiras ainda não descobertos não entram no prompt.

## Estilo dos comentários

Mortes, chefes derrotados e fogueiras liberadas usam `ENXUTO_DARK_SOULS + EMOCAO`.
A variante mantém o humor exagerado, mas permite uma reação simples quando não surgir
uma boa piada. Foi escolhida após a avaliação A/B; a qualidade durante a jogatina ainda
precisa ser observada. Chat, radar e abertura pela Steam usam seus caminhos anteriores.

Após atualizar, reinicie a Luna para carregar o prompt. O nome do ramo aparece no log
na linha `🧩 Prompt`. A integração continua sem enviar contagem de mortes para a fala.

## Verificar sem voz nem LLM

No log normal da Luna, `chefe derrotado | Taurus Demon` significa que a marca de
vitória mudou, não que o personagem entrou na arena. O registro antigo `chefe`
também tinha esse significado. A detecção é separada da fala: depois da tentativa
de comentário, o log registra entrega ou descarte, com o motivo disponível
(como perda de foco, leitura indisponível ou evento expirado). Uma geração sem
texto aproveitável também ganha um aviso. Os logs anteriores não guardavam todos
esses motivos; não permitem concluir por que uma fala deixou de sair.

```powershell
.\venv\Scripts\python.exe -X utf8 -m integracoes.dark_souls.piloto observar --segundos 60
.\venv\Scripts\python.exe -X utf8 -m unittest testes.testa_dark_souls testes.testa_momento testes.testa_execucoes
```

O diagnóstico escreve `logs/dark_souls/diagnostico.jsonl`. Não inicia Luna,
Telegram, áudio ou modelo. Leituras iniciais de mortes/chefes representam totais
do save; só as diferenças posteriores contam no acompanhamento.

Para avaliar o estilo em texto, sem emitir áudio nem precisar jogar:

```powershell
.\venv\Scripts\python.exe -X utf8 -m testes.bancada_dark_souls
```

Essa bancada chama o modelo já carregado no TurboLLM três vezes, com cenários
sintéticos. Leia as respostas: testes automáticos não garantem humor ou coerência.
Use `--preparar` para capturar apenas os prompts sem modelo carregado.

Validação da remoção da contagem: [resultado e limites da bancada](../../testes/resultado_dark_souls_sem_contagem.md).

Para comparar oito mortes seguidas com thinking ligado e desligado no Gemma 4 12B:

```powershell
.\venv\Scripts\python.exe -X utf8 -m testes.bancada_dark_souls_thinking --mortes 8
```

São 16 gerações, sem mudar a preferência de thinking da Luna. Cada modo recebe
suas próprias falas anteriores. A comparação salva textos e tempos em
`logs/dark_souls/thinking-*.md`; detalhes do experimento em
[testes/README.md](../../testes/README.md#piloto-dark-souls-remastered).

O coletor trabalha em CPU, uma leitura por segundo. A geração de falas ainda usa
o LLM e pode disputar GPU com o jogo. FPS/engasgos e qualidade da companhia
precisam ser avaliados durante uma sessão real.

## Origem e limites

[FONTES.md](FONTES.md) registra os projetos utilizados e a licença do leitor.
As versões de arquivo mapeadas são 1.0.0.0, 1.3.0.0 e 1.3.1.0; somente a versão
presente na máquina foi verificada ao preparar o piloto. Assinaturas desconhecidas,
ambíguas ou leituras incompletas suspendem a leitura. Compatibilidade com mods e
uso online não foi validada neste piloto.

## Repetição dos comentários de morte

Os comentários de morte passam por uma comparação textual com cinco falas recentes.
Se copiar demais, há uma segunda tentativa; persistindo a repetição, o comentário é descartado.
A memória é limitada à execução da Luna e não acrescenta contagem ao texto falado.
Ideias parecidas com palavras diferentes ainda podem escapar.

Teste sem rede:

    .\venv\Scripts\python.exe -X utf8 -m unittest testes.testa_repeticao_dark_souls

Bancada sem áudio:

    .\venv\Scripts\python.exe -X utf8 -m testes.bancada_repeticao_dark_souls

[Resultado e limites](../../testes/resultado_repeticao_dark_souls.md).
