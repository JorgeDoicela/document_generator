# -*- coding: utf-8 -*-
"""
Plantilla reutilizable para generar informes .docx en normas APA 7 (trabajo
de estudiante). El texto es monocromático; las figuras conservan su color
original, porque en una captura el color suele ser información.

Los datos del estudiante (portada y sufijo de archivos) se leen del .env de
la raíz del repositorio la primera vez que se necesitan, no al importar.

Uso típico en el script de una actividad (lo genera `tareas.py tarea`):

    import sys
    from pathlib import Path
    AQUI = Path(__file__).resolve().parent
    sys.path.insert(0, str(AQUI.parents[2] / "plantillas"))  # materias/<materia>/<tarea>/
    from apa_docx import *

    SALIDA = AQUI / nombre_entregable("A15_Titulo_Corto")   # + sufijo del .env
    bib = Bibliografia()
    bib.agregar("oracle2024", ["Oracle"], 2024, "MySQL 8.4 reference manual",
                url="https://dev.mysql.com/doc/refman/8.4/en/")

    doc, figura, tabla = nuevo_documento(
        titulo="Título del Informe",
        materia="Nombre de la Materia",
        salida=SALIDA,
        tarea=AQUI,           # docente y fecha de entrega desde TAREA.md
    )

    parrafo(doc, "Introducción, sin encabezado como pide APA 7...")
    titulo(doc, "Procedimientos almacenados", 1, criterios="C1")
    parrafo(doc, f"Texto con cita {bib.cita('oracle2024')}.")
    figura(doc, None, "Descripción de la figura", "fig1.png", "Nota explicativa.")
    tabla(doc, None, "Descripción de la tabla", ["Col A", "Col B"], [("x", "y")])
    transversal(doc, "C5")    # p. ej. "Ortografía y redacción"
    referencias(doc, bib)

    guardar_documento(doc, SALIDA)

Ver documentación técnica completa en docs/02-motores-documentales/01-motor-apa7.md.
"""
import datetime
import os
import re
import sys
from pathlib import Path
from typing import List, Optional, Union

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import config
    from motor_base import (
        PREFIJO_MARCA,
        SUFIJO_TRANSVERSAL,
        marcar_elemento,
        normalizar_criterios,
        registrar_motor,
    )
else:
    from . import config
    from .motor_base import (
        PREFIJO_MARCA,
        SUFIJO_TRANSVERSAL,
        marcar_elemento,
        normalizar_criterios,
        registrar_motor,
    )


# Constantes públicas leídas dinámicamente mediante __getattr__
NOMBRE_ESTUDIANTE: str = ""
INSTITUCION: str = ""
CARRERA: str = ""
SUFIJO_ARCHIVOS: str = ""

__all__ = [
    "Bibliografia", "NEGRO", "WD_ALIGN_PARAGRAPH",
    "NOMBRE_ESTUDIANTE", "INSTITUCION", "CARRERA", "SUFIJO_ARCHIVOS",
    "aplicar_metadatos", "caja_captura_evidencia", "codigo", "codigo_bloque",
    "convertir_a_grises", "dividir_formula_larga", "enunciado_formal",
    "fecha_hoy", "fecha_portada", "formula_bloque", "guardar_documento",
    "insertar_indice_automatico", "leer_fuente", "nombre_entregable",
    "normalizar_latex_a_unicode", "nuevo_documento", "nuevo_documento_tematico",
    "parrafo", "referencia", "referencias", "resumen_ejecutivo",
    "salto_de_pagina", "tabla", "tabla_academica", "tabla_institucional",
    "texto_a_omml", "titulo", "transversal", "vinieta",
]


NEGRO = RGBColor(0, 0, 0)
FUENTE = "Times New Roman"
IDIOMA = "es-ES"
PREFIJO_MARCA = "rubrica_"
SUFIJO_TRANSVERSAL = "_todo"

_MESES = ("enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
          "agosto", "septiembre", "octubre", "noviembre", "diciembre")

# --------------------------------------------------------------------------
# Datos del estudiante: se leen del .env al primer uso
# --------------------------------------------------------------------------
_CONSTANTES_ENV = ("NOMBRE_ESTUDIANTE", "INSTITUCION", "CARRERA", "SUFIJO_ARCHIVOS")
_config: dict[str, str] | None = None


def _cfg() -> dict[str, str]:
    global _config
    if _config is None:
        _config = dict(config.cargar_o_salir())
    return _config



def __getattr__(nombre):
    # NOMBRE_ESTUDIANTE, INSTITUCION... siguen disponibles como antes, pero
    # solo leen el .env cuando alguien los usa.
    if nombre in _CONSTANTES_ENV:
        return _cfg()[nombre]
    raise AttributeError(f"module {__name__!r} has no attribute {nombre!r}")


def fecha_portada(fecha: datetime.date | None = None) -> str:
    """date(2026, 9, 23) → '23 de septiembre de 2026' (hoy si no se indica)."""
    fecha = fecha or datetime.date.today()
    return f"{fecha.day} de {_MESES[fecha.month - 1]} de {fecha.year}"


def fecha_hoy() -> str:
    return fecha_portada()


def nombre_entregable(base, extension=".docx", *, tarea=None, grupo=None, sufijo=None):
    """Genera el nombre estándar del archivo entregable.

    - Modalidad Individual: '<base>_<SUFIJO_ARCHIVOS>.docx'
    - Modalidad Grupal: '<base>_<GRUPO>.docx' o sufijo explícito.
    """
    ext = extension if extension.startswith(".") else f".{extension}"
    suf = sufijo or _cfg()["SUFIJO_ARCHIVOS"]

    if grupo and str(grupo).strip().lower() in ("n/a", "na", "ninguno", "ninguna", "-", "no aplica", "none"):
        grupo = None

    if tarea is not None:
        try:
            if __package__ in (None, ""):
                sys.path.insert(0, str(Path(__file__).resolve().parent))
                import ficha
            else:
                from . import ficha
            t_obj = ficha.leer_tarea(Path(tarea))
            if t_obj.es_grupal:
                suf = grupo or t_obj.grupo or _cfg().get("GRUPO_DEFECTO") or suf
            elif not sufijo and t_obj.integrantes:
                import unicodedata
                nom_env = _cfg().get("NOMBRE_ESTUDIANTE", "").strip().lower()
                nom_est = t_obj.integrantes[0].strip()
                if not nom_env or nom_est.lower() != nom_env:
                    sin_tildes = unicodedata.normalize("NFKD", nom_est).encode("ascii", "ignore").decode()
                    palabras = re.findall(r"[A-Za-z0-9]+", sin_tildes)
                    if len(palabras) >= 2:
                        suf = f"{palabras[1]}_{palabras[0]}"
                    elif palabras:
                        suf = palabras[0]
        except Exception:
            pass
    elif grupo:
        suf = grupo

    suf_limpio = re.sub(r"[^\w\-]", "_", str(suf)).strip("_")
    return f"{base}_{suf_limpio}{ext}"


# --------------------------------------------------------------------------
# Utilidades de bajo nivel
# --------------------------------------------------------------------------
def _fuente_fija(rpr, nombre=FUENTE):
    """Fija la fuente en todos los alfabetos y quita las fuentes de tema
    (los estilos de encabezado de Word traen Calibri Light por tema, que
    tiene prioridad sobre el nombre de fuente)."""
    for viejo in rpr.findall(qn("w:rFonts")):
        rpr.remove(viejo)
    fuentes = OxmlElement("w:rFonts")
    for atributo in ("w:ascii", "w:hAnsi", "w:eastAsia", "w:cs"):
        fuentes.set(qn(atributo), nombre)
    rpr.insert(0, fuentes)


def _idioma(rpr, idioma=IDIOMA):
    for viejo in rpr.findall(qn("w:lang")):
        rpr.remove(viejo)
    lang = OxmlElement("w:lang")
    for atributo in ("w:val", "w:eastAsia", "w:bidi"):
        lang.set(qn(atributo), idioma)
    rpr.append(lang)


def _tema_activo(doc):
    """Devuelve el TemaDocumental asociado al documento si usa un tema no-APA7."""
    meta = getattr(doc, "_rubric_driven", None)
    if isinstance(meta, dict):
        return meta.get("tema")
    return None


def _estilos(doc, tema=None):
    """Normal, encabezados 1-3 y viñetas. Soporta APA 7 estándar y cualquier TemaDocumental."""
    if tema is not None:
        f_nombre = tema.fuente
        tam_cuerpo = tema.tamano_cuerpo
        interlineado = tema.interlineado
        espacio_despues = tema.espacio_despues
        color_h1 = tema.rgb_primario()
        color_txt = tema.rgb_texto()
        h1_centrado = tema.h1_centrado
        tams_h = {1: tema.tamano_h1, 2: tema.tamano_h2, 3: tema.tamano_h3}
    else:
        f_nombre = FUENTE
        tam_cuerpo = 12.0
        interlineado = 2.0
        espacio_despues = 0.0
        color_h1 = NEGRO
        color_txt = NEGRO
        h1_centrado = True
        tams_h = {1: 12.0, 2: 12.0, 3: 12.0}

    normal = doc.styles["Normal"]
    normal.font.name = f_nombre
    normal.font.size = Pt(tam_cuerpo)
    normal.font.color.rgb = color_txt
    _fuente_fija(normal.element.get_or_add_rPr(), f_nombre)
    _idioma(normal.element.get_or_add_rPr())
    normal.paragraph_format.line_spacing = interlineado
    normal.paragraph_format.space_after = Pt(espacio_despues)

    for nivel in (1, 2, 3):
        est = doc.styles[f"Heading {nivel}"]
        est.font.name = f_nombre
        est.font.size = Pt(tams_h[nivel])
        est.font.bold = True
        est.font.italic = (nivel == 3)
        est.font.color.rgb = color_h1 if nivel == 1 else color_txt
        _fuente_fija(est.element.get_or_add_rPr(), f_nombre)
        pf = est.paragraph_format
        pf.alignment = WD_ALIGN_PARAGRAPH.CENTER if (nivel == 1 and h1_centrado) else WD_ALIGN_PARAGRAPH.LEFT
        pf.line_spacing = interlineado
        pf.space_before = Pt(12 if nivel == 1 else 10)
        pf.space_after = Pt(4 if tema is not None else 0)
        pf.keep_with_next = True
        pf.first_line_indent = Inches(0)

    viñetas = doc.styles["List Bullet"]
    viñetas.font.name = f_nombre
    viñetas.font.color.rgb = color_txt


def _numero_de_pagina(section):
    p = section.header.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    p.paragraph_format.line_spacing = 1.0
    _campo(p, "PAGE")


def _campo(parrafo_, instruccion, texto_previo=""):
    run = parrafo_.add_run()
    inicio = OxmlElement("w:fldChar")
    inicio.set(qn("w:fldCharType"), "begin")
    inicio.set(qn("w:dirty"), "true")
    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = f" {instruccion} "
    separa = OxmlElement("w:fldChar")
    separa.set(qn("w:fldCharType"), "separate")
    fin = OxmlElement("w:fldChar")
    fin.set(qn("w:fldCharType"), "end")
    run._r.append(inicio)
    run._r.append(instr)
    run._r.append(separa)
    if texto_previo:
        t = OxmlElement("w:t")
        t.text = texto_previo
        run._r.append(t)
    run._r.append(fin)
    run.font.color.rgb = NEGRO
    return run


def _marcar(parrafo_, nombre):
    """Marcador invisible: así el .docx recuerda qué criterio cubre cada sección."""
    marcar_elemento(parrafo_, nombre)


def _ids_criterios(criterios: Optional[Union[str, List[str]]]) -> list[str]:
    return [str(c) for c in normalizar_criterios(criterios)]





def _set_borde_celda(celda, color="000000", tam="4"):
    tc_pr = celda._tc.get_or_add_tcPr()
    bordes = OxmlElement("w:tcBorders")
    for lado in ("top", "left", "bottom", "right"):
        el = OxmlElement("w:%s" % lado)
        el.set(qn("w:val"), "single")
        el.set(qn("w:sz"), tam)
        el.set(qn("w:color"), color)
        bordes.append(el)
    tc_pr.append(bordes)


def _sombrear_celda(celda, hexcolor="D9D9D9"):
    tc_pr = celda._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), hexcolor)
    tc_pr.append(shd)


def _texto_con_cursivas(p, texto, tamano=12):
    """Añade `texto` a `p` interpretando sintaxis de formato enriquecido."""
    _agregar_texto_enriquecido(p, texto, tamano=tamano)


def _agregar_texto_enriquecido(parrafo_obj, texto: str, *, f_nombre: str = FUENTE, tamano: float = 12,
                              negrita: bool = False, cursiva: bool = False, color=NEGRO):
    """Delega el renderizado de texto enriquecido al núcleo único en bloques.py."""
    if __package__ in (None, ""):
        import bloques as _bloques
    else:
        from . import bloques as _bloques
    _bloques.agregar_texto_enriquecido(
        parrafo_obj,
        texto,
        fuente=f_nombre,
        tamano=tamano,
        negrita=negrita,
        cursiva=cursiva,
        color=color,
    )


def _siguiente(doc, clave):
    estado = doc.__dict__.setdefault("_rubric_driven", {})
    estado[clave] = estado.get(clave, 0) + 1
    return estado[clave]


# --------------------------------------------------------------------------
# Bloques de contenido
# --------------------------------------------------------------------------
def parrafo(doc, texto="", *, alineacion=WD_ALIGN_PARAGRAPH.JUSTIFY,
            sangria=None, espaciado=None, negrita=False, cursiva=False,
            tamano=None, antes=0, despues=None):
    tema = _tema_activo(doc)
    f_nombre = tema.fuente if tema is not None else FUENTE
    color_txt = tema.rgb_texto() if tema is not None else NEGRO
    sangria_pulg = 0.4 if tema is not None else 0.5
    if sangria is None:
        sangria = tema.sangria_primera_linea if tema is not None else True
    if espaciado is None:
        espaciado = tema.interlineado if tema is not None else 2.0
    if tamano is None:
        tamano = tema.tamano_cuerpo if tema is not None else 12
    if despues is None:
        despues = tema.espacio_despues if tema is not None else 0

    if texto and "\n" in texto:
        parrafos = []
        for linea in texto.split("\n"):
            linea_limpia = linea.strip()
            if not linea_limpia:
                continue
            es_vinieta = bool(re.match(r"^\s*(?:•\s*|[-*]\s+)", linea))
            p_linea = doc.add_paragraph()
            pf = p_linea.paragraph_format
            pf.line_spacing = espaciado
            if es_vinieta:
                p_linea.alignment = WD_ALIGN_PARAGRAPH.LEFT
                pf.left_indent = Inches(sangria_pulg)
                pf.first_line_indent = Inches(-0.2)
                pf.space_before = Pt(1)
                pf.space_after = Pt(2)
            else:
                p_linea.alignment = alineacion
                pf.space_before = Pt(antes)
                pf.space_after = Pt(despues)
                if sangria:
                    pf.first_line_indent = Inches(sangria_pulg)
            _agregar_texto_enriquecido(
                p_linea,
                linea if not es_vinieta else linea.lstrip(),
                f_nombre=f_nombre,
                tamano=tamano,
                negrita=negrita,
                cursiva=cursiva,
                color=color_txt,
            )
            parrafos.append(p_linea)
        return parrafos[-1] if parrafos else doc.add_paragraph()

    p = doc.add_paragraph()
    p.alignment = alineacion
    pf = p.paragraph_format
    pf.line_spacing = espaciado
    pf.space_before = Pt(antes)
    pf.space_after = Pt(despues)
    if sangria:
        pf.first_line_indent = Inches(sangria_pulg)
    if texto:
        _agregar_texto_enriquecido(
            p,
            texto,
            f_nombre=f_nombre,
            tamano=tamano,
            negrita=negrita,
            cursiva=cursiva,
            color=color_txt,
        )
    return p


def titulo(doc, texto, nivel=1, criterios=None):
    """Encabezado APA 7 con estilo de Word 'Heading N'.

    nivel 1: centrado y negrita (secciones principales).
    nivel 2: alineado a la izquierda, negrita.
    nivel 3: alineado a la izquierda, negrita y cursiva.

    criterios: IDs de la rúbrica que cubre esta sección ("C1" o ["C1", "C2"]).
    Se guardan como marcadores invisibles en el .docx y los usa
    `tareas.py comprobar` para verificar la cobertura.
    """
    nivel = min(max(int(nivel), 1), 3)
    # Limpia asteriscos de markdown para encabezados en el DOM y bookmarks
    texto_limpio = re.sub(r"\*\*\*([^*]+?)\*\*\*", r"\1", str(texto))
    texto_limpio = re.sub(r"\*\*([^*]+?)\*\*", r"\1", texto_limpio)
    texto_limpio = re.sub(r"\*([^*]+?)\*", r"\1", texto_limpio)
    p = doc.add_paragraph(texto_limpio, style=f"Heading {nivel}")
    for ident in _ids_criterios(criterios):
        _marcar(p, PREFIJO_MARCA + ident)
    return p


def transversal(doc, *criterios):
    """Declara criterios que se cumplen en todo el documento (ortografía,
    formato APA...). No tienen sección propia ni cuentan para el reparto de
    extensión."""
    ids = _ids_criterios(list(criterios) if len(criterios) != 1 else criterios[0])
    p = doc.paragraphs[-1]
    for ident in ids:
        _marcar(p, PREFIJO_MARCA + ident + SUFIJO_TRANSVERSAL)


def vinieta(doc, texto):
    tema = _tema_activo(doc)
    p = doc.add_paragraph(style="List Bullet")
    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    pf = p.paragraph_format
    pf.line_spacing = tema.interlineado if tema is not None else 2.0
    pf.space_after = Pt(2 if tema is not None else 0)
    pf.left_indent = Inches(0.4 if tema is not None else 0.5)
    f_nombre = tema.fuente if tema is not None else FUENTE
    tam = tema.tamano_cuerpo if tema is not None else 12
    color_txt = tema.rgb_texto() if tema is not None else NEGRO
    _agregar_texto_enriquecido(p, texto, f_nombre=f_nombre, tamano=tam, color=color_txt)
    return p


def codigo(doc, texto, tamano=8.5):
    """Bloque de código/comandos monoespaciado a espacio sencillo."""
    for linea in texto.split("\n"):
        p = doc.add_paragraph()
        pf = p.paragraph_format
        pf.line_spacing = 1.0
        pf.space_before = Pt(0)
        pf.space_after = Pt(0)
        pf.left_indent = Inches(0.4)
        pf.first_line_indent = Inches(0)
        p.alignment = WD_ALIGN_PARAGRAPH.LEFT
        r = p.add_run(linea if linea.strip() else " ")
        r.font.name = "Courier New"
        _fuente_fija(r._element.get_or_add_rPr(), "Courier New")
        r.font.size = Pt(tamano)
        r.font.color.rgb = NEGRO


def salto_de_pagina(doc):
    doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)


def referencia(doc, texto):
    """Entrada de la lista de referencias con sangría francesa.
    Lo que va entre *asteriscos* sale en cursiva (títulos de libros, revistas)."""
    tema = _tema_activo(doc)
    f_nombre = tema.fuente if tema is not None else FUENTE
    tam = tema.tamano_cuerpo if tema is not None else 12
    color_txt = tema.rgb_texto() if tema is not None else NEGRO
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    pf = p.paragraph_format
    pf.line_spacing = tema.interlineado if tema is not None else 2.0
    pf.left_indent = Inches(0.5)
    pf.first_line_indent = Inches(-0.5)
    pf.space_after = Pt(tema.espacio_despues if tema is not None else 0)
    _agregar_texto_enriquecido(p, texto, f_nombre=f_nombre, tamano=tam, color=color_txt)
    return p


def _make_figura(carpeta_capturas):
    """Genera la función figura() con la carpeta de capturas ya fijada."""
    def figura(doc, numero, descripcion, archivo, nota, ancho=5.5):
        """numero=None numera automáticamente (Figura 1, 2...)."""
        tema = _tema_activo(doc)
        f_nombre = tema.fuente if tema is not None else FUENTE
        tam = tema.tamano_cuerpo if tema is not None else 12
        color_txt = tema.rgb_texto() if tema is not None else NEGRO
        esp = tema.interlineado if tema is not None else 2.0

        numero = _siguiente(doc, "figura") if numero is None else numero
        p = doc.add_paragraph()
        p.paragraph_format.line_spacing = esp
        p.paragraph_format.space_before = Pt(12)
        p.paragraph_format.space_after = Pt(0)
        p.paragraph_format.keep_with_next = True
        r = p.add_run("Figura %s" % numero)
        r.bold = True
        r.font.name = f_nombre
        _fuente_fija(r._element.get_or_add_rPr(), f_nombre)
        r.font.size = Pt(tam)
        r.font.color.rgb = color_txt

        p = doc.add_paragraph()
        p.paragraph_format.line_spacing = esp
        p.paragraph_format.space_after = Pt(6)
        p.paragraph_format.keep_with_next = True
        _agregar_texto_enriquecido(
            p, descripcion, f_nombre=f_nombre, tamano=tam, cursiva=True, color=color_txt
        )

        ruta = os.fspath(archivo)
        if not os.path.isabs(ruta):
            ruta = os.path.join(carpeta_capturas, ruta)
        if os.path.exists(ruta):
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p.paragraph_format.space_after = Pt(6)
            p.paragraph_format.line_spacing = 1.0
            p.paragraph_format.keep_with_next = True
            p.add_run().add_picture(ruta, width=Inches(ancho))
        else:
            parrafo(doc, "[FALTA LA CAPTURA: %s]" % archivo,
                    alineacion=WD_ALIGN_PARAGRAPH.CENTER, sangria=False)

        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        p.paragraph_format.line_spacing = 1.5 if tema is None else esp
        p.paragraph_format.space_after = Pt(12)
        r = p.add_run("Nota. ")
        r.italic = True
        r.font.name = f_nombre
        _fuente_fija(r._element.get_or_add_rPr(), f_nombre)
        r.font.size = Pt(10)
        r.font.color.rgb = color_txt
        _agregar_texto_enriquecido(p, nota, f_nombre=f_nombre, tamano=10, color=color_txt)
        return numero
    return figura


def tabla(doc, numero, descripcion, encabezados, filas, anchos=None, estilo=None):
    """Tabla en formato APA 7 oficial (Opción 1) o cuadrícula institucional (Opción 4).

    numero=None numera automáticamente.
    Por defecto genera la tabla en formato APA 7 canónico (3 líneas horizontales,
    cero verticales, fondo blanco). Puede alternarse a cuadrícula pasando estilo='grid'
    o mediante la variable de entorno ESTILO_TABLA=grid. Deja un párrafo después, para
    que dos tablas seguidas no se fusionen (LibreOffice se cuelga con eso).
    """
    try:
        from plantillas.visual import EstilosTabla, resolver_estilo_tabla, tabla_estilizada
    except ImportError:
        from visual import (  # type: ignore[no-redef]
            EstilosTabla,
            resolver_estilo_tabla,
            tabla_estilizada,
        )

    tema = _tema_activo(doc)
    numero = _siguiente(doc, "tabla") if numero is None else numero
    defecto_tabla = tema.estilo_tabla if tema is not None else EstilosTabla.APA
    fuente_tabla = tema.fuente if tema is not None else FUENTE
    estilo_resuelto = resolver_estilo_tabla(estilo, defecto=defecto_tabla)
    return tabla_estilizada(
        doc,
        encabezados=encabezados,
        filas=filas,
        estilo=estilo_resuelto,
        anchos=anchos,
        numero_tabla=numero,
        titulo_tabla=descripcion,
        fuente=fuente_tabla,
    )


def leer_fuente(ruta):
    with open(ruta, encoding="utf-8") as f:
        return f.read().rstrip()


def convertir_a_grises(carpeta_capturas, patrones=("*.png", "*.jpg", "*.jpeg")):
    """DESACONSEJADA. Convierte a escala de grises las capturas de una carpeta.

    La norma del repositorio es que **las figuras conserven su color
    original**: el texto del documento es monocromático, las imágenes no. En
    una fotografía o una captura el color suele ser información —qué diodo
    está encendido, de qué color es un cable, si una advertencia está en rojo—
    y perderlo empobrece la evidencia sin ganar nada a cambio.

    Esta función se conserva solo para documentos antiguos que ya dependen de
    ella. Reescribe los archivos **en el sitio**, de modo que antes de
    convertir cada imagen guarda una copia intacta en la subcarpeta
    `originales/`, que ningún glob de la plantilla alcanza. Así la conversión
    deja de ser irreversible: basta con volver a copiar desde ahí.
    """
    import glob
    import shutil

    from PIL import Image

    respaldo = os.path.join(carpeta_capturas, "originales")
    os.makedirs(respaldo, exist_ok=True)
    convertidas = []
    for patron in patrones:
        for ruta in glob.glob(os.path.join(carpeta_capturas, patron)):
            copia = os.path.join(respaldo, os.path.basename(ruta))
            if not os.path.exists(copia):
                shutil.copy2(ruta, copia)
            im = Image.open(ruta).convert("L").convert("RGB")
            im.save(ruta, quality=92)
            convertidas.append(ruta)
    return convertidas


# --------------------------------------------------------------------------
# Citas y referencias (APA 7, IEEE y Vancouver)
# --------------------------------------------------------------------------
ESTILOS_CITACION = ("apa7", "ieee", "vancouver")


def _normalizar_estilo_citacion(estilo: str) -> str:
    clave = (estilo or "apa7").strip().lower()
    if clave in ("apa", "apa7", "apa 7"):
        return "apa7"
    if clave in ("ieee", "vancouver"):
        return clave
    raise ValueError(f"Estilo de citación no soportado: {estilo!r}. Válidos: {', '.join(ESTILOS_CITACION)}")


def _apellido(autor: str) -> str:
    """'Ramos, J. A.' → 'Ramos'; 'Oracle' → 'Oracle'."""
    return autor.split(",")[0].strip()


def _autor_ieee(autor: str) -> str:
    """'Ramos, J. A.' → 'J. A. Ramos'; 'Oracle' → 'Oracle'."""
    if "," not in autor:
        return autor.strip()
    apellido, iniciales = [p.strip() for p in autor.split(",", 1)]
    return f"{iniciales} {apellido}".strip() if iniciales else apellido


def _autor_vancouver(autor: str) -> str:
    """'Ramos, J. A.' → 'Ramos JA'; 'Oracle' → 'Oracle'."""
    if "," not in autor:
        return autor.strip()
    apellido, iniciales = [p.strip() for p in autor.split(",", 1)]
    inics_limpias = "".join(ch for ch in iniciales if ch.isalpha()).upper()
    return f"{apellido} {inics_limpias}".strip() if inics_limpias else apellido


def _unir(elementos, conector="y"):
    if len(elementos) == 1:
        return elementos[0]
    return ", ".join(elementos[:-1]) + f" {conector} " + elementos[-1]


class Bibliografia:
    """Gestor bibliográfico multi-estilo (APA 7, IEEE numérico y Vancouver).

        bib = Bibliografia()                    # APA 7 por defecto
        bib_ieee = Bibliografia(estilo="ieee")  # IEEE numérico [1]
        bib_van = Bibliografia(estilo="vancouver")  # Vancouver numérico (1)

        bib.agregar("ramos2024", ["Ramos, J.", "Pérez, A."], 2024,
                    "Bases de datos relacionales", "Alfaomega")
        bib.agregar("oracle2024", ["Oracle"], 2024, "MySQL 8.4 reference manual",
                    url="https://dev.mysql.com/doc/refman/8.4/en/")
        bib.agregar("lee2023", ["Lee, K."], 2023, "Indexing strategies",
                    "Journal of Databases", detalles="12(3), 45–60", tipo="articulo")

        bib.cita("ramos2024")            → '(Ramos y Pérez, 2024)' | '[1]' | '(1)'
        bib.cita("ramos2024", "p. 15")   → '(Ramos y Pérez, 2024, p. 15)' | '[1, p. 15]' | '(1, p. 15)'
        bib.cita_narrativa("lee2023")    → 'Lee (2023)' | 'Lee [2]' | 'Lee (2)'
        referencias(doc, bib)            → sección Referencias en página nueva

    tipo="articulo" o "capitulo" pone en cursiva la fuente (revista, libro);
    el resto pone en cursiva el título. Para casos especiales, `texto=` da la
    entrada completa (con *cursivas* entre asteriscos).
    """

    def __init__(self, estilo: str = "apa7"):
        self.estilo = _normalizar_estilo_citacion(estilo)
        self._fuentes: dict[str, dict] = {}
        self._citadas: set[str] = set()
        self._orden_aparicion: list[str] = []

    @property
    def es_numerico(self) -> bool:
        return self.estilo in ("ieee", "vancouver")

    def numero(self, clave: str) -> int:
        """Devuelve el índice numérico (1-based) asignado por orden de aparición."""
        if clave not in self._orden_aparicion:
            self._fuente(clave)
        return self._orden_aparicion.index(clave) + 1

    def agregar(self, clave, autores, anio, titulo="", fuente="", *, url="",
                detalles="", tipo="libro", texto=""):
        if clave in self._fuentes:
            raise ValueError(f"La referencia '{clave}' ya existe")
        if isinstance(autores, str):
            autores = [autores]
        if not autores:
            raise ValueError(f"'{clave}': hace falta al menos un autor (persona u organización)")
        self._fuentes[clave] = dict(autores=list(autores), anio=str(anio), titulo=titulo,
                                    fuente=fuente, url=url, detalles=detalles, tipo=tipo,
                                    texto=texto)
        return clave

    def _fuente(self, clave):
        if clave not in self._fuentes:
            disponibles = ", ".join(sorted(self._fuentes)) or "ninguna"
            raise KeyError(f"No hay referencia '{clave}' (hay: {disponibles})")
        if clave not in self._citadas:
            self._citadas.add(clave)
            self._orden_aparicion.append(clave)
        return self._fuentes[clave]

    def _autores_cita(self, f):
        apellidos = [_apellido(a) for a in f["autores"]]
        if len(apellidos) >= 3:
            return f"{apellidos[0]} et al."
        return " y ".join(apellidos)

    def cita(self, *claves, pagina=""):
        """Cita en el texto según el estilo activo:
        - apa7: '(Ramos, 2024)' / '(Lee, 2023; Ramos, 2024)'
        - ieee: '[1]' / '[1], [2]' / '[1, p. 15]'
        - vancouver: '(1)' / '(1,2)' / '(1, p. 15)'
        Una segunda posición textual se toma como página: cita('x', 'p. 15').
        """
        lista_claves = list(claves)
        if len(lista_claves) == 2 and lista_claves[1] not in self._fuentes and not pagina:
            pagina = str(lista_claves[1])
            lista_claves = lista_claves[:1]

        if self.estilo == "ieee":
            nums = [self.numero(clave) for clave in lista_claves]
            if len(nums) == 1 and pagina:
                return f"[{nums[0]}, {pagina}]"
            return ", ".join(f"[{n}]" for n in nums)

        if self.estilo == "vancouver":
            nums = [self.numero(clave) for clave in lista_claves]
            cuerpo = ",".join(str(n) for n in nums)
            return f"({cuerpo}, {pagina})" if pagina else f"({cuerpo})"

        partes = []
        for clave in lista_claves:
            f = self._fuente(clave)
            partes.append(f"{self._autores_cita(f)}, {f['anio']}")
        partes.sort(key=str.lower)
        texto = "; ".join(partes)
        return f"({texto}, {pagina})" if pagina else f"({texto})"

    def cita_narrativa(self, clave, pagina=""):
        """Cita narrativa:
        - apa7: 'Ramos y Pérez (2024)'
        - ieee: 'Ramos y Pérez [1]'
        - vancouver: 'Ramos y Pérez (1)'
        """
        f = self._fuente(clave)
        if self.estilo == "ieee":
            n = self.numero(clave)
            suf = f", {pagina}" if pagina else ""
            return f"{self._autores_cita(f)} [{n}{suf}]"
        if self.estilo == "vancouver":
            n = self.numero(clave)
            suf = f", {pagina}" if pagina else ""
            return f"{self._autores_cita(f)} ({n}{suf})"
        sufijo = f", {pagina}" if pagina else ""
        return f"{self._autores_cita(f)} ({f['anio']}{sufijo})"

    def entrada(self, clave) -> str:
        f = self._fuentes[clave]
        if f.get("texto"):
            if self.estilo == "ieee" and not re.match(r"^\[\d+\]\s+", str(f["texto"]).strip()):
                return f"[{self.numero(clave)}] {f['texto']}"
            if self.estilo == "vancouver" and not re.match(r"^\d+\.\s+", str(f["texto"]).strip()):
                return f"{self.numero(clave)}. {f['texto']}"
            return str(f["texto"])

        if self.estilo == "ieee":
            n = self.numero(clave)
            autores = _unir([_autor_ieee(a) for a in f["autores"]])
            es_art = f["tipo"] in ("articulo", "capitulo")
            partes = [f"[{n}] {autores},"]
            if f["titulo"]:
                partes.append(f"\"{f['titulo']},\"" if es_art else f"*{f['titulo']}*.")
            fuente = f["fuente"]
            if fuente and fuente not in f["autores"]:
                fuente_fmt = f"*{fuente}*" if es_art else fuente
                bloque_f = f"{fuente_fmt}, {f['detalles']}" if f["detalles"] else fuente_fmt
                partes.append(f"{bloque_f}, {f['anio']}.")
            elif f["detalles"]:
                partes.append(f"{f['detalles']}, {f['anio']}.")
            else:
                partes.append(f"{f['anio']}.")
            if f["url"]:
                partes.append(f"Disponible en: {f['url']}")
            return " ".join(partes)

        if self.estilo == "vancouver":
            n = self.numero(clave)
            autores = ", ".join(_autor_vancouver(a) for a in f["autores"])
            if not autores.endswith("."):
                autores += "."
            partes = [f"{n}. {autores}"]
            if f["titulo"]:
                partes.append(f"{f['titulo'].rstrip('.')}.")
            fuente = f["fuente"]
            if fuente and fuente not in f["autores"]:
                fuente_txt = f"{fuente.rstrip('.')}."
                anio_det = f"{f['anio']};{f['detalles'].rstrip('.')}." if f["detalles"] else f"{f['anio']}."
                partes.append(f"{fuente_txt} {anio_det}")
            elif f["detalles"]:
                partes.append(f"{f['anio']};{f['detalles'].rstrip('.')}.")
            else:
                partes.append(f"{f['anio']}.")
            if f["url"]:
                partes.append(f"Disponible en: {f['url']}")
            return " ".join(partes)

        autores = _unir(f["autores"])
        if not autores.endswith("."):
            autores += "."
        partes = [f"{autores} ({f['anio']})."]
        cursiva_fuente = f["tipo"] in ("articulo", "capitulo")
        if f["titulo"]:
            partes.append(f"{f['titulo']}." if cursiva_fuente else f"*{f['titulo']}*.")
        fuente = f["fuente"]
        if fuente and fuente not in f["autores"]:
            fuente = f"*{fuente}*" if cursiva_fuente else fuente
            partes.append(f"{fuente}, {f['detalles']}." if f["detalles"] else f"{fuente}.")
        elif f["detalles"]:
            partes.append(f"{f['detalles']}.")
        if f["url"]:
            partes.append(f["url"])
        return " ".join(partes)

    def no_citadas(self):
        return sorted(set(self._fuentes) - self._citadas)

    def ordenadas(self):
        if self.es_numerico:
            return list(self._orden_aparicion)

        def orden(clave):
            f = self._fuentes[clave]
            return ([_apellido(a).lower() for a in f["autores"]], f["anio"])
        return sorted(self._citadas, key=orden)


def referencias(doc, bib=None, *, criterios=None, nueva_pagina=True, entradas=()):
    """Sección 'Referencias' (APA 7 alfabético o IEEE/Vancouver por orden de aparición).
    Incluye las fuentes de `bib` que se hayan citado; `entradas` añade referencias manuales."""
    if nueva_pagina:
        salto_de_pagina(doc)
    titulo(doc, "Referencias", 1, criterios=criterios)
    textos = [bib.entrada(c) for c in bib.ordenadas()] if bib else []
    textos_manuales = list(entradas)
    if bib and bib.es_numerico:
        lista_final = textos + textos_manuales
    else:
        lista_final = sorted(textos + textos_manuales, key=lambda t: t.lstrip("*").lower())
    for texto in lista_final:
        referencia(doc, texto)
    if bib and bib.no_citadas():
        print("Aviso: referencias registradas pero nunca citadas (no se incluyen): "
              + ", ".join(bib.no_citadas()))


# --------------------------------------------------------------------------
# Punto de entrada: crea el documento con portada y estilos ya aplicados
# --------------------------------------------------------------------------
def _desde_tarea(carpeta):
    """Docente y fecha de entrega desde TAREA.md y el README de la materia."""
    if __package__ in (None, ""):
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import ficha
    else:
        from . import ficha
    try:
        t = ficha.leer_tarea(carpeta)
    except FileNotFoundError:
        return None, None
    return t.materia.docente, t.fecha



def _extraer_tema_de_texto(texto_fmt: str) -> str:
    """Extrae un nombre de tema o ruta JSON desde un campo de formato (TAREA.md o MATERIA.md)."""
    fmt_limpio = (texto_fmt or "").strip()
    if not fmt_limpio:
        return ""
    fmt_lower = fmt_limpio.lower()
    if fmt_lower in ("apa7", "apa", "por defecto", "default"):
        return ""
    if fmt_lower.endswith(".json") and Path(fmt_limpio).is_file():
        return fmt_limpio
    try:
        if __package__ in (None, ""):
            import temas as temas_mod
        else:
            from . import temas as temas_mod
        for nombre_tema in sorted(temas_mod.listar_temas(), key=len, reverse=True):
            if nombre_tema == "apa7":
                continue
            if re.search(rf"\b{re.escape(nombre_tema.lower())}\b", fmt_lower):
                return str(nombre_tema)
    except Exception:
        pass
    return ""


def _resolver_tema_solicitado(formato, fmt_tarea: str, cfg_actual: dict, fmt_materia: str = "") -> str:
    """Resuelve el tema documental por precedencia: argumento > TAREA.md > MATERIA.md > TEMA_DEFECTO (.env)."""
    mod_formato = (str(formato) if formato is not None else "").strip()
    if mod_formato:
        return mod_formato

    for fuente_fmt in (fmt_tarea, fmt_materia):
        if not fuente_fmt:
            continue
        fmt_lower = fuente_fmt.strip().lower()
        if fmt_lower in ("apa7", "apa", "por defecto", "default"):
            return ""
        hallado = _extraer_tema_de_texto(fuente_fmt)
        if hallado:
            return hallado

    tema_env = str(cfg_actual.get("TEMA_DEFECTO", "")).strip()
    if tema_env and tema_env.lower() not in ("apa7", "apa", "por defecto", "default"):
        return tema_env
    return ""


def nuevo_documento(*, titulo, materia, salida, fecha=None, docente=None, tarea=None,
                    carpeta_capturas=None, nombre=None, institucion=None, carrera=None,
                    indice=False, modalidad=None, grupo=None, integrantes=None,
                    formato=None):
    """Crea el Document(), aplica estilos APA 7 o un TemaDocumental configurable, arma la portada de
    estudiante (con soporte nativo para modalidad individual o grupal) y deja el cursor listo para el cuerpo.

    Portada APA 7 de estudiante: título, autor(es), grupo si aplica, afiliación (carrera,
    institución), curso, docente y fecha de entrega.
      - tarea: carpeta de la tarea; si se indica, `docente`, `fecha`, `modalidad`,
        `grupo` e `integrantes` se toman de TAREA.md y de la materia cuando no se pasan aquí.
      - fecha: str o datetime.date; por defecto la de entrega, o la de hoy.
      - indice: añade un índice automático tras la portada.
      - formato: preset ("apa7", "academico", "tecnico", "ejecutivo", "ieee"), nombre de tema
        en themes/ o themes/local/, ruta a un theme.json, o None (auto-detección por TAREA.md o .env).
    """
    salida = os.fspath(salida)
    cfg_actual = _cfg()

    fmt_tarea = ""
    fmt_materia = ""
    if tarea is not None:
        try:
            if __package__ in (None, ""):
                sys.path.insert(0, str(Path(__file__).resolve().parent))
                import ficha
            else:
                from . import ficha
            t_obj = ficha.leer_tarea(Path(tarea))
            docente = docente or t_obj.materia.docente
            fecha = fecha or t_obj.fecha
            if modalidad is None:
                modalidad = t_obj.modalidad
            if grupo is None:
                grupo = t_obj.grupo
            if integrantes is None and t_obj.integrantes:
                integrantes = t_obj.integrantes
            fmt_tarea = str(t_obj.formato or "")
            fmt_materia = str(t_obj.materia.formato or "")
        except Exception:
            pass

    if grupo and str(grupo).strip().lower() in ("n/a", "na", "ninguno", "ninguna", "-", "no aplica", "none"):
        grupo = None

    if fecha is None or isinstance(fecha, datetime.date):
        fecha = fecha_portada(fecha)
    if carpeta_capturas is None:
        carpeta_capturas = os.path.join(os.path.dirname(os.path.abspath(salida)), "capturas")

    institucion = institucion or cfg_actual["INSTITUCION"]
    carrera = carrera or cfg_actual["CARRERA"]

    # Normalizar integrantes
    lista_integrantes: list[str] = []
    if isinstance(integrantes, str):
        lista_integrantes = [i.strip() for i in re.split(r"[,;\n]+", integrantes) if i.strip()]
    elif isinstance(integrantes, (list, tuple)):
        lista_integrantes = [str(i).strip() for i in integrantes if str(i).strip()]

    mod_str = (str(modalidad) if modalidad is not None else "").strip().lower()
    if mod_str in ("individual", "solo", "unipersonal"):
        es_grupal = False
    elif mod_str in ("grupal", "grupo", "en equipo", "equipo"):
        es_grupal = True
    else:
        es_grupal = bool(grupo) or len(lista_integrantes) > 1

    if not lista_integrantes:
        if es_grupal and cfg_actual.get("INTEGRANTES_DEFECTO"):
            lista_integrantes = [i.strip() for i in cfg_actual["INTEGRANTES_DEFECTO"].split(",") if i.strip()]
        elif nombre:
            lista_integrantes = [nombre]
        elif cfg_actual.get("NOMBRE_ESTUDIANTE"):
            nom_env = cfg_actual["NOMBRE_ESTUDIANTE"]
            if es_grupal and "," in nom_env:
                lista_integrantes = [i.strip() for i in nom_env.split(",") if i.strip()]
            else:
                lista_integrantes = [nom_env]
        else:
            lista_integrantes = ["Estudiante"]

    autor_metadata = ", ".join(lista_integrantes) if lista_integrantes else (grupo or "Estudiante")

    tema_solicitado = _resolver_tema_solicitado(formato, fmt_tarea, cfg_actual, fmt_materia=fmt_materia)
    usar_tematico = bool(tema_solicitado) and tema_solicitado.lower() not in ("apa7", "apa", "por defecto", "default")

    if usar_tematico:
        doc = Document()
        if __package__ in (None, ""):
            import bloques as bloques_mod
            import formato_institucional as fmt_inst
            import temas as temas_mod
        else:
            from . import bloques as bloques_mod
            from . import formato_institucional as fmt_inst
            from . import temas as temas_mod

        tema_obj = temas_mod.cargar_tema(tema_solicitado)
        _estilos(doc, tema=tema_obj)
        fmt_inst.aplicar_portada(
            doc,
            titulo=titulo,
            subtitulo=materia,
            tema=tema_obj,
            organizacion=carrera or "",
            institucion=institucion or "",
            docente=docente,
            periodo=str(fecha) if fecha else f"Periodo {datetime.date.today().year}",
            modalidad=modalidad,
            grupo=grupo,
            integrantes=lista_integrantes,
            tarea=tarea,
        )
        props = doc.core_properties
        props.title, props.author, props.subject = titulo, autor_metadata, materia
        props.language = IDIOMA
        doc.__dict__.setdefault("_rubric_driven", {})["tema"] = tema_obj

        if indice:
            bloques_mod.insertar_indice_automatico(doc, fuente=tema_obj.fuente)

        figura_fn = _make_figura(carpeta_capturas)
        return doc, figura_fn, tabla

    doc = Document()
    _estilos(doc)
    props = doc.core_properties
    props.title, props.author, props.subject = titulo, autor_metadata, materia
    props.language = IDIOMA

    sec = doc.sections[0]
    sec.top_margin = sec.bottom_margin = Inches(1)
    sec.left_margin = sec.right_margin = Inches(1)
    _numero_de_pagina(sec)

    # ------------------------------- PORTADA -------------------------------
    for _ in range(3):
        parrafo(doc, "", sangria=False)
    parrafo(doc, titulo, alineacion=WD_ALIGN_PARAGRAPH.CENTER, sangria=False, negrita=True)
    parrafo(doc, "", sangria=False)
    afiliacion = ", ".join(x for x in (carrera, institucion) if x)

    lineas_autoria = []
    if es_grupal:
        if grupo:
            lineas_autoria.append(grupo)
        lineas_autoria.extend(lista_integrantes)
    else:
        lineas_autoria.append(lista_integrantes[0] if lista_integrantes else "Estudiante")

    bloque_portada = list(lineas_autoria)
    if afiliacion:
        bloque_portada.append(afiliacion)
    for linea in (materia, docente, fecha):
        if linea:
            bloque_portada.append(linea)

    for linea_texto in bloque_portada:
        parrafo(doc, linea_texto, alineacion=WD_ALIGN_PARAGRAPH.CENTER, sangria=False)
    salto_de_pagina(doc)

    if indice:
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = p.add_run("Índice")
        r.bold = True
        r.font.color.rgb = NEGRO
        campo = _campo(doc.add_paragraph(), 'TOC \\o "1-3" \\h \\z \\u',
                       "Actualiza el índice: clic derecho → Actualizar campo (F9).")
        doc.__dict__.setdefault("_rubric_driven", {})["indice"] = campo
        salto_de_pagina(doc)
        _actualizar_campos_al_abrir(doc)

    # El cuerpo empieza con el título en negrita; la introducción va sin
    # encabezado "Introducción", como pide APA 7.
    parrafo(doc, titulo, alineacion=WD_ALIGN_PARAGRAPH.CENTER, sangria=False, negrita=True)

    figura_fn = _make_figura(carpeta_capturas)
    return doc, figura_fn, tabla


def _actualizar_campos_al_abrir(doc):
    ajustes = doc.settings.element
    if ajustes.find(qn("w:updateFields")) is None:
        el = OxmlElement("w:updateFields")
        el.set(qn("w:val"), "true")
        ajustes.append(el)


def _rellenar_indice(doc):
    """Delega el relleno provisional del índice en bloques.rellenar_indice()."""
    rellenar_indice(doc)


def guardar_documento(doc, salida):
    _rellenar_indice(doc)
    salida = os.fspath(salida)
    Path(salida).parent.mkdir(parents=True, exist_ok=True)
    doc.save(salida)
    print("Documento generado:", salida)


class MotorAPA7:
    """Motor documental bajo el estándar APA 7 (estudiante)."""

    def configurar_pagina(self, doc, **kwargs):
        _estilos(doc)
        sec = doc.sections[0]
        sec.top_margin = sec.bottom_margin = Inches(1)
        sec.left_margin = sec.right_margin = Inches(1)
        _numero_de_pagina(sec)
        return doc


    def titulo_seccion(
        self,
        doc,
        texto: str,
        nivel: int = 1,
        criterios: Optional[Union[str, List[str]]] = None,
        **kwargs,
    ):
        return titulo(doc, texto, nivel=nivel, criterios=criterios)

    def marcar_transversal(self, doc, *criterios: str) -> None:
        transversal(doc, *criterios)


registrar_motor("apa7", MotorAPA7)


# Exportaciones de conveniencia desde los núcleos genéricos (omml, bloques, formato_institucional)
if __package__ in (None, ""):
    from bloques import (
        aplicar_metadatos,
        caja_captura_evidencia,
        codigo_bloque,
        enunciado_formal,
        insertar_indice_automatico,
        rellenar_indice,
        resumen_ejecutivo,
        tabla_academica,
    )
    from formato_institucional import nuevo_documento_tematico
    from omml import (
        dividir_formula_larga,
        formula_bloque,
        normalizar_latex_a_unicode,
        texto_a_omml,
    )
else:
    from .bloques import (  # noqa: F401
        aplicar_metadatos,
        caja_captura_evidencia,
        codigo_bloque,
        enunciado_formal,
        insertar_indice_automatico,
        rellenar_indice,
        resumen_ejecutivo,
        tabla_academica,
    )
    from .formato_institucional import nuevo_documento_tematico  # noqa: F401
    from .omml import (  # noqa: F401
        dividir_formula_larga,
        formula_bloque,
        normalizar_latex_a_unicode,
        texto_a_omml,
    )

tabla_institucional = tabla_academica


