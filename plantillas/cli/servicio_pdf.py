# -*- coding: utf-8 -*-
"""Servicio de conversión documental DOCX a PDF mediante LibreOffice headless.

Implementa aislamiento de procesos, grupo de sesión independiente y límites
de cuota de escritura en disco para prevenir cuelgues o consumo excesivo de memoria.
"""
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import List, Optional

_PLANTILLAS_DIR = str(Path(__file__).resolve().parent.parent)
if _PLANTILLAS_DIR not in sys.path:
    sys.path.insert(0, _PLANTILLAS_DIR)

if __package__ and "." in __package__:
    from .. import config, plataforma
else:
    import config  # type: ignore[no-redef]
    import plataforma  # type: ignore[no-redef]

# Directorios temporales aislados en disco
_CACHE_BASE = plataforma.directorio_cache_base()
LO_TMP = _CACHE_BASE / "lo-tmp"
LO_PERFIL = _CACHE_BASE / "lo-perfil"
LO_LIMITE_BYTES = 2 * 1024**3
LO_TIMEOUT = 300

# Re-exportación para consumidores externos y tests
buscar_libreoffice = plataforma.buscar_libreoffice


def _limitar_escritura() -> None:
    """Restringe el tamaño máximo de archivo que el proceso hijo puede escribir (POSIX)."""
    if sys.platform == "win32":
        return
    import resource

    resource.setrlimit(resource.RLIMIT_FSIZE, (LO_LIMITE_BYTES, LO_LIMITE_BYTES))


def _ruta_relativa(ruta: Path, raiz: Optional[Path] = None) -> str:
    ruta_res = Path(ruta).resolve()
    if raiz is not None:
        raiz_res = Path(raiz).resolve()
        if ruta_res.is_relative_to(raiz_res):
            return ruta_res.relative_to(raiz_res).as_posix()
    return str(ruta_res)


def convertir_pdf(documentos: List[Path], raiz: Optional[Path] = None) -> int:
    """Convierte cada archivo .docx a .pdf junto a él. Devuelve el número de fallos."""
    soffice = buscar_libreoffice()
    if not soffice:
        print("LibreOffice no está instalado: instálalo o exporta el PDF a mano desde Word.")
        return len(documentos)

    LO_TMP.mkdir(parents=True, exist_ok=True)
    LO_PERFIL.mkdir(parents=True, exist_ok=True)
    entorno = plataforma.entorno_libreoffice(LO_TMP)
    perfil_uri = LO_PERFIL.resolve().as_uri()
    fallos = 0

    for docx in documentos:
        docx = Path(docx).resolve()
        comando = [
            soffice,
            f"-env:UserInstallation={perfil_uri}",
            "--headless",
            "--convert-to",
            "pdf",
            "--outdir",
            str(docx.parent),
            str(docx),
        ]
        # Proceso en su propio grupo/árbol: si se cuelga se termina solo ese árbol
        proc = subprocess.Popen(
            comando,
            env=entorno,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            **plataforma.kwargs_proceso_aislado(_limitar_escritura),
        )
        try:
            salida, error = proc.communicate(timeout=LO_TIMEOUT)
        except subprocess.TimeoutExpired:
            plataforma.terminar_arbol_procesos(proc)
            proc.communicate()
            print(
                f"Error: {docx.name} tardó más de {LO_TIMEOUT} s; el .docx probablemente está mal "
                "formado (p. ej. dos tablas seguidas sin párrafo entre medias)."
            )
            fallos += 1
            continue

        pdf = docx.with_suffix(".pdf")
        if proc.returncode == 0 and pdf.exists() and pdf.stat().st_mtime >= docx.stat().st_mtime:
            print(f"PDF generado: {_ruta_relativa(pdf, raiz)}")
            # Copia de conveniencia a la carpeta Descargas/Downloads solo para tareas reales (nunca en tests)
            en_test = (
                "unittest" in sys.modules
                or bool(os.environ.get("PYTEST_CURRENT_TEST"))
                or plataforma.es_ruta_temporal(docx)
            )
            es_materia_real = (
                docx.is_relative_to((raiz / "materias").resolve())
                if raiz is not None
                else "materias" in docx.parts
            )
            if not en_test and es_materia_real and config.copiar_pdf_descargas_activo():
                descargas = plataforma.directorio_descargas()
                if descargas is not None and descargas.is_dir():
                    try:
                        destino_descargas = descargas / pdf.name

                        # Limpiar en Descargas archivos .docx o variantes con diferente mayúscula/minúscula
                        for f_antigua in descargas.iterdir():
                            if f_antigua.is_file():
                                if (
                                    f_antigua.name.lower() == pdf.name.lower()
                                    and f_antigua.name != pdf.name
                                ):
                                    f_antigua.unlink(missing_ok=True)
                                elif f_antigua.name.lower() == pdf.stem.lower() + ".docx":
                                    f_antigua.unlink(missing_ok=True)

                        shutil.copy2(pdf, destino_descargas)

                        home = Path.home().resolve()
                        destino_res = destino_descargas.resolve()
                        if destino_res.is_relative_to(home):
                            rel_dest = destino_res.relative_to(home).as_posix()
                            print(f"  [entrega] Listo para subir en: ~/{rel_dest}")
                        else:
                            print(f"  [entrega] Listo para subir en: {destino_res}")
                    except OSError:
                        pass
        else:
            print(f"Error al convertir {docx.name}:\n{(error or salida).strip()}")
            fallos += 1

    return fallos


def cmd_pdf(args, raiz: Optional[Path] = None) -> None:
    """Despachador del subcomando pdf."""
    objetivo = Path(args.ruta).resolve()
    if objetivo.is_dir():
        documentos = sorted(p for p in objetivo.glob("*.docx") if not p.name.startswith("~$"))
    elif objetivo.suffix.lower() == ".docx" and objetivo.exists():
        documentos = [objetivo]
    else:
        sys.exit(f"No es un .docx ni una carpeta: {args.ruta}")

    if not documentos:
        sys.exit(f"No hay archivos .docx en {args.ruta}")

    sys.exit(1 if convertir_pdf(documentos, raiz) else 0)
