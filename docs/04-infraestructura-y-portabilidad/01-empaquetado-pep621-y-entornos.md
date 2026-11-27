# Empaquetado Estándar PEP 621 y Gestión de Entornos

Este documento describe la arquitectura de empaquetado del repositorio bajo los estándares modernos de Python (**PEP 517**, **PEP 518** y **PEP 621**), la instalación en modo editable y los mecanismos de resiliencia implementados para la creación del entorno virtual.

---

## 1. Especificación de `pyproject.toml`

El repositorio reemplaza las manipulaciones manuales de `sys.path` por la formalización del paquete `plantillas` mediante un archivo `pyproject.toml` declarativo estándar:

```toml
[build-system]
requires = ["setuptools>=61.0"]
build-backend = "setuptools.build_meta"

[project]
name = "document-generator"
version = "1.0.0"
description = "Framework documental multi-propósito guiado por rúbricas"
readme = "README.md"
requires-python = ">=3.10"
authors = [
    { name = "document_generator contributors" }
]
dependencies = [
    "python-docx>=1.1.2",
    "Pillow>=10.0.0",
    "lxml>=5.0.0",
    "pypdf>=4.0.0",
]

[project.optional-dependencies]
dev = [
    "ruff>=0.8.0",
    "mypy>=1.10.0",
]

[project.scripts]
tareas = "plantillas.tareas:main"

[tool.setuptools.packages.find]
where = ["."]
include = ["plantillas*"]

[tool.ruff]
line-length = 100
target-version = "py310"
exclude = [
    ".venv",
    "plantillas/tarea",
]

[tool.ruff.lint]
select = ["E", "F", "W", "I", "B"]
ignore = ["E501"]

[tool.mypy]
python_version = "3.10"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true
disallow_incomplete_defs = true
check_untyped_defs = true
exclude = [
    "plantillas/tarea/generar_documento\\.py$",
]
```

### Ventajas Arquitectónicas:
1. **Entrypoint de Sistema (`project.scripts`):** Al instalar el paquete en el entorno virtual (`pip install -e .`), se crea automáticamente un binario ejecutable `tareas` en `.venv/bin/tareas` (Linux/macOS) y `.venv\Scripts\tareas.exe` (Windows), resolviendo la invocación directa sin depender de la ruta del script.
2. **Modo Editable (`-e .`):** Cualquier cambio en los scripts de `plantillas/` toma efecto de forma instantánea sin requerir re-instalaciones.
3. **Dependencias de Desarrollo Aisladas (`dev`):** Herramientas de análisis de calidad (`ruff`, `mypy`) se instalan como opcionales (`pip install -e ".[dev]"`), manteniendo `requirements.txt` limpio para producción.
4. **Descubrimiento Automático de Paquetes:** `setuptools.packages.find` localiza `plantillas` y sus submódulos respetando la jerarquía de código.

---

## 2. Paridad de Dependencias (`requirements.txt`)

Para asegurar interoperabilidad tanto con herramientas basadas en `pip install -r requirements.txt` como con entornos basados en `pyproject.toml`, el archivo `requirements.txt` mantiene una sincronización estricta con las versiones mínimas probadas:

```text
python-docx>=1.1.2
Pillow>=10.0.0
lxml>=5.0.0
pypdf>=4.0.0
```

| Librería | Versión Mínima | Propósito Técnico |
|---|---|---|
| `python-docx` | `>=1.1.2` | Generación, formateo y manipulación del árbol WordML / OpenXML. |
| `Pillow` | `>=10.0.0` | Inspección de dimensiones, resolución DPI y procesamiento de capturas. |
| `lxml` | `>=5.0.0` | Parseo XML de alta velocidad para la auditoría estática en `comprobar.py`. |
| `pypdf` | `>=4.0.0` | Verificación de integridad y metadatos de los PDFs generados. |

---

## 3. Resiliencia en Creación del Entorno Virtual (`setup.sh`)

En distribuciones Linux derivadas de Debian o Ubuntu, el paquete base del sistema operativo `python3` suele suministrarse sin el módulo `ensurepip` preinstalado a nivel de sistema (separándolo en un paquete externo `python3-venv`). Si un usuario clona el repositorio e intenta ejecutar `python3 -m venv .venv`, el comando aborta.

Para eliminar esta fricción de manera transparente, `setup.sh` implementa un mecanismo de fallback resiliente de dos fases:

```mermaid
flowchart TD
    A["setup.sh: Inicialización de .venv"] --> B{"python3 -m venv .venv"}
    B -->|Éxito\n(ensurepip disponible)| C["pip disponible nativamente"]
    B -->|Fallo\n(ensurepip ausente)| D["python3 -m venv --without-pip .venv"]
    D --> E{"¿Existe curl o wget?"}
    E -->|curl / wget| F["Descarga e inyección segura de get-pip.py\n(bootstrap de pip en .venv)"]
    E -->|Ninguno| G["Error informativo:\nInstale python3-venv o curl"]
    C --> H["pip install -r requirements.txt && pip install -e ."]
    F --> H
```

### Implementación en `setup.sh`:

```bash
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
```

Este patrón garantiza que el entorno se autoconfigure con éxito en cualquier equipo limpio sin necesidad de permisos de superusuario (`sudo`).

---

## 4. Calidad Estática, Automatización y Configuración de IDE

Para mantener el código en estándares de producción continuos y preservar un entorno de trabajo limpio en el editor, el repositorio articula tres capas de soporte:

### A. Metas de Automatización en `Makefile`:

```makefile
lint:         # Comprueba estilo y errores sintácticos con ruff
typecheck:    # Verifica consistencia estática de tipos con mypy
test:         # Ejecuta la suite de 22 pruebas unitarias
auditar:      # Auditoría estática global de todas las materias
check-all:    # Ejecuta lint, typecheck, test y auditar en secuencia
clean:        # Elimina __pycache__, *.pyc, .mypy_cache, .ruff_cache y *.egg-info
```

### B. Configuración de Espacio de Trabajo en VSCode (`.vscode/settings.json`):

Para eliminar el ruido visual de carpetas de caché transitorias y mantener una presentación jerárquica en el explorador de archivos, se aplican dos directivas:

1. **Exclusión de Artefactos de Caché (`files.exclude`):**
   Oculta del panel lateral las carpetas efímeras generadas por herramientas de análisis (`.mypy_cache`, `.ruff_cache`, `*.egg-info`, `.pytest_cache`).
2. **Anidamiento Jerárquico de Archivos (`explorer.fileNesting`):**
   Agrupa visualmente bajo flechas desplegables los archivos relacionados en la raíz:
   - `tareas` anida `tareas.bat`
   - `setup.sh` anida `setup.bat`
   - `pyproject.toml` anida `requirements.txt`
   - `.env.example` anida `.env`
   - `.gitignore` anida `.gitattributes` y `.editorconfig`
