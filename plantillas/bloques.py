# -*- coding: utf-8 -*-
"""Componentes editoriales universales en OpenXML para cualquier tipo de documento.

Centraliza la construcción tipográfica agnóstica de universidad o formato:
- Texto enriquecido Markdown (***negrita cursiva***, **negrita**, *cursiva*, `código`, ^sup, _{sub}).
- Párrafos estructurados sin estiramiento tipográfico ni saltos suaves (<w:br/>) en texto justificado.
- Enunciados formales, bloques de código, tablas fijas, evidencias visuales, resúmenes ejecutivos,
  índices automáticos TOC nativos y metadatos Core Properties.
"""
import re
from pathlib import Path
from typing import Any, List, Optional, Sequence, Union

from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor

NEGRO = RGBColor(20, 20, 20)
GRIS_OSCURO = RGBColor(60, 60, 60)
GRIS_TITULO = RGBColor(115, 115, 115)

_PATRON_ENRIQUECIDO = re.compile(
    r"(\*\*\*[^*]+?\*\*\*|\*\*[^*]+?\*\*|\*(?!\s)[^*]+?(?<!\s)\*|`[^`]+?`|\^\{?[0-9a-zA-Z]+\}?|_\{[0-9a-zA-Z]+\})"
)
_PATRON_VINIETA = re.compile(r"^\s*(?:•\s*|[-*]\s+)")


def _fuente_de_doc(doc: Any, defecto: str = "Arial") -> str:
    """Devuelve la fuente del tema activo asociado al documento, o el valor por defecto."""
    meta = getattr(doc, "_rubric_driven", None)
    if isinstance(meta, dict):
        tema = meta.get("tema")
        if tema is not None and getattr(tema, "fuente", None):
            return str(tema.fuente)
    return defecto


def _estilo_tabla_de_doc(doc: Any, defecto: str = "grid") -> str:
    """Devuelve el estilo de tabla del tema activo asociado al documento, o el defecto."""
    meta = getattr(doc, "_rubric_driven", None)
    if isinstance(meta, dict):
        tema = meta.get("tema")
        if tema is not None and getattr(tema, "estilo_tabla", None):
            return str(tema.estilo_tabla)
    return defecto


def fijar_fuente_run(run: Any, nombre: str) -> None:
    """Fija la fuente en los cuatro grupos de alfabetos WordML para evitar fallbacks."""
    run.font.name = nombre
    rpr = run._element.get_or_add_rPr()
    for viejo in rpr.findall(qn("w:rFonts")):
        rpr.remove(viejo)
    fuentes = OxmlElement("w:rFonts")
    for atributo in ("w:ascii", "w:hAnsi", "w:eastAsia", "w:cs"):
        fuentes.set(qn(atributo), nombre)
    rpr.insert(0, fuentes)


_fijar_fuente_run = fijar_fuente_run


def set_borde_celda(celda: Any, color: str = "CCCCCC", tam: str = "4") -> None:
    """Aplica bordes uniformes a una celda de tabla en WordML."""
    tc_pr = celda._tc.get_or_add_tcPr()
    bordes = OxmlElement("w:tcBorders")
    for lado in ("top", "left", "bottom", "right"):
        el = OxmlElement(f"w:{lado}")
        el.set(qn("w:val"), "single")
        el.set(qn("w:sz"), tam)
        el.set(qn("w:color"), color)
        bordes.append(el)
    tc_pr.append(bordes)


def sombrear_celda(celda: Any, hexcolor: str = "F2F2F2") -> None:
    """Aplica sombreado de fondo sólido a una celda."""
    tc_pr = celda._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), hexcolor)
    tc_pr.append(shd)


def agregar_texto_enriquecido(
    parrafo_obj: Any,
    texto: str,
    *,
    fuente: str = "Arial",
    tamano: float = 11,
    negrita: bool = False,
    cursiva: bool = False,
    color: RGBColor = NEGRO,
) -> None:
    """Inserta texto interpretando Markdown (***negrita cursiva***, **negrita**, *cursiva*,
    `código inline`) y notaciones de superíndices (^n, ^{exp}) y subíndices (_{sub})."""
    if not texto:
        return
    partes = _PATRON_ENRIQUECIDO.split(texto)
    for parte in partes:
        if not parte:
            continue
        es_neg = negrita
        es_cur = cursiva
        es_sup = False
        es_sub = False
        es_code = False
        txt = parte

        if parte.startswith("***") and parte.endswith("***") and len(parte) >= 6:
            es_neg = True
            es_cur = True
            txt = parte[3:-3]
        elif parte.startswith("**") and parte.endswith("**") and len(parte) >= 4:
            es_neg = True
            txt = parte[2:-2]
        elif parte.startswith("*") and parte.endswith("*") and len(parte) >= 2:
            es_cur = True
            txt = parte[1:-1]
        elif parte.startswith("`") and parte.endswith("`") and len(parte) >= 2:
            es_code = True
            txt = parte[1:-1]
        elif parte.startswith("^"):
            es_sup = True
            txt = parte[1:].strip("{}")
        elif parte.startswith("_{") and parte.endswith("}"):
            es_sub = True
            txt = parte[2:-1]

        r = parrafo_obj.add_run(txt)
        f_run = "Courier New" if es_code else fuente
        _fijar_fuente_run(r, f_run)
        r.font.size = Pt(max(tamano - 1.0, 8.0) if es_code else tamano)
        r.bold = es_neg
        r.italic = es_cur
        r.font.superscript = es_sup
        r.font.subscript = es_sub
        r.font.color.rgb = RGBColor(40, 40, 40) if es_code else color


def parrafo_estructurado(
    doc: Any,
    texto: str = "",
    *,
    fuente: Optional[str] = None,
    alineacion: Optional[Any] = None,
    sangria: bool = False,
    espaciado: float = 1.15,
    negrita: bool = False,
    cursiva: bool = False,
    tamano: float = 11,
    antes: int = 0,
    despues: int = 6,
    color: RGBColor = NEGRO,
) -> Any:
    """Inserta párrafos limpios fragmentando saltos de línea (\\n) en párrafos independientes.

    Previene el estiramiento tipográfico en texto justificado y aplica automáticamente
    sangría francesa en viñetas (•, -, *) y alineación limpia en enumeraciones y subtítulos.
    """
    f_activa = fuente or _fuente_de_doc(doc, "Arial")
    if not texto:
        p = doc.add_paragraph()
        p.alignment = alineacion or WD_ALIGN_PARAGRAPH.JUSTIFY
        pf = p.paragraph_format
        pf.line_spacing = espaciado
        pf.space_before = Pt(antes)
        pf.space_after = Pt(despues)
        return p

    lineas = texto.split("\n")
    parrafos_creados = []

    for idx, linea in enumerate(lineas):
        linea_limpia = linea.strip()
        if not linea_limpia:
            continue

        p = doc.add_paragraph()
        pf = p.paragraph_format
        pf.line_spacing = espaciado

        es_vinieta = bool(_PATRON_VINIETA.match(linea))
        es_enumeracion = bool(re.match(r"^\s*([0-9]+\.|[a-zA-Z]\))\s+", linea))
        es_subtitulo_dos_puntos = linea_limpia.endswith(":") and len(linea_limpia) < 80

        if es_vinieta:
            p.alignment = WD_ALIGN_PARAGRAPH.LEFT
            pf.left_indent = Inches(0.25)
            pf.first_line_indent = Inches(-0.15)
            pf.space_before = Pt(1)
            pf.space_after = Pt(2)
        elif es_enumeracion:
            p.alignment = WD_ALIGN_PARAGRAPH.LEFT
            pf.left_indent = Inches(0.25)
            pf.space_before = Pt(2)
            pf.space_after = Pt(3)
        elif es_subtitulo_dos_puntos:
            p.alignment = WD_ALIGN_PARAGRAPH.LEFT
            pf.space_before = Pt(4)
            pf.space_after = Pt(2)
        else:
            p.alignment = alineacion or WD_ALIGN_PARAGRAPH.JUSTIFY
            pf.space_before = Pt(antes if idx == 0 else 2)
            pf.space_after = Pt(despues if idx == len(lineas) - 1 else 3)
            if sangria:
                pf.first_line_indent = Inches(0.4)

        agregar_texto_enriquecido(
            p,
            linea if not es_vinieta else linea.lstrip(),
            fuente=f_activa,
            tamano=tamano,
            negrita=negrita or (es_subtitulo_dos_puntos and not es_vinieta),
            cursiva=cursiva,
            color=color,
        )
        parrafos_creados.append(p)

    return parrafos_creados[-1] if parrafos_creados else doc.add_paragraph()


def enunciado_formal(
    doc: Any,
    texto_enunciado: str,
    numero: Union[int, str] = 1,
    etiqueta: str = "Enunciado",
    *,
    fuente: Optional[str] = None,
) -> Any:
    """Inserta una consigna o enunciado con presentación editorial limpia sobre el lienzo.

    Evita recuadros de tablas o barras laterales coloreadas, presentando el enunciado
    con sangría de 0.25" y tipografía sobria.
    """
    f_activa = fuente or _fuente_de_doc(doc, "Arial")
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    pf = p.paragraph_format
    pf.left_indent = Inches(0.25)
    pf.space_before = Pt(6)
    pf.space_after = Pt(6)
    pf.line_spacing = 1.15

    etiqueta_limpia = str(etiqueta).rstrip(":").strip()
    num_str = str(numero).strip()
    if num_str.isdigit():
        prefijo = f"{etiqueta_limpia} {num_str}: "
    elif num_str:
        prefijo = f"{num_str}: "
    else:
        prefijo = f"{etiqueta_limpia}: "

    meta = getattr(doc, "_rubric_driven", None)
    tema = meta.get("tema") if isinstance(meta, dict) else None
    col_txt = tema.rgb_texto() if tema is not None else NEGRO

    r_tit = p.add_run(prefijo)
    r_tit.bold = True
    fijar_fuente_run(r_tit, f_activa)
    r_tit.font.size = Pt(10.5)
    r_tit.font.color.rgb = col_txt

    agregar_texto_enriquecido(
        p,
        f"«{texto_enunciado}»",
        fuente=f_activa,
        tamano=10.5,
        cursiva=True,
        color=col_txt,
    )
    return p


def codigo_bloque(
    doc: Any,
    texto: str,
    etiqueta: Optional[str] = None,
    titulo: Optional[str] = None,
    *,
    fuente_pie: Optional[str] = None,
) -> None:
    """Inserta un bloque de código técnico monoespaciado limpio para documentación o verificación."""
    f_pie = fuente_pie or _fuente_de_doc(doc, "Arial")
    pie = etiqueta or titulo
    for linea in texto.split("\n"):
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.LEFT
        pf = p.paragraph_format
        pf.line_spacing = 1.0
        pf.space_before = Pt(0)
        pf.space_after = Pt(0)
        pf.left_indent = Inches(0.4)
        r = p.add_run(linea if linea.strip() else " ")
        _fijar_fuente_run(r, "Courier New")
        r.font.size = Pt(8.5)
        r.font.color.rgb = RGBColor(40, 40, 40)

    if pie:
        p_et = doc.add_paragraph()
        p_et.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_et.paragraph_format.space_before = Pt(2)
        p_et.paragraph_format.space_after = Pt(6)
        r_et = p_et.add_run(pie)
        _fijar_fuente_run(r_et, f_pie)
        r_et.font.size = Pt(8.0)
        r_et.italic = True
        r_et.font.color.rgb = GRIS_TITULO


def tabla_academica(
    doc: Any,
    encabezados: List[str],
    filas: List[List[Any]],
    anchos: Optional[List[float]] = None,
    estilo: Optional[str] = None,
    numero_tabla: Optional[Union[int, str]] = None,
    titulo_tabla: Optional[str] = None,
    nota_pie: Optional[str] = None,
    tamano_cabecera: float = 9.5,
    tamano_cuerpo: float = 9.0,
    *,
    fuente: Optional[str] = None,
    estilo_defecto: Optional[str] = None,
) -> Any:
    """Genera una tabla editorial con layout fijo (w:tblLayout='fixed') y anchos proporcionales."""
    try:
        from plantillas.visual import resolver_estilo_tabla, tabla_estilizada
    except ImportError:
        from visual import resolver_estilo_tabla, tabla_estilizada  # type: ignore[no-redef]

    f_activa = fuente or _fuente_de_doc(doc, "Arial")
    defecto_activo = estilo_defecto or _estilo_tabla_de_doc(doc, "grid")
    estilo_resuelto = resolver_estilo_tabla(estilo, defecto=defecto_activo)
    return tabla_estilizada(
        doc,
        encabezados=encabezados,
        filas=filas,
        estilo=estilo_resuelto,
        anchos=anchos,
        numero_tabla=numero_tabla,
        titulo_tabla=titulo_tabla,
        nota_pie=nota_pie,
        fuente=f_activa,
        tamano_cabecera=tamano_cabecera,
        tamano_cuerpo=tamano_cuerpo,
    )


def caja_captura_evidencia(
    doc: Any,
    ruta_imagen: Union[str, Path],
    etiqueta_figura: str = "Evidencia Documental",
    ancho: float = 5.6,
    *,
    fuente: Optional[str] = None,
) -> Any:
    """Inserta una figura centrada con pie de figura normalizado e idempotente."""
    ruta = Path(ruta_imagen)
    if not ruta.exists():
        return None

    f_activa = fuente or _fuente_de_doc(doc, "Arial")
    p_img = doc.add_paragraph()
    p_img.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_img.paragraph_format.space_before = Pt(6)
    p_img.paragraph_format.space_after = Pt(2)
    p_img.add_run().add_picture(str(ruta), width=Inches(ancho))

    p_cap = doc.add_paragraph()
    p_cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_cap.paragraph_format.space_before = Pt(0)
    p_cap.paragraph_format.space_after = Pt(6)
    et = str(etiqueta_figura).strip()
    if not re.match(r"^figura\b", et, re.I):
        et = f"Figura: {et}"
    if not et.endswith((".", "!", "?")):
        et = f"{et}."
    r = p_cap.add_run(et)
    _fijar_fuente_run(r, f_activa)
    r.font.size = Pt(8.5)
    r.italic = True
    r.font.color.rgb = GRIS_TITULO
    return p_img


def resumen_ejecutivo(
    doc: Any,
    texto: str,
    palabras_clave: Optional[Sequence[str]] = None,
    *,
    titulo: str = "Resumen",
    fuente: Optional[str] = None,
    tamano: Optional[float] = None,
    espaciado: Optional[float] = None,
    color_titulo: Optional[RGBColor] = None,
) -> Any:
    """Inserta un bloque formal de resumen / abstract con línea opcional de palabras clave."""
    meta = getattr(doc, "_rubric_driven", None)
    tema = meta.get("tema") if isinstance(meta, dict) else None
    f_activa = fuente or (str(tema.fuente) if tema is not None and getattr(tema, "fuente", None) else "Arial")
    tam_activo = tamano if tamano is not None else (float(tema.tamano_cuerpo) if tema is not None else 11.0)
    esp_activo = espaciado if espaciado is not None else (float(tema.interlineado) if tema is not None else 1.15)
    col_tit = color_titulo if color_titulo is not None else (tema.rgb_primario() if tema is not None else NEGRO)
    col_txt = tema.rgb_texto() if tema is not None else NEGRO

    p_tit = doc.add_paragraph()
    p_tit.alignment = WD_ALIGN_PARAGRAPH.LEFT
    p_tit.paragraph_format.space_before = Pt(8)
    p_tit.paragraph_format.space_after = Pt(4)
    p_tit.paragraph_format.keep_with_next = True
    r_tit = p_tit.add_run(titulo)
    r_tit.bold = True
    _fijar_fuente_run(r_tit, f_activa)
    r_tit.font.size = Pt(tam_activo + 1)
    r_tit.font.color.rgb = col_tit

    p_body = parrafo_estructurado(
        doc,
        texto,
        fuente=f_activa,
        tamano=tam_activo,
        espaciado=esp_activo,
        despues=4,
        color=col_txt,
    )

    if palabras_clave:
        p_kw = doc.add_paragraph()
        p_kw.alignment = WD_ALIGN_PARAGRAPH.LEFT
        p_kw.paragraph_format.space_before = Pt(2)
        p_kw.paragraph_format.space_after = Pt(8)
        r_lbl = p_kw.add_run("Palabras clave: ")
        r_lbl.bold = True
        r_lbl.italic = True
        _fijar_fuente_run(r_lbl, f_activa)
        r_lbl.font.size = Pt(tam_activo - 0.5)
        r_lbl.font.color.rgb = GRIS_OSCURO
        r_val = p_kw.add_run(", ".join(palabras_clave) + ".")
        r_val.italic = True
        _fijar_fuente_run(r_val, f_activa)
        r_val.font.size = Pt(tam_activo - 0.5)
        r_val.font.color.rgb = GRIS_OSCURO

    return p_body


def insertar_indice_automatico(
    doc: Any,
    *,
    titulo: str = "Tabla de Contenidos",
    niveles: str = "1-3",
    fuente: Optional[str] = None,
    salto_despues: bool = True,
) -> Any:
    """Inserta un campo nativo TOC de Word y habilita la actualización automática al abrir."""
    meta = getattr(doc, "_rubric_driven", None)
    tema = meta.get("tema") if isinstance(meta, dict) else None
    f_activa = fuente or _fuente_de_doc(doc, "Arial")
    col_tit = tema.rgb_primario() if tema is not None else NEGRO
    p_tit = doc.add_paragraph()
    p_tit.alignment = WD_ALIGN_PARAGRAPH.LEFT
    p_tit.paragraph_format.space_before = Pt(4)
    p_tit.paragraph_format.space_after = Pt(8)
    p_tit.paragraph_format.keep_with_next = True
    r_tit = p_tit.add_run(titulo)
    r_tit.bold = True
    fijar_fuente_run(r_tit, f_activa)
    r_tit.font.size = Pt(13)
    r_tit.font.color.rgb = col_tit

    p_toc = doc.add_paragraph()
    run = p_toc.add_run()
    _fijar_fuente_run(run, f_activa)
    fld_begin = OxmlElement("w:fldChar")
    fld_begin.set(qn("w:fldCharType"), "begin")
    fld_begin.set(qn("w:dirty"), "true")
    instr = OxmlElement("w:instrText")
    instr.set(qn("xml:space"), "preserve")
    instr.text = f' TOC \\o "{niveles}" \\h \\z \\u '
    fld_sep = OxmlElement("w:fldChar")
    fld_sep.set(qn("w:fldCharType"), "separate")
    t_prev = OxmlElement("w:t")
    t_prev.text = "Actualiza el índice: clic derecho -> Actualizar campo (F9)."
    fld_end = OxmlElement("w:fldChar")
    fld_end.set(qn("w:fldCharType"), "end")
    run._r.append(fld_begin)
    run._r.append(instr)
    run._r.append(fld_sep)
    run._r.append(t_prev)
    run._r.append(fld_end)

    doc.__dict__.setdefault("_rubric_driven", {})["indice"] = run

    # Marcar actualización automática de campos al abrir el archivo en Word/LibreOffice
    settings = doc.settings.element
    if settings.find(qn("w:updateFields")) is None:
        uf = OxmlElement("w:updateFields")
        uf.set(qn("w:val"), "true")
        settings.append(uf)

    if salto_despues:
        doc.add_page_break()

    return p_toc


def rellenar_indice(doc: Any) -> None:
    """Rellena los encabezados Heading 1-3 como contenido provisional del campo TOC.

    Word recalcula el campo con números de página al abrir el archivo; LibreOffice
    headless no recalcula TOC al exportar a PDF, por lo que esta población previa
    garantiza que el PDF nunca muestre un índice en blanco.
    """
    run = doc.__dict__.get("_rubric_driven", {}).get("indice")
    if run is None:
        return
    entradas: List[str] = []
    for p in doc.paragraphs:
        st_name = p.style.name if p.style else ""
        m = re.fullmatch(r"Heading (\d)", st_name or "")
        if m and p.text.strip():
            entradas.append("    " * (int(m[1]) - 1) + p.text.strip())
    r = run._r
    fin = r[-1]
    for el in list(r):
        if el.tag in (qn("w:t"), qn("w:br")):
            r.remove(el)
    posicion = list(r).index(fin)
    nuevos = []
    for i, entrada in enumerate(entradas or ["(sin encabezados)"]):
        if i:
            nuevos.append(OxmlElement("w:br"))
        t = OxmlElement("w:t")
        t.set(qn("xml:space"), "preserve")
        t.text = entrada
        nuevos.append(t)
    for desplazamiento, el in enumerate(nuevos):
        r.insert(posicion + desplazamiento, el)


def aplicar_metadatos(
    doc: Any,
    *,
    titulo: Optional[str] = None,
    autor: Optional[str] = None,
    asunto: Optional[str] = None,
    palabras_clave: Optional[Sequence[str]] = None,
    comentarios: Optional[str] = None,
) -> None:
    """Aplica metadatos estándar OpenXML (Core Properties) al documento."""
    props = doc.core_properties
    if titulo:
        props.title = titulo
    if autor:
        props.author = autor
    if asunto:
        props.subject = asunto
    if palabras_clave:
        props.keywords = ", ".join(palabras_clave)
    if comentarios:
        props.comments = comentarios
