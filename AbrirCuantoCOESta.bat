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
call :buscar_python
if not defined PY (
    echo No se encontro Python 3.11 o superior. Intentando instalarlo solo para tu usuario...
    where winget >nul 2>nul && winget install -e --id Python.Python.3.12 --scope user --silent --accept-package-agreements --accept-source-agreements
    call :buscar_python
)
if not defined PY (
    echo.
    echo No se pudo instalar Python automaticamente.
    echo Instala Python 3.12 desde https://www.python.org/downloads/
    echo marcando la casilla "Add Python to PATH" ^(no requiere administrador^)
    echo y vuelve a hacer doble clic en este archivo.
    exit /b 1
)
echo Usando %PY%
%PY% -m venv .venv || exit /b 1
if exist "wheels\" (
    echo Instalando librerias desde la carpeta wheels, sin internet...
    ".venv\Scripts\python.exe" -m pip install --no-index --find-links wheels -r requirements-app.txt || exit /b 1
) else (
    echo Descargando librerias ^(pandas, matplotlib...^)...
    ".venv\Scripts\python.exe" -m pip install --disable-pip-version-check -r requirements-app.txt || exit /b 1
)
exit /b 0

:buscar_python
rem Prueba que Python de verdad corra y sea 3.11+ (el acceso directo de la Microsoft Store no cuenta).
set "PY="
py -3 -c "import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)" >nul 2>nul && set "PY=py -3" && exit /b 0
python -c "import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)" >nul 2>nul && set "PY=python" && exit /b 0
for %%V in (313 312 311) do (
    if exist "%LOCALAPPDATA%\Programs\Python\Python%%V\python.exe" (
        set "PY="%LOCALAPPDATA%\Programs\Python\Python%%V\python.exe""
        exit /b 0
    )
)
exit /b 0

:error
echo.
echo No se pudo preparar la app. Corre DiagnosticoConexion.bat y revisa diagnostico_conexion.txt
if exist ".venv" rmdir /s /q ".venv"
pause
exit /b 1
