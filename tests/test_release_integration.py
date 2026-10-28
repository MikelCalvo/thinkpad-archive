"""Public-builder integration for the accepted sourced model dossiers."""
from pathlib import Path
import copy
import json
import os
import tempfile
import unittest

import test_build as fixtures
from thinkpad_archive import build_site
from thinkpad_archive.model_design import ModelDesignRenderer
from thinkpad_archive.validation import load_catalogue, load_locales

ROOT = Path(__file__).resolve().parents[1]


def profiles_for(records):
    rows: list[dict] = [dict(model_id=m['id'], summary=None, context=None, facts=[], dates=[],
                 prices=[], markets=[], references=[]) for m in records['models']['models']]
    rows[0].update(
        summary={'en': 'A source-backed synthetic notebook.', 'es': 'Un portátil sintético con fuentes.'},
        facts=[dict(key='processor', value={'en': 'Synthetic processor', 'es': 'Procesador sintético'},
                    scope={'en': 'Exact test configuration.', 'es': 'Configuración exacta de prueba.'}, sources=['reference'])],
        references=[dict(id='reference', url='https://example.org/reference', title='Synthetic reference',
                         kind='official', locator='Test specification')])
    return {'schema_version': 1, 'profiles': rows}


class ReleaseIntegration(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=os.environ.get('TMPDIR'))
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.data = self.root / 'data'
        self.records = fixtures.fixture_data()
        fixtures.write_fixture(self.data, self.records)
        self.profile_path = self.data / 'profiles.json'
        self.profiles = profiles_for(self.records)
        self.profile_path.write_text(json.dumps(self.profiles))

    def test_public_builder_renders_validated_profiles_and_accepted_design(self):
        output = build_site(self.root / 'site', data_dir=self.data, default_language='es')
        self.assertIn('<html lang="es" data-language-entry="true">', (output / 'index.html').read_text())
        for lang, summary in [('en', 'A source-backed synthetic notebook.'), ('es', 'Un portátil sintético con fuentes.')]:
            text = (output / lang / 'models/700c.html').read_text()
            self.assertIn(summary, text)
            self.assertIn('class="model-design-page"', text)
            self.assertIn('data-fact-key="processor"', text)
            self.assertIn('class="spec-group"', text)
            self.assertIn('data-package-id="audio"', text)
            self.assertIn('class="firmware-warning"', text)
            self.assertNotIn('preview-status', text)
            self.assertNotIn('design-footer-note', text)
        css = (output / 'assets/style.css').read_bytes()
        detail_css = (ROOT / 'assets/model-design.css').read_bytes()
        self.assertTrue(css.endswith(detail_css))
        self.assertEqual(css.count(detail_css), 1)
        self.assertFalse((output / 'data').exists())

    def test_invalid_profile_sidecar_is_refused_before_creating_output(self):
        for field, value in [('profiles', []), ('schema_version', 999)]:
            with self.subTest(field=field):
                payload = copy.deepcopy(self.profiles)
                payload[field] = value
                self.profile_path.write_text(json.dumps(payload))
                output = self.root / ('rejected-' + field)
                with self.assertRaises(ValueError):
                    build_site(output, data_dir=self.data)
                self.assertFalse(output.exists())

    def test_legacy_catalogue_without_sidecar_remains_supported(self):
        self.profile_path.unlink()
        output = build_site(self.root / 'legacy', data_dir=self.data)
        self.assertIn('ThinkPad 700C', (output / 'en/models/700c.html').read_text())
        self.assertIn('https://example.org/manual.pdf', (output / 'en/models/700c.html').read_text())

    def test_release_styles_preserve_the_accepted_mobile_layout(self):
        import re
        css = (ROOT / 'assets/model-design.css').read_text()
        mobile = re.search(r'@media\(max-width:720px\)\{(.*)\}\n', css)
        self.assertIsNotNone(mobile, 'Accepted mobile breakpoint must not be removed with preview selectors')
        assert mobile is not None
        for rule in ('.spec-groups{grid-template-columns:1fr}',
                     '.manual-cards{grid-template-columns:1fr}',
                     '.package-row{grid-template-columns:1fr;',
                     '.package-actions{justify-content:flex-start;max-width:none}',
                     '.key-specs>div,.spec-group[open]>.key-specs>div{grid-template-columns:1fr;'):
            self.assertIn(rule, mobile.group(1))

    def test_print_keeps_breadcrumb_hidden_and_specifications_visible(self):
        css = (ROOT / 'assets/model-design.css').read_text()
        print_rules = css.split('@media print{', 1)[1]
        self.assertIn('.model-design-page .design-location{display:none}', print_rules)
        self.assertIn('.spec-groups{display:block}', print_rules)

    def test_detail_renderer_has_no_preview_badges_or_preview_footer(self):
        data = load_catalogue(ROOT / 'data')
        renderer = ModelDesignRenderer(data, load_locales(ROOT / 'locales'))
        model = next(m for m in data['models'] if m['id'] == 't30')
        for lang in ('en', 'es'):
            text = renderer.model(lang + '/models/t30.html', lang, model)
            self.assertNotIn('preview-status', text)
            self.assertNotIn('design-footer-note', text)
            self.assertNotIn('0.4.0 ·', text)
            self.assertNotIn('after the design is approved', text)
            self.assertNotIn('tras aprobar el diseño', text)


if __name__ == '__main__':
    unittest.main()
