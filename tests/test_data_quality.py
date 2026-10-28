"""Source-backed data corrections; no manufacturer source bodies are bundled."""
from pathlib import Path
import json
import unittest
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]


def models_by_id():
    return {m['id']: m for m in json.loads((ROOT / 'data/models.json').read_text())['models']}


class DataQuality(unittest.TestCase):
    def test_backfilled_types_keep_unsupported_members_explicitly_unknown(self):
        models = models_by_id()
        for identity in ('r52-1846', 'r52-1858'):
            with self.subTest(identity=identity):
                self.assertTrue(models[identity]['introduced'])
                self.assertTrue(models[identity]['introduced_unknown'])
                self.assertTrue(all(i['year'] == 2005 for i in models[identity]['introduced']))
                self.assertTrue(all('Type ' in v for i in models[identity]['introduced'] for v in i['variants']))
        self.assertEqual(models['r52-1846']['introduced_unknown'], ['ThinkPad R52 (Type 1850)', 'ThinkPad R52 (Type 1870)'])
        self.assertEqual(models['r52-1858']['introduced_unknown'], ['ThinkPad R52 (Type 1862)', 'ThinkPad R52 (Type 1863)'])
        self.assertEqual(models['a21e-2632']['name'], 'ThinkPad i Series 1800 (Type 2632)')
        self.assertEqual(models['a21e-2632']['introduced'][0]['year'], 2000)
        self.assertEqual(models['a22m-2629']['name'], 'ThinkPad A22m (Type 2633)')
        self.assertEqual(models['a22m-2629']['introduced'], [])
        self.assertEqual(models['a22m-2629']['introduced_unknown'], ['ThinkPad A22m (Type 2633)'])
        self.assertEqual(models['1500-2621']['introduced_unknown'], ['ThinkPad 1400 (Type 2651)'])
        self.assertEqual({i['year'] for i in models['1500-2621']['introduced']}, {1999, 2000})
        self.assertEqual(models['750']['introduced_unknown'], ['ThinkPad 750CSE'])
        self.assertNotIn('750CSE', models['750']['name'])
        self.assertNotIn('ThinkPad 750CSE', models['750']['aliases'])

    def test_regional_dates_and_non_thinkpad_exclusion_are_not_guessed(self):
        models = models_by_id()
        self.assertNotIn('s51', models)  # Its official route is ThinkCentre.
        for identity in ('edge-e10', 'edge-e30', 'edge-e40', 'edge-e50'):
            with self.subTest(identity=identity):
                self.assertEqual([i['year'] for i in models[identity]['introduced']], [2010])
        for identity in ('edge-e31', 'x200si', 'x230i-tablet'):
            self.assertEqual(models[identity]['introduced'], [], identity)

    def test_source_grounded_expansion_keeps_variant_identity_and_references(self):
        models = models_by_id()
        # Dated identities absent from the 0.3.0 snapshot, not inferred drivers.
        required = {'t420': 2011, 't430': 2012, 't440p': 2013, 't480': 2018,
                    'x240': 2013, 'x280': 2018, 'p50': 2015, 'p70': 2015,
                    'tablet-2': 2012, '25-anniversary-edition': 2017,
                    't14-gen-1-amd': 2020, 't14-gen-1-intel': 2020, 'i-series-1124': 2000}
        for identity, year in required.items():
            with self.subTest(identity=identity):
                self.assertIn(identity, models)
                model = models[identity]
                self.assertEqual([i['year'] for i in model['introduced']], [year])
                self.assertFalse(model['driver_ids'])
                self.assertIsNone(model['matrix_url'])
                self.assertTrue(model['document_ids'] or model['thinkwiki'])
        self.assertNotEqual(models['t14-gen-1-amd']['document_ids'], models['t14-gen-1-intel']['document_ids'])
        self.assertNotIn('ThinkPad T14', models['t14-gen-1-amd']['aliases'])
        self.assertNotIn('ThinkPad T14', models['t14-gen-1-intel']['aliases'])

    def test_modern_generation_and_cpu_variants_are_explicit_and_source_linked(self):
        models = models_by_id()
        for identity in ('t14-gen-5-intel', 'p1-gen-8', 'x1-carbon-gen-14-aura-edition',
                         'x1-yoga-2nd-gen', 'e14-gen-8-amd', '11e-3rd-gen'):
            with self.subTest(identity=identity):
                self.assertIn(identity, models)
                model = models[identity]
                self.assertFalse(model['driver_ids'])
                self.assertIsNone(model['matrix_url'])
                self.assertTrue(model['document_ids'])
                self.assertEqual(model['introduced'][0]['variants'], [model['name']])
                self.assertTrue(model['introduced'][0]['url'].startswith('https://psref.lenovo.com/Product/ThinkPad/'))
        self.assertEqual(models['x1-carbon-gen-14-aura-edition']['introduced'][0]['year'], 2026)
        self.assertNotEqual(models['t14-gen-5-intel']['document_ids'], models['t14-gen-5-amd']['document_ids'])

    def test_official_product_binding_resolves_heading_variations_without_ambiguous_aliases(self):
        models = models_by_id()
        for identity, year in [('e545', 2013), ('helix-2nd-gen', 2014), ('x1-yoga-1st-gen', 2016)]:
            with self.subTest(identity=identity):
                self.assertIn(identity, models)
                self.assertEqual(models[identity]['introduced'][0]['year'], year)
                self.assertTrue(models[identity]['document_ids'])
                self.assertFalse(models[identity]['driver_ids'])
        self.assertIn('ThinkPad Edge E545', models['e545']['aliases'])
        self.assertIn('ThinkPad Helix (2nd Gen)', models['helix-2nd-gen']['aliases'])
        self.assertNotIn('ThinkPad X1 Yoga', models['x1-yoga-1st-gen']['aliases'])

    def test_reconciled_platform_years_link_to_exact_official_psref_pages(self):
        # Exact platform headers and explicit US-announcement rows corroborate
        # these existing years. This does not infer years for type groups.
        ids = '''a22e g40 g41 l412 l512 r40 r400 r40e r500 r50e r51 r51e
        r60 r60e r61 r61e r61i t22 t23 t30 t40 t400 t400s t40p t41 t410
        t410i t410s t410si t41p t42 t42p t43 t43p t500 t510 t510i t60
        t60p t61 t61p w500 w510 w700 w701 w701ds x100e x120e x200 x200t
        x200s x201 x201-tablet x201i x201s x21 x22 x220 x220-tablet x220i
        x220i-tablet x30 x300 x301 x31 x32 x40 x41 x41t x60 x60t x60s
        x61 x61t x61s z60m z60t z61e z61m z61p z61t'''.split()
        self.assertEqual(len(ids), 81)
        self.assertEqual(len(set(ids)), 81)
        models = models_by_id()
        for identity in ids:
            with self.subTest(identity=identity):
                model = models[identity]
                self.assertEqual(len(model['introduced']), 1)
                introduction = model['introduced'][0]
                self.assertEqual(introduction['variants'], [model['name']])
                url = urlsplit(introduction['url'])
                self.assertEqual(url.netloc, 'psrefstuff.lenovo.com')
                self.assertIn('/withdrawnbook/', url.path)
                self.assertRegex(url.fragment, r'^page=[1-9][0-9]*$')
                self.assertTrue(model['document_ids'])


if __name__ == '__main__':
    unittest.main()
