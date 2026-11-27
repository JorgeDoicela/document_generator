---
name: analisis-rubricas-consignas
description: Metodología para ingesta, extracción, desestructuración y normalización de consignas docentes y rúbricas de evaluación en PDF o DOCX. Transforma requisitos heterogéneos en matrices estructuradas para TAREA.md y scaffolding automático.
---

# Análisis y Normalización de Rúbricas y Consignas Docentes

Esta skill define el protocolo metódico para interpretar, extraer y normalizar las guías de estudio, consignas de tareas y matrices de rúbrica suministradas por los docentes universitarios.

---

## 1. Protocolo de Ingesta desde `~/Descargas` o `enunciado/`

1. **Detección Automática:** Cuando el estudiante descargue el archivo oficial (PDF o DOCX) en `~/Descargas` (o `Downloads`), el agente lo transfiere inmediatamente a `materias/<materia>/<tarea>/enunciado/` para centralizar los insumos en el workspace local.
2. **Inspección de Contenido y Extracción de Tema:** Leer íntegramente el documento base mediante herramientas directas (`view_file`, lectura de texto o extracción de tablas DOCX). Si el `.docx` incluye un formato institucional o corporativo propio que aún no existe en `themes/local/`, ejecutar:
   ```bash
   tareas temas --extraer enunciado/<archivo>.docx --nombre <slug-institucion>
   ```
   Esto extrae márgenes, tipografía, paleta cromática, estilo de tabla e imágenes a `themes/local/<slug-institucion>/theme.json`.

---

## 2. Tipología de Rúbricas y Extracción

Las directrices docentes se clasifican en tres tipologías con procedimientos específicos:

### Tipo A: Rúbrica Tabular en DOCX
* **Procedimiento:** Ejecutar directamente el subcomando de importación:
  ```bash
  tareas rubrica <tarea> --importar enunciado/<archivo>.docx
  ```
* **Verificación:** Inspeccionar `TAREA.md` y comprobar que las filas `| ID | Criterio | Puntaje | Dónde se cumple |` coincidan exactamente con la tabla del docente. Si los puntajes están en escala porcentual, registrar el peso respectivo.

### Tipo B: Rúbrica en PDF o Imagen
* **Procedimiento:** Transcribir manualmente cada criterio a la tabla de `TAREA.md`:
  - Asignar identificadores continuos: `C1`, `C2`, `C3`, etc.
  - Extraer la descripción sintética y precisa del criterio evaluado.
  - Extraer el puntaje máximo asignado a la categoría de desempeño superior (*Excelente / Sobresaliente*).
  - Verificar que la suma de puntajes coincida con la calificación total (escala de 10 puntos o 100%).

### Tipo C: Consigna sin Rúbrica Explícita
* **Procedimiento de Desglose:**
  1. Identificar las preguntas específicas, ejercicios prácticos, demostraciones o fases operativas requeridas en el texto de la consigna.
  2. Sintetizar un criterio claro para cada entregable (p. ej., `C1: Modelado formal en lógica de primer orden`, `C2: Demostración mediante resolución`).
  3. Reservar criterios finales para aspectos formales estándar (`C_n: Conclusiones y fundamentación técnica`, `C_{n+1}: Formato institucional, citas APA 7 y ortografía`).
  4. Distribuir el puntaje total (ej. 10 puntos) de forma proporcional a la complejidad técnica de cada parte.
  5. **Validación:** Presentar la propuesta de criterios al estudiante antes de compilar el documento.

---

## 3. Identificación de Criterios Transversales

Al normalizar la rúbrica, distinguir claramente:

1. **Criterios de Sección (Específicos):** Aquellos que corresponden a un desarrollo técnico concreto (se abordan en un encabezado con marcador `criterios="C1"`).
2. **Criterios Transversales (Holísticos):** Criterios que aplican a la totalidad del informe (p. ej. *Ortografía y redacción*, *Bibliografía y normas APA*, *Trabajo en equipo y organización*).
   * Estos criterios deben registrarse en `TAREA.md` y marcarse en el script de generación mediante:
     ```python
     # Con formato_institucional (o transversal(doc, ...) en apa_docx)
     inst.marcar_transversal(doc, "C5", "C6")
     ```

---

## 4. Generación y Armonización del Esqueleto

Una vez consolidada la tabla de rúbrica en `TAREA.md`:

1. **Generación Inicial:**
   ```bash
   tareas esqueleto <tarea> --palabras 1500
   ```
2. **Ponderación de Extensión:** `tareas esqueleto` distribuye automáticamente la extensión recomendada de palabras de forma proporcional al puntaje de cada criterio:
   - Un criterio con peso del 40% (4 puntos) recibirá mayor extensión y profundidad de desarrollo.
   - Un criterio del 10% (1 punto) mantendrá una extensión acotada y concisa.
3. **Inmutabilidad de Marcadores:** Al redactar en `generar_documento.py`, está terminantemente prohibido alterar los argumentos `criterios="C1"` o eliminar llamadas a `marcar_transversal()` / `transversal()`, ya que son el ancla utilizada por el motor de comprobación estática. Si se utiliza el flujo declarativo en `documento.md`, conservar las anotaciones de encabezado (`# Título {#C1}`) y la clave `transversales: [...]` en el frontmatter YAML.
