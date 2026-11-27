# -*- coding: utf-8 -*-
"""Pruebas unitarias para citación multi-estilo (APA 7, IEEE, Vancouver),
compilador declarativo Markdown/YAML y vista previa de temas."""
import re
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from docx import Document

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "plantillas"))

import apa_docx  # noqa: E402
import comprobar as comp  # noqa: E402
import markdown_docx  # noqa: E402
import preview_tema  # noqa: E402
import temas as temas_mod  # noqa: E402


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

    def test_apa7_no_duplica_punto_final_con_detalles_terminados_en_punto(self) -> None:
        bib = apa_docx.Bibliografia(estilo="apa7")
        bib.agregar(
            "russell2021",
            ["Russell, S.", "Norvig, P."],
            2021,
            "Artificial Intelligence: A Modern Approach.",
            "Pearson",
            detalles="4.a ed.",
        )
        entrada = bib.entrada("russell2021")
        self.assertNotIn("..", entrada)
        self.assertTrue(entrada.endswith("Pearson, 4.a ed."))

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
                formato="apa7",
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
                formato="apa7",
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
                tema="apa7",
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
            salida = Path(tmp) / "preview_apa7.docx"
            ruta = preview_tema.generar_preview_tema("apa7", salida=salida)
            self.assertTrue(ruta.is_file())
            analisis = comp.analizar(ruta)
            self.assertEqual(analisis.anomalias_formato, [])
            self.assertEqual(analisis.avisos_tipograficos, [])
            self.assertGreaterEqual(len(analisis.referencias), 2)

    def test_generar_previews_todos_solo_temas_personalizados(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            tdir = tmp_path / "local" / "mi_tema"
            tdir.mkdir(parents=True)
            (tdir / "theme.json").write_text('{"nombre": "mi_tema", "fuente": "Arial"}', encoding="utf-8")

            with mock.patch.object(temas_mod, "DIR_TEMAS", tmp_path), mock.patch.object(
                temas_mod, "DIR_TEMAS_LOCALES", tmp_path / "local"
            ):
                rutas = preview_tema.generar_previews("todos", salida=tmp_path / "out")

            nombres = [r.name for r in rutas]
            self.assertEqual(nombres, ["preview_mi_tema.docx"])
            self.assertTrue(rutas[0].is_file())

    def test_catalogo_estilos_lista_todas_las_categorias(self) -> None:
        cat = preview_tema.obtener_catalogo_estilos()
        elementos = {g["elemento"]: dict(g["opciones"]) for g in cat}
        self.assertIn("Tablas", elementos)
        self.assertIn("apa", elementos["Tablas"])
        self.assertIn("grid", elementos["Tablas"])
        self.assertIn("Citas y Referencias", elementos)
        self.assertEqual(set(elementos["Citas y Referencias"].keys()), {"apa7", "ieee", "vancouver"})
        self.assertIn("Tema Documental", elementos)
        self.assertIn("apa7", elementos["Tema Documental"])
        self.assertIn("Bloques Editoriales, OMML y Tarjetas", elementos)
        self.assertIn("formula_bloque", elementos["Bloques Editoriales, OMML y Tarjetas"])

    def test_generar_catalogo_estilos_sin_anomalias(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            salida = Path(tmp) / "catalogo.docx"
            ruta = preview_tema.generar_catalogo_estilos(tema="apa7", salida=salida)
            self.assertTrue(ruta.is_file())
            analisis = comp.analizar(ruta)
            self.assertEqual(analisis.anomalias_formato, [])
            self.assertEqual(analisis.avisos_tipograficos, [])
            self.assertGreaterEqual(len(analisis.secciones), 6)
            self.assertTrue(any(s.tablas >= 1 for s in analisis.secciones))
            doc = Document(str(ruta))
            parrafos_txt = "\n".join(p.text for p in doc.paragraphs)
            self.assertNotIn("`", parrafos_txt)
            for tabla in doc.tables:
                for fila in tabla.rows:
                    for celda in fila.cells:
                        self.assertIsNone(re.search(r"(?<!\.)\.\.(?!\.)", celda.text))
            xml = doc.element.xml
            self.assertIn("cantSplit", xml)
            self.assertIn("keepNext", xml)
            self.assertIn("oMathPara", xml)
            self.assertEqual(sum(1 for _ in doc.inline_shapes), 3)

    def test_carpetas_workspace_y_temas_conservan_gitkeep(self) -> None:
        for rel in (
            "materias/.gitkeep",
            "themes/.gitkeep",
            "themes/local/.gitkeep",
            "themes/.previews/.gitkeep",
        ):
            self.assertTrue((RAIZ / rel).is_file(), f"Falta {rel}")


if __name__ == "__main__":
    unittest.main()
