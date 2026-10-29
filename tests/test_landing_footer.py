"""Catalogue cleanup and the shared two-line creator footer."""
from html import unescape
from html.parser import HTMLParser
from pathlib import Path
import os
import re
import tempfile
import unittest

import test_build as fixtures
import thinkpad_archive


def plain(text):
    return ' '.join(unescape(re.sub(r'<[^>]*>', '', text)).split())


class Tags(HTMLParser):
    def __init__(self, text):
        super().__init__(convert_charrefs=True)
        self.tags = []
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        self.tags.append((tag, dict(attrs)))


class LandingFooter(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=os.environ.get('TMPDIR'))
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        records = fixtures.fixture_data()
        records['models']['models'][0]['introduced'] = [
            {'year': 1992, 'variants': ['700C'], 'url': 'https://example.org/history'}]
        fixtures.write_fixture(self.root / 'data', records)
        self.site = thinkpad_archive.build_site(self.root / 'site', data_dir=self.root / 'data')

    def test_catalogue_views_omit_library_and_utility_cards(self):
        for lang in ('en', 'es'):
            for suffix in ('index.html', 'catalogue.html', 'years/1992.html', 'years/unknown.html'):
                with self.subTest(lang=lang, suffix=suffix):
                    text = (self.site / lang / suffix).read_text()
                    self.assertNotIn('reference-library', text)
                    self.assertNotIn('class="document"', text)
                    self.assertNotIn('class="utility"', text)
                    self.assertNotIn('PC Doctor', text)
                    self.assertIn('id="model-rows"', text)
                    self.assertIn('data-model-id="700c"', text)
                    self.assertIn('models/700c.html#manuals', text)

    def test_footer_is_only_independence_and_creator_in_both_languages(self):
        expected = {
            'en': ['Independent community reference · Not affiliated with IBM or Lenovo', 'Created by Mikel Calvo · 📊 Stats'],
            'es': ['Referencia comunitaria independiente · Sin afiliación con IBM ni Lenovo', 'Creado por Mikel Calvo · 📊 Stats'],
        }
        for path in self.site.rglob('*.html'):
            with self.subTest(path=str(path.relative_to(self.site))):
                text = path.read_text()
                match = re.search(r'<html lang="([^"]+)"', text)
                self.assertIsNotNone(match)
                assert match is not None
                lang = match[1]
                footer = text.split('<footer>', 1)[1].split('</footer>', 1)[0]
                paragraphs = re.findall(r'<p>(.*?)</p>', footer)
                self.assertEqual([plain(p) for p in paragraphs], expected[lang])

    def test_creator_name_alone_is_a_secure_new_tab_link(self):
        for lang in ('en', 'es'):
            for suffix in ('index.html', 'sources.html', 'models/700c.html', 'years/1992.html'):
                with self.subTest(lang=lang, suffix=suffix):
                    text = (self.site / lang / suffix).read_text()
                    footer = text.split('<footer>', 1)[1].split('</footer>', 1)[0]
                    links = [attrs for tag, attrs in Tags(footer).tags if tag == 'a']
                    self.assertEqual(len(links), 2)
                    self.assertEqual(links[1].get("class"), "footer-stats")
                    self.assertNotIn("target", links[1])
                    self.assertEqual(links[0].get('href'), 'https://mikelcalvo.net/')
                    self.assertEqual(links[0].get('target'), '_blank')
                    self.assertEqual(set(links[0].get('rel', '').split()), {'noopener', 'noreferrer'})
                    self.assertRegex(footer, r'>Mikel Calvo</a>')

    def test_model_manuals_software_and_firmware_warning_are_preserved(self):
        for lang in ('en', 'es'):
            text = (self.site / lang / 'models/700c.html').read_text()
            self.assertIn('id="manuals"', text)
            self.assertIn('href="https://example.org/manual.pdf"', text)
            self.assertIn('id="drivers"', text)
            self.assertIn('Audio Features', text)
            self.assertIn('class="firmware-warning"', text)
            self.assertIn('System Program', text)


if __name__ == '__main__':
    unittest.main()
