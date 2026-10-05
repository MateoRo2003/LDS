@echo off
rem Instala SIGNALIS en esta computadora. Se corre una sola vez (doble clic).
rem Necesita Python 3.11 o mas nuevo y conexion a internet.
chcp 65001 >nul
cd /d "%~dp0"

where python >nul 2>nul
if errorlevel 1 (
    echo.
    echo No encontre Python en esta computadora.
    echo Instalalo desde https://www.python.org/downloads/ marcando la casilla
    echo "Add python.exe to PATH", y despues volve a abrir este archivo.
    echo.
    pause
    exit /b 1
)

echo Preparando SIGNALIS. Puede tardar varios minutos: descarga unos 700 MB.
echo.
python -m venv .venv
if errorlevel 1 goto error
.venv\Scripts\python -m pip install --upgrade pip
.venv\Scripts\python -m pip install -r app-python\requirements.txt
if errorlevel 1 goto error

echo.
echo Listo. Para abrir la aplicacion, doble clic en SIGNALIS.bat
echo.
pause
exit /b 0

:error
echo.
echo Algo fallo durante la instalacion. Sacale una foto a esta ventana y mandasela al profesor.
echo.
pause
exit /b 1
