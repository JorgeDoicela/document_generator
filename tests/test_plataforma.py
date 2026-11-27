# -*- coding: utf-8 -*-
"""Pruebas unitarias para la capa de abstracción multiplataforma (plantillas/plataforma.py)."""
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from plantillas import plataforma


class TestPlataforma(unittest.TestCase):
    def test_entorno_utf8_inyecta_variables(self):
        env = plataforma.entorno_utf8({"FOO": "bar"}, EXTRA="1")
        self.assertEqual(env["FOO"], "bar")
        self.assertEqual(env["EXTRA"], "1")
        self.assertEqual(env["PYTHONUTF8"], "1")
        self.assertEqual(env["PYTHONIOENCODING"], "utf-8")

    def test_rutas_y_comandos_windows_vs_posix(self):
        raiz = Path("/proyecto")
        with mock.patch.object(plataforma, "es_windows", return_value=True):
            self.assertEqual(
                plataforma.ruta_python_venv(raiz),
                raiz / ".venv" / "Scripts" / "python.exe",
            )
            self.assertEqual(plataforma.comando_python_venv_relativo(), r".venv\Scripts\python.exe")
            self.assertEqual(plataforma.comando_copiar_env(), "copy .env.example .env")

        with mock.patch.object(plataforma, "es_windows", return_value=False):
            self.assertEqual(
                plataforma.ruta_python_venv(raiz),
                raiz / ".venv" / "bin" / "python",
            )
            self.assertEqual(plataforma.comando_python_venv_relativo(), ".venv/bin/python")
            self.assertEqual(plataforma.comando_copiar_env(), "cp .env.example .env")

    def test_directorio_cache_base_windows_y_posix(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            with (
                mock.patch.object(plataforma, "es_windows", return_value=True),
                mock.patch.dict(os.environ, {"LOCALAPPDATA": tmpdir}, clear=False),
            ):
                self.assertEqual(
                    plataforma.directorio_cache_base(),
                    Path(tmpdir) / plataforma.nombre_proyecto(),
                )

        with mock.patch.object(plataforma, "es_windows", return_value=False):
            self.assertEqual(plataforma.directorio_cache_base(), Path.home() / ".cache")

    def test_es_ruta_temporal(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            archivo = Path(tmpdir) / "doc.docx"
            archivo.write_text("x", encoding="utf-8")
            self.assertTrue(plataforma.es_ruta_temporal(archivo))
        ruta_no_temporal = Path.home().resolve() / "document_generator_no_tmp" / "doc.docx"
        self.assertFalse(plataforma.es_ruta_temporal(ruta_no_temporal))

    def test_buscar_libreoffice_respeta_soffice_bin(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            fake_bin = Path(tmpdir) / "soffice.exe"
            fake_bin.write_text("stub", encoding="utf-8")
            with mock.patch.dict(os.environ, {"SOFFICE_BIN": str(fake_bin)}, clear=False):
                self.assertEqual(plataforma.buscar_libreoffice(), str(fake_bin))

    def test_buscar_libreoffice_fallback_windows_program_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            prog_dir = Path(tmpdir) / "LibreOffice" / "program"
            prog_dir.mkdir(parents=True)
            soffice_com = prog_dir / "soffice.com"
            soffice_com.write_text("stub", encoding="utf-8")

            with (
                mock.patch.object(plataforma, "es_windows", return_value=True),
                mock.patch.object(plataforma, "es_macos", return_value=False),
                mock.patch.dict(
                    os.environ,
                    {"SOFFICE_BIN": "", "ProgramFiles": tmpdir, "ProgramFiles(x86)": ""},
                    clear=False,
                ),
                mock.patch("shutil.which", return_value=None),
            ):
                self.assertEqual(plataforma.buscar_libreoffice(), str(soffice_com))

    def test_entorno_libreoffice_windows_establece_temp_y_tmp(self):
        tmp_dir = Path("/tmp/lo-test")
        with mock.patch.object(plataforma, "es_windows", return_value=True):
            env = plataforma.entorno_libreoffice(tmp_dir)
            self.assertEqual(env["TMPDIR"], str(tmp_dir))
            self.assertEqual(env["TEMP"], str(tmp_dir))
            self.assertEqual(env["TMP"], str(tmp_dir))
            self.assertEqual(env["PYTHONUTF8"], "1")

    def test_kwargs_proceso_aislado_windows_vs_posix(self):
        def _dummy() -> None:
            return None

        with mock.patch.object(plataforma, "es_windows", return_value=True):
            kw = plataforma.kwargs_proceso_aislado(_dummy)
            self.assertIn("creationflags", kw)
            self.assertNotIn("preexec_fn", kw)
            self.assertNotIn("start_new_session", kw)

        with mock.patch.object(plataforma, "es_windows", return_value=False):
            kw = plataforma.kwargs_proceso_aislado(_dummy)
            self.assertTrue(kw["start_new_session"])
            self.assertIs(kw["preexec_fn"], _dummy)
            self.assertNotIn("creationflags", kw)

    def test_terminar_arbol_procesos_windows_usa_taskkill(self):
        proc = mock.MagicMock()
        proc.pid = 4321
        with (
            mock.patch.object(plataforma, "es_windows", return_value=True),
            mock.patch("subprocess.run") as mock_run,
        ):
            plataforma.terminar_arbol_procesos(proc)
            mock_run.assert_called_once()
            args_cmd = mock_run.call_args.args[0]
            self.assertEqual(args_cmd, ["taskkill", "/F", "/T", "/PID", "4321"])
            proc.kill.assert_called_once()

    def test_directorio_descargas_windows_fallback_downloads(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            fake_home = Path(tmpdir)
            downloads = fake_home / "Downloads"
            downloads.mkdir()
            with (
                mock.patch.object(plataforma, "es_windows", return_value=True),
                mock.patch.object(plataforma, "_descargas_windows_registro", return_value=None),
                mock.patch.object(Path, "home", return_value=fake_home),
            ):
                self.assertEqual(plataforma.directorio_descargas(), downloads)

    def test_resolver_fuente_monospace_explicita_y_fallback_windows(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            f_exp = Path(tmpdir) / "custom.ttf"
            f_exp.write_bytes(b"font")
            self.assertEqual(plataforma.resolver_fuente_monospace(fuente_explicita=f_exp), f_exp)

            win_fonts = Path(tmpdir) / "Fonts"
            win_fonts.mkdir()
            consola = win_fonts / "consola.ttf"
            consola.write_bytes(b"font")
            with (
                mock.patch.object(plataforma, "es_windows", return_value=True),
                mock.patch.object(plataforma, "es_macos", return_value=False),
                mock.patch.dict(os.environ, {"WINDIR": tmpdir}, clear=False),
            ):
                self.assertEqual(plataforma.resolver_fuente_monospace(), consola)


if __name__ == "__main__":
    unittest.main()
