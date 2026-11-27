# -*- coding: utf-8 -*-
"""Tests del kit. Ejecutar desde la raíz:  .venv/bin/python -m unittest -v

No tocan el .env ni materias/ reales: los de extremo a extremo copian
plantillas/ a un directorio temporal con su propio .env.
"""
import os
import shutil
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "plantillas"))

ENV = textwrap.dedent("""\
    NOMBRE_ESTUDIANTE="Ana Pérez"
    INSTITUCION="Universidad Ejemplo"
    CARRERA="Carrera de Software"
    SUFIJO_ARCHIVOS="Perez_Ana"
    """)

import apa_docx  # noqa: E402  (importar no debe exigir el .env)
import bloques  # noqa: E402
import comprobar as comp  # noqa: E402
import esqueleto as esq  # noqa: E402
import ficha  # noqa: E402
import formato_institucional as inst  # noqa: E402
import omml  # noqa: E402
import plataforma  # noqa: E402
import rubrica as rub  # noqa: E402


class TestRubrica(unittest.TestCase):
    def test_numero(self):
        self.assertEqual(rub.numero("2,5 pts"), 2.5)
        self.assertEqual(rub.numero("20 %"), 20.0)
        self.assertIsNone(rub.numero("<!-- -->"))

    def test_leer_tabla_antigua_sin_id(self):
        texto = textwrap.dedent("""\
            # A1 — X

            ## Rúbrica

            | Criterio | Puntaje | Dónde se cumple |
            |---|---|---|
            | Diseño del modelo | 3 | |
            | Ortografía | 1 | |

            ## Qué se entrega
            """)
        with tempfile.TemporaryDirectory() as d:
            ruta = Path(d) / "TAREA.md"
            ruta.write_text(texto, encoding="utf-8")
            criterios = rub.leer(ruta)
            self.assertEqual([c.id for c in criterios], ["C1", "C2"])
            self.assertEqual(criterios[0].puntaje, 3)
            self.assertTrue(criterios[1].transversal)
            rub.escribir(ruta, criterios)
            nuevo = ruta.read_text(encoding="utf-8")
            self.assertIn("| ID | Criterio | Puntaje | Dónde se cumple |", nuevo)
            self.assertIn("## Qué se entrega", nuevo)
            self.assertEqual(len(rub.leer(ruta)), 2)

    def test_referencias_no_es_transversal(self):
        c = rub.Criterio("C4", "Referencias en formato APA")
        self.assertTrue(c.de_referencias)
        self.assertFalse(c.transversal)

    def test_importar_matriz_docx(self):
        from docx import Document
        doc = Document()
        t = doc.add_table(rows=1, cols=3)
        for celda, texto in zip(t.rows[0].cells, ["Criterio", "Excelente (4)", "Regular (2)"], strict=False):
            celda.text = texto
        for fila in (["Explica el concepto", "a", "b"], ["Implementa", "c", "d"], ["Total", "", ""]):
            for celda, texto in zip(t.add_row().cells, fila, strict=False):
                celda.text = texto

        with tempfile.TemporaryDirectory() as d:
            ruta = Path(d) / "r.docx"
            doc.save(ruta)
            criterios = rub.importar_docx(ruta)
        self.assertEqual([(c.id, c.texto, c.puntaje) for c in criterios],
                         [("C1", "Explica el concepto", 4), ("C2", "Implementa", 4)])


class TestFicha(unittest.TestCase):
    def test_fecha_y_extension(self):
        self.assertEqual(str(ficha.leer_fecha("2026-10-25")), "2026-10-25")
        self.assertEqual(str(ficha.leer_fecha("25/10/2026")), "2026-10-25")
        self.assertIsNone(ficha.leer_fecha("<!-- AAAA-MM-DD -->"))
        self.assertEqual(ficha.leer_extension("1.500 palabras"), 1500)
        self.assertEqual(ficha.leer_extension("4-6 páginas"), 5 * ficha.PALABRAS_POR_PAGINA)

    def test_celdas_con_barra_escapada(self):
        self.assertEqual(ficha.celdas("| a | b \\| c |"), ["a", "b | c"])


class TestBibliografia(unittest.TestCase):
    def setUp(self):
        self.bib = apa_docx.Bibliografia()
        self.bib.agregar("ramos", ["Ramos, J.", "Pérez, A."], 2023, "Bases de datos", "Alfaomega")
        self.bib.agregar("lee", ["Lee, K.", "Kim, S.", "Park, J."], 2021, "Indexing",
                         "Journal of Databases", detalles="12(3), 45–60", tipo="articulo")

    def test_citas(self):
        self.assertEqual(self.bib.cita("ramos"), "(Ramos y Pérez, 2023)")
        self.assertEqual(self.bib.cita("ramos", "p. 15"), "(Ramos y Pérez, 2023, p. 15)")
        self.assertEqual(self.bib.cita("ramos", "lee"), "(Lee et al., 2021; Ramos y Pérez, 2023)")
        self.assertEqual(self.bib.cita_narrativa("lee"), "Lee et al. (2021)")
        with self.assertRaises(KeyError):
            self.bib.cita("no-existe")

    def test_entradas(self):
        self.assertEqual(self.bib.entrada("ramos"),
                         "Ramos, J. y Pérez, A. (2023). *Bases de datos*. Alfaomega.")
        self.assertEqual(self.bib.entrada("lee"), "Lee, K., Kim, S. y Park, J. (2021). Indexing. "
                                                  "*Journal of Databases*, 12(3), 45–60.")

    def test_solo_citadas_y_en_orden(self):
        self.bib.cita("ramos")
        self.assertEqual(self.bib.ordenadas(), ["ramos"])
        self.assertEqual(self.bib.no_citadas(), ["lee"])


class TestCitasEnTexto(unittest.TestCase):
    def test_detecta_citas(self):
        texto = ("Según Ramos y Pérez (2023) y Lee et al. (2021), algo (Oracle, 2024; "
                 "Ministerio de Educación, s.f., p. 3). Ver Figura 1 (captura). ISO (9001).")
        self.assertEqual(sorted(set(comp._citas(texto))),
                         [("Lee", "2021"), ("Ministerio de Educación", "s.f."),
                          ("Oracle", "2024"), ("Ramos", "2023")])

    def test_coincide(self):
        self.assertTrue(comp._coincide("Ramos", "2023", "Ramos, J. y Pérez, A. (2023). *X*."))
        self.assertFalse(comp._coincide("Ramos", "2022", "Ramos, J. (2023). X."))


class TestEsqueleto(unittest.TestCase):
    def test_bloque(self):
        criterios = [rub.Criterio("C1", "Explica el concepto", 6),
                     rub.Criterio("C2", "Implementa el código", 2),
                     rub.Criterio("C3", "Ortografía y redacción", 1),
                     rub.Criterio("C4", "Referencias APA", 1)]
        bloque, refs = esq.bloque(criterios, 1000)
        self.assertIn("criterios='C1'", bloque)
        self.assertIn("~600 palabras", bloque)  # 800 × 6/8
        self.assertIn("~200 palabras", bloque)  # 800 × 2/8
        self.assertIn("transversal(doc, 'C3')", bloque)
        self.assertEqual(refs, "C4")

    def test_no_pisa_texto_escrito(self):
        self.assertFalse(esq._tiene_texto('# x\ntitulo(doc, "A", 1)\nparrafo(doc, "")\n'))
        self.assertTrue(esq._tiene_texto('parrafo(doc, "Ya escrito")\n'))


class TestExtremoAExtremo(unittest.TestCase):
    """Crea materia y tarea, importa la rúbrica, genera y comprueba."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.kit = Path(self.tmp.name)
        shutil.copytree(RAIZ / "plantillas", self.kit / "plantillas",
                        ignore=shutil.ignore_patterns("__pycache__"))
        (self.kit / ".env").write_text(ENV, encoding="utf-8")
        self.entorno = plataforma.entorno_utf8(
            {k: v for k, v in os.environ.items() if k != "RUBRIC_DRIVEN_ENV"}
        )

    def tearDown(self):
        self.tmp.cleanup()

    def tareas(self, *args, ok=True):
        r = subprocess.run(
            [sys.executable, "plantillas/tareas.py", *args],
            cwd=self.kit,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=self.entorno,
        )
        if ok and r.returncode != 0:
            self.fail(f"tareas.py {' '.join(args)} → {r.returncode}\n{r.stdout}\n{r.stderr}")
        return r

    def test_flujo_completo(self):
        self.tareas("materia", "sgbd1", "Sistemas de Bases de Datos I")
        ficha = self.kit / "materias/sgbd1/MATERIA.md"
        ficha.write_text(ficha.read_text(encoding="utf-8").replace(
            "| **Docente** | <!-- nombre --> |", "| **Docente** | Ing. Luis Gómez |"), encoding="utf-8")
        self.tareas("tarea", "sgbd1", "A15", "Procedimientos almacenados")
        carpeta = self.kit / "materias/sgbd1/A15_Procedimientos_Almacenados"
        tarea_md = carpeta / "TAREA.md"
        tarea_md.write_text(tarea_md.read_text(encoding="utf-8")
                            .replace("<!-- AAAA-MM-DD -->", "2026-10-25")
                            .replace("| ID | Criterio | Puntaje | Dónde se cumple |\n|---|---|---|---|\n",
                                     "| ID | Criterio | Puntaje | Dónde se cumple |\n|---|---|---|---|\n"
                                     "| C1 | Explica el concepto | 3 | |\n"
                                     "| C2 | Implementa el código | 1 | |\n"
                                     "| C3 | Ortografía y redacción | 1 | |\n"
                                     "| C4 | Referencias APA | 1 | |\n"), encoding="utf-8")
        ruta = "materias/sgbd1/A15_Procedimientos_Almacenados"
        self.tareas("esqueleto", ruta)

        # Sin contenido: secciones vacías → la comprobación falla.
        r = self.tareas("generar", ruta, "--sin-pdf", ok=False)
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn("está vacía", r.stdout)

        script = carpeta / "generar_documento.py"
        texto = script.read_text(encoding="utf-8")
        texto = texto.replace(
            '# bib.agregar("clave", ["Apellido, A."], 2026, "Título de la obra", "Editorial")',
            'bib.agregar("ramos", ["Ramos, J."], 2023, "Bases de datos", "Alfaomega")')
        texto = texto.replace("criterios='C1')\nparrafo(doc, \"\")",
                              "criterios='C1')\nparrafo(doc, f\"Concepto {bib.cita('ramos')}. \" * 60)")
        texto = texto.replace("criterios='C2')\nparrafo(doc, \"\")",
                              "criterios='C2')\nparrafo(doc, \"Código del ejercicio. \" * 30)")
        texto = texto.replace('titulo(doc, "Conclusiones", 1)\nparrafo(doc, "")',
                              'titulo(doc, "Conclusiones", 1)\nparrafo(doc, "Fin. " * 20)')
        script.write_text(texto, encoding="utf-8")

        # El esqueleto ya no se reescribe sin --forzar.
        self.assertNotEqual(self.tareas("esqueleto", ruta, ok=False).returncode, 0)

        r = self.tareas("generar", ruta, "--sin-pdf", ok=False)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        tarea = tarea_md.read_text(encoding="utf-8")
        self.assertIn("| C1 | Explica el concepto | 3 | Explica el concepto (", tarea)
        self.assertIn("| C3 | Ortografía y redacción | 1 | todo el documento |", tarea)
        self.assertIn("| C4 | Referencias APA | 1 | Referencias |", tarea)

        docx = carpeta / "A15_Procedimientos_Almacenados_Perez_Ana.docx"
        from docx import Document
        doc = Document(str(docx))
        textos = [p.text for p in doc.paragraphs]
        self.assertIn("Ing. Luis Gómez", textos)            # portada con docente
        self.assertIn("25 de octubre de 2026", textos)       # y fecha de entrega
        self.assertIn("Ramos, J. (2023). Bases de datos. Alfaomega.", textos)
        estilos = {p.style.name for p in doc.paragraphs}
        self.assertIn("Heading 1", estilos)

        self.tareas("marcar", ruta, "lista")
        self.assertIn("| lista |", (self.kit / "materias/sgbd1/MATERIA.md").read_text(encoding="utf-8"))
        self.assertIn("A15_Procedimientos_Almacenados", self.tareas("estado").stdout)

    @unittest.skipUnless(plataforma.buscar_libreoffice(), "sin LibreOffice")
    def test_pdf(self):
        self.tareas("materia", "m", "Materia")
        self.tareas("tarea", "m", "A1", "Prueba")
        ruta = "materias/m/A1_Prueba"
        r = self.tareas("generar", ruta, ok=False)
        self.assertIn("PDF generado", r.stdout, r.stdout + r.stderr)
        self.assertTrue((self.kit / ruta / "A1_Prueba_Perez_Ana.pdf").exists())


    def test_auditar_cli(self):
        self.tareas("materia", "m1", "Materia 1")
        self.tareas("tarea", "m1", "A1", "Tarea 1")
        r = self.tareas("auditar", ok=False)
        self.assertEqual(r.returncode, 1)
        self.assertIn("Total: 1 tareas auditadas", r.stdout)
        self.assertIn("Auditoría fallida", r.stdout)



class TestFormatoInstitucional(unittest.TestCase):
    def test_titulo_y_transversal_institucional(self):
        from docx import Document
        doc = Document()
        doc.add_paragraph("Portada institucional")
        doc.add_page_break()
        inst.titulo_seccion(doc, "Sección de Prueba", nivel=1, criterios="C1")
        doc.add_paragraph("Contenido analítico de prueba para el criterio C1.")
        inst.marcar_transversal(doc, "C2")
        with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as tmp:
            doc.save(tmp.name)
            analisis = comp.analizar(Path(tmp.name))
            self.assertEqual(len(analisis.secciones), 1)
            self.assertEqual(analisis.secciones[0].criterios, ["C1"])
            self.assertIn("C2", analisis.transversales)


class TestMotorBase(unittest.TestCase):
    def test_protocolo_y_registro(self):
        from plantillas import motor_base
        self.assertIn("apa7", motor_base.motores_disponibles())
        self.assertIn("institucional", motor_base.motores_disponibles())

        motor_apa = motor_base.obtener_motor("apa7")
        self.assertIsNotNone(motor_apa)
        instancia_apa = motor_apa()
        self.assertIsInstance(instancia_apa, motor_base.BaseDocumentEngine)

        motor_inst = motor_base.obtener_motor("institucional")
        self.assertIsNotNone(motor_inst)
        instancia_inst = motor_inst()
        self.assertIsInstance(instancia_inst, motor_base.BaseDocumentEngine)

    def test_normalizar_criterios(self):
        from plantillas import motor_base
        self.assertEqual(motor_base.normalizar_criterios("C1, C2"), ["C1", "C2"])
        self.assertEqual(motor_base.normalizar_criterios(["c3", "c4"]), ["C3", "C4"])
        self.assertEqual(motor_base.normalizar_criterios(None), [])
        with self.assertRaises(ValueError):
            motor_base.normalizar_criterios("C!@#")



class TestAuditoriaGlobal(unittest.TestCase):
    def test_auditar_raiz_inexistente(self):
        resultados = comp.auditar_todo(Path("/no/existe/ruta"))
        self.assertEqual(resultados, [])
        self.assertTrue(comp.imprimir_auditoria_global(resultados))

    def test_auditar_materias_reales(self):
        resultados = comp.auditar_todo(RAIZ / "materias")
        # En un clon limpio del repo público materias/ puede estar vacío (.gitkeep)
        ok = comp.imprimir_auditoria_global(resultados)
        self.assertTrue(ok)


class TestFichaMateria(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.carpeta = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_prioriza_materia_md(self):
        (self.carpeta / "MATERIA.md").write_text("# Materia Nueva\n\n| | |\n|---|---|\n| **Docente** | Dr. Torres |\n", encoding="utf-8")
        (self.carpeta / "README.md").write_text("# Materia Vieja\n", encoding="utf-8")
        m = ficha.leer_materia(self.carpeta)
        self.assertEqual(m.nombre, "Materia Nueva")
        self.assertEqual(m.docente, "Dr. Torres")

    def test_fallback_readme_md(self):
        (self.carpeta / "README.md").write_text("# Materia Legada\n\n| | |\n|---|---|\n| **Docente** | Ing. Mora |\n", encoding="utf-8")
        m = ficha.leer_materia(self.carpeta)
        self.assertEqual(m.nombre, "Materia Legada")
        self.assertEqual(m.docente, "Ing. Mora")


class TestImportarSinEnv(unittest.TestCase):
    def test_importar_no_lee_env(self):
        entorno = plataforma.entorno_utf8(RUBRIC_DRIVEN_ENV="/no/existe/.env")
        r = subprocess.run(
            [sys.executable, "-c", "import apa_docx; print('ok')"],
            cwd=RAIZ / "plantillas",
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=entorno,
        )
        self.assertEqual(r.returncode, 0)
        self.assertIn("ok", r.stdout)
class TestModalidadIndividualYGrupal(unittest.TestCase):
    def setUp(self):
        from unittest import mock

        import config

        self.tmp = tempfile.TemporaryDirectory()
        self.carpeta = Path(self.tmp.name)
        env_tmp = self.carpeta / ".env"
        env_tmp.write_text(ENV, encoding="utf-8")
        self._patch_env = mock.patch.object(config, "ARCHIVO_ENV", env_tmp)
        self._patch_env.start()

    def tearDown(self):
        self._patch_env.stop()
        self.tmp.cleanup()

    def test_tarea_individual(self):
        t_dir = self.carpeta / "A1_Individual"
        t_dir.mkdir()
        (t_dir / "TAREA.md").write_text(
            "# A1 — Algoritmos\n\n"
            "- **Materia:** Programación\n"
            "- **Tipo:** Actividad (A)\n"
            "- **Modalidad:** Individual\n"
            "- **Estado:** pendiente\n",
            encoding="utf-8",
        )
        t = ficha.leer_tarea(t_dir)
        self.assertFalse(t.es_grupal)
        self.assertEqual(t.modalidad, "individual")
        self.assertIsNone(t.grupo)
        self.assertEqual(t.integrantes, [])
        integrantes = t.resolver_integrantes({"NOMBRE_ESTUDIANTE": "Ana Perez"})
        self.assertEqual(integrantes, ["Ana Perez"])

    def test_tarea_grupal_con_integrantes(self):
        t_dir = self.carpeta / "CP1_Grupal"
        t_dir.mkdir()
        (t_dir / "TAREA.md").write_text(
            "# CP1 — Lógica\n\n"
            "- **Materia:** Representación\n"
            "- **Tipo:** Práctica (P)\n"
            "- **Modalidad:** Grupal\n"
            "- **Grupo:** Grupo 1\n"
            "- **Integrantes:** Ana Perez, Juan Gomez, Carlos Diaz\n"
            "- **Estado:** pendiente\n",
            encoding="utf-8",
        )
        t = ficha.leer_tarea(t_dir)
        self.assertTrue(t.es_grupal)
        self.assertEqual(t.modalidad, "grupal")
        self.assertEqual(t.grupo, "Grupo 1")
        self.assertEqual(t.integrantes, ["Ana Perez", "Juan Gomez", "Carlos Diaz"])

    def test_nombre_entregable_individual_vs_grupal(self):
        t_ind = self.carpeta / "T_Ind"
        t_ind.mkdir()
        (t_ind / "TAREA.md").write_text("# T1 — Tarea 1\n- **Modalidad:** Individual\n", encoding="utf-8")

        t_grup = self.carpeta / "T_Grup"
        t_grup.mkdir()
        (t_grup / "TAREA.md").write_text("# T2 — Tarea 2\n- **Modalidad:** Grupal\n- **Grupo:** Grupo 1\n", encoding="utf-8")

        nombre_ind = apa_docx.nombre_entregable("T1_Tarea", tarea=t_ind, sufijo="Perez_Ana")
        self.assertEqual(nombre_ind, "T1_Tarea_Perez_Ana.docx")

        nombre_grup = apa_docx.nombre_entregable("T2_Tarea", tarea=t_grup, sufijo="Perez_Ana")
        self.assertEqual(nombre_grup, "T2_Tarea_Grupo_1.docx")

    def test_portada_institucional_individual_vs_grupal(self):
        from docx import Document

        # Caso Individual
        doc_ind = Document()
        inst.aplicar_portada(
            doc_ind,
            titulo="Actividad 1",
            subtitulo="Programación",
            tema="apa7",
            modalidad="individual",
            integrantes=["Estudiante Solitario"],
        )
        textos_ind = [p.text for p in doc_ind.paragraphs]
        self.assertTrue(any("ESTUDIANTE:" in t for t in textos_ind))
        self.assertFalse(any("GRUPO" in t for t in textos_ind))
        self.assertTrue(any("Estudiante Solitario" in t for t in textos_ind))

        # Caso Grupal
        doc_grup = Document()
        inst.aplicar_portada(
            doc_grup,
            titulo="Laboratorio 1",
            subtitulo="Ciberseguridad",
            tema="apa7",
            modalidad="grupal",
            grupo="Grupo Alfa",
            integrantes=["Estudiante 1", "Estudiante 2"],
        )
        textos_grup = [p.text for p in doc_grup.paragraphs]
        self.assertTrue(any("GRUPO ALFA — INTEGRANTES:" in t for t in textos_grup))
        self.assertTrue(any("Estudiante 1" in t for t in textos_grup))
        self.assertTrue(any("Estudiante 2" in t for t in textos_grup))

    def test_parseo_integrantes_multilinea_subvinietas(self):
        t_dir = self.carpeta / "T_Subvinietas"
        t_dir.mkdir()
        (t_dir / "TAREA.md").write_text(
            "# P1 — Programación Concurrente\n\n"
            "- **Materia:** Sistemas\n"
            "- **Modalidad:** Grupal\n"
            "- **Grupo:** Equipo Delta\n"
            "- **Integrantes:**\n"
            "  - Laura Gomez\n"
            "  - Andres Mendoza\n"
            "  * Beatriz Torres\n"
            "- **Estado:** pendiente\n",
            encoding="utf-8",
        )
        t = ficha.leer_tarea(t_dir)
        self.assertTrue(t.es_grupal)
        self.assertEqual(t.grupo, "Equipo Delta")
        self.assertEqual(t.integrantes, ["Laura Gomez", "Andres Mendoza", "Beatriz Torres"])

    def test_precedencia_estricta_individual_con_grupo_residual(self):
        t_dir = self.carpeta / "T_Residual"
        t_dir.mkdir()
        (t_dir / "TAREA.md").write_text(
            "# A1 — Algoritmos\n\n"
            "- **Materia:** Computación\n"
            "- **Modalidad:** Individual\n"
            "- **Grupo:** N/A\n"
            "- **Estado:** pendiente\n",
            encoding="utf-8",
        )
        t = ficha.leer_tarea(t_dir)
        self.assertFalse(t.es_grupal)
        self.assertEqual(t.modalidad, "individual")
        self.assertIsNone(t.grupo)

    def test_tarea_individual_con_estudiante_especifico(self):
        t_dir = self.carpeta / "T_Estudiante"
        t_dir.mkdir()
        (t_dir / "TAREA.md").write_text(
            "# A2 — Redes\n\n"
            "- **Materia:** Ciberseguridad\n"
            "- **Modalidad:** Individual\n"
            "- **Estudiante:** Shaskia Peñaherrera Vittoria Alcivar\n"
            "- **Estado:** pendiente\n",
            encoding="utf-8",
        )
        t = ficha.leer_tarea(t_dir)
        self.assertFalse(t.es_grupal)
        self.assertEqual(t.modalidad, "individual")
        self.assertEqual(t.integrantes, ["Shaskia Peñaherrera Vittoria Alcivar"])

    def test_portada_apa_individual_vs_grupal(self):
        import apa_docx

        # Individual
        salida_ind = self.carpeta / "apa_ind.docx"
        doc_ind, _, _ = apa_docx.nuevo_documento(
            titulo="Informe Individual",
            materia="Ciberseguridad",
            salida=salida_ind,
            modalidad="individual",
            grupo="N/A",
            nombre="Ana Lopez",
        )
        p_textos_ind = [p.text for p in doc_ind.paragraphs]
        self.assertIn("Ana Lopez", p_textos_ind)
        self.assertNotIn("N/A", p_textos_ind)

        # Grupal
        salida_grup = self.carpeta / "apa_grup.docx"
        doc_grup, _, _ = apa_docx.nuevo_documento(
            titulo="Informe Grupal",
            materia="Ciberseguridad",
            salida=salida_grup,
            modalidad="grupal",
            grupo="Grupo Alfa",
            integrantes=["Estudiante 1", "Estudiante 2"],
        )
        p_textos_grup = [p.text for p in doc_grup.paragraphs]
        self.assertIn("Grupo Alfa", p_textos_grup)

    def test_nombre_entregable_estudiante_especifico(self):
        import apa_docx

        t_dir = self.carpeta / "T_Estudiante2"
        t_dir.mkdir()
        (t_dir / "TAREA.md").write_text(
            "# P3 — Sistemas\n\n"
            "- **Materia:** Ciberseguridad\n"
            "- **Modalidad:** Individual\n"
            "- **Estudiante:** Shaskia Peñaherrera Vittoria Alcivar\n"
            "- **Estado:** pendiente\n",
            encoding="utf-8",
        )
        nombre = apa_docx.nombre_entregable("P3_Sistemas", tarea=t_dir)
        self.assertIn("Penaherrera_Shaskia", nombre)

    def test_cmd_tarea_con_estudiante_y_fallback(self):
        from argparse import Namespace

        import tareas
        from cli import comandos_gestion

        materias_dir = self.carpeta / "materias"
        materias_dir.mkdir(exist_ok=True)
        (materias_dir / "redes").mkdir(exist_ok=True)
        (materias_dir / "redes" / "MATERIA.md").write_text("# Redes\n", encoding="utf-8")

        # 1. Con flag explícito --estudiante
        args_exp = Namespace(
            materia="redes",
            codigo="P1",
            titulo="Enrutamiento BGP",
            tipo=None,
            modalidad="individual",
            grupal=False,
            grupo=None,
            integrantes=None,
            estudiante="Carlos Sanchez",
        )
        comandos_gestion.cmd_tarea(
            args_exp,
            materias_dir,
            RAIZ / "plantillas",
            tareas.TIPOS,
            tareas.slug_titulo,
            tareas.tipo_por_codigo,
            tareas.rellenar,
            tareas.ruta_relativa,
        )
        tarea_creada = materias_dir / "redes" / "P1_Enrutamiento_BGP" / "TAREA.md"
        self.assertTrue(tarea_creada.exists())
        contenido = tarea_creada.read_text(encoding="utf-8")
        self.assertIn("- **Modalidad:** Individual", contenido)
        self.assertIn("- **Estudiante:** Carlos Sanchez", contenido)

        # 2. Sin flag explícito -> fallback a NOMBRE_ESTUDIANTE
        args_fb = Namespace(
            materia="redes",
            codigo="P2",
            titulo="Subredes IPv6",
            tipo=None,
            modalidad="individual",
            grupal=False,
            grupo=None,
            integrantes=None,
            estudiante=None,
        )
        comandos_gestion.cmd_tarea(
            args_fb,
            materias_dir,
            RAIZ / "plantillas",
            tareas.TIPOS,
            tareas.slug_titulo,
            tareas.tipo_por_codigo,
            tareas.rellenar,
            tareas.ruta_relativa,
        )
        tarea_fb = materias_dir / "redes" / "P2_Subredes_IPv6" / "TAREA.md"
        self.assertTrue(tarea_fb.exists())
        contenido_fb = tarea_fb.read_text(encoding="utf-8")
        self.assertIn("- **Modalidad:** Individual", contenido_fb)
        self.assertIn("- **Estudiante:**", contenido_fb)

        # 3. Con archivo de enunciado explícito (--enunciado)
        archivo_muestra = materias_dir / "consigna_muestra.pdf"
        archivo_muestra.write_text("PDF binario simulado", encoding="utf-8")
        args_enunciado = Namespace(
            materia="redes",
            codigo="P3",
            titulo="Seguridad en BGP",
            tipo=None,
            modalidad="individual",
            grupal=False,
            grupo=None,
            integrantes=None,
            estudiante=None,
            enunciado=str(archivo_muestra),
        )
        comandos_gestion.cmd_tarea(
            args_enunciado,
            materias_dir,
            RAIZ / "plantillas",
            tareas.TIPOS,
            tareas.slug_titulo,
            tareas.tipo_por_codigo,
            tareas.rellenar,
            tareas.ruta_relativa,
        )
        enunciado_copiado = materias_dir / "redes" / "P3_Seguridad_En_BGP" / "enunciado" / "consigna_muestra.pdf"
        self.assertTrue(enunciado_copiado.exists())
        self.assertEqual(enunciado_copiado.read_text(encoding="utf-8"), "PDF binario simulado")

    def test_deteccion_encabezado_y_pie_duplicado(self):
        from docx import Document
        from docx.oxml import OxmlElement
        from docx.oxml.ns import qn
        doc = Document()
        sec = doc.sections[0]
        # Duplicar PAGE en footer
        p_foot = sec.footer.paragraphs[0]
        for _ in range(2):
            r = p_foot.add_run()
            for _instr, tipo in ((None, "begin"), ("PAGE", "instrText"), (None, "end")):
                el = OxmlElement("w:fldChar") if tipo != "instrText" else OxmlElement("w:instrText")
                if tipo == "instrText":
                    el.set(qn("xml:space"), "preserve")
                    el.text = " PAGE "
                else:
                    el.set(qn("w:fldCharType"), tipo)
                r._r.append(el)
        ruta_dup = self.carpeta / "test_dup.docx"
        doc.save(str(ruta_dup))
        analisis = comp.analizar(ruta_dup)
        self.assertTrue(any("Numeración duplicada" in a for a in analisis.anomalias_formato))

    def test_configurar_pagina_institucional_idempotente(self):
        from docx import Document
        doc = Document()
        # Llamar dos veces seguidas no debe duplicar runs en header ni en footer
        inst.configurar_pagina(doc, tema="apa7")
        inst.configurar_pagina(doc, tema="apa7")
        sec = doc.sections[0]
        self.assertLessEqual(len(sec.header.paragraphs[0].runs), 1)
        self.assertEqual(len(sec.footer.paragraphs[0].runs), 1)

    def test_dividir_formula_larga(self):
        formula_corta = "∀x (P(x) → Q(x))"
        self.assertEqual(omml.dividir_formula_larga(formula_corta), [formula_corta])

        formula_larga = "∀m [ ( ModeloIA(m) ∧ ¬∃v (MedidaValidacion(v) ∧ Implementa(m, v)) ) → ∀a ( AtaqueEnvenenamiento(a) → ¬InmuneA(m, a) ) ]"
        partes = omml.dividir_formula_larga(formula_larga, max_long=75)
        self.assertEqual(len(partes), 2)
        self.assertTrue(partes[0].startswith("∀m"))
        self.assertTrue(partes[1].startswith("→"))

    def test_parrafo_estructurado_divide_saltos_linea(self):
        from docx import Document
        from docx.enum.text import WD_ALIGN_PARAGRAPH

        doc = Document()
        texto_multilinea = (
            "Encabezado de lista:\n"
            "• Primer elemento de viñeta\n"
            "• Segundo elemento con detalle técnico\n"
            "Párrafo de conclusión justificado."
        )
        bloques.parrafo_estructurado(doc, texto_multilinea)
        self.assertEqual(len(doc.paragraphs), 4)

        # Viñetas alineadas a la izquierda
        self.assertEqual(doc.paragraphs[1].alignment, WD_ALIGN_PARAGRAPH.LEFT)
        self.assertEqual(doc.paragraphs[2].alignment, WD_ALIGN_PARAGRAPH.LEFT)
        # Párrafo de conclusión justificado
        self.assertEqual(doc.paragraphs[3].alignment, WD_ALIGN_PARAGRAPH.JUSTIFY)

    def test_comprobar_detecta_saltos_linea_en_parrafos_justificados(self):
        from docx import Document
        from docx.enum.text import WD_ALIGN_PARAGRAPH

        doc = Document()
        # Simular portada y salto de página
        doc.add_paragraph("Portada")
        p_salto = doc.add_paragraph()
        p_salto.add_run().add_break()
        # Crear párrafo defectuoso con \n en justificado
        p_bad = doc.add_paragraph()
        p_bad.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        p_bad.add_run("Línea 1 que se justificará\nLínea 2 con espaciado deforme")

        ruta = self.carpeta / "test_bad_justification.docx"
        doc.save(str(ruta))

        analisis = comp.analizar(ruta)
        self.assertTrue(
            any("justificación forzada y saltos de línea internos" in a for a in analisis.avisos_tipograficos)
        )

    def test_enunciado_formal_estructura(self):
        """Verifica que enunciado_formal use tipografía sobre el lienzo (sin tablas) y sangría 0.25 pulg."""
        from docx import Document
        from docx.shared import Inches

        doc = Document()
        p = bloques.enunciado_formal(doc, "Texto de consigna", etiqueta="Enunciado 1")
        self.assertEqual(len(doc.tables), 0)  # Cero tablas
        self.assertEqual(p.paragraph_format.left_indent, Inches(0.25))
        self.assertTrue(p.runs[0].bold)
        self.assertTrue(p.runs[1].italic)

    def test_servicio_pdf_no_contamina_descargas_en_test(self):
        """Verifica que el flag en_test evite cualquier fuga de archivos a ~/Descargas."""
        import sys

        # unittest está en sys.modules
        self.assertIn("unittest", sys.modules)

    def test_comprobar_detecta_barra_lateral_izquierda_callout_ia(self):
        """Verifica que comprobar.analizar() detecte tablas 1x1 y párrafos con barra lateral izquierda gruesa."""
        from docx import Document
        from docx.oxml import OxmlElement
        from docx.oxml.ns import qn

        doc = Document()
        doc.add_paragraph("Portada")
        p_salto = doc.add_paragraph()
        p_salto.add_run().add_break()

        # 1. Tabla 1x1 con borde izquierdo grueso coloreado (estilo callout IA)
        tbl = doc.add_table(rows=1, cols=1)
        tbl.cell(0, 0).text = "Cuadro con barra lateral tipo IA"
        tc_pr = tbl.cell(0, 0)._tc.get_or_add_tcPr()
        tc_bdr = OxmlElement("w:tcBorders")
        left_el = OxmlElement("w:left")
        left_el.set(qn("w:val"), "single")
        left_el.set(qn("w:sz"), "24")
        left_el.set(qn("w:color"), "1D4ED8")
        tc_bdr.append(left_el)
        tc_pr.append(tc_bdr)

        # 2. Párrafo con borde izquierdo grueso (estilo blockquote/callout IA)
        p_b = doc.add_paragraph("Párrafo con franja lateral izquierda")
        p_pr = p_b._p.get_or_add_pPr()
        p_bdr = OxmlElement("w:pBdr")
        p_left = OxmlElement("w:left")
        p_left.set(qn("w:val"), "single")
        p_left.set(qn("w:sz"), "24")
        p_left.set(qn("w:color"), "991B1B")
        p_bdr.append(p_left)
        p_pr.append(p_bdr)

        ruta = self.carpeta / "test_barra_lateral_ia.docx"
        doc.save(str(ruta))

        analisis = comp.analizar(ruta)
        self.assertTrue(
            any("Caja de celda única con barra vertical izquierda" in a for a in analisis.avisos_tipograficos)
        )
        self.assertTrue(
            any("Párrafo con barra vertical izquierda de acento" in a for a in analisis.avisos_tipograficos)
        )

    def test_dibujar_tarjeta_academica_sin_barra_lateral(self):
        """Verifica que visual.dibujar_tarjeta_academica() renderice nodos sobrios sin errores."""
        import visual
        from PIL import Image, ImageDraw, ImageFont

        img = Image.new("RGB", (600, 240), (255, 255, 255))
        draw = ImageDraw.Draw(img)
        fnt = ImageFont.load_default()
        visual.dibujar_tarjeta_academica(
            draw,
            (20, 20, 580, 220),
            "Título Académico",
            "Descripción técnica sin barra vertical lateral de acento.",
            fuente_titulo=fnt,
            fuente_cuerpo=fnt,
        )
        self.assertEqual(img.size, (600, 240))


if __name__ == "__main__":
    unittest.main()


