# -*- coding: utf-8 -*-
"""Comandos de visualización tabular del estado de tareas académicas."""
import datetime
import sys
from pathlib import Path
from typing import List, Optional, Tuple

_PLANTILLAS_DIR = str(Path(__file__).resolve().parent.parent)
if _PLANTILLAS_DIR not in sys.path:
    sys.path.insert(0, _PLANTILLAS_DIR)

if __package__ and "." in __package__:
    from .. import comprobar as comp
    from .. import ficha
    from .. import rubrica as rub
else:
    import comprobar as comp  # type: ignore[no-redef]
    import ficha  # type: ignore[no-redef]
    import rubrica as rub  # type: ignore[no-redef]



def cmd_estado(args, materias_dir: Path) -> None:
    """Muestra la tabla de tareas ordenadas por fecha de entrega con su estado de rúbrica."""
    if not materias_dir.is_dir():
        sys.exit("Todavía no hay materias (tareas.py materia <carpeta> \"Nombre\").")

    materias = (
        [materias_dir / args.materia]
        if getattr(args, "materia", None)
        else sorted(p for p in materias_dir.iterdir() if p.is_dir())
    )
    filas: List[Tuple[datetime.date, str, str, str, Optional[int], str]] = []
    hoy = datetime.date.today()

    for m in materias:
        if not m.is_dir():
            continue
        for carpeta in sorted(p for p in m.iterdir() if (p / "TAREA.md").exists()):
            t = ficha.leer_tarea(carpeta)
            if t.estado == "entregada" and not getattr(args, "todas", False):
                continue
            criterios = rub.leer(t.ruta)
            if not criterios:
                cobertura = "sin rúbrica"
            elif comp.buscar_docx(carpeta) is None:
                cobertura = f"{len(criterios)} criterios, sin .docx"
            else:
                inf = comp.comprobar(carpeta)
                cubiertos = sum(1 for c in inf.coberturas if c.cubierto)
                problemas = len(inf.errores)
                cobertura = f"{cubiertos}/{len(criterios)} cubiertos"
                cobertura += f", {problemas} error{'es' if problemas != 1 else ''}" if problemas else ""

            dias = (t.fecha - hoy).days if t.fecha else None
            filas.append((t.fecha or datetime.date.max, m.name, t.base, t.estado, dias, cobertura))

    if not filas:
        print("No hay tareas pendientes." if not getattr(args, "todas", False) else "No hay tareas.")
        return

    filas.sort()
    print(f"{'Entrega':<10}  {'Días':>5}  {'Estado':<9}  {'Materia':<14}  {'Tarea':<36}  Rúbrica")
    for fecha, materia, base, estado, dias, cobertura in filas:
        f = fecha.isoformat() if fecha != datetime.date.max else "—"
        d = "—" if dias is None else ("hoy" if dias == 0 else f"{dias:+d}")
        print(f"{f:<10}  {d:>5}  {estado:<9}  {materia[:14]:<14}  {base[:36]:<36}  {cobertura}")
