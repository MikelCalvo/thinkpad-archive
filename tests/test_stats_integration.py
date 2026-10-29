"""The public dashboard is linked everywhere; collection is explicit opt-in."""
from pathlib import Path
from html.parser import HTMLParser
import inspect
import os
import subprocess
import tempfile
import unittest

import test_build as fixtures
from thinkpad_archive import build_site

ROOT = Path(__file__).resolve().parents[1]


class Tags(HTMLParser):
    def __init__(self, text):
        super().__init__(convert_charrefs=True)
        self.tags = []
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        self.tags.append((tag, dict(attrs)))


class StatsIntegration(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=os.environ.get('TMPDIR'))
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        fixtures.write_fixture(self.root / 'data')

    def build(self, name='site', **kwargs):
        return build_site(self.root / name, data_dir=self.root / 'data', **kwargs)

    def test_default_build_links_public_stats_but_never_collects(self):
        site = self.build()
        for lang in ('en', 'es'):
            self.assertTrue((site / lang / 'stats.html').is_file())
        for page in site.rglob('*.html'):
            with self.subTest(page=str(page.relative_to(site))):
                text = page.read_text()
                tags = Tags(text).tags
                footer = text.split('<footer>', 1)[1].split('</footer>', 1)[0]
                self.assertIn('📊', footer)
                self.assertIn('Stats', footer)
                self.assertLess(footer.index('Mikel Calvo'), footer.index('Stats'))
                link = next(a for tag, a in tags if tag == 'a' and a.get('class') == 'footer-stats')
                self.assertEqual((page.parent / link['href']).name, 'stats.html')
                self.assertNotIn('analytics.js', text)
                self.assertNotIn('data-stats-enabled', text)
        stats = (site / 'es/stats.html').read_text()
        self.assertIn('id="stats-dashboard"', stats)
        self.assertIn('assets/stats.js', stats)
        self.assertIn('assets/stats.css', stats)
        self.assertIn('../en/stats.html', stats)
        self.assertIn('https://thinkpadarchive.com/es/stats.html', stats)
        self.assertNotIn('data-year-url', stats)
        self.assertNotIn('stats-export', stats)
        # No aggregate export control in the dashboard. The shared header may
        # offer the collection-free catalogue ZIP and checksum.
        self.assertNotIn(' download=', stats.split('<main', 1)[1])

    def test_opt_in_adds_only_same_origin_collector_except_dashboard(self):
        self.assertIn('stats_enabled', inspect.signature(build_site).parameters)
        site = self.build(stats_enabled=True)
        for page in site.rglob('*.html'):
            text = page.read_text()
            tags = Tags(text).tags
            csp = next(a['content'] for tag, a in tags if a.get('http-equiv') == 'Content-Security-Policy')
            self.assertIn("connect-src 'self'", csp)
            if page.name == 'stats.html':
                self.assertNotIn('analytics.js', text)
                self.assertNotIn('data-stats-enabled', text)
            else:
                self.assertIn('data-stats-enabled="true"', text)
                self.assertEqual(sum(tag == 'script' and a.get('src', '').endswith('/analytics.js') for tag, a in tags), 1)
        for name in ('stats.js', 'stats.css', 'analytics.js'):
            self.assertEqual((site / 'assets' / name).read_bytes(), (ROOT / 'assets' / name).read_bytes())

    def test_opt_in_requires_actual_boolean_before_creating_output(self):
        self.assertIn('stats_enabled', inspect.signature(build_site).parameters)
        for index, value in enumerate(('yes', 1, None)):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    self.build('bad-' + str(index), stats_enabled=value)
                self.assertFalse((self.root / ('bad-' + str(index))).exists())

    def test_cli_opt_in_builds_dashboard_and_collector(self):
        argv = ['python3', '-m', 'thinkpad_archive', 'build', '--output', str(self.root / 'cli'), '--data-dir', str(self.root / 'data'), '--enable-stats']
        result = subprocess.run(argv, cwd=ROOT, text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('analytics.js', (self.root / 'cli/en/index.html').read_text())
        self.assertNotIn('analytics.js', (self.root / 'cli/es/stats.html').read_text())
