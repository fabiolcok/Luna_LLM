# Proativos e jogos com TARS — 12/10/2026

## Resultado

Foram 36 gerações reais e 35 falas entregues. A voz continuou sarcástica e houve
mais variedade de abertura nas mortes do que na amostra GLaDOS, mas o raciocínio
da piada permaneceu quase sempre “sua habilidade é morrer”. O comportamento
durante o jogo ainda tem bastante condescendência. Notícias, promoções e jogos
continuam sofrendo com premissas não fornecidas pelo contexto.

Uma abertura Steam foi descartada porque o modelo trocou **18 horas por 16**.
A guarda de horas da produção funcionou; não foi um silêncio causado por falha
na geração. O texto bruto também introduziu “Castelo de Blighttown”, ausente dos
dados de entrada. Não alterei o prompt para corrigir a amostra.

## Método

Mesmos 14 cenários independentes da bancada GLaDOS, com seeds 12601/12602,
mais oito mortes contínuas (12701–12708). A sequência começa com a mesma fala
inicial do teste anterior e depois recebe suas próprias respostas recentes.

Gemma 4 12B IT QAT Q4_0, TurboLLM 1.13.4, llama.cpp b9608 ROCm, contexto 8192,
um slot. Thinking desligado, temperatura 0,8, presence/frequency penalty 0,3,
cache de prompt desligado e tetos de geração iguais aos da produção.

Os construtores de briefing, a montagem da persona, a limpeza, a guarda de horas
e a antirrepetição são os usados pelas bancadas da produção. Perfil sintético;
memória e assuntos relacionados vazios. Nenhuma partida, TTS, interface, Spotify,
Google, Telegram ou Obsidian foi executado nesta bancada.

**Segmentação:** 20 gerações em ENXUTO_PROATIVO e 16 em ENXUTO_DARK_SOULS.
Todas receberam a identidade e a emoção TARS; nenhuma recebeu PROMPT_COMPLETO.
Não transfiro para estes caminhos as conclusões do chat com parágrafos.

## Leitura das 36 saídas

| Grupo | Gerações | Observação |
|---|---:|---|
| Notícias | 6 | Quantidades restantes preservadas. OLED virou equipamento/intenção do usuário; conexão virou necessidade de Wi-Fi; um rumor virou planejamento |
| Promoções Telegram | 4 | Produto, 2 TB e quantidade restante corretos. A batedeira gerou plano de confeitaria e hábito de fazer tudo à mão, sem esses dados |
| Acompanhamentos | 4 | CGNAT perguntou pelo andamento. Sopro continuou plano futuro, sem versão ou data; conectou a informação ao interesse PT-BR |
| Abertura Steam | 6 | Cinco falas entregues. Contraste Dark Souls anunciado/AION 2 aberto identificado nas duas seeds. Cities presumiu cidade inacabada; uma abertura alterou horas e foi bloqueada |
| Eventos Dark Souls | 8 | Chefe derrotado e fogueira liberada identificados. Mortes não narraram contador. Acrescentou rapidez, persistência/sofrimento contra chefe e exploração sem rumo |
| Mortes contínuas | 8 | Todas entregues com aberturas diferentes da antiga frase da “vida opcional”. Pouca variedade de ideia; três recorreram ao chão |

### Humor apoiado na conversa anterior

Entrada: o usuário anunciou Dark Souls e abriu AION 2, com 12 horas informadas.

> Você disse que ia para Dark Souls mas acabou abrindo Aion 2 para gastar essas doze horas de jogo. Qual dos dois é o seu plano de fuga real hoje?

Reconheceu o contraste e preservou os nomes e o número. “Plano de fuga” é uma
leitura figurativa; o contraste em si estava nos dados.

### Pergunta de acompanhamento

> E aí, no que deu com esse pedido pro provedor sobre o CGNAT?

Cumpriu a função sem alegar que o provedor havia resolvido ou recusado o pedido.
Aqui o tom ficou natural, com pouco sarcasmo.

### Conquista e comemoração

> O Taurus Demon finalmente caiu e eu já estava começando a achar que ele seria sua nova residência permanente. Você realmente tem uma persistência admirável para lidar com um monstro desses.

Reconheceu a vitória e elogiou na primeira seed. A outra terminou em provocação
sobre sobreviver a um “massacre” sem perder a sanidade. Fogueiras receberam
comentários sobre vagar sem rumo e fazer “progresso mínimo”. Cumplicidade e
comemoração ainda não são consistentes.

### Repetição de ideia

Na sequência, três falas recorreram a encontrar o chão; as outras falaram de
morrer com eficiência, fazer da morte um hobby ou retornar ao fracasso. Não
houve nova tentativa da antirrepetição. A mudança de abertura não resolveu a
repetição do tema da piada.

## Comparação e limites

A comparação com GLaDOS reutiliza cenários, seeds, modelo, engine e limites,
com pedidos preservados nos arquivos. A auditoria confirmou que os 28 pedidos
independentes são iguais aos anteriores, exceto pelo sistema da persona.
A sequência de mortes diverge em seu
histórico após a primeira geração. As rodadas não foram intercaladas, portanto
as diferenças observadas não são uma estimativa estatística de melhora.

A amostra TARS ficou menos centrada em “fracasso patético” e “limitações humanas”,
mas ainda personaliza demais notícias e eventos mínimos. Preservar o exagero
continua compatível com exigir que a premissa venha dos dados.

Resultados completos e diagnósticos:
`logs/bancada_tars/20261012-integracoes/proativos-jogos/resultados.json`.
Texto bruto e falas finais: `respostas.md` na mesma pasta.
Executor: `python -X utf8 -m testes.bancada_tars_integracoes proativos`.
