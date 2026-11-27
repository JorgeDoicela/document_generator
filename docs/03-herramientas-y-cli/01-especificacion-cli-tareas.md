# Especificación del CLI `tareas`

El punto de entrada unificado de la herramienta es el despachador de línea de comandos `tareas` (entrypoint en `plantillas/tareas.py`, invocado mediante `./tareas` en Linux/macOS, `tareas.bat` en Windows o el comando de terminal `tareas` si el paquete editable está activo en el entorno virtual).

### Arquitectura Interna del CLI
La lógica interna del CLI se encuentra desacoplada en controladores de dominio bajo `plantillas/cli/`:
* `plantillas/cli/comandos_gestion.py`: Subcomandos administrativos (`verificar`, `materia`, `tarea`, `marcar`).
* `plantillas/cli/comandos_documentales.py`: Subcomandos de compilación e inspección (`rubrica`, `esqueleto`, `generar`, `comprobar`, `auditar`).
* `plantillas/cli/servicio_pdf.py`: Servicio aislado de conversión a PDF con LibreOffice headless y gestión de timeouts/cuotas de disco.
* `plantillas/cli/tablas.py`: Renderizado y formateo de la tabla de avance (`estado`).
* `plantillas/tareas.py`: Despachador ligero y definidor del árbol de argumentos con `argparse`.

---

## 1. Estructura General de Invocación

```bash
tareas <subcomando> [opciones] [argumentos...]
```

### Códigos de Retorno del Proceso:
* `0`: Ejecución exitosa sin errores bloqueantes.
* `1`: Fallo de validación, error de sintaxis en rúbrica o criterios sin cubrir en auditoría.
* `2`: Error de configuración (`.env` faltante o incompleto).


---

## 2. Referencia Exhaustiva de Subcomandos

### 1. `verificar`

Audita el entorno de ejecución, herramientas externas y directivas de seguridad.

* **Sintaxis:** `tareas verificar`
* **Comprobaciones:**
  - Existencia y completitud de las variables en `.env`.
  - Intérprete Python de `.venv/` en la raíz.
  - Dependencias obligatorias (`python-docx`, `Pillow`, `lxml`, `pypdf`).
  - Detección del ejecutable `soffice` de LibreOffice.
  - Aislamiento de `.env` fuera del control de versiones git.

---

### 2. `materia`

Inicializa la carpeta y ficha de una nueva asignatura académica.

* **Sintaxis:** `tareas materia <carpeta> "<Nombre Completo>"`
* **Argumentos:**
  - `<carpeta>`: Nombre de la carpeta en minúsculas con guiones dentro de `materias/` (ej. `seguridad-redes`).
  - `"<Nombre Completo>"`: Nombre oficial de la cátedra (ej. `"Seguridad de Redes y Comunicaciones"`).
* **Artefactos Creados:** `materias/<carpeta>/MATERIA.md` con plantilla de docente, reglas y tabla de tareas.

---

### 3. `tarea`

Crea la estructura de una tarea dentro de una materia existente.

* **Sintaxis:** `tareas tarea <materia> <código> "<Título Corto>" [--tipo <tipo>] [--modalidad {individual,grupal}] [--grupal] [--grupo <nombre>] [--integrantes <lista>]`
* **Argumentos y Opciones:**
  - `<materia>`: Nombre de la carpeta de la materia.
  - `<código>`: Código con prefijo de tipo: `A` (Actividad), `P` o `CP` (Práctica), `E` (Evaluación), `S` (Seminario), `T` (Tarea). Ej. `TP1`.
  - `"<Título Corto>"`: Título del tema.
  - `--modalidad {individual,grupal}`: Declara explícitamente el régimen de autoría (por defecto `individual`).
  - `--grupal`: Atajo para configurar la tarea en modalidad grupal.
  - `--grupo "<nombre>"`: Identificador del grupo (ej. `"Grupo 1"`).
  - `--integrantes "<lista>"`: Nombres de integrantes separados por comas.
* **Artefactos Creados:**
  - `materias/<materia>/<CODIGO>_<Titulo_Corto>/`
  - `TAREA.md` (ficha con rúbrica base, modalidad y metadatos de autoría).
  - `enunciado/` (directorio para PDFs/DOCXs oficiales).
  - `capturas/` (directorio para capturas de ejecución real).
  - `insumos/` (directorio para borradores, apuntes y aportes de equipo).
  - `generar_documento.py` (script base de compilación adaptado a la modalidad).

---

### 4. `rubrica`

Inspecciona la rúbrica registrada en `TAREA.md` o importa una rúbrica oficial desde un documento Word del docente.

* **Sintaxis:** `tareas rubrica <ruta_tarea> [--importar <archivo.docx>]`
* **Opciones:**
  - `--importar <docx>`: Parsea las tablas del documento Word especificado, detecta filas de criterios y puntajes, y sobreescribe la sección `## Rúbrica` de `TAREA.md`.
* **Salida sin opciones:** Imprime en terminal la tabla de criterios, su puntaje y su peso porcentual calculado.

---

### 5. `esqueleto`

Reescribe `generar_documento.py` estructurando una sección por cada criterio de la rúbrica.

* **Sintaxis:** `tareas esqueleto <ruta_tarea> [--palabras N] [--forzar]`
* **Opciones:**
  - `--palabras N`: Extensión total orientativa del documento (por defecto 1500 palabras o lo estipulado en `TAREA.md`).
  - `--forzar`: Sobreescribe el archivo `generar_documento.py` incluso si ya contiene código previo (genera respaldo `.bak`).
* **Comportamiento:** Cada criterio recibe una sección marcada con `criterios="C1"` y una cuota orientativa de palabras proporcional a su peso.

---

### 6. `generar`

Compila el documento Word (desde `generar_documento.py` o `documento.md`), ejecuta la auditoría estática y exporta a PDF.

* **Sintaxis:** `tareas generar <ruta_tarea> [--desde-md] [--tema TEMA] [--citas ESTILO] [--sin-pdf]`
* **Opciones:**
  - `--desde-md`: Compila `documento.md` mediante el compilador declarativo Markdown/YAML en lugar de ejecutar `generar_documento.py` (también se activa automáticamente si existe `documento.md` sin `generar_documento.py`).
  - `--tema TEMA`: Sobrescribe el tema documental declarado al compilar desde `documento.md`.
  - `--citas {apa7,ieee,vancouver}`: Sobrescribe el estilo de citación al compilar desde `documento.md`.
  - `--sin-pdf`: Omite la invocación a LibreOffice, generando únicamente el `.docx` y validando la rúbrica.
* **Comportamiento:**
  1. Ejecuta el intérprete Python sobre `generar_documento.py` o compila `documento.md`.
  2. Ejecuta `comprobar()` sobre el `.docx` resultante.
  3. Actualiza la columna "Dónde se cumple" en `TAREA.md`.
  4. Si la comprobación pasa sin errores, exporta el PDF final.

---

### 7. `comprobar`

Audita el archivo `.docx` generado frente a los criterios de la rúbrica sin compilar de nuevo.

* **Sintaxis:** `tareas comprobar [<ruta_tarea>] [--actualizar] [--todas]`
* **Opciones:**
  - `--actualizar`: Escribe los resultados de la auditoría directamente en la columna "Dónde se cumple" de `TAREA.md`.
  - `--todas`: Si se especifica, delega automáticamente en `auditar` inspeccionando todas las tareas del repositorio.
* **Salida:** Reporte detallado de cumplimiento (`[ok]`, `[falta]`), recuento de palabras por sección, balance de pesos, citas sin referencia y marcas de contenido pendiente.

---

### 8. `auditar`

Ejecuta una auditoría estática global recursiva de todas las tareas académicas del repositorio en una sola ejecución.

* **Sintaxis:** `tareas auditar [<materia>] [--actualizar]`
* **Opciones:**
  - `<materia>`: Limita la auditoría masiva a una asignatura específica (por defecto audita todas).
  - `--actualizar`: Actualiza la columna "Dónde se cumple" en cada `TAREA.md` evaluada.
* **Comportamiento:**
  - Inspecciona cada directorio con `TAREA.md`.
  - Valida la existencia del `.docx`, cobertura del 100% de rúbrica, citas bibliográficas y ausencia de marcadores pendientes.
  - Imprime una tabla consolidada con métricas agregadas por tarea.
  - Devuelve código de salida `0` si todos los entregables están conformes o `1` si existe al menos un error bloqueante.


---

### 9. `pdf`

Convierte de forma aislada uno o más archivos `.docx` a PDF utilizando LibreOffice.

* **Sintaxis:** `tareas pdf <archivo.docx | ruta_tarea>`
* **Mecanismos de Seguridad:**
  - Ejecución en subproceso con `start_new_session=True` para aislar grupos de procesos.
  - Timeout configurable de 60 segundos por archivo para evitar bloqueos si LibreOffice entra en bucle.
  - Perfil de usuario temporal aislado (`-env:UserInstallation=file:///tmp/...`) para no colisionar con instancias de LibreOffice del usuario.

---

### 10. `estado`

Muestra una tabla unificada con el estado de avance y cobertura de todas las materias.

* **Sintaxis:** `tareas estado [<materia>] [--todas]`
* **Opciones:**
  - `<materia>`: Filtra las tareas pertenecientes a una única asignatura.
  - `--todas`: Incluye tareas ya entregadas (por defecto oculta las tareas con estado `entregada`).

---

### 11. `marcar`

Transiciona el estado de una tarea sincronizando simultáneamente `TAREA.md` y la ficha `MATERIA.md` de la materia.

* **Sintaxis:** `tareas marcar <ruta_tarea> <estado> [--forzar]`
* **Argumentos:**
  - `<estado>`: `pendiente`, `lista` o `entregada`.
* **Opciones:**
  - `--forzar`: Permite marcar como `lista` incluso si la auditoría estática arroja errores o avisos pendientes.

---

### 12. `temas`

Gestiona los temas documentales del framework (`plantillas/temas.py`, `plantillas/extractor_tema.py` y `plantillas/preview_tema.py`): lista los presets y temas locales disponibles, genera moldes `theme.json`, extrae automáticamente el formato desde cualquier `.docx` de referencia o genera muestras visuales de validación.

* **Sintaxis:**
  ```bash
  tareas temas
  tareas temas --crear <nombre> [--base <preset>] [--local]
  tareas temas --extraer <archivo.docx> [--nombre <slug>] [--compartido]
  tareas temas --preview <tema|todos> [--salida <ruta>] [--citas apa7|ieee|vancouver] [--sin-pdf]
  ```
* **Opciones:**
  - *(sin opciones)*: Imprime los presets integrados (`apa7`, `academico`, `tecnico`, `ejecutivo`, `ieee`) y los temas detectados en `themes/` y `themes/local/`.
  - `--crear <nombre>`: Crea un archivo `theme.json` editable heredando del preset `--base` (`academico` por defecto). Con `--local`, lo guarda en `themes/local/` (ignorado por Git).
  - `--extraer <archivo.docx>`: Analiza el OpenXML del `.docx` suministrado e infiere márgenes, tipografía, interlineado, color primario, estilo de tabla (`grid`/`apa`) e imágenes embebidas (`header`, `logo_portada`, `banner_inferior`), generando el `theme.json` en `themes/local/<slug>/` por defecto (o en `themes/<slug>/` con `--compartido`).
  - `--nombre <slug>`: Identificador explícito del tema al usar `--extraer` (si se omite, se deriva del nombre del `.docx`).
  - `--preview <tema|todos>`: Genera un documento de muestra completo (`.docx` y `.pdf`, salvo `--sin-pdf`) en `themes/.previews/` (o en `--salida`) para validar visualmente portada, tipografía, OMML, tablas, código y referencias del tema.

---

### 13. `compilar`

Compila cualquier archivo Markdown con frontmatter YAML a `.docx` y opcionalmente `.pdf` sin necesidad de escribir scripts Python.

* **Sintaxis:** `tareas compilar <archivo.md> [--salida <archivo.docx>] [--tema TEMA] [--citas apa7|ieee|vancouver] [--sin-pdf]`
* **Opciones:**
  - `--salida` / `-o`: Ruta personalizada del `.docx` de salida (por defecto usa el nombre del archivo `.md` o el campo `salida:` del frontmatter).
  - `--tema`: Sobrescribe el tema declarado en el frontmatter.
  - `--citas`: Sobrescribe el estilo de citación (`apa7`, `ieee` o `vancouver`).
  - `--sin-pdf`: Genera únicamente el `.docx` sin invocar LibreOffice.
* **Comportamiento:** Si en la carpeta del `.md` existe un archivo `TAREA.md`, ejecuta automáticamente `comprobar()` y actualiza la cobertura de rúbrica.


