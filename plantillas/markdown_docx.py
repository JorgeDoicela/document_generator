# -*- coding: utf-8 -*-
"""Compilador declarativo Markdown + YAML frontmatter -> WordML (.docx).

Permite redactar documentos académicos, técnicos o ejecutivos en un archivo
Markdown estructurado (con metadatos y referencias en frontmatter YAML),
compilándolos directamente a `.docx` con soporte completo de:
  - Temas documentales (`apa7` o temas personalizados en `theme.json`).
  - Marcadores XML de rúbrica en encabezados (`# Sección {#C1}` o `{criterios="C1, C2"}`).
  - Criterios transversales (`transversales: [C4, C5]`).
  - Ecuaciones matemáticas OMML vectoriales (`$$ ... $$`).
  - Citas declarativas (`[@clave]`, `[@clave, p. 15]`, `[@c1; @c2]`, `@clave`) en
    estilos APA 7, IEEE numérico o Vancouver.
  - Tablas Markdown con layout fijo (`apa` o `grid`), bloques de código, listas,
    enunciados formales (`>`), figuras (`![alt](ruta)`) y saltos de página (`---`).
"""
from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import apa_docx
    import bloques
    import formato_institucional as fmt_inst
    import omml
    import rubrica as rub
    import temas as temas_mod
else:
    from . import apa_docx, bloques, omml
    from . import formato_institucional as fmt_inst
    from . import rubrica as rub
    from . import temas as temas_mod

_TITULOS_REF = {"referencias", "referencias bibliograficas", "bibliografia", "references"}
_RE_HEADING = re.compile(r"^(#{1,3})\s+(.+?)\s*$")
_RE_ATTRS = re.compile(r"\s*\{([^}]+)\}\s*$")
_RE_IMAGEN = re.compile(r'^!\[([^\]]*)\]\(([^)\s]+)(?:\s+"([^"]*)")?\)\s*$')
_RE_CITA_BRACKET = re.compile(r"\[(@!?[A-Za-z_][\w-]*(?:[^]]*))\]")
_RE_CITA_NARRATIVA_INLINE = re.compile(r"(?<![\w.@])@([A-Za-z_][\w-]*)")
_RE_CODE_SPAN = re.compile(r"(`[^`]+`)")
_RE_SEP_TABLA = re.compile(r"^\s*\|?(?:\s*:?-+:?\s*\|)+\s*:?-+:?\s*\|?\s*$")
_RE_LISTA_BULLET = re.compile(r"^\s*[-*•]\s+(.+)$")
_RE_LISTA_NUM = re.compile(r"^\s*(\d+[.)])\s+(.+)$")


# --------------------------------------------------------------------------
# Parser YAML ligero sin dependencias externas (con delegación a PyYAML si existe)
# --------------------------------------------------------------------------
def _parsear_escalar(valor: str) -> Any:
    s = valor.strip()
    if not s:
        return ""
    if (s.startswith('"') and s.endswith('"')) or (s.startswith("'") and s.endswith("'")):
        return s[1:-1]
    low = s.lower()
    if low in ("true", "yes", "sí", "si"):
        return True
    if low in ("false", "no"):
        return False
    if low in ("null", "none", "~"):
        return None
    if s.startswith("[") and s.endswith("]"):
        interno = s[1:-1].strip()
        if not interno:
            return []
        return [_parsear_escalar(p) for p in _dividir_csv_yaml(interno)]
    if re.fullmatch(r"-?\d+", s):
        return int(s)
    if re.fullmatch(r"-?\d+\.\d+", s):
        return float(s)
    return s


def _dividir_csv_yaml(texto: str) -> List[str]:
    partes: List[str] = []
    actual: List[str] = []
    en_comilla: Optional[str] = None
    for ch in texto:
        if en_comilla:
            actual.append(ch)
            if ch == en_comilla:
                en_comilla = None
        elif ch in ('"', "'"):
            en_comilla = ch
            actual.append(ch)
        elif ch == ",":
            partes.append("".join(actual).strip())
            actual = []
        else:
            actual.append(ch)
    if actual:
        partes.append("".join(actual).strip())
    return [p for p in partes if p]


def _quitar_comentario_yaml(linea: str) -> str:
    en_comilla: Optional[str] = None
    for idx, ch in enumerate(linea):
        if en_comilla:
            if ch == en_comilla:
                en_comilla = None
        elif ch in ('"', "'"):
            en_comilla = ch
        elif ch == "#" and (idx == 0 or linea[idx - 1].isspace()):
            return linea[:idx].rstrip()
    return linea.rstrip()


def _parsear_yaml_simple(texto: str) -> Dict[str, Any]:
    """Parsea frontmatter YAML estándar sin requerir PyYAML."""
    try:
        import yaml  # type: ignore[import-untyped]

        cargado = yaml.safe_load(texto)
        return cargado if isinstance(cargado, dict) else {}
    except ImportError:
        pass

    lineas_crudas = [_quitar_comentario_yaml(ln) for ln in texto.splitlines()]
    lineas = [(len(ln) - len(ln.lstrip(" ")), ln.strip()) for ln in lineas_crudas if ln.strip()]

    def _parse_bloque(idx: int, indent_base: int) -> Tuple[Any, int]:
        if idx >= len(lineas):
            return {}, idx
        indent0, contenido0 = lineas[idx]
        if contenido0.startswith("- ") or contenido0 == "-":
            return _parse_lista(idx, indent0)
        return _parse_mapa(idx, indent_base)

    def _parse_mapa(idx: int, indent_base: int) -> Tuple[Dict[str, Any], int]:
        res: Dict[str, Any] = {}
        while idx < len(lineas):
            indent, cont = lineas[idx]
            if indent < indent_base or cont.startswith("- "):
                break
            if ":" not in cont:
                idx += 1
                continue
            clave, resto = cont.split(":", 1)
            clave = clave.strip().strip('"').strip("'")
            resto = resto.strip()
            idx += 1
            if resto in ("|", ">"):
                bloque_txt: List[str] = []
                while idx < len(lineas) and lineas[idx][0] > indent:
                    bloque_txt.append(lineas[idx][1])
                    idx += 1
                res[clave] = ("\n" if resto == "|" else " ").join(bloque_txt)
            elif resto == "":
                if idx < len(lineas) and lineas[idx][0] > indent:
                    val, idx = _parse_bloque(idx, lineas[idx][0])
                    res[clave] = val
                else:
                    res[clave] = ""
            else:
                res[clave] = _parsear_escalar(resto)
        return res, idx

    def _parse_lista(idx: int, indent_base: int) -> Tuple[List[Any], int]:
        items: List[Any] = []
        while idx < len(lineas):
            indent, cont = lineas[idx]
            if indent < indent_base or not (cont.startswith("- ") or cont == "-"):
                break
            cuerpo = cont[1:].strip()
            idx += 1
            if not cuerpo:
                if idx < len(lineas) and lineas[idx][0] > indent:
                    val, idx = _parse_bloque(idx, lineas[idx][0])
                    items.append(val)
                else:
                    items.append("")
                continue
            if ":" in cuerpo and not (cuerpo.startswith('"') or cuerpo.startswith("'")):
                k, v = cuerpo.split(":", 1)
                k = k.strip().strip('"').strip("'")
                v = v.strip()
                obj: Dict[str, Any] = {}
                if v == "":
                    if idx < len(lineas) and lineas[idx][0] > indent + 1:
                        sub_val, idx = _parse_bloque(idx, lineas[idx][0])
                        obj[k] = sub_val
                    else:
                        obj[k] = ""
                else:
                    obj[k] = _parsear_escalar(v)
                if idx < len(lineas) and lineas[idx][0] > indent:
                    extra, idx = _parse_mapa(idx, lineas[idx][0])
                    obj.update(extra)
                items.append(obj)
            else:
                items.append(_parsear_escalar(cuerpo))
        return items, idx

    resultado, _ = _parse_mapa(0, 0)
    return resultado


def extraer_frontmatter(texto: str) -> Tuple[Dict[str, Any], str]:
    """Separa el bloque YAML frontmatter (`--- ... ---`) del cuerpo Markdown."""
    limpio = texto.lstrip("\ufeff")
    if not limpio.startswith("---"):
        return {}, limpio
    m = re.match(r"^---\r?\n(.*?)\r?\n---(?:\r?\n|$)", limpio, re.DOTALL)
    if not m:
        return {}, limpio
    meta = _parsear_yaml_simple(m.group(1))
    cuerpo = limpio[m.end():]
    return meta, cuerpo


# --------------------------------------------------------------------------
# Helpers de resolución de encabezados, citas y tablas
# --------------------------------------------------------------------------
def _extraer_atributos_encabezado(texto: str) -> Tuple[str, List[str]]:
    """Extrae criterios de rúbrica desde `# Título {#C1 #C2}` o `{criterios="C1, C2"}`."""
    m = _RE_ATTRS.search(texto)
    if not m:
        return texto.strip(), []
    titulo_limpio = texto[: m.start()].strip()
    bloque = m.group(1)
    crits: List[str] = []
    for cm in re.finditer(r'criterios\s*=\s*["\']([^"\']+)["\']', bloque, re.I):
        crits.extend(re.split(r"[,\s]+", cm.group(1).strip()))
    for hm in re.finditer(r"#([A-Za-z0-9_]+)", bloque):
        crits.append(hm.group(1))
    return titulo_limpio, [c.upper() for c in crits if c]


def _resolver_citas_texto(texto: str, bib: apa_docx.Bibliografia) -> str:
    """Reemplaza citas declarativas `[@clave]`, `[@c1; @c2]` y `@clave` por el formato activo."""
    if not bib._fuentes:
        return texto

    def _reemplazar_segmento(seg: str) -> str:
        def _sub_corchetes(m: re.Match[str]) -> str:
            contenido = m.group(1).strip()
            partes = [p.strip() for p in contenido.split(";") if p.strip()]
            if len(partes) == 1 and partes[0].startswith("@!"):
                resto = partes[0][2:].strip()
                if "," in resto:
                    clave, pag = [x.strip() for x in resto.split(",", 1)]
                    return str(bib.cita_narrativa(clave, pagina=pag)) if clave in bib._fuentes else m.group(0)
                return str(bib.cita_narrativa(resto)) if resto in bib._fuentes else m.group(0)

            claves: List[str] = []
            pagina = ""
            for p in partes:
                if not p.startswith("@"):
                    return m.group(0)
                cuerpo_p = p[1:].strip()
                if "," in cuerpo_p:
                    cl, pag = [x.strip() for x in cuerpo_p.split(",", 1)]
                    claves.append(cl)
                    pagina = pag
                else:
                    claves.append(cuerpo_p)
            if not claves or any(c not in bib._fuentes for c in claves):
                return m.group(0)
            return str(bib.cita(*claves, pagina=pagina))

        seg = _RE_CITA_BRACKET.sub(_sub_corchetes, seg)

        def _sub_narrativa(m: re.Match[str]) -> str:
            clave = m.group(1)
            return str(bib.cita_narrativa(clave)) if clave in bib._fuentes else m.group(0)

        return _RE_CITA_NARRATIVA_INLINE.sub(_sub_narrativa, seg)

    partes = _RE_CODE_SPAN.split(texto)
    return "".join(p if p.startswith("`") and p.endswith("`") else _reemplazar_segmento(p) for p in partes)


def _dividir_fila_tabla(linea: str) -> List[str]:
    limpia = linea.strip()
    if limpia.startswith("|"):
        limpia = limpia[1:]
    if limpia.endswith("|"):
        limpia = limpia[:-1]
    return [c.strip() for c in limpia.split("|")]


def _cargar_referencias_bib(meta: Dict[str, Any], estilo_citas: str) -> apa_docx.Bibliografia:
    bib = apa_docx.Bibliografia(estilo=estilo_citas)
    refs = meta.get("referencias") or []
    if not isinstance(refs, list):
        return bib
    for item in refs:
        if not isinstance(item, dict) or not item.get("clave"):
            continue
        autores = item.get("autores") or item.get("autor") or ["Autor"]
        bib.agregar(
            str(item["clave"]),
            autores,
            item.get("anio", item.get("año", "s. f.")),
            str(item.get("titulo", "")),
            str(item.get("fuente", "")),
            url=str(item.get("url", "")),
            detalles=str(item.get("detalles", "")),
            tipo=str(item.get("tipo", "libro")),
            texto=str(item.get("texto", "")),
        )
    return bib


def _crear_documento_base(
    meta: Dict[str, Any],
    *,
    ruta_salida: Path,
    tema_nombre: str,
    tarea: Optional[Path],
    carpeta_capturas: Path,
) -> Tuple[Any, temas_mod.TemaDocumental]:
    titulo_doc = str(meta.get("titulo") or ruta_salida.stem.replace("_", " "))
    materia = str(meta.get("materia") or meta.get("subtitulo") or "")
    institucion = meta.get("institucion")
    carrera = meta.get("carrera") or meta.get("organizacion")
    docente = meta.get("docente")
    fecha = meta.get("fecha") or meta.get("periodo")
    modalidad = meta.get("modalidad")
    grupo = meta.get("grupo")
    integrantes = meta.get("integrantes") or meta.get("autor") or meta.get("estudiante")
    incluir_indice = bool(meta.get("indice", False))

    tema_obj = temas_mod.cargar_tema(tema_nombre)

    if tema_obj.nombre == "apa7":
        try:
            doc, _, _ = apa_docx.nuevo_documento(
                titulo=titulo_doc,
                materia=materia or "Documento Académico",
                salida=ruta_salida,
                fecha=fecha,
                docente=docente,
                tarea=tarea,
                carpeta_capturas=str(carpeta_capturas),
                nombre=str(integrantes) if isinstance(integrantes, str) else None,
                institucion=str(institucion) if institucion else "Institución",
                carrera=str(carrera) if carrera else "",
                indice=incluir_indice,
                modalidad=str(modalidad) if modalidad else None,
                grupo=str(grupo) if grupo else None,
                integrantes=integrantes,
                formato="apa7",
            )
            return doc, tema_obj
        except Exception:
            pass

    doc = fmt_inst.nuevo_documento_tematico(
        titulo=titulo_doc,
        subtitulo=materia,
        tema=tema_obj,
        institucion=str(institucion) if institucion else None,
        organizacion=str(carrera) if carrera else None,
        docente=str(docente) if docente else None,
        periodo=str(fecha) if fecha else None,
        modalidad=str(modalidad) if modalidad else None,
        grupo=str(grupo) if grupo else None,
        integrantes=integrantes,
        tarea=tarea,
        incluir_indice=incluir_indice,
    )
    return doc, tema_obj


# --------------------------------------------------------------------------
# Punto de entrada público del compilador declarativo
# --------------------------------------------------------------------------
def compilar_markdown(
    ruta_md: Union[str, Path],
    *,
    salida: Optional[Union[str, Path]] = None,
    tema: Optional[str] = None,
    estilo_citas: Optional[str] = None,
    tarea: Optional[Union[str, Path]] = None,
) -> Path:
    """Compila un archivo Markdown con frontmatter YAML a un `.docx` validable."""
    origen = Path(ruta_md).resolve()
    if not origen.is_file():
        raise FileNotFoundError(f"No existe el archivo Markdown: {origen}")

    meta, cuerpo = extraer_frontmatter(origen.read_text(encoding="utf-8"))

    tema_final = str(tema or meta.get("tema") or meta.get("formato") or "apa7").strip()
    estilo_final = str(
        estilo_citas
        or meta.get("estilo_citas")
        or meta.get("citas")
        or ("ieee" if tema_final.lower() == "ieee" else "apa7")
    ).strip()

    if salida is not None:
        ruta_salida = Path(salida).resolve()
    elif meta.get("salida"):
        cand_salida = Path(str(meta["salida"]))
        ruta_salida = cand_salida if cand_salida.is_absolute() else (origen.parent / cand_salida).resolve()
    else:
        ruta_salida = origen.with_suffix(".docx")

    tarea_path = Path(tarea).resolve() if tarea is not None else (origen.parent if (origen.parent / "TAREA.md").is_file() else None)
    carpeta_capturas = origen.parent / "capturas"

    bib = _cargar_referencias_bib(meta, estilo_final)
    doc, tema_obj = _crear_documento_base(
        meta,
        ruta_salida=ruta_salida,
        tema_nombre=tema_final,
        tarea=tarea_path,
        carpeta_capturas=carpeta_capturas,
    )

    if meta.get("resumen"):
        kw = meta.get("palabras_clave") or []
        if isinstance(kw, str):
            kw = [x.strip() for x in kw.split(",") if x.strip()]
        bloques.resumen_ejecutivo(
            doc,
            _resolver_citas_texto(str(meta["resumen"]), bib),
            palabras_clave=kw if isinstance(kw, list) else None,
            fuente=tema_obj.fuente,
            tamano=max(tema_obj.tamano_cuerpo - 0.5, 9.5),
            color_titulo=tema_obj.rgb_primario(),
        )

    lineas = cuerpo.splitlines()
    i = 0
    total = len(lineas)
    num_figura = 0
    criterios_ref: Optional[List[str]] = None
    if meta.get("criterios_referencias"):
        cr = meta["criterios_referencias"]
        criterios_ref = [str(x).upper() for x in cr] if isinstance(cr, list) else [str(cr).upper()]

    while i < total:
        linea = lineas[i]
        stripped = linea.strip()

        if not stripped:
            i += 1
            continue

        # Saltos de página explícitos
        if stripped in ("---", "***", "<!-- pagebreak -->", "\\newpage"):
            apa_docx.salto_de_pagina(doc)
            i += 1
            continue

        # Bloques de código cercados (```lang ... ```)
        if stripped.startswith("```"):
            lenguaje = stripped[3:].strip()
            bloque_cod: List[str] = []
            i += 1
            while i < total and not lineas[i].strip().startswith("```"):
                bloque_cod.append(lineas[i])
                i += 1
            if i < total:
                i += 1
            bloques.codigo_bloque(
                doc,
                "\n".join(bloque_cod),
                etiqueta=lenguaje or None,
                fuente_pie=tema_obj.fuente,
            )
            continue

        # Ecuaciones matemáticas OMML ($$ ... $$)
        if stripped.startswith("$$"):
            leyenda = ""
            m_linea = re.match(r"^\$\$(.+?)\$\$(?:\s*\{leyenda\s*=\s*[\"']([^\"']+)[\"']\})?\s*$", stripped)
            if m_linea:
                expr = m_linea.group(1).strip()
                leyenda = m_linea.group(2) or ""
                i += 1
            else:
                expr_lineas: List[str] = []
                resto_ini = stripped[2:].strip()
                if resto_ini:
                    expr_lineas.append(resto_ini)
                i += 1
                while i < total and not lineas[i].strip().startswith("$$"):
                    expr_lineas.append(lineas[i])
                    i += 1
                if i < total:
                    cierre = lineas[i].strip()
                    m_ley = re.search(r'\{leyenda\s*=\s*["\']([^"\']+)["\']\}', cierre)
                    if m_ley:
                        leyenda = m_ley.group(1)
                    i += 1
                expr = " ".join(x.strip() for x in expr_lineas if x.strip())
            if i < total:
                m_com = re.match(r"^<!--\s*leyenda:\s*(.+?)\s*-->$", lineas[i].strip(), re.I)
                if m_com:
                    leyenda = m_com.group(1).strip()
                    i += 1
            omml.formula_bloque(doc, expr, leyenda)
            continue

        # Encabezados (#, ##, ###) con marcadores de rúbrica
        m_h = _RE_HEADING.match(stripped)
        if m_h:
            nivel = len(m_h.group(1))
            titulo_txt, crits = _extraer_atributos_encabezado(m_h.group(2))
            if nivel == 1 and rub.normalizar(titulo_txt) in _TITULOS_REF:
                if crits:
                    criterios_ref = crits
                i += 1
                continue
            apa_docx.titulo(doc, titulo_txt, nivel=nivel, criterios=crits or None)
            i += 1
            continue

        # Tablas Markdown (| col1 | col2 |)
        if "|" in stripped and i + 1 < total and _RE_SEP_TABLA.match(lineas[i + 1]):
            encabezados = [_resolver_citas_texto(c, bib) for c in _dividir_fila_tabla(stripped)]
            i += 2
            filas: List[List[str]] = []
            while i < total and "|" in lineas[i] and lineas[i].strip():
                fila = [_resolver_citas_texto(c, bib) for c in _dividir_fila_tabla(lineas[i])]
                while len(fila) < len(encabezados):
                    fila.append("")
                filas.append(fila[: len(encabezados)])
                i += 1
            bloques.tabla_academica(
                doc,
                encabezados,
                filas,
                estilo=tema_obj.estilo_tabla,
                fuente=tema_obj.fuente,
                tamano_cuerpo=max(tema_obj.tamano_cuerpo - 1.0, 9.0),
            )
            continue

        # Blockquotes (> **Etiqueta:** texto  o  > texto) -> enunciado_formal sin cajas coloreadas
        if stripped.startswith(">"):
            cita_lineas: List[str] = []
            while i < total and lineas[i].strip().startswith(">"):
                cita_lineas.append(lineas[i].strip().lstrip(">").strip())
                i += 1
            texto_cita = _resolver_citas_texto(" ".join(cita_lineas), bib)
            m_etq = re.match(r"^\*\*([^*]+?):\*\*\s*(.+)$", texto_cita)
            if m_etq:
                etq, cuerpo_etq = m_etq.group(1).strip(), m_etq.group(2).strip()
            else:
                etq, cuerpo_etq = "Nota", texto_cita
            bloques.enunciado_formal(
                doc,
                cuerpo_etq,
                numero="",
                etiqueta=etq,
                fuente=tema_obj.fuente,
            )
            continue

        # Imágenes / Figuras (![alt](ruta "pie"))
        m_img = _RE_IMAGEN.match(stripped)
        if m_img:
            alt = _resolver_citas_texto(m_img.group(1).strip(), bib)
            ruta_raw = m_img.group(2).strip()
            pie = _resolver_citas_texto((m_img.group(3) or alt).strip(), bib)
            cand_img = Path(ruta_raw)
            if not cand_img.is_absolute():
                if (origen.parent / cand_img).is_file():
                    cand_img = origen.parent / cand_img
                elif (carpeta_capturas / cand_img).is_file():
                    cand_img = carpeta_capturas / cand_img
            num_figura += 1
            bloques.caja_captura_evidencia(
                doc,
                cand_img,
                f"Figura {num_figura}. {pie or f'Evidencia {num_figura}'}",
                fuente=tema_obj.fuente,
            )
            i += 1
            continue

        # Listas con viñetas
        m_bul = _RE_LISTA_BULLET.match(linea)
        if m_bul:
            apa_docx.vinieta(doc, _resolver_citas_texto(m_bul.group(1).strip(), bib))
            i += 1
            continue

        # Listas numeradas
        m_num = _RE_LISTA_NUM.match(linea)
        if m_num:
            texto_item = f"{m_num.group(1)} {_resolver_citas_texto(m_num.group(2).strip(), bib)}"
            apa_docx.parrafo(doc, texto_item, sangria=False)
            i += 1
            continue

        # Comentarios HTML ignorados
        if stripped.startswith("<!--") and stripped.endswith("-->"):
            i += 1
            continue

        # Párrafo normal (agrupa líneas consecutivas no estructurales)
        parr_lineas: List[str] = [stripped]
        i += 1
        while i < total:
            sig = lineas[i].strip()
            if (
                not sig
                or sig.startswith("#")
                or sig.startswith("```")
                or sig.startswith("$$")
                or sig.startswith(">")
                or sig in ("---", "***", "<!-- pagebreak -->", "\\newpage")
                or _RE_IMAGEN.match(sig)
                or _RE_LISTA_BULLET.match(lineas[i])
                or _RE_LISTA_NUM.match(lineas[i])
                or ("|" in sig and i + 1 < total and _RE_SEP_TABLA.match(lineas[i + 1]))
            ):
                break
            parr_lineas.append(sig)
            i += 1
        texto_parr = _resolver_citas_texto(" ".join(parr_lineas), bib)
        apa_docx.parrafo(doc, texto_parr)

    # Criterios transversales declarados en frontmatter
    transv = meta.get("transversales") or []
    if isinstance(transv, str):
        transv = [x.strip() for x in re.split(r"[,\s]+", transv) if x.strip()]
    if transv and doc.paragraphs:
        apa_docx.transversal(doc, *[str(x) for x in transv])

    # Referencias automáticas si se citaron fuentes
    if bib._citadas:
        apa_docx.referencias(doc, bib, criterios=criterios_ref)

    apa_docx.guardar_documento(doc, ruta_salida)
    return ruta_salida
