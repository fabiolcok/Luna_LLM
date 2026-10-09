# Semente de humor na abertura de Hades — 2026-09-04

Escopo: somente comentário de abertura de jogo, sem alterar prompts gerais ou produção.
Comando: `venv\Scripts\python.exe -X utf8 testes/bancada_steam_ab.py --semente-hades --repeticoes 4`.
Resultados: `logs/bancada_steam_semente_20260904_232518.json` (local).
Modelo: Gemma 4 12B QAT Q4_0 do TurboLLM, confirmado no terminal.

12 respostas: quatro com instrução atual; quatro com dados opcionais; quatro com
os mesmos dados opcionais e uma semente: a desistência de ontem teve uma carreira
curtíssima. O terceiro braço permite comparar semente sem confundir seu efeito com
a retirada da obrigação de citar detalhe + horas. EMOCAO e ENXUTO_PROATIVO intactos.
As variantes foram alternadas na ordem de execução, com abordagem igual por rodada.
Fixtures pessoais isoladas pelo executor da bancada de persona; sem histórico de
falas anteriores entre gerações. Não é um teste do monitor completo com anti-repetição.

## Observações

- Semente: 4/4 respostas focaram na duração da desistência, 0/4 citaram horas de jogo.
- Atual: 4/4 citaram horas (uma corrompeu o número com "Três puluh cinco").
- Opcional sem semente: 0/4 citaram horas, mas voltaram a persistência, sofrimento e
  suposições como autossabotagem. Logo, omitir estatística não é ganho exclusivo da semente.
- Semente: 3/4 repetiram quase a mesma primeira frase sobre a desistência durar menos
  que carregar o menu/tela inicial. A quarta usou um suspiro. O foco melhorou, a
  diversidade ficou limitada nesta amostra.
- Segundas frases ainda perderam nexo: virar página e desistir no parágrafo seguinte
  inverte a situação, que era VOLTAR após desistir; "colocar o luto no currículo"
  mistura imagens sem uma ligação clara. Hipérbole por si só não foi penalizada.

Checks automáticos: 4/4 nos três braços; todos usaram núcleo enxuto COM EMOCAO;
nenhum prompt sofreu o corte de 1.500 caracteres. Os checks não medem nexo ou variedade.
Teste rápido: `node testes/rodar.js`, 36 arquivos passaram.

Conclusão editorial: a semente direcionou a piada para a contradição desejada, mas
não resolveu a coerência da continuação e induziu repetição. Não promover para
produção com base neste resultado. Quatro amostras de um único caso, sem seed pareada,
não estabelecem superioridade estatística nem generalização para outros jogos.
