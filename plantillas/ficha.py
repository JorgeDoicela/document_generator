# -*- coding: utf-8 -*-
"""Lectura y escritura de las fichas en Markdown: TAREA.md y el README.md de
cada materia.

Las fichas son texto libre para personas, así que el análisis es tolerante:
los comentarios HTML (<!-- ... -->) cuentan como campos vacíos y los campos
que no aparecen se devuelven como None.
"""
import datetime
import re
from dataclasses import dataclass, field
from pathlib import Path

PALABRAS_POR_PAGINA = 275  # Times New Roman 12 a doble espacio, aproximado

_COMENTARIO = re.compile(r"<!--.*?-->", re.S)
_CAMPO = re.compile(r"^\s*-\s*\*\*(?P<campo>[^*]+?):\*\*\s*(?P<valor>.*)$")


def sin_comentarios(texto: str) -> str:
    return _COMENTARIO.sub("", texto).strip()


# --------------------------------------------------------------------------
# Markdown mínimo: secciones, campos y tablas
# --------------------------------------------------------------------------
def seccion(texto: str, nombre: str) -> tuple[int, int] | None:
    """Rango [inicio, fin) de las líneas bajo '## <nombre>' (sin el título)."""
    lineas = texto.splitlines()
    inicio = None
    for i, linea in enumerate(lineas):
        if re.match(r"^##\s+", linea):
            if inicio is not None:
                return inicio, i
            if linea[2:].strip().lower() == nombre.lower():
                inicio = i + 1
    return (inicio, len(lineas)) if inicio is not None else None


def campos(texto: str) -> dict:
    """Campos '- **Clave:** valor' → {'clave': 'valor'} (claves en minúsculas).

    Soporta valores en la misma línea y sub-viñetas o líneas indentadas
    subordinadas (p. ej. listas de integrantes).
    """
    valores = {}
    clave_actual = None
    lineas_acumuladas: list[str] = []

    for linea in texto.splitlines():
        m = _CAMPO.match(linea)
        if m:
            if clave_actual is not None:
                valores[clave_actual] = sin_comentarios("\n".join(lineas_acumuladas).strip())
            clave_actual = m["campo"].strip().lower()
            val = m["valor"].strip()
            lineas_acumuladas = [val] if val else []
        elif clave_actual is not None:
            stripped = linea.strip()
            if (linea.startswith((" ", "\t")) or stripped.startswith(("-", "*", "•"))) and not linea.startswith("#") and stripped:
                lineas_acumuladas.append(stripped)
            elif not stripped:
                continue
            else:
                valores[clave_actual] = sin_comentarios("\n".join(lineas_acumuladas).strip())
                clave_actual = None
                lineas_acumuladas = []

    if clave_actual is not None:
        valores[clave_actual] = sin_comentarios("\n".join(lineas_acumuladas).strip())

    return valores


def reemplazar_campo(texto: str, campo: str, valor: str) -> str:
    patron = re.compile(r"^(\s*-\s*\*\*" + re.escape(campo) + r":\*\*\s*).*$", re.M | re.I)
    if not patron.search(texto):
        raise KeyError(f"no hay un campo '{campo}'")
    return patron.sub(lambda m: m[1] + valor, texto, count=1)


def celdas(linea: str) -> list[str]:
    """'| a | b \\| c |' → ['a', 'b | c']."""
    interior = linea.strip()
    interior = interior[1:] if interior.startswith("|") else interior
    interior = interior[:-1] if interior.endswith("|") and not interior.endswith("\\|") else interior
    partes = re.split(r"(?<!\\)\|", interior)
    return [p.strip().replace("\\|", "|") for p in partes]


def es_separador(linea: str) -> bool:
    return bool(re.fullmatch(r"\s*\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)*\|?\s*", linea))


def tablas(lineas: list[str], desde: int = 0, hasta: int | None = None):
    """Devuelve las tablas como (inicio, fin, encabezados, filas)."""
    hasta = len(lineas) if hasta is None else hasta
    i = desde
    while i < hasta:
        if lineas[i].lstrip().startswith("|") and i + 1 < hasta and es_separador(lineas[i + 1]):
            inicio = i
            encabezados = celdas(lineas[i])
            filas = []
            i += 2
            while i < hasta and lineas[i].lstrip().startswith("|"):
                filas.append(celdas(lineas[i]))
                i += 1
            yield inicio, i, encabezados, filas
        else:
            i += 1


def escapar_celda(texto) -> str:
    return str(texto).replace("|", "\\|").replace("\n", " ")


# --------------------------------------------------------------------------
# Valores de los campos
# --------------------------------------------------------------------------
def leer_fecha(texto: str | None) -> datetime.date | None:
    """Acepta AAAA-MM-DD y DD/MM/AAAA."""
    if not texto:
        return None
    m = re.search(r"(\d{4})-(\d{1,2})-(\d{1,2})", texto)
    if m:
        a, mes, d = map(int, m.groups())
    else:
        m = re.search(r"(\d{1,2})/(\d{1,2})/(\d{4})", texto)
        if not m:
            return None
        d, mes, a = map(int, m.groups())
    try:
        return datetime.date(a, mes, d)
    except ValueError:
        return None


def leer_extension(texto: str | None) -> int | None:
    """'1500 palabras' → 1500; '4-6 páginas' → 5 × PALABRAS_POR_PAGINA."""
    if not texto:
        return None
    numeros = [int(n) for n in re.findall(r"\d+", texto.replace(".", ""))]
    if not numeros:
        return None
    media = sum(numeros) / len(numeros)
    if re.search(r"p[áa]g", texto, re.I):
        media *= PALABRAS_POR_PAGINA
    return int(round(media))


# --------------------------------------------------------------------------
# Fichas
# --------------------------------------------------------------------------
@dataclass
class Materia:
    carpeta: Path
    nombre: str
    docente: str | None = None
    formato: str | None = None


@dataclass
class Tarea:
    carpeta: Path
    codigo: str
    titulo: str
    materia: Materia
    estado: str = "pendiente"
    fecha: datetime.date | None = None
    extension: int | None = None
    formato: str | None = None
    campos: dict = field(default_factory=dict)
    modalidad: str = "individual"
    grupo: str | None = None
    integrantes: list[str] = field(default_factory=list)

    @property
    def es_grupal(self) -> bool:
        return (
            self.modalidad.lower() == "grupal"
            or bool(self.grupo)
            or len(self.integrantes) > 1
        )

    def resolver_integrantes(self, config_dict: dict | None = None) -> list[str]:
        """Devuelve los integrantes de la tarea, con fallback a .env o estudiante único."""
        if self.integrantes:
            return list(self.integrantes)
        if config_dict:
            if self.es_grupal and config_dict.get("INTEGRANTES_DEFECTO"):
                raw = config_dict["INTEGRANTES_DEFECTO"]
                return [i.strip() for i in raw.split(",") if i.strip()]
            if config_dict.get("NOMBRE_ESTUDIANTE"):
                return [config_dict["NOMBRE_ESTUDIANTE"]]
        return []

    @property
    def ruta(self) -> Path:
        return self.carpeta / "TAREA.md"

    @property
    def base(self) -> str:
        return self.carpeta.name


def ruta_ficha_materia(carpeta: Path) -> Path:
    """Localiza la ficha técnica de la materia (prioriza MATERIA.md, con fallback a README.md)."""
    materia_md = Path(carpeta) / "MATERIA.md"
    if materia_md.exists():
        return materia_md
    readme_md = Path(carpeta) / "README.md"
    if readme_md.exists():
        return readme_md
    return materia_md


def leer_materia(carpeta: Path) -> Materia:
    carpeta = Path(carpeta)
    ficha = ruta_ficha_materia(carpeta)
    if not ficha.exists():
        return Materia(carpeta, carpeta.name)
    texto = ficha.read_text(encoding="utf-8")
    nombre = next((linea[2:].strip() for linea in texto.splitlines() if linea.startswith("# ")), carpeta.name)
    datos = {}
    for _, _, _, filas in tablas(texto.splitlines()):
        for fila in filas:
            if len(fila) >= 2:
                datos[fila[0].strip("* ").lower()] = sin_comentarios(fila[1]) or None
    return Materia(carpeta, nombre, datos.get("docente"), datos.get("formato que pide el docente"))


def leer_tarea(carpeta: Path) -> Tarea:
    carpeta = Path(carpeta).resolve()
    ruta = carpeta / "TAREA.md"
    if not ruta.exists():
        raise FileNotFoundError(f"No existe {ruta}")
    texto = ruta.read_text(encoding="utf-8")
    primera = next((linea[2:].strip() for linea in texto.splitlines() if linea.startswith("# ")), carpeta.name)

    codigo, _, titulo = primera.partition(" — ")
    datos = campos(texto)
    rango = seccion(texto, "Formato")
    formato_seccion = sin_comentarios("\n".join(texto.splitlines()[slice(*rango)])) if rango else ""
    formato = formato_seccion or datos.get("formato") or None

    # Extracción y normalización de modalidad y equipo
    grupo = datos.get("grupo") or None
    if grupo and grupo.strip().lower() in ("n/a", "na", "ninguno", "ninguna", "-", "no aplica", "none"):
        grupo = None

    integrantes_raw = datos.get("integrantes") or datos.get("autor") or datos.get("estudiante") or ""
    integrantes = [
        re.sub(r"^[-*•\d.]+\s*", "", item).strip()
        for item in re.split(r"[,;\n]+", integrantes_raw)
        if re.sub(r"^[-*•\d.]+\s*", "", item).strip()
    ]

    mod_campo = datos.get("modalidad")
    if mod_campo is not None:
        es_grupal = mod_campo.strip().lower() in ("grupal", "grupo", "en equipo", "equipo")
    else:
        es_grupal = bool(grupo) or len(integrantes) > 1
    modalidad = "grupal" if es_grupal else "individual"

    return Tarea(
        carpeta=carpeta,
        codigo=codigo.strip() or carpeta.name.split("_")[0],
        titulo=titulo.strip() or primera,
        materia=leer_materia(carpeta.parent),
        estado=(datos.get("estado") or "pendiente").lower(),
        fecha=leer_fecha(datos.get("fecha de entrega")),
        extension=leer_extension(datos.get("extensión") or datos.get("extension")),
        formato=formato or None,
        campos=datos,
        modalidad=modalidad,
        grupo=grupo,
        integrantes=integrantes,
    )


def marcar_estado(tarea: Tarea, estado: str) -> list[Path]:
    """Cambia 'Estado:' en TAREA.md y la fila de la tabla de la ficha de materia."""
    cambiados = []
    texto = tarea.ruta.read_text(encoding="utf-8")
    tarea.ruta.write_text(reemplazar_campo(texto, "Estado", estado), encoding="utf-8")
    cambiados.append(tarea.ruta)

    ficha = ruta_ficha_materia(tarea.materia.carpeta)
    if ficha.exists():
        lineas = ficha.read_text(encoding="utf-8").splitlines()
        for i, linea in enumerate(lineas):
            fila = celdas(linea) if linea.lstrip().startswith("|") else []
            if len(fila) >= 3 and fila[0].strip("`") == tarea.base:
                fila[-1] = estado
                lineas[i] = "| " + " | ".join(escapar_celda(c) for c in fila) + " |"
                ficha.write_text("\n".join(lineas) + "\n", encoding="utf-8")
                cambiados.append(ficha)
                break
    return cambiados
