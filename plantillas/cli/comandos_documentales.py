# -*- coding: utf-8 -*-
"""Comandos de ingeniería documental: rubrica, esqueleto, generar, comprobar y auditar."""
import re
import subprocess
import sys
from pathlib import Path
from typing import Callable, Optional

_PLANTILLAS_DIR = str(Path(__file__).resolve().parent.parent)
if _PLANTILLAS_DIR not in sys.path:
    sys.path.insert(0, _PLANTILLAS_DIR)

if __package__ and "." in __package__:
    from .. import comprobar as comp
    from .. import esqueleto as esq
    from .. import ficha, markdown_docx, plataforma
    from .. import rubrica as rub
else:
    import comprobar as comp  # type: ignore[no-redef]
    import esqueleto as esq  # type: ignore[no-redef]
    import ficha  # type: ignore[no-redef]
    import markdown_docx  # type: ignore[no-redef]
    import plataforma  # type: ignore[no-redef]
    import rubrica as rub  # type: ignore[no-redef]



def cmd_rubrica(args, carpeta_tarea_fn: Callable[[str], Path]) -> None:
    """Muestra o importa la rúbrica de una tarea académica."""
    carpeta = carpeta_tarea_fn(args.tarea)
    tarea_md = carpeta / "TAREA.md"
    if getattr(args, "importar", None):
        origen = Path(args.importar)
        if not origen.is_absolute() and not origen.exists():
            origen = carpeta / origen
        if not origen.exists():
            sys.exit(f"No existe {args.importar}")
        if origen.suffix.lower() != ".docx":
            sys.exit(
                "Solo se importan rúbricas en .docx. Para un PDF o una imagen, copia los "
                "criterios a la tabla de TAREA.md (o pídeselo al agente)."
            )
        criterios = rub.importar_docx(origen)
        if not criterios:
            sys.exit(f"No encontré ninguna tabla de rúbrica en {origen.name}.")
        existentes = rub.leer(tarea_md)
        if existentes and not getattr(args, "forzar", False):
            sys.exit(f"TAREA.md ya tiene {len(existentes)} criterios; usa --forzar para sustituirlos.")
        rub.escribir(tarea_md, criterios)
        print(f"Importados {len(criterios)} criterios de {origen.name} a TAREA.md. Revísalos.")

    criterios = rub.leer(tarea_md)
    if not criterios:
        sys.exit(
            "TAREA.md no tiene rúbrica todavía: rellena la tabla de la sección Rúbrica "
            "o usa --importar <rubrica.docx>."
        )
    total = sum(c.puntaje or 0 for c in criterios)
    ancho = max(len(c.id) for c in criterios)
    for c in criterios:
        pct = f"{100 * c.puntaje / total:4.0f} %" if total and c.puntaje is not None else "     "
        tipo = " (transversal)" if c.transversal else " (referencias)" if c.de_referencias else ""
        print(f"  {c.id:<{ancho}}  {comp.formato_puntaje(c):>9}  {pct}  {c.texto}{tipo}")
    print(
        f"  Total: {rub.formatear_puntaje(total)} pts"
        if total
        else "  Sin puntajes: el reparto de extensión será a partes iguales."
    )
    if any(re.fullmatch(r"C\d+", c.id) is None for c in criterios):
        print("  (IDs propios: úsalos tal cual en criterios=\"...\")")


def cmd_esqueleto(
    args, carpeta_tarea_fn: Callable[[str], Path], ruta_relativa_fn: Callable[[Path], str]
) -> None:
    """Escribe en generar_documento.py el esqueleto estructurado por criterio."""
    carpeta = carpeta_tarea_fn(args.tarea)
    tarea = ficha.leer_tarea(carpeta)
    criterios = rub.leer(tarea.ruta)
    if not criterios:
        sys.exit("TAREA.md no tiene rúbrica: sin ella no hay esqueleto que generar.")
    script = carpeta / "generar_documento.py"
    if not script.exists():
        sys.exit("No existe generar_documento.py en la tarea.")
    if "| ID |" not in tarea.ruta.read_text(encoding="utf-8"):
        rub.escribir(tarea.ruta, criterios)
    try:
        esq.aplicar(
            script,
            criterios,
            getattr(args, "palabras", None) or tarea.extension,
            forzar=getattr(args, "forzar", False),
        )
    except (ValueError, FileExistsError) as e:
        sys.exit(str(e))
    total = getattr(args, "palabras", None) or tarea.extension or esq.PALABRAS_POR_DEFECTO
    print(
        f"Esqueleto escrito en {ruta_relativa_fn(script)}: {len(criterios)} criterios, "
        f"~{total} palabras en total."
    )
    print("  Cada sección lleva un comentario con su criterio, peso y extensión orientativa.")


def cmd_generar(
    args,
    carpeta_tarea_fn: Callable[[str], Path],
    python_del_repo_fn: Callable[[], str],
    ruta_relativa_fn: Callable[[Path], str],
    convertir_pdf_fn: Callable[[list, Optional[Path]], int],
    raiz: Path,
) -> None:
    """Ejecuta generar_documento.py o compila documento.md, audita el Word y exporta a PDF."""
    carpeta = carpeta_tarea_fn(args.tarea)
    script = carpeta / "generar_documento.py"
    doc_md = carpeta / "documento.md"
    usar_md = bool(getattr(args, "desde_md", False)) or (doc_md.exists() and not script.exists())

    if usar_md:
        if not doc_md.exists():
            sys.exit(f"No existe {ruta_relativa_fn(doc_md)}")
        try:
            markdown_docx.compilar_markdown(
                doc_md,
                tema=getattr(args, "tema", None),
                estilo_citas=getattr(args, "citas", None),
                tarea=carpeta,
            )
        except (FileNotFoundError, ValueError, KeyError) as exc:
            sys.exit(f"Error al compilar {ruta_relativa_fn(doc_md)}: {exc}")
    else:
        if not script.exists():
            sys.exit(f"No existe {ruta_relativa_fn(script)} ni {ruta_relativa_fn(doc_md)}")
        r = subprocess.run([python_del_repo_fn(), str(script)], cwd=raiz, env=plataforma.entorno_utf8())
        if r.returncode != 0:
            sys.exit(f"generar_documento.py terminó con error ({r.returncode}).")
    print()
    inf = comp.comprobar(carpeta)
    if inf.coberturas:
        comp.actualizar_tarea(carpeta, inf)
    comp.imprimir(inf, carpeta)
    fallo_pdf = False
    if not getattr(args, "sin_pdf", False) and inf.docx:
        print()
        fallo_pdf = convertir_pdf_fn([inf.docx], raiz) > 0
    sys.exit(0 if inf.ok and not fallo_pdf else 1)


def cmd_compilar(
    args,
    ruta_relativa_fn: Callable[[Path], str],
    convertir_pdf_fn: Callable[[list, Optional[Path]], int],
    raiz: Path,
) -> None:
    """Compila un archivo Markdown con frontmatter YAML a .docx y opcionalmente .pdf."""
    origen = Path(args.archivo).resolve()
    if not origen.is_file():
        sys.exit(f"No existe el archivo Markdown: {args.archivo}")
    try:
        docx_generado = markdown_docx.compilar_markdown(
            origen,
            salida=getattr(args, "salida", None),
            tema=getattr(args, "tema", None),
            estilo_citas=getattr(args, "citas", None),
        )
    except (FileNotFoundError, ValueError, KeyError) as exc:
        sys.exit(f"Error al compilar {origen.name}: {exc}")

    ok = True
    if (origen.parent / "TAREA.md").is_file():
        print()
        inf = comp.comprobar(origen.parent, docx=docx_generado)
        if inf.coberturas:
            comp.actualizar_tarea(origen.parent, inf)
        comp.imprimir(inf, origen.parent)
        ok = inf.ok

    fallo_pdf = False
    if not getattr(args, "sin_pdf", False):
        print()
        fallo_pdf = convertir_pdf_fn([docx_generado], raiz) > 0
    else:
        print(f"DOCX compilado: {ruta_relativa_fn(docx_generado)}")

    sys.exit(0 if ok and not fallo_pdf else 1)


def cmd_comprobar(
    args,
    carpeta_tarea_fn: Callable[[str], Path],
    materias_dir: Path,
) -> None:
    """Verifica el archivo Word generado frente a la rúbrica."""
    if getattr(args, "todas", False) or getattr(args, "tarea", None) in ("todas", "todo", "--todas"):
        cmd_auditar(args, materias_dir)
        return
    carpeta = carpeta_tarea_fn(args.tarea)
    inf = comp.comprobar(carpeta, getattr(args, "docx", None))
    if getattr(args, "actualizar", False) and inf.coberturas:
        comp.actualizar_tarea(carpeta, inf)
    comp.imprimir(inf, carpeta)
    if getattr(args, "actualizar", False) and inf.coberturas:
        print("  TAREA.md: columna «Dónde se cumple» actualizada.")
    sys.exit(0 if inf.ok else 1)


def cmd_auditar(args, materias_dir: Path) -> None:
    """Audita recursivamente todas las tareas académicas del repositorio."""
    solo_materia = getattr(args, "materia", None)
    resultados = comp.auditar_todo(materias_dir, solo_materia)
    if getattr(args, "actualizar", False):
        for carpeta, inf in resultados:
            if inf.coberturas:
                comp.actualizar_tarea(carpeta, inf)
        print("  Columnas «Dónde se cumple» actualizadas en cada TAREA.md.\n")
    ok = comp.imprimir_auditoria_global(resultados)
    sys.exit(0 if ok else 1)
