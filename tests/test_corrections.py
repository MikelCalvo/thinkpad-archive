"""Per-model, static GitHub correction drafts; opening is never submission."""
import copy
from html.parser import HTMLParser
from pathlib import Path
import tempfile
import unittest
from urllib.parse import parse_qs, urlsplit

from thinkpad_archive import build_site
from thinkpad_archive.model_design import ModelDesignRenderer
from thinkpad_archive.profiles import load_profiles
from thinkpad_archive.render import Renderer
from thinkpad_archive.validation import load_catalogue, load_locales

ROOT = Path(__file__).resolve().parents[1]
ISSUES = 'https://github.com/MikelCalvo/thinkpad-archive/issues/new'


class Links(HTMLParser):
    def __init__(self, text):
        super().__init__(convert_charrefs=True)
        self.links = []
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        if tag == 'a':
            self.links.append(dict(attrs))


class Corrections(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = load_catalogue(ROOT / 'data')
        cls.locales = load_locales(ROOT / 'locales')
        cls.models = {m['id']: m for m in cls.data['models']}
        cls.profiles = load_profiles(ROOT / 'data/profiles.json', set(cls.models))

    def renderer(self, enriched=True):
        if enriched:
            return ModelDesignRenderer(self.data, self.locales, profiles=self.profiles)
        return Renderer(self.data, self.locales)

    def correction(self, text):
        links = [a for a in Links(text).links
                 if 'model-correction' in a.get('class', '').split()]
        self.assertEqual(len(links), 1, 'Each model needs one native correction link')
        return links[0]

    def test_all_model_identities_and_languages_have_exact_public_drafts(self):
        renderer = self.renderer()
        for lang in ('en', 'es'):
            for model in self.data['models']:
                with self.subTest(lang=lang, model=model['id']):
                    path = lang + '/models/' + model['id'] + '.html'
                    text = renderer.model(path, lang, model)
                    a = self.correction(text)
                    parts = urlsplit(a['href'])
                    self.assertEqual(parts.scheme + '://' + parts.netloc + parts.path, ISSUES)
                    query = parse_qs(parts.query, strict_parsing=True)
                    self.assertEqual(set(query), {'title', 'body'})
                    self.assertEqual(query['title'], [('Corrección: ' if lang == 'es' else 'Correction: ') + model['name']])
                    body = query['body'][0]
                    self.assertIn(model['name'], body)
                    self.assertIn(model['id'], body)
                    self.assertIn('https://thinkpadarchive.com/' + path, body)
                    self.assertNotIn('localhost', body)
                    self.assertNotIn('127.0.0.1', body)
                    self.assertNotIn('/home/', body)
                    self.assertLess(len(a['href'].encode('utf-8')), 4000)
                    self.assertEqual(a.get('target'), '_blank')
                    self.assertEqual(set(a.get('rel', '').split()), {'noopener', 'noreferrer'})
                    self.assertNotIn('onclick', a)

    def test_draft_prompts_are_localized_and_request_exact_variant_evidence(self):
        for lang, expected in (
            ('en', ['What needs correcting?', 'Suggested correction', 'Sources', 'machine type', 'serial numbers']),
            ('es', ['¿Qué hay que corregir?', 'Corrección propuesta', 'Fuentes', 'tipo de máquina', 'números de serie']),
        ):
            text = self.renderer().model(lang + '/models/x230.html', lang, self.models['x230'])
            a = self.correction(text)
            body = parse_qs(urlsplit(a['href']).query)['body'][0]
            for prompt in expected:
                self.assertIn(prompt, body)
            self.assertIn('GitHub', a['title'])
            self.assertIn('cuenta' if lang == 'es' else 'account', a['title'])
            self.assertIn('GitHub', a['aria-label'])
            self.assertIn('Proponer una corrección' if lang == 'es' else 'Suggest a correction', text)
            self.assertLess(text.index('class="model-correction"'), text.index('id="manuals"'))

    def test_legacy_without_profiles_keeps_the_same_correction_action(self):
        renderer = self.renderer(enriched=False)
        for lang in ('en', 'es'):
            text = renderer.model(lang + '/models/a22m-2629.html', lang, self.models['a22m-2629'])
            a = self.correction(text)
            self.assertIn('a22m-2629', parse_qs(urlsplit(a['href']).query)['body'][0])
            self.assertIn('2633', parse_qs(urlsplit(a['href']).query)['title'][0])

    def test_reserved_unicode_and_html_model_names_cannot_inject_query_or_markup(self):
        renderer = self.renderer()
        model = copy.deepcopy(self.models['x230'])
        model['name'] = 'ThinkPad <img src=x onerror=bad()> & "A+B" / 日本 #?'
        text = renderer.model('es/models/x230.html', 'es', model)
        a = self.correction(text)
        query = parse_qs(urlsplit(a['href']).query, strict_parsing=True)
        self.assertEqual(set(query), {'title', 'body'})
        self.assertEqual(query['title'], ['Corrección: ' + model['name']])
        self.assertIn(model['name'], query['body'][0])
        self.assertNotIn('<img src=x', text)

    def test_public_builder_emits_actions_without_new_script_form_or_collection(self):
        with tempfile.TemporaryDirectory() as folder:
            output = build_site(Path(folder) / 'public')
            for lang in ('en', 'es'):
                text = (output / lang / 'models/x230.html').read_text()
                self.correction(text)
                self.assertNotIn('data-stats-enabled="true"', text)
                self.assertNotIn('corrections.js', text)
                self.assertNotIn('<form action=', text)
                for page in ('index.html', 'sources.html', 'stats.html'):
                    self.assertNotIn('class="model-correction"', (output / lang / page).read_text())
            css = (output / 'assets/style.css').read_text()
            self.assertIn('.model-correction{', css)
            self.assertIn('.model-correction:focus-visible', css)


if __name__ == '__main__':
    unittest.main()
