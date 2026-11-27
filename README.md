# document_generator — Framework Documental Multi-Propósito (Rubric-Driven)

Framework programático en Python para la generación, estructuración y auditoría estática de **documentos académicos y profesionales** bajo el estándar oficial **APA 7.ª edición** y **temas personalizados vía JSON (`theme.json`)** en formato **WordML (`.docx`)** y **PDF vectorial**.

El principio rector del sistema es determinista: los criterios de evaluación o requisitos del documento gobiernan la estructura, y un auditor estático verifica el XML resultante antes de entregarlo.

> **Nota de procedencia:** Este proyecto nace como una derivación y extensión adaptada a partir de [rubric-driven](https://github.com/JosephBano/rubric-driven), creado originalmente por **Joseph Andrés Baño Naranjo** bajo licencia MIT. Consulta la sección [Origen del Proyecto y Adaptaciones](#origen-del-proyecto-y-adaptaciones) para el detalle técnico de los cambios incorporados.

---

## Capacidades Principales

1. **Estándar APA 7 y Sistema de Temas JSON (`plantillas/temas.py`, `formato_institucional.py`, `apa_docx.py`):**
   - **Preset oficial integrado (`apa7`):** norma APA 7.ª edición (papel US Letter, Times New Roman 12 pt, doble espacio, márgenes de 1", encabezados niveles 1–3 sin espaciado redundante, control de viudas/huérfanas, paginación superior derecha en Times New Roman 12 pt y tablas de 3 líneas).
   - **Temas institucionales/personalizados (`theme.json`):** configura colores, tipografía, interlineado, márgenes, encabezados, logos y banners sin tocar Python, o extráelos automáticamente desde cualquier `.docx` con `./tareas temas --extraer`. Los temas privados se guardan en `themes/local/` (ignorados por Git).
2. **Ingeniería OpenXML de Alta Fidelidad (`omml.py`, `bloques.py`, `visual.py`):**
   - **Ecuaciones matemáticas OMML vectoriales (`omml.py`):** convierte expresiones y comandos LaTeX a Unicode + XML OMML (`<m:oMathPara>`) compatible con Microsoft Word y LibreOffice (sin caracteres rotos ni desbordes horizontales).
   - **Bloques editoriales universales (`bloques.py`):** texto enriquecido Markdown (`**negrita**`, `*cursiva*`, `` `código inline` ``, superíndices/subíndices), párrafos estructurados sin estiramiento tipográfico, resúmenes ejecutivos con palabras clave, índices automáticos nativos (TOC), metadatos Core Properties y figuras con pies idempotentes.
   - **Tablas con layout fijo (`w:tblLayout="fixed"`):** soporte nativo para estilo **APA 7** (3 líneas horizontales) y **Grid** (cuadrícula completa), con anchos proporcionales y repetición de cabeceras en saltos de página.
   - **Renderizadores visuales a 300 DPI (`visual.py`):** capturas sintéticas de terminal CLI (temas `Dark` y `Light`), bloques de código estilizados y tarjetas académicas sobrias.
3. **Entrada Declarativa Markdown/YAML y Citación Multi-Estilo (`markdown_docx.py`, `apa_docx.py`, `preview_tema.py`):**
   - Compila archivos Markdown con frontmatter YAML directamente a `.docx`/`.pdf` (`./tareas compilar documento.md`) conservando marcadores de rúbrica (`{#C1}`), ecuaciones OMML (`$$ ... $$`), tablas, código y citas declarativas (`[@clave]`, `@clave`).
   - Soporta citación y referencias en **APA 7**, **IEEE numérico (`[1]`)** y **Vancouver (`(1)`)**, con auditoría estática biyectiva automática en `comprobar.py`.
   - Genera muestras visuales rápidas de cualquier tema o de todos los temas con `./tareas temas --preview <tema|todos>`.
4. **Pipeline Guiado por Rúbricas y Auditoría Estática (`rubrica.py`, `esqueleto.py`, `comprobar.py`):**
   - Importa rúbricas desde `.docx` o `TAREA.md` y genera esqueletos ponderados por puntaje.
   - Audita el `.docx` a nivel XML: cobertura del 100% de criterios (`w:bookmarkStart`), proporcionalidad de palabras, correspondencia biyectiva entre citas y referencias (APA 7, IEEE y Vancouver), detección de fugas LaTeX/Markdown y prevención de defectos visuales.
5. **Ecosistema de Agentes IA (`.agents/`):**
   - Incluye reglas (`AGENTS.md`) y 4 skills especializadas (`.agents/skills/`) para flujos asistidos por IA en análisis de consignas, rigor académico, ingeniería OpenXML y laboratorios técnicos.
6. **Privacidad por Diseño:**
   - El workspace personal del usuario (`materias/*`), los temas privados (`themes/local/*`) y las vistas previas (`themes/.previews/*`) conservan únicamente sus archivos `.gitkeep` en Git y su contenido queda excluido junto con `.env` por defecto.

---

## Inicio Rápido Multiplataforma

### Requisitos Previos
- **Python 3.10+** (probado en Python 3.10 a 3.13 en Linux y Windows).
- **Git**.
- **LibreOffice** (opcional, requerido únicamente para la exportación automatizada a PDF).

### Linux y macOS
```bash
git clone https://github.com/JorgeDoicela/document_generator.git && cd document_generator
./setup.sh
cp .env.example .env      # editar con tus datos
./tareas verificar
./tareas temas
```

### Windows (PowerShell o CMD)
```powershell
.\setup.ps1
Copy-Item .env.example .env
.\tareas.ps1 verificar
.\tareas.ps1 temas
```

### Probar los Ejemplos Reproducibles en 1 Comando
```bash
# Ejemplo programático (Python -> DOCX)
python examples/ejemplo_completo/generar_documento.py
./tareas comprobar examples/ejemplo_completo

# Ejemplo declarativo (Markdown/YAML -> DOCX con citas IEEE y OMML)
./tareas compilar examples/ejemplo_markdown/documento.md --sin-pdf
```

---

## Uso Rápido como Generador de Documentos

### 1. Generar cualquier tipo de documento desde Python
```python
from plantillas import bloques, formato_institucional as inst, omml

doc = inst.nuevo_documento_tematico(
    titulo="Arquitectura de Microservicios",
    subtitulo="Especificación Técnica — RFC-01",
    tema="apa7",             # apa7 | nombre_tema | ruta/theme.json
    incluir_indice=True,
)
bloques.resumen_ejecutivo(doc, "Resumen ejecutivo del documento.", palabras_clave=["APA 7", "OpenXML"])
inst.titulo_seccion(doc, "1. Modelo Matemático", nivel=1, criterios="C1")
omml.formula_bloque(doc, r"\forall x \in \mathcal{S} : \text{Latencia}(x) \leq 50\text{ ms}", "Ecuación 1.")
inst.guardar_documento(doc, "informe_apa7.docx")
```

### 2. Extraer o crear tu propio tema institucional o corporativo
```bash
# Extraer automáticamente tipografía, márgenes, colores e imágenes desde cualquier .docx oficial
./tareas temas --extraer enunciado/plantilla.docx --nombre mi-universidad

# O crear un molde manual en themes/local/ (ignorado por Git)
./tareas temas --crear mi-universidad --base apa7 --local
```
El comando `--extraer` analiza el OpenXML del documento de referencia y genera `themes/local/mi-universidad/theme.json` con sus activos gráficos listos para usar con `tema="mi-universidad"`.

### 3. Flujo Completo Guiado por Rúbricas
```bash
./tareas materia ingenieria-software "Ingeniería de Software"
./tareas tarea ingenieria-software A1 "Arquitectura Limpia"
./tareas rubrica materias/ingenieria-software/A1_Arquitectura_Limpia --importar enunciado/rubrica.docx
./tareas esqueleto materias/ingenieria-software/A1_Arquitectura_Limpia
./tareas generar materias/ingenieria-software/A1_Arquitectura_Limpia
./tareas estado
```

---

## Referencia de Comandos CLI

| Comando | Descripción |
|---|---|
| `./tareas verificar` | Comprueba entorno (`.venv`, dependencias, `.env`, LibreOffice y Git). |
| `./tareas temas [--crear NOMBRE] [--extraer DOCX] [--preview TEMA\|todos]` | Lista presets/temas, crea un molde `theme.json`, extrae formato desde un `.docx` o genera vista previa visual. |
| `./tareas estilos [--catalogo] [--tema TEMA] [--sin-pdf]` | Lista todos los estilos elegibles (tablas, terminales, código, citas, temas y portadas) o genera su muestrario visual en PDF. |
| `./tareas compilar <archivo.md> [--tema TEMA] [--citas apa7\|ieee\|vancouver] [--sin-pdf]` | Compila un documento declarativo Markdown/YAML a `.docx` y `.pdf` (auditando contra `TAREA.md` si existe). |
| `./tareas materia <carpeta> "<Nombre>"` | Crea una nueva materia dentro de `materias/` (workspace local ignorado por Git). |
| `./tareas tarea <materia> <código> "<Título>" [--grupal] [--formato TEMA]` | Inicializa una tarea con su estructura (`TAREA.md`, `enunciado/`, `capturas/`). |
| `./tareas rubrica <tarea> [--importar docx]` | Visualiza o importa la rúbrica oficial en `TAREA.md`. |
| `./tareas esqueleto <tarea> [--palabras N]` | Genera secciones ponderadas por criterio en `generar_documento.py`. |
| `./tareas generar <tarea> [--desde-md] [--sin-pdf]` | Compila `generar_documento.py` (o `documento.md`), ejecuta auditoría estática y exporta a `.pdf`. |
| `./tareas comprobar <tarea> [--actualizar]` | Audita el `.docx` contra la rúbrica y estándares OpenXML. |
| `./tareas auditar [<materia>]` | Auditoría estática global de todas las tareas locales. |
| `./tareas pdf <archivo.docx \| carpeta>` | Convierte archivos `.docx` a `.pdf` mediante LibreOffice aislado. |
| `./tareas estado [<materia>]` | Muestra tabla de avance y cobertura de rúbrica. |
| `./tareas marcar <tarea> <estado>` | Actualiza el estado (`pendiente`, `lista`, `entregada`). |

---

## Estructura del Proyecto

```text
document_generator/
├── plantillas/                 # Paquete Python principal (PEP 517/621)
│   ├── cli/                     # Despachador CLI y servicio LibreOffice aislado
│   ├── motor_base.py            # Protocolo BaseDocumentEngine y registro de motores
│   ├── temas.py                 # Preset oficial (apa7) y loader de temas JSON (themes/ y themes/local/)
│   ├── omml.py                  # Motor matemático LaTeX -> Unicode -> OMML vectorial
│   ├── bloques.py               # Componentes editoriales universales (Markdown, TOC, tablas, resumen)
│   ├── formato_institucional.py # Motor configurable multi-propósito
│   ├── apa_docx.py              # Motor APA 7 y gestor bibliográfico multi-estilo (APA 7, IEEE, Vancouver)
│   ├── markdown_docx.py         # Compilador declarativo Markdown + frontmatter YAML -> .docx
│   ├── preview_tema.py          # Generador de vistas previas visuales para presets y temas JSON
│   ├── visual.py                # Terminales 300 DPI, código WordML y tablas fijas
│   ├── rubrica.py / esqueleto.py / comprobar.py / ficha.py
│   └── plataforma.py            # Abstracción multiplataforma (Linux, macOS, Windows)
├── examples/                    # Ejemplos completos reproducibles y verificados en CI
├── materias/                    # Workspace privado del usuario (solo .gitkeep en Git)
├── themes/                      # Temas compartidos y themes/local/ (ignorado por Git)
├── .agents/                     # Directrices y skills locales para agentes de IA
├── docs/                        # Documentación técnica modular (00- a 04-)
├── tests/                       # Suite de pruebas unitarias e integración
└── .githooks/                   # Hook pre-commit de prevención de fugas (.env / secretos)
```

---

## Documentación Técnica

La arquitectura interna, contratos del CLI, motores documentales y guías de infraestructura se mantienen en el catálogo modular Docs-as-Code:

- [Documentación Técnica Completa](docs/00-indice-general.md)
  - [01. Arquitectura y Modelo de Fichas](docs/01-arquitectura/01-vision-general-y-patrones.md)
  - [02. Motores Documentales, Temas y Componentes Visuales](docs/02-motores-documentales/00-arquitectura-motores-base.md)
  - [03. Especificación CLI y Auditoría Estática](docs/03-herramientas-y-cli/01-especificacion-cli-tareas.md)
  - [04. Empaquetado PEP 621, Multiplataforma y Seguridad](docs/04-infraestructura-y-portabilidad/01-empaquetado-pep621-y-entornos.md)

---

## Seguridad, Privacidad y Contribuciones

- `.env`, `materias/*`, `themes/local/*` y `themes/.previews/*` (conservando solo sus `.gitkeep`) están excluidos en `.gitignore` y protegidos por `.githooks/pre-commit`.
- La copia automática de PDFs a la carpeta Descargas del sistema está **desactivada por defecto** (`COPIAR_PDF_DESCARGAS=false`); actívala explícitamente en tu `.env` si la necesitas.
- Consulta [CONTRIBUTING.md](CONTRIBUTING.md) para contribuir mejoras, nuevos presets o motores.

---

## Origen del Proyecto y Adaptaciones

Este repositorio parte de la base de [JosephBano/rubric-driven](https://github.com/JosephBano/rubric-driven), proyecto original de **Joseph Andrés Baño Naranjo** (licencia MIT), del cual hereda el paradigma *rubric-driven*, la estructura de materias/tareas, la importación de rúbricas, el flujo base del CLI `tareas` y el núcleo inicial de generación APA 7 y auditoría sobre `.docx`.

Sobre esa base, **Jorge Doicela** adaptó y amplió el proyecto a sus necesidades con las siguientes incorporaciones técnicas:

- **Arquitectura de motores y sistema de temas (`motor_base.py`, `temas.py`, `formato_institucional.py`, `extractor_tema.py`):** protocolo `BaseDocumentEngine`, preset oficial refinado `apa7`, soporte para temas JSON (`themes/` y `themes/local/`), extracción automática de estilos desde archivos `.docx` (`./tareas temas --extraer`), vistas previas (`preview_tema.py`) y portadas con autoría individual, grupal o corporativa.
- **Ingeniería OpenXML, ecuaciones OMML y componentes visuales (`omml.py`, `bloques.py`, `visual.py`, `fuentes_comunes.py`):** conversión LaTeX a Unicode y OMML vectorial compatible con Word y LibreOffice, bloques editoriales con parseo Markdown, índices automáticos (TOC), tablas con layout fijo (`APA 7` y `Grid`) y renderizadores de terminal/código a 300 DPI.
- **Refactorización modular y empaquetado PEP 621 (`plantillas/`, `plantillas/cli/`, `pyproject.toml`, `Makefile`):** migración de `_plantillas/` a paquete Python instalable (`pip install -e .`), separación del CLI en submódulos, subcomandos `auditar` y `temas`, y auditoría estática ampliada para detectar fugas de LaTeX/Markdown y defectos visuales.
- **Soporte multiplataforma, seguridad y ecosistema IA (`plataforma.py`, `setup.*`, `tareas.*`, `.githooks/`, `.agents/skills/`, `docs/`, `examples/`):** paridad Linux/macOS/Windows con CI en matriz Ubuntu/Windows, hook `pre-commit` contra fugas de secretos, exportación a Descargas opt-in, documentación técnica modular Docs-as-Code, skills especializadas para agentes IA y ampliación de la suite de pruebas (`tests/`).

---

## Licencia

El software base original es obra de **Joseph Andrés Baño Naranjo** y se distribuye bajo la licencia [MIT](LICENSE). Las adaptaciones, refactorizaciones y extensiones incorporadas en este repositorio por **Jorge Doicela** se distribuyen bajo los mismos términos de la licencia MIT, preservando intacto el aviso de derechos de autor y permisos original en [LICENSE](LICENSE).
