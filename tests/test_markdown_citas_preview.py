# -*- coding: utf-8 -*-
"""Pruebas unitarias para citación multi-estilo (APA 7, IEEE, Vancouver),
compilador declarativo Markdown/YAML y vista previa de temas."""
import sys
import tempfile
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "plantillas"))

import apa_docx  # noqa: E402
import comprobar as comp  # noqa: E402
import markdown_docx  # noqa: E402
import preview_tema  # noqa: E402


class TestEstilosCitacion(unittest.TestCase):
    """Valida Bibliografia en estilos APA 7, IEEE numérico y Vancouver."""

    def _poblar(self, estilo: str) -> apa_docx.Bibliografia:
        bib = apa_docx.Bibliografia(estilo=estilo)
        bib.agregar(
            "zeta2024",
            ["Zeta, M.", "Álvarez, C."],
            2024,
            "Arquitectura de compiladores",
            "Editorial Técnica",
        )
        bib.agregar(
            "alfa2023",
            ["Alfa, K."],
            2023,
            "Análisis estático de XML",
            "Journal of Software",
            detalles="15(2), 10-24",
            tipo="articulo",
        )
        return bib

    def test_estilo_invalido_lanza_error(self) -> None:
        with self.assertRaises(ValueError):
            apa_docx.Bibliografia(estilo="chicago")

    def test_ieee_numeracion_por_orden_de_aparicion(self) -> None:
        bib = self._poblar("ieee")
        self.assertTrue(bib.es_numerico)
        self.assertEqual(bib.cita("zeta2024"), "[1]")
        self.assertEqual(bib.cita("alfa2023", "p. 12"), "[2, p. 12]")
        self.assertEqual(bib.cita("zeta2024", "alfa2023"), "[1], [2]")
        self.assertEqual(bib.cita_narrativa("zeta2024"), "Zeta y Álvarez [1]")
        self.assertEqual(bib.ordenadas(), ["zeta2024", "alfa2023"])
        self.assertTrue(bib.entrada("zeta2024").startswith("[1] M. Zeta y C. Álvarez,"))
        self.assertTrue(bib.entrada("alfa2023").startswith('[2] K. Alfa, "Análisis estático de XML,"'))

    def test_vancouver_numeracion_y_formato(self) -> None:
        bib = self._poblar("vancouver")
        self.assertTrue(bib.es_numerico)
        self.assertEqual(bib.cita("zeta2024"), "(1)")
        self.assertEqual(bib.cita("zeta2024", "alfa2023"), "(1,2)")
        self.assertEqual(bib.cita_narrativa("alfa2023"), "Alfa (2)")
        self.assertEqual(bib.ordenadas(), ["zeta2024", "alfa2023"])
        self.assertTrue(bib.entrada("zeta2024").startswith("1. Zeta M, Álvarez C."))
        self.assertTrue(bib.entrada("alfa2023").startswith("2. Alfa K."))

    def test_comprobar_audita_citas_ieee_y_detecta_huerfanas(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            carpeta = Path(tmp)
            (carpeta / "TAREA.md").write_text(
                "# T1\n\n## Rúbrica\n\n| ID | Criterio | Puntaje | Dónde se cumple |\n"
                "|---|---|---|---|\n"
                "| C1 | Desarrollo | 5 pts | — |\n"
                "| C2 | Referencias | 5 pts | — |\n",
                encoding="utf-8",
            )
            doc, _, _ = apa_docx.nuevo_documento(
                titulo="Prueba IEEE",
                materia="Pruebas",
                salida=carpeta / "salida.docx",
                institucion="Org",
                carrera="Ing",
                nombre="Tester",
                formato="ieee",
            )
            bib = self._poblar("ieee")
            apa_docx.titulo(doc, "1. Desarrollo", 1, criterios="C1")
            apa_docx.parrafo(doc, f"Texto con cita válida {bib.cita('zeta2024')} y cita huérfana [9].")
            apa_docx.referencias(doc, bib, criterios="C2")
            apa_docx.guardar_documento(doc, carpeta / "salida.docx")

            inf = comp.comprobar(carpeta, docx=carpeta / "salida.docx")
            self.assertTrue(any("Cita numérica sin referencia: [9]." in e for e in inf.errores))

    def test_comprobar_audita_citas_vancouver_biyectivas(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            carpeta = Path(tmp)
            (carpeta / "TAREA.md").write_text(
                "# T1\n\n## Rúbrica\n\n| ID | Criterio | Puntaje | Dónde se cumple |\n"
                "|---|---|---|---|\n"
                "| C1 | Desarrollo | 5 pts | — |\n"
                "| C2 | Referencias | 5 pts | — |\n",
                encoding="utf-8",
            )
            doc, _, _ = apa_docx.nuevo_documento(
                titulo="Prueba Vancouver",
                materia="Pruebas",
                salida=carpeta / "salida.docx",
                institucion="Org",
                carrera="Ing",
                nombre="Tester",
                formato="academico",
            )
            bib = self._poblar("vancouver")
            apa_docx.titulo(doc, "1. Desarrollo", 1, criterios="C1")
            apa_docx.parrafo(doc, f"Evidencia {bib.cita('zeta2024')} y contraste {bib.cita('alfa2023')}.")
            apa_docx.referencias(doc, bib, criterios="C2")
            apa_docx.guardar_documento(doc, carpeta / "salida.docx")

            inf = comp.comprobar(carpeta, docx=carpeta / "salida.docx")
            self.assertTrue(inf.ok, f"Errores inesperados: {inf.errores}")

    def test_comprobar_no_confunde_indexacion_o_funciones_con_citas(self) -> None:
        self.assertEqual(list(comp._citas_numericas("valor = arr[0] + matriz[1] + fn(2)", comp._CITA_IEEE)), [])
        self.assertEqual(list(comp._citas_numericas("valor = arr[0] + fn(2)", comp._CITA_VANCOUVER)), [])
        self.assertEqual(list(comp._citas_numericas("Según evidencia [1] y [2-3].", comp._CITA_IEEE)), [1, 2, 3])
        self.assertEqual(list(comp._citas_numericas("Según evidencia (1,2).", comp._CITA_VANCOUVER)), [1, 2])


class TestCompiladorMarkdown(unittest.TestCase):
    """Valida el parser YAML ligero y la compilación declarativa Markdown -> DOCX."""

    def test_extraer_frontmatter_sin_pyyaml(self) -> None:
        md = (
            "---\n"
            'titulo: "Documento de Prueba"\n'
            "tema: tecnico\n"
            "indice: true\n"
            "palabras_clave: [Python, OpenXML]\n"
            "referencias:\n"
            "  - clave: ref1\n"
            '    autores: ["Pérez, J."]\n'
            "    anio: 2025\n"
            '    titulo: "Guía Técnica"\n'
            '    fuente: "Editorial"\n'
            "---\n\n"
            "# 1. Sección {#C1}\n\nTexto.\n"
        )
        meta, cuerpo = markdown_docx.extraer_frontmatter(md)
        self.assertEqual(meta["titulo"], "Documento de Prueba")
        self.assertEqual(meta["tema"], "tecnico")
        self.assertTrue(meta["indice"])
        self.assertEqual(meta["palabras_clave"], ["Python", "OpenXML"])
        self.assertEqual(len(meta["referencias"]), 1)
        self.assertEqual(meta["referencias"][0]["clave"], "ref1")
        self.assertIn("# 1. Sección {#C1}", cuerpo)

    def test_compilar_ejemplo_declarativo_y_auditar_cero_errores(self) -> None:
        ejemplo_dir = RAIZ / "examples" / "ejemplo_markdown"
        with tempfile.TemporaryDirectory() as tmp:
            salida = Path(tmp) / "compilado.docx"
            ruta = markdown_docx.compilar_markdown(
                ejemplo_dir / "documento.md",
                salida=salida,
                tarea=ejemplo_dir,
            )
            self.assertTrue(ruta.is_file())
            inf = comp.comprobar(ejemplo_dir, docx=ruta)
            self.assertTrue(inf.ok, f"Errores en auditoría declarativa: {inf.errores}")
            assert inf.analisis is not None
            self.assertEqual(len(inf.analisis.referencias), 2)
            self.assertTrue(inf.analisis.referencias[0].startswith("[1]"))
            self.assertEqual(len(inf.analisis.anomalias_formato), 0)
            self.assertEqual(len(inf.analisis.avisos_tipograficos), 0)

    def test_compilar_con_override_de_tema_y_citas_vancouver(self) -> None:
        ejemplo_dir = RAIZ / "examples" / "ejemplo_markdown"
        with tempfile.TemporaryDirectory() as tmp:
            salida = Path(tmp) / "vancouver.docx"
            ruta = markdown_docx.compilar_markdown(
                ejemplo_dir / "documento.md",
                salida=salida,
                tema="ejecutivo",
                estilo_citas="vancouver",
                tarea=ejemplo_dir,
            )
            inf = comp.comprobar(ejemplo_dir, docx=ruta)
            self.assertTrue(inf.ok, f"Errores en modo Vancouver: {inf.errores}")
            assert inf.analisis is not None
            self.assertTrue(inf.analisis.referencias[0].startswith("1. "))


class TestPreviewTema(unittest.TestCase):
    """Valida la generación de muestras visuales de temas."""

    def test_generar_preview_presets_sin_anomalias(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            for preset in ("apa7", "tecnico", "ieee"):
                salida = Path(tmp) / f"preview_{preset}.docx"
                ruta = preview_tema.generar_preview_tema(preset, salida=salida)
                self.assertTrue(ruta.is_file())
                analisis = comp.analizar(ruta)
                self.assertEqual(analisis.anomalias_formato, [])
                self.assertEqual(analisis.avisos_tipograficos, [])
                self.assertGreaterEqual(len(analisis.referencias), 2)

    def test_generar_previews_todos(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            rutas = preview_tema.generar_previews("todos", salida=Path(tmp))
            self.assertGreaterEqual(len(rutas), 5)
            for r in rutas:
                self.assertTrue(r.is_file())


if __name__ == "__main__":
    unittest.main()
