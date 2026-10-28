"""Exercise the public v2 module CLI in isolated child processes."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import test_build as fixtures


class CliTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="tp-cli-", dir=os.environ.get("TMPDIR"))
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.data = self.base / "data"
        fixtures.write_fixture(self.data)
        self.output = self.base / "site"

    def run_cli(self, *args):
        env = {k: os.environ[k] for k in ("PATH", "HOME", "TMPDIR", "LANG") if k in os.environ}
        return subprocess.run([sys.executable, "-m", "thinkpad_archive", *args], cwd=fixtures.ROOT, env=env, capture_output=True, text=True, timeout=30)

    def test_help_describes_public_finder_only(self):
        result = self.run_cli("build", "--help")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("--data-dir", result.stdout)
        self.assertIn("--locales-dir", result.stdout)
        self.assertNotIn("--private-map", result.stdout)
        self.assertNotIn("private", result.stdout.lower())

    def test_build_v2_public_default_en_and_explicit_spanish(self):
        for lang in (None, "es"):
            with self.subTest(lang=lang):
                output = self.base / ("public-en" if lang is None else "public-es")
                args = ["build", "--output", str(output), "--data-dir", str(self.data), "--locales-dir", str(fixtures.ROOT / "locales")]
                if lang:
                    args += ["--default-language", lang]
                result = self.run_cli(*args)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn('<html lang="' + (lang or "en") + '">', (output / "index.html").read_text())
                self.assertIn("Built", result.stdout)
                self.assertNotIn(str(self.base), result.stdout + result.stderr)
                self.assertFalse(any(output.rglob("volumes.html")))

    def test_error_is_sanitized_nonzero_no_traceback(self):
        (self.data / "drivers.json").write_text("not json")
        result = self.run_cli("build", "--output", str(self.output), "--data-dir", str(self.data))
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn(str(self.base), result.stdout + result.stderr)
        self.assertNotIn("Traceback", result.stderr)
        self.assertIn("error", result.stderr.lower())
        self.assertNotIn("private", result.stderr)
        self.assertFalse(self.output.exists())

    def test_existing_output_rejected_without_changes(self):
        self.output.mkdir()
        marker = self.output / "marker"
        marker.write_text("unchanged")
        result = self.run_cli("build", "--output", str(self.output), "--data-dir", str(self.data))
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(marker.read_text(), "unchanged")
        self.assertEqual(list(self.output.iterdir()), [marker])

    def test_missing_command_invalid_language_missing_output(self):
        for args in ([], ["build"], ["build", "--output", str(self.output), "--default-language", "../en", "--data-dir", str(self.data)]):
            result = self.run_cli(*args)
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(self.output.exists())


if __name__ == "__main__":
    unittest.main()
