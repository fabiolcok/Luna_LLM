# Fontes do coletor Remastered

O leitor em `leitor.py` é uma adaptação em Python, sob GPL-3.0-only, dos
mapeamentos de memória, flags e fogueiras do **SoulMemory/SoulSplitter**.
Copyright (c) 2022 Frank van der Stam. A rotina de event flags credita também
JKAnderson/DSR-Gadget; o código de Remastered traz créditos a
CapitaineToinon/LiveSplit.DarkSoulsIGT. A licença integral está em `LICENSE`.

Versão de referência inspecionada: commit
`1248a03aef80b779d7ae53748b9f4ff11dd3935c` (SoulMemory 1.8.5).

- [Remastered.cs](https://github.com/FrankvdStam/SoulSplitter/blob/1248a03aef80b779d7ae53748b9f4ff11dd3935c/src/SoulMemory/DarkSouls1/Remastered.cs)
- [Boss.cs](https://github.com/FrankvdStam/SoulSplitter/blob/1248a03aef80b779d7ae53748b9f4ff11dd3935c/src/SoulMemory/DarkSouls1/Boss.cs)
- [Bonfire.cs](https://github.com/FrankvdStam/SoulSplitter/blob/1248a03aef80b779d7ae53748b9f4ff11dd3935c/src/SoulMemory/DarkSouls1/Bonfire.cs)
- [DSDeaths — confirmação do contador em GameDataMan + 0x98](https://github.com/quidrex/DSDeaths/blob/master/Program.cs)

O catálogo foi extraído das anotações e IDs dos enums Boss/Bonfire. Não inclui
o enum BonfireState. Preservamos os nomes de origem para não inventar traduções.

O piloto não carrega o DLL do SoulMemory nem executa a inicialização `IsJapanese`,
que cria uma thread remota. Não distribui nem depende do executável DSDeaths.
Usa exclusivamente consultas e leitura de memória do processo, sem escrita,
injeção, alterações de save ou arquivos na pasta do jogo. A troca com a Luna
consiste em snapshots e eventos; não há acesso a conta ou API Steam.
