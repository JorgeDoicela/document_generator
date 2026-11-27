# document_generator — Framework Documental Multi-Propósito (Rubric-Driven)

Framework programático en Python para la generación, estructuración y auditoría estática de **cualquier tipo de documento profesional o académico** (ensayos APA 7, informes académicos institucionales, especificaciones técnicas y RFCs, reportes ejecutivos, artículos estilo IEEE y plantillas corporativas personalizadas vía JSON) en formato **WordML (`.docx`)** y **PDF vectorial**.

El principio rector del sistema es determinista: los criterios de evaluación o requisitos del documento gobiernan la estructura, y un auditor estático verifica el XML resultante antes de entregarlo.

---

## Capacidades Principales

1. **Motores Multi-Propósito y Sistema de Temas (`plantillas/temas.py`, `formato_institucional.py`, `apa_docx.py`):**
   - **5 presets integrados:** `apa7`, `academico`, `tecnico`, `ejecutivo` e `ieee`.
   - **Temas institucionales/corporativos plug-and-play (`theme.json`):** configura colores, tipografía, interlineado, márgenes, encabezados, logos y banners sin tocar Python. Los temas privados con marcas propias se guardan en `themes/local/` (ignorados por Git).
2. **Ingeniería OpenXML de Alta Fidelidad (`omml.py`, `bloques.py`, `visual.py`):**
   - **Ecuaciones matemáticas OMML vectoriales (`omml.py`):** convierte expresiones y comandos LaTeX a Unicode + XML OMML (`<m:oMathPara>`) compatible con Microsoft Word y LibreOffice (sin caracteres rotos ni desbordes horizontales).
   - **Bloques editoriales universales (`bloques.py`):** texto enriquecido Markdown (`**negrita**`, `*cursiva*`, `` `código inline` ``, superíndices/subíndices), párrafos estructurados sin estiramiento tipográfico, resúmenes ejecutivos con palabras clave, índices automáticos nativos (TOC), metadatos Core Properties y figuras con pies idempotentes.
   - **Tablas con layout fijo (`w:tblLayout="fixed"`):** soporte nativo para estilo **APA 7** (3 líneas horizontales) y **Grid** (cuadrícula completa), con anchos proporcionales y repetición de cabeceras en saltos de página.
   - **Renderizadores visuales a 300 DPI (`visual.py`):** capturas sintéticas de terminal CLI (temas `Dark` y `Light`), bloques de código estilizados y tarjetas académicas sobrias.
3. **Pipeline Guiado por Rúbricas y Auditoría Estática (`rubrica.py`, `esqueleto.py`, `comprobar.py`):**
   - Importa rúbricas desde `.docx` o `TAREA.md` y genera esqueletos ponderados por puntaje.
   - Audita el `.docx` a nivel XML: cobertura del 100% de criterios (`w:bookmarkStart`), proporcionalidad de palabras, correspondencia biyectiva entre citas y referencias APA 7, detección de fugas LaTeX/Markdown y prevención de defectos visuales.
4. **Ecosistema de Agentes IA (`.agents/`):**
   - Incluye reglas (`AGENTS.md`) y 4 skills especializadas (`.agents/skills/`) para flujos asistidos por IA en análisis de consignas, rigor académico, ingeniería OpenXML y laboratorios técnicos.
5. **Privacidad por Diseño:**
   - El workspace personal del usuario (`materias/*`, conservando `materias/.gitkeep`), los temas privados (`themes/local/`) y `.env` están excluidos de Git por defecto.

---

## Inicio Rápido Multiplataforma

### Requisitos Previos
- **Python 3.10+** (probado en Python 3.10 a 3.13 en Linux y Windows).
- **Git**.
- **LibreOffice** (opcional, requerido únicamente para la exportación automatizada a PDF).

### Linux y macOS
```bash
git clone <URL_DEL_REPOSITORIO> && cd document_generator
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

### Probar el Ejemplo Reproducible en 1 Comando
```bash
python examples/ejemplo_completo/generar_documento.py
./tareas comprobar examples/ejemplo_completo
```

---

## Uso Rápido como Generador de Documentos

### 1. Generar cualquier tipo de documento desde Python
```python
from plantillas import bloques, formato_institucional as inst, omml

doc = inst.nuevo_documento_tematico(
    titulo="Arquitectura de Microservicios",
    subtitulo="Especificación Técnica — RFC-01",
    tema="tecnico",          # apa7 | academico | tecnico | ejecutivo | ieee | ruta/theme.json
    incluir_indice=True,
)
bloques.resumen_ejecutivo(doc, "Resumen ejecutivo del sistema.", palabras_clave=["RFC", "Arquitectura"])
inst.titulo_seccion(doc, "1. Modelo Matemático", nivel=1, criterios="C1")
omml.formula_bloque(doc, r"\forall x \in \mathcal{S} : \text{Latencia}(x) \leq 50\text{ ms}", "Ecuación 1.")
inst.guardar_documento(doc, "informe_tecnico.docx")
```

### 2. Extraer o crear tu propio tema institucional o corporativo
```bash
# Extraer automáticamente tipografía, márgenes, colores e imágenes desde cualquier .docx oficial
./tareas temas --extraer enunciado/plantilla.docx --nombre mi-universidad

# O crear un molde manual en themes/local/ (ignorado por Git)
./tareas temas --crear mi-universidad --base academico --local
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
| `./tareas temas [--crear NOMBRE] [--extraer DOCX] [--base PRESET] [--local]` | Lista presets/temas, crea un molde `theme.json` o extrae formato desde un `.docx`. |
| `./tareas materia <carpeta> "<Nombre>"` | Crea una nueva materia dentro de `materias/` (workspace local ignorado por Git). |
| `./tareas tarea <materia> <código> "<Título>" [--grupal] [--formato TEMA]` | Inicializa una tarea con su estructura (`TAREA.md`, `enunciado/`, `capturas/`). |
| `./tareas rubrica <tarea> [--importar docx]` | Visualiza o importa la rúbrica oficial en `TAREA.md`. |
| `./tareas esqueleto <tarea> [--palabras N]` | Genera secciones ponderadas por criterio en `generar_documento.py`. |
| `./tareas generar <tarea> [--sin-pdf]` | Compila `.docx`, ejecuta auditoría estática y exporta a `.pdf`. |
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
│   ├── temas.py                 # Presets (apa7, academico, tecnico, ejecutivo, ieee) y loader JSON
│   ├── omml.py                  # Motor matemático LaTeX -> Unicode -> OMML vectorial
│   ├── bloques.py               # Componentes editoriales universales (Markdown, TOC, tablas, resumen)
│   ├── formato_institucional.py # Motor configurable multi-propósito
│   ├── apa_docx.py              # Motor APA 7 y gestor bibliográfico
│   ├── visual.py                # Terminales 300 DPI, código WordML y tablas fijas
│   ├── rubrica.py / esqueleto.py / comprobar.py / ficha.py
│   └── plataforma.py            # Abstracción multiplataforma (Linux, macOS, Windows)
├── examples/                    # Ejemplos completos reproducibles y verificados en CI
├── materias/                    # Workspace privado del usuario (solo .gitkeep en Git)
├── themes/                      # Temas compartidos y themes/local/ (ignorado por Git)
├── .agents/                     # Directrices y skills locales para agentes de IA
├── docs/                        # Documentación técnica modular (00- a 04-)
├── tools/                       # Utilidades de diagramas de flujo y comparativa visual
├── tests/                       # Suite de pruebas unitarias e integración
└── .githooks/                   # Hook pre-commit de prevención de fugas (.env / secretos)
```

---

## Seguridad, Privacidad y Contribuciones

- `.env`, `materias/*` (excepto `materias/.gitkeep`) y `themes/local/` están excluidos en `.gitignore` y protegidos por `.githooks/pre-commit`.
- La copia automática de PDFs a la carpeta Descargas del sistema está **desactivada por defecto** (`COPIAR_PDF_DESCARGAS=false`); actívala explícitamente en tu `.env` si la necesitas.
- Consulta [CONTRIBUTING.md](CONTRIBUTING.md) para contribuir mejoras, nuevos presets o motores.

## Licencia

Distribuido bajo licencia [MIT](LICENSE).
