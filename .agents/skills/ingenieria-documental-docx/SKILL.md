---
name: ingenieria-documental-docx
description: Directrices de ingeniería para generación programática de documentos WordML (docx) y conversión a PDF vectorial con LibreOffice. Cubre OMML matemático, diseño editorial de tablas, marcadores de rúbrica OpenXML y prevención de bloqueos de sistema.
---

# Ingeniería Documental OpenXML y Conversión a PDF

Esta skill define los estándares técnicos de bajo nivel para la manipulación de documentos WordML (`.docx`) y su exportación a PDF vectorial mediante `python-docx` y LibreOffice headless en el repositorio.

---

## 1. Reglas Críticas de Estabilidad de LibreOffice

Al compilar documentos `.docx` a `.pdf` mediante el proceso headless de LibreOffice, ciertas inconsistencias de marcado XML pueden provocar cuelgues, consumo excesivo de memoria o bloqueos por llenado de `/tmp`. Se aplican las siguientes reglas innegociables:

1. **Prohibición de Tablas Contiguas sin Separador:**
   * **Regla:** NUNCA insertar dos tablas consecutivas sin un párrafo intermedio entre ellas.
   * **Causa Raíz:** LibreOffice intenta concatenar internamente estructuras de tablas adyacentes mal formadas en el DOM, entrando en un bucle infinito que agota la memoria o satura el disco temporal.
   * **Implementación:**
     ```python
     # Correcto
     tabla_1 = doc.add_table(...)
     p_sep = doc.add_paragraph()
     p_sep.paragraph_format.space_before = Pt(0)
     p_sep.paragraph_format.space_after = Pt(4)
     tabla_2 = doc.add_table(...)
     ```

2. **Ejecución Asilada con Cuotas:**
   * Las conversiones a PDF deben realizarse siempre mediante `tareas.py pdf` o `convertir_pdf()` de `plantillas/cli/servicio_pdf.py`, el cual aísla el entorno en un grupo de procesos independiente (`start_new_session=True`), limita la escritura en disco (`RLIMIT_FSIZE`) y aplica un timeout de 300 segundos.

---

## 2. Motor Tipográfico de Ecuaciones Matemáticas (OMML Vectorial)

Para garantizar rigor académico y tipografía editorial formal en ecuaciones lógicas y matemáticas:

1. **Uso de Cambria Math y OMML:**
   * Prohibido utilizar texto plano en negrita, colores llamativos (azul) o caracteres literales de escape (`^` o `_`) para representar superíndices o subíndices.
   * Las ecuaciones deben integrarse mediante Office Math Markup Language (OMML) nativo (`<m:oMathPara><m:oMath>`), el cual LibreOffice convierte a vectores nítidos en PDF en tipografía estándar **Cambria Math**.

2. **Uso de `formula_bloque` y Normalización LaTeX → Unicode OMML:**
   * Todas las ecuaciones deben generarse mediante `formula_bloque(doc, formula, etiqueta)` de `plantillas/omml.py` (re-exportado en `formato_institucional.py` y `apa_docx.py`).
   * Antes de construir `<m:oMath>`, `texto_a_omml()` y `dividir_formula_larga()` invocan `normalizar_latex_a_unicode()`, traduciendo comandos LaTeX (`\forall`, `\exists`, `\land`, `\lor`, `\implies`, `\in`, `\cup`, `\times`, `\sqcap`, `\sqsubseteq`, alfabeto griego como `\tau`, `\phi`, `\psi`, `\Sigma`, `\Omega`, `\text{}`, `\mathcal{}`, `\Big(`, etc.) a Unicode matemático limpio compatible con Cambria Math y LibreOffice, erradicando de raíz el renderizado de caracteres rotos (`¿`).
   * La función procesa automáticamente sintaxis con potencias (`2^n`, `M^e`, `R^-`), subíndices (`x_i`, `p_sub`) o XML directo de OMML.
   * **Bloqueo Estático:** `plantillas/comprobar.py` audita tanto `w:t` como `m:t` y emite un `[error]` bloqueante ante cualquier comando LaTeX crudo no normalizado.
   * La presentación editorial es limpia: párrafo centrado directamente sobre el lienzo del documento, sin cajas con marcos ni sombreados de fondo.

3. **Constructos Matemáticos Avanzados:**
   * **Fracciones (`<m:f>`):**
     ```xml
     <m:f>
       <m:num><m:r><m:t>Numerador</m:t></m:r></m:num>
       <m:den><m:r><m:t>Denominador</m:t></m:r></m:den>
     </m:f>
     ```
   * **Sumatorias e Integrales (`<m:nary>`):**
     ```xml
     <m:nary>
       <m:naryPr><m:chr m:val="∑"/><m:limLoc m:val="undOvr"/></m:naryPr>
       <m:sub><m:r><m:t>i=1</m:t></m:r></m:sub>
       <m:sup><m:r><m:t>n</m:t></m:r></m:sup>
       <m:e><m:r><m:t>x_i</m:t></m:r></m:e>
     </m:nary>
     ```
   * **Superíndices (`<m:sSup>`) y Subíndices (`<m:sSub>`):**
     ```xml
     <m:sSup>
       <m:e><m:r><m:t>2</m:t></m:r></m:e>
       <m:sup><m:r><m:t>n</m:t></m:r></m:sup>
     </m:sSup>
     ```

---

## 3. Diseño Editorial de Tablas Profesionales

Toda tabla generada para informes académicos debe poseer las propiedades estándar del OpenXML corporativo:

1. **Repetición de Cabecera en Saltos de Página (`w:tblHeader`):**
   * La primera fila de cada tabla debe contener el elemento `w:tblHeader` para que, en caso de extenderse por varias páginas, la cabecera se replique automáticamente en la parte superior de cada página.
   ```python
   tr_pr = t.rows[0]._tr.get_or_add_trPr()
   tbl_header = OxmlElement("w:tblHeader")
   tbl_header.set(qn("w:val"), "true")
   tr_pr.append(tbl_header)
   ```

2. **Protección Contra División de Filas (`w:cantSplit`):**
   * Cada fila de datos del cuerpo de la tabla debe contener `w:cantSplit` para evitar que una fila se parta a la mitad entre dos páginas.
   ```python
   no_partir = OxmlElement("w:cantSplit")
   no_partir.set(qn("w:val"), "true")
   fila._tr.get_or_add_trPr().append(no_partir)
   ```

3. **Estilo Visual y Anchos Fijos Proporcionales (`w:tblLayout="fixed"`):**
   * Cabecera con fondo gris suave `#E8E8E8` en modo `grid` (o fondo limpio con 3 líneas horizontales en modo `apa`), texto en negrita centrado y bordes discretos.
   * Celdas interiores con texto compacto (`tamano_cabecera` y `tamano_cuerpo` configurables en `tabla_academica`/`tabla_estilizada`) e interlineado 1.05.
   * **Bloques de Código sin Cortes (`bloque_codigo_word`):** Los bloques 2×1 aplican `w:cantSplit` en ambas filas y `keep_with_next = True` en la cabecera para impedir que el título del archivo quede separado del código en un salto de página.
   * **Prevención de Cortes de Palabra en LibreOffice:** `tabla_estilizada()` aplica `w:tblLayout w:type="fixed"`, `w:tblW`, `w:tblGrid/w:gridCol` y `w:tcW` explícitos en twips (`dxa`). Si no se pasan `anchos`, `_calcular_anchos_proporcionales()` calcula automáticamente el reparto según el token indivisible más largo y la longitud media por columna, evitando cortes de URIs o identificadores a mitad de palabra.

---

## 4. Inyección de Marcadores OpenXML para Auditoría de Rúbrica

El sistema de verificación estática (`plantillas/comprobar.py`) audita la cobertura de la tarea buscando marcadores de marcador de posición (*bookmarks*) en el XML del documento:

1. **Marcador de Criterio Específico:**
   * En los títulos de sección, inyectar los elementos `w:bookmarkStart` y `w:bookmarkEnd` alrededor del texto con el nombre `rubrica_<ID>` (p. ej. `rubrica_C1`):
   ```python
   inst.titulo_seccion(doc, "Desarrollo del Problema", nivel=1, criterios="C1")
   ```

2. **Marcador de Criterio Transversal:**
   * Para criterios holísticos (ortografía, bibliografía APA 7, trabajo en equipo o formato general), invocar `inst.marcar_transversal(doc, "C5", "C6")` (o `apa_docx.transversal(doc, ...)`) sobre un párrafo del cuerpo del informe antes de finalizar el documento.
   * Esto inyecta marcadores con sufijo `_todo` (`rubrica_C5_todo`).

3. **Ubicación Obligatoria en el Cuerpo:**
   * Los marcadores deben ubicarse siempre **después del primer salto de página de la portada institucional**. Cualquier marcador colocado en la portada queda excluido del análisis de comprobación.

---

## 5. Prohibición de Cajas de Llamada Coloreadas, Barras Laterales de Acento ("Estética IA") y Uso de `enunciado_formal`

1. **Cero Cajas Tipo Primaria y Cero Barras Verticales Izquierdas (`border-l-*` / `w:left`):**
   * Queda estrictamente prohibido utilizar tablas de celda única con marcos coloreados (azul, celeste, gris), fondos sombreados (`#F1F5F9`, `#F8F9FA`) o **barras/franjas verticales de acento pegadas al borde izquierdo** tanto en documentos Word (`w:tcBorders/w:left` o `w:pBdr/w:left` grueso asimétrico) como en tarjetas de diagramas generados con Pillow/Matplotlib. Este patrón visual refleja plantillas genéricas de IA y resulta inaceptable en entregables universitarios e ingeniería.
   * **Auditoría Estática:** `plantillas/comprobar.py` detecta y reporta en `avisos_tipograficos` toda tabla 1×1 o párrafo con borde izquierdo grueso asimétrico (`w:sz >= 18`).
   * **Estándar en Diagramas:** Toda tarjeta o nodo de diagrama debe usar `visual.dibujar_tarjeta_academica()` con contorno perimetral uniforme y fino (`2 px`), fondo limpio, jerarquía tipográfica y divisor horizontal discreto.
2. **Presentación Editorial con `enunciado_formal`:**
   * Los enunciados docentes y consignas se presentan directamente sobre el lienzo del documento mediante `enunciado_formal(doc, texto, etiqueta, numero)`:
     - Sangría izquierda tipográfica de 0.25 pulgadas (`Inches(0.25)`).
     - Etiqueta en negrita Arial 10.5 pt (`Enunciado 1:`, `Pregunta 2:`).
     - Texto de la consigna en cursiva Arial 10.5 pt, sin bordes ni tablas.

---

## 6. Prevención de Deformación Tipográfica en Párrafos Justificados

1. **Causa Raíz de Estiramiento de Líneas:**
   * En Word y LibreOffice, cuando se inserta un salto de línea suave (`\n` o `<w:br/>`) dentro de un mismo párrafo XML (`<w:p>`) con alineación justificada (`WD_ALIGN_PARAGRAPH.JUSTIFY`), el motor tipográfico estira artificialmente las palabras de la línea precedente de margen a margen, produciendo espacios gigantescos y un aspecto antiestético severo.
2. **Solución Canónica con `bloques.parrafo_estructurado` / `inst.parrafo` / `apa_docx.parrafo`:**
   * Todo texto multilínea debe dividirse en párrafos independientes (`<w:p>` separados).
   * Los listados de viñetas (`•`, `-`) o numerados deben estructurarse con alineación izquierda (`LEFT`) y sangría francesa (*hanging indent* de 0.25 in), preservando una lectura técnica impecable.
   * Para documentos extensos, aprovechar los bloques universales de `plantillas/bloques.py`: `resumen_ejecutivo()`, `insertar_indice_automatico()` (campo TOC nativo con `w:updateFields`) y `aplicar_metadatos()`.
3. **Auditoría Estática:**
   * `comprobar.py` audita la presencia de `<w:br/>` en párrafos justificados bajo `avisos_tipograficos`.

---

## 7. Control de Desbordamiento de Fórmulas Matemáticas

1. **Límite de Longitud:**
   * Fórmulas OMML que superen los 75 caracteres tienden a rebasar los márgenes de impresión en documentos con márgenes estándar de 1 pulgada.
2. **Segmentación Automatizada:**
   * `formula_bloque` ejecuta `dividir_formula_larga(formula, max_long=75)` (previa normalización LaTeX → Unicode para medir la longitud visual real) y fragmenta ecuaciones extensas en conectivas lógicas (`⇒`, `⟹`, `→`, `⇔`, `⟺`, `≡`, `⊑`, `∧`, `∨`) en renglones sucesivos centrados, garantizando fidelidad matemática y presentación vectorial nítida.

---

## 8. Eliminación y Procesamiento de Sintaxis Markdown (`**` y `*`)

1. **Prohibición Estricta de Fuga de Sintaxis Markdown:**
   * Queda terminantemente prohibido que aparezcan asteriscos de Markdown (`**` o `*`) como texto literal visible en los documentos Word o archivos PDF generados.
   * **Causa Raíz:** `python-docx` no interpreta sintaxis Markdown por defecto; cadenas que contienen `**texto**` pasadas directamente a `add_run()` imprimen los asteriscos como caracteres literales, arruinando la calidad profesional del documento.
2. **Procesamiento Nativo con Motor de Texto Enriquecido:**
   * Todo texto con formato en negrita (`**negrita**`), cursiva (`*cursiva*`), combinada (`***negrita cursiva***`) o código en línea (`` `codigo` ``) debe procesarse mediante el parser integrado en `plantillas/bloques.py` (`agregar_texto_enriquecido`) y `plantillas/apa_docx.py` (`_agregar_texto_enriquecido`).
   * Las funciones de alto nivel (`inst.parrafo`, `bloques.parrafo_estructurado`, `apa_docx.parrafo`, `vinieta`, `tabla`, `bloques.tabla_academica`, `bloques.enunciado_formal`) tokenizan la cadena y descomponen el texto en runs nativos de OpenXML (`r.bold = True`, `r.italic = True`, `Courier New` para inline code), eliminando de raíz los caracteres de escape.
3. **Auditoría Estática:**
   * `plantillas/comprobar.py` audita de forma estática la presencia de asteriscos literales (`**`) en todos los párrafos del documento bajo `avisos_tipograficos`, bloqueando entregas con fugas de marcado.

---

## 9. Prevención de Desbordamiento y Colisión de Texto en Diagramas Vectoriales y Marcos

Para garantizar calidad editorial nítida y profesional en diagramas conceptuales, redes ontológicas y marcos (frames) generados programáticamente:

1. **Prohibición Estricta de Colisión de Texto con Bordes:**
   * Queda terminantemente prohibido que las etiquetas de texto, valores de ranuras (slots) o descripciones sobrepasen las cajas delimitadoras (*bounding boxes*) o queden intersectadas por las líneas de borde de los rectángulos.
   * **Causa Raíz:** El posicionamiento horizontal con coordenadas $X$ fijas en una sola línea (p. ej., `x=0.62` para un valor largo dentro de una caja que termina en `x=0.92`) agota el espacio horizontal y desborda el texto sobre la línea perimetral de la tarjeta.
2. **Arquitectura Estructurada en Dos Sub-filas por Ranura:**
   * Al diagramar marcos (frames), cada ranura debe organizarse en dos niveles visuales:
     - **Sub-fila 1 (Metadatos):** Nombre de la ranura alineado a la izquierda en negrita (`• Ranura: <nombre>`) y etiqueta de tipo de dato anclada a la derecha con sangría defensiva (`Tipo: [<tipo>]`).
     - **Sub-fila 2 (Valor Asignado):** Valor asignado (`Valor = <valor>`) con sangría izquierda de 0.02 unidades, aprovechando el ancho horizontal completo de la tarjeta (hasta un 90% del contenedor).
3. **Control Defensivo de Ancho y Truncamiento Seguro:**
   * Toda cadena de valor debe pasar por control de longitud (`textwrap.shorten` o truncamiento con elipsis defensiva si excede los 85 caracteres en marcos individuales o 46 caracteres en columnas jerárquicas dobles).
   * Utilizar siempre las funciones canónicas del motor gráfico: `renderizar_diagrama_marco_formal` y `renderizar_diagrama_marcos_jerarquicos` de `plantillas/visual.py`.

---

## 10. Enrutamiento Geométrico de Grafos Ontológicos, Pies de Figura y Auditoría Visual de PDF

1. **Enrutamiento Geométrico en Grafos Dirigidos (Matplotlib):**
   * Toda arista debe anclarse estrictamente en los **bordes exteriores** de los nodos (nunca en los centros), con `shrinkA=1..2, shrinkB=1..2`.
   * **Convención de Curvatura `arc3`:** En aristas horizontales de izquierda a derecha, un valor negativo (`rad=-0.12`) curva el arco **hacia arriba** (sobrepasando limpiamente nodos intermedios); en aristas de derecha a izquierda, un valor negativo (`rad=-0.18`) curva el arco **hacia abajo**. Jamás permitir que una arista atraviese el cuerpo o el texto de un nodo.
   * **Ajuste de Texto Obligatorio:** Toda tarjeta con múltiples viñetas debe envolver líneas con `textwrap.wrap` acorde al ancho real del contenedor y reservar canales vacíos entre columnas para las flechas.
2. **Pies de Figura y Etiquetas Idempotentes:**
   * `caja_captura_evidencia()` evita automáticamente prefijos duplicados (`Figura: Figura N.`) y puntos finales repetidos (`..`).
   * `enunciado_formal()` elimina dos puntos redundantes en etiquetas numeradas (`Consigna Docente 1:`).
   * `plantillas/comprobar.py` audita pies de figura duplicados o con doble punto en `avisos_tipograficos`.
3. **Inspección Visual Obligatoria Post-PDF:**
   * Antes de marcar una tarea como `lista`, renderizar las páginas críticas del PDF (diagramas, tablas densas y ecuaciones OMML) a PNG con `pymupdf` e inspeccionarlas visualmente para certificar cero caracteres rotos, cero colisiones gráficas y cero cortes de palabra.



