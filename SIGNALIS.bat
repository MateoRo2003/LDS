@echo off
rem Abre SIGNALIS (doble clic). Antes hay que haber corrido instalar.bat una vez.
chcp 65001 >nul
cd /d "%~dp0"

if not exist ".venv\Scripts\pythonw.exe" (
    echo SIGNALIS todavia no esta instalado en esta computadora.
    echo Primero abri instalar.bat y espera a que termine.
    echo.
    pause
    exit /b 1
)

rem pythonw: sin ventana negra de consola. La app se cierra sola al cerrar su ventana.
start "" ".venv\Scripts\pythonw.exe" "app-python\app.py"
