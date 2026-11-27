# -*- coding: utf-8 -*-
"""Comandos CLI de gestión de temas documentales y catálogo visual de estilos."""
from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Callable

_PLANTILLAS_DIR = str(Path(__file__).resolve().parent.parent)
if _PLANTILLAS_DIR not in sys.path:
    sys.path.insert(0, _PLANTILLAS_DIR)

if __package__ and "." in __package__:
    from .. import extractor_tema, preview_tema
    from .. import temas as temas_mod
    from . import servicio_pdf
else:
    import extractor_tema  # type: ignore[no-redef]
    import preview_tema  # type: ignore[no-redef]
    import temas as temas_mod  # type: ignore[no-redef]
    from cli import servicio_pdf  # type: ignore[no-redef]


def exportar_preview_pdf(rutas: list[Path], raiz: Path, *, conservar_docx: bool) -> None:
    """Convierte documentos de vista previa a PDF y limpia los .docx temporales por defecto."""
    fallos = servicio_pdf.convertir_pdf(rutas, raiz)
    if fallos:
        sys.exit(1)
    if not conservar_docx:
        for docx_tmp in rutas:
            if docx_tmp.with_suffix(".pdf").is_file():
                docx_tmp.unlink(missing_ok=True)


def cmd_temas(args, raiz: Path, ruta_relativa: Callable[[Path], str]) -> None:
    """Lista los temas documentales, crea un molde, extrae desde .docx o genera vista previa."""
    if getattr(args, "preview", None):
        try:
            rutas = preview_tema.generar_previews(
                args.preview,
                salida=getattr(args, "salida", None),
                estilo_citas=getattr(args, "citas", None),
            )
        except (FileNotFoundError, ValueError) as exc:
            sys.exit(f"Error al generar vista previa: {exc}")
        if not rutas:
            print("No hay temas personalizados en themes/ o themes/local/ para previsualizar.")
            print("Para ver apa7 y todos los estilos disponibles ejecuta: ./tareas estilos --catalogo")
            return
        if getattr(args, "sin_pdf", False):
            for r in rutas:
                print(f"Vista previa DOCX: {ruta_relativa(r)}")
            return
        conservar = getattr(args, "salida", None) is not None
        exportar_preview_pdf(rutas, raiz, conservar_docx=conservar)
        for r in rutas:
            print(f"Vista previa PDF: {ruta_relativa(r.with_suffix('.pdf'))}")
        return

    if args.extraer:
        try:
            res = extractor_tema.extraer_tema_desde_docx(
                args.extraer,
                nombre=args.nombre,
                privado=not args.compartido,
            )
        except (FileNotFoundError, ValueError) as exc:
            sys.exit(f"Error al extraer tema: {exc}")
        print(f"Tema extraído: {res.tema.nombre} -> {ruta_relativa(res.ruta_json)}")
        for det in res.detalles:
            print(f"  - {det}")
        print(f"  Úsalo en tus documentos con: tema={res.tema.nombre!r}")
        return

    if args.crear:
        slug = re.sub(r"[^a-z0-9_-]+", "-", args.crear.strip().lower()).strip("-")
        if not slug:
            sys.exit("Nombre de tema no válido.")
        base_dir = temas_mod.DIR_TEMAS_LOCALES if args.local else temas_mod.DIR_TEMAS
        archivo = temas_mod.exportar_molde_tema(base_dir / slug, nombre=slug, base=args.base)
        print(f"Molde de tema creado: {ruta_relativa(archivo)}")
        print("  Edita colores, fuente y rutas opcionales a logo/banner/membrete.")
        return

    print(f"{'Tema':<16} {'Fuente':<18} {'Tablas':<8} Descripción")
    print("-" * 88)
    for nombre in temas_mod.listar_temas():
        t = temas_mod.cargar_tema(nombre)
        print(f"{t.nombre:<16} {t.fuente:<18} {t.estilo_tabla:<8} {t.descripcion}")


def cmd_estilos(args, raiz: Path, ruta_relativa: Callable[[Path], str]) -> None:
    """Muestra todos los estilos elegibles por elemento o genera un muestrario visual (.docx/.pdf)."""
    if getattr(args, "catalogo", False):
        try:
            ruta = preview_tema.generar_catalogo_estilos(
                tema=getattr(args, "tema", None) or "apa7",
                salida=getattr(args, "salida", None),
            )
        except (FileNotFoundError, ValueError) as exc:
            sys.exit(f"Error al generar catálogo de estilos: {exc}")
        if getattr(args, "sin_pdf", False):
            print(f"Catálogo visual DOCX: {ruta_relativa(ruta)}")
            return
        conservar = getattr(args, "salida", None) is not None
        exportar_preview_pdf([ruta], raiz, conservar_docx=conservar)
        print(f"Catálogo visual PDF: {ruta_relativa(ruta.with_suffix('.pdf'))}")
        return

    for grupo in preview_tema.obtener_catalogo_estilos():
        print(f"\n[{grupo['elemento']}]")
        print(f"  Dónde se elige: {grupo['config']}")
        for clave, desc in grupo["opciones"]:
            print(f"    - {clave:<14} {desc}")
    print("\nPara ver una comparativa visual real en PDF ejecuta:")
    print("  ./tareas estilos --catalogo")
