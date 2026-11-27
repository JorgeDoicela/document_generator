# -*- coding: utf-8 -*-
"""Pruebas unitarias deterministas (sin red) para plantillas/verificador_citas.py."""
import json
import sys
import tempfile
import unittest
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "plantillas"))

import apa_docx  # noqa: E402
import verificador_citas as vc  # noqa: E402


class TestVerificadorCitas(unittest.TestCase):
    """Valida detección de DOIs reales/falsos/reciclados, URLs y búsquedas en catálogos."""

    def test_extraccion_doi_url_anio(self) -> None:
        ref_doi = (
            "National Institute of Standards and Technology. (2024). "
            "The NIST Cybersecurity Framework (CSF) 2.0. https://doi.org/10.6028/NIST.CSWP.29."
        )
        self.assertEqual(vc.extraer_doi(ref_doi), "10.6028/NIST.CSWP.29")
        self.assertEqual(vc.extraer_anio(ref_doi), 2024)

        ref_url = "Goodfellow, I. (2016). Deep Learning. MIT Press. https://www.deeplearningbook.org."
        self.assertIsNone(vc.extraer_doi(ref_url))
        self.assertEqual(vc.extraer_url(ref_url), "https://www.deeplearningbook.org")

    def test_doi_valido_coincidente_crossref(self) -> None:
        def fake_fetch(url: str, metodo: str, timeout: float) -> vc.RespuestaHTTP:
            self.assertIn("api.crossref.org/works/", url)
            payload = {
                "message": {
                    "title": ["The NIST Cybersecurity Framework (CSF) 2.0"],
                    "issued": {"date-parts": [[2024]]},
                    "author": [],
                }
            }
            return vc.RespuestaHTTP(status=200, cuerpo=json.dumps(payload))

        res = vc.verificar_referencia(
            "National Institute of Standards and Technology. (2024). "
            "The NIST Cybersecurity Framework (CSF) 2.0. https://doi.org/10.6028/NIST.CSWP.29",
            fetcher=fake_fetch,
        )
        self.assertEqual(res.estado, vc.ESTADO_VERIFICADA)
        self.assertEqual(res.codigo, "verificada_doi")

    def test_doi_inexistente_404_bloquea_como_error(self) -> None:
        def fake_fetch(url: str, metodo: str, timeout: float) -> vc.RespuestaHTTP:
            return vc.RespuestaHTTP(status=404, error="Not Found")

        res = vc.verificar_referencia(
            "Autor Falso. (2025). Artículo Alucinado. https://doi.org/10.9999/falso.2025.001",
            fetcher=fake_fetch,
        )
        self.assertEqual(res.estado, vc.ESTADO_ERROR)
        self.assertEqual(res.codigo, "doi_inexistente")

    def test_doi_reciclado_de_otra_obra_bloquea_como_error(self) -> None:
        def fake_fetch(url: str, metodo: str, timeout: float) -> vc.RespuestaHTTP:
            payload = {
                "message": {
                    "title": ["Photosynthesis in Antarctic Marine Diatoms"],
                    "issued": {"date-parts": [[2018]]},
                    "author": [{"family": "Smith"}],
                }
            }
            return vc.RespuestaHTTP(status=200, cuerpo=json.dumps(payload))

        res = vc.verificar_referencia(
            "Pérez, J. (2024). Arquitectura Zero Trust en Kubernetes. https://doi.org/10.1000/reciclado",
            fetcher=fake_fetch,
        )
        self.assertEqual(res.estado, vc.ESTADO_ERROR)
        self.assertEqual(res.codigo, "doi_no_coincide")
        self.assertIn("Photosynthesis", res.detalle)

    def test_url_viva_rota_y_bloqueada_anti_bot(self) -> None:
        def fetch_viva(url: str, metodo: str, timeout: float) -> vc.RespuestaHTTP:
            return vc.RespuestaHTTP(status=200)

        def fetch_404(url: str, metodo: str, timeout: float) -> vc.RespuestaHTTP:
            return vc.RespuestaHTTP(status=404, error="Not Found")

        def fetch_403(url: str, metodo: str, timeout: float) -> vc.RespuestaHTTP:
            return vc.RespuestaHTTP(status=403, error="Forbidden")

        r_ok = vc.verificar_referencia("Org. (2024). Guía. https://ejemplo.org/ok", fetcher=fetch_viva)
        self.assertEqual(r_ok.estado, vc.ESTADO_VERIFICADA)

        r_err = vc.verificar_referencia("Org. (2024). Guía. https://ejemplo.org/no-existe", fetcher=fetch_404)
        self.assertEqual(r_err.estado, vc.ESTADO_ERROR)
        self.assertEqual(r_err.codigo, "url_rota")

        r_bot = vc.verificar_referencia("Org. (2024). Guía. https://editorial.org/paper", fetcher=fetch_403)
        self.assertEqual(r_bot.estado, vc.ESTADO_AVISO)
        self.assertEqual(r_bot.codigo, "url_bloqueada_bot")

    def test_sin_doi_ni_url_verifica_en_openlibrary_y_avisa_si_no_existe(self) -> None:
        def fetch_openlibrary(url: str, metodo: str, timeout: float) -> vc.RespuestaHTTP:
            if "api.openalex.org" in url:
                return vc.RespuestaHTTP(status=200, cuerpo=json.dumps({"results": []}))
            if "openlibrary.org" in url:
                return vc.RespuestaHTTP(
                    status=200,
                    cuerpo=json.dumps(
                        {
                            "docs": [
                                {
                                    "title": "Artificial Intelligence: A Modern Approach",
                                    "author_name": ["Stuart Russell", "Peter Norvig"],
                                    "first_publish_year": 1995,
                                }
                            ]
                        }
                    ),
                )
            return vc.RespuestaHTTP(status=404)

        r_ok = vc.verificar_referencia(
            "Russell, S., & Norvig, P. (2021). Artificial Intelligence: A Modern Approach (4.a ed.). Pearson.",
            fetcher=fetch_openlibrary,
        )
        self.assertEqual(r_ok.estado, vc.ESTADO_VERIFICADA)
        self.assertEqual(r_ok.codigo, "verificada_openlibrary")

        def fetch_vacio(url: str, metodo: str, timeout: float) -> vc.RespuestaHTTP:
            return vc.RespuestaHTTP(status=200, cuerpo=json.dumps({"results": [], "docs": []}))

        r_aviso = vc.verificar_referencia(
            "Autor Inventado, X. (2025). Libro Que Nunca Existió En Ningún Catálogo. Editorial Fantasma.",
            fetcher=fetch_vacio,
        )
        self.assertEqual(r_aviso.estado, vc.ESTADO_AVISO)
        self.assertEqual(r_aviso.codigo, "no_verificada_catalogo")

    def test_verificar_docx_extrae_referencias_y_evalua_modo_estricto(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            salida = Path(tmp) / "doc_citas.docx"
            doc, _, _ = apa_docx.nuevo_documento(
                titulo="Prueba Citas",
                materia="Pruebas",
                salida=salida,
                institucion="Org",
                carrera="Ing",
                nombre="Tester",
                formato="apa7",
            )
            bib = apa_docx.Bibliografia(estilo="apa7")
            bib.agregar(
                "real2024",
                ["Organización"],
                2024,
                "Estándar Real",
                "Editorial",
                url="https://ejemplo.org/real",
            )
            bib.agregar(
                "sinurl2024",
                ["Autor Local"],
                2024,
                "Monografía Universitaria Local",
                "Imprenta Local",
            )
            apa_docx.parrafo(doc, f"Texto {bib.cita('real2024')} y {bib.cita('sinurl2024')}.")
            apa_docx.referencias(doc, bib)
            apa_docx.guardar_documento(doc, salida)

            def fake_fetch(url: str, metodo: str, timeout: float) -> vc.RespuestaHTTP:
                if "ejemplo.org/real" in url:
                    return vc.RespuestaHTTP(status=200)
                return vc.RespuestaHTTP(status=200, cuerpo=json.dumps({"results": [], "docs": []}))

            inf = vc.verificar_docx(salida, fetcher=fake_fetch, max_workers=2)
            self.assertEqual(len(inf.verificadas), 1)
            self.assertEqual(len(inf.avisos), 1)
            self.assertEqual(len(inf.errores), 0)
            self.assertTrue(inf.ok(estricto=False))
            self.assertFalse(inf.ok(estricto=True))


if __name__ == "__main__":
    unittest.main()
