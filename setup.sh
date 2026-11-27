#!/usr/bin/env bash
# ==============================================================================
# Script de inicialización y verificación para document_generator (rubric-driven)
# ==============================================================================
set -euo pipefail

cd "$(dirname "$0")"
PROYECTO="$(basename "$(pwd)")"

echo "=== Inicializando entorno ${PROYECTO} ==="

# 1. Verificar Python 3
if ! command -v python3 >/dev/null 2>&1; then
    echo "[ERROR] python3 no está instalado en el sistema." >&2
    exit 1
fi

# 2. Crear entorno virtual si no existe
if [ ! -d ".venv" ]; then
    echo "[*] Creando entorno virtual en .venv/..."
    if ! python3 -m venv .venv 2>/dev/null; then
        echo "[!] ensurepip no disponible, inicializando con --without-pip..."
        python3 -m venv --without-pip .venv
        if command -v curl >/dev/null 2>&1; then
            curl -sS https://bootstrap.pypa.io/get-pip.py | .venv/bin/python
        elif command -v wget >/dev/null 2>&1; then
            wget -qO- https://bootstrap.pypa.io/get-pip.py | .venv/bin/python
        else
            echo "[ERROR] python3-venv no está instalado y no se encontró curl ni wget." >&2
            echo "        Instale python3-venv con: sudo apt install python3-venv" >&2
            exit 1
        fi
    fi
else
    echo "[OK] Entorno virtual .venv/ ya existe."
fi

# 3. Instalar o actualizar dependencias y paquete editable
echo "[*] Instalando dependencias de requirements.txt y paquete editable..."
.venv/bin/pip install --quiet --upgrade pip
.venv/bin/pip install --quiet -r requirements.txt
.venv/bin/pip install --quiet -e .

# 4. Asegurar archivo de configuración .env
if [ ! -f ".env" ]; then
    echo "[*] Creando .env inicial desde .env.example..."
    cp .env.example .env
    echo "[AVISO] Se ha creado .env con datos de ejemplo. Por favor edítalo con tus datos personales."
else
    echo "[OK] Archivo .env presente."
fi

# 5. Configurar githooks locales
if [ -d ".git" ] && [ -d ".githooks" ]; then
    echo "[*] Configurando hooks de seguridad git en .githooks/..."
    git config core.hooksPath .githooks
fi

# 6. Ejecutar suite de pruebas y verificación del sistema
echo "[*] Verificando estado del kit y herramientas..."
if ! .venv/bin/python plantillas/tareas.py verificar; then
    echo "[AVISO] La verificación reportó elementos faltantes (por ejemplo, LibreOffice o .env incompleto)."
fi

echo ""
echo "[*] Ejecutando suite de pruebas unitarias..."
.venv/bin/python -m unittest

echo ""
echo "=== Entorno listo para trabajar ==="
