"""Offline distribution uses the actual static builder, never arbitrary staging."""
from pathlib import Path
import hashlib
import importlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

import test_build as fixtures

ROOT = Path(__file__).resolve().parents[1]


class OfflineRelease(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='archive offline ', dir=os.environ.get('TMPDIR'))
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.data = self.root / 'metadata'
        fixtures.write_fixture(self.data)

    def api(self):
        from thinkpad_archive import __path__
        self.assertTrue((Path(next(iter(__path__))) / 'offline_release.py').is_file(),
                        'Offline release API is not implemented')
        return importlib.import_module('thinkpad_archive.offline_release')

    def package(self, destination='release', **kwargs):
        return self.api().build_offline_release(self.root / destination, data_dir=self.data, **kwargs)

    def verify(self, output):
        version = (ROOT / 'VERSION').read_text().strip()
        name = 'thinkpad-archive-' + version + '-offline.zip'
        path = output / name
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        self.assertEqual((output / (name + '.sha256')).read_text(), digest + '  ' + name + '\n')
        self.assertEqual({p.name for p in output.iterdir()}, {name, name + '.sha256'})
        prefix = 'thinkpad-archive-' + version + '/'
        with zipfile.ZipFile(path) as archive:
            self.assertIsNone(archive.testzip())
            names = archive.namelist()
            self.assertEqual(names, sorted(set(names)))
            self.assertTrue(all(n.startswith(prefix) and '..' not in n.split('/') and '\\' not in n for n in names))
            content = {n[len(prefix):]: archive.read(n) for n in names}
            self.assertEqual(content['LICENSE'], (ROOT / 'LICENSE').read_bytes())
            self.assertEqual(content['VERSION'], (version + '\n').encode())
            self.assertIn(b'index.html', content['READ-ME.txt'])
            self.assertIn('Español', content['READ-ME.txt'].decode())
            manifest = json.loads(content['SHA256SUMS.json'])
            self.assertEqual(manifest['version'], version)
            expected = {n: hashlib.sha256(body).hexdigest() for n, body in content.items() if n != 'SHA256SUMS.json'}
            self.assertEqual(manifest['files'], expected)
            self.assertTrue(all(i.date_time == (1980, 1, 1, 0, 0, 0) and (i.external_attr >> 16) == 0o100644 for i in archive.infolist()))
        return content

    def test_bilingual_complete_archive_checksum_manifest_and_public_boundary(self):
        module = self.api()
        with patch('socket.socket', side_effect=RuntimeError('Network forbidden')):
            output = self.package()
        content = self.verify(output)
        for lang in ('en', 'es'):
            self.assertIn(lang + '/models/700c.html', content)
            self.assertIn(lang + '/models/x230-tablet.html', content)
            page = content[lang + '/models/700c.html'].decode()
            self.assertIn('model-correction', page)
            self.assertIn('https://example.org/manual.pdf', page)
            self.assertNotIn('data-stats-enabled="true"', page)
            self.assertNotIn('<script src="../../assets/analytics.js"', page)
        self.assertIn('lang="en"', content['index.html'].decode())
        self.assertNotIn('data/', '\n'.join(content))
        self.assertFalse(any(n.endswith(('.pdf', '.exe', '.sqlite', '.py')) for n in content))
        self.assertTrue(callable(module.build_offline_release))

    def test_same_inputs_generate_identical_zip_and_checksums(self):
        one, two = self.package('one'), self.package('two')
        self.assertEqual({p.name: p.read_bytes() for p in one.iterdir()}, {p.name: p.read_bytes() for p in two.iterdir()})

    def test_existing_directory_file_and_symlink_are_preserved(self):
        self.api()
        folder = self.root / 'occupied';folder.mkdir();(folder / 'keep').write_text('unchanged')
        file = self.root / 'occupied-file';file.write_text('unchanged')
        link = self.root / 'occupied-link';link.symlink_to(folder, target_is_directory=True)
        for destination in (folder, file, link):
            with self.subTest(name=destination.name), self.assertRaises(ValueError):
                self.api().build_offline_release(destination, data_dir=self.data)
        self.assertEqual((folder / 'keep').read_text(), 'unchanged')
        self.assertEqual(file.read_text(), 'unchanged')
        self.assertTrue(link.is_symlink())

    def test_symlink_parent_and_output_inside_source_are_refused(self):
        module = self.api()
        alias = self.root / 'alias';alias.symlink_to(self.root, target_is_directory=True)
        for path in (alias / 'out', self.data / 'out'):
            with self.subTest(kind=path.name), self.assertRaises(ValueError):
                module.build_offline_release(path, data_dir=self.data)
            self.assertFalse(path.exists())

    def test_bad_metadata_leaves_no_output_or_staging(self):
        module = self.api();(self.data / 'drivers.json').write_text('not json')
        before = set(self.root.iterdir())
        with self.assertRaises(ValueError):
            module.build_offline_release(self.root / 'refused', data_dir=self.data)
        self.assertEqual(set(self.root.iterdir()), before)

    def test_unlisted_generated_file_is_refused_not_packaged(self):
        module = self.api();real = module.build_site
        def contaminated(*args, **kwargs):
            site = real(*args, **kwargs)
            (site / 'unlisted.sqlite').write_bytes(b'not public')
            return site
        with patch.object(module, 'build_site', side_effect=contaminated), self.assertRaises(ValueError):
            self.package('refused')
        self.assertFalse((self.root / 'refused').exists())
        self.assertEqual({p.name for p in self.root.iterdir()}, {'metadata'})

    def test_invalid_version_refused_without_output(self):
        module = self.api();real = module.read_bytes
        for number, value in enumerate((b'../wrong', b'0.5.2\nextra', b'01.2.3', b'1.2', b'1.2.3;bad')):
            def read(path, *args, **kwargs):
                return value if Path(path).name == 'VERSION' else real(path, *args, **kwargs)
            with self.subTest(number=number), patch.object(module, 'read_bytes', side_effect=read), self.assertRaises(ValueError):
                self.package('invalid-' + str(number))
            self.assertFalse((self.root / ('invalid-' + str(number))).exists())

    def test_archive_failure_cleans_owned_staging_without_output(self):
        module = self.api();before = set(self.root.iterdir())
        with patch.object(module.zipfile.ZipFile, 'writestr', side_effect=OSError('synthetic IO refusal')), self.assertRaises(ValueError):
            self.package('refused')
        self.assertEqual(set(self.root.iterdir()), before)

    def test_generated_manifest_includes_source_rights_and_spanish_root_option(self):
        output = self.package('spanish', default_language='es')
        content = self.verify(output)
        self.assertIn('lang="es"', content['index.html'].decode())
        self.assertEqual(content['docs/sources-and-rights.md'], (ROOT / 'docs/sources-and-rights.md').read_bytes())

    def test_member_total_and_count_limits_fail_closed_without_partial_output(self):
        module = self.api()
        for index, (limit, value) in enumerate((('MAX_MEMBERS', 1), ('MAX_TOTAL', 1), ('MAX_MEMBER', 1))):
            before = set(self.root.iterdir())
            with self.subTest(limit=limit), patch.object(module, limit, value), self.assertRaises(ValueError):
                self.package('refused-' + str(index))
            self.assertEqual(set(self.root.iterdir()), before)

    def test_generated_missing_member_symlink_and_corrupt_archive_are_refused(self):
        module = self.api();real = module.build_site
        for number, mode in enumerate(('missing', 'symlink')):
            def contaminated(*args, **kwargs):
                site = real(*args, **kwargs)
                path = site / 'en/models/700c.html'
                path.unlink()
                if mode == 'symlink':
                    path.symlink_to(site / 'index.html')
                return site
            with self.subTest(mode=mode), patch.object(module, 'build_site', side_effect=contaminated), self.assertRaises(ValueError):
                self.package('refused-' + str(number))
            self.assertEqual({p.name for p in self.root.iterdir()}, {'metadata'})
        original = module.zipfile.ZipFile.writestr
        def corrupt(archive, info, body, **kwargs):
            return original(archive, info, b'corrupt', **kwargs)
        with patch.object(module.zipfile.ZipFile, 'writestr', new=corrupt), self.assertRaises(ValueError):
            self.package('corrupt')
        self.assertEqual({p.name for p in self.root.iterdir()}, {'metadata'})

    def test_publish_copy_failure_cleans_only_owned_output(self):
        module = self.api()
        with patch.object(module.shutil, 'copyfileobj', side_effect=OSError('synthetic copy refusal')), self.assertRaises(ValueError):
            self.package('refused')
        self.assertEqual({p.name for p in self.root.iterdir()}, {'metadata'})

    def test_cli_success_from_unrelated_directory_and_sanitized_refusal(self):
        self.api()
        env = {k: os.environ[k] for k in ('PATH', 'HOME', 'TMPDIR', 'LANG') if k in os.environ}
        env['PYTHONPATH'] = str(ROOT)
        output = self.root / 'cli package'
        cmd = [sys.executable, '-m', 'thinkpad_archive', 'offline-release', '--output', str(output), '--data-dir', str(self.data)]
        run = subprocess.run(cmd, cwd=self.root, env=env, capture_output=True, text=True, timeout=40)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.verify(output)
        again = subprocess.run(cmd, cwd=self.root, env=env, capture_output=True, text=True, timeout=20)
        self.assertNotEqual(again.returncode, 0)
        self.assertIn('offline release refused', again.stderr)
        self.assertNotIn(str(self.root), again.stdout + again.stderr)
        self.assertNotIn('Traceback', again.stderr)
        self.assertNotIn('--enable-stats', subprocess.check_output([sys.executable, '-m', 'thinkpad_archive', 'offline-release', '--help'], cwd=ROOT, env=env, text=True))


if __name__ == '__main__':
    unittest.main()
