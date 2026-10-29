"""Basic CI consumes the real verification runner and safe workflow gates."""
from pathlib import Path
import importlib.util
import os
import re
import subprocess
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


def load_tool(name):
    path = ROOT / 'tools' / (name + '.py')
    if not path.is_file():
        raise AssertionError('Required verification tool is not implemented: ' + name)
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise AssertionError('Could not load verification tool')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class BasicCI(unittest.TestCase):
    def test_runner_executes_tests_node_syntax_all_builds_links_and_optional_package(self):
        module = load_tool('check')
        with tempfile.TemporaryDirectory(dir=os.environ.get('TMPDIR')) as folder:
            calls = []
            def run(argv, **kwargs):
                calls.append((argv, kwargs))
                return subprocess.CompletedProcess(argv, 0)
            with patch.object(module.subprocess, 'run', side_effect=run):
                module.check_project(Path(folder) / 'checks', package=True)
            argv = [row[0] for row in calls]
            self.assertTrue(any('unittest' in a and 'discover' in a for a in argv))
            self.assertTrue(any('compileall' in a for a in argv))
            self.assertEqual(sum(a[:2] == ['node', '--check'] for a in argv), len(list((ROOT / 'assets').glob('*.js'))))
            builds = [a for a in argv if 'build' in a and 'thinkpad_archive' in a]
            self.assertEqual(len(builds), 3)
            self.assertTrue(any('--default-language' in a and 'es' in a for a in builds))
            self.assertTrue(any('--enable-stats' in a for a in builds))
            self.assertEqual(sum(any(str(x).endswith('check_site.py') for x in a) for a in argv), 3)
            self.assertTrue(any('offline-release' in a for a in argv))
            self.assertTrue(all(k['check'] and 0 < k['timeout'] <= 600 for _, k in calls))

    def test_runner_child_failure_is_not_hidden_and_existing_output_is_preserved(self):
        module = load_tool('check')
        with tempfile.TemporaryDirectory(dir=os.environ.get('TMPDIR')) as folder:
            dest = Path(folder) / 'existing';dest.mkdir();(dest / 'keep').write_text('unchanged')
            calls = []
            def run(argv, **kwargs):
                calls.append(argv)
                raise subprocess.CalledProcessError(1, argv)
            with patch.object(module.subprocess, 'run', side_effect=run), self.assertRaises(ValueError):
                module.check_project(dest, package=False)
            self.assertEqual(calls, [])
            self.assertEqual((dest / 'keep').read_text(), 'unchanged')
            with patch.object(module.subprocess, 'run', side_effect=run), self.assertRaises(subprocess.CalledProcessError):
                module.check_project(Path(folder) / 'new', package=False)
            self.assertEqual(len(calls), 1)

    def test_push_pr_and_reusable_ci_are_readonly_version_matrix_with_node_and_lint(self):
        path = ROOT / '.github/workflows/ci.yml'
        self.assertTrue(path.is_file(), 'Branch/PR CI workflow is missing')
        text = path.read_text()
        for required in ('push:', 'branches:', 'pull_request:', 'workflow_call:', "'3.11'", "'3.13'",
                         'actions/setup-node@', 'contents: read', 'persist-credentials: false',
                         'tools/check.py', 'actionlint/cmd/actionlint@v1.7.11', 'if-no-files-found: error'):
            self.assertIn(required, text)
        self.assertNotIn('contents: write', text)
        self.assertNotIn('pull_request_target', text)
        self.assertNotIn('continue-on-error', text)
        self.assertNotIn('secrets: inherit', text)

    def test_release_draft_waits_for_shared_ci_and_only_runs_on_version_tags(self):
        path = ROOT / '.github/workflows/release.yml'
        self.assertTrue(path.is_file(), 'Tag-to-draft release workflow is missing')
        text = path.read_text()
        for required in ('tags:', "'v*'", 'uses: ./.github/workflows/ci.yml', 'needs: checks',
                         'contents: write', 'persist-credentials: false', 'tools/release_draft.py',
                         'cancel-in-progress: false', 'github.sha'):
            self.assertIn(required, text)
        self.assertNotIn('git push', text)
        self.assertNotIn('--clobber', text)
        for workflow in (ROOT / '.github/workflows').glob('*.yml'):
            for use in re.findall(r'uses:\s+([^\s#]+)', workflow.read_text()):
                self.assertTrue(use.startswith('./') or re.fullmatch(r'actions/[a-z-]+@[0-9a-f]{40}', use), use)

    def test_ci_inline_programs_forward_flags_and_refuse_bad_whitespace_refs(self):
        source = (ROOT / '.github/workflows/ci.yml').read_text().splitlines()
        blocks = []
        start = None
        for index, line in enumerate(source):
            if line == "          python - <<'PY'":start = index + 1
            elif line == '          PY' and start is not None:
                blocks.append('\n'.join(row[10:] for row in source[start:index]) + '\n');start = None
        self.assertEqual(len(blocks), 2)
        with tempfile.TemporaryDirectory(dir=os.environ.get('TMPDIR')) as folder:
            before = Path.cwd();os.chdir(folder)
            try:
                for flag in ('yes', 'no'):
                    calls = []
                    with patch.dict(os.environ, {'PACKAGE': flag}, clear=True), patch('subprocess.run', side_effect=lambda argv, **kwargs: calls.append(argv)):
                        exec(compile(blocks[0], '<actual CI verification block>', 'exec'), {})
                    self.assertEqual('--package' in calls[0], flag == 'yes')
                with patch.dict(os.environ, {'PACKAGE': 'yes'}, clear=True), patch('subprocess.run', side_effect=subprocess.CalledProcessError(1, ['checks'])), self.assertRaises(subprocess.CalledProcessError):
                    exec(compile(blocks[0], '<actual CI verification block>', 'exec'), {})
                for base in ('a' * 40, '', '0' * 40):
                    calls = []
                    with patch.dict(os.environ, {'BASE_SHA': base, 'HEAD_SHA': 'b' * 40}, clear=True), patch('subprocess.check_output', return_value=b'c' * 40), patch('subprocess.run', side_effect=lambda argv, **kwargs: calls.append(argv)):
                        exec(compile(blocks[1], '<actual CI whitespace block>', 'exec'), {})
                    self.assertEqual(calls[0], ['git', 'diff', '--check', base if base == 'a' * 40 else 'c' * 40, 'b' * 40])
                calls.clear()
                with patch.dict(os.environ, {'BASE_SHA': '--unsafe', 'HEAD_SHA': 'b' * 40}, clear=True), patch('subprocess.run', side_effect=lambda argv, **kwargs: calls.append(argv)), self.assertRaises(SystemExit):
                    exec(compile(blocks[1], '<actual CI whitespace block>', 'exec'), {})
                self.assertEqual(calls, [])
            finally:os.chdir(before)

    def test_docker_includes_the_new_test_prerequisites_without_private_files(self):
        docker = (ROOT / 'Dockerfile').read_text()
        context = (ROOT / '.dockerignore').read_text()
        for rel in ('.github/workflows/ci.yml', '.github/workflows/release.yml', 'CHANGELOG.md'):
            self.assertIn(rel, docker)
            self.assertIn('!' + rel, context)
        self.assertNotIn('COPY . ', docker)


if __name__ == '__main__':
    unittest.main()
