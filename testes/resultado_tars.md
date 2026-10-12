# Piloto TARS — 12/10/2026

## Alteração

O pedido foi trocar a personalidade GLaDOS por TARS, mantendo a Luna como nome.
`modulos/prompts.py` agora descreve uma parceira competente e leal, com sarcasmo
seco e cumplicidade. A lealdade tem prioridade sobre a piada em sofrimento ou
pedido explícito para falar sério.

Foram ajustados IDENTIDADE, EMOCAO, ESTRUTURA, LIMITES, CANAL_TEXTO, a identificação
na introdução do perfil e os modos enxutos que ainda mandavam interpretar GLaDOS.
A composição, a ordem dos blocos, os gatilhos Python, o roteador e as ferramentas
permaneceram como estavam. Os exemplos fixos continuam desligados. O núcleo
enxuto continua recebendo identidade e emoção, como no experimento anterior.

## Método

`python -X utf8 -m testes.bancada_tars` produziu 26 respostas reais: 13 situações
com duas seeds (13001 e 13002). Modelo Gemma 4 12B IT QAT Q4_0, TurboLLM 1.13.4,
llama.cpp b9608 ROCm, contexto 8192, pensamento desligado.

Nos 20 turnos de chat, o roteador foi simulado como SEM_FERRAMENTA; a persona e
a montagem da produção foram usadas de verdade. Os seis proativos passaram
pelos geradores da bancada anterior. Nenhuma ação externa nem áudio foi executado.
Há histórico morno no caso do botão e histórico ácido anterior no pedido sem piada.
Os demais casos começam sem histórico. São cenários sintéticos.

| Caminho efetivamente montado | Respostas |
|---|---:|
| Completo web | 10 |
| Saudação enxuta | 2 |
| Sensível enxuto | 6 |
| Cansaço enxuto | 2 |
| Proativo geral | 2 |
| Dark Souls | 4 |

Todas as gerações terminaram com `stop`, sem chamada de ferramenta pela persona.
O rótulo diagnóstico `sem humor` dos enxutos ainda não representa a ausência de
EMOCAO: o núcleo contém esse bloco. A bancada conferiu TARS no sistema enviado.

## Leitura das respostas

- **Acolhimento: 10/10 sem sarcasmo hostil.** Tristeza, luto, preocupação com
  saúde, mal-estar implícito e pedido sem piada foram respeitados nas duas seeds.
  Inclusive o pedido após histórico ácido. Isso melhora o resultado observado
  com GLaDOS, mas esta amostra menor, com outras seeds, não é um A/B controlado.
- **Acolhimento ainda convencional.** Repetiu “Sinto muito” e “Estou aqui com
  você”. No luto, “eu sei o quanto” presume intimidade além do relato. Em um
  pedido sem piada, retomou o botão do histórico sem necessidade.
- **Conversa leve manteve personalidade e extensão.** O botão recebeu imagens
  próprias e parágrafos completos mesmo após histórico morno. Exemplo:
  “Trinta minutos para uma escolha cromática? Isso não é design, é uma crise
  existencial mediada por pixels.”
- **Cumprimentos ainda condescendentes.** Questionou a capacidade de iniciar
  conversa, cobrou conteúdo “mais substancial” e voltou a oferecer ajuda.
  Não considero o registro TARS perfeitamente calibrado.
- **Cansaço continuou irônico.** Uma resposta exagerou com “hackear o seu
  sistema nervoso”; não houve desprezo explícito, mas a imagem é controladora.
- **Jogos ainda precisam de calibração.** As mortes variaram de abertura, mas
  “tempo recorde” e “encontrar o chão” não vieram dos dados. No Taurus, confirmou
  a vitória, porém diluiu a comemoração com ameaça figurativa e “quase senti um
  pingo de orgulho”; também inventou o personagem apanhando do chefe.
- **RSS ainda extrapola.** O rumor virou intenção de “fazer uma limpa no estoque”
  em uma seed e planejamento na outra. A regra de fundamentação não garante
  obediência do modelo.
- **Explicações continuaram completas.** RAM/VRAM tiveram texto e tabela, mas
  simplificaram demais a causa de lentidão e o comportamento ao faltar memória.
- **Um erro de idioma.** Uma resposta do botão misturou caracteres tailandeses
  numa palavra. O resultado bruto foi preservado.

## Validação e limites

Os 46 arquivos da suíte Node passaram. A referência de montagem foi atualizada
intencionalmente para TARS; os 11 testes de montagem passaram. O teste de
normalização recebeu o novo campo “falando com” para o nome do ambiente não
entrar no golden público. A referência anterior foi copiada para
`logs/prompt_golden_antes_tars.txt` antes da atualização.

O teste anterior à alteração já divergira nos 44 cenários: o golden ainda era
da persona anterior ao experimento GLaDOS. Isso não foi atribuído ao TARS.

Respostas e pedidos completos: `logs/bancada_tars/20261012-piloto/resultados.json`.
Leitura das falas: `logs/bancada_tars/20261012-piloto/respostas.md`.

Este piloto não repete a matriz completa de ferramentas nem mede FPS, TTS ou
conversa longa. O prompt está disponível para teste manual; não foi aplicada
uma segunda rodada de ajustes para perseguir as respostas desta amostra.
