"""Tests for a generated-site link/fragment verifier, not hardware validation."""
import importlib.util
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class SiteCheck(unittest.TestCase):
    def checker(self):
        path = ROOT / 'tools' / 'check_site.py'
        self.assertTrue(path.is_file(), 'generated-site checker API is missing')
        spec = importlib.util.spec_from_file_location('sitecheck', path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod.check_site

    def test_valid_site_relative_links_and_fragments(self):
        check = self.checker()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'models').mkdir()
            (root / 'index.html').write_text('<html lang="en"><a href="models/x.html#manuals">X</a><a href="https://example.com/a">Source</a></html>')
            (root / 'models/x.html').write_text('<html lang="en"><h2 id="manuals">Manuals</h2><a href="../index.html">Home</a></html>')
            result = check(root)
            self.assertEqual(result['errors'], [])
            self.assertEqual(result['html_pages'], 2)
            self.assertEqual(result['external_links'], 1)

    def test_missing_internal_file_and_fragment_are_reported(self):
        check = self.checker()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'index.html').write_text('<a href="missing.html">M</a><a href="#missing">A</a>')
            result = check(root)
            self.assertEqual({e['reason'] for e in result['errors']}, {'missing-file', 'missing-fragment'})

    def test_escape_unsafe_scheme_and_remote_asset_are_rejected(self):
        check = self.checker()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'index.html').write_text('<a href="../outside.txt">Escape</a><a href="javascript:alert(1)">Bad</a><script src="https://example.com/a.js"></script>')
            result = check(root)
            self.assertEqual({e['reason'] for e in result['errors']}, {'path-escape', 'unsafe-scheme', 'remote-asset'})

    def test_https_canonical_is_metadata_not_a_remote_asset(self):
        check = self.checker()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'index.html').write_text('<link rel="canonical" href="https://thinkpadarchive.com/en/"><script src="https://example.com/a.js"></script><link rel="canonical" href="javascript:alert(1)">')
            result = check(root)
            self.assertEqual(result['external_links'], 1)
            self.assertEqual([e['reason'] for e in result['errors']], ['remote-asset', 'unsafe-scheme'])

    def test_stats_api_export_is_allowed_only_by_explicit_scoped_flag(self):
        check = self.checker()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'index.html').write_text('<a href="/api/stats/export.json">Export</a><a href="/api/private">Not allowed</a>')
            self.assertEqual(len(check(root)['errors']), 2)
            import inspect
            self.assertIn('allow_stats_api', inspect.signature(check).parameters)
            result = check(root, allow_stats_api=True)
            self.assertEqual([e['link'] for e in result['errors']], ['/api/private'])
            self.assertEqual(result['internal_links'], 1)

    def test_duplicate_ids_are_rejected(self):
        check = self.checker()
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'index.html').write_text('<h2 id="same"></h2><p id="same"></p>')
            self.assertIn('duplicate-id', [e['reason'] for e in check(root)['errors']])


if __name__ == '__main__':
    unittest.main()
