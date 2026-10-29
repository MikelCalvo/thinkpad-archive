"""Crawler-readable sharing metadata; no network or hardware certification."""
from html.parser import HTMLParser
from pathlib import Path
import json
import os
import struct
import tempfile
import unittest

import test_build as fixtures
from thinkpad_archive import build_site
from thinkpad_archive.render import Renderer
from thinkpad_archive.validation import load_catalogue, load_locales

ROOT = Path(__file__).resolve().parents[1]
ORIGIN = 'https://thinkpadarchive.com'


class Head(HTMLParser):
    def __init__(self, text):
        super().__init__(convert_charrefs=True)
        self.metadata, self.links, self.in_head = {}, [], False
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'head':
            self.in_head = True
        if self.in_head and tag == 'meta' and ('name' in attrs or 'property' in attrs):
            key = attrs.get('property', attrs.get('name'))
            if key in self.metadata:
                raise AssertionError('Repeated metadata: ' + str(key))
            self.metadata[key] = attrs.get('content', '')
        if self.in_head and tag == 'link':
            self.links.append(attrs)

    def handle_endtag(self, tag):
        if tag == 'head':
            self.in_head = False


class SocialMetadata(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(dir=os.environ.get('TMPDIR'))
        cls.addClassCleanup(cls.temp.cleanup)
        base = Path(cls.temp.name)
        records = fixtures.fixture_data()
        records['models']['models'][0]['introduced'] = [
            {'year': 1992, 'variants': ['700C'], 'url': 'https://example.org/history'}]
        records['models']['models'][0]['name'] = 'ThinkPad 700C & "Special" <test>'
        fixtures.write_fixture(base / 'data', records)
        cls.site = build_site(base / 'site', data_dir=base / 'data')
        cls.locales = load_locales(ROOT / 'locales')
        cls.renderer = Renderer(load_catalogue(base / 'data'), cls.locales)

    def head(self, relative):
        return Head((self.site / relative).read_text())

    def test_each_page_has_static_large_card_title_description_and_image(self):
        for page in self.site.rglob('*.html'):
            with self.subTest(page=str(page.relative_to(self.site))):
                head = Head(page.read_text())
                tags = head.metadata
                self.assertEqual(tags.get('twitter:card'), 'summary_large_image')
                self.assertEqual(tags.get('og:type'), 'website')
                self.assertEqual(tags.get('og:site_name'), 'ThinkPad Archive')
                for key in ('og:title', 'og:description', 'og:url', 'og:image', 'og:image:alt', 'og:locale'):
                    self.assertTrue(tags.get(key), key)
                self.assertEqual(tags.get('twitter:title'), tags['og:title'])
                self.assertEqual(tags.get('twitter:description'), tags['og:description'])
                self.assertEqual(tags.get('description'), tags['og:description'])
                self.assertEqual(tags.get('twitter:image'), tags['og:image'])
                self.assertEqual(tags.get('twitter:image:alt'), tags['og:image:alt'])
                self.assertEqual(tags.get('og:image:width'), '1200')
                self.assertEqual(tags.get('og:image:height'), '630')
                self.assertEqual(tags.get('og:image:type'), 'image/png')
                self.assertTrue(tags['og:image'].startswith(ORIGIN + '/assets/social-'))
                self.assertFalse(any(text in tags['og:url'] for text in ('127.0.0.1', 'localhost', '?', '#')))
                canonical = [a['href'] for a in head.links if a.get('rel') == 'canonical']
                self.assertEqual(canonical, [tags['og:url']])

    def test_page_specific_titles_and_descriptions_are_localized_and_escaped(self):
        for lang in ('en', 'es'):
            model = self.head(lang + '/models/700c.html').metadata
            self.assertIn('ThinkPad 700C & "Special" <test>', model.get('og:title', ''))
            self.assertIn('ThinkPad 700C & "Special" <test>', model.get('og:description', ''))
            self.assertIn('manuals' if lang == 'en' else 'manuales', model['og:description'].lower())
            self.assertNotIn('<test>', (self.site / lang / 'models/700c.html').read_text())
            home = self.head(lang + '/index.html').metadata
            sources = self.head(lang + '/sources.html').metadata
            year = self.head(lang + '/years/1992.html').metadata
            self.assertEqual(home.get('og:title'), 'ThinkPad Archive · ' + ('Manuals, drivers and history' if lang == 'en' else 'Manuales, drivers e historia'))
            self.assertIn('1992', year.get('og:title', ''))
            self.assertIn('1992', year.get('og:description', ''))
            self.assertIn('Sources' if lang == 'en' else 'Fuentes', sources.get('og:title', ''))
            self.assertEqual(len({home['og:description'], sources['og:description'], year['og:description'], model['og:description']}), 4)
            self.assertEqual(home['og:locale'], 'en_US' if lang == 'en' else 'es_ES')
            self.assertIn('/assets/social-' + lang + '.png', home['og:image'])
        self.assertNotEqual(self.head('es/index.html').metadata['og:description'], self.head('en/index.html').metadata['og:description'])

    def test_home_legacy_and_neutral_entries_have_one_canonical_per_language(self):
        for lang in ('en', 'es'):
            for suffix in ('index.html', 'catalogue.html'):
                self.assertEqual(self.head(lang + '/' + suffix).metadata.get('og:url'), ORIGIN + '/' + lang + '/')
        self.assertEqual(self.head('index.html').metadata.get('og:url'), ORIGIN + '/en/')
        for relative in ('en/sources.html', 'es/models/700c.html', 'es/years/1992.html'):
            self.assertEqual(self.head(relative).metadata.get('og:url'), ORIGIN + '/' + relative)

    def test_png_cards_are_copied_unchanged_and_have_social_dimensions(self):
        for lang in ('en', 'es'):
            relative = 'assets/social-' + lang + '.png'
            path = self.site / relative
            self.assertTrue(path.is_file(), relative)
            data = path.read_bytes()
            self.assertEqual(data, (ROOT / relative).read_bytes())
            self.assertEqual(data[:8], b'\x89PNG\r\n\x1a\n')
            self.assertEqual(struct.unpack('>II', data[16:24]), (1200, 630))
            self.assertLess(len(data), 1024 * 1024)

    def test_enriched_renderer_uses_the_same_sharing_head(self):
        from thinkpad_archive.model_design import ModelDesignRenderer
        renderer = ModelDesignRenderer(self.renderer.data, self.locales)
        model = renderer.data['models'][0]
        page = renderer.model('es/models/700c.html', 'es', model)
        metadata = Head(page).metadata
        self.assertIn(model['name'], metadata.get('og:title', ''))
        self.assertEqual(metadata.get('og:url'), ORIGIN + '/es/models/700c.html')

    def test_docker_context_admits_only_the_two_named_social_pngs(self):
        from fnmatch import fnmatchcase
        lines = (ROOT / '.dockerignore').read_text().splitlines()
        for path, allowed in [('assets/social-en.png', True), ('assets/social-es.png', True), ('assets/private.png', False)]:
            matches = [line for line in lines if fnmatchcase(path, line.lstrip('!'))]
            self.assertTrue(matches)
            self.assertEqual(matches[-1].startswith('!'), allowed, path)
