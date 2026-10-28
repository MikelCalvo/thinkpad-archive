"""Concise catalogue rows without losing identity, counts or navigation."""
from pathlib import Path
from html.parser import HTMLParser
import os
import re
import tempfile
import unittest

import test_build as fixtures
from thinkpad_archive import build_site


class Text(HTMLParser):
    def __init__(self, markup):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.feed(markup)

    def handle_data(self, data):
        self.parts.append(data)


def plain(markup):
    return ''.join(Text(markup).parts)


class LandingCleanup(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(dir=os.environ.get('TMPDIR'))
        cls.addClassCleanup(cls.temp.cleanup)
        root = Path(cls.temp.name)
        records = fixtures.fixture_data()
        records['models']['models'][0]['introduced'] = [dict(year=1992, variants=['700C'], url='https://example.org/700c')]
        fixtures.write_fixture(root / 'data', records)
        cls.output = build_site(root / 'site', data_dir=root / 'data')

    def catalogue_pages(self):
        for lang in ('en', 'es'):
            for page in ('index.html', 'catalogue.html', 'years/1992.html'):
                yield lang, (self.output / lang / page).read_text()

    def test_short_bilingual_table_headers(self):
        expected = {'en': ['Model', 'Family', 'Manuals', 'Drivers & Software'],
                    'es': ['Modelo', 'Familia', 'Manuales', 'Controladores y software']}
        for lang, text in self.catalogue_pages():
            with self.subTest(lang=lang):
                head = text.split('<thead>', 1)[1].split('</thead>', 1)[0]
                self.assertEqual([plain(cell) for cell in re.findall(r'<th[^>]*>(.*?)</th>', head)], expected[lang])

    def test_all_view_filter_labels_and_options_are_concise(self):
        expected = {
            'en': {'labels': ['Models', 'Family', 'Drivers & Software', 'Manuals'],
                   'hint': 'Model…', 'options': ['With manuals', 'Without manuals', 'With drivers & software', 'Without drivers & software']},
            'es': {'labels': ['Modelos', 'Familia', 'Controladores y software', 'Manuales'],
                   'hint': 'Modelo…', 'options': ['Con manuales', 'Sin manuales', 'Con controladores y software', 'Sin controladores y software']}}
        for lang, text in self.catalogue_pages():
            with self.subTest(lang=lang):
                form = text.split('<form id="filters"', 1)[1].split('</form>', 1)[0]
                labels = [plain(label) for label in re.findall(r'<label[^>]*>(.*?)</label>', form)]
                self.assertEqual(labels, expected[lang]['labels'])
                self.assertIn('placeholder="' + expected[lang]['hint'] + '"', form)
                for option in expected[lang]['options']:
                    self.assertIn(option, plain(form))

    def test_support_cells_are_only_the_preserved_counts_and_links(self):
        for lang, text in self.catalogue_pages():
            body = text.split('<tbody id="model-rows">', 1)[1].split('</tbody>', 1)[0]
            rows = re.findall(r'<tr\b[^>]*>(.*?)</tr>', body)
            self.assertEqual(len(rows), 3)
            for row in rows:
                cells = re.findall(r'<td>(.*?)</td>', row)
                self.assertEqual(len(cells), 3)
                for cell in cells[1:]:
                    self.assertRegex(plain(cell), r'^\d+$')
                    self.assertNotIn('<span', cell)
                self.assertIn('class="alias"', cells[0])  # family/era remains
            self.assertIn('<span class="alias">700 C</span>', body)
            self.assertRegex(body, r'href="[^"]*700c\.html#manuals">1</a>')
            self.assertRegex(body, r'href="[^"]*700c\.html#drivers">2</a>')

    def test_matching_counter_is_absent_and_timeline_counts_remain(self):
        for lang, text in self.catalogue_pages():
            self.assertNotIn('result-count', text)
            self.assertNotIn('Entradas coincidentes', text)
            self.assertNotIn('Matching entries', text)
            self.assertIn('class="year-count">3</span>', text)
            self.assertIn('id="empty-results"', text)
            self.assertIn('id="model-search"', text)

    def test_css_default_is_dark_without_javascript_or_system_preference(self):
        css = (self.output / 'assets/style.css').read_text()
        self.assertNotIn('prefers-color-scheme', css)
        declarations = css.split(':root:not([data-theme]){', 1)[1].split('}', 1)[0]
        self.assertIn('color-scheme:dark', declarations)
        self.assertIn('--paper:#18191b', declarations)


if __name__ == '__main__':
    unittest.main()
