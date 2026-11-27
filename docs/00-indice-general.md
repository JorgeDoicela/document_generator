# Documentación Técnica — document_generator (rubric-driven)

Bienvenido a la documentación técnica modular de **document_generator**. Este repositorio implementa un sistema integral de ingeniería documental asistido por rúbricas (**rubric-driven architecture**), diseñado para la preparación, estructuración ponderada, generación estandarizada y verificación estática de documentos académicos, técnicos y ejecutivos (APA 7, temas configurables y presets institucionales).

---

## 1. Estructura de la Documentación

La documentación se organiza bajo una taxonomía jerárquica numérica de dos dígitos (`01-`, `02-`, ...), garantizando modularidad, navegación predecible y compatibilidad con generadores de sitios estáticos:

```
docs/
├── 00-indice-general.md                              # Índice maestro y mapa de navegación
├── 01-arquitectura/
│   ├── 01-vision-general-y-patrones.md               # Paradigma rubric-driven, pipeline y componentes
│   └── 02-modelo-de-datos-y-fichas.md                # Esquema de TAREA.md, MATERIA.md y parseo de rúbricas
├── 02-motores-documentales/
│   ├── 00-arquitectura-motores-base.md               # Protocolo BaseDocumentEngine, marcadores XML y catálogo
│   ├── 01-motor-apa7.md                              # Generador APA 7, citas, bibliografía y marcadores
│   ├── 02-motor-institucional-y-temas.md             # Motor multi-propósito, presets/JSON, extractor .docx y OMML
│   └── 03-componentes-visuales-y-tablas.md           # Terminales 300 DPI, tarjetas académicas, código WordML y tablas APA/Grid

├── 03-herramientas-y-cli/
│   ├── 01-especificacion-cli-tareas.md               # Contrato y especificación del CLI tareas
│   └── 02-auditoria-estatica-comprobar.md            # Motor de auditoría estática XML, tipografía y comprobación
├── 04-infraestructura-y-portabilidad/
│   ├── 01-empaquetado-pep621-y-entornos.md           # pyproject.toml, virtualenv y bootstrapping de pip
│   ├── 02-soporte-multiplataforma.md                 # Paridad Linux, macOS y Windows (setup, wrappers, Makefile)
│   └── 03-seguridad-y-githooks.md                    # Hook pre-commit, variables de entorno y privacidad
```

---

## 2. Mapa Rápido de Referencia

| Módulo | Descripción Técnica | Archivos Fuente Relacionados |
|---|---|---|
| [01. Arquitectura General](01-arquitectura/01-vision-general-y-patrones.md) | Principios de diseño *rubric-driven*, flujo de datos y modelo conceptual. | `plantillas/tareas.py`, `plantillas/cli/`, `plantillas/motor_base.py` |
| [02. Modelo de Fichas](01-arquitectura/02-modelo-de-datos-y-fichas.md) | Especificación de esquemas Markdown para metadatos de tareas y materias. | `plantillas/ficha.py`, `plantillas/rubrica.py` |
| [03. Arquitectura de Motores](02-motores-documentales/00-arquitectura-motores-base.md) | Protocolo abstracto BaseDocumentEngine, marcadores XML y catálogo. | `plantillas/motor_base.py` |
| [04. Motor APA 7](02-motores-documentales/01-motor-apa7.md) | Maquetación bajo el estándar APA 7 (estudiante), citación y bibliografía. | `plantillas/apa_docx.py`, `plantillas/motor_base.py`, `plantillas/fuentes_comunes.py` |
| [05. Motor Institucional y Temas](02-motores-documentales/02-motor-institucional-y-temas.md) | Maquetación configurable por presets/JSON (`academico`, `tecnico`, `ejecutivo`, `ieee`), extractor de `.docx`, OMML y bloques editoriales. | `plantillas/formato_institucional.py`, `plantillas/temas.py`, `plantillas/extractor_tema.py`, `plantillas/omml.py`, `plantillas/bloques.py` |
| [06. Componentes Visuales y Tablas](02-motores-documentales/03-componentes-visuales-y-tablas.md) | Terminales 300 DPI, tarjetas académicas sin barra lateral, código WordML y tablas (APA 7 / Grid). | `plantillas/visual.py`, `plantillas/apa_docx.py`, `plantillas/bloques.py` |
| [07. Especificación CLI](03-herramientas-y-cli/01-especificacion-cli-tareas.md) | Comandos del despachador `tareas` (subcomandos, flags y códigos de salida). | `plantillas/tareas.py`, `plantillas/cli/`, `tareas`, `tareas.bat` |
| [08. Auditoría Estática](03-herramientas-y-cli/02-auditoria-estatica-comprobar.md) | Motor de verificación WordML, estética editorial, proporciones y auditoría global. | `plantillas/comprobar.py`, `plantillas/cli/comandos_documentales.py` |
| [09. Empaquetado PEP 621](04-infraestructura-y-portabilidad/01-empaquetado-pep621-y-entornos.md) | Instalación estándar editable, dependencias, calidad y entorno IDE. | `pyproject.toml`, `requirements.txt`, `.vscode/settings.json`, `Makefile` |
| [10. Multiplataforma](04-infraestructura-y-portabilidad/02-soporte-multiplataforma.md) | Scripts de aprovisionamiento en Linux, macOS y Windows. | `setup.sh`, `setup.bat`, `plantillas/cli/servicio_pdf.py` |
| [11. Seguridad y Hooks](04-infraestructura-y-portabilidad/03-seguridad-y-githooks.md) | Controles preventivos contra fugas de `.env`, `materias/` y credenciales. | `.githooks/pre-commit`, `.env.example`, `.gitignore` |

---

## 3. Procedencia y Licencia

Este proyecto deriva de [JosephBano/rubric-driven](https://github.com/JosephBano/rubric-driven) (autor original: **Joseph Andrés Baño Naranjo**) y ha sido adaptado y extendido por **Jorge Doicela** bajo los mismos términos de la licencia MIT, manteniendo intacto el aviso de derechos de autor original en [LICENSE](../LICENSE).

- [Volver al README](../README.md)
