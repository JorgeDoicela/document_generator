# -*- coding: utf-8 -*-
"""Sistema extensible de temas documentales (presets + temas JSON personalizados).

Permite generar cualquier tipo de documento (académico APA 7, informe institucional,
especificación técnica/RFC, informe ejecutivo, artículo estilo IEEE o identidad
propia de cualquier universidad/organización) sin hardcodear marcas en el código fuente.
"""
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

from docx.shared import RGBColor

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from config import RAIZ
else:
    from .config import RAIZ

DIR_TEMAS = RAIZ / "themes"
DIR_TEMAS_LOCALES = DIR_TEMAS / "local"

RGBTuple = Tuple[int, int, int]


@dataclass(frozen=True)
class TemaDocumental:
    """Definición completa de identidad tipográfica, márgenes y activos visuales."""

    nombre: str
    descripcion: str = ""
    fuente: str = "Arial"
    tamano_cuerpo: float = 11.0
    tamano_h1: float = 13.0
    tamano_h2: float = 11.5
    tamano_h3: float = 11.0
    interlineado: float = 1.15
    espacio_despues: float = 6.0
    sangria_primera_linea: bool = False
    h1_centrado: bool = False
    margen_sup: float = 0.85
    margen_inf: float = 0.85
    margen_izq: float = 1.0
    margen_der: float = 1.0
    color_primario: RGBTuple = (30, 58, 138)
    color_texto: RGBTuple = (20, 20, 20)
    color_secundario: RGBTuple = (100, 110, 125)
    estilo_tabla: str = "grid"
    encabezado_texto: str = ""
    pie_texto: str = ""
    logo_portada: Optional[str] = None
    banner_inferior: Optional[str] = None
    imagen_encabezado: Optional[str] = None
    directorio_base: Optional[str] = None

    def rgb_primario(self) -> RGBColor:
        return RGBColor(*self.color_primario)

    def rgb_texto(self) -> RGBColor:
        return RGBColor(*self.color_texto)

    def rgb_secundario(self) -> RGBColor:
        return RGBColor(*self.color_secundario)

    def resolver_activo(self, ruta_relativa: Optional[str]) -> Optional[Path]:
        """Resuelve una ruta de imagen relativa al directorio del tema o a la raíz del repo."""
        if not ruta_relativa:
            return None
        p = Path(ruta_relativa)
        if p.is_absolute():
            return p if p.exists() else None
        if self.directorio_base:
            cand = Path(self.directorio_base) / p
            if cand.exists():
                return cand
        cand_raiz = RAIZ / p
        return cand_raiz if cand_raiz.exists() else None


PRESETS: Dict[str, TemaDocumental] = {
    "apa7": TemaDocumental(
        nombre="apa7",
        descripcion="Norma APA 7.a edición (Times New Roman 12 pt, doble espacio, tablas 3 líneas).",
        fuente="Times New Roman",
        tamano_cuerpo=12.0,
        tamano_h1=12.0,
        tamano_h2=12.0,
        tamano_h3=12.0,
        interlineado=2.0,
        espacio_despues=0.0,
        sangria_primera_linea=True,
        h1_centrado=True,
        margen_sup=1.0,
        margen_inf=1.0,
        margen_izq=1.0,
        margen_der=1.0,
        color_primario=(0, 0, 0),
        color_texto=(0, 0, 0),
        color_secundario=(80, 80, 80),
        estilo_tabla="apa",
    ),
    "academico": TemaDocumental(
        nombre="academico",
        descripcion="Informe académico institucional moderno (Arial 11 pt, interlineado 1.15, tablas Grid).",
        fuente="Arial",
        tamano_cuerpo=11.0,
        tamano_h1=13.0,
        tamano_h2=11.5,
        tamano_h3=11.0,
        interlineado=1.15,
        espacio_despues=6.0,
        sangria_primera_linea=False,
        h1_centrado=False,
        margen_sup=0.85,
        margen_inf=0.85,
        margen_izq=1.0,
        margen_der=1.0,
        color_primario=(27, 54, 93),
        color_texto=(20, 20, 20),
        color_secundario=(105, 115, 125),
        estilo_tabla="grid",
    ),
    "tecnico": TemaDocumental(
        nombre="tecnico",
        descripcion="Informe técnico, laboratorio, arquitectura o RFC (Calibri 10.5 pt, limpio y compacto).",
        fuente="Calibri",
        tamano_cuerpo=10.5,
        tamano_h1=14.0,
        tamano_h2=12.0,
        tamano_h3=11.0,
        interlineado=1.15,
        espacio_despues=5.0,
        sangria_primera_linea=False,
        h1_centrado=False,
        margen_sup=0.8,
        margen_inf=0.8,
        margen_izq=0.9,
        margen_der=0.9,
        color_primario=(15, 76, 129),
        color_texto=(25, 28, 32),
        color_secundario=(95, 105, 118),
        estilo_tabla="grid",
    ),
    "ejecutivo": TemaDocumental(
        nombre="ejecutivo",
        descripcion="Informe ejecutivo, propuesta comercial o memoria corporativa (Georgia/Arial sobrio).",
        fuente="Arial",
        tamano_cuerpo=10.5,
        tamano_h1=14.5,
        tamano_h2=12.0,
        tamano_h3=10.5,
        interlineado=1.2,
        espacio_despues=6.0,
        sangria_primera_linea=False,
        h1_centrado=False,
        margen_sup=0.9,
        margen_inf=0.9,
        margen_izq=1.0,
        margen_der=1.0,
        color_primario=(31, 41, 55),
        color_texto=(20, 20, 20),
        color_secundario=(107, 114, 128),
        estilo_tabla="apa",
    ),
    "ieee": TemaDocumental(
        nombre="ieee",
        descripcion="Artículo técnico-científico estilo IEEE (Times New Roman 10.5 pt, compacto).",
        fuente="Times New Roman",
        tamano_cuerpo=10.5,
        tamano_h1=11.5,
        tamano_h2=10.5,
        tamano_h3=10.5,
        interlineado=1.08,
        espacio_despues=4.0,
        sangria_primera_linea=True,
        h1_centrado=True,
        margen_sup=0.75,
        margen_inf=0.75,
        margen_izq=0.75,
        margen_der=0.75,
        color_primario=(0, 0, 0),
        color_texto=(0, 0, 0),
        color_secundario=(90, 90, 90),
        estilo_tabla="apa",
    ),
}


def _normalizar_rgb(valor: Union[List[int], Tuple[int, int, int], str]) -> RGBTuple:
    if isinstance(valor, str):
        hex_str = valor.lstrip("#").strip()
        if len(hex_str) == 6:
            return (int(hex_str[0:2], 16), int(hex_str[2:4], 16), int(hex_str[4:6], 16))
        raise ValueError(f"Color hex no válido: {valor!r}")
    if len(valor) != 3:
        raise ValueError(f"Color RGB debe tener 3 componentes: {valor!r}")
    return (int(valor[0]), int(valor[1]), int(valor[2]))


def _cargar_desde_json(ruta_json: Path) -> TemaDocumental:
    datos = json.loads(ruta_json.read_text(encoding="utf-8"))
    base_nombre = str(datos.pop("hereda", "academico")).lower()
    base = PRESETS.get(base_nombre, PRESETS["academico"])
    campos = asdict(base)
    campos["directorio_base"] = str(ruta_json.parent.resolve())

    for k, v in datos.items():
        if k not in campos:
            continue
        if k.startswith("color_"):
            campos[k] = _normalizar_rgb(v)
        else:
            campos[k] = v

    if not campos.get("nombre"):
        campos["nombre"] = ruta_json.parent.name
    return TemaDocumental(**campos)


def cargar_tema(nombre_o_ruta: Union[str, Path, TemaDocumental] = "academico") -> TemaDocumental:
    """Resuelve un tema desde presets integrados, ruta JSON directa o carpetas themes/ y themes/local/."""
    if isinstance(nombre_o_ruta, TemaDocumental):
        return nombre_o_ruta

    clave = str(nombre_o_ruta).strip()
    if clave.lower() in PRESETS:
        return PRESETS[clave.lower()]

    ruta = Path(clave)
    candidatos = [
        ruta,
        ruta / "theme.json" if ruta.is_dir() else ruta,
        DIR_TEMAS / clave / "theme.json",
        DIR_TEMAS_LOCALES / clave / "theme.json",
    ]
    for cand in candidatos:
        if cand.is_file() and cand.suffix.lower() == ".json":
            return _cargar_desde_json(cand)

    disponibles = ", ".join(listar_temas())
    raise ValueError(f"Tema documental no encontrado: {clave!r}. Disponibles: {disponibles}")


def listar_temas() -> List[str]:
    """Lista los presets integrados y los temas JSON detectados en themes/ y themes/local/."""
    encontrados = set(PRESETS.keys())
    for base in (DIR_TEMAS, DIR_TEMAS_LOCALES):
        if base.is_dir():
            for sub in base.iterdir():
                if sub.is_dir() and (sub / "theme.json").is_file():
                    encontrados.add(sub.name)
    return sorted(encontrados)


def _rgb_a_hex(rgb: RGBTuple) -> str:
    return f"#{rgb[0]:02X}{rgb[1]:02X}{rgb[2]:02X}"


def exportar_molde_tema(destino: Path, nombre: str, base: str = "academico") -> Path:
    """Crea un archivo theme.json listo para personalizar por cualquier usuario u organización."""
    preset = PRESETS.get(base.lower(), PRESETS["academico"])
    destino.mkdir(parents=True, exist_ok=True)
    archivo = destino / "theme.json"
    plantilla = {
        "nombre": nombre,
        "hereda": preset.nombre,
        "descripcion": f"Tema personalizado {nombre}",
        "fuente": preset.fuente,
        "tamano_cuerpo": preset.tamano_cuerpo,
        "interlineado": preset.interlineado,
        "color_primario": _rgb_a_hex(preset.color_primario),
        "color_texto": _rgb_a_hex(preset.color_texto),
        "color_secundario": _rgb_a_hex(preset.color_secundario),
        "estilo_tabla": preset.estilo_tabla,
        "encabezado_texto": preset.encabezado_texto,
        "pie_texto": preset.pie_texto,
        "logo_portada": preset.logo_portada,
        "banner_inferior": preset.banner_inferior,
        "imagen_encabezado": preset.imagen_encabezado,
    }
    archivo.write_text(json.dumps(plantilla, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return archivo
