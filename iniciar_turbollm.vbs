' Inicia o TurboLLM em segundo plano (janela oculta) no login do Windows.
' Usa caminhos COMPLETOS (node + turbollm global) pra NAO depender do PATH no login
' — que era o motivo de nao subir antes.
' --no-open = nao abre o navegador a cada boot.
' O modelo da Luna (Gemma-4-12B) carrega sob demanda (JIT) na primeira chamada dela.
Set fso = CreateObject("Scripting.FileSystemObject")
Set s = CreateObject("WScript.Shell")
appdata = s.ExpandEnvironmentStrings("%APPDATA%")

' O node nem sempre esta em Program Files (instalador por usuario, nvm, winget...).
' Sem esta checagem o script falhava calado no login e a Luna dava 503 sem explicacao.
node = "C:\Program Files\nodejs\node.exe"
If Not fso.FileExists(node) Then node = "node"      ' cai pro PATH

turbo = appdata & "\npm\node_modules\turbollm\bin\turbollm.mjs"
If Not fso.FileExists(turbo) Then
    MsgBox "TurboLLM nao encontrado em:" & vbCrLf & turbo & vbCrLf & vbCrLf & _
           "Instale com:  npm install -g turbollm", vbExclamation, "Luna"
    WScript.Quit 1
End If

s.Run """" & node & """ """ & turbo & """ --no-open", 0, False
Set s = Nothing
