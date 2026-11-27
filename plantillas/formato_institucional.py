# -*- coding: utf-8 -*-
"""Motor Documental Institucional y Multi-Propósito configurable por temas.

Permite generar informes académicos, técnicos/RFC, ejecutivos, artículos estilo IEEE
o documentos con identidad corporativa/universitaria propia mediante objetos
TemaDocumental (presets integrados o archivos theme.json).
"""
import datetime
import re
import sys
from pathlib import Path
from typing import Any, List, Optional, Sequence, Union

from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import bloques
    import config
    import omml
    import temas
    from motor_base import (
        PREFIJO_MARCA,
        SUFIJO_TRANSVERSAL,
        marcar_elemento,
        normalizar_criterios,
        registrar_motor,
    )
else:
    from . import bloques, config, omml, temas
    from .motor_base import (
        PREFIJO_MARCA,
        SUFIJO_TRANSVERSAL,
        marcar_elemento,
        normalizar_criterios,
        registrar_motor,
    )

TemaRef = Union[str, Path, temas.TemaDocumental]


def _tema_de_doc(doc: Any, tema: Optional[TemaRef] = None) -> temas.TemaDocumental:
    if tema is not None:
        return temas.cargar_tema(tema)
    meta = getattr(doc, "_rubric_driven", None)
    if isinstance(meta, dict) and isinstance(meta.get("tema"), temas.TemaDocumental):
        return meta["tema"]
    return temas.cargar_tema("academico")


def _set_numero_pagina(parrafo: Any, tema: temas.TemaDocumental) -> None:
    """Inserta campo nativo de Word PAGE con texto opcional de pie de página."""
    parrafo.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    if tema.pie_texto:
        r_txt = parrafo.add_run(f"{tema.pie_texto}   |   ")
        bloques.fijar_fuente_run(r_txt, tema.fuente)
        r_txt.font.size = Pt(9.0)
        r_txt.font.color.rgb = tema.rgb_secundario()

    run = parrafo.add_run()
    for _instr, tipo in ((None, "begin"), ("PAGE", "instrText"), (None, "separate"), (None, "end")):
        el = OxmlElement("w:fldChar") if tipo != "instrText" else OxmlElement("w:instrText")
        if tipo == "instrText":
            el.set(qn("xml:space"), "preserve")
            el.text = " PAGE "
        else:
            el.set(qn("w:fldCharType"), tipo)
            if tipo == "begin":
                el.set(qn("w:dirty"), "true")
        run._r.append(el)
    bloques.fijar_fuente_run(run, tema.fuente)
    run.font.size = Pt(9.5)
    run.font.color.rgb = tema.rgb_secundario()


def _aplicar_estilos_base(doc: Any, t: temas.TemaDocumental) -> None:
    """Sincroniza los estilos nativos de Word (Normal, Heading 1..3, List Bullet) con el tema."""
    def _fijar_rfonts(rpr: Any, nombre: str) -> None:
        for viejo in rpr.findall(qn("w:rFonts")):
            rpr.remove(viejo)
        fuentes = OxmlElement("w:rFonts")
        for attr in ("w:ascii", "w:hAnsi", "w:eastAsia", "w:cs"):
            fuentes.set(qn(attr), nombre)
        rpr.insert(0, fuentes)

    if "Normal" in doc.styles:
        normal = doc.styles["Normal"]
        normal.font.name = t.fuente
        normal.font.size = Pt(t.tamano_cuerpo)
        normal.font.color.rgb = t.rgb_texto()
        rpr_normal = normal.element.get_or_add_rPr()
        _fijar_rfonts(rpr_normal, t.fuente)
        for viejo_lang in rpr_normal.findall(qn("w:lang")):
            rpr_normal.remove(viejo_lang)
        lang_el = OxmlElement("w:lang")
        for attr in ("w:val", "w:eastAsia", "w:bidi"):
            lang_el.set(qn(attr), "es-ES")
        rpr_normal.append(lang_el)
        normal.paragraph_format.line_spacing = t.interlineado
        normal.paragraph_format.space_after = Pt(t.espacio_despues)

    tams_h = {1: t.tamano_h1, 2: t.tamano_h2, 3: t.tamano_h3}
    for nivel in (1, 2, 3):
        clave = f"Heading {nivel}"
        if clave not in doc.styles:
            continue
        est = doc.styles[clave]
        est.font.name = t.fuente
        est.font.size = Pt(tams_h[nivel])
        est.font.bold = True
        est.font.italic = (nivel == 3)
        est.font.color.rgb = t.rgb_primario() if nivel == 1 else t.rgb_texto()
        _fijar_rfonts(est.element.get_or_add_rPr(), t.fuente)
        pf = est.paragraph_format
        pf.alignment = WD_ALIGN_PARAGRAPH.CENTER if (nivel == 1 and t.h1_centrado) else WD_ALIGN_PARAGRAPH.LEFT
        pf.line_spacing = t.interlineado
        pf.space_before = Pt(12 if nivel == 1 else 10)
        pf.space_after = Pt(4)
        pf.keep_with_next = True
        pf.first_line_indent = Inches(0)

    if "List Bullet" in doc.styles:
        vinietas = doc.styles["List Bullet"]
        vinietas.font.name = t.fuente
        vinietas.font.color.rgb = t.rgb_texto()


def configurar_pagina(
    doc: Any,
    tema: TemaRef = "academico",
    imagen_header: Optional[Path] = None,
) -> Any:
    """Configura estilos base, márgenes, encabezado y pie de página de forma idempotente según el tema."""
    t = temas.cargar_tema(tema)
    doc.__dict__.setdefault("_rubric_driven", {})["tema"] = t
    _aplicar_estilos_base(doc, t)

    sec = doc.sections[0]
    sec.top_margin = Inches(t.margen_sup)
    sec.bottom_margin = Inches(t.margen_inf)
    sec.left_margin = Inches(t.margen_izq)
    sec.right_margin = Inches(t.margen_der)
    sec.different_first_page_header_footer = True

    header_p = sec.header.paragraphs[0]
    header_p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    header_p.paragraph_format.space_after = Pt(4)
    for r in list(header_p.runs):
        p_el = r._r.getparent()
        if p_el is not None:
            p_el.remove(r._r)

    img = imagen_header or t.resolver_activo(t.imagen_encabezado)
    if img and img.exists():
        header_p.add_run().add_picture(str(img), width=Inches(1.15))
    elif t.encabezado_texto:
        r_h = header_p.add_run(t.encabezado_texto)
        bloques.fijar_fuente_run(r_h, t.fuente)
        r_h.font.size = Pt(8.5)
        r_h.font.color.rgb = t.rgb_secundario()

    footer_p = sec.footer.paragraphs[0]
    footer_p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    for r in list(footer_p.runs):
        p_el = r._r.getparent()
        if p_el is not None:
            p_el.remove(r._r)
    _set_numero_pagina(footer_p, t)
    return doc


def aplicar_portada(
    doc: Any,
    *,
    titulo: str,
    subtitulo: str = "",
    tema: TemaRef = "academico",
    institucion: Optional[str] = None,
    organizacion: Optional[str] = None,
    docente: Optional[str] = None,
    periodo: Optional[str] = None,
    modalidad: Optional[str] = None,
    grupo: Optional[str] = None,
    integrantes: Optional[Union[str, Sequence[str]]] = None,
    tarea: Optional[Union[Path, str]] = None,
    espacio_superior: int = 90,
    espacio_inferior: int = 80,
) -> Any:
    """Construye una portada formal alineada al tema (individual, grupal o corporativa)."""
    t = temas.cargar_tema(tema)
    cfg: dict[str, str] = {}
    try:
        cfg = config.cargar()
    except Exception:
        pass

    if tarea is not None:
        try:
            if __package__ in (None, ""):
                import ficha
            else:
                from . import ficha
            t_obj = ficha.leer_tarea(Path(tarea))
            if docente is None and t_obj.materia.docente:
                docente = t_obj.materia.docente
            if modalidad is None:
                modalidad = t_obj.modalidad
            if grupo is None:
                grupo = t_obj.grupo
            if integrantes is None and t_obj.integrantes:
                integrantes = t_obj.integrantes
        except Exception:
            pass

    if grupo and grupo.strip().lower() in ("n/a", "na", "ninguno", "ninguna", "-", "no aplica", "none"):
        grupo = None

    lista_integrantes: List[str] = []
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
        if es_grupal and cfg.get("INTEGRANTES_DEFECTO"):
            lista_integrantes = [i.strip() for i in cfg["INTEGRANTES_DEFECTO"].split(",") if i.strip()]
        elif cfg.get("NOMBRE_ESTUDIANTE"):
            nombre_env = cfg["NOMBRE_ESTUDIANTE"]
            if es_grupal and "," in nombre_env:
                lista_integrantes = [i.strip() for i in nombre_env.split(",") if i.strip()]
            else:
                lista_integrantes = [nombre_env]
        else:
            lista_integrantes = ["Autor"]

    configurar_pagina(doc, tema=t)

    # Logo o encabezado visual de portada (prioriza logo_portada sobre imagen_encabezado)
    img_logo = t.resolver_activo(t.logo_portada) or t.resolver_activo(t.imagen_encabezado)
    p_top = doc.add_paragraph()
    p_top.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    p_top.paragraph_format.space_after = Pt(espacio_superior)
    if img_logo and img_logo.exists():
        p_top.add_run().add_picture(str(img_logo), width=Inches(1.25))

    if subtitulo:
        p_sub = doc.add_paragraph()
        p_sub.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        p_sub.paragraph_format.space_after = Pt(2)
        r_sub = p_sub.add_run(subtitulo.upper())
        bloques.fijar_fuente_run(r_sub, t.fuente)
        r_sub.font.size = Pt(15)
        r_sub.font.color.rgb = t.rgb_secundario()

    p_tit = doc.add_paragraph()
    p_tit.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    p_tit.paragraph_format.space_after = Pt(28)
    r_tit = p_tit.add_run(titulo)
    r_tit.bold = True
    bloques.fijar_fuente_run(r_tit, t.fuente)
    r_tit.font.size = Pt(26)
    r_tit.font.color.rgb = t.rgb_primario()

    p_lbl = doc.add_paragraph()
    p_lbl.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    p_lbl.paragraph_format.space_after = Pt(4)
    if es_grupal:
        etiqueta_autor = f"{(grupo or 'GRUPO DE TRABAJO').upper()} — INTEGRANTES:"
    else:
        etiqueta_autor = "ESTUDIANTE:" if (t.nombre in ("academico", "apa7") or tarea is not None) else "AUTOR:"

    r_g = p_lbl.add_run(etiqueta_autor)
    r_g.bold = True
    bloques.fijar_fuente_run(r_g, t.fuente)
    r_g.font.size = Pt(10.5)
    r_g.font.color.rgb = t.rgb_texto()

    p_nom = doc.add_paragraph()
    p_nom.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    p_nom.paragraph_format.line_spacing = 1.2
    p_nom.paragraph_format.space_after = Pt(14)
    r_nom = p_nom.add_run("\n".join(lista_integrantes if es_grupal else lista_integrantes[:1]))
    bloques.fijar_fuente_run(r_nom, t.fuente)
    r_nom.font.size = Pt(10)
    r_nom.font.color.rgb = t.rgb_texto()

    inst_final = institucion or cfg.get("INSTITUCION", "")
    org_final = organizacion or cfg.get("CARRERA", "")
    doc_final = f"Docente: {docente}" if docente else ""
    per_final = periodo or f"Periodo {datetime.date.today().year}"
    lineas_pie = [x for x in (doc_final, org_final, inst_final, per_final) if x]

    p_pie = doc.add_paragraph()
    p_pie.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    p_pie.paragraph_format.space_after = Pt(20 if t.resolver_activo(t.banner_inferior) else espacio_inferior)
    r_pie = p_pie.add_run("\n".join(lineas_pie))
    bloques.fijar_fuente_run(r_pie, t.fuente)
    r_pie.font.size = Pt(9.5)
    r_pie.font.color.rgb = t.rgb_secundario()

    img_banner = t.resolver_activo(t.banner_inferior)
    if img_banner and img_banner.exists():
        p_ban = doc.add_paragraph()
        p_ban.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_ban.paragraph_format.space_before = Pt(12)
        p_ban.paragraph_format.space_after = Pt(0)
        p_ban.add_run().add_picture(str(img_banner), width=Inches(5.8))

    bloques.aplicar_metadatos(
        doc,
        titulo=titulo,
        autor=", ".join(lista_integrantes),
        asunto=subtitulo or inst_final,
    )

    doc.add_page_break()
    return doc


def titulo_seccion(
    doc: Any,
    texto: str,
    nivel: int = 1,
    criterios: Optional[Union[str, List[str]]] = None,
    *,
    tema: Optional[TemaRef] = None,
    antes: int = 12,
    despues: int = 4,
) -> Any:
    """Inserta un encabezado Word Heading N con estilo del tema y marcadores XML de rúbrica."""
    t = _tema_de_doc(doc, tema)
    nivel = min(max(int(nivel), 1), 3)
    p = doc.add_paragraph(style=f"Heading {nivel}")
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER if (nivel == 1 and t.h1_centrado) else WD_ALIGN_PARAGRAPH.LEFT
    pf = p.paragraph_format
    pf.line_spacing = t.interlineado
    pf.space_before = Pt(antes)
    pf.space_after = Pt(despues)
    pf.keep_with_next = True

    texto_limpio = re.sub(r"\*\*\*([^*]+?)\*\*\*", r"\1", str(texto))
    texto_limpio = re.sub(r"\*\*([^*]+?)\*\*", r"\1", texto_limpio)
    texto_limpio = re.sub(r"\*(?!\s)([^*]+?)(?<!\s)\*", r"\1", texto_limpio)

    r = p.add_run(texto_limpio)
    r.bold = True
    bloques._fijar_fuente_run(r, t.fuente)

    if nivel == 1:
        r.font.size = Pt(t.tamano_h1)
        r.font.color.rgb = t.rgb_primario()
    elif nivel == 2:
        r.font.size = Pt(t.tamano_h2)
        r.font.color.rgb = t.rgb_texto()
    else:
        r.font.size = Pt(t.tamano_h3)
        r.font.color.rgb = t.rgb_texto()
        r.italic = True

    if criterios:
        for c in normalizar_criterios(criterios):
            marcar_elemento(p, PREFIJO_MARCA + c)
    return p


def marcar_transversal(doc: Any, *criterios: str) -> None:
    """Inyecta marcadores de criterios transversales en el último párrafo del documento."""
    if not doc.paragraphs:
        doc.add_paragraph()
    p = doc.paragraphs[-1]
    for c in normalizar_criterios(list(criterios)):
        marcar_elemento(p, PREFIJO_MARCA + c + SUFIJO_TRANSVERSAL)


def parrafo(doc: Any, texto: str = "", *, tema: Optional[TemaRef] = None, **kwargs: Any) -> Any:
    """Inserta párrafos estructurados heredando tipografía e interlineado del tema activo."""
    t = _tema_de_doc(doc, tema)
    kwargs.setdefault("fuente", t.fuente)
    kwargs.setdefault("tamano", t.tamano_cuerpo)
    kwargs.setdefault("espaciado", t.interlineado)
    kwargs.setdefault("despues", int(t.espacio_despues))
    kwargs.setdefault("sangria", t.sangria_primera_linea)
    kwargs.setdefault("color", t.rgb_texto())
    return bloques.parrafo_estructurado(doc, texto, **kwargs)


def tabla(doc: Any, encabezados: List[str], filas: List[List[Any]], **kwargs: Any) -> Any:
    """Genera una tabla editorial alineada al tema activo (layout fijo + anchos proporcionales)."""
    t = _tema_de_doc(doc)
    kwargs.setdefault("fuente", t.fuente)
    kwargs.setdefault("estilo_defecto", t.estilo_tabla)
    return bloques.tabla_academica(doc, encabezados, filas, **kwargs)


def nuevo_documento_tematico(
    titulo: str,
    subtitulo: str = "",
    *,
    tema: TemaRef = "academico",
    incluir_indice: bool = False,
    **kwargs: Any,
) -> Any:
    """Crea un Document() inicializado con cualquier tema preset o theme.json."""
    from docx import Document

    doc = Document()
    aplicar_portada(doc, titulo=titulo, subtitulo=subtitulo, tema=tema, **kwargs)
    if incluir_indice:
        t = _tema_de_doc(doc)
        bloques.insertar_indice_automatico(doc, fuente=t.fuente)
    return doc


def guardar_documento(doc: Any, salida: Union[Path, str]) -> Path:
    """Rellena el índice provisional (si existe), crea carpetas padre y guarda el .docx."""
    bloques.rellenar_indice(doc)
    destino = Path(salida)
    destino.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(destino))
    return destino


class MotorInstitucional:
    """Motor documental genérico configurable por tema (implementa BaseDocumentEngine)."""

    def __init__(self, tema: TemaRef = "academico") -> None:
        self.tema = temas.cargar_tema(tema)

    def configurar_pagina(self, doc: Any, imagen_header: Optional[Path] = None, **kwargs: Any) -> Any:
        return configurar_pagina(doc, tema=self.tema, imagen_header=imagen_header)

    def titulo_seccion(
        self,
        doc: Any,
        texto: str,
        nivel: int = 1,
        criterios: Optional[Union[str, List[str]]] = None,
        **kwargs: Any,
    ) -> Any:
        return titulo_seccion(doc, texto, nivel=nivel, criterios=criterios, tema=self.tema, **kwargs)

    def marcar_transversal(self, doc: Any, *criterios: str) -> None:
        marcar_transversal(doc, *criterios)


class MotorTecnico(MotorInstitucional):
    """Preset de motor para informes técnicos, laboratorios y especificaciones."""

    def __init__(self) -> None:
        super().__init__(tema="tecnico")


class MotorEjecutivo(MotorInstitucional):
    """Preset de motor para informes ejecutivos, propuestas y memorias corporativas."""

    def __init__(self) -> None:
        super().__init__(tema="ejecutivo")


class MotorIEEE(MotorInstitucional):
    """Preset de motor para artículos científico-técnicos estilo IEEE."""

    def __init__(self) -> None:
        super().__init__(tema="ieee")


registrar_motor("academico", MotorInstitucional)
registrar_motor("institucional", MotorInstitucional)
registrar_motor("tecnico", MotorTecnico)
registrar_motor("ejecutivo", MotorEjecutivo)
registrar_motor("ieee", MotorIEEE)

# Re-exportaciones de conveniencia para scripts que importen solo formato_institucional
formula_bloque = omml.formula_bloque
texto_a_omml = omml.texto_a_omml
normalizar_latex_a_unicode = omml.normalizar_latex_a_unicode
dividir_formula_larga = omml.dividir_formula_larga
enunciado_formal = bloques.enunciado_formal
codigo_bloque = bloques.codigo_bloque
caja_captura_evidencia = bloques.caja_captura_evidencia
resumen_ejecutivo = bloques.resumen_ejecutivo
insertar_indice_automatico = bloques.insertar_indice_automatico
rellenar_indice = bloques.rellenar_indice
aplicar_metadatos = bloques.aplicar_metadatos
tabla_academica = bloques.tabla_academica
tabla_institucional = tabla

if __package__ in (None, ""):
    from apa_docx import Bibliografia, referencias, salto_de_pagina, vinieta
else:
    from .apa_docx import Bibliografia, referencias, salto_de_pagina, vinieta  # noqa: F401
