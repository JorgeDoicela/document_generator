# -*- coding: utf-8 -*-
"""Ejemplo autocontenido y reproducible del framework documental rubric-driven.

Demuestra:
- Portada y tipografía mediante preset oficial `apa7` (y compatibilidad con temas JSON).
- Resumen ejecutivo con palabras clave e índice automático TOC.
- Marcadores XML de rúbrica (`criterios="C1"` y `marcar_transversal`).
- Ecuaciones vectoriales OMML con normalización automática de LaTeX.
- Tablas con layout fijo (w:tblLayout="fixed") y bloques de código estilizados.
- Gestión bibliográfica y citas APA 7 verificadas por `comprobar.py`.
"""
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from plantillas import apa_docx, bloques, omml  # noqa: E402
from plantillas import formato_institucional as inst  # noqa: E402
from plantillas.visual import EstilosTabla, Temas, bloque_codigo_word  # noqa: E402


def construir_documento(salida: Path | None = None) -> Path:
    destino = salida or (AQUI / "DEMO1_Ejemplo_Informe_Rubric_Driven.docx")

    bib = apa_docx.Bibliografia()
    bib.agregar(
        "russell_norvig",
        ["Russell, S.", "Norvig, P."],
        2021,
        "Artificial Intelligence: A Modern Approach (4.a ed.)",
        "Pearson",
    )
    bib.agregar(
        "iso_25010",
        ["International Organization for Standardization"],
        2023,
        "Systems and software engineering — SQuaRE (ISO/IEC 25010:2023)",
        url="https://www.iso.org/standard/78176.html",
    )

    doc = inst.nuevo_documento_tematico(
        titulo="Arquitectura Documental Guiada por Rúbricas",
        subtitulo="Ejemplo Reproducible — Estándar APA 7",
        tema="apa7",
        institucion="Universidad Ejemplo",
        organizacion="Facultad de Ingeniería",
        integrantes=["Ana Perez"],
        incluir_indice=True,
    )

    bloques.resumen_ejecutivo(
        doc,
        "Este informe demostrativo valida de extremo a extremo la generación programática de "
        "documentos OpenXML con trazabilidad automática de criterios de evaluación, ecuaciones "
        "matemáticas OMML y verificación bibliográfica APA 7.",
        palabras_clave=["Rubric-Driven", "OpenXML", "OMML", "APA 7", "Automatización"],
    )

    inst.titulo_seccion(doc, "1. Fundamentación Técnica y Formulación OMML", nivel=1, criterios="C1")
    bloques.enunciado_formal(
        doc,
        "Formular el criterio de cobertura documental y demostrar su representación vectorial sin fugas LaTeX.",
        numero=1,
        etiqueta="Consigna",
    )
    inst.parrafo(
        doc,
        f"La ingeniería documental reproducible exige separar el contenido semántico de la maquetación visual. "
        f"En sistemas complejos, la verificación formal reduce los defectos estructurales antes de la entrega "
        f"{bib.cita('iso_25010')}. Asimismo, la representación explícita de restricciones permite auditar de manera "
        f"determinista la completitud de cada requisito {bib.cita('russell_norvig')}.\n"
        f"- **Separación de capas:** motor tipográfico independiente del tema institucional.\n"
        f"- **Trazabilidad XML:** cada sección enlaza con su criterio mediante `w:bookmarkStart`.",
    )
    omml.formula_bloque(
        doc,
        r"\forall c \in \mathcal{R} : \text{Cubierto}(c) \implies \text{Cobertura}(\mathcal{D}) = 100\%",
        "Ecuación 1. Condición de cobertura total de rúbrica normalizada automáticamente a OMML.",
    )

    inst.titulo_seccion(doc, "2. Comparativa Tabular y Código Reproducible", nivel=1, criterios="C2")
    inst.parrafo(
        doc,
        "El motor documental desacopla el contenido semántico de la identidad visual mediante el preset "
        "oficial APA 7 y archivos `theme.json` externos. De este modo, un mismo script puede compilarse "
        "bajo norma APA 7 o bajo cualquier tema institucional personalizado en `themes/local/` sin "
        "duplicar lógica ni modificar la estructura de criterios. Asimismo, todas las tablas se construyen "
        "con `w:tblLayout=\"fixed\"`, anchos proporcionales calculados automáticamente y repetición de "
        "cabeceras en saltos de página para garantizar fidelidad tipográfica al exportar a PDF.\n"
        "- **Portabilidad OpenXML:** los bloques de código y tablas fijan sus fuentes en los cuatro "
        "alfabetos WordML para prevenir sustituciones inesperadas entre Microsoft Word y LibreOffice.\n"
        "- **Personalización sin código:** las identidades institucionales se extraen automáticamente "
        "desde cualquier plantilla `.docx` hacia `themes/local/` mediante el subcomando `temas --extraer`.",
    )
    inst.tabla(
        doc,
        encabezados=["Modo", "Tipografía", "Interlineado", "Aplicación Principal"],
        filas=[
            ["apa7 (oficial)", "Times New Roman 12 pt", "2.0", "Ensayos y trabajos universitarios APA 7"],
            ["theme.json", "Configurable", "Configurable", "Plantillas institucionales o corporativas"],
            ["--extraer DOCX", "Inferida del .docx", "Inferido", "Clonado automático de formatos docentes"],
        ],
        estilo=EstilosTabla.APA,
        numero_tabla=1,
        titulo_tabla="Modos de Maquetación Documental Soportados",
    )
    inst.parrafo(doc, "")
    bloque_codigo_word(
        doc,
        'from plantillas import formato_institucional as inst\n'
        'doc = inst.nuevo_documento_tematico("Informe APA 7", tema="apa7")\n'
        'inst.titulo_seccion(doc, "1. Alcance", nivel=1, criterios="C1")\n',
        archivo="ejemplo_uso.py",
        lenguaje="Python",
        tema=Temas.LIGHT,
    )

    inst.titulo_seccion(doc, "3. Conclusiones", nivel=1, criterios="C3")
    inst.parrafo(
        doc,
        "La desvinculación entre el motor documental, los temas configurables y el workspace privado "
        "permite mantener un repositorio público liviano, auditable y apto para cualquier institución "
        "o equipo de ingeniería sin comprometer la calidad tipográfica ni la verificación estática.",
    )
    inst.marcar_transversal(doc, "C4")
    apa_docx.referencias(doc, bib, criterios="C4")

    inst.guardar_documento(doc, destino)
    return destino


if __name__ == "__main__":
    ruta = construir_documento()
    print(f"Documento de ejemplo generado: {ruta}")
