' Sobe a Luna SEM janela de terminal (pra atalho no menu iniciar / na barra de tarefas).
' O caminho sai do proprio arquivo: ScriptFullName -> pasta Atalhos -> raiz do projeto.
' Antes era cravado em G:\Projetos\Luna_LLM, o que quebrava em qualquer outra maquina.
Set fso = CreateObject("Scripting.FileSystemObject")
raiz = fso.GetParentFolderName(fso.GetParentFolderName(WScript.ScriptFullName))

If Not fso.FileExists(raiz & "\venv\Scripts\activate.bat") Then
    MsgBox "Ambiente virtual nao encontrado em:" & vbCrLf & raiz & "\venv" & vbCrLf & vbCrLf & _
           "Crie uma vez, na pasta do projeto:" & vbCrLf & _
           "    python -m venv venv" & vbCrLf & _
           "    venv\Scripts\activate" & vbCrLf & _
           "    pip install -r requirements.txt", vbExclamation, "Luna"
    WScript.Quit 1
End If

Set sh = CreateObject("WScript.Shell")
sh.Run "cmd /c cd /d """ & raiz & """ && call venv\Scripts\activate.bat && python main.py", 0, False
Set sh = Nothing
