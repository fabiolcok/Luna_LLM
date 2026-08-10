@echo off
title Luna
rem %~dp0 = pasta DESTE arquivo; ".." sobe pra raiz do projeto.
rem Antes o caminho era cravado (G:\Projetos\Luna_LLM), entao em outra maquina o cd falhava,
rem o venv nao era ativado e o python do SISTEMA rodava o main.py — o erro que aparecia era
rem "No module named 'webview'", que nao tem nada a ver com a causa real.
rem
rem Estrutura com goto, e nao com "|| (... & ... & ...)": naquele formato o & vira separador
rem dentro dos parenteses e "%~dp0" termina em barra invertida, que escapa a aspa. Dava erro
rem de sintaxe e a janela fechava sem dizer nada.
cd /d "%~dp0.."
if errorlevel 1 goto :sem_pasta
if not exist "venv\Scripts\activate.bat" goto :sem_venv

call venv\Scripts\activate.bat
python main.py
pause
exit /b 0

:sem_pasta
echo.
echo  [ERRO] Nao consegui entrar na pasta do projeto a partir deste atalho.
echo.
pause
exit /b 1

:sem_venv
echo.
echo  [ERRO] Ambiente virtual nao encontrado em:
echo         %CD%\venv
echo.
echo  Crie uma vez, na pasta do projeto:
echo      python -m venv venv
echo      venv\Scripts\activate
echo      pip install -r requirements.txt
echo.
pause
exit /b 1
