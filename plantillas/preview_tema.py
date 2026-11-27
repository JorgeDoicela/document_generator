# -*- coding: utf-8 -*-
"""Generador de vistas previas y catálogo visual para temas y estilos.

Proporciona dos capacidades desacopladas:
  1. `generar_preview_tema`: muestra completa de un tema específico (`apa7` o `theme.json`).
  2. `obtener_catalogo_estilos` / `generar_catalogo_estilos`: inventario en consola y
     muestrario comparativo en `.docx`/`.pdf` de todos los estilos configurables.
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import apa_docx
    import bloques
    import formato_institucional as fmt_inst
    import omml
    import plataforma
    import temas as temas_mod
    import visual
else:
    from . import apa_docx, bloques, omml, plataforma, visual
    from . import formato_institucional as fmt_inst
    from . import temas as temas_mod

DIR_PREVIEWS = temas_mod.DIR_TEMAS / ".previews"


def _hex_rgb(rgb: temas_mod.RGBTuple) -> str:
    return f"#{rgb[0]:02X}{rgb[1]:02X}{rgb[2]:02X}"


def _resolver_ruta_salida(salida: Optional[Union[str, Path]], nombre_archivo: str) -> Path:
    if salida is not None:
        return Path(salida).resolve()
    Path(DIR_PREVIEWS).mkdir(parents=True, exist_ok=True)
    return Path(DIR_PREVIEWS / nombre_archivo).resolve()


def _iniciar_documento_muestra(
    t: temas_mod.TemaDocumental,
    ruta_salida: Path,
    *,
    titulo: str,
    subtitulo: str,
    autor: str = "Autor de Muestra",
    resumen: Optional[str] = None,
    palabras_clave: Optional[List[str]] = None,
) -> Any:
    """Inicializa un Document() aplicando APA 7 oficial o el TemaDocumental indicado."""
    if t.nombre == "apa7":
        doc, _, _ = apa_docx.nuevo_documento(
            titulo=titulo,
            materia=subtitulo,
            salida=ruta_salida,
            institucion="document_generator",
            carrera="Ingeniería Documental",
            nombre=autor,
            docente="Comité de Revisión",
            fecha="2026",
            formato="apa7",
        )
        return doc

    return fmt_inst.nuevo_documento_tematico(
        titulo=titulo,
        subtitulo=subtitulo,
        tema=t,
        institucion="document_generator",
        organizacion="Ingeniería Documental",
        docente="Comité de Revisión",
        periodo="2026",
        integrantes=[autor],
        resumen=resumen,
        palabras_clave=palabras_clave,
    )


def _bib_muestra(estilo_ref: str) -> apa_docx.Bibliografia:
    bib = apa_docx.Bibliografia(estilo=estilo_ref)
    bib.agregar(
        "russell2021",
        ["Russell, S.", "Norvig, P."],
        2021,
        "Artificial Intelligence: A Modern Approach",
        "Pearson",
        detalles="4.a ed.",
    )
    bib.agregar(
        "nist2024",
        ["National Institute of Standards and Technology"],
        2024,
        "The NIST Cybersecurity Framework (CSF) 2.0",
        "U.S. Department of Commerce",
        url="https://doi.org/10.6028/NIST.CSWP.29",
    )
    return bib


def generar_preview_tema(
    tema: Union[str, Path, temas_mod.TemaDocumental],
    *,
    salida: Optional[Union[str, Path]] = None,
    estilo_citas: Optional[str] = None,
) -> Path:
    """Genera un archivo `.docx` de muestra visual para el tema indicado."""
    t = temas_mod.cargar_tema(tema)
    estilo_ref = estilo_citas or "apa7"
    ruta_salida = _resolver_ruta_salida(salida, f"preview_{t.nombre}.docx")

    bib = _bib_muestra(estilo_ref)
    texto_resumen = (
        f"Este documento de muestra valida la identidad visual del tema **{t.nombre}**, "
        f"verificando portada/cabecera, jerarquía de encabezados, tipografía ({t.fuente} {t.tamano_cuerpo} pt), "
        f"ecuaciones OMML vectoriales, tablas en estilo `{t.estilo_tabla}` y referencias en formato `{estilo_ref}`."
    )
    kw_resumen = [t.nombre, t.fuente, t.estilo_tabla, estilo_ref]
    doc = _iniciar_documento_muestra(
        t,
        ruta_salida,
        titulo=f"Muestra Visual del Tema: {t.nombre}",
        subtitulo=t.descripcion or "Validación Tipográfica y Editorial",
        resumen=texto_resumen if t.estilo_portada == "articulo" else None,
        palabras_clave=kw_resumen if t.estilo_portada == "articulo" else None,
    )

    if t.estilo_portada != "articulo":
        bloques.resumen_ejecutivo(
            doc,
            texto_resumen,
            palabras_clave=kw_resumen,
            fuente=t.fuente,
            tamano=max(t.tamano_cuerpo - 0.5, 9.5),
            color_titulo=t.rgb_primario(),
        )

    apa_docx.titulo(doc, "1. Parámetros de Identidad del Tema", nivel=1)
    apa_docx.parrafo(
        doc,
        f"El tema **{t.nombre}** emplea la familia tipográfica *{t.fuente}* con cuerpo de "
        f"`{t.tamano_cuerpo} pt`, interlineado `{t.interlineado}` y tablas en modo `{t.estilo_tabla}`. "
        f"La estructura sigue principios de ingeniería documental determinista {bib.cita('russell2021')} "
        f"y trazabilidad verificable {bib.cita('nist2024')}.",
    )

    bloques.tabla_academica(
        doc,
        ["Propiedad", "Valor Configurado", "Propósito Editorial"],
        [
            ["Fuente principal", f"{t.fuente} ({t.tamano_cuerpo} pt)", "Cuerpo de texto y tablas"],
            ["Encabezados (H1 / H2 / H3)", f"{t.tamano_h1} / {t.tamano_h2} / {t.tamano_h3} pt", "Jerarquía estructural"],
            ["Interlineado / Post-espacio", f"{t.interlineado} / {t.espacio_despues} pt", "Densidad de lectura"],
            ["Márgenes (Sup/Inf/Izq/Der)", f"{t.margen_sup}\" / {t.margen_inf}\" / {t.margen_izq}\" / {t.margen_der}\"", "Caja tipográfica"],
            ["Paleta (Primario / Texto)", f"{_hex_rgb(t.color_primario)} / {_hex_rgb(t.color_texto)}", "Contraste y sobriedad"],
            ["Estilo de tablas", t.estilo_tabla, "Layout fijo compatible con LibreOffice"],
        ],
        estilo=t.estilo_tabla,
        fuente=t.fuente,
        tamano_cuerpo=max(t.tamano_cuerpo - 1.0, 9.0),
    )

    apa_docx.titulo(doc, "1.1 Enunciado Formal y Ecuación OMML", nivel=2)
    bloques.enunciado_formal(
        doc,
        "Comprobar que la tipografía, las ecuaciones matemáticas vectoriales y el código fuente "
        "se renderizan sin desbordes ni caracteres corruptos al exportar a PDF.",
        numero="",
        etiqueta="Consigna de validación",
        fuente=t.fuente,
    )
    omml.formula_bloque(
        doc,
        r"\forall x \in \mathcal{D} : \text{Calidad}(x) \geq \tau \implies \text{Aprobado}(x)",
        "Ecuación 1. Condición formal de validación documental.",
    )

    apa_docx.titulo(doc, "1.1.1 Bloque de Código de Referencia", nivel=3)
    bloques.codigo_bloque(
        doc,
        f'from plantillas import formato_institucional as inst\ndoc = inst.nuevo_documento_tematico(titulo="Demo", tema="{t.nombre}")',
        etiqueta="python",
        fuente_pie=t.fuente,
    )

    apa_docx.referencias(doc, bib)
    apa_docx.guardar_documento(doc, ruta_salida)
    return ruta_salida


def generar_previews(
    objetivo: str,
    *,
    salida: Optional[Union[str, Path]] = None,
    estilo_citas: Optional[str] = None,
) -> List[Path]:
    """Genera vista previa para un tema específico o para 'todos' los temas personalizados.

    Nota: con `objetivo="todos"` excluye el preset base `apa7` para no duplicar el
    muestrario generado por `generar_catalogo_estilos()`.
    """
    if objetivo.strip().lower() in ("todos", "all"):
        personalizados = [n for n in temas_mod.listar_temas() if n != "apa7"]
        if not personalizados:
            return []
        rutas: List[Path] = []
        base_dir = Path(salida).resolve() if salida is not None else DIR_PREVIEWS
        base_dir.mkdir(parents=True, exist_ok=True)
        for nombre in personalizados:
            rutas.append(
                generar_preview_tema(
                    nombre,
                    salida=base_dir / f"preview_{nombre}.docx",
                    estilo_citas=estilo_citas,
                )
            )
        return rutas

    return [generar_preview_tema(objetivo, salida=salida, estilo_citas=estilo_citas)]


def obtener_catalogo_estilos() -> List[Dict[str, Any]]:
    """Devuelve el inventario estructurado de todos los elementos y estilos elegibles."""
    temas_disponibles = temas_mod.listar_temas()
    return [
        {
            "elemento": "Tablas",
            "config": "ESTILO_TABLA en .env | estilo_tabla en theme.json | estilo= en Python",
            "opciones": [
                ("apa", "3 líneas horizontales APA 7 (cabecera limpia, sin bordes verticales)."),
                ("grid", "Cuadrícula completa con bordes grises y cabecera sombreada."),
            ],
        },
        {
            "elemento": "Terminales (300 DPI) y Bloques de Código",
            "config": "tema=Temas.DARK | Temas.LIGHT en visual.py | bloques.codigo_bloque()",
            "opciones": [
                ("light", "Academic Paper: fondo claro de alto contraste, optimizado para impresión/PDF."),
                ("dark", "Tokyo Night: fondo oscuro estilo editor moderno."),
                ("minimalista", "bloques.codigo_bloque(): caja monoespaciada sobria con pie opcional."),
            ],
        },
        {
            "elemento": "Bloques Editoriales, OMML y Tarjetas",
            "config": "plantillas/bloques.py | plantillas/omml.py | plantillas/visual.py",
            "opciones": [
                ("enunciado_formal", "Consignas docentes limpias sobre el lienzo (sin cajas ni barras laterales)."),
                ("formula_bloque", "Ecuaciones LaTeX normalizadas a Unicode + XML OMML vectorial (Cambria Math)."),
                ("tarjeta_academica", "visual.dibujar_tarjeta_academica(): nodos 300 DPI de contorno uniforme."),
            ],
        },
        {
            "elemento": "Citas y Referencias",
            "config": "Bibliografia(estilo=...) | estilo_citas: en Markdown | --citas en CLI",
            "opciones": [
                ("apa7", "Autor-año: (Russell y Norvig, 2021) y lista en orden alfabético."),
                ("ieee", "Numérico entre corchetes: [1] y lista por orden de aparición."),
                ("vancouver", "Numérico entre paréntesis: (1) y lista numerada 1. por aparición."),
            ],
        },
        {
            "elemento": "Tema Documental",
            "config": "TEMA_DEFECTO en .env | Formato: en TAREA.md | tema: en Markdown | --tema",
            "opciones": [
                (
                    nombre,
                    temas_mod.cargar_tema(nombre).descripcion or f"Tema personalizado ({nombre})",
                )
                for nombre in temas_disponibles
            ],
        },
        {
            "elemento": "Portada / Modalidad",
            "config": "Modalidad: en TAREA.md | modalidad: en Markdown | --modalidad / --grupal",
            "opciones": [
                ("individual", "Portada para un único estudiante/autor."),
                ("grupal", "Portada con nombre de grupo y lista completa de integrantes."),
            ],
        },
    ]


def _seccion_tipografia_y_omml_catalogo(doc: Any, t: temas_mod.TemaDocumental) -> None:
    apa_docx.titulo(doc, "1. Tipografía, Enunciado Formal y Ecuaciones OMML", nivel=1)
    apa_docx.parrafo(
        doc,
        "El motor tipográfico convierte automáticamente **negritas**, *cursivas*, `código inline`, "
        "superíndices como x^2 y subíndices como H_2O en runs nativos de WordML sin dejar sintaxis cruda.",
    )
    apa_docx.vinieta(doc, "Lista con viñetas y sangría francesa automática (0.25 pulgadas).")
    apa_docx.vinieta(doc, "Encabezados jerárquicos nativos Word (Heading 1, Heading 2 y Heading 3).")

    apa_docx.titulo(doc, "1.1 Enunciado Formal sin Cajas Coloreadas", nivel=2)
    bloques.enunciado_formal(
        doc,
        "Demostrar que las consignas docentes se maquetan con sangría y tipografía limpia sobre el lienzo, "
        "y que las ecuaciones matemáticas se vectorizan sin glifos corruptos.",
        numero=1,
        etiqueta="Consigna",
        fuente=t.fuente,
    )

    apa_docx.titulo(doc, "1.1.1 Ecuación Vectorial OMML", nivel=3)
    omml.formula_bloque(
        doc,
        r"\forall x \in \mathcal{D} : \text{Calidad}(x) \geq \tau \implies \text{Aprobado}(x)",
        "Ecuación 1. Ecuación OMML generada desde LaTeX con normalización automática a Unicode.",
    )


def _seccion_tablas_catalogo(doc: Any, t: temas_mod.TemaDocumental) -> None:
    apa_docx.titulo(doc, "2. Estilos de Tablas (apa vs. grid)", nivel=1)
    apa_docx.parrafo(
        doc,
        "El estilo `apa` usa tres líneas horizontales sin bordes verticales ni relleno, conforme a APA 7. "
        "El estilo `grid` dibuja cuadrícula completa y sombreado gris en la cabecera para tablas técnicas.",
    )
    datos_enc = ["Métrica", "Valor Base", "Estado"]
    datos_filas = [
        ["Cobertura de rúbrica", "100 %", "Aprobado"],
        ["Errores XML / LaTeX", "0", "Limpio"],
        ["Layout de tabla", "Fijo (fixed)", "Estable"],
    ]
    variantes: Tuple[Tuple[str, int, str, str], ...] = (
        (
            visual.EstilosTabla.APA,
            1,
            "Muestra en estilo APA (3 líneas horizontales APA 7)",
            'Configuración: ESTILO_TABLA="apa" o estilo_tabla: "apa".',
        ),
        (
            visual.EstilosTabla.GRID,
            2,
            "Muestra en estilo Grid (cuadrícula completa)",
            'Configuración: ESTILO_TABLA="grid" o estilo_tabla: "grid".',
        ),
    )
    for idx, (estilo_tbl, num_tbl, tit_tbl, nota_tbl) in enumerate(variantes):
        if idx > 0:
            apa_docx.parrafo(
                doc,
                "La Tabla 2 muestra exactamente los mismos datos renderizados con el estilo `grid`.",
                sangria=False,
            )
        visual.tabla_estilizada(
            doc,
            datos_enc,
            datos_filas,
            estilo=estilo_tbl,
            numero_tabla=num_tbl,
            titulo_tabla=tit_tbl,
            nota_pie=nota_tbl,
            fuente=t.fuente,
        )


def _renderizar_tarjeta_muestra(ruta: Path) -> Path:
    from PIL import Image, ImageDraw, ImageFont

    img = Image.new("RGB", (920, 260), (255, 255, 255))
    draw = ImageDraw.Draw(img)
    ruta_sans = plataforma.resolver_fuente_sans(bold=False)
    ruta_sans_bold = plataforma.resolver_fuente_sans(bold=True)
    f_tit: Any
    f_cuerpo: Any
    if ruta_sans:
        f_tit = ImageFont.truetype(str(ruta_sans_bold or ruta_sans), 22)
        f_cuerpo = ImageFont.truetype(str(ruta_sans), 18)
    else:
        f_tit = ImageFont.load_default()
        f_cuerpo = ImageFont.load_default()

    visual.dibujar_tarjeta_academica(
        draw,
        caja=(20, 20, 900, 240),
        titulo="TARJETA ACADÉMICA SOBRIA (visual.dibujar_tarjeta_academica)",
        cuerpo=(
            "Diseño editorial de publicación científica: contorno perimetral uniforme de 2 px, "
            "fondo limpio sin gradientes ni barras laterales de acento y divisor horizontal discreto."
        ),
        fuente_titulo=f_tit,
        fuente_cuerpo=f_cuerpo,
    )
    img.save(ruta, dpi=(300, 300))
    return ruta


def _seccion_terminales_catalogo(doc: Any, t: temas_mod.TemaDocumental) -> None:
    apa_docx.titulo(doc, "3. Terminales CLI y Tarjeta Académica a 300 DPI", nivel=1)
    apa_docx.parrafo(
        doc,
        "Las capturas de terminal usan `visual.renderizar_terminal()` en paletas `Temas.LIGHT` y "
        "`Temas.DARK`; los nodos de diagramas usan `visual.dibujar_tarjeta_academica()`.",
    )
    salida_cmd = [
        "Tema             Fuente             Tablas   Descripción",
        "-----------------------------------------------------------------------",
        "apa7             Times New Roman    apa      Norma APA 7.a edición",
        "[OK] Auditoría estática superada: 0 errores.",
    ]
    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        for tema_term, etiqueta in (
            (visual.Temas.LIGHT, "Figura 1. Terminal CLI con tema light (Academic Paper)."),
            (visual.Temas.DARK, "Figura 2. Terminal CLI con tema dark (Tokyo Night)."),
        ):
            img_path = visual.renderizar_terminal(
                f"terminal — tema {tema_term}",
                "./tareas temas",
                salida_cmd,
                tmp_dir / f"term_{tema_term}.png",
                tema=tema_term,
            )
            bloques.caja_captura_evidencia(doc, img_path, etiqueta, fuente=t.fuente)
        tarjeta_path = _renderizar_tarjeta_muestra(tmp_dir / "tarjeta_academica.png")
        bloques.caja_captura_evidencia(
            doc,
            tarjeta_path,
            "Figura 3. Nodo editorial generado con dibujar_tarjeta_academica().",
            fuente=t.fuente,
        )


def _seccion_codigo_catalogo(doc: Any, t: temas_mod.TemaDocumental) -> None:
    apa_docx.titulo(doc, "4. Bloques de Código (light, dark y minimalista)", nivel=1)
    apa_docx.parrafo(
        doc,
        "Los bloques de código disponen de `visual.bloque_codigo_word()` en modo `light` y `dark`, "
        "además de `bloques.codigo_bloque()` para listados minimalistas sobre fondo neutro.",
    )
    fragmento = (
        'from plantillas import apa_docx\n'
        'bib = apa_docx.Bibliografia(estilo="apa7")\n'
        'print(bib.cita("russell2021"))'
    )
    visual.bloque_codigo_word(
        doc,
        fragmento,
        archivo="ejemplo_light.py",
        lenguaje="Python (tema light)",
        tema=visual.Temas.LIGHT,
    )
    apa_docx.parrafo(doc, "Variante alternativa en fondo oscuro (`Temas.DARK`):", sangria=False)
    visual.bloque_codigo_word(
        doc,
        fragmento,
        archivo="ejemplo_dark.py",
        lenguaje="Python (tema dark)",
        tema=visual.Temas.DARK,
    )
    apa_docx.parrafo(doc, "Variante minimalista (`bloques.codigo_bloque()`):", sangria=False)
    bloques.codigo_bloque(doc, fragmento, etiqueta="python (minimalista)", fuente_pie=t.fuente)


def _seccion_citas_catalogo(doc: Any, t: temas_mod.TemaDocumental) -> None:
    apa_docx.titulo(doc, "5. Formatos de Citación (apa7, ieee y vancouver)", nivel=1)
    apa_docx.parrafo(
        doc,
        "La clase `Bibliografia(estilo=...)` formatea citas en el texto y entradas bibliográficas "
        "en tres normas estándar. La Tabla 3 compara la salida real generada para la misma fuente.",
    )
    filas_citas: List[List[str]] = []
    for est_cita in apa_docx.ESTILOS_CITACION:
        bib_tmp = _bib_muestra(est_cita)
        cita_txt = bib_tmp.cita("russell2021")
        narr_txt = bib_tmp.cita_narrativa("russell2021")
        entrada_txt = bib_tmp.entrada("russell2021")
        filas_citas.append([est_cita, f"{cita_txt} / {narr_txt}", entrada_txt])

    visual.tabla_estilizada(
        doc,
        ["Estilo", "Cita Parentética / Narrativa", "Entrada en Referencias"],
        filas_citas,
        estilo=t.estilo_tabla,
        anchos=[0.9, 1.9, 3.7],
        numero_tabla=3,
        titulo_tabla="Comparativa de Formatos de Citación Soportados",
        fuente=t.fuente,
    )


def _seccion_temas_y_portadas_catalogo(doc: Any, t: temas_mod.TemaDocumental) -> None:
    apa_docx.titulo(doc, "6. Temas, Portadas y Guía de Configuración", nivel=1)
    filas_temas = []
    for nom_t in temas_mod.listar_temas():
        tm = temas_mod.cargar_tema(nom_t)
        filas_temas.append([tm.nombre, f"{tm.fuente} {tm.tamano_cuerpo} pt", tm.estilo_tabla, tm.descripcion])

    visual.tabla_estilizada(
        doc,
        ["Tema", "Tipografía", "Tablas", "Descripción"],
        filas_temas,
        estilo=t.estilo_tabla,
        anchos=[1.1, 1.5, 0.7, 3.2],
        numero_tabla=4,
        titulo_tabla="Temas Documentales Detectados en el Entorno",
        fuente=t.fuente,
    )

    apa_docx.parrafo(
        doc,
        "La Tabla 5 resume las dos modalidades de portada y dónde se selecciona cada parámetro "
        "editorial en el flujo de trabajo.",
        sangria=False,
    )
    filas_config = [
        ["Tablas", "apa | grid", "ESTILO_TABLA (.env) o estilo_tabla (theme.json)"],
        ["Terminales y código", "light | dark | minimalista", "Temas.LIGHT | Temas.DARK | bloques.codigo_bloque()"],
        ["Bloques y fórmulas", "enunciado_formal | OMML", "bloques.enunciado_formal() | omml.formula_bloque()"],
        ["Citas y referencias", "apa7 | ieee | vancouver", 'Bibliografia(estilo="apa7"), estilo_citas: o --citas'],
        ["Tema documental", "apa7 | paper | <nombre theme.json>", "TEMA_DEFECTO (.env), Formato: (TAREA.md) o --tema"],
        ["Portada / modalidad", "individual | grupal", "Modalidad: (TAREA.md), modalidad: o --grupal"],
    ]
    visual.tabla_estilizada(
        doc,
        ["Elemento", "Opciones", "Dónde se Configura"],
        filas_config,
        estilo=t.estilo_tabla,
        anchos=[1.5, 1.8, 3.2],
        numero_tabla=5,
        titulo_tabla="Resumen de Selección por Elemento",
        fuente=t.fuente,
    )


def generar_catalogo_estilos(
    *,
    tema: Union[str, Path, temas_mod.TemaDocumental] = "apa7",
    salida: Optional[Union[str, Path]] = None,
) -> Path:
    """Genera un muestrario visual (.docx) comparando todos los estilos de tablas,
    terminales, bloques de código, citación, temas y portadas disponibles."""
    t = temas_mod.cargar_tema(tema)
    ruta_salida = _resolver_ruta_salida(salida, "catalogo_estilos.docx")
    texto_resumen_cat = (
        "Este muestrario reúne en un solo documento todos los estilos seleccionables del framework "
        "(tablas `apa` vs `grid`, terminales CLI y bloques de código `light` vs `dark`, formatos de "
        "citación `apa7`, `ieee` y `vancouver`, temas documentales y modalidades de portada) para "
        "inspeccionarlos visualmente antes de elegir."
    )
    kw_cat = ["apa", "grid", "light", "dark", "apa7", "paper", "ieee", "vancouver"]
    doc = _iniciar_documento_muestra(
        t,
        ruta_salida,
        titulo="Catálogo y Comparativa Visual de Estilos",
        subtitulo="Guía de Elección Editorial",
        autor="Equipo Editorial",
        resumen=texto_resumen_cat if t.estilo_portada == "articulo" else None,
        palabras_clave=kw_cat if t.estilo_portada == "articulo" else None,
    )

    if t.estilo_portada != "articulo":
        bloques.resumen_ejecutivo(
            doc,
            texto_resumen_cat,
            palabras_clave=kw_cat,
            fuente=t.fuente,
            tamano=max(t.tamano_cuerpo - 0.5, 9.5),
            color_titulo=t.rgb_primario(),
        )

    _seccion_tipografia_y_omml_catalogo(doc, t)
    _seccion_tablas_catalogo(doc, t)
    _seccion_terminales_catalogo(doc, t)
    _seccion_codigo_catalogo(doc, t)
    _seccion_citas_catalogo(doc, t)
    _seccion_temas_y_portadas_catalogo(doc, t)

    apa_docx.guardar_documento(doc, ruta_salida)
    return ruta_salida
