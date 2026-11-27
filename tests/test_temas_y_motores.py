# -*- coding: utf-8 -*-
"""Pruebas unitarias para temas configurables, motores multi-propósito, bloques y ejemplo reproducible."""
import importlib.util
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from plantillas import (
    bloques,
    comprobar,
    config,
    extractor_tema,
    motor_base,
    omml,
    plataforma,
    temas,
)
from plantillas import formato_institucional as inst

RAIZ = Path(__file__).resolve().parent.parent


class TestTemasDocumentales(unittest.TestCase):
    def test_presets_integrados_disponibles(self):
        disponibles = temas.listar_temas()
        for esperado in ("apa7", "academico", "tecnico", "ejecutivo", "ieee"):
            self.assertIn(esperado, disponibles)
            t = temas.cargar_tema(esperado)
            self.assertEqual(t.nombre, esperado)

    def test_exportar_y_cargar_tema_json_personalizado(self):
        with tempfile.TemporaryDirectory() as tmp:
            destino = Path(tmp) / "mi_uni"
            archivo = temas.exportar_molde_tema(destino, nombre="mi_uni", base="tecnico")
            self.assertTrue(archivo.is_file())
            cargado = temas.cargar_tema(archivo)
            self.assertEqual(cargado.nombre, "mi_uni")
            self.assertEqual(cargado.fuente, "Calibri")
            self.assertEqual(cargado.color_primario, (15, 76, 129))

    def test_tema_inexistente_lanza_error(self):
        with self.assertRaises(ValueError):
            temas.cargar_tema("tema_que_no_existe_xyz")


class TestMotoresMultiProposito(unittest.TestCase):
    def test_motores_registrados_cumplen_protocolo(self):
        for clave in ("apa7", "academico", "institucional", "tecnico", "ejecutivo", "ieee"):
            cls = motor_base.obtener_motor(clave)
            self.assertIsNotNone(cls, f"Motor {clave} no registrado")
            instancia = cls()
            self.assertIsInstance(instancia, motor_base.BaseDocumentEngine)

    def test_documento_tematico_con_resumen_toc_y_codigo_inline(self):
        doc = inst.nuevo_documento_tematico(
            titulo="Especificación de Arquitectura",
            subtitulo="RFC-001",
            tema="tecnico",
            integrantes=["Ana Perez"],
            incluir_indice=True,
        )
        bloques.resumen_ejecutivo(
            doc,
            "Resumen de prueba con `codigo_inline` y **negrita**.",
            palabras_clave=["Arquitectura", "OpenXML"],
        )
        inst.titulo_seccion(doc, "1. Introducción", nivel=1, criterios="C1")
        inst.parrafo(doc, "Uso de `pip install -e .` en entorno local.")
        omml.formula_bloque(doc, r"\forall x \in A : x \geq 0", "Ecuación 1.")
        inst.marcar_transversal(doc, "C2")

        xml = doc.element.xml
        self.assertIn("TOC", xml)
        self.assertIn("rubrica_C1", xml)
        self.assertIn("rubrica_C2_todo", xml)
        self.assertIn("oMathPara", xml)
        self.assertNotIn("`", "\n".join(p.text for p in doc.paragraphs))

    def test_portada_renderiza_banner_inferior_desde_json(self):
        from PIL import Image

        with tempfile.TemporaryDirectory() as tmp:
            tdir = Path(tmp) / "tema_con_banner"
            tdir.mkdir()
            img_path = tdir / "banner.png"
            Image.new("RGB", (200, 40), (30, 58, 138)).save(img_path)
            (tdir / "theme.json").write_text(
                '{"nombre": "demo_banner", "banner_inferior": "banner.png"}',
                encoding="utf-8",
            )
            doc = inst.nuevo_documento_tematico(
                titulo="Informe con Banner",
                tema=tdir / "theme.json",
                integrantes=["Ana Perez"],
            )
            self.assertIn("graphicData", doc.element.xml)

    def test_apa_nuevo_documento_respeta_estilos_de_tema_tecnico(self):
        from docx.shared import RGBColor

        from plantillas import apa_docx

        with tempfile.TemporaryDirectory() as tmp:
            env_tmp = Path(tmp) / ".env"
            env_tmp.write_text(
                'NOMBRE_ESTUDIANTE="Ana Perez"\nINSTITUCION="Universidad Ejemplo"\n'
                'CARRERA="Software"\nSUFIJO_ARCHIVOS="Perez_Ana"\n',
                encoding="utf-8",
            )
            with mock.patch.object(config, "ARCHIVO_ENV", env_tmp), mock.patch.object(apa_docx, "_config", None):
                doc, _fig, _tab = apa_docx.nuevo_documento(
                    titulo="Spec Tecnica",
                    materia="Arquitectura",
                    salida=Path(tmp) / "out.docx",
                    formato="tecnico",
                    indice=True,
                )
                p = apa_docx.parrafo(doc, "Texto con `codigo_inline` en tema técnico.")
            self.assertEqual(doc.styles["Normal"].font.name, "Calibri")
            self.assertEqual(doc.styles["Heading 1"].font.color.rgb, RGBColor(15, 76, 129))
            self.assertEqual(p.runs[0].font.name, "Calibri")
            self.assertEqual(p.paragraph_format.line_spacing, 1.15)
            self.assertIn("TOC", doc.element.xml)
            self.assertNotIn("`", p.text)

    def test_apa_nuevo_documento_respeta_tema_defecto_de_env_y_all_exports(self):
        from plantillas import apa_docx

        for simbolo in (
            "enunciado_formal",
            "formula_bloque",
            "codigo_bloque",
            "caja_captura_evidencia",
            "resumen_ejecutivo",
            "insertar_indice_automatico",
            "nuevo_documento_tematico",
        ):
            self.assertIn(simbolo, apa_docx.__all__)
            self.assertTrue(hasattr(apa_docx, simbolo))

        with tempfile.TemporaryDirectory() as tmp:
            env_tmp = Path(tmp) / ".env"
            env_tmp.write_text(
                'NOMBRE_ESTUDIANTE="Ana Perez"\nINSTITUCION="Universidad Ejemplo"\n'
                'CARRERA="Software"\nSUFIJO_ARCHIVOS="Perez_Ana"\n'
                'TEMA_DEFECTO="ejecutivo"\n',
                encoding="utf-8",
            )
            with mock.patch.object(config, "ARCHIVO_ENV", env_tmp), mock.patch.object(apa_docx, "_config", None):
                doc, _fig, _tab = apa_docx.nuevo_documento(
                    titulo="Reporte Ejecutivo",
                    materia="Estrategia",
                    salida=Path(tmp) / "exec.docx",
                )
            self.assertEqual(doc.styles["Normal"].font.name, "Arial")
            self.assertEqual(doc.styles["Normal"].paragraph_format.line_spacing, 1.2)


class TestOptInDescargasYFuentes(unittest.TestCase):
    def test_copiar_pdf_descargas_es_opt_in_por_defecto(self):
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop("COPIAR_PDF_DESCARGAS", None)
            with mock.patch.object(config, "ARCHIVO_ENV", Path("/no/existe/.env")):
                self.assertFalse(config.copiar_pdf_descargas_activo())

    def test_copiar_pdf_descargas_activable_por_entorno(self):
        with mock.patch.dict(os.environ, {"COPIAR_PDF_DESCARGAS": "true"}):
            self.assertTrue(config.copiar_pdf_descargas_activo())

    def test_resolver_fuente_sans_no_lanza_error(self):
        ruta = plataforma.resolver_fuente_sans(bold=False)
        self.assertTrue(ruta is None or ruta.is_file())


class TestEjemploReproducible(unittest.TestCase):
    def test_ejemplo_completo_genera_y_pasa_auditoria_sin_errores(self):
        script = RAIZ / "examples" / "ejemplo_completo" / "generar_documento.py"
        self.assertTrue(script.is_file())
        spec = importlib.util.spec_from_file_location("ejemplo_completo_mod", script)
        self.assertIsNotNone(spec)
        assert spec is not None and spec.loader is not None
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)

        with tempfile.TemporaryDirectory() as tmp:
            salida = Path(tmp) / "demo.docx"
            mod.construir_documento(salida=salida)
            self.assertTrue(salida.is_file())

            inf = comprobar.comprobar(script.parent, docx=salida)
            self.assertTrue(inf.ok, f"Errores inesperados en ejemplo: {inf.errores}")
            self.assertTrue(all(c.cubierto for c in inf.coberturas))
            self.assertEqual(len(inf.coberturas), 4)


class TestExtractorTema(unittest.TestCase):
    def test_extraer_tema_completo_y_roundtrip(self):
        from docx import Document
        from docx.shared import Inches, Pt, RGBColor
        from PIL import Image

        with tempfile.TemporaryDirectory() as tmp:
            tmp_p = Path(tmp)
            img_hdr = tmp_p / "hdr.png"
            img_logo = tmp_p / "logo.png"
            img_ban = tmp_p / "ban.png"
            Image.new("RGB", (120, 30), (180, 30, 30)).save(img_hdr)
            Image.new("RGB", (80, 80), (20, 60, 120)).save(img_logo)
            Image.new("RGB", (320, 50), (180, 30, 30)).save(img_ban)

            src_docx = tmp_p / "plantilla_universidad.docx"
            doc = Document()
            sec = doc.sections[0]
            sec.top_margin = Inches(0.75)
            sec.left_margin = Inches(1.1)
            sec.header.paragraphs[0].add_run().add_picture(str(img_hdr), width=Inches(1.0))

            p_logo = doc.add_paragraph()
            p_logo.add_run().add_picture(str(img_logo), width=Inches(1.0))
            p_tit = doc.add_paragraph(style="Heading 1")
            r_tit = p_tit.add_run("Plantilla Oficial")
            r_tit.font.name = "Georgia"
            r_tit.font.size = Pt(16)
            r_tit.font.color.rgb = RGBColor(180, 30, 30)
            p_ban = doc.add_paragraph()
            p_ban.add_run().add_picture(str(img_ban), width=Inches(4.0))
            doc.add_page_break()

            p_body = doc.add_paragraph()
            r_body = p_body.add_run("Texto de cuerpo de ejemplo para inferencia tipográfica automática.")
            r_body.font.name = "Georgia"
            r_body.font.size = Pt(10.5)

            bloques.tabla_academica(doc, ["Col1", "Col2"], [["A", "B"]], estilo="grid")
            doc.save(str(src_docx))

            destino = tmp_p / "tema_extraido"
            res = extractor_tema.extraer_tema_desde_docx(
                src_docx, nombre="uni-demo", destino=destino
            )
            self.assertTrue(res.ruta_json.is_file())
            self.assertEqual(res.tema.nombre, "uni-demo")
            self.assertEqual(res.tema.fuente, "Georgia")
            self.assertEqual(res.tema.tamano_cuerpo, 10.5)
            self.assertEqual(res.tema.margen_sup, 0.75)
            self.assertEqual(res.tema.margen_izq, 1.1)
            self.assertEqual(res.tema.color_primario, (180, 30, 30))
            self.assertEqual(res.tema.estilo_tabla, "grid")
            self.assertIsNotNone(res.tema.imagen_encabezado)
            self.assertIsNotNone(res.tema.logo_portada)
            self.assertIsNotNone(res.tema.banner_inferior)
            self.assertEqual(len(res.imagenes_extraidas), 3)

            # Roundtrip: generar un documento nuevo usando el theme.json extraído
            doc_nuevo = inst.nuevo_documento_tematico(
                titulo="Documento Replicado",
                tema=res.ruta_json,
                integrantes=["Ana Perez"],
            )
            self.assertIn("graphicData", doc_nuevo.element.xml)

    def test_extraer_tema_inexistente_lanza_error(self):
        with self.assertRaises(FileNotFoundError):
            extractor_tema.extraer_tema_desde_docx("/no/existe/plantilla.docx")

    def test_extraer_tema_logo_en_tabla_y_pie_pagina(self):
        from docx import Document
        from docx.shared import Inches
        from PIL import Image

        with tempfile.TemporaryDirectory() as tmp:
            tmp_p = Path(tmp)
            img_logo = tmp_p / "logo_tbl.png"
            Image.new("RGB", (90, 90), (20, 60, 120)).save(img_logo)

            src_docx = tmp_p / "plantilla_tabla.docx"
            doc = Document()
            doc.sections[0].footer.paragraphs[0].add_run("Documento Confidencial")
            tbl = doc.add_table(rows=1, cols=1)
            tbl.rows[0].cells[0].paragraphs[0].add_run().add_picture(str(img_logo), width=Inches(1.0))
            doc.add_page_break()
            p = doc.add_paragraph("Cuerpo principal")
            p.paragraph_format.line_spacing = 1.5
            doc.save(str(src_docx))

            res = extractor_tema.extraer_tema_desde_docx(
                src_docx, nombre="corp-tbl", destino=tmp_p / "out_tema"
            )
            self.assertEqual(res.tema.logo_portada, "logo_portada.png")
            self.assertEqual(res.tema.pie_texto, "Documento Confidencial")
            self.assertEqual(res.tema.interlineado, 1.5)


class TestRegresionesTipograficasYTemas(unittest.TestCase):
    def test_negrita_al_inicio_no_se_trata_como_vinieta_y_multiplicacion_intacta(self):
        from docx import Document
        from docx.enum.text import WD_ALIGN_PARAGRAPH

        doc = Document()
        p_neg = bloques.parrafo_estructurado(doc, "**Conclusión:** El resultado es 2 * 3 + 4 * 5 = 26.")
        self.assertEqual(p_neg.alignment, WD_ALIGN_PARAGRAPH.JUSTIFY)
        self.assertIsNone(p_neg.paragraph_format.first_line_indent)
        self.assertIn("2 * 3 + 4 * 5 = 26.", p_neg.text)
        self.assertTrue(p_neg.runs[0].bold)

        p_vin = bloques.parrafo_estructurado(doc, "* Elemento de lista real")
        self.assertEqual(p_vin.alignment, WD_ALIGN_PARAGRAPH.LEFT)
        self.assertIsNotNone(p_vin.paragraph_format.first_line_indent)

    def test_bloques_y_omml_heredan_fuente_del_tema_y_toc_se_rellena(self):
        with tempfile.TemporaryDirectory() as tmp:
            doc = inst.nuevo_documento_tematico(
                titulo="Informe Técnico",
                tema="tecnico",
                integrantes=["Ana Perez"],
                incluir_indice=True,
            )
            p_enun = bloques.enunciado_formal(doc, "Demostrar la propiedad.")
            omml.formula_bloque(doc, r"\forall x \in A", "Ecuación 1.")
            inst.titulo_seccion(doc, "1. Arquitectura Base", nivel=1, criterios="C1")
            inst.parrafo(doc, "Contenido técnico.")

            salida = Path(tmp) / "out_toc.docx"
            inst.guardar_documento(doc, salida)

            self.assertEqual(p_enun.runs[0].font.name, "Calibri")
            self.assertEqual(doc.paragraphs[-3].runs[0].font.name, "Calibri")
            self.assertIn("1. Arquitectura Base", doc.element.xml)
            self.assertNotIn("Actualiza el índice", doc.element.xml)

    def test_portada_prioriza_logo_portada_sobre_imagen_encabezado(self):
        from PIL import Image

        with tempfile.TemporaryDirectory() as tmp:
            tdir = Path(tmp) / "tema_dos_imgs"
            tdir.mkdir()
            # Crear dos imágenes con distinto tamaño/contenido para distinguirlas en el docx
            Image.new("RGB", (80, 80), (10, 20, 30)).save(tdir / "logo_grande.png")
            Image.new("RGB", (120, 25), (200, 10, 10)).save(tdir / "hdr_chico.png")
            (tdir / "theme.json").write_text(
                '{"nombre": "dos_imgs", "logo_portada": "logo_grande.png", "imagen_encabezado": "hdr_chico.png"}',
                encoding="utf-8",
            )
            doc = inst.nuevo_documento_tematico(
                titulo="Test Logo",
                tema=tdir / "theme.json",
                integrantes=["Ana Perez"],
            )
            # La imagen incrustada en el cuerpo (portada) debe ser logo_grande.png
            blobs_body = [
                rel.target_part.blob
                for rel in doc.part.rels.values()
                if "image" in str(rel.reltype)
            ]
            self.assertIn((tdir / "logo_grande.png").read_bytes(), blobs_body)

    def test_fuentes_comunes_carga_todas_en_bibliografia(self):
        from plantillas import apa_docx, fuentes_comunes

        bib = apa_docx.Bibliografia()
        claves = list(fuentes_comunes.FUENTES_CARRERA.keys())
        cargadas = fuentes_comunes.cargar_en_bibliografia(bib, *claves)
        self.assertEqual(cargadas, claves)
        self.assertEqual(bib.cita("russell_norvig"), "(Russell y Norvig, 2021)")
        self.assertEqual(bib.cita("copi_cohen"), "(Copi et al., 2018)")
        for clave in claves:
            entrada = bib.entrada(clave)
            self.assertTrue(len(entrada) > 15, f"Entrada vacía para {clave}")

        with self.assertRaises(KeyError):
            fuentes_comunes.cargar_en_bibliografia(bib, "clave_inexistente_xyz")

    def test_nuevo_documento_tematico_sincroniza_estilos_base_y_docente(self):
        from docx.shared import RGBColor

        doc = inst.nuevo_documento_tematico(
            titulo="Informe de Investigación",
            subtitulo="Metodología",
            tema="tecnico",
            docente="Dra. Laura Gómez",
            integrantes=["Ana Perez"],
        )
        self.assertEqual(doc.styles["Normal"].font.name, "Calibri")
        self.assertEqual(doc.styles["Heading 1"].font.name, "Calibri")
        self.assertEqual(doc.styles["Heading 1"].font.color.rgb, RGBColor(15, 76, 129))
        texto_portada = "\n".join(p.text for p in doc.paragraphs)
        self.assertIn("Docente: Dra. Laura Gómez", texto_portada)

        p = bloques.parrafo_estructurado(doc, "Párrafo heredado.")
        self.assertEqual(p.runs[0].font.name, "Calibri")
        tbl = bloques.tabla_academica(doc, ["A", "B"], [["1", "2"]])
        self.assertEqual(tbl.rows[0].cells[0].paragraphs[0].runs[0].font.name, "Calibri")

    def test_apa_nuevo_documento_hereda_formato_de_materia_md(self):
        from plantillas import apa_docx

        with tempfile.TemporaryDirectory() as tmp:
            tmp_p = Path(tmp)
            env_tmp = tmp_p / ".env"
            env_tmp.write_text(
                'NOMBRE_ESTUDIANTE="Ana Perez"\nINSTITUCION="Universidad Ejemplo"\n'
                'CARRERA="Software"\nSUFIJO_ARCHIVOS="Perez_Ana"\n',
                encoding="utf-8",
            )
            mat_dir = tmp_p / "materias" / "arq"
            tar_dir = mat_dir / "A1_Prueba"
            tar_dir.mkdir(parents=True)
            (mat_dir / "MATERIA.md").write_text(
                "# Arquitectura\n\n| Campo | Valor |\n|---|---|\n"
                "| Docente | Dr. Carlos Ruiz |\n"
                "| Formato que pide el docente | tecnico |\n",
                encoding="utf-8",
            )
            (tar_dir / "TAREA.md").write_text(
                "# A1 — Prueba\n\n- **Estado:** pendiente\n\n## Formato\n<!-- vacio -->\n",
                encoding="utf-8",
            )
            with mock.patch.object(config, "ARCHIVO_ENV", env_tmp), mock.patch.object(apa_docx, "_config", None):
                doc, _fig, _tab = apa_docx.nuevo_documento(
                    titulo="Diseño Base",
                    materia="Arquitectura",
                    salida=tar_dir / "out.docx",
                    tarea=tar_dir,
                )
            self.assertEqual(doc.styles["Normal"].font.name, "Calibri")
            self.assertIn("Docente: Dr. Carlos Ruiz", "\n".join(p.text for p in doc.paragraphs))

    def test_comprobar_inspecciona_tablas_sin_falso_positivo_en_codigo(self):
        from plantillas import visual

        with tempfile.TemporaryDirectory() as tmp:
            doc = inst.nuevo_documento_tematico(
                titulo="Auditoría Tablas",
                tema="tecnico",
                integrantes=["Ana Perez"],
            )
            inst.titulo_seccion(doc, "1. Resultados", nivel=1, criterios="C1")
            inst.tabla(
                doc,
                encabezados=["Concepto", "Detalle"],
                filas=[["Criterio", "Validado según (Russell y Norvig, 2021)"]],
            )
            visual.bloque_codigo_word(
                doc,
                "def fn(**kwargs):\n    return 2 ** 3\n",
                archivo="demo.py",
                lenguaje="Python",
            )
            ruta = Path(tmp) / "tablas.docx"
            inst.guardar_documento(doc, ruta)

            analisis = comprobar.analizar(ruta)
            self.assertTrue(any(ap == "Russell" and an == "2021" for ap, an, _ in analisis.citas))
            self.assertFalse(
                any("Markdown" in w for w in analisis.avisos_tipograficos),
                f"Falso positivo de Markdown en bloque de código: {analisis.avisos_tipograficos}",
            )

    def test_comprobar_detecta_citas_autores_institucionales_multipalabra(self):
        citas = list(
            comprobar._citas(
                "Conforme a (International Organization for Standardization, 2023) y "
                "(Parlamento Europeo y Consejo de la Unión Europea, 2016) y (Russell y Norvig, 2021)."
            )
        )
        self.assertEqual(len(citas), 3)
        self.assertTrue(
            comprobar._coincide(
                citas[0][0],
                citas[0][1],
                "International Organization for Standardization. (2023). Systems and software engineering.",
            )
        )
        self.assertTrue(
            comprobar._coincide(
                citas[1][0],
                citas[1][1],
                "Parlamento Europeo y Consejo de la Unión Europea. (2016). Reglamento (UE) 2016/679.",
            )
        )
        self.assertTrue(
            comprobar._coincide(
                citas[2][0],
                citas[2][1],
                "Russell, S., y Norvig, P. (2021). Artificial Intelligence.",
            )
        )

    def test_ficha_lee_formato_inline_cuando_no_hay_seccion(self):
        from plantillas import ficha

        t = ficha.leer_tarea(RAIZ / "examples" / "ejemplo_completo")
        self.assertEqual(t.formato, "tecnico")

    def test_formato_institucional_limpia_markdown_y_emite_campo_page_completo(self):
        doc = inst.nuevo_documento_tematico(
            titulo="Prueba Limpieza",
            tema="tecnico",
            integrantes=["Ana Perez"],
        )
        p = inst.titulo_seccion(doc, "1. **Sección** con *énfasis*", nivel=1, criterios="C1")
        self.assertEqual(p.text, "1. Sección con énfasis")
        footer_xml = doc.sections[0].footer._element.xml
        self.assertIn('fldCharType="begin"', footer_xml)
        self.assertIn('fldCharType="separate"', footer_xml)
        self.assertIn('fldCharType="end"', footer_xml)
        self.assertIn('dirty="true"', footer_xml)
        # Re-exportaciones autosuficientes en formato_institucional
        self.assertTrue(callable(inst.Bibliografia))
        self.assertTrue(callable(inst.referencias))
        self.assertTrue(callable(inst.vinieta))
        self.assertTrue(callable(inst.salto_de_pagina))

    def test_resumen_ejecutivo_hereda_tema_y_celda_tabla_soporta_codigo_inline(self):
        from plantillas import visual

        doc = inst.nuevo_documento_tematico(
            titulo="Coherencia Temática",
            tema="ieee",
            integrantes=["Ana Perez"],
        )
        p_res = bloques.resumen_ejecutivo(doc, "Síntesis experimental.", palabras_clave=["IEEE"])
        self.assertAlmostEqual(p_res.paragraph_format.line_spacing, 1.08, places=2)

        t = inst.tabla(
            doc,
            encabezados=["Expresión", "Comando"],
            filas=[["2 * 3 * 4 = 24", "Ejecutar `tareas verificar` con x^2"]],
        )
        celda_expr = t.rows[1].cells[0].paragraphs[0]
        self.assertEqual(celda_expr.text, "2 * 3 * 4 = 24")
        self.assertFalse(any(r.italic for r in celda_expr.runs))

        celda_cmd = t.rows[1].cells[1].paragraphs[0]
        self.assertNotIn("`", celda_cmd.text)
        self.assertTrue(any(r.font.name == "Courier New" for r in celda_cmd.runs))
        self.assertTrue(any(r.font.superscript for r in celda_cmd.runs))
        self.assertIsNotNone(visual.EstilosTabla.APA)

    def test_cli_tarea_acepta_formato_en_linea_de_comandos(self):
        from types import SimpleNamespace

        from plantillas import ficha, tareas

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            env_tmp = tmp_path / ".env"
            env_tmp.write_text(
                'NOMBRE_ESTUDIANTE="Ana Perez"\n'
                'INSTITUCION="Universidad Ejemplo"\n'
                'CARRERA="Software"\n'
                'SUFIJO_ARCHIVOS="Perez_Ana"\n',
                encoding="utf-8",
            )
            materias_tmp = tmp_path / "materias"
            (materias_tmp / "redes").mkdir(parents=True)
            (materias_tmp / "redes" / "MATERIA.md").write_text("# Redes\n", encoding="utf-8")

            args = SimpleNamespace(
                materia="redes",
                codigo="P1",
                titulo="Arquitectura Zero Trust",
                enunciado=None,
                tipo=None,
                modalidad="individual",
                grupal=False,
                grupo=None,
                integrantes=None,
                estudiante=None,
                formato="tecnico",
            )
            with mock.patch.object(config, "ARCHIVO_ENV", env_tmp), mock.patch.object(
                tareas, "MATERIAS", materias_tmp
            ):
                tareas.cmd_tarea(args)

            t = ficha.leer_tarea(materias_tmp / "redes" / "P1_Arquitectura_Zero_Trust")
            self.assertEqual(t.formato, "tecnico")

    def test_rfonts_en_portada_tablas_toc_y_etiqueta_omml(self):
        from docx.oxml.ns import qn

        from plantillas import omml

        doc = inst.nuevo_documento_tematico(
            titulo="Verificación Tipográfica",
            subtitulo="Auditoría OpenXML",
            tema="tecnico",
            integrantes=["Ana Perez"],
            incluir_indice=True,
        )
        t = inst.tabla(doc, encabezados=["Clave", "Valor"], filas=[["A", "**B** con `codigo`"]])
        omml.formula_bloque(doc, r"x + y = z", "Ecuación 1.")

        # Portada y TOC deben fijar rFonts en los 4 alfabetos
        runs_titulo = [r for p in doc.paragraphs if p.text == "Verificación Tipográfica" for r in p.runs]
        self.assertTrue(runs_titulo)
        rfonts_tit = runs_titulo[0]._element.find(f".//{qn('w:rFonts')}")
        self.assertIsNotNone(rfonts_tit)
        self.assertEqual(rfonts_tit.get(qn("w:ascii")), "Calibri")

        # Título del TOC debe heredar el color primario del tema técnico (#0F4C81)
        runs_toc = [r for p in doc.paragraphs if p.text == "Tabla de Contenidos" for r in p.runs]
        self.assertTrue(runs_toc)
        self.assertEqual(str(runs_toc[0].font.color.rgb), "0F4C81")

        # Celda de tabla con markdown unificado debe fijar rFonts
        r_celda = t.rows[1].cells[1].paragraphs[0].runs[0]
        rfonts_celda = r_celda._element.find(f".//{qn('w:rFonts')}")
        self.assertIsNotNone(rfonts_celda)
        self.assertEqual(rfonts_celda.get(qn("w:ascii")), "Calibri")

    def test_ejemplo_completo_pasa_comprobar_sin_errores_ni_avisos(self):
        import importlib.util

        from plantillas import comprobar

        ejemplo_dir = config.RAIZ / "examples" / "ejemplo_completo"
        spec = importlib.util.spec_from_file_location(
            "ejemplo_completo_mod", ejemplo_dir / "generar_documento.py"
        )
        assert spec is not None and spec.loader is not None
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)

        with tempfile.TemporaryDirectory() as tmp:
            salida = Path(tmp) / "DEMO1_Ejemplo_Informe_Rubric_Driven.docx"
            mod.construir_documento(salida)
            inf = comprobar.comprobar(ejemplo_dir, docx=salida)
            self.assertTrue(inf.ok, f"Errores inesperados: {inf.errores}")
            avisos_relevantes = [
                a for a in inf.avisos if "más reciente que el .docx" not in a
            ]
            self.assertEqual(avisos_relevantes, [], f"Avisos inesperados: {avisos_relevantes}")


if __name__ == "__main__":
    unittest.main()
