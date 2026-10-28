"""Qualified historical years must keep their evidence scope visible."""
from pathlib import Path
import copy
import json
import os
import tempfile
import unittest

import test_build as fixtures
from thinkpad_archive import build_site

ROOT = Path(__file__).resolve().parents[1]


def evidence(kind='commercial_listing'):
    return {'kind': kind, 'note': {'en': 'Exact type listed in a dated sales catalogue; first launch unconfirmed.',
                                  'es': 'Tipo exacto en un catálogo comercial fechado; primer lanzamiento sin confirmar.'}}


def qualified_data():
    data = fixtures.fixture_data()
    data['models']['models'][0]['introduced'] = [
        {'year': 1992, 'variants': ['Synthetic 700C'], 'url': 'https://example.org/catalogue',
         'evidence': evidence()}]
    return data


class DateEvidence(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir=os.environ.get('TMPDIR'))
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def test_dated_commercial_listing_is_not_rendered_as_confirmed_launch(self):
        fixtures.write_fixture(self.root / 'data', qualified_data())
        build_site(self.root / 'site', data_dir=self.root / 'data')
        for lang, label, kind, note in (
            ('en', 'Documented years', 'Commercial listing', evidence()['note']['en']),
            ('es', 'Años documentados', 'Catálogo comercial', evidence()['note']['es']),
        ):
            text = (self.root / 'site' / lang / 'models/700c.html').read_text()
            self.assertIn(label, text)
            self.assertIn(kind, text)
            self.assertIn(note, text)
            self.assertNotIn(('Introduced in' if lang == 'en' else 'Presentados en') + ':', text)
            year = (self.root / 'site' / lang / 'years/1992.html').read_text()
            self.assertIn('data-model-id="700c"', year)

    def test_regional_evidence_kinds_are_localized_and_escaped(self):
        for index, (kind, en, es) in enumerate((
            ('regional_availability', 'Regional availability', 'Disponibilidad regional'),
            ('regional_sku_launch', 'Regional SKU introduction', 'Presentación regional de una configuración'),
        )):
            data = qualified_data()
            row = data['models']['models'][0]['introduced'][0]
            row['evidence'] = evidence(kind)
            row['evidence']['note'] = {'en': '<Not global>', 'es': '<No mundial>'}
            source = self.root / ('data-' + str(index))
            output = self.root / ('site-' + str(index))
            fixtures.write_fixture(source, data)
            build_site(output, data_dir=source)
            for lang, label in [('en', en), ('es', es)]:
                text = (output / lang / 'models/700c.html').read_text()
                self.assertIn(label, text)
                self.assertIn('&lt;', text)
                self.assertNotIn(row['evidence']['note'][lang], text)

    def test_qualified_evidence_rejects_unknown_kinds_and_incomplete_notes(self):
        invalid = [None, {}, {'kind': 'copyright', 'note': evidence()['note']},
                   {'kind': 'commercial_listing', 'note': {'en': 'English only'}},
                   {'kind': 'commercial_listing', 'note': {'en': '', 'es': 'Texto'}},
                   dict(evidence(), extra='unrecognized')]
        for index, value in enumerate(invalid):
            with self.subTest(index=index):
                data = qualified_data()
                data['models']['models'][0]['introduced'][0]['evidence'] = copy.deepcopy(value)
                source = self.root / ('invalid-' + str(index))
                output = self.root / ('out-' + str(index))
                fixtures.write_fixture(source, data)
                with self.assertRaises(ValueError):
                    build_site(output, data_dir=source)
                self.assertFalse(output.exists())

    def test_offline_audit_accepts_qualified_rows_and_rejects_bad_scope(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location('qualified_audit', ROOT / 'tools/catalogue_audit.py')
        audit = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(audit)
        data = qualified_data()
        tablet = data['drivers']['drivers'][2]
        tablet['source_url'] = tablet['links'][0]['url']
        unassociated = data['drivers']['drivers'][3]
        unassociated['links'] = [{'kind': 'reference', 'url': unassociated['source_url']}]
        fixtures.write_fixture(self.root / 'audit' / 'data', data)
        self.assertEqual(audit.audit_catalogue(self.root / 'audit')['models'], 3)
        for value in [evidence('copyright'), {'kind': 'commercial_listing', 'note': {'en': 'Only English'}}]:
            data['models']['models'][0]['introduced'][0]['evidence'] = value
            fixtures.write_fixture(self.root / 'audit' / 'data', data)
            with self.assertRaises(ValueError):
                audit.audit_catalogue(self.root / 'audit')

    def test_backfilled_regional_records_have_explicit_date_scope(self):
        models = {m['id']: m for m in json.loads((ROOT / 'data/models.json').read_text())['models']}
        for identity, year, kind, exact in [
            ('edge-e31', 2011, 'regional_sku_launch', '025027C'),
            ('x200si', 2010, 'regional_availability', 'NS2FVMH'),
            ('x230i-tablet', 2012, 'regional_availability', '3438-AK8'),
        ]:
            with self.subTest(identity=identity):
                row = models[identity]['introduced'][0] if models[identity]['introduced'] else {}
                self.assertEqual(row.get('year'), year)
                self.assertEqual(row['evidence']['kind'], kind)
                self.assertIn(exact, row['evidence']['note']['en'])
                self.assertIn(exact, row['evidence']['note']['es'])
        self.assertEqual(models['a22m-2629']['introduced'], [])
        self.assertEqual(models['750']['introduced_unknown'], ['ThinkPad 750CSE'])
        self.assertEqual(models['1500-2621']['introduced_unknown'], ['ThinkPad 1400 (Type 2651)'])

    def test_all_four_special_r52_types_use_exact_dated_brochure_not_family_launch(self):
        models = {m['id']: m for m in json.loads((ROOT / 'data/models.json').read_text())['models']}
        for identity, types in [('r52-1846', ['1850', '1870']), ('r52-1858', ['1862', '1863'])]:
            rows = [r for r in models[identity]['introduced'] if r.get('evidence')]
            self.assertEqual({v for r in rows for v in r['variants']},
                             {'ThinkPad R52 (Type ' + t + ')' for t in types})
            self.assertFalse(models[identity].get('introduced_unknown'))
            for row in rows:
                self.assertEqual(row['year'], 2005)
                self.assertEqual(row['evidence']['kind'], 'commercial_listing')
                self.assertIn('291939136', row['url'])
                self.assertIn('March 2005', row['evidence']['note']['en'])


if __name__ == '__main__':
    unittest.main()
