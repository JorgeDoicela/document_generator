# Memoria Arquitectónica del Proyecto (`document_generator`)

## Arquitectura del Framework Documental
- **Separación Framework vs. Workspace Privado:** El repositorio versiona exclusivamente el motor (`plantillas/`), ejemplos reproducibles (`examples/`), pruebas (`tests/`), documentación (`docs/`) y skills IA (`.agents/`). La carpeta `materias/` se mantiene vacía en Git mediante `materias/.gitkeep` y todo su contenido local queda ignorado por `.gitignore`, al igual que `.env` y `themes/local/`.
- **Núcleo Desacoplado:**
  - `plantillas/omml.py`: conversor LaTeX -> Unicode -> OMML (`<m:oMathPara>`) compatible con Word y LibreOffice sin caracteres rotos (`¿`), con segmentación automática de fórmulas extensas (> 75 caracteres).
  - `plantillas/bloques.py`: componentes editoriales universales (`agregar_texto_enriquecido` con soporte Markdown + `` `código inline` ``, `parrafo_estructurado`, `enunciado_formal`, `codigo_bloque`, `tabla_academica`, `caja_captura_evidencia`, `resumen_ejecutivo`, `insertar_indice_automatico`, `aplicar_metadatos`).
  - `plantillas/temas.py`: sistema de temas configurables (`TemaDocumental`) con 5 presets integrados (`apa7`, `academico`, `tecnico`, `ejecutivo`, `ieee`) y carga dinámica desde archivos `theme.json` (`themes/` y `themes/local/`).
  - `plantillas/extractor_tema.py`: extractor automático de temas desde cualquier `.docx` (`./tareas temas --extraer <archivo.docx>`), infiriendo márgenes, tipografía, paleta cromática, estilo de tabla e imágenes embebidas en `themes/local/<nombre>/`.
  - `plantillas/formato_institucional.py`: `MotorInstitucional`, `MotorTecnico`, `MotorEjecutivo` y `MotorIEEE` implementando `BaseDocumentEngine` y registrados en `motor_base.py`.
  - `plantillas/apa_docx.py`: motor APA 7 con soporte completo para temas configurables (`formato=`, `TAREA.md` o `TEMA_DEFECTO` en `.env`) y re-exportación directa de `omml` y `bloques` en `__all__`.
- **Calidad Estática y Seguridad:**
  - `comprobar.py` valida cobertura de rúbricas (marcadores XML `rubrica_C*`), proporcionalidad de palabras, correspondencia biyectiva citas/referencias, fugas LaTeX/Markdown y prohíbe cajas de llamada coloreadas o barras laterales de acento ("estética IA").
  - `servicio_pdf.py` aísla LibreOffice en procesos independientes con cuota de disco y timeout; la copia del PDF final a Descargas es estrictamente opt-in (`COPIAR_PDF_DESCARGAS=true` en `.env`, `false` por defecto).
  - `plataforma.py` centraliza UTF-8 en consola/subprocesos, detección de LibreOffice, resolución de fuentes monoespaciadas y sans-serif en Linux/macOS/Windows, y terminación segura de árboles de procesos.
- **CI/CD:** Matrix GitHub Actions (`ubuntu-latest` y `windows-latest`, Python 3.10 y 3.13) ejecutando `ruff check`, `mypy` y `python -m unittest -v`.
