# Memoria Arquitectónica del Proyecto (`document_generator`)

## Arquitectura del Framework Documental
- **Separación Framework vs. Workspace Privado:** El repositorio versiona exclusivamente el motor (`plantillas/`), ejemplos reproducibles (`examples/`), pruebas (`tests/`), documentación (`docs/`) y skills IA (`.agents/`). Las carpetas `materias/`, `themes/`, `themes/local/` y `themes/.previews/` conservan únicamente sus archivos `.gitkeep` en Git y todo su contenido local queda ignorado por `.gitignore`, al igual que `.env`.
- **Núcleo Desacoplado:**
  - `plantillas/omml.py`: conversor LaTeX -> Unicode -> OMML (`<m:oMathPara>`) compatible con Word y LibreOffice sin caracteres rotos (`¿`), con segmentación automática de fórmulas extensas (> 75 caracteres).
  - `plantillas/bloques.py`: componentes editoriales universales (`agregar_texto_enriquecido` con soporte Markdown + `` `código inline` ``, `parrafo_estructurado`, `enunciado_formal`, `codigo_bloque`, `tabla_academica`, `caja_captura_evidencia`, `resumen_ejecutivo`, `insertar_indice_automatico`, `aplicar_metadatos`).
  - `plantillas/temas.py`: sistema de temas configurables (`TemaDocumental`) con `apa7` como único preset integrado oficial y carga dinámica desde archivos `theme.json` (`themes/` y `themes/local/`).
  - `plantillas/extractor_tema.py`: extractor automático de temas desde cualquier `.docx` (`./tareas temas --extraer <archivo.docx>`), infiriendo márgenes, tipografía, paleta cromática, estilo de tabla e imágenes embebidas en `themes/local/<nombre>/`.
  - `plantillas/formato_institucional.py`: `MotorInstitucional` implementando `BaseDocumentEngine` y registrado en `motor_base.py` junto a `MotorAPA7` (`apa7` e `institucional`).
  - `plantillas/apa_docx.py`: motor APA 7 refinado (US Letter 8.5"x11", numeración `PAGE` en Times New Roman 12 pt, `widow_control=True`, `Bibliografia(estilo="apa7|ieee|vancouver")` sin doble punto final) con soporte para temas JSON y re-exportación directa de `omml` y `bloques`.
  - `plantillas/markdown_docx.py`: compilador declarativo Markdown + frontmatter YAML hacia `.docx` (`tareas compilar` / `tareas generar --desde-md`), con parser YAML integrado sin dependencias externas.
  - `plantillas/preview_tema.py`: vistas previas de temas (`tareas temas --preview`) y catálogo comparativo de estilos (`tareas estilos [--catalogo]`).
- **Calidad Estática y Seguridad:**
  - `comprobar.py` valida cobertura de rúbricas (marcadores XML `rubrica_C*`), proporcionalidad de palabras, correspondencia biyectiva citas/referencias (`apa7`, `ieee` `[N]` y `vancouver` `(N)`), fugas LaTeX/Markdown y prohíbe cajas de llamada coloreadas o barras laterales de acento ("estética IA").
  - `visual.py`: bloques de código (`bloque_codigo_word`) protegidos con `w:cantSplit` y `keep_with_next` para evitar cortes entre páginas; `dibujar_tarjeta_academica()` y tablas con layout fijo `apa`/`grid`.
  - `servicio_pdf.py` aísla LibreOffice en procesos independientes con cuota de disco y timeout; la copia del PDF final a Descargas es estrictamente opt-in (`COPIAR_PDF_DESCARGAS=true` en `.env`, `false` por defecto).
  - `plataforma.py` centraliza UTF-8 en consola/subprocesos, detección de LibreOffice, resolución de fuentes monoespaciadas y sans-serif en Linux/macOS/Windows, y terminación segura de árboles de procesos.
- **CI/CD:** Matrix GitHub Actions (`ubuntu-latest` y `windows-latest`, Python 3.10 y 3.13) ejecutando `ruff check`, `mypy` y `python -m unittest -v`.
