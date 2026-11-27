@echo off
setlocal EnableExtensions
chcp 65001 >nul
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"
cd /d "%~dp0"
for %%I in ("%~dp0.") do set "PROYECTO=%%~nxI"

echo === Inicializando entorno %PROYECTO% en Windows ===

set "PY_CMD="
py -3 -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)" >nul 2>&1
if not errorlevel 1 (
    set "PY_CMD=py -3"
) else (
    python -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)" >nul 2>&1
    if not errorlevel 1 (
        set "PY_CMD=python"
    )
)

if not defined PY_CMD (
    echo [ERROR] Se requiere Python 3.10 o superior instalado y disponible en PATH o mediante el launcher 'py'.
    exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
    echo [*] Creando entorno virtual en .venv...
    %PY_CMD% -m venv .venv
    if errorlevel 1 (
        echo [ERROR] No se pudo crear el entorno virtual .venv.
        exit /b 1
    )
) else (
    echo [OK] Entorno virtual .venv ya existe.
)

set "VENV_PY=.venv\Scripts\python.exe"

echo [*] Instalando dependencias y paquete editable...
"%VENV_PY%" -m pip install --quiet --upgrade pip
if errorlevel 1 exit /b 1
"%VENV_PY%" -m pip install --quiet -r requirements.txt
if errorlevel 1 exit /b 1
"%VENV_PY%" -m pip install --quiet -e .
if errorlevel 1 exit /b 1

if not exist ".env" (
    echo [*] Creando .env inicial desde .env.example...
    copy /y .env.example .env >nul
    if errorlevel 1 exit /b 1
    echo [AVISO] Se ha creado .env con datos de ejemplo. Editalo con tus datos personales.
) else (
    echo [OK] Archivo .env presente.
)

if exist ".git" if exist ".githooks" (
    echo [*] Configurando hooks de seguridad git en .githooks...
    git config core.hooksPath .githooks
)

echo [*] Verificando estado del kit y herramientas...
"%VENV_PY%" plantillas\tareas.py verificar
if errorlevel 1 (
    echo [AVISO] La verificacion reporto elementos faltantes ^(por ejemplo, LibreOffice o .env incompleto^).
)

echo.
echo [*] Ejecutando suite de pruebas unitarias...
"%VENV_PY%" -m unittest
if errorlevel 1 (
    echo [ERROR] Fallaron pruebas unitarias.
    exit /b 1
)

echo.
echo === Entorno listo para trabajar en Windows ===
exit /b 0
