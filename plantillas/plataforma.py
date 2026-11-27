# -*- coding: utf-8 -*-
"""Capa de abstracción multiplataforma (Linux, macOS y Windows).

Centraliza todas las operaciones dependientes del sistema operativo para evitar
lógica condicional dispersa: configuración UTF-8 de consola y subprocesos,
detección de LibreOffice, resolución de directorios de usuario (caché, temporal,
Descargas/Downloads), aislamiento y terminación de árboles de procesos, y
resolución de fuentes tipográficas del sistema.
"""
from __future__ import annotations

import os
import shutil
import signal
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Callable, Mapping, Optional


def es_windows() -> bool:
    """Indica si el intérprete se ejecuta sobre Windows."""
    return os.name == "nt"


def es_macos() -> bool:
    """Indica si el intérprete se ejecuta sobre macOS."""
    return sys.platform == "darwin"


def configurar_consola_utf8() -> None:
    """Garantiza salida UTF-8 en stdout/stderr para evitar UnicodeEncodeError en Windows.

    En consolas Windows (CMD/PowerShell con cp850/cp1252) o tuberías redirigidas,
    caracteres como '→', '—', '«', '»' o tildes pueden lanzar UnicodeEncodeError
    si no se reconfigura el stream a UTF-8.
    """
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            try:
                reconfigure(encoding="utf-8", errors="replace")
            except (OSError, ValueError):
                pass


def entorno_utf8(
    base: Optional[Mapping[str, str]] = None,
    **extra: str,
) -> dict[str, str]:
    """Construye un diccionario de variables de entorno forzando UTF-8 en subprocesos Python."""
    env = dict(os.environ if base is None else base)
    env["PYTHONUTF8"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    env.update(extra)
    return env


def ruta_python_venv(raiz: Path) -> Path:
    """Devuelve la ruta esperada del intérprete Python dentro de .venv."""
    if es_windows():
        return raiz / ".venv" / "Scripts" / "python.exe"
    return raiz / ".venv" / "bin" / "python"


def comando_python_venv_relativo() -> str:
    """Devuelve el comando relativo recomendado para invocar Python del .venv."""
    return r".venv\Scripts\python.exe" if es_windows() else ".venv/bin/python"


def comando_copiar_env() -> str:
    """Devuelve el comando de shell apropiado para copiar .env.example a .env."""
    return "copy .env.example .env" if es_windows() else "cp .env.example .env"


def rutas_equivalentes(a: Path, b: Path) -> bool:
    """Compara dos rutas de forma insensible a mayúsculas en Windows y exacta en POSIX."""
    return os.path.normcase(str(a.resolve())) == os.path.normcase(str(b.resolve()))


def nombre_proyecto() -> str:
    """Devuelve dinámicamente el nombre de la carpeta raíz del proyecto."""
    nombre = Path(__file__).resolve().parent.parent.name.strip()
    return nombre or "document_generator"


def directorio_cache_base() -> Path:
    """Devuelve el directorio base de caché de usuario según convenciones del SO."""
    if es_windows():
        local_app_data = os.environ.get("LOCALAPPDATA")
        if local_app_data:
            return Path(local_app_data) / nombre_proyecto()
    return Path.home() / ".cache"


def es_ruta_temporal(ruta: Path) -> bool:
    """Determina si una ruta reside dentro del directorio temporal del sistema."""
    try:
        resuelta = Path(ruta).resolve()
        tmp_sistema = Path(tempfile.gettempdir()).resolve()
        if resuelta.is_relative_to(tmp_sistema):
            return True
        if not es_windows():
            tmp_posix = Path("/tmp").resolve()
            if resuelta.is_relative_to(tmp_posix):
                return True
    except OSError:
        return False
    return False


def _descargas_windows_registro() -> Optional[Path]:
    """Consulta la carpeta conocida 'Downloads' en el Registro de Windows."""
    if sys.platform != "win32":
        return None
    try:
        import winreg

        subclave = r"Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders"
        guid_downloads = "{374DE290-123F-4565-9164-39C4925E467B}"
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, subclave) as key:
            valor, _ = winreg.QueryValueEx(key, guid_downloads)
        if isinstance(valor, str) and valor.strip():
            ruta = Path(os.path.expandvars(valor.strip()))
            if ruta.is_dir():
                return ruta
    except OSError:
        return None
    return None


def _descargas_xdg() -> Optional[Path]:
    """Lee XDG_DOWNLOAD_DIR desde ~/.config/user-dirs.dirs en escritorios Linux."""
    if es_windows() or es_macos():
        return None
    user_dirs = Path.home() / ".config" / "user-dirs.dirs"
    if not user_dirs.is_file():
        return None
    try:
        for linea in user_dirs.read_text(encoding="utf-8", errors="ignore").splitlines():
            linea = linea.strip()
            if linea.startswith("XDG_DOWNLOAD_DIR="):
                raw = linea.split("=", 1)[1].strip().strip('"').strip("'")
                raw = raw.replace("$HOME", str(Path.home()))
                candidata = Path(os.path.expandvars(raw))
                if candidata.is_dir():
                    return candidata
    except OSError:
        return None
    return None


def directorio_descargas() -> Optional[Path]:
    """Resuelve la carpeta de descargas del usuario en Windows, Linux y macOS."""
    home = Path.home()
    if es_windows():
        reg = _descargas_windows_registro()
        if reg is not None:
            return reg
        candidatas = [home / "Downloads", home / "Descargas"]
    else:
        xdg = _descargas_xdg()
        if xdg is not None:
            return xdg
        candidatas = [home / "Descargas", home / "Downloads"]

    for carpeta in candidatas:
        if carpeta.is_dir():
            return carpeta
    return None


def _rutas_libreoffice_estandar() -> list[Path]:
    """Lista las ubicaciones estándar de instalación de LibreOffice por sistema operativo."""
    if es_windows():
        program_files = [
            os.environ.get("ProgramFiles", r"C:\Program Files"),
            os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"),
        ]
        local_app = os.environ.get("LOCALAPPDATA")
        bases = [Path(p) / "LibreOffice" / "program" for p in program_files if p]
        if local_app:
            bases.append(Path(local_app) / "Programs" / "LibreOffice" / "program")
        rutas: list[Path] = []
        for base in bases:
            # En Windows soffice.com es el wrapper de consola oficial; soffice.exe es el binario GUI.
            rutas.append(base / "soffice.com")
            rutas.append(base / "soffice.exe")
        return rutas

    if es_macos():
        return [
            Path("/Applications/LibreOffice.app/Contents/MacOS/soffice"),
            Path.home() / "Applications/LibreOffice.app/Contents/MacOS/soffice",
        ]

    return [
        Path("/usr/bin/soffice"),
        Path("/usr/local/bin/soffice"),
        Path.home() / ".nix-profile/bin/soffice",
        Path("/snap/bin/libreoffice"),
    ]


def buscar_libreoffice() -> Optional[str]:
    """Localiza el binario de LibreOffice (SOFFICE_BIN -> PATH -> rutas estándar del SO)."""
    override = os.environ.get("SOFFICE_BIN", "").strip()
    if override:
        ruta_override = Path(override)
        if ruta_override.is_file():
            return str(ruta_override)

    nombres_path = ("soffice.com", "soffice", "libreoffice") if es_windows() else ("soffice", "libreoffice")
    for nombre in nombres_path:
        encontrado = shutil.which(nombre)
        if encontrado:
            return encontrado

    for candidata in _rutas_libreoffice_estandar():
        if candidata.is_file():
            return str(candidata)

    return None


def entorno_libreoffice(tmp_dir: Path) -> dict[str, str]:
    """Prepara las variables de entorno para aislar temporales de LibreOffice en cualquier SO."""
    tmp_str = str(tmp_dir)
    if es_windows():
        return entorno_utf8(TMPDIR=tmp_str, TEMP=tmp_str, TMP=tmp_str)
    return entorno_utf8(TMPDIR=tmp_str)


def kwargs_proceso_aislado(limitar_fn: Optional[Callable[[], None]] = None) -> dict[str, Any]:
    """Devuelve los kwargs de subprocess.Popen para aislar el proceso hijo según el SO."""
    if es_windows():
        flags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0) | getattr(
            subprocess, "CREATE_NO_WINDOW", 0
        )
        return {"creationflags": flags}
    return {
        "start_new_session": True,
        "preexec_fn": limitar_fn,
    }


def terminar_arbol_procesos(proc: subprocess.Popen[Any]) -> None:
    """Termina de forma segura un proceso y todo su árbol de hijos en POSIX y Windows."""
    if es_windows():
        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        try:
            subprocess.run(
                ["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=15,
                check=False,
                creationflags=flags,
            )
        except (OSError, subprocess.SubprocessError):
            pass
        try:
            proc.kill()
        except OSError:
            pass
        return

    if sys.platform != "win32" and hasattr(os, "killpg"):
        try:
            os.killpg(proc.pid, signal.SIGKILL)
            return
        except (ProcessLookupError, PermissionError, OSError):
            pass
    try:
        proc.kill()
    except OSError:
        pass


def resolver_fuente_monospace(
    fuente_explicita: Optional[Path] = None,
    fuente_incluida: Optional[Path] = None,
) -> Optional[Path]:
    """Resuelve una fuente tipográfica monoespaciada existente en Linux, macOS o Windows."""
    candidatas: list[Path] = []
    if fuente_explicita is not None:
        candidatas.append(Path(fuente_explicita))
    if fuente_incluida is not None:
        candidatas.append(Path(fuente_incluida))

    if es_windows():
        win_fonts = Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts"
        candidatas.extend([
            win_fonts / "consola.ttf",
            win_fonts / "CascadiaMono.ttf",
            win_fonts / "lucon.ttf",
            win_fonts / "cour.ttf",
        ])
    elif es_macos():
        candidatas.extend([
            Path("/System/Library/Fonts/Menlo.ttc"),
            Path("/System/Library/Fonts/Monaco.ttf"),
            Path("/Library/Fonts/Courier New.ttf"),
        ])
    else:
        candidatas.extend([
            Path("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"),
            Path("/usr/share/fonts/truetype/liberation/LiberationMono-Regular.ttf"),
            Path("/usr/share/fonts/TTF/DejaVuSansMono.ttf"),
        ])

    for ruta in candidatas:
        if ruta.is_file():
            return ruta
    return None


def resolver_fuente_sans(bold: bool = False) -> Optional[Path]:
    """Resuelve una fuente sans-serif existente en Linux, macOS o Windows."""
    candidatas: list[Path] = []
    if es_windows():
        win_fonts = Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts"
        candidatas.extend(
            [win_fonts / "arialbd.ttf", win_fonts / "segoeuib.ttf", win_fonts / "calibrib.ttf"]
            if bold
            else [win_fonts / "arial.ttf", win_fonts / "segoeui.ttf", win_fonts / "calibri.ttf"]
        )
    elif es_macos():
        candidatas.extend([
            Path("/System/Library/Fonts/Helvetica.ttc"),
            Path("/Library/Fonts/Arial Bold.ttf" if bold else "/Library/Fonts/Arial.ttf"),
        ])
    else:
        candidatas.extend(
            [
                Path("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"),
                Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
            ]
            if bold
            else [
                Path("/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"),
                Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
            ]
        )
    for ruta in candidatas:
        if ruta.is_file():
            return ruta
    return None
