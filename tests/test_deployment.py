"""Static deployment contract; live HTTP smoke is a separate gate."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class DeploymentTests(unittest.TestCase):
    def test_image_builds_tests_and_checks_public_site(self):
        path = ROOT / 'Dockerfile'
        self.assertTrue(path.is_file(), 'A reproducible deployment image is required')
        text = path.read_text()
        for command in ('unittest discover', 'thinkpad_archive build', 'tools/check_site.py'):
            self.assertIn(command, text)
        self.assertNotIn('COPY . ', text)
        self.assertIn('COPY --from=build /public /srv', text)

    def test_origin_serves_http_without_certificates_and_narrow_webhook_only(self):
        path = ROOT / 'deploy' / 'Caddyfile'
        self.assertTrue(path.is_file(), 'A scoped HTTP origin configuration is required')
        text = path.read_text()
        self.assertIn('http://:8080', text)
        self.assertNotIn('/run/tls', text)
        self.assertNotIn('https://', text)
        for item in ('path /_deploy/github', 'method POST',
                     '/webhooks/source/github/events/manual', 'file_server'):
            self.assertIn(item, text)
        image = (ROOT / 'Dockerfile').read_text()
        self.assertIn('EXPOSE 8080', image)
        self.assertIn('http://127.0.0.1:8080/healthz', image)
        self.assertNotIn('--no-check-certificate', image)

    def test_context_admits_local_svg_favicon_but_not_unlisted_payloads(self):
        from fnmatch import fnmatchcase
        lines = (ROOT / '.dockerignore').read_text().splitlines()
        self.assertTrue((ROOT / 'assets/favicon.svg').is_file())
        for path, allowed in (('assets/favicon.svg', True), ('assets/style.css', True),
                              ('assets/language.js', True), ('assets/private.bin', False),
                              ('build/public/index.html', False), ('.git/config', False)):
            with self.subTest(path=path):
                matches = [line for line in lines if fnmatchcase(path, line.lstrip('!'))]
                self.assertTrue(matches)
                self.assertEqual(matches[-1].startswith('!'), allowed)

    def test_context_excludes_all_unlisted_files(self):
        path = ROOT / '.dockerignore'
        self.assertTrue(path.is_file(), 'Build context must be an allowlist')
        lines = path.read_text().splitlines()
        self.assertEqual(lines[0], '**')
        self.assertNotIn('!build/', lines)
        self.assertNotIn('!.git/', lines)


if __name__ == '__main__':
    unittest.main()
