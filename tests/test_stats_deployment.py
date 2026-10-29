"""Opt-in analytics deployment must not replace the static-only default."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class StatsDeployment(unittest.TestCase):
    def test_static_default_and_opt_in_targets_are_separate(self):
        text = (ROOT / 'Dockerfile').read_text()
        self.assertIn('AS stats', text)
        self.assertIn('--enable-stats', text)
        self.assertIn('thinkpad_archive.stats_server', text)
        self.assertIn('AS static', text)
        self.assertGreater(text.rindex('AS static'), text.index('AS stats'))

    def test_scoped_proxy_strips_identifying_headers_and_has_no_request_log(self):
        path = ROOT / 'deploy/Caddyfile.stats'
        self.assertTrue(path.is_file())
        text = path.read_text()
        self.assertIn('handle /api/stats/*', text)
        for key in ('Cookie', 'User-Agent', 'Referer', 'Forwarded', 'X-Forwarded-For', 'X-Real-IP'):
            self.assertIn('header_up -' + key, text)
        self.assertIn('log {', text)
        self.assertIn('output discard', text)
        self.assertIn('max_size 1KB', text)
        self.assertIn('file_server', text)

    def test_compose_persists_only_counts_privately_and_exposes_only_proxy(self):
        path = ROOT / 'deploy/compose.stats.yaml'
        self.assertTrue(path.is_file())
        text = path.read_text()
        self.assertIn('target: stats', text)
        self.assertIn('target: stats-web', text)
        self.assertIn('mode=0700', text)
        self.assertIn('stats-data:/data', text)
        self.assertIn('ANALYTICS_ORIGIN', text)
        self.assertNotIn('8081:8081', text)
        self.assertNotIn('privileged:', text)
