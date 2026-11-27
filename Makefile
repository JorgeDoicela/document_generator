.PHONY: help setup verificar temas estado auditar test lint typecheck check-all clean

ifeq ($(OS),Windows_NT)
  PYTHON := .venv/Scripts/python.exe
  RUFF := .venv/Scripts/ruff.exe
  MYPY := .venv/Scripts/mypy.exe
  TAREAS := cmd /C tareas.bat
  SETUP := cmd /C setup.bat
else
  PYTHON := .venv/bin/python
  RUFF := .venv/bin/ruff
  MYPY := .venv/bin/mypy
  TAREAS := ./tareas
  SETUP := ./setup.sh
endif

PROYECTO := $(notdir $(CURDIR))

help:
	@echo "$(PROYECTO) - Framework Documental Rubric-Driven"
	@echo "=============================================="
	@echo "  make setup       Inicializa el entorno (.venv, dependencias y .env)"
	@echo "  make verificar   Valida herramientas (Python, LibreOffice, .env)"
	@echo "  make temas       Lista presets y temas documentales disponibles"
	@echo "  make estado      Muestra la tabla de avance de todas las materias"
	@echo "  make auditar     Ejecuta la auditoría estática global de todas las tareas"
	@echo "  make test        Ejecuta la suite de pruebas unitarias del kit"
	@echo "  make lint        Comprueba estilo y errores con ruff"
	@echo "  make typecheck   Verifica consistencia estática de tipos con mypy"
	@echo "  make check-all   Ejecuta lint, typecheck, test y auditar en secuencia"
	@echo "  make clean       Elimina archivos temporales y caché de Python"

setup:
	@$(SETUP)

verificar:
	@$(TAREAS) verificar

temas:
	@$(TAREAS) temas

estado:
	@$(TAREAS) estado

auditar:
	@$(TAREAS) auditar

test:
	@$(PYTHON) -m unittest

lint:
	@$(RUFF) check plantillas tests examples tools

typecheck:
	@$(MYPY) plantillas

check-all: lint typecheck test auditar
	@echo "[OK] Todas las comprobaciones (lint, mypy, unittest, auditar) pasaron exitosamente."

clean:
	@$(PYTHON) -c "import pathlib, shutil; raiz = pathlib.Path('.'); [shutil.rmtree(p, ignore_errors=True) for pat in ('**/__pycache__', '.mypy_cache', '.ruff_cache', '*.egg-info', '.pytest_cache') for p in raiz.glob(pat) if p.is_dir() and '.venv' not in p.parts]; [p.unlink(missing_ok=True) for pat in ('**/*.pyc', '**/*.py.bak') for p in raiz.glob(pat) if p.is_file() and '.venv' not in p.parts]"
	@echo "[OK] Archivos temporales y cachés eliminados."
