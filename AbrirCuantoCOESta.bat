@echo off
rem Cuanto COESta: abre la app de escritorio con doble clic (sin .exe, sin permisos de administrador).
setlocal
cd /d "%~dp0"


if not exist ".venv\Scripts\pythonw.exe" (
    call :instalar
    if errorlevel 1 goto :error
)
start "" ".venv\Scripts\pythonw.exe" app\escritorio.py
exit /b 0

:instalar
echo Primera vez: preparando Cuanto COESta. Tarda unos minutos...
set "PY="
where py >nul 2>nul && set "PY=py -3"
if not defined PY (where python >nul 2>nul && set "PY=python")
if not defined PY (
    echo No se encontro Python. Instala Python 3.11 o superior desde python.org
    echo y marca la casilla "Add Python to PATH". No requiere administrador.
    exit /b 1
)
%PY% -m venv .venv || exit /b 1
if exist "wheels\" (
    echo Instalando librerias desde la carpeta wheels, sin internet...
    ".venv\Scripts\python.exe" -m pip install --no-index --find-links wheels -r requirements-app.txt || exit /b 1
) else (
    ".venv\Scripts\python.exe" -m pip install -r requirements-app.txt || exit /b 1
)
exit /b 0

:error
echo.
echo No se pudo preparar la app. Corre DiagnosticoConexion.bat y envia diagnostico_conexion.txt
if exist ".venv" rmdir /s /q ".venv"
pause
exit /b 1
