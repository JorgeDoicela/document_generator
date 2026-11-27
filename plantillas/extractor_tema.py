# -*- coding: utf-8 -*-
"""Extractor automático de temas documentales desde archivos .docx de referencia.

Inspecciona el OpenXML de cualquier documento Word (plantilla universitaria, guía
docente o informe corporativo) para inferir márgenes, tipografía, interlineado,
paleta cromática, estilo de tablas e imágenes embebidas (membrete de encabezado,
logo de portada y banner inferior), generando un archivo `theme.json` reutilizable
por `MotorInstitucional` y `temas.cargar_tema()`.
"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, List, Optional, Tuple

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import temas
else:
    from . import temas

_A_NS = "http://schemas.openxmlformats.org/drawingml/2006/main"
_R_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
_W_BLIP = f"{{{_A_NS}}}blip"
_R_EMBED = f"{{{_R_NS}}}embed"

_EXTENSIONES_MIME = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/gif": ".gif",
    "image/bmp": ".bmp",
    "image/webp": ".webp",
}


@dataclass
class ResultadoExtraccion:
    """Resultado estructurado de la extracción de un tema desde un .docx."""

    ruta_json: Path
    tema: temas.TemaDocumental
    imagenes_extraidas: List[Path] = field(default_factory=list)
    detalles: List[str] = field(default_factory=list)


def _es_color_acento(hex_color: str) -> bool:
    """Devuelve True si el color hexadecimal no es negro puro, blanco puro ni gris neutro."""
    h = hex_color.lstrip("#").upper()
    if len(h) != 6 or not re.fullmatch(r"[0-9A-F]{6}", h):
        return False
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    # Descartar blancos, negros y grises muy neutros
    if max(r, g, b) < 35 or min(r, g, b) > 225:
        return False
    if max(r, g, b) - min(r, g, b) < 25:
        return False
    return True


def _color_hex_de_font(font: Any) -> Optional[str]:
    if font is None or font.color is None:
        return None
    rgb = font.color.rgb
    if rgb is None:
        return None
    return f"#{str(rgb).upper()}"


def _tamano_pt(val: Any) -> Optional[float]:
    if val is None:
        return None
    pt = getattr(val, "pt", None)
    if pt is None:
        return None
    return round(float(pt), 1)


def _margen_pulgadas(val: Any, defecto: float) -> float:
    if val is None:
        return defecto
    pulg = getattr(val, "inches", None)
    if pulg is None:
        return defecto
    valor = round(float(pulg), 2)
    return valor if 0.25 <= valor <= 2.5 else defecto


def _relacion_aspecto_imagen(datos: bytes) -> Optional[float]:
    """Devuelve ancho/alto usando Pillow para distinguir logos cuadrados de banners anchos."""
    try:
        import io

        from PIL import Image

        with Image.open(io.BytesIO(datos)) as img:
            w, h = img.size
            return (w / h) if h > 0 else None
    except Exception:
        return None


def _extraer_blips_de_elemento(el: Any, part: Any) -> List[Tuple[bytes, str]]:
    """Extrae pares (bytes_imagen, extension) de todos los nodos <a:blip> de un subárbol XML."""
    salida: List[Tuple[bytes, str]] = []
    vistos: set[str] = set()
    for blip in el.iter(_W_BLIP):
        rid = blip.get(_R_EMBED)
        if not rid or rid in vistos or rid not in part.rels:
            continue
        vistos.add(rid)
        rel = part.rels[rid]
        target = getattr(rel, "target_part", None)
        if target is None:
            continue
        blob = getattr(target, "blob", None)
        if not blob:
            continue
        ctype = str(getattr(target, "content_type", "")).lower()
        ext = _EXTENSIONES_MIME.get(ctype)
        if not ext:
            partname = str(getattr(target, "partname", ""))
            suf = Path(partname).suffix.lower()
            ext = suf if suf in (".png", ".jpg", ".jpeg", ".gif", ".bmp") else ".png"
        salida.append((blob, ext))
    return salida


def _detectar_estilo_tabla(doc: Any) -> str:
    """Detecta si las tablas del documento usan cuadrícula completa (grid) o solo horizontales (apa)."""
    for tabla in doc.tables:
        tbl_pr = tabla._tbl.tblPr
        if tbl_pr is not None:
            bordes = tbl_pr.find(qn("w:tblBorders"))
            if bordes is not None:
                for lado in ("left", "right", "insideV"):
                    el = bordes.find(qn(f"w:{lado}"))
                    if el is not None and el.get(qn("w:val"), "none") not in ("none", "nil"):
                        return "grid"
        for fila in tabla.rows[:2]:
            for celda in fila.cells[:3]:
                tc_pr = celda._tc.tcPr
                if tc_pr is None:
                    continue
                bordes = tc_pr.find(qn("w:tcBorders"))
                if bordes is None:
                    continue
                for lado in ("left", "right"):
                    el = bordes.find(qn(f"w:{lado}"))
                    if el is not None and el.get(qn("w:val"), "none") not in ("none", "nil"):
                        return "grid"
        return "apa"
    return "grid"


def _es_salto_pagina_xml(el: Any) -> bool:
    """Devuelve True si el elemento <w:p> contiene un salto de página explícito."""
    if any(br.get(qn("w:type")) == "page" for br in el.iter(qn("w:br"))):
        return True
    p_pr = el.find(qn("w:pPr"))
    return p_pr is not None and p_pr.find(qn("w:pageBreakBefore")) is not None


def extraer_tema_desde_docx(
    ruta_docx: Path | str,
    nombre: Optional[str] = None,
    *,
    destino: Optional[Path] = None,
    privado: bool = True,
) -> ResultadoExtraccion:
    """Analiza un archivo .docx y genera un tema reusable (`theme.json` + imágenes extraídas)."""
    archivo = Path(ruta_docx).resolve()
    if not archivo.is_file():
        raise FileNotFoundError(f"No existe el archivo .docx: {archivo}")

    slug_base = nombre or archivo.stem
    slug = re.sub(r"[^a-z0-9_-]+", "-", slug_base.strip().lower()).strip("-") or "tema-extraido"

    if destino is None:
        base_dir = temas.DIR_TEMAS_LOCALES if privado else temas.DIR_TEMAS
        carpeta_tema = base_dir / slug
    else:
        carpeta_tema = Path(destino)
    carpeta_tema.mkdir(parents=True, exist_ok=True)

    doc = Document(str(archivo))
    detalles: List[str] = []
    imagenes_extraidas: List[Path] = []

    # 1. Márgenes
    sec = doc.sections[0]
    margen_sup = _margen_pulgadas(sec.top_margin, 0.85)
    margen_inf = _margen_pulgadas(sec.bottom_margin, 0.85)
    margen_izq = _margen_pulgadas(sec.left_margin, 1.0)
    margen_der = _margen_pulgadas(sec.right_margin, 1.0)
    detalles.append(f"Márgenes: sup={margen_sup}\", inf={margen_inf}\", izq={margen_izq}\", der={margen_der}\"")

    # 2. Tipografía e interlineado (estilo Normal + muestreo de runs)
    fuente_normal = None
    tam_normal = None
    interlineado_normal: Optional[float] = None
    espacio_despues: Optional[float] = None
    try:
        normal = doc.styles["Normal"]
        fuente_normal = normal.font.name if normal.font and normal.font.name else None
        tam_normal = _tamano_pt(normal.font.size) if normal.font else None
        if normal.paragraph_format and isinstance(normal.paragraph_format.line_spacing, (int, float)):
            ls = float(normal.paragraph_format.line_spacing)
            if 0.9 <= ls <= 2.5:
                interlineado_normal = round(ls, 2)
        espacio_despues = _tamano_pt(normal.paragraph_format.space_after) if normal.paragraph_format else None
    except KeyError:
        pass
    if espacio_despues is None:
        espacio_despues = 6.0

    fuentes_runs: Counter[str] = Counter()
    tams_runs: Counter[float] = Counter()
    interlineados_p: Counter[float] = Counter()
    colores_acento: Counter[str] = Counter()
    h1_centrado = False
    sangria_primera_linea = False

    for p in doc.paragraphs[:120]:
        st_name = p.style.name if p.style else ""
        if st_name == "Heading 1" and p.alignment == WD_ALIGN_PARAGRAPH.CENTER:
            h1_centrado = True
        if p.paragraph_format and isinstance(p.paragraph_format.line_spacing, (int, float)):
            ls_p = float(p.paragraph_format.line_spacing)
            if 0.9 <= ls_p <= 2.5 and p.text.strip():
                interlineados_p[round(ls_p, 2)] += 1
        if (
            st_name == "Normal"
            and p.paragraph_format
            and p.paragraph_format.first_line_indent
            and getattr(p.paragraph_format.first_line_indent, "inches", 0) >= 0.35
        ):
            sangria_primera_linea = True

        for r in p.runs:
            txt = r.text.strip()
            if not txt:
                continue
            peso = min(len(txt), 80)
            if r.font.name:
                fuentes_runs[r.font.name] += peso
            tam_r = _tamano_pt(r.font.size)
            if tam_r and 8.5 <= tam_r <= 13.0:
                tams_runs[tam_r] += peso
            col_r = _color_hex_de_font(r.font)
            if col_r and _es_color_acento(col_r):
                # Priorizar colores en títulos o textos destacados
                boost = 5 if (st_name.startswith("Heading") or (tam_r and tam_r >= 13.0) or r.bold) else 1
                colores_acento[col_r] += boost

    fuente = fuentes_runs.most_common(1)[0][0] if fuentes_runs else (fuente_normal or "Arial")
    tam_cuerpo = tams_runs.most_common(1)[0][0] if tams_runs else (tam_normal or 11.0)
    interlineado = (
        interlineado_normal
        if interlineado_normal is not None
        else (interlineados_p.most_common(1)[0][0] if interlineados_p else 1.15)
    )
    detalles.append(f"Tipografía cuerpo: {fuente} {tam_cuerpo} pt (interlineado {interlineado})")

    # 3. Color primario y tamaños de encabezados
    # Priorizar colores de acento usados realmente en los runs (títulos/portada)
    # sobre el color heredado del estilo Heading 1 por defecto de Word (#365F91 / #2F5496).
    color_primario = colores_acento.most_common(1)[0][0] if colores_acento else "#1B365D"
    tam_h1, tam_h2, tam_h3 = max(tam_cuerpo + 2.0, 12.0), max(tam_cuerpo + 0.5, 11.0), tam_cuerpo
    try:
        h1 = doc.styles["Heading 1"]
        col_h1 = _color_hex_de_font(h1.font)
        if not colores_acento and col_h1 and _es_color_acento(col_h1):
            color_primario = col_h1
        tam_h1 = _tamano_pt(h1.font.size) or tam_h1
        if h1.paragraph_format and h1.paragraph_format.alignment == WD_ALIGN_PARAGRAPH.CENTER:
            h1_centrado = True
    except KeyError:
        pass
    try:
        tam_h2 = _tamano_pt(doc.styles["Heading 2"].font.size) or tam_h2
    except KeyError:
        pass
    try:
        tam_h3 = _tamano_pt(doc.styles["Heading 3"].font.size) or tam_h3
    except KeyError:
        pass
    detalles.append(f"Color primario detectado: {color_primario}")

    # 4. Estilo de tablas
    estilo_tabla = _detectar_estilo_tabla(doc)
    detalles.append(f"Estilo de tabla inferido: {estilo_tabla}")

    # 5. Encabezado (imagen o texto)
    imagen_encabezado: Optional[str] = None
    encabezado_texto = ""
    for hdr in (sec.header, sec.first_page_header):
        if hdr is None:
            continue
        blips_hdr = _extraer_blips_de_elemento(hdr._element, hdr.part)
        if blips_hdr and not imagen_encabezado:
            blob, ext = blips_hdr[0]
            dest_img = carpeta_tema / f"header{ext}"
            dest_img.write_bytes(blob)
            imagen_encabezado = dest_img.name
            imagenes_extraidas.append(dest_img)
            detalles.append(f"Imagen de encabezado extraída: {dest_img.name}")
            break
        if not encabezado_texto:
            txt_hdr = " ".join(p.text.strip() for p in hdr.paragraphs if p.text.strip()).strip()
            if txt_hdr:
                encabezado_texto = txt_hdr[:120]

    # 5b. Pie de página (texto descriptivo, excluyendo números de página)
    pie_texto = ""
    for ftr in (sec.footer, sec.first_page_footer):
        if ftr is None:
            continue
        txt_ftr = " ".join(p.text.strip() for p in ftr.paragraphs if p.text.strip()).strip()
        txt_ftr = re.sub(r"\s*\|\s*$", "", txt_ftr).strip()
        if txt_ftr and not txt_ftr.isdigit():
            pie_texto = txt_ftr[:120]
            break

    # 6. Imágenes de portada (en párrafos o tablas antes del primer salto de página o primeros 25 bloques)
    logo_portada: Optional[str] = None
    banner_inferior: Optional[str] = None
    imgs_portada: List[Tuple[bytes, str]] = []
    bloques_portada = 0
    for child in doc.element.body.iterchildren():
        if bloques_portada > 25:
            break
        if child.tag in (qn("w:p"), qn("w:tbl")):
            bloques_portada += 1
            imgs_portada.extend(_extraer_blips_de_elemento(child, doc.part))
            if child.tag == qn("w:p") and _es_salto_pagina_xml(child):
                break

    if len(imgs_portada) == 1:
        blob, ext = imgs_portada[0]
        ratio = _relacion_aspecto_imagen(blob)
        if ratio is not None and ratio >= 2.8:
            dest_img = carpeta_tema / f"banner_inferior{ext}"
            dest_img.write_bytes(blob)
            banner_inferior = dest_img.name
            imagenes_extraidas.append(dest_img)
            detalles.append(f"Banner inferior extraído: {dest_img.name}")
        else:
            dest_img = carpeta_tema / f"logo_portada{ext}"
            dest_img.write_bytes(blob)
            logo_portada = dest_img.name
            imagenes_extraidas.append(dest_img)
            detalles.append(f"Logo de portada extraído: {dest_img.name}")
    elif len(imgs_portada) >= 2:
        blob_top, ext_top = imgs_portada[0]
        dest_top = carpeta_tema / f"logo_portada{ext_top}"
        dest_top.write_bytes(blob_top)
        logo_portada = dest_top.name
        imagenes_extraidas.append(dest_top)
        detalles.append(f"Logo de portada extraído: {dest_top.name}")

        blob_bot, ext_bot = imgs_portada[-1]
        dest_bot = carpeta_tema / f"banner_inferior{ext_bot}"
        dest_bot.write_bytes(blob_bot)
        banner_inferior = dest_bot.name
        imagenes_extraidas.append(dest_bot)
        detalles.append(f"Banner inferior extraído: {dest_bot.name}")

    # 7. Escribir theme.json y cargar como TemaDocumental validado
    datos_json = {
        "nombre": slug,
        "hereda": "academico",
        "descripcion": f"Tema extraído automáticamente desde {archivo.name}.",
        "fuente": fuente,
        "tamano_cuerpo": tam_cuerpo,
        "tamano_h1": tam_h1,
        "tamano_h2": tam_h2,
        "tamano_h3": tam_h3,
        "interlineado": interlineado,
        "espacio_despues": espacio_despues,
        "sangria_primera_linea": sangria_primera_linea,
        "h1_centrado": h1_centrado,
        "margen_sup": margen_sup,
        "margen_inf": margen_inf,
        "margen_izq": margen_izq,
        "margen_der": margen_der,
        "color_primario": color_primario,
        "color_texto": "#141414",
        "color_secundario": "#69737D",
        "estilo_tabla": estilo_tabla,
        "encabezado_texto": encabezado_texto,
        "pie_texto": pie_texto,
        "logo_portada": logo_portada,
        "banner_inferior": banner_inferior,
        "imagen_encabezado": imagen_encabezado,
    }
    ruta_json = carpeta_tema / "theme.json"
    ruta_json.write_text(json.dumps(datos_json, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    tema_cargado = temas.cargar_tema(ruta_json)

    return ResultadoExtraccion(
        ruta_json=ruta_json,
        tema=tema_cargado,
        imagenes_extraidas=imagenes_extraidas,
        detalles=detalles,
    )
