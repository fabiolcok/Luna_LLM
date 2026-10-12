# Vozes do Kokoro na web — 12/10/2026

Configurações → Uso → Voz oferece os 54 timbres em um seletor com nove grupos de origem.
Português brasileiro vem primeiro. Cada opção indica se a voz é feminina ou masculina,
e a origem da escolha aparece abaixo do campo. A escolha continua salva em `config_luna.json`.
Alpha permanece como padrão; a personalidade e o texto enviado ao LLM não mudaram.

O catálogo único em `modulos/vozes_kokoro.py` alimenta o servidor e a validação do TTS.
Todos os timbres usam o pipeline `lang_code='p'`; origem estrangeira pode trazer sotaque.
Voz inválida enviada pela web não é salva, e uma configuração antiga desconhecida volta
para Alpha. A troca vale para as próximas sínteses; o áudio já gerado permanece igual.

Validação:

- Suíte Node: 46 arquivos passaram, incluindo seleção, confirmação e reconexão.
- Python: 38 testes passaram (vozes, volume, execuções, leitura web e personalidade).
- Edge oculto: 54 opções e nove grupos, sem transbordamento lateral do painel em
  1920×1080, 900×900 e 420×900. A prévia não se conectou à Luna em execução.
- Os 54 arquivos oficiais foram baixados para o cache local e verificados como tensores
  finitos com dimensão de timbre compatível. O catálogo corresponde exatamente aos arquivos.
- Síntese real na CPU, sem reprodução de som: uma voz de cada grupo gerou WAV finito e
  não vazio usando a função `_sintetizar_wav` da Luna. Isso confirma funcionamento;
  qualidade, sotaque e preferência ainda dependem de ouvir cada voz.

Artefatos locais, ignorados pelo Git:

- `logs/bancada_web/20261012-vozes-kokoro/`: prévia e capturas.
- `logs/bancada_tts/kokoro-vozes-20261012/`: nove WAVs e resultado da síntese.

Fonte do catálogo: [Kokoro-82M — vozes](https://huggingface.co/hexgrad/Kokoro-82M/blob/main/VOICES.md).

## Favoritas

A lista usa um menu próprio com uma estrela em cada linha, permitindo marcar ou desmarcar
qualquer timbre sem primeiro escolhê-lo como voz ativa. As vozes marcadas passam para o grupo
`★ Favoritas`, no início da lista, sem duplicação. A opção também identifica sua origem
para distinguir vozes de mesmo nome. Clicar na estrela mantém o menu aberto;
clicar no nome escolhe o timbre e fecha a lista.
O grupo desaparece ao remover a última favorita.

As favoritas são salvas em `vozes_favoritas`, junto das demais configurações, e voltam
após reiniciar. Favoritar não troca o timbre ativo nem sintetiza áudio. O servidor altera
uma estrela por comando, preservando as outras preferências. A interface aguarda a
confirmação antes de acender a estrela e impede mudanças enquanto estiver desconectada.

Validação: os 23 testes Python de voz, volume e personalidade passaram na etapa de
persistência. Após mover as estrelas para dentro da lista, os 46 arquivos Node passaram,
incluindo favoritar outra voz sem selecioná-la, menu aberto, preservação de foco e teclado.
A prévia no Edge continuou sem transbordamento nas três resoluções, com duas favoritas,
54 opções únicas e dez grupos. Uma interação no navegador confirmou os comandos de
favoritar e selecionar, além de fechar por Escape ou clique fora. Capturas atuais em
`logs/bancada_web/20261012-vozes-menu/`.
