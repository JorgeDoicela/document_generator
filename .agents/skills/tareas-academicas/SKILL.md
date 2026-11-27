---
name: tareas-academicas
description: Directrices para el desarrollo de tareas universitarias de alto rigor académico. Activa esta skill para investigar a profundidad, fundamentar respuestas, validar fuentes y estructurar entregables con estándar de estudiante destacado.
---

# Desarrollo de Tareas Universitarias de Alto Rigor

Esta skill define el estándar operativo para la resolución de asignaciones, talleres, clases prácticas y seminarios universitarios. El agente actúa con la mentalidad de un estudiante universitario sobresaliente: riguroso, dedicado, analítico y metódico.

---

## 1. Principios Fundamentales del Trabajo Académico

1. **Cero Superficialidad:** Prohibido limitarse a definiciones enciclopédicas genéricas o respuestas de manual. Toda respuesta debe profundizar en la causa, mecanismo de funcionamiento, implicaciones prácticas y análisis crítico.
2. **Cero Relleno ("Fluff"):** No añadir párrafos vacíos o frases redundantes para inflar el recuento de palabras. La extensión debe ser producto de la densidad argumental, ejemplos contextualizados, comparativas y análisis técnico.
3. **Alineación con la Especialidad:** Salvo que el enunciado exija un contexto distinto, articular los ejemplos y análisis con la carrera configurada en `.env`, utilizando terminología técnica precisa (tecnolecto formal).
4. **Pensamiento Crítico y Argumentación:** Cada afirmación debe estar respaldada por una premisa lógica, un estándar de la industria (ISO, NIST, IEEE, RFC) o una referencia bibliográfica contrastada.

---

## 2. Metodología de Investigación y Contrastación

Antes de redactar cualquier sección de una tarea:

1. **Desglose de Preguntas Complejas:** Identificar los conceptos nucleares, las variables en juego y los criterios de evaluación del docente.
2. **Búsqueda en Fuentes de Primer Nivel:**
   * Libros canónicos y manuales universitarios reconocidos.
   * Publicaciones académicas y científicas con revisión por pares.
   * Marcos de trabajo oficiales, estándares técnicos y documentación oficial de tecnologías.
3. **Triangulación de Información:** No depender de una sola fuente para conceptos clave. Contrastar definiciones entre al menos dos autores o marcos de referencia para evidenciar amplitud de criterio.
4. **Verificación Factual:** Prohibido inventar datos estadísticos, leyes, operadores matemáticos o citas textuales.

---

## 3. Rigor Bibliográfico y Normas APA 7

El manejo de referencias es un pilar innegociable de la integridad académica:

1. **Cero Citas Fantasma:** Toda cita en el texto debe contar con su correspondiente entrada bibliográfica completa y verificable.
2. **Uso del Gestor Bibliográfico:** En scripts de generación (`generar_documento.py`), registrar cada fuente mediante `bib.agregar(...)` y citar estrictamente con `bib.cita("clave")` o `bib.cita_narrativa("clave")`.
3. **Estructura Estricta APA 7:**
   * **Libro:** Autor, A. A. (Año). *Título de la obra*. Editorial.
   * **Artículo:** Autor, A. A., & Autor, B. B. (Año). Título del artículo. *Nombre de la Revista*, volumen(número), páginas. https://doi.org/xxxx
   * **Norma/Estándar:** Organización. (Año). *Título del estándar* (Norma No. XXX). Enlace o editorial.
4. **Integración Fluida:** Las citas deben integrarse orgánicamente en el discurso mediante citas parentéticas o narrativas, evitando acumular citas al final de párrafos sin desarrollo reflexivo propio.

---

## 4. Estructura y Desarrollo de Entregables

Al construir el documento final mediante el flujo de rúbrica:

1. **Cumplimiento de Criterios (Nivel Excelente):** Cada criterio de la rúbrica debe quedar abordado de forma exhaustiva, cubriendo tanto los requerimientos explícitos como los implícitos.
2. **Proporcionalidad por Puntaje:** Asignar la profundidad analítica y extensión textual en concordancia con el peso porcentual del criterio en la nota final.
4. **Formatos Institucionales y Estándar Editorial Innegociable:**
   * **Cero Cajas de Llamada Coloreadas y Cero Barras Laterales de Acento ("Estética IA"):** Queda terminantemente prohibido utilizar tablas de celda única con marcos coloreados, fondos sombreados o **barras verticales coloreadas a la izquierda** (`border-l-*` en diagramas o `w:left` grueso en Word). Los enunciados docentes se presentan sobre el lienzo con `enunciado_formal(doc, texto, etiqueta, numero)`, y las tarjetas de diagramas emplean contorno uniforme sobrio mediante `visual.dibujar_tarjeta_academica()`.
   * **Prevención de Estiramiento Tipográfico:** Todo texto con saltos de línea o viñetas debe estructurarse en párrafos independientes con `parrafo` o `bloques.parrafo_estructurado` (viñetas con alineación izquierda y sangría francesa 0.25"). Jamás concatenar texto con `<w:br/>` dentro de un párrafo justificado.
   * **Fórmulas OMML sin Desbordamiento ni Fugas LaTeX:** Toda ecuación matemática o lógica debe integrarse en OMML vectorial mediante `formula_bloque`, que normaliza comandos LaTeX a Unicode matemático (`normalizar_latex_a_unicode`) y segmenta fórmulas de más de 75 caracteres mediante `dividir_formula_larga`. Prohibido dejar comandos LaTeX crudos en párrafos u OMML.
   * **Cero Fugas de Asteriscos Markdown (`**` o `*`):** Ningún entregable puede contener asteriscos literales de marcado (`**texto**`). Toda negrita o cursiva debe procesarse a través del motor de texto enriquecido en runs nativos de OpenXML para garantizar un acabado tipográfico 100% profesional.
   * **Revisión Pre-Entrega Estática y Visual:** Ejecutar la verificación estática (`tareas comprobar` / `tareas generar`) asegurando cero errores (`[error]`) y resolviendo las advertencias de extensión o balance temático; complementar con inspección visual de las páginas renderizadas del PDF (`pymupdf`) para validar ecuaciones OMML, tablas sin cortes de palabra y diagramas sin solapamientos.

---

## 5. Ingesta y Procesamiento Ágil de Consignas (`~/Descargas`)

Para agilizar el flujo de trabajo sin fricción manual:

1. **Detección Autónoma en `~/Descargas`:** Si el estudiante indica que descargó una guía, consigna o rúbrica de la plataforma universitaria, el agente inspecciona de inmediato la carpeta `~/Descargas/` para identificar el archivo por nombre o tomar el PDF/DOCX más reciente.
2. **Centralización en `enunciado/`:**
   - Para tareas nuevas: Invocar `./plantillas/tareas.py tarea <materia> <CODIGO> "<Titulo>" --enunciado ~/Descargas/<archivo>` para inicializar la tarea e importar el archivo simultáneamente.
   - Para tareas existentes: Copiar el archivo directamente a `materias/<materia>/<tarea>/enunciado/`.
3. **Extracción Inmediata de Rúbrica:** Procesar de forma autónoma el contenido del archivo copiado para poblar la rúbrica en `TAREA.md` y preparar la estructura del entregable sin requerir que el usuario mueva archivos manualmente.
4. **Entrega Organizada en `~/Descargas` (Estándar snake_case sin duplicados):**
   - **Nomenclatura oficial:**
     * Individual: `nombre_apellido_<actividad>_<numero>.pdf` (ej. `ana_perez_tarea_practica_2.pdf`).
     * Grupal: `grupo_<numero>_<actividad>_<numero>.pdf` (ej. `grupo_1_clase_practica_3.pdf`, `grupo_1_tarea_practica_3.pdf`).
   - Al compilar el PDF final de la tarea (`tareas generar` o `tareas pdf`), si el usuario habilitó `COPIAR_PDF_DESCARGAS=true` en su `.env` local (opt-in, `false` por defecto), el motor documental copia exclusivamente el archivo `.pdf` final a la raíz de Descargas (sin archivos `.docx` ni duplicados por mayúsculas/minúsculas).
   - Si el docente entrega un `.docx` con identidad visual propia que aún no existe en `themes/local/`, extraer el tema con `./tareas temas --extraer enunciado/<archivo>.docx --nombre <slug>` antes de compilar.
5. **Protocolo de Limpieza Post-Entrega (Solo al terminar):**
   Únicamente tras la confirmación explícita del estudiante de que la tarea ha sido entregada en la plataforma académica:
   - Limpiar de `~/Descargas/` los archivos fuente descargados (PDFs y DOCX de docentes o compañeros) que ya están preservados en el repositorio (`enunciado/` e `insumos/`).
   - Limpiar la carpeta temporal de entrega en `~/Descargas/` (o los PDFs generados) para que el área de descargas quede 100% limpia y preparada para la siguiente tarea.



