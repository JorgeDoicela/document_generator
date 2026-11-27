# -*- coding: utf-8 -*-
"""Pruebas unitarias para el módulo de componentes visuales (plantillas/visual.py)."""
import tempfile
import unittest
from pathlib import Path

from docx import Document
from PIL import Image

from plantillas import visual


class TestComponentesVisuales(unittest.TestCase):
    def test_sanitizar_salida_terminal_mojibake_y_ansi(self):
        entrada_bytes = (
            b"Leyendo archivo y comprobando sintaxis...\n"
            b"\x1b[?25h*** Ejecuci\xf3n Iniciada. ***\n"
            b"SISTEMA DE AUTENTICACI\xc3\x83 N\n"
            b"contrase\xc3\x83\xc2\xb1a\n"
            b">> \xc3\x83 XITO: Autenticaci\xc3\x83\xc2\xb3n\n"
            b"[?25h\n"
        )
        lineas = visual.sanitizar_salida_terminal(entrada_bytes)
        texto_unido = "\n".join(lineas)

        self.assertNotIn("Leyendo archivo y comprobando sintaxis", texto_unido)
        self.assertNotIn("[?25h", texto_unido)
        self.assertNotIn("Ã", texto_unido)
        self.assertIn("Ejecución Iniciada", texto_unido)
        self.assertIn("AUTENTICACIÓN", texto_unido)
        self.assertIn("contraseña", texto_unido)
        self.assertIn("ÉXITO: Autenticación", texto_unido)

    def test_renderizar_terminal_dark_y_light(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            salida_dark = Path(tmpdir) / "consola_dark.png"
            salida_light = Path(tmpdir) / "consola_light.png"

            lineas = [
                "*** Ejecución Iniciada. ***",
                "Ingrese usuario:",
                "> admin",
                ">> ÉXITO: Acceso concedido.",
                "*** Ejecución Finalizada. ***",
            ]

            visual.renderizar_terminal(
                titulo_ventana="Prueba Dark",
                comando_mostrado="./test.sh",
                salida_lineas=lineas,
                ruta_salida=salida_dark,
                tema="dark",
            )
            self.assertTrue(salida_dark.exists())
            with Image.open(salida_dark) as im_d:
                self.assertEqual(im_d.format, "PNG")
                self.assertGreater(im_d.width, 500)

            visual.renderizar_terminal(
                titulo_ventana="Prueba Light",
                comando_mostrado="./test.sh",
                salida_lineas=lineas,
                ruta_salida=salida_light,
                tema="light",
            )
            self.assertTrue(salida_light.exists())
            with Image.open(salida_light) as im_l:
                self.assertEqual(im_l.format, "PNG")
                self.assertGreater(im_l.width, 500)

    def test_bloque_codigo_word(self):
        doc = Document()
        codigo = 'Algoritmo Test\n    Escribir "Hola mundo"\nFinAlgoritmo'
        tabla = visual.bloque_codigo_word(
            doc,
            codigo=codigo,
            archivo="test.psc",
            lenguaje="PSeInt",
            tema="light",
        )
        self.assertEqual(len(tabla.rows), 2)
        self.assertIn("test.psc", tabla.rows[0].cells[0].text)
        self.assertIn("Algoritmo Test", tabla.rows[1].cells[0].text)

    def test_tabla_estilizada_opciones_autorizadas(self):
        encabezados = ["Columna 1", "Columna 2"]
        filas = [
            ["Dato 1", "Dato **importante**"],
            ["Dato 2", "Valor regular"],
        ]

        # Validar las dos opciones autorizadas: Opción 1 (APA) y Opción 4 (GRID)
        for estilo in (visual.EstilosTabla.APA, visual.EstilosTabla.GRID):
            doc = Document()
            t = visual.tabla_estilizada(
                doc,
                encabezados=encabezados,
                filas=filas,
                estilo=estilo,
                anchos=[2.5, 3.5],
                numero_tabla=1,
                titulo_tabla="Tabla de prueba de estilo",
                nota_pie="Fuente propia.",
            )
            self.assertEqual(len(t.rows), 3)
            self.assertEqual(len(t.columns), 2)
            # Verificar repetición de cabecera en fila 0
            self.assertTrue(t.rows[0]._tr.xpath("./w:trPr/w:tblHeader"))
            # Verificar prevención de partición de filas
            self.assertTrue(t.rows[1]._tr.xpath("./w:trPr/w:cantSplit"))
            # Verificar texto en celda y procesamiento de markdown
            self.assertIn("Columna 1", t.rows[0].cells[0].text)
            self.assertIn("Dato importante", t.rows[1].cells[1].text)
            self.assertNotIn("**", t.rows[1].cells[1].text)

    def test_resolver_estilo_tabla_y_variable_entorno(self):
        self.assertEqual(visual.resolver_estilo_tabla("apa"), visual.EstilosTabla.APA)
        self.assertEqual(visual.resolver_estilo_tabla("grid"), visual.EstilosTabla.GRID)
        self.assertEqual(visual.resolver_estilo_tabla("1"), visual.EstilosTabla.APA)
        self.assertEqual(visual.resolver_estilo_tabla("4"), visual.EstilosTabla.GRID)
        self.assertEqual(visual.resolver_estilo_tabla("institucional"), visual.EstilosTabla.GRID)


if __name__ == "__main__":
    unittest.main()
