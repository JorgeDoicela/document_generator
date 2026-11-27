# Motor Documental Institucional y Sistema de Temas (`formato_institucional`, `temas`, `extractor_tema`)

Los módulos `plantillas.formato_institucional`, `plantillas.temas`, `plantillas.extractor_tema`, `plantillas.omml` y `plantillas.bloques` conforman un motor documental multi-propósito totalmente desacoplado de marcas o universidades específicas.

Permite generar informes académicos, especificaciones técnicas (RFCs), reportes ejecutivos, artículos estilo IEEE o documentos con la identidad visual de cualquier institución mediante **presets integrados** o archivos **`theme.json`** configurables.

---

## 1. Catálogo de Presets y Temas JSON (`plantillas.temas`)

El sistema incluye cinco presets integrados y carga dinámicamente temas personalizados desde `themes/<nombre>/theme.json` o `themes/local/<nombre>/theme.json` (ignorado por Git para marcas privadas):

| Preset | Tipografía | Interlineado | Estilo de Tabla | Caso de Uso |
|---|---|---|---|---|
| `apa7` | Times New Roman 12 pt | `2.0` | `apa` (3 líneas) | Ensayos y trabajos universitarios bajo APA 7. |
| `academico` | Arial 11 pt | `1.15` | `grid` | Informes académicos e institucionales modernos. |
| `tecnico` | Calibri 10.5 pt | `1.15` | `grid` | Laboratorios, arquitectura de software y RFCs. |
| `ejecutivo` | Arial 10.5 pt | `1.2` | `apa` | Propuestas, reportes gerenciales y memorias. |
| `ieee` | Times New Roman 10.5 pt | `1.08` | `apa` | Artículos científico-técnicos compactos. |

### Esquema de `theme.json`

Un tema personalizado se crea manualmente (`./tareas temas --crear mi-tema --base academico --local`) o se extrae automáticamente desde cualquier plantilla `.docx` existente (`./tareas temas --extraer plantilla.docx --nombre mi-tema`):

| Clave JSON | Tipo | Uso |
|---|---|---|
| `hereda` | `str` | Preset base (`apa7`, `academico`, `tecnico`, `ejecutivo`, `ieee`). |
| `fuente`, `tamano_cuerpo`, `tamano_h1..h3` | `str` / `float` | Jerarquía tipográfica de cuerpo y encabezados. |
| `interlineado`, `espacio_despues`, `margen_*` | `float` | Geometría de página (márgenes en pulgadas) y espaciado. |
| `color_primario`, `color_texto`, `color_secundario` | Hex (`#1B365D`) o RGB | Paleta cromática de títulos, portada y pies. |
| `estilo_tabla` | `"apa"` \| `"grid"` | Estilo de tablas por defecto del tema. |
| `logo_portada`, `imagen_encabezado`, `banner_inferior` | Ruta relativa opcional | Activos gráficos locales (escudo, membrete y banner inferior). |
| `encabezado_texto`, `pie_texto` | `str` | Textos opcionales de encabezado y pie de página. |

---

## 2. Portada Formal y Autoría Desacoplada (`aplicar_portada`)

`formato_institucional.aplicar_portada()` (invocada automáticamente por `nuevo_documento_tematico()` y por `apa_docx.nuevo_documento(..., formato=...)`) soporta autoría individual, grupal y corporativa:

1. **Modalidad Individual vs. Grupal:**
   - **Individual:** imprime `ESTUDIANTE:` (en temas académicos o tareas con `TAREA.md`) o `AUTOR:` (en temas técnicos/ejecutivos/IEEE), tomando estrictamente el primer integrante (`lista[:1]`).
   - **Grupal:** imprime `{(grupo or 'GRUPO DE TRABAJO').upper()} — INTEGRANTES:` seguido de la lista completa de integrantes.
2. **Resolución Jerárquica de Integrantes:**
   - Parámetro explícito `integrantes` → metadatos de `TAREA.md` → `INTEGRANTES_DEFECTO` en `.env` → `NOMBRE_ESTUDIANTE` en `.env` → fallback `"Autor"`.
3. **Encabezados y Paginación Idempotente (`configurar_pagina`):**
   - Activa `different_first_page_header_footer = True` para mantener la portada limpia.
   - A partir de la página 2, inserta `imagen_encabezado` (si existe) o `encabezado_texto`, junto con el campo nativo `PAGE` en el pie de página.
   - Si el tema define `banner_inferior`, lo renderiza al pie de la carátula.

---

## 3. Trazabilidad de Rúbricas (`titulo_seccion` y `marcar_transversal`)

Para que cualquier documento generado con un tema institucional o técnico pase la auditoría estática (`./tareas comprobar`), el motor inyecta estilos nativos `Heading 1..3` y marcadores XML (`w:bookmarkStart`):

```python
from plantillas import formato_institucional as inst

doc = inst.nuevo_documento_tematico(
    titulo="Especificación de Arquitectura",
    subtitulo="RFC-01",
    tema="tecnico",
    incluir_indice=True,
)
inst.titulo_seccion(doc, "1. Alcance y Requisitos", nivel=1, criterios="C1")
inst.parrafo(doc, "Cuerpo con **negrita**, *cursiva* y `código inline`.")
inst.marcar_transversal(doc, "C4")
```

> [!IMPORTANT]
> `marcar_transversal()` debe invocarse sobre un párrafo del cuerpo del documento (después del salto de página de la portada y antes de `doc.save()`).

---

## 4. Motor Matemático OMML Vectorial (`plantillas.omml`)

El módulo `plantillas/omml.py` (re-exportado por `formato_institucional` y `apa_docx`) convierte expresiones matemáticas y lógicas en nodos **Office Math Markup Language (OMML)** nativos (`<m:oMathPara><m:oMath>`), compatibles con Microsoft Word y LibreOffice Writer:

* **Normalización Automática LaTeX → Unicode (`normalizar_latex_a_unicode`):** traduce comandos LaTeX (`\forall`, `\exists`, `\land`, `\lor`, `\implies`, `\in`, `\cup`, `\times`, `\sqcap`, `\sqsubseteq`, `\text{}`, `\mathcal{}`, `\Big(`, letras griegas, etc.) a símbolos Unicode compatibles con Cambria Math, evitando caracteres rotos (`¿`) al exportar a PDF.
* **Conversión a OMML (`texto_a_omml`):** transforma exponentes (`2^n`, `R^-`), subíndices (`x_i`) y super/subíndices combinados en estructuras `<m:sSup>`, `<m:sSub>` y `<m:sSubSup>`, respetando bloques OMML crudos cuando se suministran directamente.
* **Segmentación Inteligente (`dividir_formula_larga`):** divide fórmulas mayores a 75 caracteres sobre conectivas lógicas (`⇒`, `⟹`, `→`, `⇔`, `⟺`, `≡`, `⊑`, `∧`, `∨`) en renglones centrados consecutivos.

---

## 5. Bloques Editoriales Universales (`plantillas.bloques`)

`plantillas/bloques.py` centraliza los componentes editoriales agnósticos del tema:

* `agregar_texto_enriquecido()`: procesa `***negrita cursiva***`, `**negrita**`, `*cursiva*`, `` `código inline` ``, superíndices (`^n`) y subíndices (`_{sub}`) en runs nativos de Word sin fugas de sintaxis Markdown.
* `parrafo_estructurado()`: fragmenta saltos de línea `\n` en párrafos independientes y aplica sangría francesa en viñetas (`•`, `-`, `*`), previniendo el estiramiento tipográfico en texto justificado.
* `enunciado_formal()`: presenta consignas y enunciados sobre el lienzo limpio (sangría 0.25", etiqueta en negrita y texto en cursiva, sin recuadros ni barras laterales).
* `tabla_academica()`: genera tablas con layout fijo (`w:tblLayout="fixed"`) y anchos proporcionales en estilo `apa` o `grid`.
* `resumen_ejecutivo()`, `insertar_indice_automatico()`, `caja_captura_evidencia()`, `codigo_bloque()` y `aplicar_metadatos()`.
