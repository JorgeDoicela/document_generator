# -*- coding: utf-8 -*-
"""Generador de vistas previas (muestras visuales) para temas documentales.

Compila rápidamente un documento de muestra completo (portada, resumen ejecutivo,
encabezados H1-H3, texto enriquecido, enunciado formal, ecuación OMML, tabla en
el estilo del tema, bloque de código y referencias) para validar visualmente
cualquier preset integrado o tema JSON personalizado.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import List, Optional, Union

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import apa_docx
    import bloques
    import formato_institucional as fmt_inst
    import omml
    import temas as temas_mod
else:
    from . import apa_docx, bloques, omml
    from . import formato_institucional as fmt_inst
    from . import temas as temas_mod

DIR_PREVIEWS = temas_mod.DIR_TEMAS / ".previews"


def _hex_rgb(rgb: temas_mod.RGBTuple) -> str:
    return f"#{rgb[0]:02X}{rgb[1]:02X}{rgb[2]:02X}"


def generar_preview_tema(
    tema: Union[str, Path, temas_mod.TemaDocumental],
    *,
    salida: Optional[Union[str, Path]] = None,
    estilo_citas: Optional[str] = None,
) -> Path:
    """Genera un archivo `.docx` de muestra visual para el tema indicado."""
    t = temas_mod.cargar_tema(tema)
    estilo_ref = estilo_citas or ("ieee" if t.nombre == "ieee" else "apa7")

    if salida is not None:
        ruta_salida = Path(salida).resolve()
    else:
        DIR_PREVIEWS.mkdir(parents=True, exist_ok=True)
        ruta_salida = (DIR_PREVIEWS / f"preview_{t.nombre}.docx").resolve()

    bib = apa_docx.Bibliografia(estilo=estilo_ref)
    bib.agregar(
        "russell2021",
        ["Russell, S.", "Norvig, P."],
        2021,
        "Artificial Intelligence: A Modern Approach",
        "Pearson",
        detalles="4.a ed.",
    )
    bib.agregar(
        "nist2024",
        ["National Institute of Standards and Technology"],
        2024,
        "The NIST Cybersecurity Framework (CSF) 2.0",
        "U.S. Department of Commerce",
        url="https://doi.org/10.6028/NIST.CSWP.29",
    )

    if t.nombre == "apa7":
        doc, _, _ = apa_docx.nuevo_documento(
            titulo=f"Muestra Visual del Tema: {t.nombre}",
            materia="Validación Tipográfica y Editorial",
            salida=ruta_salida,
            institucion="document_generator",
            carrera="Ingeniería Documental",
            nombre="Autor de Muestra",
            docente="Comité de Revisión",
            fecha="2026",
            formato="apa7",
        )
    else:
        doc = fmt_inst.nuevo_documento_tematico(
            titulo=f"Muestra Visual del Tema: {t.nombre}",
            subtitulo=t.descripcion or "Validación Tipográfica y Editorial",
            tema=t,
            institucion="document_generator",
            organizacion="Ingeniería Documental",
            docente="Comité de Revisión",
            periodo="2026",
            integrantes=["Autor de Muestra"],
        )

    bloques.resumen_ejecutivo(
        doc,
        f"Este documento de muestra valida la identidad visual del tema **{t.nombre}**, "
        f"verificando portada, jerarquía de encabezados, tipografía ({t.fuente} {t.tamano_cuerpo} pt), "
        f"ecuaciones OMML vectoriales, tablas en estilo `{t.estilo_tabla}` y referencias en formato `{estilo_ref}`.",
        palabras_clave=[t.nombre, t.fuente, t.estilo_tabla, estilo_ref],
        fuente=t.fuente,
        tamano=max(t.tamano_cuerpo - 0.5, 9.5),
        color_titulo=t.rgb_primario(),
    )

    apa_docx.titulo(doc, "1. Parámetros de Identidad del Tema", nivel=1)
    apa_docx.parrafo(
        doc,
        f"El tema **{t.nombre}** emplea la familia tipográfica *{t.fuente}* con cuerpo de "
        f"`{t.tamano_cuerpo} pt`, interlineado `{t.interlineado}` y tablas en modo `{t.estilo_tabla}`. "
        f"La estructura sigue principios de ingeniería documental determinista {bib.cita('russell2021')} "
        f"y trazabilidad verificable {bib.cita('nist2024')}.",
    )

    bloques.tabla_academica(
        doc,
        ["Propiedad", "Valor Configurado", "Propósito Editorial"],
        [
            ["Fuente principal", f"{t.fuente} ({t.tamano_cuerpo} pt)", "Cuerpo de texto y tablas"],
            ["Encabezados (H1 / H2 / H3)", f"{t.tamano_h1} / {t.tamano_h2} / {t.tamano_h3} pt", "Jerarquía estructural"],
            ["Interlineado / Post-espacio", f"{t.interlineado} / {t.espacio_despues} pt", "Densidad de lectura"],
            ["Márgenes (Sup/Inf/Izq/Der)", f"{t.margen_sup}\" / {t.margen_inf}\" / {t.margen_izq}\" / {t.margen_der}\"", "Caja tipográfica"],
            ["Paleta (Primario / Texto)", f"{_hex_rgb(t.color_primario)} / {_hex_rgb(t.color_texto)}", "Contraste y sobriedad"],
            ["Estilo de tablas", t.estilo_tabla, "Layout fijo compatible con LibreOffice"],
        ],
        estilo=t.estilo_tabla,
        fuente=t.fuente,
        tamano_cuerpo=max(t.tamano_cuerpo - 1.0, 9.0),
    )

    apa_docx.titulo(doc, "1.1 Enunciado Formal y Ecuación OMML", nivel=2)
    bloques.enunciado_formal(
        doc,
        "Comprobar que la tipografía, las ecuaciones matemáticas vectoriales y el código fuente "
        "se renderizan sin desbordes ni caracteres corruptos al exportar a PDF.",
        numero="",
        etiqueta="Consigna de validación",
        fuente=t.fuente,
    )
    omml.formula_bloque(
        doc,
        r"\forall x \in \mathcal{D} : \text{Calidad}(x) \geq \tau \implies \text{Aprobado}(x)",
        "Ecuación 1. Condición formal de validación documental.",
    )

    apa_docx.titulo(doc, "1.1.1 Bloque de Código de Referencia", nivel=3)
    bloques.codigo_bloque(
        doc,
        f'from plantillas import formato_institucional as inst\ndoc = inst.nuevo_documento_tematico(titulo="Demo", tema="{t.nombre}")',
        etiqueta="python",
        fuente_pie=t.fuente,
    )

    apa_docx.referencias(doc, bib)
    apa_docx.guardar_documento(doc, ruta_salida)
    return ruta_salida


def generar_previews(
    objetivo: str,
    *,
    salida: Optional[Union[str, Path]] = None,
    estilo_citas: Optional[str] = None,
) -> List[Path]:
    """Genera vista previa para un tema específico o para 'todos' los temas disponibles."""
    if objetivo.strip().lower() in ("todos", "all"):
        rutas: List[Path] = []
        base_dir = Path(salida).resolve() if salida is not None else DIR_PREVIEWS
        base_dir.mkdir(parents=True, exist_ok=True)
        for nombre in temas_mod.listar_temas():
            rutas.append(
                generar_preview_tema(
                    nombre,
                    salida=base_dir / f"preview_{nombre}.docx",
                    estilo_citas=estilo_citas,
                )
            )
        return rutas

    return [generar_preview_tema(objetivo, salida=salida, estilo_citas=estilo_citas)]
