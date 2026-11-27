#!/usr/bin/env python3
"""rubric-driven: materias, tareas, rúbricas, comprobación y PDF.

Uso (desde la raíz del repositorio):
    python plantillas/tareas.py verificar
    python plantillas/tareas.py materia <carpeta> "<Nombre de la materia>"
    python plantillas/tareas.py tarea <materia> <codigo> "<Título>" [--tipo T]
    python plantillas/tareas.py rubrica <tarea> [--importar archivo.docx]
    python plantillas/tareas.py esqueleto <tarea> [--palabras N] [--forzar]
    python plantillas/tareas.py generar <tarea> [--desde-md] [--sin-pdf]
    python plantillas/tareas.py compilar <archivo.md> [--salida DOCX] [--tema TEMA] [--citas ESTILO] [--sin-pdf]
    python plantillas/tareas.py comprobar <tarea> [--actualizar] [--verificar-citas]
    python plantillas/tareas.py verificar-citas <archivo.docx | tarea> [--estricto]
    python plantillas/tareas.py auditar [<materia>] [--actualizar]
    python plantillas/tareas.py pdf <archivo.docx | carpeta>
    python plantillas/tareas.py estado [<materia>]
    python plantillas/tareas.py marcar <tarea> <pendiente|lista|entregada>
    python plantillas/tareas.py temas [--crear NOMBRE] [--extraer ARCHIVO.DOCX] [--preview TEMA|todos] [--base PRESET] [--local]
    python plantillas/tareas.py estilos [--catalogo] [--tema TEMA] [--salida RUTA] [--sin-pdf]

Ejemplos:
    python plantillas/tareas.py materia programacion-web-2 "Programación Web 2"
    python plantillas/tareas.py tarea sgbd1 A15 "Procedimientos almacenados"
    python plantillas/tareas.py rubrica materias/sgbd1/A15_Procedimientos_Almacenados \\
        --importar enunciado/rubrica.docx
    python plantillas/tareas.py esqueleto materias/sgbd1/A15_Procedimientos_Almacenados
    python plantillas/tareas.py generar materias/sgbd1/A15_Procedimientos_Almacenados

Las materias se crean siempre dentro de materias/; <materia> es solo el nombre
de su carpeta (sgbd1), no la ruta. <tarea> es la ruta a la carpeta de la tarea.
"""
import argparse
import re
import subprocess
import sys
import unicodedata
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import plataforma
    from cli import comandos_documentales as doc_cmds
    from cli import comandos_gestion as gestion_cmds
    from cli import comandos_temas as temas_cmds
    from cli import servicio_pdf, tablas
    from config import RAIZ
else:
    from . import plataforma
    from .cli import comandos_documentales as doc_cmds
    from .cli import comandos_gestion as gestion_cmds
    from .cli import comandos_temas as temas_cmds
    from .cli import servicio_pdf, tablas
    from .config import RAIZ

PLANTILLAS = RAIZ / "plantillas"
MATERIAS = RAIZ / "materias"
TIPOS = {
    "actividad": "Actividad (A)",
    "practica": "Práctico-experimental (P)",
    "evaluacion": "Evaluación (E)",
    "otro": "Otro",
}
ESTADOS = ("pendiente", "lista", "entregada")

# Re-exportaciones de compatibilidad
LO_TMP = servicio_pdf.LO_TMP
LO_PERFIL = servicio_pdf.LO_PERFIL
LO_LIMITE_BYTES = servicio_pdf.LO_LIMITE_BYTES
LO_TIMEOUT = servicio_pdf.LO_TIMEOUT


def slug_titulo(titulo: str) -> str:
    """'Procedimientos almacenados' -> 'Procedimientos_Almacenados' (sin tildes)."""
    sin_tildes = unicodedata.normalize("NFKD", titulo).encode("ascii", "ignore").decode()
    palabras = re.findall(r"[A-Za-z0-9]+", sin_tildes)
    return "_".join(p[:1].upper() + p[1:] for p in palabras)


def tipo_por_codigo(codigo: str) -> str:
    return {"A": "actividad", "P": "practica", "E": "evaluacion"}.get(codigo[:1].upper(), "otro")


def rellenar(plantilla: Path, **valores) -> str:
    texto = plantilla.read_text(encoding="utf-8")
    for clave, valor in valores.items():
        texto = texto.replace("{" + clave + "}", valor)
    return texto


def ruta_relativa(ruta: Path) -> str:
    ruta = Path(ruta).resolve()
    return ruta.relative_to(RAIZ).as_posix() if ruta.is_relative_to(RAIZ) else str(ruta)


def carpeta_tarea(texto: str) -> Path:
    """Admite la ruta completa o relativa a la raíz o a materias/."""
    for candidata in (Path(texto), RAIZ / texto, MATERIAS / texto):
        if (candidata / "TAREA.md").exists():
            return candidata.resolve()
    sys.exit(f"No encuentro la tarea '{texto}' (debe ser una carpeta con TAREA.md).")


def git(*args, check=True, capturar=False):
    return subprocess.run(
        ["git", *args],
        cwd=RAIZ,
        check=check,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=capturar,
    )


def python_del_repo() -> str:
    venv = plataforma.ruta_python_venv(RAIZ)
    return str(venv) if venv.exists() else sys.executable


# Delegaciones modulares del CLI
def cmd_verificar(args) -> None:
    gestion_cmds.cmd_verificar(args, RAIZ, git)


def cmd_materia(args) -> None:
    gestion_cmds.cmd_materia(args, MATERIAS, PLANTILLAS, rellenar)


def cmd_tarea(args) -> None:
    gestion_cmds.cmd_tarea(
        args, MATERIAS, PLANTILLAS, TIPOS, slug_titulo, tipo_por_codigo, rellenar, ruta_relativa
    )


def cmd_marcar(args) -> None:
    gestion_cmds.cmd_marcar(args, carpeta_tarea, ruta_relativa)


def cmd_rubrica(args) -> None:
    doc_cmds.cmd_rubrica(args, carpeta_tarea)


def cmd_esqueleto(args) -> None:
    doc_cmds.cmd_esqueleto(args, carpeta_tarea, ruta_relativa)


def cmd_generar(args) -> None:
    doc_cmds.cmd_generar(args, carpeta_tarea, python_del_repo, ruta_relativa, servicio_pdf.convertir_pdf, RAIZ)


def cmd_compilar(args) -> None:
    doc_cmds.cmd_compilar(args, ruta_relativa, servicio_pdf.convertir_pdf, RAIZ)


def cmd_comprobar(args) -> None:
    doc_cmds.cmd_comprobar(args, carpeta_tarea, MATERIAS, ruta_relativa)


def cmd_verificar_citas(args) -> None:
    doc_cmds.cmd_verificar_citas(args, carpeta_tarea, ruta_relativa)


def cmd_auditar(args) -> None:
    doc_cmds.cmd_auditar(args, MATERIAS)


def cmd_pdf(args) -> None:
    servicio_pdf.cmd_pdf(args, RAIZ)


def cmd_estado(args) -> None:
    tablas.cmd_estado(args, MATERIAS)


def cmd_temas(args) -> None:
    """Lista los temas documentales, crea un molde, extrae desde .docx o genera vista previa."""
    temas_cmds.cmd_temas(args, RAIZ, ruta_relativa)


def cmd_estilos(args) -> None:
    """Muestra todos los estilos elegibles por elemento o genera un muestrario visual (.docx/.pdf)."""
    temas_cmds.cmd_estilos(args, RAIZ, ruta_relativa)


def convertir_pdf(documentos: list) -> int:
    return servicio_pdf.convertir_pdf([Path(d) for d in documentos], RAIZ)


def main() -> None:
    plataforma.configurar_consola_utf8()
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="accion", required=True)

    sub.add_parser("verificar", help="comprueba .env, Python, LibreOffice y el repo público")

    p = sub.add_parser("materia", help="crea la carpeta de una materia")
    p.add_argument("carpeta", help="nombre en minúsculas con guiones, p. ej. programacion-web-2")
    p.add_argument("nombre", help="nombre completo de la materia")

    p = sub.add_parser("tarea", help="crea la carpeta de una tarea dentro de una materia")
    p.add_argument("materia", help="carpeta de la materia, p. ej. sgbd1")
    p.add_argument("codigo", help="código del docente: A15, P2, E1...")
    p.add_argument("titulo", help="título corto de la tarea")
    p.add_argument("--enunciado", "-e", default=None, help="ruta al archivo PDF o DOCX (p. ej. en ~/Descargas) para copiar a enunciado/")
    p.add_argument("--tipo", choices=TIPOS, help="se deduce de la letra del código si se omite")
    p.add_argument("--modalidad", choices=["individual", "grupal"], default="individual", help="modalidad de la tarea (por defecto individual)")
    p.add_argument("--grupal", action="store_true", help="atajo para configurar la tarea como modalidad grupal")
    p.add_argument("--grupo", default=None, help="nombre o número del grupo (p. ej. 'Grupo 1')")
    p.add_argument("--integrantes", default=None, help="lista de integrantes separados por comas")
    p.add_argument("--estudiante", default=None, help="nombre del estudiante (para modalidad individual)")
    p.add_argument("--formato", "--tema", dest="formato", default=None, help="preset oficial (apa7) o nombre/ruta de tema JSON en themes/ o themes/local/")

    p = sub.add_parser("rubrica", help="muestra la rúbrica de TAREA.md o la importa de un .docx")
    p.add_argument("tarea", help="carpeta de la tarea")
    p.add_argument("--importar", metavar="DOCX", help="rúbrica del docente en .docx")
    p.add_argument("--forzar", action="store_true", help="sustituye los criterios que ya haya")

    p = sub.add_parser("esqueleto", help="escribe en generar_documento.py una sección por criterio")
    p.add_argument("tarea", help="carpeta de la tarea")
    p.add_argument("--palabras", type=int, help="extensión total (por defecto la de TAREA.md o 1500)")
    p.add_argument("--forzar", action="store_true", help="reescribe secciones con texto (copia .bak)")

    p = sub.add_parser("generar", help="ejecuta generar_documento.py (o compila documento.md), comprueba y convierte a PDF")
    p.add_argument("tarea", help="carpeta de la tarea")
    p.add_argument("--desde-md", action="store_true", help="compila documento.md en lugar de ejecutar generar_documento.py")
    p.add_argument("--tema", default=None, help="sobrescribe el tema al compilar desde documento.md")
    p.add_argument("--citas", choices=["apa7", "ieee", "vancouver"], default=None, help="estilo de citación al compilar desde documento.md")
    p.add_argument("--verificar-citas", action="store_true", help="verifica en línea (Crossref/OpenAlex/OpenLibrary/HTTP) que las referencias existan")
    p.add_argument("--sin-pdf", action="store_true", help="no convierte a PDF")

    p = sub.add_parser("compilar", help="compila un archivo Markdown/YAML declarativo a .docx y .pdf")
    p.add_argument("archivo", help="ruta al archivo .md con frontmatter YAML")
    p.add_argument("--salida", "-o", default=None, help="ruta de salida del archivo .docx")
    p.add_argument("--tema", default=None, help="sobrescribe el tema declarado en el frontmatter")
    p.add_argument("--citas", choices=["apa7", "ieee", "vancouver"], default=None, help="sobrescribe el estilo de citación (apa7, ieee, vancouver)")
    p.add_argument("--verificar-citas", action="store_true", help="verifica en línea que DOIs, URLs y obras citadas sean reales")
    p.add_argument("--sin-pdf", action="store_true", help="genera únicamente el .docx sin convertir a PDF")

    p = sub.add_parser("comprobar", help="verifica el .docx contra la rúbrica")
    p.add_argument("tarea", nargs="?", default="todas", help="carpeta de la tarea (o 'todas')")
    p.add_argument("--todas", action="store_true", help="audita todas las tareas del repositorio")
    p.add_argument("--docx", help="documento a comprobar (por defecto, el más reciente)")
    p.add_argument("--actualizar", action="store_true",
                   help="rellena «Dónde se cumple» en TAREA.md")
    p.add_argument("--verificar-citas", action="store_true",
                   help="verifica en línea que DOIs, URLs y obras citadas existan realmente")

    p = sub.add_parser("verificar-citas", help="verifica en línea la autenticidad de las referencias de un .docx o tarea")
    p.add_argument("objetivo", help="ruta a un archivo .docx o carpeta de tarea")
    p.add_argument("--estricto", action="store_true", help="falla también si alguna referencia queda sin verificación automática")

    p = sub.add_parser("auditar", help="auditoría estática global de todas las tareas del repositorio")
    p.add_argument("materia", nargs="?", help="limita la auditoría solo a esta materia")
    p.add_argument("--actualizar", action="store_true",
                   help="rellena «Dónde se cumple» en cada TAREA.md")

    p = sub.add_parser("pdf", help="convierte .docx a .pdf con LibreOffice")
    p.add_argument("ruta", help="un archivo .docx o una carpeta (convierte todos sus .docx)")

    p = sub.add_parser("estado", help="tareas pendientes por fecha de entrega, con su cobertura")
    p.add_argument("materia", nargs="?", help="solo esta materia")
    p.add_argument("--todas", action="store_true", help="incluye las entregadas")

    p = sub.add_parser("marcar", help="cambia el estado en TAREA.md y en el README de la materia")
    p.add_argument("tarea", help="carpeta de la tarea")
    p.add_argument("estado", choices=ESTADOS)
    p.add_argument("--forzar", action="store_true", help="marca aunque la comprobación falle")

    p = sub.add_parser("temas", help="lista temas, crea un molde, extrae desde .docx o genera vista previa")
    p.add_argument("--crear", metavar="NOMBRE", default=None, help="crea un molde theme.json personalizable")
    p.add_argument("--extraer", metavar="DOCX", default=None, help="extrae automáticamente tipografía, márgenes, colores e imágenes desde un .docx")
    p.add_argument("--preview", metavar="TEMA", default=None, help="genera un documento de muestra (.docx/.pdf) para un tema o 'todos'")
    p.add_argument("--salida", "-o", default=None, help="ruta/carpeta de salida al usar --preview")
    p.add_argument("--citas", choices=["apa7", "ieee", "vancouver"], default=None, help="estilo de citación en la vista previa")
    p.add_argument("--sin-pdf", action="store_true", help="al usar --preview, genera solo .docx sin convertir a PDF")
    p.add_argument("--nombre", metavar="NOMBRE", default=None, help="nombre del tema al usar --extraer (por defecto el nombre del archivo)")
    p.add_argument("--base", default="apa7", help="preset base al crear un tema (defecto: apa7)")
    p.add_argument("--local", action="store_true", help="crea el tema en themes/local/ (ignorado por Git)")
    p.add_argument("--compartido", action="store_true", help="al usar --extraer, guarda en themes/ en lugar de themes/local/")

    p = sub.add_parser("estilos", help="lista todos los estilos elegibles o genera un catálogo visual comparativo")
    p.add_argument("--catalogo", "--visual", action="store_true", help="genera un documento (.docx/.pdf) comparando visualmente todos los estilos")
    p.add_argument("--tema", default="apa7", help="tema base del documento catálogo (defecto: apa7)")
    p.add_argument("--salida", "-o", default=None, help="ruta de salida del archivo .docx catálogo")
    p.add_argument("--sin-pdf", action="store_true", help="al usar --catalogo, genera solo .docx sin convertir a PDF")

    args = parser.parse_args()
    {
        "verificar": cmd_verificar,
        "materia": cmd_materia,
        "tarea": cmd_tarea,
        "rubrica": cmd_rubrica,
        "esqueleto": cmd_esqueleto,
        "generar": cmd_generar,
        "compilar": cmd_compilar,
        "comprobar": cmd_comprobar,
        "verificar-citas": cmd_verificar_citas,
        "auditar": cmd_auditar,
        "pdf": cmd_pdf,
        "estado": cmd_estado,
        "marcar": cmd_marcar,
        "temas": cmd_temas,
        "estilos": cmd_estilos,
    }[args.accion](args)


if __name__ == "__main__":
    main()
