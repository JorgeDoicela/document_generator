# -*- coding: utf-8 -*-
"""Pruebas unitarias para normalización LaTeX->OMML, pies de figura, tablas fijas y auditoría estática."""
import sys
import tempfile
import unittest
from pathlib import Path

from docx import Document

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "plantillas"))

import comprobar  # noqa: E402
from bloques import (  # noqa: E402
    caja_captura_evidencia,
    enunciado_formal,
)
from omml import (  # noqa: E402
    dividir_formula_larga,
    formula_bloque,
    normalizar_latex_a_unicode,
    texto_a_omml,
)
from visual import _calcular_anchos_proporcionales, tabla_estilizada  # noqa: E402


class TestOmmlYCalidadDocumental(unittest.TestCase):
    def test_normalizar_latex_a_unicode_elimina_comandos_crudos(self):
        latex = r"\forall c \, \forall p \; \Big( \text{Cliente}(c) \land \text{Producto}(p) \implies \exists o \big( \text{Pedido}(o) \big) \Big)"
        res = normalizar_latex_a_unicode(latex)
        self.assertNotIn("\\", res)
        self.assertIn("∀", res)
        self.assertIn("∃", res)
        self.assertIn("∧", res)
        self.assertIn("⇒", res)
        self.assertIn("Cliente(c)", res)

    def test_texto_a_omml_genera_xml_valido_sin_latex(self):
        latex = r"\text{Tripleta RDF} = \langle s, p, o \rangle \in (\mathcal{U} \cup \mathcal{B}) \times \mathcal{U}"
        xml = texto_a_omml(latex)
        self.assertIn("<m:oMathPara", xml)
        self.assertIn("⟨", xml)
        self.assertIn("∈", xml)
        self.assertIn("∪", xml)
        self.assertIn("×", xml)
        self.assertNotIn("\\text", xml)
        self.assertNotIn("\\mathcal", xml)

    def test_texto_a_omml_soporta_superindice_negativo(self):
        xml = texto_a_omml("Cliente ⊓ ∃compra.Producto ⊑ ∃asociadoA^-.Pedido")
        self.assertIn("<m:sSup>", xml)
        self.assertIn("<m:t>-</m:t>", xml)

    def test_dividir_formula_larga_normaliza_antes_de_dividir(self):
        latex = (
            r"\forall x \, \forall y \; (\text{Paciente}(x) \land \text{Enfermedad}(y) \land \text{padece}(x, y) "
            r"\implies \exists z (\text{Tratamiento}(z) \land \text{recibe}(x, z) \land \text{indicadoPara}(z, y)))"
        )
        lineas = dividir_formula_larga(latex, max_long=75)
        self.assertEqual(len(lineas), 2)
        self.assertTrue(lineas[1].startswith("⇒"))
        for lin in lineas:
            self.assertNotIn("\\", lin)

    def test_enunciado_formal_evita_dos_puntos_duplicados(self):
        doc = Document()
        p = enunciado_formal(doc, "Texto de prueba.", etiqueta="Consigna Docente:", numero=1)
        self.assertTrue(p.text.startswith("Consigna Docente 1: "))
        self.assertNotIn("Docente: 1:", p.text)

    def test_caja_captura_evidencia_evita_prefijo_y_punto_duplicados(self):
        from PIL import Image

        with tempfile.TemporaryDirectory() as tmp:
            img_path = Path(tmp) / "muestra.png"
            Image.new("RGB", (40, 40), (255, 255, 255)).save(img_path)

            doc = Document()
            caja_captura_evidencia(doc, img_path, "Figura 1. Diagrama de prueba.")
            cap_text = doc.paragraphs[-1].text
            self.assertEqual(cap_text, "Figura 1. Diagrama de prueba.")
            self.assertFalse(cap_text.startswith("Figura: Figura"))
            self.assertFalse(cap_text.endswith(".."))

            caja_captura_evidencia(doc, img_path, "Diagrama sin prefijo")
            cap_text2 = doc.paragraphs[-1].text
            self.assertEqual(cap_text2, "Figura: Diagrama sin prefijo.")

    def test_anchos_proporcionales_tabla_fija(self):
        encabezados = ["Sujeto (URI)", "Predicado", "Objeto (URI)", "Descripción"]
        filas = [["shop:prod_servidor_nvidia_a100", "rdf:type", "shop:Producto", "Servidor GPU de IA."]]
        anchos = _calcular_anchos_proporcionales(encabezados, filas, ancho_total=6.5)
        self.assertEqual(len(anchos), 4)
        self.assertAlmostEqual(sum(anchos), 6.5, places=1)
        self.assertGreater(anchos[0], anchos[1])

        doc = Document()
        t = tabla_estilizada(doc, encabezados, filas)
        xml_str = t._tbl.xml
        self.assertIn('w:tblLayout w:type="fixed"', xml_str)

    def test_comprobar_detecta_fuga_latex_en_parrafo(self):
        with tempfile.TemporaryDirectory() as tmp:
            docx_path = Path(tmp) / "fuga.docx"
            doc = Document()
            doc.add_paragraph("Portada")
            doc.add_page_break()
            doc.add_paragraph(r"Fórmula rota: \forall x \in \mathcal{U} \implies \text{Error}")
            doc.save(docx_path)

            analisis = comprobar.analizar(docx_path)
            self.assertTrue(any("LaTeX crudos" in msg for msg in analisis.anomalias_formato))

    def test_comprobar_aprueba_formula_bloque_normalizada(self):
        with tempfile.TemporaryDirectory() as tmp:
            docx_path = Path(tmp) / "limpia.docx"
            doc = Document()
            doc.add_paragraph("Portada")
            doc.add_page_break()
            formula_bloque(doc, r"\forall x (\text{A}(x) \implies \exists y \text{B}(x, y))", "Ecuación 1")
            doc.save(docx_path)

            analisis = comprobar.analizar(docx_path)
            self.assertEqual(analisis.anomalias_formato, [])


if __name__ == "__main__":
    unittest.main()
