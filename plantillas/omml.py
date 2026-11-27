# -*- coding: utf-8 -*-
"""Motor matemático OMML (Office Math Markup Language) para WordML y LibreOffice.

Convierte expresiones matemáticas y lógicas (incluyendo comandos LaTeX comunes,
superíndices y subíndices) en nodos OMML vectoriales nativos (<m:oMathPara>),
normalizando a Unicode compatible con Cambria Math para evitar caracteres rotos ('¿')
y segmentando fórmulas extensas para prevenir desbordamiento horizontal.
"""
import inspect
import re
from typing import Any, List, Optional
from xml.sax.saxutils import escape

from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import parse_xml
from docx.shared import Pt, RGBColor

GRIS_ETIQUETA = RGBColor(115, 115, 115)

_LATEX_COMANDOS_UNICODE = (
    # Lógica, cuantificadores y lógicas descriptivas
    (r"\\Longleftrightarrow\b", "⟺"),
    (r"\\Leftrightarrow\b", "⇔"),
    (r"\\iff\b", "⇔"),
    (r"\\Longrightarrow\b", "⟹"),
    (r"\\Rightarrow\b", "⇒"),
    (r"\\implies\b", "⇒"),
    (r"\\longleftrightarrow\b", "↔"),
    (r"\\leftrightarrow\b", "↔"),
    (r"\\longrightarrow\b", "→"),
    (r"\\rightarrow\b", "→"),
    (r"\\to\b", "→"),
    (r"\\leftarrow\b", "←"),
    (r"\\forall\b", "∀"),
    (r"\\nexists\b", "∄"),
    (r"\\exists\b", "∃"),
    (r"\\land\b", "∧"),
    (r"\\wedge\b", "∧"),
    (r"\\lor\b", "∨"),
    (r"\\vee\b", "∨"),
    (r"\\lnot\b", "¬"),
    (r"\\neg\b", "¬"),
    (r"\\equiv\b", "≡"),
    (r"\\models\b", "⊨"),
    (r"\\vdash\b", "⊢"),
    (r"\\top\b", "⊤"),
    (r"\\bot\b", "⊥"),
    (r"\\sqsubseteq\b", "⊑"),
    (r"\\sqsupseteq\b", "⊒"),
    (r"\\sqcap\b", "⊓"),
    (r"\\sqcup\b", "⊔"),
    # Conjuntos y relaciones
    (r"\\notin\b", "∉"),
    (r"\\in\b", "∈"),
    (r"\\subseteq\b", "⊆"),
    (r"\\supseteq\b", "⊇"),
    (r"\\subset\b", "⊂"),
    (r"\\supset\b", "⊃"),
    (r"\\cup\b", "∪"),
    (r"\\cap\b", "∩"),
    (r"\\setminus\b", "∖"),
    (r"\\emptyset\b", "∅"),
    (r"\\varnothing\b", "∅"),
    (r"\\times\b", "×"),
    (r"\\cdot\b", "·"),
    (r"\\circ\b", "∘"),
    (r"\\oplus\b", "⊕"),
    (r"\\otimes\b", "⊗"),
    (r"\\leq\b", "≤"),
    (r"\\le\b", "≤"),
    (r"\\geq\b", "≥"),
    (r"\\ge\b", "≥"),
    (r"\\neq\b", "≠"),
    (r"\\ne\b", "≠"),
    (r"\\approx\b", "≈"),
    (r"\\pm\b", "±"),
    (r"\\infty\b", "∞"),
    (r"\\sum\b", "∑"),
    (r"\\prod\b", "∏"),
    (r"\\langle\b", "⟨"),
    (r"\\rangle\b", "⟩"),
    (r"\\ldots\b", "…"),
    (r"\\cdots\b", "⋯"),
    # Letras griegas comunes
    (r"\\varepsilon\b", "ε"),
    (r"\\varphi\b", "φ"),
    (r"\\vartheta\b", "ϑ"),
    (r"\\alpha\b", "α"),
    (r"\\beta\b", "β"),
    (r"\\gamma\b", "γ"),
    (r"\\delta\b", "δ"),
    (r"\\epsilon\b", "ε"),
    (r"\\zeta\b", "ζ"),
    (r"\\eta\b", "η"),
    (r"\\theta\b", "θ"),
    (r"\\iota\b", "ι"),
    (r"\\kappa\b", "κ"),
    (r"\\lambda\b", "λ"),
    (r"\\mu\b", "μ"),
    (r"\\nu\b", "ν"),
    (r"\\xi\b", "ξ"),
    (r"\\pi\b", "π"),
    (r"\\rho\b", "ρ"),
    (r"\\sigma\b", "σ"),
    (r"\\tau\b", "τ"),
    (r"\\upsilon\b", "υ"),
    (r"\\phi\b", "φ"),
    (r"\\chi\b", "χ"),
    (r"\\psi\b", "ψ"),
    (r"\\omega\b", "ω"),
    (r"\\Gamma\b", "Γ"),
    (r"\\Delta\b", "Δ"),
    (r"\\Theta\b", "Θ"),
    (r"\\Lambda\b", "Λ"),
    (r"\\Xi\b", "Ξ"),
    (r"\\Pi\b", "Π"),
    (r"\\Sigma\b", "Σ"),
    (r"\\Phi\b", "Φ"),
    (r"\\Psi\b", "Ψ"),
    (r"\\Omega\b", "Ω"),
)


def normalizar_latex_a_unicode(formula: str) -> str:
    """Convierte comandos LaTeX a Unicode matemático compatible con Cambria Math / LibreOffice OMML.

    Elimina el riesgo de que LibreOffice interprete comandos LaTeX crudos (\\forall, \\text{},
    \\mathcal{}, \\Big()...) como caracteres inválidos ('¿') al convertir a PDF.
    """
    if not formula or "\\" not in formula:
        return formula

    s = formula
    for _ in range(4):
        nuevo = re.sub(
            r"\\(?:text|mathrm|mathbf|mathit|mathsf|mathtt|mathcal|mathbb|operatorname)\s*\{([^{}]*)\}",
            r"\1",
            s,
        )
        if nuevo == s:
            break
        s = nuevo

    s = re.sub(r"\\(?:left|right|Big|big|Bigg|bigg|bigl|bigr|Bigl|Bigr)\s*([()\[\]{}|.])", r"\1", s)
    s = s.replace(r"\{", "{").replace(r"\}", "}")

    for patron, reemplazo in _LATEX_COMANDOS_UNICODE:
        s = re.sub(patron, reemplazo, s)

    s = re.sub(r"\\(?:qquad|quad)", "  ", s)
    s = re.sub(r"\\[,;:!]", " ", s)
    s = re.sub(r"[ \t]{2,}", " ", s)
    return s.strip()


def texto_a_omml(formula: str) -> str:
    """Convierte una fórmula lógica o matemática a XML OMML nativo de WordML.

    Normaliza comandos LaTeX a Unicode matemático, transforma exponentes (2^n, M^e, R^-),
    subíndices (x_i, y_i) y respeta ecuaciones OMML directas.
    """
    formula = formula.strip()
    if "<m:oMathPara" in formula:
        return formula
    if "<m:oMath>" in formula or "<m:oMath " in formula:
        return f'<m:oMathPara xmlns:m="http://schemas.openxmlformats.org/officeDocument/2006/math">{formula}</m:oMathPara>'
    if any(tag in formula for tag in ("<m:f>", "<m:rad>", "<m:nary>", "<m:m>", "<m:sSup>", "<m:sSub>")):
        return f'<m:oMathPara xmlns:m="http://schemas.openxmlformats.org/officeDocument/2006/math"><m:oMath>{formula}</m:oMath></m:oMathPara>'

    formula = normalizar_latex_a_unicode(formula)

    partes: List[str] = []
    patron = re.compile(r"([A-Za-z0-9\)\}\]]+)(?:\^([A-Za-z0-9+\-]+|\{[^}]+\})|_([A-Za-z0-9+\-]+|\{[^}]+\}))+")
    pos = 0
    for m in patron.finditer(formula):
        ini, fin = m.span()
        if ini > pos:
            partes.append(f"<m:r><m:t>{escape(formula[pos:ini])}</m:t></m:r>")
        full = m.group(0)
        m_sup = re.search(r"\^([A-Za-z0-9+\-]+|\{([^}]+)\})", full)
        m_sub = re.search(r"_([A-Za-z0-9+\-]+|\{([^}]+)\})", full)
        base = re.split(r"[\^_]", full)[0]
        sup_val = (m_sup.group(2) or m_sup.group(1)) if m_sup else None
        sub_val = (m_sub.group(2) or m_sub.group(1)) if m_sub else None
        if sup_val and sub_val:
            partes.append(
                f"<m:sSubSup><m:e><m:r><m:t>{escape(base)}</m:t></m:r></m:e>"
                f"<m:sub><m:r><m:t>{escape(sub_val)}</m:t></m:r></m:sub>"
                f"<m:sup><m:r><m:t>{escape(sup_val)}</m:t></m:r></m:sup></m:sSubSup>"
            )
        elif sup_val:
            partes.append(
                f"<m:sSup><m:e><m:r><m:t>{escape(base)}</m:t></m:r></m:e>"
                f"<m:sup><m:r><m:t>{escape(sup_val)}</m:t></m:r></m:sup></m:sSup>"
            )
        elif sub_val:
            partes.append(
                f"<m:sSub><m:e><m:r><m:t>{escape(base)}</m:t></m:r></m:e>"
                f"<m:sub><m:r><m:t>{escape(sub_val)}</m:t></m:r></m:sub></m:sSub>"
            )
        pos = fin
    if pos < len(formula):
        partes.append(f"<m:r><m:t>{escape(formula[pos:])}</m:t></m:r>")
    cuerpo = "".join(partes)
    return f'<m:oMathPara xmlns:m="http://schemas.openxmlformats.org/officeDocument/2006/math"><m:oMath>{cuerpo}</m:oMath></m:oMathPara>'


def dividir_formula_larga(formula: str, max_long: int = 75) -> List[str]:
    """Divide una fórmula lógica o matemática larga para evitar desbordamiento horizontal."""
    formula = formula.strip()
    if "<m:" not in formula:
        formula = normalizar_latex_a_unicode(formula)
    if len(formula) <= max_long:
        return [formula]
    if "\n" in formula:
        return [parte.strip() for parte in formula.split("\n") if parte.strip()]

    operadores = [" ⇒ ", " ⟹ ", " → ", " ⇔ ", " ⟺ ", " ≡ ", " ⊑ ", " ∧ ", " ∨ "]
    mitad = len(formula) // 2
    mejor_pos = -1
    mejor_dist = 999
    for op in operadores:
        idx = 0
        while True:
            pos = formula.find(op, idx)
            if pos == -1:
                break
            dist = abs(pos - mitad)
            if dist < mejor_dist:
                mejor_dist = dist
                mejor_pos = pos
            idx = pos + len(op)

    if mejor_pos != -1 and mejor_dist < len(formula) * 0.45:
        linea1 = formula[:mejor_pos].strip()
        linea2 = formula[mejor_pos:].strip()
        return [linea1, linea2]
    return [formula]


def formula_bloque(
    doc_o_formula: Any,
    formula_o_etiqueta: Optional[Any] = None,
    etiqueta: Optional[str] = None,
    *,
    antes: int = 6,
    despues: int = 6,
    fuente_etiqueta: Optional[str] = None,
):
    """Inserta una ecuación matemática centrada en OMML directo sobre el lienzo.

    Protege contra desbordamientos horizontales dividiendo ecuaciones extensas en líneas
    armónicas con espaciado protegido.
    """
    if hasattr(doc_o_formula, "add_paragraph") or hasattr(doc_o_formula, "paragraphs"):
        doc = doc_o_formula
        formula_raw = formula_o_etiqueta
        etiqueta_final = etiqueta
    else:
        frame = inspect.currentframe()
        caller_frame = frame.f_back if frame else None
        doc = (caller_frame.f_locals.get("doc") or caller_frame.f_globals.get("doc")) if caller_frame else None
        formula_raw = doc_o_formula
        etiqueta_final = str(formula_o_etiqueta) if formula_o_etiqueta else None

    if doc is None:
        raise ValueError("formula_bloque requiere una instancia de Document")

    f_etiqueta = fuente_etiqueta
    if not f_etiqueta:
        meta = getattr(doc, "_rubric_driven", None)
        tema = meta.get("tema") if isinstance(meta, dict) else None
        f_etiqueta = str(tema.fuente) if tema is not None and getattr(tema, "fuente", None) else "Arial"

    lineas: List[str] = []
    if isinstance(formula_raw, (list, tuple)):
        for item in formula_raw:
            lineas.extend(dividir_formula_larga(str(item)))
    else:
        lineas = dividir_formula_larga(str(formula_raw or ""))

    ultimo_p = None
    total = len(lineas)
    for i, linea in enumerate(lineas):
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        pf = p.paragraph_format
        pf.space_before = Pt(antes if i == 0 else 2)
        pf.space_after = Pt(2 if (i < total - 1 or etiqueta_final) else despues)
        pf.line_spacing = 1.0

        omml_xml = texto_a_omml(linea)
        p._p.append(parse_xml(omml_xml))
        ultimo_p = p

    if etiqueta_final:
        p2 = doc.add_paragraph()
        p2.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p2.paragraph_format.space_before = Pt(0)
        p2.paragraph_format.space_after = Pt(despues)
        r_et = p2.add_run(etiqueta_final)
        r_et.font.name = f_etiqueta
        rpr = r_et._element.get_or_add_rPr()
        from docx.oxml import OxmlElement
        from docx.oxml.ns import qn

        for viejo in rpr.findall(qn("w:rFonts")):
            rpr.remove(viejo)
        fuentes = OxmlElement("w:rFonts")
        for attr in ("w:ascii", "w:hAnsi", "w:eastAsia", "w:cs"):
            fuentes.set(qn(attr), f_etiqueta)
        rpr.insert(0, fuentes)
        r_et.font.size = Pt(8.5)
        r_et.font.color.rgb = GRIS_ETIQUETA
        r_et.italic = True

    return ultimo_p
