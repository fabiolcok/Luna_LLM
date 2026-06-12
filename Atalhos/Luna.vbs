Set sh = CreateObject("WScript.Shell")
sh.Run "cmd /c cd /d G:\Projetos\Luna_LLM && call venv\Scripts\activate.bat && python main.py", 0, False
Set sh = Nothing
