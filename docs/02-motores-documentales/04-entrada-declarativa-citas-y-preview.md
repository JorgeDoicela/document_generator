# Entrada Declarativa Markdown/YAML, Citación Multi-Estilo y Vista Previa de Temas

Este documento especifica tres capacidades desacopladas del framework documental: la compilación declarativa desde Markdown con frontmatter YAML (`plantillas/markdown_docx.py`), el soporte de citación en múltiples estándares (`APA 7`, `IEEE` y `Vancouver`) y la generación automatizada de vistas previas visuales de temas (`plantillas/preview_tema.py`).

---

## 1. Compilador Declarativo Markdown/YAML (`plantillas/markdown_docx.py`)

El módulo `markdown_docx.py` permite redactar documentos completos sin escribir código Python, preservando las garantías de trazabilidad de rúbrica, ecuaciones OMML vectoriales, tablas con layout fijo y auditoría estática sobre el `.docx` resultante.

El parser YAML integrado opera sin dependencias externas obligatorias (delega a `PyYAML` únicamente si está instalado en el entorno).

### 1.1 Esquema del Frontmatter YAML

```yaml
---
titulo: "Título del Documento"
subtitulo: "Subtítulo o Materia"
tema: apa7                     # apa7 | nombre_tema_json | ruta/theme.json
estilo_citas: apa7             # apa7 | ieee | vancouver
modalidad: individual          # individual | grupal
autor: "Ana Pérez"             # o lista en integrantes: ["Ana Pérez", "Luis Gómez"]
grupo: "Grupo 1"               # opcional en modalidad grupal
institucion: "Institución"
carrera: "Carrera / Área"
docente: "Docente / Revisor"
fecha: "2026"
indice: false
resumen: "Resumen ejecutivo del documento."
palabras_clave: [Markdown, YAML, OMML]
transversales: [C4]            # criterios de rúbrica aplicados a todo el documento
criterios_referencias: [C3]    # opcional; también se puede marcar con # Referencias {#C3}
salida: "informe_final.docx"   # opcional; por defecto usa el nombre del archivo .md
referencias:
  - clave: russell2021
    autores: ["Russell, S.", "Norvig, P."]
    anio: 2021
    titulo: "Artificial Intelligence: A Modern Approach"
    fuente: "Pearson"
    detalles: "4.a ed."
    tipo: libro                # libro | articulo | capitulo | informe
    url: ""
---
```

### 1.2 Sintaxis Soportada en el Cuerpo Markdown

| Elemento Markdown | Resultado OpenXML | Módulo Invocado |
|---|---|---|
| `# Título {#C1}` / `## Sub {criterios="C1, C2"}` | Encabezado `Heading 1..3` con marcador invisible `rubrica_C*` | `apa_docx.titulo()` |
| `[@clave]` / `[@clave, p. 15]` / `[@c1; @c2]` | Cita parentética o numérica según `estilo_citas` | `Bibliografia.cita()` |
| `@clave` / `[@!clave]` | Cita narrativa (ignora correos y bloques de código inline) | `Bibliografia.cita_narrativa()` |
| `$$ \forall x \in \mathcal{S} $$ {leyenda="Ec. 1."}` | Ecuación vectorial `<m:oMathPara>` sin fugas LaTeX | `omml.formula_bloque()` |
| ```` ```python ... ``` ```` | Bloque de código monoespaciado estilizado | `bloques.codigo_bloque()` |
| `\| Col 1 \| Col 2 \|` | Tabla con `w:tblLayout="fixed"` en modo `apa` o `grid` | `bloques.tabla_academica()` |
| `> **Consigna:** Texto` | Enunciado formal sin cajas coloreadas ni barras laterales | `bloques.enunciado_formal()` |
| `` ![Descripción](ruta.png) `` | Figura numerada con pie idempotente | `bloques.caja_captura_evidencia()` |
| `- Elemento` / `1. Elemento` | Lista con viñetas o numerada sin estiramiento tipográfico | `apa_docx.vinieta()` / `parrafo()` |
| `---` o `<!-- pagebreak -->` | Salto de página explícito | `apa_docx.salto_de_pagina()` |

### 1.3 Uso desde CLI

```bash
# Compilar cualquier archivo Markdown/YAML independiente
./tareas compilar examples/ejemplo_markdown/documento.md
./tareas compilar documento.md --tema ieee --citas ieee --sin-pdf

# Compilar documento.md dentro de una tarea con auditoría de TAREA.md
./tareas generar materias/<materia>/<tarea> --desde-md
```

---

## 2. Formatos de Citación (`APA 7`, `IEEE` y `Vancouver`)

La clase `Bibliografia` en [apa_docx.py](../../plantillas/apa_docx.py) soporta tres estilos configurables mediante `Bibliografia(estilo="apa7" | "ieee" | "vancouver")`:

| Estilo | Cita en Texto | Cita Múltiple | Cita Narrativa | Orden en Referencias | Formato de Entrada |
|---|---|---|---|---|---|
| `apa7` | `(Ramos, 2024)` | `(Lee, 2023; Ramos, 2024)` | `Ramos (2024)` | Alfabético por apellido | `Ramos, J. (2024). *Título*. Fuente.` |
| `ieee` | `[1]` | `[1], [2]` | `Ramos [1]` | Orden de aparición | `[1] J. Ramos, *Título*. Fuente, 2024.` |
| `vancouver` | `(1)` | `(1,2)` | `Ramos (1)` | Orden de aparición | `1. Ramos J. Título. Fuente. 2024.` |

### Auditoría Estática Biyectiva (`comprobar.py`)

El motor [comprobar.py](../../plantillas/comprobar.py) detecta automáticamente el estilo de la sección `Referencias` inspeccionando sus entradas compiladas en el `.docx`:

1. **Modo IEEE (`[N] ...`):** extrae citas `[N]` del cuerpo y verifica correspondencia biyectiva con los índices `[N]` en `Referencias`.
2. **Modo Vancouver (`N. ...`):** extrae citas `(N)`, `(N,M)` y rangos `(N-M)` del cuerpo y verifica correspondencia biyectiva con `N.` en `Referencias`.
3. **Modo APA 7 (defecto):** verifica correspondencia autor-año entre citas narrativas/parentéticas y entradas alfabéticas.

---

## 3. Vista Previa Automática de Temas (`plantillas/preview_tema.py`)

El módulo [preview_tema.py](../../plantillas/preview_tema.py) genera un documento de muestra estandarizado que ejercita portada, resumen ejecutivo, encabezados H1-H3, tabla de parámetros del tema, enunciado formal, ecuación OMML, bloque de código y referencias para inspección visual directa en Word o PDF.

```bash
# Generar vista previa (.docx y .pdf) de un tema específico en themes/.previews/
./tareas temas --preview apa7
./tareas temas --preview apa7 --citas ieee

# Generar muestras para todos los temas disponibles (apa7 + locales)
./tareas temas --preview todos --sin-pdf
```

La carpeta de salida por defecto (`themes/.previews/`) está excluida en `.gitignore` para evitar versionar artefactos temporales.
