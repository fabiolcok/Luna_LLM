# Piloto de expressões da Luna

Animated Noto Emoji © Google, licença CC BY 4.0:
https://creativecommons.org/licenses/by/4.0/
Origem: https://googlefonts.github.io/noto-emoji-animation/
Documentação: https://googlefonts.github.io/noto-emoji-files/?view=docs

99 arquivos Lottie baixados em 09/11/2026 de
https://fonts.gstatic.com/s/e/notoemoji/latest/CODIGO/lottie.json
Os JSON originais permanecem intactos. A prévia adapta cópias em memória:
oculta camadas de base selecionadas e, opcionalmente, troca preenchimentos
escuros por ciano. A adaptação é experimental, não aprovada pelo Google.
O catálogo é uma seleção de carinhas, não uma cópia de todo o Unicode.

Correções visuais do piloto: correcoes.js identifica explicitamente as camadas
de cabeça de dez animações com composições internas, preservando suas máscaras.
Cinco expressões com mãos amarelas e as mãos de Espiando recebem tons de ciano
com variação de luminosidade, incluindo degradês. Os originais não são alterados.
O filtro "Corrigidos para revisar" lista essas 15 expressões; o controle
"Aplicar correções visuais" permite comparar com a adaptação anterior.
Marcações de problema e favoritas não são apagadas nem consideradas aprovadas.

Player lottie-web 5.13.0 (Airbnb), licença MIT em LICENSE-lottie.md.
Origem: https://github.com/airbnb/lottie-web/tree/v5.13.0

avatar.svg e avatar.css são uma cópia de trabalho do avatar/estilos da Luna.
O piloto não abre WebSocket, não chama ferramentas, TTS ou LLM.
As bolinhas e os arcos são uma prévia; não executam os easter eggs de produção.

Abrir com a Luna já ligada: /static/piloto-emojis/index.html
Não precisa reiniciar. Nenhuma rota ou arquivo da interface principal foi alterado.
Favoritas e ajustes ficam na chave localStorage luna-piloto-emojis.
Para remover o piloto depois da avaliação, remover somente static/piloto-emojis
e limpar essa chave de localStorage. Exporte as escolhas antes, se quiser guardá-las.
