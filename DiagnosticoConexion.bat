@echo off
rem Prueba si esta PC puede descargar del COES, el BCRP y PyPI. No instala nada.
setlocal
cd /d "%~dp0"
set "CUANTO_COESTA_PAUSA=1"
set "PY="
if exist ".venv\Scripts\python.exe" set "PY=.venv\Scripts\python.exe"
if not defined PY (where py >nul 2>nul && set "PY=py -3")
if not defined PY (where python >nul 2>nul && set "PY=python")
if not defined PY (
    echo No se encontro Python en esta PC.
    pause
    exit /b 1
)
%PY% -m src.utils.diagnostico
