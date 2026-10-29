"""Tag-to-draft release handling with inert GitHub IO and real offline assets."""
from pathlib import Path
import hashlib
import importlib.util
import json
import os
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import test_build as fixtures
from thinkpad_archive.offline_release import build_offline_release

ROOT = Path(__file__).resolve().parents[1]


def tool():
    path = ROOT / 'tools/release_draft.py'
    if not path.is_file():
        raise AssertionError('Draft release tool is not implemented')
    spec = importlib.util.spec_from_file_location('release_draft', path)
    if spec is None or spec.loader is None:
        raise AssertionError('Could not load release tool')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ReleaseDraft(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir=os.environ.get('TMPDIR'))
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        fixtures.write_fixture(self.root / 'data')
        self.assets = build_offline_release(self.root / 'offline', data_dir=self.root / 'data')
        self.version = (ROOT / 'VERSION').read_text().strip()
        self.tag = 'v' + self.version
        self.sha = 'a' * 40
        self.repo = 'example/archive'

    def release(self, *, draft=True, digest_override=None):
        return {'id': 123, 'tag_name': self.tag, 'draft': draft, 'prerelease': self.version.startswith('0.'),
                'assets': [{'name': p.name, 'size': p.stat().st_size, 'state': 'uploaded',
                            'digest': digest_override or 'sha256:' + hashlib.sha256(p.read_bytes()).hexdigest()}
                           for p in sorted(self.assets.iterdir())]}

    def invoke(self, module, **kwargs):
        return module.prepare_draft(self.assets, repository=self.repo, tag=self.tag, sha=self.sha, **kwargs)

    def test_new_tag_creates_one_draft_with_assets_after_exact_identity_checks(self):
        module = tool();calls = []
        def run(argv, **kwargs):
            calls.append(argv)
            if argv[:3] == ['git', 'rev-parse', 'HEAD']:
                return subprocess.CompletedProcess(argv, 0, stdout=self.sha + '\n', stderr='')
            if argv[:3] == ['git', 'rev-parse', self.tag + '^{commit}']:
                return subprocess.CompletedProcess(argv, 0, stdout=self.sha + '\n', stderr='')
            if argv[:3] == ['gh', 'api', 'repos/' + self.repo + '/releases?per_page=100']:
                listing = [self.release()] if any(c[:3] == ['gh', 'release', 'create'] for c in calls) else []
                return subprocess.CompletedProcess(argv, 0, stdout=json.dumps([listing]), stderr='')
            if argv[:3] == ['gh', 'release', 'create']:
                return subprocess.CompletedProcess(argv, 0, stdout='https://example.invalid/release', stderr='')
            if argv[:3] == ['gh', 'api', 'repos/' + self.repo + '/releases/tags/' + self.tag]:
                return subprocess.CompletedProcess(argv, 0, stdout=json.dumps(self.release()), stderr='')
            raise AssertionError('Unexpected inert command')
        with patch.object(module.subprocess, 'run', side_effect=run):
            result = self.invoke(module)
        creates = [c for c in calls if c[:3] == ['gh', 'release', 'create']]
        self.assertEqual(len(creates), 1)
        for flag in ('--draft', '--verify-tag', '--notes-file'):
            self.assertIn(flag, creates[0])
        self.assertEqual('--prerelease' in creates[0], self.version.startswith('0.'))
        self.assertNotIn('--clobber', creates[0])
        self.assertEqual(result['status'], 'draft-created')

    def test_existing_identical_draft_is_noop_and_unknown_api_failure_never_creates(self):
        module = tool();calls = []
        def run(argv, **kwargs):
            calls.append(argv)
            value = self.sha + '\n' if argv[0] == 'git' else json.dumps([self.release()])
            return subprocess.CompletedProcess(argv, 0, stdout=value, stderr='')
        with patch.object(module.subprocess, 'run', side_effect=run):
            result = self.invoke(module)
        self.assertEqual(result['status'], 'draft-already-present')
        self.assertFalse(any(c[:3] == ['gh', 'release', 'create'] for c in calls))
        calls.clear()
        def broken(argv, **kwargs):
            calls.append(argv)
            if argv[0] == 'git':return subprocess.CompletedProcess(argv, 0, stdout=self.sha, stderr='')
            raise subprocess.CalledProcessError(1, argv)
        with patch.object(module.subprocess, 'run', side_effect=broken), self.assertRaises(subprocess.CalledProcessError):
            self.invoke(module)
        self.assertFalse(any(c[:3] == ['gh', 'release', 'create'] for c in calls))

    def test_tag_version_sha_and_existing_asset_mismatches_refuse(self):
        module = tool()
        with self.assertRaises(ValueError):self.invoke(module, version='0.0.0')
        for state in (self.release(digest_override='sha256:' + 'b' * 64), self.release(draft=False)):
            calls = []
            def run(argv, **kwargs):
                calls.append(argv)
                value = self.sha if argv[0] == 'git' else json.dumps([state])
                return subprocess.CompletedProcess(argv, 0, stdout=value, stderr='')
            with patch.object(module.subprocess, 'run', side_effect=run), self.assertRaises(ValueError):
                self.invoke(module)
            self.assertFalse(any(c[:3] == ['gh', 'release', 'create'] for c in calls))

    def test_sha_mismatch_and_ambiguous_create_fail_without_replay(self):
        module = tool();calls = []
        def wrong_sha(argv, **kwargs):
            calls.append(argv)
            return subprocess.CompletedProcess(argv, 0, stdout='b' * 40, stderr='')
        with patch.object(module.subprocess, 'run', side_effect=wrong_sha), self.assertRaises(ValueError):
            self.invoke(module)
        self.assertFalse(any(c[0] == 'gh' for c in calls))
        calls.clear()
        def create_failed(argv, **kwargs):
            calls.append(argv)
            if argv[0] == 'git':return subprocess.CompletedProcess(argv, 0, stdout=self.sha, stderr='')
            if argv[:3] == ['gh', 'release', 'create']:
                raise subprocess.CalledProcessError(1, argv)
            return subprocess.CompletedProcess(argv, 0, stdout='[[]]', stderr='')
        with patch.object(module.subprocess, 'run', side_effect=create_failed), self.assertRaises(subprocess.CalledProcessError):
            self.invoke(module)
        self.assertEqual(sum(c[:3] == ['gh', 'release', 'create'] for c in calls), 1)

    def test_assets_validator_rejects_corrupt_members_even_with_new_outer_checksum(self):
        module = tool()
        import zipfile
        archive = next(self.assets.glob('*.zip'))
        with zipfile.ZipFile(archive) as old:
            contents = {n: old.read(n) for n in old.namelist()}
        name = next(n for n in contents if n.endswith('/index.html'))
        contents[name] = b'changed'
        with zipfile.ZipFile(archive, 'w') as out:
            for path, data in contents.items():out.writestr(path, data)
        checksum = hashlib.sha256(archive.read_bytes()).hexdigest()
        next(self.assets.glob('*.sha256')).write_text(checksum + '  ' + archive.name + '\n')
        calls = []
        with patch.object(module.subprocess, 'run', side_effect=lambda *a, **k: calls.append(a)), self.assertRaises(ValueError):
            self.invoke(module)
        self.assertEqual(calls, [])

    def test_wrong_prerelease_state_is_refused_before_create_or_after_one_create(self):
        module = tool()
        for initially_present in (True, False):
            with self.subTest(existing=initially_present):
                calls = []
                invalid = self.release();invalid['prerelease'] = not self.version.startswith('0.')
                def run(argv, **kwargs):
                    calls.append(argv)
                    if argv[0] == 'git':
                        return subprocess.CompletedProcess(argv, 0, stdout=self.sha, stderr='')
                    if argv[:3] == ['gh', 'release', 'create']:
                        return subprocess.CompletedProcess(argv, 0, stdout='draft created', stderr='')
                    present = initially_present or any(c[:3] == ['gh', 'release', 'create'] for c in calls)
                    return subprocess.CompletedProcess(argv, 0, stdout=json.dumps([[invalid] if present else []]), stderr='')
                with patch.object(module.subprocess, 'run', side_effect=run), self.assertRaises(ValueError):
                    self.invoke(module)
                self.assertEqual(sum(c[:3] == ['gh', 'release', 'create'] for c in calls), 0 if initially_present else 1)
                self.assertFalse(any(c[:3] in (['gh', 'release', 'edit'], ['gh', 'release', 'upload']) for c in calls))

    def test_both_stable_and_prerelease_channels_create_and_reconcile(self):
        # Characterize the existing channel policy independently of VERSION.
        import thinkpad_archive.offline_release as offline
        for number, expected in (('0.9.0', True), ('1.0.0', False)):
            with self.subTest(version=number):
                root = self.root / ('channel-' + number)
                root.mkdir()
                (root / 'VERSION').write_text(number + '\n')
                (root / 'CHANGELOG.md').write_text('# Changelog\n\n## ' + number + '\n\n- Channel fixture.\n')
                with patch.object(offline, 'release_version', return_value=number):
                    assets = build_offline_release(root / 'offline', data_dir=self.root / 'data')
                module = tool(); calls = []; present = False
                release = {'tag_name': 'v' + number, 'draft': True, 'prerelease': expected,
                           'assets': [{'name': p.name, 'size': p.stat().st_size, 'state': 'uploaded',
                                       'digest': 'sha256:' + hashlib.sha256(p.read_bytes()).hexdigest()}
                                      for p in sorted(assets.iterdir())]}
                def run(argv, **kwargs):
                    nonlocal present
                    calls.append(argv)
                    if argv[0] == 'git':
                        return subprocess.CompletedProcess(argv, 0, stdout=self.sha, stderr='')
                    if argv[:3] == ['gh', 'release', 'create']:
                        present = True
                        return subprocess.CompletedProcess(argv, 0, stdout='created', stderr='')
                    if argv[:2] == ['gh', 'api']:
                        return subprocess.CompletedProcess(argv, 0, stdout=json.dumps([[release] if present else []]), stderr='')
                    raise AssertionError('Unexpected inert channel command')
                with patch.object(module, 'ROOT', root), patch.object(module.subprocess, 'run', side_effect=run):
                    result = module.prepare_draft(assets, repository=self.repo, tag='v' + number, sha=self.sha)
                    again = module.prepare_draft(assets, repository=self.repo, tag='v' + number, sha=self.sha)
                creates = [a for a in calls if a[:3] == ['gh', 'release', 'create']]
                self.assertEqual(len(creates), 1)
                self.assertEqual('--prerelease' in creates[0], expected)
                self.assertEqual(result['status'], 'draft-created')
                self.assertEqual(again['status'], 'draft-already-present')
                self.assertFalse(any(a[:3] in (['gh', 'release', 'edit'], ['gh', 'release', 'upload']) for a in calls))

    def test_checksum_refusal_precedes_remote_queries(self):
        module = tool()
        next(self.assets.glob('*.sha256')).write_text('wrong')
        calls = []
        with patch.object(module.subprocess, 'run', side_effect=lambda *a, **k: calls.append(a)), self.assertRaises(ValueError):
            self.invoke(module)
        self.assertEqual(calls, [])


if __name__ == '__main__':
    unittest.main()
