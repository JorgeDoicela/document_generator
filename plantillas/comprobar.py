# -*- coding: utf-8 -*-
"""Comprueba un entregable .docx contra la rúbrica de su TAREA.md.

No se fía de lo que diga el script ni el agente: abre el .docx generado y
mira qué hay de verdad.

  - cobertura: cada criterio debe tener una sección marcada con su ID
    (`titulo(..., criterios="C1")`), estar declarado como transversal, o como
    mínimo una sección cuyo título se le parezca (cobertura "probable");
  - proporción: la extensión de cada sección frente al peso del criterio;
  - extensión total frente a la que pide TAREA.md;
  - restos: capturas que faltan, secciones vacías, TODO, [COMPLETAR];
  - citas APA: cada cita del texto tiene su referencia y viceversa;
  - frescura: el .docx es más nuevo que generar_documento.py, el .pdf que el .docx.
"""
import datetime
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import ficha
    import rubrica as rub
else:
    from . import ficha
    from . import rubrica as rub


TITULOS_REFERENCIAS = {"referencias", "referencias bibliograficas", "bibliografia", "references"}
_ANEXO = re.compile(r"^(anexo|apendice|apéndice|appendix)", re.I)
_PENDIENTE = re.compile(
    r"\[(?:FALTA|COMPLETAR|TODO|PENDIENTE)[^\]]*\]|\bFIXME\b|\bTODO:\b|\bPENDIENTE:\b|\blorem ipsum\b|(?-i:\bTODO\b)",
    re.I,
)
_PALABRA = re.compile(r"\w+(?:[-'’]\w+)*")
_ANIO = r"(?:(?:1[89]|20)\d{2}[a-z]?|s\.\s?f\.)"
_APELLIDO = r"[A-ZÁÉÍÓÚÑÜ][\wÁÉÍÓÚÑÜáéíóúñü'’-]+(?:\s(?:de|del|van|von|la)\s[A-ZÁÉÍÓÚÑ][\wáéíóúñ'’-]+)?"
_AUTOR_CORPORATIVO = (
    r"[A-ZÁÉÍÓÚÑÜ][\wÁÉÍÓÚÑÜáéíóúñü'’-]+"
    r"(?:\s+(?:(?:de|del|la|las|los|el|y|e|of|for|and|the)\s+)*[A-ZÁÉÍÓÚÑÜ][\wÁÉÍÓÚÑÜáéíóúñü'’-]+){2,}"
)
_CITA_NARRATIVA = re.compile(rf"({_APELLIDO})(?:\set\sal\.|\s(?:y|e|&)\s{_APELLIDO})?\s\(({_ANIO})")
_PARENTESIS = re.compile(r"\(([^()]+)\)")
_PARTE_CITA = re.compile(rf"^(?:véase\s|ver\s|cf\.\s)?({_APELLIDO})(?:\set\sal\.|\s(?:y|e|&)\s.+?)?,\s({_ANIO})")
_PARTE_CITA_CORP = re.compile(rf"^(?:véase\s|ver\s|cf\.\s)?({_AUTOR_CORPORATIVO}),\s({_ANIO})")
_CITA_IEEE = re.compile(r"(?<![A-Za-z0-9_])\[([1-9]\d*(?:\s*(?:,|[-–])\s*[1-9]\d*)*)(?:,\s*(?:p\.|pp\.|sec\.|cap\.)\s*[^]]+)?\]")
_CITA_VANCOUVER = re.compile(r"(?<![A-Za-z0-9_])\(([1-9]\d*(?:\s*(?:,|[-–])\s*[1-9]\d*)*)(?:,\s*(?:p\.|pp\.)\s*[^)]+)?\)")
_REF_IEEE = re.compile(r"^\[(\d+)\]\s+")
_REF_VANCOUVER = re.compile(r"^(\d+)\.\s+")
_PALABRAS_VACIAS = set(
    "para como sobre entre desde hasta donde cuando cada todo toda todos todas este esta estos "
    "estas ese esa con sin por los las del una uno unos unas que sus otro otra mediante "
    "correcto correcta correctamente adecuado adecuada adecuadamente claro clara claramente "
    "estudiante presenta explica describe realiza incluye elabora identifica muestra".split()
)

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
M = "{http://schemas.openxmlformats.org/officeDocument/2006/math}"
_PATRON_LATEX = re.compile(
    r"\\(?:forall|exists|land|lor|implies|Rightarrow|iff|Leftrightarrow|text|mathcal|mathrm|"
    r"sqcap|sqcup|sqsubseteq|in|cup|cap|times|Big|big|left|right|langle|rangle|neg|lnot|"
    r"frac|sqrt|sum|prod|leq|geq|neq|equiv|subseteq)\b"
)


def palabras(texto: str) -> int:
    return len(_PALABRA.findall(texto))


# --------------------------------------------------------------------------
# Análisis del .docx
# --------------------------------------------------------------------------
@dataclass
class Seccion:
    titulo: str
    nivel: int
    criterios: list = field(default_factory=list)
    palabras: int = 0
    figuras: int = 0
    tablas: int = 0
    anexo: bool = False
    referencias: bool = False

    @property
    def vacia(self) -> bool:
        return not (self.palabras or self.figuras or self.tablas)


@dataclass
class Analisis:
    secciones: list = field(default_factory=list)
    palabras_cuerpo: int = 0
    referencias: list = field(default_factory=list)
    hay_seccion_referencias: bool = False
    transversales: set = field(default_factory=set)
    pendientes: list = field(default_factory=list)   # (sección, texto)
    citas: list = field(default_factory=list)         # (apellido, año, contexto)
    citas_ieee: list = field(default_factory=list)    # (numero, contexto)
    citas_vancouver: list = field(default_factory=list)  # (numero, contexto)
    anomalias_formato: list = field(default_factory=list)
    avisos_tipograficos: list = field(default_factory=list)


def _texto(p) -> str:
    return "".join(t.text or "" for t in p.iter(W + "t"))


def _estilo(p, estilos) -> str:
    ppr = p.find(W + "pPr")
    est = ppr.find(W + "pStyle") if ppr is not None else None
    return estilos.get(est.get(W + "val"), "") if est is not None else ""


def _nivel(p, estilos) -> int | None:
    nombre = _estilo(p, estilos).lower()
    m = re.match(r"(heading|título|titulo)\s*(\d)", nombre)
    if m:
        return int(m[2])
    ppr = p.find(W + "pPr")
    lvl = ppr.find(W + "outlineLvl") if ppr is not None else None
    if lvl is not None and lvl.get(W + "val", "9").isdigit() and int(lvl.get(W + "val")) < 9:
        return int(lvl.get(W + "val")) + 1
    return None


def _salto_de_pagina(p) -> bool:
    return any(br.get(W + "type") == "page" for br in p.iter(W + "br"))


def _citas(texto: str):
    for m in _CITA_NARRATIVA.finditer(texto):
        yield m[1], m[2].replace(" ", "")
    for m in _PARENTESIS.finditer(texto):
        for parte in m[1].split(";"):
            p_limpia = parte.strip()
            c = _PARTE_CITA.match(p_limpia) or _PARTE_CITA_CORP.match(p_limpia)
            if c:
                yield c[1], c[2].replace(" ", "")


def _expandir_numeros(spec: str) -> list[int]:
    """Expande '1, 2-4' en [1, 2, 3, 4]."""
    nums: list[int] = []
    for parte in spec.split(","):
        p = parte.strip()
        if not p:
            continue
        rango = re.match(r"^(\d+)\s*[-–]\s*(\d+)$", p)
        if rango:
            ini, fin = int(rango.group(1)), int(rango.group(2))
            if ini <= fin and (fin - ini) <= 50:
                nums.extend(range(ini, fin + 1))
        elif p.isdigit():
            nums.append(int(p))
    return nums


def _citas_numericas(texto: str, patron: re.Pattern):
    for m in patron.finditer(texto):
        for n in _expandir_numeros(m.group(1)):
            yield n


def analizar(ruta_docx: Path) -> Analisis:
    from docx import Document

    doc = Document(str(ruta_docx))
    estilos = {s.style_id: s.name for s in doc.styles}
    titulo_doc = (doc.core_properties.title or "").strip()
    a = Analisis()
    abiertas: list[Seccion] = []
    cuerpo = list(doc.element.body.iterchildren())

    # Verificación de integridad en encabezados y pies de página
    for num_sec, sec in enumerate(doc.sections, 1):
        for tipo, contenedor in (("encabezado", sec.header), ("pie de página", sec.footer)):
            for p in contenedor.paragraphs:
                paginas = sum(1 for el in p._p.iter(W + "instrText") if "PAGE" in (el.text or "").upper())
                if paginas > 1:
                    a.anomalias_formato.append(
                        f"Numeración duplicada ({paginas} campos PAGE) en el {tipo} de la sección {num_sec}."
                    )
                dibujos = list(p._p.iter(W + "drawing"))
                if len(dibujos) > 1:
                    a.anomalias_formato.append(
                        f"Imágenes duplicadas ({len(dibujos)} elementos drawing) en el {tipo} de la sección {num_sec}."
                    )

    # La portada termina en el primer salto de página (si lo hay).
    inicio = 0
    for i, el in enumerate(cuerpo):
        if el.tag == W + "p" and _salto_de_pagina(el):
            inicio = i + 1
            break

    en_indice = False
    titulo_visto = False
    for el in cuerpo[inicio:]:
        if el.tag == W + "tbl":
            for s in abiertas:
                s.tablas += 1
            # Auditoría estética: prohibir cajas tipo callout con barra lateral izquierda (w:left grueso)
            filas_tbl = el.findall(W + "tr")
            if len(filas_tbl) == 1:
                celdas_tbl = filas_tbl[0].findall(W + "tc")
                if len(celdas_tbl) == 1:
                    tc_pr = celdas_tbl[0].find(W + "tcPr")
                    tc_bdr = tc_pr.find(W + "tcBorders") if tc_pr is not None else None
                    tbl_pr = el.find(W + "tblPr")
                    tbl_bdr = tbl_pr.find(W + "tblBorders") if tbl_pr is not None else None
                    for bdr in (tc_bdr, tbl_bdr):
                        if bdr is None:
                            continue
                        left_b = bdr.find(W + "left")
                        right_b = bdr.find(W + "right")
                        if left_b is not None:
                            sz_left = int(left_b.get(W + "sz", "0") or 0)
                            val_left = left_b.get(W + "val", "none")
                            sz_right = int(right_b.get(W + "sz", "0") or 0) if right_b is not None else 0
                            if val_left not in ("none", "nil") and sz_left >= 18 and sz_left > sz_right * 2:
                                a.avisos_tipograficos.append(
                                    "Caja de celda única con barra vertical izquierda de acento (estilo callout IA). "
                                    "Elimina la barra lateral y utiliza enunciado_formal() o párrafos limpios."
                                )
                                break
            # Detectar si la tabla es un bloque de código estilizado (2x1 con fuente monoespaciada)
            es_bloque_codigo = False
            if len(filas_tbl) == 2 and all(len(tr.findall(W + "tc")) == 1 for tr in filas_tbl):
                fuentes_tbl = {
                    (rf.get(W + "ascii") or rf.get(W + "hAnsi") or "").lower()
                    for rf in el.iter(W + "rFonts")
                }
                if fuentes_tbl and fuentes_tbl <= {"consolas", "courier new", "inconsolata", "dejavu sans mono", ""}:
                    es_bloque_codigo = True

            if not es_bloque_codigo:
                for p_celda in el.iter(W + "p"):
                    txt_c = _texto(p_celda).strip()
                    if not txt_c:
                        continue
                    for m in _PENDIENTE.finditer(txt_c):
                        a.pendientes.append((abiertas[-1].titulo if abiertas else "tabla", m[0]))
                    for apellido, anio in _citas(txt_c):
                        a.citas.append((apellido, anio, txt_c[:60]))
                    for num in _citas_numericas(txt_c, _CITA_IEEE):
                        a.citas_ieee.append((num, txt_c[:60]))
                    for num in _citas_numericas(txt_c, _CITA_VANCOUVER):
                        a.citas_vancouver.append((num, txt_c[:60]))
                    if "**" in txt_c:
                        a.avisos_tipograficos.append(
                            f"Fuga de sintaxis Markdown en tabla (asteriscos literales '**'): «{txt_c[:50]}...»."
                        )
                    txt_omml_c = "".join(t.text or "" for t in p_celda.iter(M + "t"))
                    if _PATRON_LATEX.search(txt_c) or _PATRON_LATEX.search(txt_omml_c):
                        muestra = (txt_omml_c or txt_c).strip()[:70]
                        a.anomalias_formato.append(
                            f"Fuga de comandos LaTeX crudos en tabla/OMML (provoca '¿' en PDF): «{muestra}»."
                        )
            continue
        if el.tag != W + "p":
            continue
        instr = " ".join(t.text or "" for t in el.iter(W + "instrText"))
        if "TOC" in instr:
            en_indice = True
        if en_indice:
            en_indice = not _salto_de_pagina(el)
            continue
        texto = _texto(el).strip()
        marcas = [b.get(W + "name", "") for b in el.iter(W + "bookmarkStart")]
        marcas = [m[len("rubrica_"):] for m in marcas if m.startswith("rubrica_")]
        for m in marcas:
            if m.endswith("_todo"):
                a.transversales.add(m[:-5].upper())
        marcas = [m.upper() for m in marcas if not m.endswith("_todo")]

        # Verificación de integridad tipográfica: saltos de línea en párrafos justificados
        ppr = el.find(W + "pPr")
        jc = ppr.find(W + "jc") if ppr is not None else None
        val_jc = jc.get(W + "val") if jc is not None else ""
        if val_jc == "both":
            tiene_nl = any("\n" in (t.text or "") for t in el.iter(W + "t"))
            tiene_soft_br = any(br.get(W + "type") != "page" for br in el.iter(W + "br"))
            if tiene_nl or tiene_soft_br:
                a.avisos_tipograficos.append(
                    f"Párrafo con justificación forzada y saltos de línea internos (\\n o w:br): «{texto[:50]}...». "
                    f"Divide el texto en párrafos o listas independientes para prevenir estiramiento de líneas."
                )

        # Verificación de fuga de sintaxis Markdown (asteriscos literales)
        if "**" in texto:
            a.avisos_tipograficos.append(
                f"Fuga de sintaxis Markdown (asteriscos literales '**'): «{texto[:50]}...». "
                f"Asegúrate de procesar negritas en runs nativos de Word sin dejar caracteres de marcado."
            )

        # Verificación de fuga de comandos LaTeX crudos en párrafos u OMML (\forall, \text{, \mathcal{, \implies, etc.)
        texto_omml = "".join(t.text or "" for t in el.iter(M + "t"))
        if _PATRON_LATEX.search(texto) or _PATRON_LATEX.search(texto_omml):
            muestra = (texto_omml or texto).strip()[:70]
            a.anomalias_formato.append(
                f"Fuga de comandos LaTeX crudos en documento/OMML (provoca '¿' en PDF): «{muestra}». "
                f"Normaliza la fórmula a Unicode matemático mediante normalizar_latex_a_unicode() o formula_bloque()."
            )

        # Verificación de pie de figura duplicado ('Figura: Figura ...' o doble punto '..')
        if re.match(r"^figura:\s*figura\b", texto.strip(), re.I) or (
            re.match(r"^figura\b", texto.strip(), re.I) and texto.strip().endswith("..")
        ):
            a.avisos_tipograficos.append(
                f"Pie de figura con prefijo duplicado o doble punto final: «{texto.strip()[:70]}»."
            )

        # Verificación estética: prohibir párrafos con barra vertical izquierda de acento (w:pBdr/w:left grueso)
        p_bdr = ppr.find(W + "pBdr") if ppr is not None else None
        if p_bdr is not None:
            left_pb = p_bdr.find(W + "left")
            right_pb = p_bdr.find(W + "right")
            if left_pb is not None:
                sz_l = int(left_pb.get(W + "sz", "0") or 0)
                val_l = left_pb.get(W + "val", "none")
                sz_r = int(right_pb.get(W + "sz", "0") or 0) if right_pb is not None else 0
                if val_l not in ("none", "nil") and sz_l >= 18 and sz_l > sz_r * 2:
                    a.avisos_tipograficos.append(
                        f"Párrafo con barra vertical izquierda de acento (estilo callout IA): «{texto[:50]}...». "
                        f"Elimina el borde izquierdo grueso y usa tipografía limpia sobre el lienzo."
                    )

        nivel = _nivel(el, estilos)
        if nivel is not None and texto:
            abiertas = [s for s in abiertas if s.nivel < nivel]
            padre_anexo = any(s.anexo for s in abiertas)
            s = Seccion(texto, nivel, marcas, anexo=padre_anexo or bool(_ANEXO.match(texto)))
            if nivel == 1 and rub.normalizar(texto) in TITULOS_REFERENCIAS:
                s.referencias = True
                a.hay_seccion_referencias = True
            a.secciones.append(s)
            abiertas.append(s)
            continue
        if marcas and abiertas:
            abiertas[-1].criterios += marcas

        if not titulo_visto and texto:
            titulo_visto = True
            if titulo_doc and texto == titulo_doc:
                continue  # el título repetido al inicio del cuerpo

        en_referencias = any(s.referencias for s in abiertas)
        if en_referencias:
            if texto:
                a.referencias.append(texto)
            continue
        n = palabras(texto)
        figuras = sum(1 for _ in el.iter(W + "drawing"))
        for s in abiertas:
            s.palabras += n
            s.figuras += figuras
        if not any(s.anexo for s in abiertas):
            a.palabras_cuerpo += n
        for m in _PENDIENTE.finditer(texto):
            a.pendientes.append((abiertas[-1].titulo if abiertas else "inicio", m[0]))
        for apellido, anio in _citas(texto):
            a.citas.append((apellido, anio, texto[:60]))
        for num in _citas_numericas(texto, _CITA_IEEE):
            a.citas_ieee.append((num, texto[:60]))
        for num in _citas_numericas(texto, _CITA_VANCOUVER):
            a.citas_vancouver.append((num, texto[:60]))
    return a


# --------------------------------------------------------------------------
# Cruce con la rúbrica
# --------------------------------------------------------------------------
def _raices(texto: str) -> set:
    return {w[:5] for w in re.findall(r"[a-z0-9]+", rub.normalizar(texto))
            if len(w) >= 4 and w not in _PALABRAS_VACIAS}


def _parecido(criterio: str, titulo: str) -> float:
    a, b = _raices(criterio), _raices(titulo)
    if not a or not b:
        return 0.0
    return len(a & b) / min(len(a), len(b))


@dataclass
class Cobertura:
    criterio: rub.Criterio
    modo: str | None = None          # marcado | transversal | referencias | probable | None
    secciones: list = field(default_factory=list)
    palabras: int = 0
    figuras: int = 0
    tablas: int = 0
    esperado: int | None = None

    @property
    def cubierto(self) -> bool:
        return self.modo is not None

    @property
    def ratio(self) -> float | None:
        if not self.esperado:
            return None
        return self.palabras / self.esperado

    def donde(self) -> str:
        if self.modo is None:
            return "SIN CUBRIR"
        if self.modo == "transversal":
            return "todo el documento"
        nombres = "; ".join(s.titulo for s in self.secciones)
        if self.modo == "referencias":
            return nombres
        texto = f"{nombres} ({self.palabras} pal."
        texto += f", {self.figuras} fig." if self.figuras else ""
        texto += f", {self.tablas} tabla{'s' if self.tablas > 1 else ''}" if self.tablas else ""
        texto += ")"
        return texto + (" — probable, sin marcar" if self.modo == "probable" else "")


def cruzar(criterios: list, a: Analisis) -> list:
    coberturas = []
    for c in criterios:
        cob = Cobertura(c)
        marcadas = [s for s in a.secciones if c.id in s.criterios]
        if marcadas:
            cob.modo = "referencias" if all(s.referencias for s in marcadas) else "marcado"
            cob.secciones = marcadas
        elif c.id in a.transversales:
            cob.modo = "transversal"
        else:
            candidatas = [(round(_parecido(c.texto, s.titulo), 2), s) for s in a.secciones
                          if not s.criterios]
            candidatas = [x for x in candidatas if x[0] >= 0.5]
            if candidatas:
                cob.modo = "probable"
                cob.secciones = [max(candidatas, key=lambda x: x[0])[1]]
        for s in cob.secciones:
            # Una sección que cubre varios criterios reparte su extensión.
            compartida = max(1, len(s.criterios))
            cob.palabras += s.palabras // compartida
            cob.figuras += s.figuras
            cob.tablas += s.tablas
        coberturas.append(cob)

    # Reparto esperado de la extensión según el peso de cada criterio.
    con_seccion = [c for c in coberturas if c.modo in ("marcado", "probable")]
    if con_seccion:
        pesos_brutos = [c.criterio.puntaje for c in con_seccion]
        if any(p is None for p in pesos_brutos):
            pesos: list[float] = [1.0] * len(con_seccion)
        else:
            pesos = [float(p) for p in pesos_brutos if p is not None]
        total_pesos = sum(pesos) or 1.0
        total_palabras = sum(c.palabras for c in con_seccion)
        for c, peso in zip(con_seccion, pesos, strict=False):
            c.esperado = round(total_palabras * peso / total_pesos)

    return coberturas



# --------------------------------------------------------------------------
# Informe
# --------------------------------------------------------------------------
@dataclass
class Informe:
    docx: Path | None
    coberturas: list = field(default_factory=list)
    errores: list = field(default_factory=list)
    avisos: list = field(default_factory=list)
    analisis: Analisis | None = None

    @property
    def ok(self) -> bool:
        return not self.errores

    @property
    def puntos(self) -> tuple[float, float]:
        total = sum(c.criterio.puntaje or 0 for c in self.coberturas)
        cubiertos = sum(c.criterio.puntaje or 0 for c in self.coberturas if c.cubierto)
        return cubiertos, total


def buscar_docx(carpeta: Path) -> Path | None:
    candidatos = [p for p in Path(carpeta).glob("*.docx") if not p.name.startswith("~$")]
    if not candidatos:
        return None

    # 1. Si generar_documento.py declara una SALIDA explícita, priorizarla
    script = Path(carpeta) / "generar_documento.py"
    if script.exists():
        try:
            contenido = script.read_text(encoding="utf-8")
            m = re.search(r'SALIDA\s*=\s*AQUI\s*/\s*["\']([^"\']+\.docx)["\']', contenido)
            if m:
                esperado = Path(carpeta) / m.group(1)
                if esperado.exists():
                    return esperado
        except Exception:
            pass

    # 2. Archivos que inician con el nombre completo de la carpeta o el código de la tarea
    nombre_carpeta = Path(carpeta).name
    codigo = nombre_carpeta.split("_")[0]
    propios = [
        p for p in candidatos
        if p.name.startswith(nombre_carpeta + "_") or p.name.startswith(codigo + "_")
    ]
    if propios:
        return max(propios, key=lambda p: p.stat().st_mtime)

    # 3. Entregables en formato grupal (p. ej. grupo_1_...)
    grupales = [p for p in candidatos if "grupo" in p.name.lower()]
    if grupales:
        return max(grupales, key=lambda p: p.stat().st_mtime)

    return max(candidatos, key=lambda p: p.stat().st_mtime)


def _coincide(apellido: str, anio: str, referencia: str) -> bool:
    """¿La entrada de referencias empieza por ese autor (personal o institucional) y lleva ese año?"""
    entrada = rub.normalizar(referencia.lstrip("*"))
    if re.search(r"\(" + re.escape(anio.lower()), entrada) is None:
        return False
    autor_norm = rub.normalizar(apellido)
    if entrada.startswith(autor_norm):
        return True
    primer_autor = re.split(r"\s+(?:y|e|&|et\s+al\.?)(?=\s|$)", autor_norm, maxsplit=1)[0].strip()
    return bool(primer_autor) and entrada.startswith(primer_autor)


def comprobar(carpeta: Path, docx: Path | None = None, hoy: datetime.date | None = None) -> Informe:
    carpeta = Path(carpeta).resolve()
    tarea = ficha.leer_tarea(carpeta)
    criterios = rub.leer(tarea.ruta)
    docx = Path(docx) if docx else buscar_docx(carpeta)
    inf = Informe(docx)

    if not criterios:
        inf.errores.append("TAREA.md no tiene rúbrica: añade los criterios a la tabla "
                           "(o `tareas.py rubrica --importar <archivo.docx>`).")
    if docx is None or not docx.exists():
        inf.coberturas = [Cobertura(c) for c in criterios]
        if tarea.estado == "pendiente":
            inf.avisos.append("Tarea en estado 'pendiente': aún no se ha generado el archivo .docx (ejecuta `tareas.py generar`).")
        else:
            inf.errores.append("No hay ningún .docx generado en la carpeta: ejecuta "
                               "`tareas.py generar`.")
        return inf

    a = inf.analisis = analizar(docx)
    inf.coberturas = cruzar(criterios, a)

    for cob in inf.coberturas:
        c = cob.criterio
        if not cob.cubierto:
            inf.errores.append(f"{c.id} sin cubrir: «{c.texto}». Márcalo con "
                               f"titulo(doc, ..., criterios=\"{c.id}\") o transversal(doc, \"{c.id}\").")
            continue
        if cob.modo == "probable":
            inf.avisos.append(f"{c.id} se asoció por el título a «{cob.secciones[0].titulo}»; "
                              f"márcalo con criterios=\"{c.id}\" para que sea seguro.")
        if cob.modo in ("marcado", "probable") and all(s.vacia for s in cob.secciones):
            inf.errores.append(f"{c.id}: la sección «{cob.secciones[0].titulo}» está vacía.")
        elif cob.ratio is not None and cob.ratio < 0.5:
            inf.avisos.append(f"{c.id} poco desarrollado: {cob.palabras} palabras frente a "
                              f"~{cob.esperado} según su peso ({formato_puntaje(c)}).")
        elif cob.ratio is not None and cob.ratio > 2.0 and cob.palabras > 150:
            inf.avisos.append(f"{c.id} desproporcionado: {cob.palabras} palabras frente a "
                              f"~{cob.esperado} según su peso ({formato_puntaje(c)}).")

    ids = {c.id for c in criterios}
    marcados = {i for s in a.secciones for i in s.criterios} | a.transversales
    for extra in sorted(marcados - ids):
        inf.avisos.append(f"El documento marca {extra}, que no está en la rúbrica de TAREA.md.")

    for s in a.secciones:
        if s.vacia and not s.referencias and not s.criterios:
            inf.avisos.append(f"La sección «{s.titulo}» está vacía.")
    for seccion, texto in a.pendientes:
        inf.errores.append(f"Contenido pendiente en «{seccion}»: {texto}")

    if tarea.extension:
        if a.palabras_cuerpo < 0.8 * tarea.extension:
            inf.avisos.append(f"Extensión corta: {a.palabras_cuerpo} palabras frente a "
                              f"~{tarea.extension} que pide TAREA.md.")
        elif a.palabras_cuerpo > 1.25 * tarea.extension:
            inf.avisos.append(f"Extensión larga: {a.palabras_cuerpo} palabras frente a "
                              f"~{tarea.extension} que pide TAREA.md.")

    # Citas y referencias
    for anomalia in a.anomalias_formato:
        inf.errores.append(f"Error de formato documental: {anomalia}")
    for aviso in a.avisos_tipograficos:
        inf.avisos.append(f"Aviso de formato tipográfico: {aviso}")

    if (a.citas or a.citas_ieee) and not a.hay_seccion_referencias:
        total_c = len(a.citas) or len(a.citas_ieee)
        inf.errores.append(f"Hay {total_c} citas en el texto pero no hay sección Referencias.")
    elif a.hay_seccion_referencias:
        if not a.referencias:
            inf.avisos.append("La sección Referencias está vacía.")
        else:
            refs_ieee = {
                int(m.group(1)): r
                for r in a.referencias
                if (m := _REF_IEEE.match(r.strip()))
            }
            refs_van = {
                int(m.group(1)): r
                for r in a.referencias
                if (m := _REF_VANCOUVER.match(r.strip()))
            }
            if refs_ieee and len(refs_ieee) >= len(a.referencias) / 2:
                citados = {n for n, _ in a.citas_ieee}
                for n in sorted(citados - set(refs_ieee)):
                    inf.errores.append(f"Cita numérica sin referencia: [{n}].")
                for n, r in refs_ieee.items():
                    if n not in citados:
                        inf.avisos.append(f"Referencia que no se cita en el texto: {r[:70]}")
            elif refs_van and len(refs_van) >= len(a.referencias) / 2:
                citados = {n for n, _ in a.citas_vancouver}
                for n in sorted(citados - set(refs_van)):
                    inf.errores.append(f"Cita numérica sin referencia: ({n}).")
                for n, r in refs_van.items():
                    if n not in citados:
                        inf.avisos.append(f"Referencia que no se cita en el texto: {r[:70]}")
            else:
                huerfanas = sorted({(ap, an) for ap, an, _ in a.citas
                                    if not any(_coincide(ap, an, r) for r in a.referencias)})
                for ap, an in huerfanas:
                    inf.errores.append(f"Cita sin referencia: {ap} ({an}).")
                for r in a.referencias:
                    if not any(_coincide(ap, an, r) for ap, an, _ in a.citas):
                        inf.avisos.append(f"Referencia que no se cita en el texto: {r[:70]}")

    # Frescura de los archivos
    script = carpeta / "generar_documento.py"
    if script.exists() and script.stat().st_mtime > docx.stat().st_mtime + 1:
        inf.avisos.append("generar_documento.py es más reciente que el .docx: regenéralo.")
    pdf = docx.with_suffix(".pdf")
    if pdf.exists() and pdf.stat().st_mtime + 1 < docx.stat().st_mtime:
        inf.avisos.append("El .pdf es más antiguo que el .docx: vuelve a convertirlo.")

    hoy = hoy or datetime.date.today()
    if tarea.fecha and tarea.fecha < hoy and tarea.estado == "pendiente":
        inf.avisos.append(f"La fecha de entrega ({tarea.fecha}) ya pasó y la tarea sigue pendiente.")
    return inf


def formato_puntaje(c: rub.Criterio) -> str:
    return f"{rub.formatear_puntaje(c.puntaje)} pts" if c.puntaje is not None else "sin puntaje"


def actualizar_tarea(carpeta: Path, inf: Informe) -> None:
    """Rellena la columna 'Dónde se cumple' de TAREA.md con lo comprobado."""
    criterios = [cob.criterio for cob in inf.coberturas]
    for cob in inf.coberturas:
        cob.criterio.donde = cob.donde()
    if criterios:
        rub.escribir(Path(carpeta) / "TAREA.md", criterios)


def imprimir(inf: Informe, carpeta: Path) -> None:
    print(f"Comprobación de {Path(carpeta).name}")
    if inf.docx:
        print(f"  Documento: {inf.docx.name}")
    if inf.analisis:
        a = inf.analisis
        if a.referencias and any(_REF_IEEE.match(r.strip()) for r in a.referencias):
            total_citas = len(a.citas_ieee)
        elif a.referencias and any(_REF_VANCOUVER.match(r.strip()) for r in a.referencias):
            total_citas = len(a.citas_vancouver)
        else:
            total_citas = len(a.citas)
        print(f"  Cuerpo: {a.palabras_cuerpo} palabras, {len(a.secciones)} secciones, "
              f"{total_citas} citas, {len(a.referencias)} referencias")
    if inf.coberturas:
        print("\n  Rúbrica")
        ancho = max(len(c.criterio.id) for c in inf.coberturas)
        for cob in inf.coberturas:
            c = cob.criterio
            marca = {"marcado": "[ok]   ", "transversal": "[ok]   ", "referencias": "[ok]   ",
                     "probable": "[~]    ", None: "[falta]"}[cob.modo]
            peso = formato_puntaje(c)
            print(f"  {marca} {c.id:<{ancho}}  {c.texto[:48]:<48}  {peso:>9}  → {cob.donde()}")
        cubiertos, total = inf.puntos
        if total:
            print(f"\n  Puntos con sección que los cubre: {rub.formatear_puntaje(cubiertos)} "
                  f"de {rub.formatear_puntaje(total)}")
    for e in inf.errores:
        print("  [error] " + e)
    for w in inf.avisos:
        print("  [aviso] " + w)
    if inf.ok and not inf.avisos:
        print("  Todo en orden.")


def auditar_todo(raiz_materias: Path, solo_materia: str | None = None) -> list[tuple[Path, Informe]]:
    """Busca recursivamente todas las tareas y ejecuta su comprobación estática."""
    raiz = Path(raiz_materias)
    if not raiz.is_dir():
        return []
    materias = [raiz / solo_materia] if solo_materia else sorted(p for p in raiz.iterdir() if p.is_dir())
    resultados: list[tuple[Path, Informe]] = []
    for m in materias:
        if not m.is_dir():
            continue
        for carpeta in sorted(p for p in m.iterdir() if (p / "TAREA.md").exists()):
            inf = comprobar(carpeta)
            resultados.append((carpeta, inf))
    return resultados


def imprimir_auditoria_global(resultados: list[tuple[Path, Informe]]) -> bool:
    """Imprime una tabla consolidada de auditoría. Devuelve True si todas pasaron sin errores."""
    if not resultados:
        print("No se encontraron tareas para auditar.")
        return True

    print(f"{'Materia':<15}  {'Tarea':<36}  {'Rúbrica':<12}  {'Citas':<7}  {'Palabras':>8}  {'Errores':>7}  Estado")
    print("-" * 96)

    total_errores = 0
    total_avisos = 0
    total_criterios_cubiertos = 0
    total_criterios = 0

    for carpeta, inf in resultados:
        materia_nombre = carpeta.parent.name
        tarea_nombre = carpeta.name

        cubiertos = sum(1 for c in inf.coberturas if c.cubierto)
        n_criterios = len(inf.coberturas)
        total_criterios_cubiertos += cubiertos
        total_criterios += n_criterios

        cobertura_str = f"{cubiertos}/{n_criterios}" if n_criterios else "sin rúbrica"
        num_citas = len(inf.analisis.citas) if inf.analisis else 0
        palabras = inf.analisis.palabras_cuerpo if inf.analisis else 0
        n_err = len(inf.errores)
        n_avi = len(inf.avisos)
        total_errores += n_err
        total_avisos += n_avi

        if n_err > 0:
            estado = "[ERROR]"
        elif n_avi > 0:
            estado = "[AVISO]"
        else:
            estado = "[OK]"

        print(
            f"{materia_nombre[:15]:<15}  "
            f"{tarea_nombre[:36]:<36}  "
            f"{cobertura_str:<12}  "
            f"{num_citas:<7}  "
            f"{palabras:>8}  "
            f"{n_err:>7}  "
            f"{estado}"
        )

    print("-" * 96)
    print(
        f"Total: {len(resultados)} tareas auditadas | "
        f"Criterios cubiertos: {total_criterios_cubiertos}/{total_criterios} | "
        f"Errores: {total_errores} | Avisos: {total_avisos}"
    )

    if total_errores == 0:
        print("\nAuditoría superada: todos los documentos cumplen con los requisitos estáticos.")
        return True
    else:
        print(f"\nAuditoría fallida: se detectaron {total_errores} errores en los entregables.")
        return False

