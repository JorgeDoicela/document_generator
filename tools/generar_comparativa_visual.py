# -*- coding: utf-8 -*-
"""Generador autocontenido del documento comparativo de estilos visuales.

Produce un documento WordML y su PDF con variantes Dark/Light de terminales 300 DPI,
bloques de código, fórmulas OMML y estilos de tablas (APA 7 vs. Grid) sin depender de
herramientas externas ni rutas específicas de usuario.
"""
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from plantillas import bloques, omml  # noqa: E402
from plantillas import formato_institucional as inst  # noqa: E402
from plantillas.cli.servicio_pdf import convertir_pdf  # noqa: E402
from plantillas.visual import (  # noqa: E402
    EstilosTabla,
    Temas,
    bloque_codigo_word,
    renderizar_terminal,
    tabla_estilizada,
)

DIR_SALIDA = RAIZ / "docs" / "comparativa_estilos"
DIR_SALIDA.mkdir(parents=True, exist_ok=True)
DOCX_SALIDA = DIR_SALIDA / "comparativa_estilos_visuales.docx"
IMG_DARK = DIR_SALIDA / "terminal_ejemplo_dark.png"
IMG_LIGHT = DIR_SALIDA / "terminal_ejemplo_light.png"


def generar(nombre_proyecto: str | None = None) -> Path:
    salida_demo = (
        "Iniciando auditoria estatica del documento...\n"
        "  [ok] Rubrica cubierta: 5/5 criterios (100%)\n"
        "  [ok] Formulas OMML sin fugas LaTeX: 4/4\n"
        "  [ok] Citas y referencias APA 7: correspondencia biyectiva\n"
        "Estado final: 0 errores, 0 avisos.\n"
    )
    proyecto = (nombre_proyecto or RAIZ.name).strip() or "document_generator"
    prompt_dinamico = f"user@workstation:~/{proyecto}$ "
    renderizar_terminal(
        titulo_ventana="CLI tareas — Auditoría Estática (Tema Dark)",
        comando_mostrado="./tareas comprobar examples/ejemplo_completo",
        salida_lineas=salida_demo,
        ruta_salida=IMG_DARK,
        tema=Temas.DARK,
        prompt_user=prompt_dinamico,
    )
    renderizar_terminal(
        titulo_ventana="CLI tareas — Auditoría Estática (Tema Light)",
        comando_mostrado="./tareas comprobar examples/ejemplo_completo",
        salida_lineas=salida_demo,
        ruta_salida=IMG_LIGHT,
        tema=Temas.LIGHT,
        prompt_user=prompt_dinamico,
    )

    doc = inst.nuevo_documento_tematico(
        titulo="Guía y Comparativa de Estilos Visuales",
        subtitulo="Framework Documental Rubric-Driven",
        tema="apa7",
        institucion="Proyecto Open Source",
        organizacion="Motor Documental",
        integrantes=["Equipo Editorial"],
    )

    bloques.resumen_ejecutivo(
        doc,
        "Este documento demuestra de forma autocontenida las capacidades tipográficas, "
        "matemáticas (OMML), de terminales a 300 DPI, bloques de código y estilos de tabla "
        "disponibles en el framework.",
        palabras_clave=["WordML", "OMML", "APA 7", "Rubric-Driven", "Documentación Técnica"],
    )

    inst.titulo_seccion(doc, "1. Terminales CLI a 300 DPI (Dark y Light)", nivel=1)
    bloques.caja_captura_evidencia(doc, IMG_DARK, "Figura 1. Salida de terminal con tema Dark (Tokyo Night).")
    bloques.caja_captura_evidencia(doc, IMG_LIGHT, "Figura 2. Salida de terminal con tema Light (Academic Paper).")

    inst.titulo_seccion(doc, "2. Bloques de Código y Ecuaciones OMML", nivel=1)
    bloque_codigo_word(
        doc,
        'def validar_cobertura(criterios: list[str]) -> float:\n    return 100.0 if criterios else 0.0\n',
        archivo="validacion.py",
        lenguaje="Python",
        tema=Temas.LIGHT,
    )
    omml.formula_bloque(
        doc,
        r"\forall x \in \mathcal{D} : \text{Valido}(x) \implies \text{Cobertura}(x) = 100\%",
        "Ecuación 1. Normalización automática de LaTeX a OMML vectorial.",
    )

    inst.titulo_seccion(doc, "3. Comparativa de Tablas (APA 7 vs. Grid)", nivel=1)
    encabezados = ["Modo", "Tipografía", "Interlineado", "Caso de Uso"]
    filas = [
        ["apa7 (oficial)", "Times New Roman 12 pt", "2.0", "Ensayos y trabajos universitarios APA 7"],
        ["theme.json", "Configurable", "Configurable", "Plantillas institucionales o personalizadas"],
        ["--extraer DOCX", "Inferida del .docx", "Inferido", "Clonado automático de formatos docentes"],
    ]
    tabla_estilizada(
        doc,
        encabezados=encabezados,
        filas=filas,
        estilo=EstilosTabla.APA,
        numero_tabla=1,
        titulo_tabla="Estilos de Tabla — Norma APA 7 (3 líneas horizontales)",
    )
    inst.parrafo(doc, "")
    tabla_estilizada(
        doc,
        encabezados=encabezados,
        filas=filas,
        estilo=EstilosTabla.GRID,
        numero_tabla=2,
        titulo_tabla="Estilos de Tabla — Cuadrícula Institucional Completa (Grid)",
    )

    doc.save(str(DOCX_SALIDA))
    convertir_pdf([DOCX_SALIDA], RAIZ)
    return DOCX_SALIDA


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Genera la comparativa visual DOCX/PDF y capturas de terminal.")
    parser.add_argument("--proyecto", default=None, help="Nombre del proyecto mostrado en el prompt (defecto: carpeta raíz).")
    args = parser.parse_args()
    generar(args.proyecto)
