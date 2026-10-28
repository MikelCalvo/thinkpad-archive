"""Missing dates are null source facts, never translated parser placeholders."""
from pathlib import Path
import importlib.util
import json
import os
import tempfile
import unittest

import test_build as fixtures

ROOT = Path(__file__).resolve().parents[1]
SENTINEL = 'No indicada en la matriz'


def projection():
    spec = importlib.util.spec_from_file_location('date_audit', ROOT / 'tools/catalogue_audit.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.normalize_matrix_row


def source_row(date):
    return {'category': 'Audio', 'description': 'Audio driver Version: 1.2 Read me',
            'os': 'Windows XP', 'released': date,
            'links': [{'url': 'https://example.org/audio.txt', 'label': 'Read me'}]}


class MissingDates(unittest.TestCase):
    def test_missing_sentinel_becomes_null_before_identity_hash(self):
        normalize = projection()
        expected = normalize(source_row(None), 'https://example.org/model')
        result = normalize(source_row(SENTINEL), 'https://example.org/model')
        self.assertIsNone(result['released'])
        self.assertEqual(result, expected)

    def test_manufacturer_date_is_preserved(self):
        result = projection()(source_row('09 Dec 2000'), 'https://example.org/model')
        self.assertEqual(result['released'], '09 Dec 2000')

    def test_imported_unknown_date_uses_localized_output(self):
        import thinkpad_archive
        records = fixtures.fixture_data()
        driver = projection()(source_row(SENTINEL), 'https://example.org/model')
        records['drivers']['drivers'] = [driver]
        for model in records['models']['models']:
            model['driver_ids'] = [driver['id']] if model['id'] == '700c' else []
        with tempfile.TemporaryDirectory(dir=os.environ.get('TMPDIR')) as tmp:
            root = Path(tmp)
            fixtures.write_fixture(root / 'data', records)
            thinkpad_archive.build_site(root / 'site', data_dir=root / 'data')
            for lang, label, value in [('en', 'Date listed by source', 'Not recorded'),
                                        ('es', 'Fecha indicada por la fuente', 'No consta')]:
                text = (root / 'site' / lang / 'models/700c.html').read_text()
                self.assertNotIn(SENTINEL, text)
                self.assertIn('<dt>' + label + '</dt><dd>' + value + '</dd>', text)

    def test_live_catalogue_missing_date_routes_have_null_dates(self):
        records = json.loads((ROOT / 'data/drivers.json').read_text())['drivers']
        routes = {'R50': 183, 'R50e': 172, 'R50p': 195, 'R51': 187, 'R51e': 169}
        self.assertFalse(any(row['released'] == SENTINEL for row in records))
        for route, expected in routes.items():
            subset = [row for row in records if row['source_url'] == 'https://download.lenovo.com/lenovo/content/ddfm/' + route + '.html']
            self.assertEqual(len(subset), expected)
            self.assertTrue(all(row['released'] is None for row in subset))


if __name__ == '__main__':
    unittest.main()
