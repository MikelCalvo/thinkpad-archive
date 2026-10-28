"""Topbar and wordmark requirements; metadata is not changed."""
from html.parser import HTMLParser
from pathlib import Path
import os
import tempfile
import unittest

import test_build as fixtures

ROOT = Path(__file__).resolve().parents[1]
COUNTS_NOTE = 'Driver counts describe source metadata entries, not unique executable packages or verified downloads.'


class Elements(HTMLParser):
    def __init__(self, text):
        super().__init__(convert_charrefs=True)
        self.starts = []
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        self.starts.append((tag, dict(attrs)))


class Topbar(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=os.environ.get('TMPDIR'))
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        fixtures.write_fixture(self.base / 'data')
        import thinkpad_archive
        self.output = thinkpad_archive.build_site(self.base / 'site', data_dir=self.base / 'data')

    def test_header_has_single_row_languages_first_without_small_brand(self):
        for relative in ['index.html', 'en/index.html', 'es/index.html', 'en/models/700c.html', 'es/sources.html']:
            text = (self.output / relative).read_text()
            header = text.split('<header', 1)[1].split('</header>', 1)[0]
            self.assertIn('class="topbar"', header)
            self.assertNotIn('class="brand"', header)
            self.assertNotIn('FIELD REFERENCE', header)
            self.assertNotIn('REFERENCIA TÉCNICA', header)
            self.assertNotIn('trackpoint', header)
            self.assertLess(header.index('class="language-nav"'), header.index('class="main-nav"'))
            self.assertIn('hreflang="en"', header)
            self.assertIn('hreflang="es"', header)

    def test_explanatory_count_paragraph_is_not_rendered_anywhere(self):
        for path in self.output.rglob('*.html'):
            text = path.read_text()
            self.assertNotIn(COUNTS_NOTE, text)
            self.assertNotIn('Las cifras describen entradas de metadatos de las fuentes', text)
            self.assertNotIn('Driver counts describe', text)
        home = (self.output / 'index.html').read_text()
        self.assertIn('Driver metadata entries</dt><dd>4</dd>', home)
        self.assertNotIn('dismissible-notice', home)

    def test_catalogue_has_no_search_help_paragraph_and_keeps_controls(self):
        for relative in ('index.html', 'en/index.html', 'es/index.html'):
            text = (self.output / relative).read_text()
            self.assertNotIn('Without JavaScript, every entry remains below.', text)
            self.assertNotIn('Sin JavaScript, todas las entradas siguen visibles.', text)
            self.assertIn('<form id="filters"', text)
            self.assertIn('id="model-search"', text)
            self.assertIn('id="model-rows"', text)
            self.assertIn('id="catalogue-heading"', text)

    def test_title_preserves_normal_i_for_copy_search_and_without_css(self):
        for relative in ('index.html', 'en/index.html', 'es/index.html'):
            text = (self.output / relative).read_text()
            title = text.split('<h1 ', 1)[1].split('</h1>', 1)[0]
            # Strip only markup; aria-label must not conceal misspelled text.
            import re
            visible_text = re.sub('<[^>]+>', '', title.split('>', 1)[1])
            self.assertEqual(visible_text, 'ThinkPad Archive')

    def test_title_has_accessible_plain_name_and_decorative_red_dot(self):
        text = (self.output / 'index.html').read_text()
        tags = Elements(text).starts
        headings = [attrs for tag, attrs in tags if tag == 'h1']
        self.assertEqual(headings, [{'class': 'archive-title', 'aria-label': 'ThinkPad Archive'}])
        self.assertIn('<span class="title-word" aria-hidden="true">Th<span class="title-i">i</span>nkPad</span>', text)
        self.assertIn('<span class="archive-word" aria-hidden="true">Archive</span>', text)
        css = (self.output / 'assets/style.css').read_text()
        self.assertIn('.title-i{', css)
        self.assertIn('linear-gradient(to bottom,var(--red) 33%,var(--ink) 33%)', css)
        self.assertIn('background-clip:text', css)
        self.assertNotIn('.archive-title span{', css)


if __name__ == '__main__':
    unittest.main()
