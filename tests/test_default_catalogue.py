"""The complete catalogue lives at index; catalogue.html remains a legacy entry."""
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import urlsplit
import os
import tempfile
import unittest

import test_build as fixtures
from thinkpad_archive import build_site


class Tags(HTMLParser):
    def __init__(self, text):
        super().__init__(convert_charrefs=True)
        self.tags = []
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        self.tags.append((tag, dict(attrs)))


class DefaultCatalogue(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(dir=os.environ.get('TMPDIR'))
        cls.addClassCleanup(cls.temp.cleanup)
        base = Path(cls.temp.name)
        records = fixtures.fixture_data()
        records['models']['models'][0]['introduced'] = [
            {'year': 1992, 'variants': ['700C'], 'url': 'https://example.org/history'}]
        fixtures.write_fixture(base / 'data', records)
        cls.site = build_site(base / 'site', data_dir=base / 'data')

    def test_all_year_links_use_the_default_index(self):
        for page in self.site.rglob('*.html'):
            for tag, attrs in Tags(page.read_text()).tags:
                if tag == 'a' and attrs.get('data-year') == 'all':
                    with self.subTest(page=str(page.relative_to(self.site))):
                        target = (page.parent / urlsplit(attrs['href']).path).resolve()
                        self.assertEqual(target.name, 'index.html')
                        self.assertIn(target.parent.name, ('en', 'es'))

    def test_language_all_targets_use_each_languages_default_index(self):
        for page in self.site.rglob('*.html'):
            for _, attrs in Tags(page.read_text()).tags:
                if 'data-all-url' in attrs:
                    with self.subTest(page=str(page.relative_to(self.site)), language=attrs['data-language-choice']):
                        target = (page.parent / attrs['data-all-url']).resolve()
                        self.assertEqual(target, (self.site / attrs['data-language-choice'] / 'index.html').resolve())

    def test_legacy_catalogue_retains_all_static_records(self):
        # Characterization: keep old direct links usable, including without JS.
        for lang in ('en', 'es'):
            for suffix in ('index.html', 'catalogue.html'):
                page = self.site / lang / suffix
                rows = [a for _, a in Tags(page.read_text()).tags if 'data-model-id' in a]
                self.assertEqual({a['data-model-id'] for a in rows}, {'700c', '700cs', 'x230-tablet'})
                self.assertTrue(all('hidden' not in a for a in rows))
