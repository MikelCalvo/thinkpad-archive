"""Hosted offline assets stay local, versioned and nonrecursive."""
from pathlib import Path
from html.parser import HTMLParser
import hashlib
import json
import os
import tempfile
import unittest
from unittest.mock import patch
import zipfile

import test_build as fixtures

ROOT = Path(__file__).resolve().parents[1]

class Tags(HTMLParser):
    def __init__(self):
        super().__init__(); self.tags = []
    def handle_starttag(self, tag, attrs):
        self.tags.append((tag, dict(attrs)))

class OfflineDownload(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=os.environ.get('TMPDIR'))
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.data = self.root / 'data'
        fixtures.write_fixture(self.data)

    def build(self, **kwargs):
        from thinkpad_archive import build_site
        return build_site(self.root / 'site', data_dir=self.data, **kwargs)

    def test_default_build_has_real_local_zip_checksum_and_native_bilingual_download(self):
        with patch('socket.socket', side_effect=RuntimeError('Network forbidden')):
            site = self.build()
        version = (ROOT / 'VERSION').read_text().strip()
        name = 'thinkpad-archive-' + version + '-offline.zip'
        archive = site / 'downloads' / name
        self.assertTrue(archive.is_file(), 'Hosted build must include the actual offline ZIP')
        digest = hashlib.sha256(archive.read_bytes()).hexdigest()
        self.assertEqual((site / 'downloads' / (name + '.sha256')).read_text(), digest + '  ' + name + '\n')
        self.assertEqual({p.name for p in (site / 'downloads').iterdir()}, {name, name + '.sha256'})
        for lang, label in [('en', 'Download offline catalogue'), ('es', 'Descargar catálogo offline')]:
            for suffix, prefix in [('index.html', '../'), ('models/700c.html', '../../')]:
                text = (site / lang / suffix).read_text(); parser = Tags(); parser.feed(text)
                links = [a for t, a in parser.tags if t == 'a' and a.get('class') == 'offline-download']
                self.assertEqual(len(links), 1)
                self.assertEqual(links[0]['href'], prefix + 'downloads/' + name)
                self.assertEqual(links[0]['download'], name)
                self.assertEqual(links[0]['aria-label'], label)
                action = text.split('class="offline-download"', 1)[1].split('</a>', 1)[0]
                self.assertIn('<svg', action)
                self.assertIn('aria-hidden="true"', action)
                self.assertLess(action.index('<svg'), action.index(label + '</span>'))
                self.assertIn('<span>' + label + '</span>', action)
                self.assertIn(version, text)
                self.assertNotIn('downloads/' + name + '.sha256', text)
                self.assertNotIn('releases/download/', text)
        with zipfile.ZipFile(archive) as z:
            self.assertIsNone(z.testzip())
            prefix = 'thinkpad-archive-' + version + '/'
            self.assertFalse(any('/downloads/' in n or n.endswith('.zip') for n in z.namelist()))
            self.assertNotIn('offline-download', z.read(prefix + 'en/index.html').decode())
            self.assertNotIn('data-stats-enabled', z.read(prefix + 'en/index.html').decode())
            manifest = json.loads(z.read(prefix + 'SHA256SUMS.json'))
            self.assertTrue(all(hashlib.sha256(z.read(prefix + p)).hexdigest() == h for p, h in manifest['files'].items()))

    def test_archive_built_from_same_metadata_language_and_never_collects(self):
        site = self.build(default_language='es', stats_enabled=True)
        archive = next((site / 'downloads').glob('*.zip'))
        version = (ROOT / 'VERSION').read_text().strip(); prefix = 'thinkpad-archive-' + version + '/'
        with zipfile.ZipFile(archive) as z:
            self.assertIn('lang="es"', z.read(prefix + 'index.html').decode())
            text = z.read(prefix + 'es/models/700c.html').decode()
            self.assertIn('ThinkPad 700C', text)
            self.assertNotIn('data-stats-enabled', text)
            self.assertNotIn('offline-download', text)
            self.assertIn('data-stats-enabled', (site / 'es/models/700c.html').read_text())

    def test_inline_hash_matches_real_zip_and_is_copyable_without_scripts(self):
        site = self.build()
        archive = next((site / 'downloads').glob('*.zip'))
        digest = hashlib.sha256(archive.read_bytes()).hexdigest()
        for page in site.rglob('*.html'):
            text = page.read_text()
            parser = Tags(); parser.feed(text)
            fields = [a for tag, a in parser.tags if tag == 'textarea' and a.get('id') == 'offline-hash']
            self.assertEqual(len(fields), 1, 'Inline SHA-256 field missing')
            field = fields[0]
            self.assertIn('readonly', field)
            self.assertNotIn('disabled', field)
            self.assertEqual(field['rows'], '2')
            self.assertIn('aria-label', field)
            self.assertIn('>' + digest + '</textarea>', text)
            self.assertNotIn('class="offline-checksum" href=', text)
        with zipfile.ZipFile(archive) as z:
            self.assertFalse(any('id="offline-hash"' in z.read(n).decode()
                                 for n in z.namelist() if n.endswith('.html')))

    def test_copy_icon_has_localized_feedback_and_progressive_no_script_fallback(self):
        site = self.build()
        for lang, label in [('en', 'Copy SHA-256'), ('es', 'Copiar SHA-256')]:
            text = (site / lang / 'index.html').read_text()
            parser = Tags(); parser.feed(text)
            buttons = [a for tag, a in parser.tags if tag == 'button' and a.get('id') == 'offline-copy']
            self.assertEqual(len(buttons), 1, 'Copy icon button missing')
            button = buttons[0]
            self.assertEqual(button['type'], 'button')
            self.assertEqual(button['aria-label'], label)
            self.assertEqual(button['title'], label)
            self.assertIn('hidden', button)
            for key in ('data-copy-label', 'data-copied-label', 'data-copy-failed'):
                self.assertTrue(button[key])
            self.assertIn('class="copy-icon"', text)
            self.assertIn('class="copy-check"', text)
            self.assertIn('id="offline-copy-status"', text)
            self.assertNotIn('select and copy', text)
            self.assertNotIn('selecciona y copia', text)

    def test_download_size_is_real_and_human_readable(self):
        from thinkpad_archive.render import human_size
        for size, en, es in [(999, '999 B', '999 B'), (1250, '1.3 kB', '1,3 kB'),
                             (200_000_000, '200 MB', '200 MB'), (1_500_000_000, '1.5 GB', '1,5 GB')]:
            self.assertEqual(human_size(size, 'en'), en)
            self.assertEqual(human_size(size, 'es'), es)
        site = self.build()
        archive = next((site / 'downloads').glob('*.zip'))
        for lang in ('en', 'es'):
            text = (site / lang / 'index.html').read_text()
            self.assertIn('<span class="offline-size">(' + human_size(archive.stat().st_size, lang) + ')</span>', text)

    def test_explicit_archive_optout_avoids_assets_and_unavailable_download_controls(self):
        site = self.build(offline_download=False)
        self.assertFalse((site / 'downloads').exists())
        self.assertNotIn('offline-download', (site / 'en/index.html').read_text())

    def test_bad_download_flags_refused_before_output(self):
        for value in (1, None, 'yes', []):
            with self.subTest(kind=type(value).__name__), self.assertRaises(ValueError):
                self.build(offline_download=value)
            self.assertFalse((self.root / 'site').exists())

    def test_packaging_failure_precedes_hosted_output_creation(self):
        import thinkpad_archive.offline_release as offline
        with patch.object(offline, 'build_offline_release', side_effect=ValueError('synthetic refusal')):
            with self.assertRaises(ValueError):
                self.build()
        self.assertFalse((self.root / 'site').exists())

if __name__ == '__main__':
    unittest.main()
