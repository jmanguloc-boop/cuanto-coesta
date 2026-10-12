@echo off
rem Deja corriendo la consulta del precio cada 30 minutos al prender la PC,
rem sin ventana y sin permisos de administrador (acceso directo en la carpeta Inicio).
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\pythonw.exe" (
    echo Primero abre la app una vez con AbrirCuantoCOESta.bat
    pause
    exit /b 1
)
set "INICIO=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"
powershell -NoProfile -Command "$s=(New-Object -ComObject WScript.Shell).CreateShortcut($env:INICIO + \CuantoCOEStaAhora.lnk); $s.TargetPath=%~dp0.venv\Scripts\pythonw.exe; $s.Arguments=run_ahora.py --bucle; $s.WorkingDirectory=%~dp0; $s.Save()"
if errorlevel 1 (
    echo No se pudo crear el acceso directo.
    pause
    exit /b 1
)
start "" ".venv\Scripts\pythonw.exe" run_ahora.py --bucle
echo Listo: el precio se consultara cada 30 minutos, tambien al prender la PC.
echo Para desactivarlo borra CuantoCOEStaAhora en la carpeta Inicio de Windows.
pause
