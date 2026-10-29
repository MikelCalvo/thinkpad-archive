"""Release automation is separate from site deployment and release creation."""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]


class OfflineWorkflow(unittest.TestCase):
    def test_published_release_exact_sha_readonly_build_and_separate_attachment(self):
        path = ROOT / '.github/workflows/offline-release.yml'
        self.assertTrue(path.is_file(), 'Offline release attachment workflow is missing')
        text = path.read_text()
        for required in ('types: [published]', 'github.event.release.tag_name', 'github.sha',
                         'persist-credentials: false', 'contents: read', 'contents: write',
                         'needs: build', "'unittest', 'discover'", "'offline-release', '--output'",
                         "'gh', 'release', 'upload'", 'SHA256SUMS', 'timeout-minutes:'):
            self.assertIn(required, text)
        self.assertNotIn("'gh', 'release', 'create'", text)
        self.assertNotIn("'--clobber'", text)
        self.assertNotIn('pull_request_target', text)
        self.assertNotIn('git push', text)
        uses = re.findall(r'uses:\s+([^\s]+)', text)
        self.assertEqual(len(uses), 4)
        self.assertTrue(all(re.fullmatch(r'actions/[a-z-]+@[a-f0-9]{40}', value) for value in uses))

    def test_packaging_prerequisites_are_present_in_the_docker_test_stage(self):
        docker = (ROOT / 'Dockerfile').read_text()
        context = (ROOT / '.dockerignore').read_text()
        for required in ('LICENSE', 'docs/sources-and-rights.md'):
            self.assertIn(required, docker)
            self.assertIn('!' + required, context)
        self.assertIn('!.github/workflows/offline-release.yml', context)
        self.assertIn('COPY .github/workflows/offline-release.yml', docker)


if __name__ == '__main__':
    unittest.main()
