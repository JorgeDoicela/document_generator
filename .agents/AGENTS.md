# Instrucciones para agentes de IA

Repositorio de tareas académicas. Ver `README.md` para la instalación y el
formato por defecto de los documentos.

## Antes de nada

- Debe existir `.env` en la raíz con los datos del estudiante. Si falta, detenerse
  y pedir al usuario que lo cree (`cp .env.example .env`). **Nunca** escribir
  datos personales en archivos versionados ni inventarlos.
- Usar siempre el Python de `.venv/` de la raíz. Si algo falla, empezar por
  `.venv/bin/python plantillas/tareas.py verificar`.
- Si se modifica la herramienta (`plantillas/`), ejecutar los tests:
  `.venv/bin/python -m unittest`.

## Estructura

```
plantillas/                       la herramienta: CLI, plantilla APA y moldes. NUNCA guardar tareas aquí
materias/                          todo el contenido, al mismo nivel que plantillas/
  <materia>/                       carpeta en minúsculas con guiones
    MATERIA.md                     ficha: docente, plataforma, formato, reglas + tabla de estado
    <CODIGO>_<Titulo_Corto>/       una carpeta por tarea (A15_..., P2_..., E1_...)
      TAREA.md                     ficha de la tarea con la rúbrica: LEER PRIMERO
      enunciado/                   enunciado y rúbrica del docente (PDF, DOCX, archivos base)
      capturas/                    evidencia real (nunca simulada)
      insumos/                     borradores, aportes de equipo y notas de trabajo
      generar_documento.py         script que produce el entregable
      <CODIGO>_<Titulo_Corto>_<SUFIJO_ARCHIVOS>.docx / .pdf   entregables finales
```

Las materias y tareas se crean solo con `plantillas/tareas.py materia|tarea`,
que las pone en `materias/`; no crear carpetas de materias en otro sitio. Las
tareas antiguas no siguen del todo esta estructura; no reorganizarlas sin pedirlo.

En adelante, `tareas` = `.venv/bin/python plantillas/tareas.py`.

## Cómo resolver una tarea

Al resolver cualquier tarea, es obligatorio aplicar las skills locales del repositorio:
- `tareas-academicas` (.agents/skills/tareas-academicas/SKILL.md): Rigor universitario, investigación en fuentes primarias, cero relleno y citas APA 7 estrictas.
- `ingenieria-documental-docx` (.agents/skills/ingenieria-documental-docx/SKILL.md): Estabilidad OpenXML, prevención de fallos de LibreOffice, tablas con repetición de cabeceras, ecuaciones OMML vectoriales y bookmarks de rúbrica.
- `analisis-rubricas-consignas` (.agents/skills/analisis-rubricas-consignas/SKILL.md): Extracción, desestructuración y normalización de consignas docentes y matrices de rúbrica.
- `laboratorios-ia-ciberseguridad` (.agents/skills/laboratorios-ia-ciberseguridad/SKILL.md): Experimentación verificable, demostraciones formales y captura de evidencia real en `capturas/`.

### Ingesta Rápida de Archivos desde Descargas (`~/Descargas`)
Cuando el usuario mencione que descargó un PDF o DOCX de una tarea (p. ej. "lo tengo en Descargas", "acabo de descargar...", "haz la tarea con el PDF descargado"):
- **Búsqueda inmediata:** Inspeccionar `~/Descargas/` para identificar el archivo por nombre o tomar el PDF/DOCX más reciente (`ls -t ~/Descargas/*.pdf ~/Descargas/*.docx | head -n 5`).
- **Incorporación al repositorio:**
  - Si la tarea no está creada: ejecutar `tareas tarea <materia> <CODIGO> "<Titulo>" --enunciado ~/Descargas/<archivo>` (esto crea la carpeta e importa el archivo a `enunciado/` en un solo paso).
  - Si la tarea ya existe: copiarlo directamente a `materias/<materia>/<tarea>/enunciado/`.
- **Análisis proactivo:** Leer el enunciado de inmediato para extraer objetivos y poblar la rúbrica en `TAREA.md`.

Cuando el usuario pida "haz la tarea materias/<materia>/<carpeta>" (o similar):

1. Leer `TAREA.md` y **todo** el contenido de `enunciado/`, completo.
2. Leer `MATERIA.md` de la materia (docente, formato, nomenclatura, reglas): sus
   reglas prevalecen sobre las de la raíz. Si sus campos están vacíos, se aplica
   el formato por defecto.
3. **Rúbrica.** Debe quedar en la tabla `| ID | Criterio | Puntaje | Dónde se cumple |`
   de `TAREA.md`:
   - si está en un `.docx` de `enunciado/`: `tareas rubrica <tarea> --importar enunciado/<archivo>.docx`
     y revisar que los criterios importados son correctos;
   - si está en PDF o imagen: copiar cada criterio con su puntaje a la tabla;
   - si no hay rúbrica ni criterios, **preguntar** antes de generar.
   `tareas rubrica <tarea>` la muestra con el peso de cada criterio.
4. Formato: lo que diga `TAREA.md` > README de la materia > README de la raíz.
   - "por defecto" → APA 7 con `plantillas/apa_docx.py`.
   - Práctica/experimental sin formato indicado → **preguntar antes de generar**.
5. Si falta algo que solo el usuario puede aportar (capturas de su equipo, datos
   personales, una decisión de enfoque), preguntar en vez de inventarlo.
6. `tareas esqueleto <tarea>`: escribe en `generar_documento.py` una sección por
   criterio con su extensión orientativa. Escribir el contenido en esas
   secciones **sin quitar `criterios="..."`** de los `titulo(...)`, ni
   `transversal(...)`, ni `criterios=` de `referencias(...)`: son lo que la
   comprobación usa. Si se añade una sección para un criterio, marcarla igual.
   Citar con `bib.cita("clave")` / `bib.cita_narrativa("clave")` tras
   `bib.agregar(...)` (`apa7`, `ieee` o `vancouver`); nunca escribir citas a mano sin su referencia.
   (Alternativamente, si la tarea usa flujo declarativo `documento.md`, conservar `# Título {#C1}` y `transversales: [...]` y compilar con `tareas generar <tarea> --desde-md` o `tareas compilar <archivo.md>`).
7. `tareas generar <tarea> --verificar-citas`: genera el `.docx`, lo comprueba contra la rúbrica,
   verifica en línea que DOIs, URLs y obras citadas existan realmente (Crossref/OpenAlex/OpenLibrary/HTTP),
   rellena "Dónde se cumple" en `TAREA.md` y genera el PDF. **Corregir todos
   los `[error]`** (incluidos DOIs inexistentes, DOIs reciclados de otra obra o enlaces 404)
   y revisar los `[aviso]` (secciones poco desarrolladas según su peso, extensión, referencias sin citar
   o referencias sin coincidencia automática). También puede ejecutarse por separado con
   `tareas verificar-citas <tarea>` o `tareas comprobar <tarea> --verificar-citas`.
   Nunca inventar DOIs, URLs ni metadatos bibliográficos desde memoria. Si algún criterio no se puede
   cubrir (p. ej. faltan capturas que solo el usuario puede hacer), decírselo
   al usuario; no rellenarlo con contenido inventado.
   Para consultar todas las variantes editoriales disponibles (tablas `apa`/`grid`, terminales/código `light`/`dark`, citas y temas), ejecutar `./tareas estilos [--catalogo]`.
8. **Auditoría Visual Obligatoria del PDF (antes de marcar `lista`):** Renderizar
   las páginas críticas del PDF (diagramas, tablas con URIs/código y ecuaciones
   OMML) a PNG con `pymupdf` e inspeccionarlas visualmente para garantizar cero
   caracteres rotos (`¿`), cero solapamiento de aristas o texto en diagramas,
   cero cortes de palabras en tablas y pies de figura limpios.
9. Al terminar: `tareas marcar <tarea> lista` (actualiza `TAREA.md` y la tabla
   de `MATERIA.md`). Si `COPIAR_PDF_DESCARGAS=true` está habilitado en `.env`, el PDF final
   queda además copiado automáticamente en `~/Descargas/` listo para subir a la plataforma.
   Solo usar `--forzar` si el usuario lo pide.
10. **Limpieza Post-Entrega (Solo al terminar / confirmar entrega):**
   Una vez que el usuario confirme que ya subió la tarea a la plataforma académica (o se marque
   como `entregada`), limpiar inmediatamente de `~/Descargas/` los archivos fuente descargados
   (PDFs y DOCX de docentes o compañeros) que ya están preservados en el repositorio (`enunciado/`
   e `insumos/`), así como los entregables finalizados. Dejar `~/Descargas/` completamente limpio
   y despejado, listo para recibir los insumos de la siguiente tarea.

## Recordatorios y Estándar Editorial Innegociable

- **Cero Cajas de Llamada Coloreadas y Cero Barras Laterales de Acento ("Estética IA"):** Queda terminantemente prohibido insertar cuadros, tablas de celda única con bordes celestes, fondos sombreados de llamada o **barras/franjas verticales coloreadas en el borde izquierdo** (`border-l-*` en diagramas PNG/SVG o `w:left` grueso asimétrico en OpenXML). Los enunciados docentes y consignas se presentan exclusivamente con tipografía académica limpia en el lienzo (`enunciado_formal`: sangría izquierda de 0.25", negrita en etiqueta y texto en cursiva). Todo nodo o tarjeta de diagrama debe emplear un diseño editorial sobrio de publicación científica (contorno perimetral uniforme y fino, fondo limpio, jerarquía tipográfica y divisor horizontal discreto) mediante `visual.dibujar_tarjeta_academica()`.
- **Prevención de Estiramiento Tipográfico:** Jamás concatenar texto con saltos de línea suaves (`\n` o `<w:br/>`) dentro de un mismo párrafo justificado. Usar siempre `parrafo` o `bloques.parrafo_estructurado` que fragmenta automáticamente en párrafos independientes y viñetas con sangría francesa (hanging indent 0.25").
- **Fórmulas Matemáticas OMML sin Desborde ni Fugas LaTeX:** Toda ecuación se genera con `formula_bloque`, que aplica automáticamente `normalizar_latex_a_unicode()` (erradicando `¿` en LibreOffice) y segmenta fórmulas > 75 caracteres en conectivas lógicas (`dividir_formula_larga`). Queda prohibido dejar comandos LaTeX crudos (`\forall`, `\text{}`, `\mathcal{}`, `\implies`) en párrafos u OMML (`comprobar.py` los bloquea como `[error]`).
- **Tablas con Layout Fijo y Anchos Proporcionales:** `tabla_estilizada` / `tabla_academica` aplican `w:tblLayout="fixed"`, `w:tblGrid` y `w:tcW` explícitos (con cálculo proporcional automático o `anchos=[...]`) para impedir que URIs o identificadores largos se partan a mitad de palabra en LibreOffice.
- **Pies de Figura y Consignas Idempotentes:** `caja_captura_evidencia` y `enunciado_formal` normalizan prefijos y puntuación final, evitando `Figura: Figura N.` o doble punto (`..`) y `Etiqueta: N:`.
- **Cero Fugas de Sintaxis Markdown (`**`):** Queda prohibido dejar asteriscos de Markdown (`**` o `*`) visibles en el lienzo del documento o PDF. El motor tipográfico (`parrafo`, `bloques.parrafo_estructurado`, `vinieta`, `tabla`, `tabla_academica`) procesa automáticamente la sintaxis en runs nativos de Word (`bold`, `italic`), eliminando los caracteres de escape.
- **Nomenclatura Única Oficial de Entregables (Estándar snake_case):**
  - **Individual:** `nombre_apellido_<actividad>_<numero>.pdf` (ej. `ana_perez_tarea_practica_2.pdf`).
  - **Grupal:** `grupo_<numero>_<actividad>_<numero>.pdf` (ej. `grupo_1_clase_practica_3.pdf`, `grupo_1_tarea_practica_3.pdf`).
  - **Exportación a Descargas (Opt-in):** La copia automática a la carpeta Descargas del sistema solo se ejecuta si el usuario habilita `COPIAR_PDF_DESCARGAS=true` en su `.env` local (desactivada por defecto para seguridad de terceros).
- **Aislamiento de Tests:** Los tests unitarios jamás deben copiar archivos temporales a Descargas.
- **Privacidad del Workspace:** El repositorio público versiona únicamente el framework, ejemplos, pruebas y documentación. `materias/*`, `themes/local/*` y `themes/.previews/*` (conservando solo sus `.gitkeep`) junto con `.env` permanecen ignorados en `.gitignore` y nunca deben versionarse.
- **Motores y Temas Configurables:** Usar `apa_docx` para el estándar oficial `apa7` (US Letter, Times New Roman 12 pt, 5 niveles de encabezado, numeración superior derecha en Times New Roman 12 pt, `widow_control=True`) o `formato_institucional` (`nuevo_documento_tematico(..., tema="apa7|paper|<nombre_o_ruta_theme_json>")`) junto con `omml.py` y `bloques.py`. El preset `paper` (alias `arxiv`/`preprint`) aplica diseño de artículo científico moderno (A4, Georgia 11 pt, cabecera directa en pág. 1 con resumen, running header y tablas booktabs). Para redacción sin Python usar `markdown_docx` (`tareas compilar <archivo.md>` o `tareas generar <tarea> --desde-md`). Consultar opciones con `./tareas temas` y `./tareas estilos [--catalogo]`.
- **Extracción Automática de Formato desde `.docx`:** Si el usuario entrega un `.docx` oficial (guía docente o plantilla institucional/corporativa) cuyo formato aún no existe en `themes/local/`, ejecutar `./tareas temas --extraer <archivo.docx> --nombre <slug>` para extraer automáticamente tipografía, márgenes, paleta de colores e imágenes (`theme.json`) en `themes/local/<slug>/` antes de generar el documento.
- Convertir a PDF siempre con `tareas.py pdf` o `generar`, nunca con `soffice` directo:
  un `.docx` mal formado puede hacer que LibreOffice llene `/tmp`.
- Con python-docx, no dejar dos tablas seguidas sin un párrafo entre medias.
