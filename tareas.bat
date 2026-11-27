@echo off
setlocal EnableExtensions EnableDelayedExpansion
chcp 65001 >nul
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"

set "AQUI=%~dp0"
set "PYTHON_VENV=%AQUI%.venv\Scripts\python.exe"

if not exist "%PYTHON_VENV%" (
    echo [!] No se encontro el entorno virtual en .venv.
    echo [*] Ejecutando setup.bat para inicializar el entorno...
    call "%AQUI%setup.bat"
    if errorlevel 1 exit /b !errorlevel!
)

"%PYTHON_VENV%" "%AQUI%plantillas\tareas.py" %*
exit /b %errorlevel%
