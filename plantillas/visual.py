# -*- coding: utf-8 -*-
"""Módulo de componentes visuales de alta fidelidad para tareas académicas.

Proporciona renderizado de capturas de terminal (CLI), bloques de código
estilizados para WordML y diagramas técnicos con soporte dual e instantáneo
para temas Dark (Modern) y Light (Academic Paper).
"""
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor
from PIL import Image, ImageDraw, ImageFont

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import plataforma
else:
    from . import plataforma


# ==============================================================================
# 1. PALETAS Y DEFINICIÓN DE TEMAS VISUALES
# ==============================================================================
class Temas:
    DARK = "dark"
    LIGHT = "light"


PALETAS_TERMINAL: Dict[str, Dict[str, Tuple[int, int, int]]] = {
    Temas.DARK: {
        "fondo_tarjeta": (26, 27, 38),       # Tokyo Night / Dark Slate
        "fondo_cabecera": (36, 40, 59),      # Barra superior
        "borde_ventana": (65, 72, 104),      # Borde sutil
        "texto_titulo": (169, 177, 214),     # Título de ventana
        "prompt_host": (122, 162, 247),      # Azul prompt
        "prompt_cmd": (192, 202, 245),       # Comando
        "texto_general": (169, 177, 214),    # Texto normal
        "texto_separador": (65, 72, 104),    # Líneas divisorias
        "texto_banner": (187, 154, 247),     # Púrpura banners
        "texto_entrada": (158, 206, 106),    # Verde entrada usuario
        "texto_exito": (115, 218, 202),      # Turquesa éxito
        "texto_alerta": (247, 118, 142),     # Rojo suave alerta/error
        "texto_clave": (224, 175, 104),      # Naranja variables
        "boton_cerrar": (247, 118, 142),
        "boton_minimizar": (224, 175, 104),
        "boton_maximizar": (158, 206, 106),
    },
    Temas.LIGHT: {
        "fondo_tarjeta": (248, 250, 252),    # Slate 50 (Gris perla)
        "fondo_cabecera": (241, 245, 249),   # Slate 100
        "borde_ventana": (203, 213, 225),    # Slate 300
        "texto_titulo": (71, 85, 105),       # Slate 600
        "prompt_host": (2, 132, 199),        # Sky 600
        "prompt_cmd": (15, 23, 42),          # Slate 900
        "texto_general": (51, 65, 85),       # Slate 700
        "texto_separador": (148, 163, 184),  # Slate 400
        "texto_banner": (124, 58, 237),      # Violet 600
        "texto_entrada": (22, 101, 52),      # Emerald 800
        "texto_exito": (13, 148, 136),       # Teal 600
        "texto_alerta": (225, 29, 72),       # Rose 600
        "texto_clave": (194, 65, 12),        # Amber 700
        "boton_cerrar": (244, 63, 94),
        "boton_minimizar": (245, 158, 11),
        "boton_maximizar": (16, 185, 129),
    },
}


# ==============================================================================
# 2. SANITIZACIÓN ROBUSTA DE SALIDAS (MOJIBAKE Y SECUENCIAS ANSI)
# ==============================================================================
def sanitizar_salida_terminal(raw: Union[bytes, str]) -> List[str]:
    """Limpia mojibake de PSeInt/Linux y erradica secuencias de escape ANSI.

    Resuelve la mezcla histórica donde ejecutables en C (como PSeInt CLI)
    imprimen banners en Latin-1 (0xf3 para 'ó') y el cuerpo en UTF-8.
    """
    if isinstance(raw, bytes):
        # Sustitución de bytes de control y banderas aisladas Latin-1
        b_corregido = raw.replace(b"Ejecuci\xf3n", "Ejecución".encode("utf-8"))
        try:
            texto = b_corregido.decode("utf-8")
        except UnicodeDecodeError:
            try:
                texto = b_corregido.decode("latin-1")
            except Exception:
                texto = b_corregido.decode("utf-8", errors="replace")
    else:
        texto = raw

    # Erradicar secuencias de control ANSI (cursor, colores VT100, clears)
    texto = re.sub(r"\x1b\[[0-9;?]*[a-zA-Z]", "", texto)
    texto = re.sub(r"\[\?25[hl]", "", texto)  # Secuencias residuales [?25h
    texto = re.sub(r"\[[0-9]+;[0-9]+[Hf]", "", texto)

    # Subsanar dobles decodificaciones (mojibake común en terminales)
    reparaciones = {
        "AUTENTICACIÃ N": "AUTENTICACIÓN",
        "AutenticaciÃ³n": "Autenticación",
        "AutenticaciÃ n": "Autenticación",
        "contraseÃ±a": "contraseña",
        "ContraseÃ±a": "Contraseña",
        "Ã XITO": "ÉXITO",
        "Ã‰XITO": "ÉXITO",
        "EjecuciÃ³n": "Ejecución",
        "número": "número",
        "nÃºmero": "número",
    }
    for err, fix in reparaciones.items():
        texto = texto.replace(err, fix)

    lineas = [linea.rstrip("\r\n") for linea in texto.splitlines()]
    # Filtrar avisos de compilación previos no relevantes para la captura de ejecución
    return [linea for linea in lineas if "Leyendo archivo y comprobando sintaxis" not in linea]


# ==============================================================================
# 3. RENDERIZADOR DE TERMINAL MULTI-TEMA (ALTA RESOLUCIÓN RETINA 2X)
# ==============================================================================
def renderizar_terminal(
    titulo_ventana: str,
    comando_mostrado: str,
    salida_lineas: Union[List[str], str, bytes],
    ruta_salida: Union[Path, str],
    *,
    tema: str = Temas.DARK,
    prompt_user: str = "user@workstation:~$ ",
    ancho_logico: int = 900,
    fuente_path: Optional[Path] = None,
) -> Path:
    """Renderiza una captura de consola de alta fidelidad estética.

    Genera a escala 2x con filtro Lanczos para garantizar nitidez tipográfica
    absoluta (antialiasing vectorial) en el documento PDF final.
    """
    if isinstance(salida_lineas, (bytes, str)):
        lineas_procesadas = sanitizar_salida_terminal(salida_lineas)
    else:
        lineas_procesadas = [
            linea for raw_l in salida_lineas for linea in sanitizar_salida_terminal(raw_l)
        ]

    # Normalización del tema (soporte para dark y light)
    modo = Temas.LIGHT if str(tema).lower() in ("light", "claro", "blanco") else Temas.DARK
    paleta = PALETAS_TERMINAL[modo]

    fpath = plataforma.resolver_fuente_monospace(
        fuente_explicita=Path(fuente_path) if fuente_path else None,
    )

    scale = 2  # Super-sampling 2x
    font_size = 14 * scale
    font = ImageFont.truetype(str(fpath), font_size) if fpath else ImageFont.load_default()
    title_font = ImageFont.truetype(str(fpath), 12 * scale) if fpath else font

    header_h = 38 * scale
    line_h = 24 * scale
    pad_x = 24 * scale
    pad_y = 18 * scale

    ancho_px = ancho_logico * scale
    total_lineas = len(lineas_procesadas) + 2  # prompt + espacio + salida
    alto_px = header_h + (total_lineas * line_h) + (pad_y * 2)

    # Lienzo con transparencia para bordes redondeados limpios
    img = Image.new("RGBA", (ancho_px, alto_px), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    radius = 10 * scale

    # Tarjeta redondeada principal
    draw.rounded_rectangle(
        [(0, 0), (ancho_px - 1, alto_px - 1)],
        radius=radius,
        fill=paleta["fondo_tarjeta"],
        outline=paleta["borde_ventana"],
        width=1 * scale,
    )

    # Cabecera redondeada en la parte superior
    draw.rounded_rectangle(
        [(0, 0), (ancho_px - 1, header_h + radius)],
        radius=radius,
        fill=paleta["fondo_cabecera"],
    )
    # Rellenar la unión para que solo la parte superior sea redondeada
    draw.rectangle([(0, header_h), (ancho_px - 1, header_h + radius)], fill=paleta["fondo_tarjeta"])
    draw.line([(0, header_h), (ancho_px - 1, header_h)], fill=paleta["borde_ventana"], width=1 * scale)

    # Botones estilo macOS / GNOME
    btn_r = 5 * scale
    btn_y = header_h // 2
    botones = [
        (18 * scale, paleta["boton_cerrar"]),
        (34 * scale, paleta["boton_minimizar"]),
        (50 * scale, paleta["boton_maximizar"]),
    ]
    for bx, bcol in botones:
        draw.ellipse([(bx - btn_r, btn_y - btn_r), (bx + btn_r, btn_y + btn_r)], fill=bcol)

    # Título centrado en la barra de título
    bbox = draw.textbbox((0, 0), titulo_ventana, font=title_font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    draw.text(
        ((ancho_px - tw) // 2, (header_h - th) // 2),
        titulo_ventana,
        fill=paleta["texto_titulo"],
        font=title_font,
    )

    # Renderizado del prompt inicial
    curr_y = header_h + pad_y
    draw.text((pad_x, curr_y), prompt_user, fill=paleta["prompt_host"], font=font)
    pb = draw.textbbox((0, 0), prompt_user, font=font)
    pw = pb[2] - pb[0]
    draw.text((pad_x + pw, curr_y), comando_mostrado, fill=paleta["prompt_cmd"], font=font)
    curr_y += line_h + (4 * scale)

    # Renderizado inteligente con resaltado sintáctico
    for linea in lineas_procesadas:
        linea_str = linea.rstrip()
        col = paleta["texto_general"]

        if "***" in linea_str:
            col = paleta["texto_banner"]
        elif "===" in linea_str or "---" in linea_str:
            col = paleta["texto_separador"]
        elif linea_str.startswith(">"):
            col = paleta["texto_entrada"]
        elif any(w in linea_str for w in ("ÉXITO", "exitosamente", "Bienvenido", "APROBADO", "ACCESO CONCEDIDO")):
            col = paleta["texto_exito"]
        elif any(w in linea_str for w in ("Error", "DENEGADO", "bloqueó", "REPROBADO", "BLOQUEADO", "Fallido")):
            col = paleta["texto_alerta"]
        elif any(w in linea_str for w in ("Intento", "TABLA", "Promedio", "Mayor", "Menor", "Edad")):
            col = paleta["texto_clave"]

        draw.text((pad_x, curr_y), linea_str, fill=col, font=font)
        curr_y += line_h

    # Redimensionado con filtro Lanczos para antialiasing de alta calidad
    out_img = img.resize((ancho_px // scale, alto_px // scale), Image.Resampling.LANCZOS)

    salida_path = Path(ruta_salida).resolve()
    salida_path.parent.mkdir(parents=True, exist_ok=True)
    out_img.save(str(salida_path), "PNG", optimize=True)
    return salida_path


# ==============================================================================
# 4. BLOQUE DE CÓDIGO ESTILIZADO PARA WORDML (PYTHON-DOCX)
# ==============================================================================
def bloque_codigo_word(
    doc,
    codigo: str,
    *,
    archivo: Optional[str] = None,
    lenguaje: str = "Pseudocódigo",
    tema: str = Temas.LIGHT,
):
    """Inserta en un documento WordML una tabla de código con diseño editorial.

    Incluye barra superior con nombre de archivo, columna de numeración de línea
    y fondo temático adaptado.
    """
    from docx.enum.table import WD_TABLE_ALIGNMENT
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    from docx.shared import Inches, Pt, RGBColor

    modo = Temas.LIGHT if str(tema).lower() in ("light", "claro", "blanco") else Temas.DARK

    if modo == Temas.LIGHT:
        bg_header = "F1F5F9"
        bg_body = "F8FAFC"
        border_col = "CBD5E1"
        txt_header = RGBColor(71, 85, 105)
        txt_code = RGBColor(15, 23, 42)
        txt_num = RGBColor(148, 163, 184)
    else:
        bg_header = "24283B"
        bg_body = "1A1B26"
        border_col = "414868"
        txt_header = RGBColor(169, 177, 214)
        txt_code = RGBColor(192, 202, 245)
        txt_num = RGBColor(86, 95, 137)

    def _set_borde(celda, color=border_col):
        tc_pr = celda._tc.get_or_add_tcPr()
        bordes = OxmlElement("w:tcBorders")
        for lado in ("top", "left", "bottom", "right"):
            el = OxmlElement(f"w:{lado}")
            el.set(qn("w:val"), "single")
            el.set(qn("w:sz"), "4")
            el.set(qn("w:color"), color)
            bordes.append(el)
        tc_pr.append(bordes)

    def _sombrear(celda, hex_color):
        tc_pr = celda._tc.get_or_add_tcPr()
        shd = OxmlElement("w:shd")
        shd.set(qn("w:val"), "clear")
        shd.set(qn("w:color"), "auto")
        shd.set(qn("w:fill"), hex_color)
        tc_pr.append(shd)

    lineas = [linea.rstrip("\r\n") for linea in codigo.strip().splitlines()]
    total_lineas = len(lineas)

    # Tabla de 2 filas: Fila 1 = Header, Fila 2 = Cuerpo de código
    tabla = doc.add_table(rows=2, cols=1)
    tabla.alignment = WD_TABLE_ALIGNMENT.CENTER
    tabla.autofit = False

    # Evitar que la cabecera y el cuerpo del bloque de código se separen entre páginas
    for fila_blk in tabla.rows:
        cant_split = OxmlElement("w:cantSplit")
        cant_split.set(qn("w:val"), "true")
        fila_blk._tr.get_or_add_trPr().append(cant_split)

    # Fila 1: Cabecera con nombre de archivo y lenguaje
    c_head = tabla.rows[0].cells[0]
    c_head.width = Inches(6.5)
    _sombrear(c_head, bg_header)
    _set_borde(c_head)
    p_head = c_head.paragraphs[0]
    p_head.alignment = WD_ALIGN_PARAGRAPH.LEFT
    p_head.paragraph_format.space_before = Pt(4)
    p_head.paragraph_format.space_after = Pt(4)
    p_head.paragraph_format.keep_with_next = True

    etiqueta = f"  {archivo}  [{lenguaje}]" if archivo else f"  [{lenguaje}]"
    r_h = p_head.add_run(etiqueta)
    r_h.font.name = "Consolas"
    r_h.font.size = Pt(9)
    r_h.bold = True
    r_h.font.color.rgb = txt_header

    # Fila 2: Código con números de línea
    c_body = tabla.rows[1].cells[0]
    c_body.width = Inches(6.5)
    _sombrear(c_body, bg_body)
    _set_borde(c_body)

    # Construir texto formateado
    ancho_num = len(str(total_lineas))
    p_body = c_body.paragraphs[0]
    p_body.paragraph_format.space_before = Pt(4)
    p_body.paragraph_format.space_after = Pt(4)
    p_body.paragraph_format.line_spacing = 1.05

    for idx, linea in enumerate(lineas, start=1):
        if idx > 1:
            p_linea = c_body.add_paragraph()
            p_linea.paragraph_format.space_before = Pt(0)
            p_linea.paragraph_format.space_after = Pt(0)
            p_linea.paragraph_format.line_spacing = 1.05
        else:
            p_linea = p_body

        num_str = f" {str(idx).rjust(ancho_num)} │ "
        r_num = p_linea.add_run(num_str)
        r_num.font.name = "Consolas"
        r_num.font.size = Pt(8.5)
        r_num.font.color.rgb = txt_num

        r_code = p_linea.add_run(linea)
        r_code.font.name = "Consolas"
        r_code.font.size = Pt(8.5)
        r_code.font.color.rgb = txt_code

    p_sep = doc.add_paragraph()
    p_sep.paragraph_format.space_before = Pt(2)
    p_sep.paragraph_format.space_after = Pt(4)
    return tabla


# ==============================================================================
# 5. GENERACIÓN Y ESTILIZADO DE TABLAS ACADÉMICAS (APA 7 Y CUADRÍCULA)
# ==============================================================================
class EstilosTabla:
    """Catálogo de estilos formales para tablas académicas e institucionales.

    Opción 1: APA (Norma oficial APA 7.ª ed. - 3 líneas horizontales, cero verticales, fondo blanco).
    Opción 4: GRID (Cuadrícula institucional completa con bordes en todas las celdas y cabecera sombreada).
    """

    APA = "apa"                     # Opción 1: Norma Oficial APA 7
    APA_ESTRICTA = "apa"            # Alias canónico
    GRID = "grid"                   # Opción 4: Cuadrícula institucional completa
    INSTITUCIONAL = "grid"          # Alias institucional
    CUADRICULA = "grid"             # Alias descriptivo


def resolver_estilo_tabla(estilo: Optional[str] = None, defecto: str = EstilosTabla.APA) -> str:
    """Resuelve el estilo de tabla activo entre Opción 1 (APA) y Opción 4 (GRID).

    Prioridad:
    1. Argumento explícito `estilo`.
    2. Variable de entorno `ESTILO_TABLA`.
    3. Valor por defecto (`defecto`, normalmente EstilosTabla.APA o EstilosTabla.GRID).
    """
    val = estilo if estilo is not None else os.environ.get("ESTILO_TABLA", defecto)
    s = str(val).strip().lower()
    if s in ("grid", "institucional", "cuadricula", "4", "tabla_grid", "tabla_institucional"):
        return EstilosTabla.GRID
    return EstilosTabla.APA


def set_borde_celda_especifico(
    celda,
    *,
    top: Optional[Dict[str, Any]] = None,
    bottom: Optional[Dict[str, Any]] = None,
    left: Optional[Dict[str, Any]] = None,
    right: Optional[Dict[str, Any]] = None,
) -> None:
    """Configura bordes específicos en los cuatro lados de una celda WordML.

    Si un lado es None, se asigna w:val='none' para anular cualquier herencia.
    Si se suministra un dict (ej. {'sz': '6', 'color': '222222', 'val': 'single'}),
    se aplican esos atributos.
    """
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn

    tc_pr = celda._tc.get_or_add_tcPr()
    bordes = OxmlElement("w:tcBorders")
    lados = {"top": top, "left": left, "bottom": bottom, "right": right}
    for nombre_lado, conf in lados.items():
        el = OxmlElement(f"w:{nombre_lado}")
        if conf is None or conf.get("val") == "none":
            el.set(qn("w:val"), "none")
        else:
            el.set(qn("w:val"), conf.get("val", "single"))
            el.set(qn("w:sz"), str(conf.get("sz", "4")))
            el.set(qn("w:color"), str(conf.get("color", "000000")))
            if "space" in conf:
                el.set(qn("w:space"), str(conf.get("space", "0")))
        bordes.append(el)
    tc_pr.append(bordes)


def sombrear_celda_word(celda, hex_color: Optional[str]) -> None:
    """Aplica sombreado sólido a una celda WordML. Si hex_color es None, no aplica sombreado."""
    if not hex_color:
        return
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn

    tc_pr = celda._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), hex_color.lstrip("#"))
    tc_pr.append(shd)


def agregar_texto_enriquecido_celda(
    parrafo,
    texto: str,
    *,
    fuente: str = "Arial",
    tamano: float = 9.0,
    negrita_base: bool = False,
    cursiva_base: bool = False,
    color_rgb=None,
) -> None:
    """Delega el renderizado de texto enriquecido en celdas al núcleo único en bloques.py."""
    if not texto:
        return
    if __package__ in (None, ""):
        import bloques as _bloques
    else:
        from . import bloques as _bloques
    _bloques.agregar_texto_enriquecido(
        parrafo,
        str(texto),
        fuente=fuente,
        tamano=tamano,
        negrita=negrita_base,
        cursiva=cursiva_base,
        color=color_rgb if color_rgb is not None else _bloques.NEGRO,
    )


def _calcular_anchos_proporcionales(
    encabezados: List[str],
    filas: List[List[Any]],
    ancho_total: float = 6.5,
) -> List[float]:
    """Calcula anchos de columna inteligentes en pulgadas según contenido y tokens indivisibles.

    Previene que identificadores largos (URIs, códigos) se partan a mitad de palabra en LibreOffice.
    """
    n_cols = len(encabezados)
    if n_cols == 0:
        return []

    pesos: List[float] = []
    minimos: List[float] = []
    for c in range(n_cols):
        celdas_col = [str(encabezados[c])] + [str(f[c]) for f in filas if c < len(f)]
        max_token = 0
        longs = []
        for txt in celdas_col:
            longs.append(len(txt))
            for tok in re.split(r"\s+", txt):
                if len(tok) > max_token:
                    max_token = len(tok)
        prom = sum(longs) / max(1, len(longs))
        # Estimar mínimo en pulgadas para no partir tokens largos (aprox 0.068" por carácter a 9pt + padding)
        min_col = max(0.55, min(2.4, max_token * 0.068 + 0.18))
        peso = max(prom * 0.75 + max_token * 0.65, 8.0)
        pesos.append(peso)
        minimos.append(min_col)

    suma_min = sum(minimos)
    if suma_min >= ancho_total:
        escala = ancho_total / suma_min
        return [round(m * escala, 3) for m in minimos]

    sobrante = ancho_total - suma_min
    suma_pesos = sum(pesos) or 1.0
    anchos = [round(m + sobrante * (p / suma_pesos), 3) for m, p in zip(minimos, pesos, strict=False)]
    return anchos


def _fijar_ancho_celda_xml(celda, pulgadas: float) -> None:
    """Establece w:tcW explícito en dxa (twips) para garantizar fidelidad en Word y LibreOffice."""
    twips = str(int(round(pulgadas * 1440)))
    tc_pr = celda._tc.get_or_add_tcPr()
    for previo in tc_pr.findall(qn("w:tcW")):
        tc_pr.remove(previo)
    tc_w = OxmlElement("w:tcW")
    tc_w.set(qn("w:w"), twips)
    tc_w.set(qn("w:type"), "dxa")
    tc_pr.append(tc_w)


def tabla_estilizada(
    doc,
    encabezados: List[str],
    filas: List[List[Any]],
    *,
    estilo: Optional[str] = None,
    anchos: Optional[List[float]] = None,
    numero_tabla: Optional[Union[int, str]] = None,
    titulo_tabla: Optional[str] = None,
    nota_pie: Optional[str] = None,
    fuente: str = "Arial",
    tamano_cabecera: float = 9.5,
    tamano_cuerpo: float = 9.0,
):
    """Genera una tabla con diseño editorial académico en WordML.

    Soporta las dos opciones autorizadas del repositorio:
    - Opción 1 (EstilosTabla.APA): Norma oficial APA 7.ª ed. (3 líneas horizontales, cero verticales, fondo blanco).
    - Opción 4 (EstilosTabla.GRID): Cuadrícula institucional completa con bordes en cada celda y cabecera sombreada.
    """
    estilo_activo = resolver_estilo_tabla(estilo, defecto=EstilosTabla.APA)

    # Rótulo y Título formal APA 7 (si se suministran)
    es_apa_tnr = estilo_activo == EstilosTabla.APA and fuente.lower() == "times new roman"
    tam_rotulo = 12.0 if es_apa_tnr else 10.5
    col_rotulo = RGBColor(0, 0, 0) if es_apa_tnr else RGBColor(20, 20, 20)
    col_titulo = RGBColor(0, 0, 0) if es_apa_tnr else RGBColor(40, 40, 40)

    if numero_tabla is not None:
        p_num = doc.add_paragraph()
        p_num.alignment = WD_ALIGN_PARAGRAPH.LEFT
        p_num.paragraph_format.space_before = Pt(12)
        p_num.paragraph_format.space_after = Pt(0 if es_apa_tnr else 2)
        p_num.paragraph_format.line_spacing = 2.0 if es_apa_tnr else 1.15
        p_num.paragraph_format.keep_with_next = True
        p_num.paragraph_format.widow_control = True
        r_num = p_num.add_run(f"Tabla {numero_tabla}")
        r_num.font.name = fuente
        r_num.font.size = Pt(tam_rotulo)
        r_num.bold = True
        r_num.font.color.rgb = col_rotulo

    if titulo_tabla:
        p_tit = doc.add_paragraph()
        p_tit.alignment = WD_ALIGN_PARAGRAPH.LEFT
        p_tit.paragraph_format.space_before = Pt(0)
        p_tit.paragraph_format.space_after = Pt(6)
        p_tit.paragraph_format.line_spacing = 2.0 if es_apa_tnr else 1.15
        p_tit.paragraph_format.keep_with_next = True
        p_tit.paragraph_format.widow_control = True
        r_tit = p_tit.add_run(titulo_tabla)
        r_tit.font.name = fuente
        r_tit.font.size = Pt(tam_rotulo)
        r_tit.italic = True
        r_tit.font.color.rgb = col_titulo

    # Resolver anchos efectivos (explícitos o calculados proporcionalmente al contenido)
    anchos_efectivos = list(anchos) if anchos is not None else _calcular_anchos_proporcionales(encabezados, filas)

    # Creación de tabla con layout fijo para que LibreOffice respete exactamente los anchos
    total_filas_datos = len(filas)
    t = doc.add_table(rows=1, cols=len(encabezados))
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    t.autofit = False

    tbl_pr = t._tbl.tblPr
    for prev_l in tbl_pr.findall(qn("w:tblLayout")):
        tbl_pr.remove(prev_l)
    tbl_layout = OxmlElement("w:tblLayout")
    tbl_layout.set(qn("w:type"), "fixed")
    tbl_pr.append(tbl_layout)

    for prev_w in tbl_pr.findall(qn("w:tblW")):
        tbl_pr.remove(prev_w)
    tbl_w = OxmlElement("w:tblW")
    tbl_w.set(qn("w:w"), str(int(round(sum(anchos_efectivos) * 1440))))
    tbl_w.set(qn("w:type"), "dxa")
    tbl_pr.append(tbl_w)

    # Actualizar tblGrid para consistencia estricta en LibreOffice Writer
    tbl_grid = t._tbl.tblGrid
    if tbl_grid is not None:
        for gc in list(tbl_grid):
            tbl_grid.remove(gc)
        for w_col in anchos_efectivos:
            gc = OxmlElement("w:gridCol")
            gc.set(qn("w:w"), str(int(round(w_col * 1440))))
            tbl_grid.append(gc)

    # Repetición obligatoria de cabecera en salto de página
    tr_pr = t.rows[0]._tr.get_or_add_trPr()
    tbl_header = OxmlElement("w:tblHeader")
    tbl_header.set(qn("w:val"), "true")
    tr_pr.append(tbl_header)

    no_partir_head = OxmlElement("w:cantSplit")
    no_partir_head.set(qn("w:val"), "true")
    tr_pr.append(no_partir_head)

    # 1. Aplicar estilo a Fila 0 (Encabezados)
    color_txt_head = RGBColor(20, 20, 20)
    borde_h_fuerte = {"val": "single", "sz": "8", "color": "222222"}
    borde_h_medio = {"val": "single", "sz": "6", "color": "222222"}

    for i, texto in enumerate(encabezados):
        celda = t.rows[0].cells[i]
        if i < len(anchos_efectivos):
            celda.width = Inches(anchos_efectivos[i])
            _fijar_ancho_celda_xml(celda, anchos_efectivos[i])

        if estilo_activo == EstilosTabla.APA:
            set_borde_celda_especifico(celda, top=borde_h_fuerte, bottom=borde_h_medio)
        else:  # EstilosTabla.GRID
            b_grid_head = {"val": "single", "sz": "4", "color": "B0B0B0"}
            set_borde_celda_especifico(celda, top=b_grid_head, bottom=b_grid_head, left=b_grid_head, right=b_grid_head)
            sombrear_celda_word(celda, "E8E8E8")
            color_txt_head = RGBColor(20, 20, 20)

        p = celda.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_before = Pt(4)
        p.paragraph_format.space_after = Pt(4)
        p.paragraph_format.line_spacing = 1.05
        agregar_texto_enriquecido_celda(
            p,
            str(texto),
            fuente=fuente,
            tamano=tamano_cabecera,
            negrita_base=True,
            color_rgb=color_txt_head,
        )

    # 2. Aplicar estilo a Filas de datos
    for idx_f, fila in enumerate(filas):
        f = t.add_row()
        no_partir = OxmlElement("w:cantSplit")
        no_partir.set(qn("w:val"), "true")
        f._tr.get_or_add_trPr().append(no_partir)

        es_ultima = (idx_f == total_filas_datos - 1)

        for i, val in enumerate(fila):
            celda = f.cells[i]
            if i < len(anchos_efectivos):
                celda.width = Inches(anchos_efectivos[i])
                _fijar_ancho_celda_xml(celda, anchos_efectivos[i])

            texto_celda = str(val)

            if estilo_activo == EstilosTabla.APA:
                if es_ultima:
                    set_borde_celda_especifico(celda, bottom=borde_h_fuerte)
                else:
                    set_borde_celda_especifico(celda)  # Todos en none
            else:  # EstilosTabla.GRID
                b_grid_celda = {"val": "single", "sz": "4", "color": "CCCCCC"}
                set_borde_celda_especifico(celda, top=b_grid_celda, bottom=b_grid_celda, left=b_grid_celda, right=b_grid_celda)

            p = celda.paragraphs[0]
            p.paragraph_format.space_before = Pt(3)
            p.paragraph_format.space_after = Pt(3)
            p.paragraph_format.line_spacing = 1.05

            if len(texto_celda) <= 12 and "\n" not in texto_celda and i > 0:
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            else:
                p.alignment = WD_ALIGN_PARAGRAPH.LEFT

            agregar_texto_enriquecido_celda(
                p,
                texto_celda,
                fuente=fuente,
                tamano=tamano_cuerpo,
                negrita_base=(i == 0 and estilo_activo in (EstilosTabla.APA, EstilosTabla.GRID)),
                color_rgb=RGBColor(30, 30, 30),
            )

    # 3. Nota formal de pie (si se suministra) o párrafo de separación
    if nota_pie:
        p_nota = doc.add_paragraph()
        p_nota.paragraph_format.space_before = Pt(4)
        p_nota.paragraph_format.space_after = Pt(12)
        p_nota.paragraph_format.line_spacing = 1.0
        r_n1 = p_nota.add_run("Nota. ")
        r_n1.font.name = fuente
        r_n1.font.size = Pt(8.5)
        r_n1.italic = True
        r_n1.font.color.rgb = RGBColor(70, 70, 70)

        r_n2 = p_nota.add_run(nota_pie)
        r_n2.font.name = fuente
        r_n2.font.size = Pt(8.5)
        r_n2.font.color.rgb = RGBColor(70, 70, 70)
    else:
        p_post = doc.add_paragraph()
        p_post.paragraph_format.space_before = Pt(0)
        p_post.paragraph_format.space_after = Pt(8)

    return t


# ==============================================================================
# 5. MOTOR VECTORIAL DE DIAGRAMAS DE MARCOS (FRAMES) Y REDES DEL CONOCIMIENTO
# ==============================================================================
def renderizar_diagrama_marco_formal(
    nombre_marco: str,
    slots_data: List[Tuple[Any, ...]],
    ruta_salida: Union[Path, str],
    *,
    titulo_grafica: Optional[str] = None,
    ancho_pulgadas: float = 10.0,
    alto_pulgadas: float = 7.4,
    dpi: int = 300,
) -> Path:
    """Renderiza un diagrama visual de marco (Frame) formal con prevención absoluta de desbordamiento.

    Cada ranura (slot) se estructura en dos sub-filas defensivas:
      - Fila 1: Nombre de ranura (izq) y Tipo de dato (der, con alineación derecha).
      - Fila 2: Valor asignado (izq, aprovechando el 90% del ancho de la tarjeta sin colisión).
    """
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.patches as patches
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(ancho_pulgadas, alto_pulgadas), dpi=dpi)
    fig.patch.set_facecolor("#FFFFFF")
    ax.set_facecolor("#FFFFFF")

    # Contenedor exterior
    marco_box = patches.FancyBboxPatch(
        (0.04, 0.04), 0.92, 0.91,
        boxstyle="round,pad=0.015,rounding_size=0.02",
        facecolor="#F8FAFC",
        edgecolor="#334155",
        linewidth=2.0
    )
    ax.add_patch(marco_box)

    # Cabecera institucional
    header_box = patches.FancyBboxPatch(
        (0.04, 0.81), 0.92, 0.14,
        boxstyle="round,pad=0.015,rounding_size=0.02",
        facecolor="#1E293B",
        edgecolor="#0F172A",
        linewidth=2.0
    )
    ax.add_patch(header_box)

    ax.text(
        0.50, 0.88, f"MARCO (FRAME): {nombre_marco}",
        ha="center", va="center",
        fontsize=12.5, fontweight="bold",
        color="#F8FAFC", fontfamily="sans-serif"
    )

    n_slots = len(slots_data)
    y_start = 0.73
    y_end = 0.08
    delta_y = (y_start - y_end) / max(1, n_slots)
    h_box = min(0.086, delta_y * 0.85)

    y_pos = y_start
    for item in slots_data:
        nombre = str(item[0])
        valor = str(item[1])
        tipo = str(item[2])
        col = item[3] if len(item) > 3 else "#2563EB"

        # Caja de la ranura
        box_slot = patches.FancyBboxPatch(
            (0.07, y_pos - h_box / 2), 0.86, h_box,
            boxstyle="round,pad=0.008,rounding_size=0.015",
            facecolor="#FFFFFF",
            edgecolor="#CBD5E1",
            linewidth=1.2
        )
        ax.add_patch(box_slot)

        # Fila 1: Ranura y Tipo
        ax.text(
            0.095, y_pos + h_box * 0.22, f"• Ranura: {nombre}",
            ha="left", va="center",
            fontsize=9.2, fontweight="bold",
            color=col, fontfamily="sans-serif"
        )
        ax.text(
            0.905, y_pos + h_box * 0.22, f"Tipo: {tipo}",
            ha="right", va="center",
            fontsize=8.0, fontstyle="italic",
            color="#64748B", fontfamily="sans-serif"
        )

        # Fila 2: Valor Asignado con control de ancho y sangría
        val_display = f"Valor = {valor}"
        if len(val_display) > 85:
            val_display = val_display[:82] + "..."
        ax.text(
            0.115, y_pos - h_box * 0.22, val_display,
            ha="left", va="center",
            fontsize=8.5, fontweight="semibold",
            color="#1E293B", fontfamily="sans-serif"
        )

        y_pos -= delta_y

    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    if titulo_grafica:
        ax.set_title(titulo_grafica, fontsize=11.5, fontweight="bold", color="#0F172A", pad=12, fontfamily="sans-serif")

    plt.tight_layout()
    ruta_salida_p = Path(ruta_salida)
    ruta_salida_p.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(str(ruta_salida_p), dpi=dpi, bbox_inches="tight")
    plt.close()
    return ruta_salida_p


def renderizar_diagrama_marcos_jerarquicos(
    titulo_padre: str,
    slots_padre: List[Tuple[Any, ...]],
    titulo_hijo: str,
    slots_hijo: List[Tuple[Any, ...]],
    ruta_salida: Union[Path, str],
    *,
    color_padre: str = "#1E293B",
    color_hijo: str = "#2563EB",
    titulo_grafica: Optional[str] = None,
    ancho_pulgadas: float = 12.0,
    alto_pulgadas: float = 7.5,
    dpi: int = 300,
) -> Path:
    """Renderiza dos marcos en jerarquía ontológica (Superclase e Hijo) con arista de herencia ISA y protección contra desbordes."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.patches as patches
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(ancho_pulgadas, alto_pulgadas), dpi=dpi)
    fig.patch.set_facecolor("#FFFFFF")
    ax.set_facecolor("#FFFFFF")

    # Marco Padre (X: 0.03 a 0.46, ancho 0.43)
    p_box = patches.FancyBboxPatch(
        (0.03, 0.05), 0.43, 0.86,
        boxstyle="round,pad=0.015,rounding_size=0.02",
        facecolor="#F8FAFC",
        edgecolor="#334155",
        linewidth=1.8
    )
    ax.add_patch(p_box)

    p_head = patches.FancyBboxPatch(
        (0.03, 0.79), 0.43, 0.12,
        boxstyle="round,pad=0.015,rounding_size=0.02",
        facecolor=color_padre,
        edgecolor="#0F172A",
        linewidth=1.8
    )
    ax.add_patch(p_head)
    ax.text(
        0.245, 0.85, f"MARCO PADRE (Superclase):\n{titulo_padre}",
        ha="center", va="center",
        fontsize=9.5, fontweight="bold",
        color="#FFFFFF", fontfamily="sans-serif"
    )

    # Marco Hijo (X: 0.54 a 0.97, ancho 0.43)
    h_box = patches.FancyBboxPatch(
        (0.54, 0.05), 0.43, 0.86,
        boxstyle="round,pad=0.015,rounding_size=0.02",
        facecolor="#F8FAFC",
        edgecolor="#334155",
        linewidth=1.8
    )
    ax.add_patch(h_box)

    h_head = patches.FancyBboxPatch(
        (0.54, 0.79), 0.43, 0.12,
        boxstyle="round,pad=0.015,rounding_size=0.02",
        facecolor=color_hijo,
        edgecolor="#0F172A",
        linewidth=1.8
    )
    ax.add_patch(h_head)
    ax.text(
        0.755, 0.85, f"MARCO HIJO (Subclase Especializada):\n{titulo_hijo}",
        ha="center", va="center",
        fontsize=9.5, fontweight="bold",
        color="#FFFFFF", fontfamily="sans-serif"
    )

    # Flecha ISA
    ax.annotate(
        "",
        xy=(0.46, 0.85),
        xytext=(0.54, 0.85),
        arrowprops=dict(
            arrowstyle="-|>",
            color="#BE185D",
            lw=3.0,
            mutation_scale=22,
        ),
    )
    ax.text(
        0.50, 0.89, "HERENCIA (ISA)\nsubtipo_de",
        ha="center", va="center",
        fontsize=8.2,
        fontweight="bold",
        color="#BE185D",
        bbox=dict(boxstyle="round,pad=0.2", facecolor="#FCE7F3", edgecolor="#F472B6", alpha=0.95)
    )

    # Renderizar slots en columnas
    def render_slots_column(x_base: float, slots: List[Tuple[Any, ...]], col_theme: str):
        n = len(slots)
        y_top = 0.72
        y_bot = 0.08
        dy = (y_top - y_bot) / max(1, n)
        h = min(0.082, dy * 0.88)
        y = y_top

        for item in slots:
            s_nom = str(item[0])
            s_val = str(item[1])
            s_tip = str(item[2])

            sb = patches.FancyBboxPatch(
                (x_base + 0.02, y - h / 2), 0.39, h,
                boxstyle="round,pad=0.008,rounding_size=0.012",
                facecolor="#FFFFFF",
                edgecolor="#CBD5E1",
                linewidth=1.0
            )
            ax.add_patch(sb)

            # Sub-fila 1: Nombre (izq) y Tipo (der)
            ax.text(
                x_base + 0.035, y + h * 0.22, f"• {s_nom}",
                ha="left", va="center",
                fontsize=8.2, fontweight="bold",
                color=col_theme, fontfamily="sans-serif"
            )
            tip_str = f"[{s_tip}]"
            if len(tip_str) > 20:
                tip_str = tip_str[:18] + "...]"
            ax.text(
                x_base + 0.395, y + h * 0.22, tip_str,
                ha="right", va="center",
                fontsize=7.2, fontstyle="italic",
                color="#64748B", fontfamily="sans-serif"
            )

            # Sub-fila 2: Valor Asignado con límite seguro de caracteres
            val_str = f"= {s_val}"
            if len(val_str) > 46:
                val_str = val_str[:43] + "..."
            ax.text(
                x_base + 0.045, y - h * 0.22, val_str,
                ha="left", va="center",
                fontsize=7.6, fontweight="semibold",
                color="#1E293B", fontfamily="sans-serif"
            )

            y -= dy

    render_slots_column(0.03, slots_padre, "#1E293B")
    render_slots_column(0.54, slots_hijo, color_hijo)

    ax.set_xlim(0, 1)
    ax.set_ylim(0.01, 0.99)
    ax.axis("off")

    if titulo_grafica:
        ax.set_title(titulo_grafica, fontsize=11.5, fontweight="bold", color="#0F172A", pad=12, fontfamily="sans-serif")

    plt.tight_layout()
    ruta_salida_p = Path(ruta_salida)
    ruta_salida_p.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(str(ruta_salida_p), dpi=dpi, bbox_inches="tight")
    plt.close()
    return ruta_salida_p


# ==============================================================================
# 8. TARJETAS Y NODOS ACADÉMICOS SOBRIOS (CERO BARRAS LATERALES TIPO IA)
# ==============================================================================
def envolver_texto_pil(
    draw: ImageDraw.ImageDraw,
    texto: str,
    fuente: Any,
    ancho_max: int,
) -> List[str]:
    """Envuelve texto respetando el ancho exacto en píxeles (cero desbordes)."""
    palabras = texto.split()
    lineas: List[str] = []
    actual = ""
    for palabra in palabras:
        candidato = f"{actual} {palabra}".strip()
        bbox = draw.textbbox((0, 0), candidato, font=fuente)
        if bbox[2] - bbox[0] <= ancho_max:
            actual = candidato
        else:
            if actual:
                lineas.append(actual)
            actual = palabra
    if actual:
        lineas.append(actual)
    return lineas


def dibujar_tarjeta_academica(
    draw: ImageDraw.ImageDraw,
    caja: Tuple[int, int, int, int],
    titulo: str,
    cuerpo: str,
    *,
    fuente_titulo: Any,
    fuente_cuerpo: Any,
    color_borde: Tuple[int, int, int] = (148, 163, 184),
    color_fondo: Tuple[int, int, int] = (255, 255, 255),
    color_titulo: Tuple[int, int, int] = (15, 23, 42),
    color_cuerpo: Tuple[int, int, int] = (51, 65, 85),
    color_divisor: Optional[Tuple[int, int, int]] = (226, 232, 240),
    grosor_borde: int = 2,
    radio: int = 10,
    pad_x: int = 24,
    pad_y: int = 20,
    interlineado_titulo: int = 28,
    interlineado_cuerpo: int = 27,
) -> None:
    """Dibuja un nodo/tarjeta editorial sobrio sin barras laterales de acento.

    Estándar editorial académico (IEEE/APA/Springer):
      - Contorno perimetral uniforme y fino (sin franjas verticales a la izquierda).
      - Fondo blanco o tinte institucional tenue.
      - Jerarquía por tipografía y separador horizontal discreto bajo el encabezado.
    """
    x0, y0, x1, y1 = caja
    draw.rounded_rectangle(
        (x0, y0, x1, y1),
        radius=radio,
        fill=color_fondo,
        outline=color_borde,
        width=grosor_borde,
    )

    ancho_texto = (x1 - x0) - 2 * pad_x
    ty = y0 + pad_y
    for linea in envolver_texto_pil(draw, titulo, fuente_titulo, ancho_texto):
        draw.text((x0 + pad_x, ty), linea, font=fuente_titulo, fill=color_titulo)
        ty += interlineado_titulo

    if color_divisor is not None:
        ty += 4
        draw.line([(x0 + pad_x, ty), (x1 - pad_x, ty)], fill=color_divisor, width=2)
        ty += 12
    else:
        ty += 8

    for parrafo in cuerpo.split("\n"):
        for linea in envolver_texto_pil(draw, parrafo, fuente_cuerpo, ancho_texto):
            draw.text((x0 + pad_x, ty), linea, font=fuente_cuerpo, fill=color_cuerpo)
            ty += interlineado_cuerpo




