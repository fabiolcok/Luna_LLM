' Inicia o TurboLLM em segundo plano (janela oculta) no login do Windows.
' Usa caminhos COMPLETOS (node + turbollm global) pra NAO depender do PATH no login
' — que era o motivo de nao subir antes.
' --no-open = nao abre o navegador a cada boot.
' O modelo da Luna (Gemma-4-12B) carrega sob demanda (JIT) na primeira chamada dela.
Set s = CreateObject("WScript.Shell")
appdata = s.ExpandEnvironmentStrings("%APPDATA%")
s.Run """C:\Program Files\nodejs\node.exe"" """ & appdata & "\npm\node_modules\turbollm\bin\turbollm.mjs"" --no-open", 0, False
