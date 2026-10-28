"""Sources page: concise first view, native disclosure, complete provenance."""
from html.parser import HTMLParser
from pathlib import Path
import copy
import json
import os
import tempfile
import unittest

import test_build as fixtures
from thinkpad_archive import build_site
from thinkpad_archive.render import Renderer
from thinkpad_archive.validation import load_locales

ROOT = Path(__file__).resolve().parents[1]


class Tree(HTMLParser):
    def __init__(self, text):
        super().__init__(convert_charrefs=True)
        self.root = {'tag': 'root', 'attrs': {}, 'children': []}
        self.stack = [self.root]
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        node = {'tag': tag, 'attrs': dict(attrs), 'children': []}
        self.stack[-1]['children'].append(node)
        if tag not in ('meta', 'link', 'input', 'img', 'br', 'hr', 'path', 'circle'):
            self.stack.append(node)

    def handle_endtag(self, tag):
        for i in range(len(self.stack) - 1, 0, -1):
            if self.stack[i]['tag'] == tag:
                del self.stack[i:]
                return

    def handle_data(self, data):
        self.stack[-1]['children'].append(data)


def nodes(node, tag=None, class_name=None):
    result = []
    if isinstance(node, dict):
        if (tag is None or node['tag'] == tag) and (class_name is None or class_name in node['attrs'].get('class', '').split()):
            result.append(node)
        for child in node['children']:
            result.extend(nodes(child, tag, class_name))
    return result


def text(node):
    return node if isinstance(node, str) else ''.join(text(c) for c in node['children'])


class SourcesRefresh(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=os.environ.get('TMPDIR'))
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.records = fixtures.fixture_data()
        groups = [('lenovo-eol-manuals', 'official'), ('lenovo-eol-selector', 'official'),
                  ('lenovo-psref', 'official'), ('psref-twbook', 'official'),
                  ('thinkwiki-history', 'community'), ('other-community', 'community')]
        self.records['models']['sources'].extend(
            {'id': key, 'title': '<' + key + '> & original title', 'url': 'https://example.org/' + key + '?a=1&b=2', 'kind': kind}
            for key, kind in groups)
        fixtures.write_fixture(self.base / 'data', self.records)
        self.site = build_site(self.base / 'site', data_dir=self.base / 'data')

    def page(self, lang):
        return Tree((self.site / lang / 'sources.html').read_text()).root

    def test_short_localized_page_and_navigation_labels(self):
        for lang, label in [('en', 'Sources'), ('es', 'Fuentes')]:
            with self.subTest(lang=lang):
                root = self.page(lang)
                self.assertEqual(text(nodes(root, 'h1')[0]), label)
                self.assertEqual(text(nodes(root, 'nav', 'main-nav')[0]).strip(), ('Catalogue' if lang == 'en' else 'Catálogo') + label)
                self.assertNotIn('ThinkPad Archive', text(nodes(root, 'main')[0]))

    def test_three_curated_source_families_use_actual_recorded_links(self):
        expected = {s['url'] for s in self.records['models']['sources'] if s['id'] in {
            'lenovo-eol-manuals', 'lenovo-eol-selector', 'lenovo-psref', 'psref-twbook', 'thinkwiki-history'}}
        for lang in ('en', 'es'):
            with self.subTest(lang=lang):
                cards = nodes(self.page(lang), 'article', 'source-family')
                self.assertEqual(len(cards), 3)
                self.assertEqual({a['attrs']['href'] for card in cards for a in nodes(card, 'a')}, expected)
                self.assertTrue(all(len(nodes(c, 'h3')) == 1 for c in cards))
                self.assertTrue(all(len(text(nodes(c, 'p')[0]).split()) < 24 for c in cards))

    def test_two_details_are_closed_and_references_preserve_all_records(self):
        for lang in ('en', 'es'):
            with self.subTest(lang=lang):
                root = self.page(lang)
                details = nodes(nodes(root, 'main')[0], 'details')
                self.assertEqual({d['attrs'].get('id') for d in details}, {'source-references', 'source-methodology'})
                self.assertTrue(all('open' not in d['attrs'] for d in details))
                references = next(d for d in details if d['attrs']['id'] == 'source-references')
                links = nodes(references, 'a')
                self.assertEqual(len(links), len(self.records['models']['sources']))
                self.assertEqual({a['attrs']['href']: text(a) for a in links}, {s['url']: s['title'] for s in self.records['models']['sources']})
                self.assertEqual(len(nodes(references, 'h3')), 2)
                method = next(d for d in details if d['attrs']['id'] == 'source-methodology')
                self.assertIn(self.records['models']['scope'][lang], text(method))
                self.assertTrue(all(a['attrs'].get('target') == '_blank' and a['attrs'].get('rel') == 'noopener noreferrer' for a in links))

    def test_evidence_rows_and_visible_firmware_caution(self):
        for lang in ('en', 'es'):
            with self.subTest(lang=lang):
                root = self.page(lang)
                evidence = nodes(root, 'dl', 'source-evidence')
                self.assertEqual(len(evidence), 1)
                self.assertEqual(len(nodes(evidence[0], 'dt')), 3)
                self.assertEqual(len(nodes(evidence[0], 'dd')), 3)
                caution = nodes(root, 'aside', 'source-install')
                self.assertEqual(len(caution), 1)
                self.assertIn('firmware', text(caution[0]).lower())
                self.assertLess(len(text(caution[0]).split()), 85)

    def test_unrecognized_sources_stay_visible_in_references_without_fake_curated_links(self):
        data = copy.deepcopy(self.records['models'])
        data.update(documents=[], drivers=[])
        data['sources'] = [data['sources'][0]]
        output = Renderer(data, load_locales(ROOT / 'locales')).source_page('en/sources.html', 'en')
        root = Tree(output).root
        self.assertEqual(nodes(root, 'article', 'source-family'), [])
        references = next(d for d in nodes(root, 'details') if d['attrs'].get('id') == 'source-references')
        self.assertEqual([a['attrs']['href'] for a in nodes(references, 'a')], [data['sources'][0]['url']])
        self.assertNotIn('download.lenovo.com', output)


if __name__ == '__main__':
    unittest.main()
