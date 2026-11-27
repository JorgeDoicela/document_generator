# -*- coding: utf-8 -*-
"""Comandos de gestión administrativa: verificar, materia, tarea y marcar."""
import importlib.util
import shutil
import sys
from pathlib import Path
from typing import Callable, Dict

_PLANTILLAS_DIR = str(Path(__file__).resolve().parent.parent)
if _PLANTILLAS_DIR not in sys.path:
    sys.path.insert(0, _PLANTILLAS_DIR)

if __package__ and "." in __package__:
    from .. import comprobar as comp
    from .. import ficha, plataforma
    from ..config import ConfigError, cargar, cargar_o_salir
else:
    import comprobar as comp  # type: ignore[no-redef]
    import ficha  # type: ignore[no-redef]
    import plataforma  # type: ignore[no-redef]
    from config import ConfigError, cargar, cargar_o_salir  # type: ignore[no-redef]



def cmd_verificar(_args, raiz: Path, git_fn: Callable) -> None:
    """Comprueba .env, Python, LibreOffice y el repositorio git."""
    ok = True

    def informe(bien: bool, texto: str) -> None:
        nonlocal ok
        ok &= bien
        print(("  [ok]    " if bien else "  [falta] ") + texto)

    print("Configuración")
    try:
        cfg = cargar()
        informe(True, f".env cargado ({cfg['NOMBRE_ESTUDIANTE']})")
    except ConfigError as e:
        informe(False, str(e).replace("\n", "\n          "))

    print("Python")
    en_venv = plataforma.rutas_equivalentes(Path(sys.prefix), raiz / ".venv")
    informe(
        en_venv,
        "ejecutando con .venv de la raíz"
        if en_venv
        else f"no se está usando .venv (usa {plataforma.comando_python_venv_relativo()}); intérprete: {sys.executable}",
    )
    for modulo, paquete in (
        ("docx", "python-docx"),
        ("PIL", "Pillow"),
        ("lxml", "lxml"),
        ("pypdf", "pypdf"),
    ):
        informe(importlib.util.find_spec(modulo) is not None, f"{paquete} instalado")

    print("LibreOffice")
    soffice = plataforma.buscar_libreoffice()
    informe(bool(soffice), soffice or "no instalado: sin él no se generan los PDF")

    print("Control de versiones (git)")
    try:
        r = git_fn("ls-files", check=False, capturar=True)
    except FileNotFoundError:
        print("  [--]    git no está instalado; no se comprueba")
    else:
        if r.returncode != 0:
            print("  [--]    no es un repositorio git; no se comprueba")
        else:
            archivos = [f.strip('"') for f in r.stdout.splitlines()]
            env_en_git = any(f == ".env" or f.endswith("/.env") for f in archivos)
            informe(
                not env_en_git,
                ".env protegido fuera de git"
                if not env_en_git
                else ".env está siendo rastreado en git (riesgo de seguridad)",
            )
            privados_en_git = [
                f
                for f in archivos
                if (f.startswith("materias/") and f != "materias/.gitkeep")
                or (f.startswith("themes/local/") and f != "themes/local/.gitkeep")
                or (f.startswith("themes/.previews/") and f != "themes/.previews/.gitkeep")
            ]
            informe(
                not privados_en_git,
                "workspace privado (materias/, themes/local/ y themes/.previews/) fuera de git"
                if not privados_en_git
                else f"{len(privados_en_git)} archivo(s) privado(s) rastreados en git (materias/, themes/local/ o themes/.previews/)",
            )
            r_hooks = git_fn("config", "--get", "core.hooksPath", check=False, capturar=True)
            hooks_path = (r_hooks.stdout or "").strip()
            if hooks_path == ".githooks":
                print("  [ok]    git hooks de seguridad activos (.githooks)")
            else:
                print("  [--]    git hooks no activados (ejecuta: git config core.hooksPath .githooks)")

    sys.exit(0 if ok else 1)


def cmd_materia(args, materias_dir: Path, plantillas_dir: Path, rellenar_fn: Callable) -> None:
    """Crea la carpeta y ficha de una nueva materia."""
    cargar_o_salir()
    if "/" in args.carpeta or "\\" in args.carpeta:
        sys.exit("Indica solo el nombre de la carpeta (p. ej. sgbd2); se crea dentro de materias/.")
    destino = materias_dir / args.carpeta
    if destino.exists():
        sys.exit(f"Ya existe: materias/{args.carpeta}/")
    destino.mkdir(parents=True)
    plantilla_materia = plantillas_dir / "materia" / "MATERIA.md"
    if not plantilla_materia.exists():
        plantilla_materia = plantillas_dir / "materia" / "README.md"
    (destino / "MATERIA.md").write_text(
        rellenar_fn(plantilla_materia, materia_nombre=args.nombre),
        encoding="utf-8",
    )
    print(f"Materia creada: materias/{args.carpeta}/")
    print("  Completa en su MATERIA.md el docente, la plataforma y las reglas de entrega.")



def cmd_tarea(
    args,
    materias_dir: Path,
    plantillas_dir: Path,
    tipos_dict: Dict[str, str],
    slug_fn: Callable[[str], str],
    tipo_codigo_fn: Callable[[str], str],
    rellenar_fn: Callable,
    ruta_relativa_fn: Callable[[Path], str],
) -> None:
    """Crea el directorio y scaffolding de una nueva tarea académica."""
    cfg = cargar_o_salir()
    nombre_carpeta = Path(args.materia).name
    carpeta_materia = materias_dir / nombre_carpeta
    if not carpeta_materia.is_dir():
        existentes = (
            ", ".join(sorted(p.name for p in materias_dir.iterdir() if p.is_dir()))
            if materias_dir.is_dir()
            else "ninguna"
        )
        sys.exit(
            f"No existe la materia '{nombre_carpeta}' en materias/ (hay: {existentes}).\n"
            f"  Créala con: tareas.py materia {nombre_carpeta} \"Nombre\""
        )

    codigo = args.codigo.upper()
    tipo = args.tipo or tipo_codigo_fn(codigo)
    base = f"{codigo}_{slug_fn(args.titulo)}"
    destino = carpeta_materia / base
    if destino.exists():
        sys.exit(f"Ya existe: {ruta_relativa_fn(destino)}")

    materia_nombre = ficha.leer_materia(carpeta_materia).nombre
    ruta_carpeta = ruta_relativa_fn(destino)
    destino.mkdir()
    (destino / "enunciado").mkdir()
    (destino / "capturas").mkdir()
    (destino / "insumos").mkdir()

    enunciado_origen = getattr(args, "enunciado", None)
    if enunciado_origen:
        origen = Path(enunciado_origen).expanduser().resolve()
        if origen.is_file():
            shutil.copy2(origen, destino / "enunciado" / origen.name)
            print(f"  Archivo de enunciado importado: enunciado/{origen.name}")
        else:
            print(f"  [aviso] El archivo de enunciado no existe: {enunciado_origen}")

    es_grupal = (
        getattr(args, "grupal", False)
        or getattr(args, "modalidad", "individual").lower() == "grupal"
        or bool(getattr(args, "grupo", None))
    )
    modalidad = "Grupal" if es_grupal else "Individual"
    if es_grupal:
        grupo_val = getattr(args, "grupo", None) or cfg.get("GRUPO_DEFECTO") or "<!-- Nombre o número de grupo -->"
        integrantes_val = (
            getattr(args, "integrantes", None)
            or cfg.get("INTEGRANTES_DEFECTO")
            or "<!-- Integrante 1, Integrante 2, ... -->"
        )
        lineas_equipo = f"- **Grupo:** {grupo_val}\n- **Integrantes:** {integrantes_val}\n"
    else:
        integrante_ind = (
            getattr(args, "estudiante", None)
            or getattr(args, "integrantes", None)
            or cfg.get("NOMBRE_ESTUDIANTE")
        )
        if integrante_ind:
            lineas_equipo = f"- **Estudiante:** {integrante_ind}\n"
        else:
            lineas_equipo = "- **Estudiante:** <!-- Nombre del estudiante -->\n"

    formato_val = (getattr(args, "formato", None) or "").strip() or "por defecto"
    (destino / "TAREA.md").write_text(
        rellenar_fn(
            plantillas_dir / "tarea" / "TAREA.md",
            codigo=codigo,
            titulo=args.titulo,
            materia_nombre=materia_nombre,
            tipo=tipos_dict[tipo],
            modalidad=modalidad,
            lineas_equipo=lineas_equipo,
            formato=formato_val,
        ),
        encoding="utf-8",
    )
    (destino / "generar_documento.py").write_text(
        rellenar_fn(
            plantillas_dir / "tarea" / "generar_documento.py",
            codigo=codigo,
            titulo=args.titulo,
            titulo_py=repr(args.titulo),
            materia_py=repr(materia_nombre),
            base=base,
            ruta_carpeta=ruta_carpeta,
        ),
        encoding="utf-8",
    )

    ficha_materia = ficha.ruta_ficha_materia(carpeta_materia)
    if ficha_materia.exists():
        texto = ficha_materia.read_text(encoding="utf-8")
        if "| Carpeta | Entrega | Estado |" in texto:
            fila = f"| `{base}` | {codigo} — {ficha.escapar_celda(args.titulo)} | pendiente |\n"
            ficha_materia.write_text(texto.rstrip("\n") + "\n" + fila, encoding="utf-8")

    print(f"Tarea creada: {ruta_carpeta}/")
    print("  1. Deja el enunciado y la RÚBRICA en enunciado/ (e insumos grupales o borradores en insumos/).")
    print(f"  2. Pasa la rúbrica a TAREA.md (tareas.py rubrica {ruta_carpeta} --importar <rubrica.docx>)")

    print("     y completa la fecha, la extensión y el formato.")
    print(f"  3. tareas.py esqueleto {ruta_carpeta}   → una sección por criterio")
    print(f"  4. Escribe el contenido y ejecuta: tareas.py generar {ruta_carpeta}")


def cmd_marcar(args, carpeta_tarea_fn: Callable[[str], Path], ruta_relativa_fn: Callable[[Path], str]) -> None:
    """Cambia el estado de una tarea y actualiza fichas."""
    carpeta = carpeta_tarea_fn(args.tarea)
    t = ficha.leer_tarea(carpeta)
    if args.estado in ("lista", "entregada") and not getattr(args, "forzar", False):
        inf = comp.comprobar(carpeta)
        if not inf.ok:
            comp.imprimir(inf, carpeta)
            sys.exit(
                f"\nLa comprobación tiene errores; corrígelos o usa --forzar para marcarla "
                f"como {args.estado} igualmente."
            )
    for ruta in ficha.marcar_estado(t, args.estado):
        print(f"Actualizado: {ruta_relativa_fn(ruta)}")
