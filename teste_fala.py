# teste_fala.py — banco de testes da VOZ da Luna (Kokoro).
# --------------------------------------------------------------------------
# Pra que serve: digitar um texto e OUVIR na hora. Ideal pra achar a grafia
# certa de uma palavra ANTES de cadastrar no dicionário de pronúncia
# (_PRONUNCIA em modulos/falar.py).
#
# Como rodar (na pasta do projeto):
#     venv\Scripts\python teste_fala.py
#
# Uso: digite qualquer frase e ENTER pra ela falar.
# Comandos:
#     /voz alpha|bella|nicole   troca a voz
#     /vel 0.9                  troca a velocidade (0.7 a 1.5)
#     /cmp palavra g1 g2 ...     fala cada grafia candidata, uma a uma (comparar)
#     /dic                      liga/desliga a correção do dicionário de pronúncia
#     /rep                      repete a última fala
#     /q  (ou Ctrl+C)           sai
#
# Dica pro teu caso: pra decidir entre "raipe" e "raypi", digite:
#     /cmp hype raipe raypi raipi
# ...ouça as três e veja qual soa como "raipe" de verdade. Depois é só pôr a
# vencedora no _PRONUNCIA de falar.py:  "hype": "raypi",
# --------------------------------------------------------------------------

import sys
import time
from modulos import falar

# nomes curtos -> nomes reais das vozes do Kokoro
_VOZES = {"alpha": "jf_alpha", "bella": "af_bella", "nicole": "af_nicole"}

# estado local do teste
_usar_dic = True          # aplicar o dicionário de pronúncia?
_re_pronuncia_backup = falar._RE_PRONUNCIA   # guarda o regex pra ligar/desligar


def _aplicar_dic(ligado):
    """Liga/desliga a correção de pronúncia mexendo no regex do módulo falar."""
    falar._RE_PRONUNCIA = _re_pronuncia_backup if ligado else None


def _falar(texto):
    falar.falar_texto(texto)   # sintetiza e toca (bloqueia até terminar)


def _cabecalho():
    print("\n" + "=" * 60)
    print("  BANCO DE TESTES DA VOZ DA LUNA (Kokoro)")
    print("=" * 60)
    print(f"  voz={falar._voz_padrao}  velocidade={falar._velocidade_padrao}  "
          f"dicionário={'ON' if _usar_dic else 'OFF'}")
    if falar._PRONUNCIA:
        print(f"  dicionário atual: {falar._PRONUNCIA}")
    print("  Comandos: /voz  /vel  /cmp  /dic  /rep  /q")
    print("  Digite um texto e ENTER pra ouvir.\n")


def main():
    global _usar_dic
    if falar._pipe is None:
        print("Kokoro não carregou — não dá pra testar a voz. Veja o erro acima.")
        return

    _cabecalho()
    while True:
        try:
            linha = input("fala> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nAté!")
            break
        if not linha:
            continue

        # ---- comandos ----
        if linha in ("/q", "/sair", "/quit"):
            print("Até!")
            break

        if linha == "/dic":
            _usar_dic = not _usar_dic
            _aplicar_dic(_usar_dic)
            print(f"  dicionário de pronúncia: {'ON' if _usar_dic else 'OFF'}")
            continue

        if linha == "/rep":
            if not falar.repetir_ultima_fala():
                print("  (nada pra repetir ainda)")
            else:
                time.sleep(0.2)
            continue

        if linha.startswith("/voz"):
            arg = linha[4:].strip().lower()
            if arg in _VOZES:
                falar.configurar_voz(voz=_VOZES[arg])
                print(f"  voz agora: {falar._voz_padrao}")
            else:
                print(f"  vozes: {', '.join(_VOZES)}")
            continue

        if linha.startswith("/vel"):
            arg = linha[4:].strip().replace(",", ".")
            try:
                falar.configurar_voz(velocidade=float(arg))
                print(f"  velocidade agora: {falar._velocidade_padrao}")
            except ValueError:
                print("  uso: /vel 0.9   (entre 0.7 e 1.5)")
            continue

        if linha.startswith("/cmp"):
            partes = linha[4:].split()
            if len(partes) < 2:
                print("  uso: /cmp palavra grafia1 grafia2 ...   (ex: /cmp hype raipe raypi)")
                continue
            palavra, candidatas = partes[0], partes[1:]
            print(f"  comparando pronúncias de '{palavra}' — dicionário desligado pro teste:")
            _aplicar_dic(False)     # fala as grafias EXATAS, sem o dict interferir
            for c in candidatas:
                print(f"    → '{c}'")
                _falar(c)
                time.sleep(0.4)
            _aplicar_dic(_usar_dic)  # restaura o estado que estava
            print(f"  Escolha a melhor e ponha em falar.py:  \"{palavra}\": \"<grafia>\",")
            continue

        # ---- texto comum: fala ----
        _falar(linha)


if __name__ == "__main__":
    main()
