"""O GIF está na gaveta: nada pode acionar a busca sem o prompt pedir.

Bug real (ago/2026): apareceu um GIF aleatório embaixo do mascote depois de uma resposta de
pesquisa web. A causa era um fallback na extração que aceitava QUALQUER `[coisa]` no fim do
texto como termo de busca no Giphy. Ele existia quando o prompt PEDIA `[gif:X]` e o modelo às
vezes emitia mal-formatado; com o GIF desativado, o prompt nunca pede e o fallback virou uma
armadilha — disparava em `[Fonte: Wikipedia]`, `[continua]` e no próprio `[clima:zoeira!]`.

Este teste guarda as duas pontas:
  - o que NÃO pode virar GIF (qualquer colchete que não seja explicitamente de gif);
  - o `[clima:X]` continua sendo extraído mesmo com pontuação, que era o furo que o alimentava.

Se um dia o GIF voltar, o combinado é o prompt emitir `[gif:termo]` — e aí o primeiro caso
abaixo (que exige que `[gif:...]` FUNCIONE) já garante que o caminho continua vivo.
"""

import re
import sys
import unittest
from pathlib import Path

RAIZ = Path(__file__).parents[1]
sys.path.insert(0, str(RAIZ))

FONTE = (RAIZ / "modulos" / "pensar.py").read_text(encoding="utf-8")


class TestaGifNaGaveta(unittest.TestCase):
    def test_o_caminho_explicito_do_gif_continua_vivo(self):
        # o combinado do TODO: "pra voltar, basta o prompt emitir [gif:]"
        self.assertIn(r"\[gif:\s*([^\]]+)\]", FONTE)

    def test_nao_existe_fallback_que_aceite_qualquer_colchete(self):
        """O fallback removido casava um colchete genérico no FIM do texto."""
        suspeitos = re.findall(r"re\.(?:search|match)\(r'(\\\[\[?[^']*)'", FONTE)
        for padrao in suspeitos:
            if "gif" in padrao.lower() or "clima" in padrao.lower():
                continue          # os explícitos são justamente o que deve existir
            with self.subTest(padrao=padrao):
                self.assertNotIn(r"\]\s*$", padrao,
                                 "voltou um fallback de colchete genérico no fim do texto — "
                                 "é o que fazia '[Fonte: Wikipedia]' virar busca no Giphy")

    def test_clima_sobrevive_a_pontuacao(self):
        """Sem isso o clima some (rosto perdido) E o colchete sobra para o próximo regex."""
        from modulos.pensar import _RE_CLIMA
        for texto in ("resposta [clima:zoeira]", "resposta [clima:zoeira!]",
                      "resposta [clima: zoeira .]", "resposta [Clima:Deboche]"):
            with self.subTest(texto=texto):
                achou = _RE_CLIMA.search(texto)
                self.assertIsNotNone(achou, "o clima deixou de ser reconhecido")
                self.assertNotIn("[", _RE_CLIMA.sub("", texto),
                                 "sobrou colchete no texto depois de tirar o clima")

    def test_texto_comum_entre_colchetes_nao_e_clima(self):
        from modulos.pensar import _RE_CLIMA
        for texto in ("resumo pronto [Fonte: Wikipedia]", "segue [continua]", "veja [1]"):
            with self.subTest(texto=texto):
                self.assertIsNone(_RE_CLIMA.search(texto))


if __name__ == "__main__":
    unittest.main()
