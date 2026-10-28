"""Design-preview contract; the public catalogue and renderer stay untouched."""
from pathlib import Path
from html.parser import HTMLParser
import copy
import json
import unittest

from thinkpad_archive.validation import load_catalogue, load_locales

ROOT = Path(__file__).resolve().parents[1]


class Tags(HTMLParser):
    def __init__(self, text):
        super().__init__()
        self.tags = []
        self.feed(text)
    def handle_starttag(self, tag, attrs):
        self.tags.append((tag, dict(attrs)))


class ModelDesign(unittest.TestCase):
    def renderer(self):
        from thinkpad_archive.model_design import ModelDesignRenderer
        return ModelDesignRenderer(load_catalogue(ROOT/'data'), load_locales(ROOT/'locales'))

    def test_preview_renderer_is_available(self):
        self.assertTrue((ROOT/'thinkpad_archive/model_design.py').is_file(), 'Isolated model design renderer is not implemented')

    def test_context_precedes_manuals_and_software_without_repeated_metadata_copy(self):
        renderer = self.renderer()
        model = next(m for m in renderer.data['models'] if m['id'] == 't30')
        for lang, manuals, drivers in [('en', 'Manuals', 'Drivers &amp; Software'), ('es', 'Manuales', 'Drivers y software')]:
            with self.subTest(lang=lang):
                text = renderer.model(lang+'/models/t30.html', lang, model)
                self.assertLess(text.index('<h1'), text.index('id="overview"'))
                self.assertLess(text.index('id="overview"'), text.index('id="manuals"'))
                self.assertLess(text.index('id="manuals"'), text.index('id="drivers"'))
                self.assertIn('>'+manuals+'<', text)
                self.assertIn('>'+drivers+'<', text)
                for key in ['source_listing', 'document_note', 'driver_note', 'metadata_only', 'availability_note']:
                    self.assertNotIn(renderer.locales[lang][key], text)
                self.assertIn(renderer.locales[lang]['firmware_warning_text'], text)
                self.assertIn('23 April 2002' if lang == 'en' else '23 de abril de 2002', text)
                self.assertIn('2366' if lang == 'en' else '2366', text)

    def test_compact_cards_preserve_every_manual_package_link_and_source(self):
        renderer = self.renderer()
        model = next(m for m in renderer.data['models'] if m['id'] == 't30')
        text = renderer.model('es/models/t30.html', 'es', model)
        tags = Tags(text).tags
        hrefs = {a['href'] for t,a in tags if t == 'a' and 'href' in a}
        expected = {renderer.docs[i]['url'] for i in model['document_ids']}
        for key in model['driver_ids']:
            driver = renderer.drivers[key]
            expected.add(driver['source_url'])
            expected.update(link['url'] for link in driver['links'])
        self.assertLessEqual(expected, hrefs)
        packages = [a['data-package-id'] for _,a in tags if 'data-package-id' in a]
        self.assertEqual(set(packages), set(model['driver_ids']))
        self.assertEqual(len(packages), len(model['driver_ids']))
        for _,a in tags:
            if a.get('href','').startswith('https://'):
                self.assertEqual(a.get('target'), '_blank')
                self.assertIn('noopener', a.get('rel',''))
        self.assertIn('reference-details', text)
        self.assertNotIn('data-package-id', text.split('id="manuals"')[0])

    def test_missing_history_and_scoped_dates_are_honest_not_invented(self):
        renderer = self.renderer()
        models = {m['id']:m for m in renderer.data['models']}
        unknown = renderer.model('es/models/a22m-2629.html','es',models['a22m-2629'])
        self.assertIn('Sin fecha confirmada',unknown)
        self.assertNotIn('pending-fact',unknown)
        self.assertNotIn('data-header-fact="date"',unknown.split('id="manuals"')[0])
        self.assertNotIn('2001',unknown.split('id="manuals"')[0])
        scoped = renderer.model('es/models/x200si.html','es',models['x200si'])
        self.assertIn('Disponibilidad regional',scoped)
        self.assertIn(models['x200si']['introduced'][0]['evidence']['note']['es'],scoped)
        self.assertNotIn('Exclusivo de Países Bajos',scoped)
        grouped = renderer.model('es/models/r52-1846.html','es',models['r52-1846'])
        self.assertIn('Catálogo comercial', grouped)
        self.assertIn('marzo de 2005', grouped)
        early = renderer.model('es/models/700c.html','es',models['700c'])
        self.assertIn('4.350',early)
        self.assertIn('catálogo',early)
        self.assertIn('1994',early)

    def test_model_heading_reuses_landing_red_dot_and_normal_i(self):
        import re
        renderer = self.renderer()
        for lang in ('en', 'es'):
            for model in renderer.data['models']:
                with self.subTest(lang=lang, model=model['id']):
                    page = renderer.model(lang+'/models/'+model['id']+'.html', lang, model)
                    heading = page.split('<h1>', 1)[1].split('</h1>', 1)[0]
                    self.assertEqual(re.sub('<[^>]+>', '', heading), model['name'])
                    if model['name'].startswith('ThinkPad '):
                        self.assertIn('<span class="brand-word">Th<span class="title-i">i</span>nkPad</span>', heading)
                        self.assertEqual(heading.count('class="title-i"'), 1)
                    else:
                        self.assertNotIn('class="title-i"', heading)
                    self.assertNotIn('ı', heading)

    def test_header_goes_directly_to_facts_without_tagline_or_top_rule(self):
        renderer = self.renderer()
        models = {m['id']: m for m in renderer.data['models']}
        for lang in ('en', 'es'):
            for model_id in ('t30', '700c', 'x200si'):
                with self.subTest(lang=lang, model=model_id):
                    text = renderer.model(lang+'/models/'+model_id+'.html', lang, models[model_id])
                    header = text.split('<header class="dossier-hero">')[1].split('</header>')[0]
                    self.assertNotIn('model-deck', header)
                    self.assertTrue(header.endswith('</h1>'))
        css = (ROOT/'assets/model-design.css').read_text()
        facts_rule = css.split('.model-meta{', 1)[1].split('}', 1)[0]
        self.assertNotIn('border-top:', facts_rule)

    def test_date_references_follow_firmware_in_final_sources(self):
        renderer = self.renderer()
        models = {m['id']: m for m in renderer.data['models']}
        for lang in ('en', 'es'):
            for model_id in ('t30', '700c', 'r52-1846', 'x200si'):
                with self.subTest(lang=lang, model=model_id):
                    text = renderer.model(lang+'/models/'+model_id+'.html', lang, models[model_id])
                    self.assertNotIn('launch-details', text.split('id="sources"')[0])
                    sources = text.split('id="sources"')[1].split('</section>')[0]
                    self.assertIn(renderer.dates(lang, models[model_id]), sources)
                    self.assertEqual(text.count('class="launch-details"'), 1)
                    self.assertLess(text.index('id="firmware"'), text.index('class="launch-details"'))

    def test_sections_have_one_category_list_and_no_redundant_navigation(self):
        renderer = self.renderer()
        model = next(m for m in renderer.data['models'] if m['id'] == 't30')
        for lang in ('en', 'es'):
            with self.subTest(lang=lang):
                text = renderer.model(lang+'/models/t30.html', lang, model)
                tags = Tags(text).tags
                self.assertNotIn('model-jumps', text)
                self.assertNotIn('category-nav', text)
                self.assertFalse(any('data-category-target' in attrs for _, attrs in tags))
                for prefix in ('drivers', 'firmware'):
                    self.assertIn('class="driver-category" id="'+prefix+'-cat-', text)
                packages = [a['data-package-id'] for _, a in tags if 'data-package-id' in a]
                self.assertEqual(set(packages), set(model['driver_ids']))
                self.assertEqual(len(packages), len(model['driver_ids']))

    def test_untrusted_model_titles_and_notes_are_escaped(self):
        renderer = self.renderer()
        model = copy.deepcopy(next(m for m in renderer.data['models'] if m['id'] == 'x200si'))
        model['name'] = '<img src=x onerror=alert(1)>'
        model['introduced'][0]['evidence']['note']['es'] = '<script>bad()</script>'
        text = renderer.model('es/models/x200si.html','es',model)
        self.assertIn('&lt;img',text)
        self.assertIn('&lt;script&gt;',text)
        self.assertNotIn('<img src=x',text)
        self.assertNotIn('<script>bad()',text)


if __name__ == '__main__':
    unittest.main()
