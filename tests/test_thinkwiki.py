"""Explicit ThinkWiki references, never inferred category URLs."""
from pathlib import Path
import json
import os
import tempfile
import unittest
from html.parser import HTMLParser
from urllib.parse import parse_qs, urlsplit
import test_build as fixtures
from thinkpad_archive import build_site

ROOT = Path(__file__).resolve().parents[1]


class Links(HTMLParser):
    def __init__(self, text):
        super().__init__(convert_charrefs=True)
        self.links = []
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'a' and 'href' in attrs:
            self.links.append(attrs['href'])


class ThinkWikiReferences(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=os.environ.get('TMPDIR'))
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)

    def build(self, records, name='site'):
        source = self.base / (name + '-data')
        fixtures.write_fixture(source, records)
        return build_site(self.base / name, data_dir=source)

    def test_explicit_category_links_render_in_both_languages(self):
        data = fixtures.fixture_data()
        data['models']['models'][0]['thinkwiki'] = [{'title': '700C', 'url': 'https://www.thinkwiki.org/wiki/Category:700C'}]
        data['models']['models'][1]['thinkwiki'] = [{'title': 'X230 Tablet', 'url': 'https://www.thinkwiki.org/wiki/Category:X230_Tablet'}]
        output = self.build(data)
        for lang in ('en', 'es'):
            for model, url in [('700c','https://www.thinkwiki.org/wiki/Category:700C'),('x230-tablet','https://www.thinkwiki.org/wiki/Category:X230_Tablet')]:
                text = (output / lang / 'models' / (model + '.html')).read_text()
                self.assertIn(url, Links(text).links)
                self.assertIn('class="model-references"', text)
                self.assertLess(text.index('class="model-references"'), text.index('<section id="manuals"'))
                self.assertNotIn('https://www.thinkwiki.org/wiki/Category:X230"', text)

    def test_legacy_record_uses_search_without_guessing_category(self):
        output = self.build(fixtures.fixture_data())
        for lang in ('en', 'es'):
            text = (output / lang / 'models/700cs.html').read_text()
            links = [u for u in Links(text).links if urlsplit(u).hostname == 'www.thinkwiki.org']
            self.assertEqual(len(links), 1)
            self.assertEqual(urlsplit(links[0]).path, '/w/index.php')
            self.assertEqual(parse_qs(urlsplit(links[0]).query), {'search':['700CS']})
            self.assertIn('Search ThinkWiki' if lang == 'en' else 'Buscar en ThinkWiki', text)
            self.assertIn('No model-specific page verified.' if lang == 'en' else 'Sin entrada específica verificada.', text)

    def test_grouped_reference_links_are_explicit_not_name_split(self):
        data = fixtures.fixture_data()
        model = data['models']['models'][0]
        model['name'] = 'ThinkPad 700C, 700CS'
        model['thinkwiki'] = [{'title':'700C', 'url':'https://www.thinkwiki.org/wiki/Category:700C'}, {'title':'700CS', 'url':'https://www.thinkwiki.org/wiki/Category:700CS'}]
        output = self.build(data)
        text = (output / 'en/models/700c.html').read_text()
        self.assertEqual([u for u in Links(text).links if 'thinkwiki.org' in u], [r['url'] for r in model['thinkwiki']])

    def test_audit_accepts_explicit_reference_metadata(self):
        import tools.catalogue_audit as audit
        data = fixtures.fixture_data()
        # Keep the audit's existing README/source identity invariant valid.
        tablet = data['drivers']['drivers'][2]
        tablet['source_url'] = tablet['links'][0]['url']
        unassociated = data['drivers']['drivers'][3]
        unassociated['links'] = [{'kind':'reference', 'url':unassociated['source_url']}]
        data['models']['models'][0]['thinkwiki'] = [{'title':'700C','url':'https://www.thinkwiki.org/wiki/Category:700C'}]
        source = self.base / 'audit'
        fixtures.write_fixture(source / 'data', data)
        result = audit.audit_catalogue(source)
        self.assertEqual(result['models'], 3)

    def test_invalid_reference_data_refused_before_output(self):
        bad = [None, {}, ['https://www.thinkwiki.org/wiki/Category:X230'],
               [{'title':'X230','url':'javascript:alert(1)'}],
               [{'title':'X230','url':'https://example.org/wiki/Category:X230'}],
               [{'title':'X230','url':'https://www.thinkwiki.org/wiki/Category:X230?x=1'}],
               [{'title':'X230','url':'https://www.thinkwiki.org/wiki/Category:X230','body':'copied source'}],
               [{'title':'','url':'https://www.thinkwiki.org/wiki/Category:X230'}],
               [{'title':'X230','url':'https://www.thinkwiki.org/wiki/Category:X230'}]*2]
        for index, value in enumerate(bad):
            with self.subTest(case=index):
                data = fixtures.fixture_data()
                data['models']['models'][0]['thinkwiki'] = value
                with self.assertRaises(ValueError):
                    self.build(data, 'bad-' + str(index))
                self.assertFalse((self.base / ('bad-' + str(index))).exists())

    def test_live_catalogue_has_explicit_coverage_and_exact_variants(self):
        models = json.loads((ROOT/'data/models.json').read_text())['models']
        self.assertEqual(len(models), 250)
        self.assertTrue(all('thinkwiki' in m for m in models))
        by_id = {m['id']:m for m in models}
        self.assertEqual(by_id['x230']['thinkwiki'], [{'title':'X230','url':'https://www.thinkwiki.org/wiki/Category:X230'}])
        self.assertEqual(by_id['x230-tablet']['thinkwiki'][0]['url'], 'https://www.thinkwiki.org/wiki/Category:X230_Tablet')
        self.assertEqual(by_id['a21e-2628']['thinkwiki'], by_id['a21e-2632']['thinkwiki'])
        self.assertEqual(len(by_id['365c']['thinkwiki']), 6)
        self.assertEqual(sum(bool(m['thinkwiki']) for m in models), 243)
        self.assertEqual(sum(len(m['thinkwiki']) for m in models), 279)
        self.assertEqual({m['id'] for m in models if not m['thinkwiki']}, {'edge-e31','p1-gen-7','reserve-edition','s51','t14-gen-5-amd','x1-carbon-gen-12','x200si'})


if __name__ == '__main__':
    unittest.main()
