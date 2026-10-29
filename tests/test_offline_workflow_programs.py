"""Exercise the shipped release workflow's actual inline Python without uploads."""
from pathlib import Path
from contextlib import redirect_stdout, redirect_stderr
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


def workflow_blocks():
    lines = (ROOT / '.github/workflows/offline-release.yml').read_text().splitlines()
    blocks = []
    start = None
    for index, line in enumerate(lines):
        if line == "          python - <<'PY'":
            start = index + 1
        elif line == '          PY' and start is not None:
            blocks.append('\n'.join(row[10:] for row in lines[start:index]) + '\n')
            start = None
    if len(blocks) != 2:
        raise AssertionError('Both final inline workflow programs must be found')
    return blocks


class WorkflowPrograms(unittest.TestCase):
    def test_build_block_accepts_exact_tag_and_sha_and_propagates_child_failures(self):
        source = workflow_blocks()[0]
        version = (ROOT / 'VERSION').read_text().strip()
        env = {'RELEASE_TAG': 'v' + version, 'RELEASE_SHA': 'a' * 40}
        with tempfile.TemporaryDirectory(dir=os.environ.get('TMPDIR')) as folder:
            before = Path.cwd()
            os.chdir(folder)
            try:
                Path('VERSION').write_text(version + '\n')
                calls = []
                def run(argv, **kwargs):
                    calls.append((argv, kwargs))
                    return subprocess.CompletedProcess(argv, 0)
                with patch.dict(os.environ, env, clear=True), patch('subprocess.check_output', return_value='a' * 40), patch('subprocess.run', side_effect=run):
                    exec(compile(source, '<actual release build block>', 'exec'), {})
                self.assertEqual(len(calls), 2)
                self.assertTrue(all(kwargs['check'] and kwargs['timeout'] > 0 for _, kwargs in calls))
                self.assertIn('offline-release', calls[1][0])
                for field, value in (('RELEASE_TAG', 'v0.0.0'), ('RELEASE_SHA', 'b' * 40)):
                    invalid = dict(env);invalid[field] = value;calls.clear()
                    with patch.dict(os.environ, invalid, clear=True), patch('subprocess.check_output', return_value='a' * 40), patch('subprocess.run', side_effect=run), self.assertRaises(SystemExit):
                        exec(compile(source, '<actual release build block>', 'exec'), {})
                    self.assertEqual(calls, [])
                calls.clear()
                with patch.dict(os.environ, env, clear=True), patch('subprocess.check_output', return_value='a' * 40), patch('subprocess.run', side_effect=subprocess.CalledProcessError(1, ['tests'])), self.assertRaises(subprocess.CalledProcessError):
                    exec(compile(source, '<actual release build block>', 'exec'), {})
            finally:
                os.chdir(before)

    def test_attach_block_verifies_real_archive_before_one_upload_and_propagates_failure(self):
        from thinkpad_archive.offline_release import build_offline_release
        import test_build as fixtures
        source = workflow_blocks()[1]
        version = (ROOT / 'VERSION').read_text().strip()
        env = {'RELEASE_TAG': 'v' + version, 'RELEASE_ID': '123', 'GH_REPO': 'example/archive'}
        with tempfile.TemporaryDirectory(dir=os.environ.get('TMPDIR')) as folder:
            root = Path(folder);fixtures.write_fixture(root / 'data')
            build_offline_release(root / 'offline', data_dir=root / 'data')
            before = Path.cwd();os.chdir(root)
            try:
                def release(argv, **kwargs):
                    self.assertEqual(argv, ['gh', 'api', 'repos/example/archive/releases/123'])
                    return json.dumps({'tag_name': env['RELEASE_TAG'], 'draft': False})
                calls = []
                def upload(argv, **kwargs):
                    calls.append((argv, kwargs))
                    return subprocess.CompletedProcess(argv, 0)
                with patch.dict(os.environ, env, clear=True), patch('subprocess.check_output', side_effect=release), patch('subprocess.run', side_effect=upload):
                    exec(compile(source, '<actual release attachment block>', 'exec'), {})
                self.assertEqual(len(calls), 1)
                self.assertEqual(calls[0][0][:3], ['gh', 'release', 'upload'])
                self.assertNotIn('--clobber', calls[0][0])
                self.assertTrue(calls[0][1]['check'])
                with patch.dict(os.environ, env, clear=True), patch('subprocess.check_output', side_effect=release), patch('subprocess.run', side_effect=subprocess.CalledProcessError(1, ['upload'])), self.assertRaises(subprocess.CalledProcessError):
                    exec(compile(source, '<actual release attachment block>', 'exec'), {})
                (root / 'offline' / ('thinkpad-archive-' + version + '-offline.zip.sha256')).write_text('incorrect')
                calls.clear()
                with patch.dict(os.environ, env, clear=True), patch('subprocess.check_output', side_effect=release), patch('subprocess.run', side_effect=upload), self.assertRaises(SystemExit):
                    exec(compile(source, '<actual release attachment block>', 'exec'), {})
                self.assertEqual(calls, [])
            finally:
                os.chdir(before)


if __name__ == '__main__':
    unittest.main()
