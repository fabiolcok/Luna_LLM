@echo off
rem Abre um terminal ja com o ambiente da Luna ativado. Caminho relativo a ESTE arquivo
rem (%~dp0 = pasta dele, ".." = raiz do projeto) — nao depende de letra de unidade.
cd /d "%~dp0.."
if errorlevel 1 goto :sem_pasta
if not exist "venv\Scripts\activate.bat" goto :sem_venv

call venv\Scripts\activate
echo --- Ambiente Luna_LLM ativado em %CD% ---
cmd /k
exit /b 0

:sem_pasta
echo  [ERRO] Nao consegui entrar na pasta do projeto a partir deste atalho.
pause
exit /b 1

:sem_venv
echo.
echo  [ERRO] Ambiente virtual nao encontrado em:
echo         %CD%\venv
echo.
echo  Crie com:
echo      python -m venv venv
echo      venv\Scripts\activate
echo      pip install -r requirements.txt
echo.
pause
exit /b 1
