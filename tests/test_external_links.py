"""Offline contract tests: no vendor network access is used here."""
import contextlib
import importlib.util
import io
import json
import pathlib
import socket
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT = pathlib.Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'tools/check_external_links.py'


def load():
    if not SOURCE.exists():
        raise AssertionError('external-link audit API has not been implemented')
    spec = importlib.util.spec_from_file_location('external_links_under_test', SOURCE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Replies:
    def __init__(self, *items):
        self.items = list(items)
        self.calls = []

    def __call__(self, url, method, timeout):
        self.calls.append((url, method, timeout))
        item = self.items.pop(0)
        if isinstance(item, Exception):
            raise item
        return dict(item)


def reply(status=200, **kw):
    return dict(status=status, content_type='application/pdf', bytes_read=0,
                location=None, challenge=False, soft_missing=False, **kw)


class InventoryTests(unittest.TestCase):
    def test_recursive_pointers_fragment_only_dedupe_and_hashes(self):
        tool = load()
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            (root / 'data').mkdir()
            payload = {'a/b~': ['https://example.com/P?x=%2f#one',
                                 'https://example.com/P?x=%2f#two',
                                 'https://example.com/P?x=%2F',
                                 'https://example.com/P?x=%2f&y=1', 'ftp://x']}
            (root / 'data/a.json').write_text(json.dumps(payload))
            got = tool.inventory(root, ['data/a.json'])
            self.assertEqual(got['occurrences'], 4)
            self.assertEqual(len(got['urls']), 3)
            first = got['urls'][0]
            self.assertEqual(first['url'], 'https://example.com/P?x=%2f')
            self.assertEqual(first['references'][1], {'file': 'data/a.json',
                             'pointer': '/a~1b~0/1', 'url': payload['a/b~'][1]})
            self.assertEqual(len(got['input_sha256']['data/a.json']), 64)

    def test_reject_credentials_before_persisting_inventory(self):
        tool = load()
        with tempfile.TemporaryDirectory() as directory:
            root = pathlib.Path(directory)
            (root / 'x.json').write_text(json.dumps(['https://user:secret@example.com/x']))
            with self.assertRaisesRegex(ValueError, 'credentials'):
                tool.inventory(root, ['x.json'])

    def test_import_has_no_network_or_writes(self):
        with mock.patch.object(socket, 'create_connection', side_effect=AssertionError('network')):
            with mock.patch.object(pathlib.Path, 'write_text', side_effect=AssertionError('write')):
                load()


class SafetyTests(unittest.TestCase):
    def test_public_url_validation(self):
        tool = load()
        for bad in ['http://localhost/a', 'http://127.0.0.1/', 'http://[::1]/',
                    'http://10.1.2.3/', 'file:///x', 'https://u:p@example.com/',
                    'http://169.254.169.254/', 'http://example.local/',
                    'https://example.com:444/', 'https://example.com/\nX']:
            with self.subTest(url=bad), self.assertRaises(ValueError):
                tool.validate_url(bad)
        self.assertEqual(tool.validate_url('https://example.com/P?q=%2f')[0], 'example.com')

    def test_private_dns_rejected(self):
        tool = load()
        with mock.patch.object(socket, 'getaddrinfo', return_value=[
                (socket.AF_INET, socket.SOCK_STREAM, 6, '', ('127.0.0.1', 443))]):
            with self.assertRaisesRegex(ValueError, 'private'):
                tool.resolve_public('example.com', 443)

    def test_multicast_literals_refused(self):
        tool = load()
        for url in ('http://224.0.0.1/', 'https://[ff02::1]/'):
            with self.subTest(url=url), self.assertRaises(ValueError):
                tool.validate_url(url)

    def test_multicast_dns_answers_refused_before_socket(self):
        tool = load()
        public = (socket.AF_INET, socket.SOCK_STREAM, 6, '', ('8.8.8.8', 80))
        multicast = (socket.AF_INET, socket.SOCK_STREAM, 6, '', ('224.0.0.1', 80))
        multicast6 = (socket.AF_INET6, socket.SOCK_STREAM, 6, '', ('ff02::1', 80, 0, 0))
        for answers in ([multicast], [multicast6], [public, multicast], [multicast, public]):
            with self.subTest(answers=answers):
                with mock.patch.object(socket, 'getaddrinfo', return_value=answers), \
                        mock.patch.object(socket, 'create_connection') as connect:
                    with self.assertRaises(ValueError):
                        tool.open_public_connection('http://example.com/a', 1)
                    self.assertEqual(connect.call_count, 0)

    def test_multicast_redirect_refused_before_next_transport(self):
        for url in ('http://224.0.0.1/', 'https://[ff02::1]/'):
            with self.subTest(url=url):
                transport = Replies(dict(reply(302), location=url), reply())
                got = load().check_url('https://example.com/a', transport=transport)
                self.assertEqual(got['category'], 'unsafe_url')
                self.assertEqual(len(transport.calls), 1)

    def test_redirect_dns_multicast_refused_before_socket(self):
        tool = load()
        calls = []
        def transport(url, method, timeout):
            calls.append(url)
            if len(calls) == 1:
                return dict(reply(302), location='http://redirect.example.com/a')
            try:
                tool.exchange(url, method, timeout)
            except ValueError:
                return {'error': 'unsafe_url'}
            except OSError:
                return {'error': 'transport_error'}
            return reply()
        answers = [(socket.AF_INET, socket.SOCK_STREAM, 6, '', ('224.0.0.1', 80))]
        with mock.patch.object(socket, 'getaddrinfo', return_value=answers), \
                mock.patch.object(socket, 'create_connection', side_effect=OSError('inert network boundary')) as connect:
            got = tool.check_url('https://example.com/a', transport=transport)
            self.assertEqual(got['category'], 'unsafe_url')
            self.assertEqual(connect.call_count, 0)

    def test_public_unicast_remains_pinned_to_validated_address(self):
        tool = load()
        for ip, url, family in [('8.8.8.8', 'http://example.com/a', socket.AF_INET),
                               ('2606:4700:4700::1111', 'http://example.com/a', socket.AF_INET6)]:
            with self.subTest(ip=ip):
                self.assertEqual(tool.validate_url('http://' + ('[' + ip + ']' if ':' in ip else ip) + '/')[1], 80)
                address = (ip, 80) if family == socket.AF_INET else (ip, 80, 0, 0)
                with mock.patch.object(socket, 'getaddrinfo', return_value=[(family, socket.SOCK_STREAM, 6, '', address)]), \
                        mock.patch.object(socket, 'create_connection', return_value='inert socket') as connect:
                    connection = tool.open_public_connection(url, 1)
                    self.assertEqual(connection._create_connection(('example.com', 80), 1), 'inert socket')
                    self.assertEqual(connect.call_args.args[0], (ip, 80))

    def test_response_prefix_never_overreads(self):
        tool = load()
        class Response:
            def __init__(self):
                self.requests = []
            def read(self, size):
                self.requests.append(size)
                return b'x' * size
        response = Response()
        data = tool.read_prefix(response, 1024)
        self.assertEqual(len(data), 1024)
        self.assertEqual(sum(response.requests), 1024)


class AuditTests(unittest.TestCase):
    def check(self, transport, **kw):
        return load().check_url('https://example.com/a', transport=transport, **kw)

    def test_head_available_no_body_or_get(self):
        transport = Replies(reply())
        got = self.check(transport)
        self.assertEqual(got['category'], 'available')
        self.assertEqual(got['reason'], 'head_only_availability')
        self.assertEqual([c[1] for c in transport.calls], ['HEAD'])
        self.assertEqual(got['bytes_read'], 0)
        self.assertTrue(got['checked_at'].endswith('Z'))

    def test_missing_requires_get_confirmation(self):
        for code in [404, 410]:
            transport = Replies(reply(code), reply(code))
            got = self.check(transport)
            self.assertEqual(got['category'], 'confirmed_missing')
            self.assertEqual([c[1] for c in transport.calls], ['HEAD', 'GET'])
        self.assertEqual(self.check(Replies(reply(404), reply(200)))['category'], 'available')

    def test_inconclusive_head_one_get_and_status_categories(self):
        for status, category in [(403, 'blocked'), (429, 'rate_limited'),
                                  (500, 'server_error'), (405, 'http_error')]:
            transport = Replies(reply(status), reply(status))
            self.assertEqual(self.check(transport)['category'], category)
            self.assertEqual(len(transport.calls), 2)

    def test_challenge_and_soft_missing_are_not_available(self):
        transport = Replies(reply(403), dict(reply(), challenge=True, bytes_read=1024))
        got = self.check(transport)
        self.assertEqual(got['category'], 'challenge')
        self.assertEqual(got['bytes_read'], 1024)
        transport = Replies(reply(405), dict(reply(), soft_missing=True))
        self.assertEqual(self.check(transport)['category'], 'suspected_soft_missing')

    def test_redirect_recording_and_final_url(self):
        transport = Replies(dict(reply(301), location='/b'), reply())
        got = self.check(transport)
        self.assertEqual(got['category'], 'available')
        self.assertEqual(got['final_url'], 'https://example.com/b')
        self.assertEqual(got['redirect_chain'][0]['status'], 301)
        self.assertEqual(len(transport.calls), 2)

    def test_redirect_bound_and_loop(self):
        transport = Replies(*[dict(reply(302), location='/' + str(i)) for i in range(6)])
        self.assertEqual(self.check(transport)['category'], 'redirect_limit')
        self.assertEqual(len(transport.calls), 6)
        transport = Replies(dict(reply(302), location='/a'))
        self.assertEqual(self.check(transport)['category'], 'redirect_loop')
        self.assertEqual(len(transport.calls), 1)

    def test_redirect_safety_validates_before_transport(self):
        transport = Replies(dict(reply(302), location='http://127.0.0.1/private'))
        self.assertEqual(self.check(transport)['category'], 'unsafe_url')
        self.assertEqual(len(transport.calls), 1)

    def test_timeout_and_sanitized_transport_failures(self):
        transport = Replies(TimeoutError('unsafe arbitrary detail'))
        got = self.check(transport)
        self.assertEqual(got['category'], 'timeout')
        self.assertNotIn('arbitrary', json.dumps(got))
        for kind in ['dns_error', 'tls_error', 'transport_error']:
            got = self.check(Replies({'error': kind}))
            self.assertEqual(got['category'], kind)

    def test_deadline_prevents_request(self):
        transport = Replies(reply())
        got = self.check(transport, deadline=0)
        self.assertEqual(got['category'], 'not_checked')
        self.assertEqual(len(transport.calls), 0)

    def test_slot_expiry_is_unrequested_not_checked(self):
        tool = load()
        class ExpiredLimiter:
            @contextlib.contextmanager
            def slot(self, host, deadline):
                raise TimeoutError()
                yield
        transport = Replies(reply())
        got = self.check(transport, limiter=ExpiredLimiter())
        self.assertEqual(len(transport.calls), 0)
        self.assertEqual(got['category'], 'not_checked')
        self.assertEqual(got['attempts'], [])

    def test_prefix_detection_conservative(self):
        tool = load()
        self.assertEqual(tool.inspect_prefix(b'<title>Just a moment...</title> cf-chl-', 'text/html'), (True, False))
        self.assertEqual(tool.inspect_prefix(b'<title>404 Not Found</title>', 'text/html'), (False, True))
        self.assertEqual(tool.inspect_prefix(b'%PDF- normal', 'application/pdf'), (False, False))


class TransportTests(unittest.TestCase):
    def test_head_and_get_headers_no_cookies_no_auth_no_head_reads(self):
        tool = load()
        observed = []
        class Response:
            status = 200
            def getheader(self, name, default=None):
                return 'application/pdf' if name == 'Content-Type' else default
            def read(self, size):
                observed.append(('read', size))
                return b'x' * size
        class Connection:
            def request(self, method, target, headers):
                observed.append((method, target, headers))
            def getresponse(self):
                return Response()
            def close(self):
                pass
        for method in ['HEAD', 'GET']:
            observed.clear()
            with mock.patch.object(tool, 'open_public_connection', return_value=Connection()):
                result = tool.exchange('https://example.com/P?q=%2f', method, 1)
            request = observed[0]
            self.assertEqual(request[1], '/P?q=%2f')
            self.assertNotIn('Cookie', request[2])
            self.assertNotIn('Authorization', request[2])
            if method == 'HEAD':
                self.assertEqual(len(observed), 1)
                self.assertEqual(result['bytes_read'], 0)
            else:
                self.assertEqual(request[2]['Range'], 'bytes=0-1023')
                self.assertEqual(observed[1], ('read', 1024))
                self.assertEqual(result['bytes_read'], 1024)

    def test_transport_uses_bounded_child_and_timeout_is_sanitized(self):
        tool = load()
        with mock.patch.object(subprocess, 'run', side_effect=subprocess.TimeoutExpired(['hidden'], 1)) as run:
            result = tool.network_request('https://example.com/a', 'GET', 0.5)
        self.assertEqual(result, {'error': 'timeout'})
        self.assertEqual(run.call_args.kwargs['timeout'], 0.5)
        self.assertNotIn('shell', run.call_args.kwargs)

    def test_limiter_enforces_same_host_interval(self):
        tool = load()
        import time
        limiter = tool.HostLimiter(per_host=1, interval=0.02)
        ticks = []
        for i in range(3):
            with limiter.slot('example.com', time.monotonic() + 1):
                ticks.append(time.monotonic())
        self.assertGreaterEqual(ticks[1] - ticks[0], 0.018)
        self.assertGreaterEqual(ticks[2] - ticks[1], 0.018)


class CheckpointTests(unittest.TestCase):
    def test_manifest_rows_summary_unique_counts_and_existing_refusal(self):
        tool = load()
        items = {'occurrences': 3, 'input_sha256': {}, 'urls': [
            {'url': 'https://example.com/a', 'references': []},
            {'url': 'https://example.com/b', 'references': []}]}
        with tempfile.TemporaryDirectory() as directory:
            out = pathlib.Path(directory) / 'audit'
            summary = tool.run_audit(items, out, workers=2, max_duration=10,
                                     checker=lambda u, **kw: dict(url=u, category='available', checked_at='now'))
            rows = [json.loads(s) for s in (out / 'results.jsonl').read_text().splitlines()]
            self.assertEqual(len(rows), 2)
            self.assertTrue(summary['complete'])
            self.assertEqual(summary['checked'], 2)
            self.assertEqual(summary['target'], 2)
            self.assertEqual(summary['categories'], {'available': 2})
            self.assertEqual(json.loads((out / 'inventory.json').read_text())['occurrences'], 3)
            self.assertTrue((out / 'manifest.json').exists())
            self.assertTrue((out / 'progress.json').exists())
            with self.assertRaises(FileExistsError):
                tool.run_audit(items, out)

    def test_cutoff_reconciles_every_pending_row(self):
        tool = load()
        items = {'occurrences': 2, 'input_sha256': {}, 'urls': [
            {'url': 'https://example.com/a', 'references': []},
            {'url': 'https://example.com/b', 'references': []}]}
        with tempfile.TemporaryDirectory() as directory:
            out = pathlib.Path(directory) / 'audit'
            summary = tool.run_audit(items, out, max_duration=0,
                                     checker=lambda *a, **k: self.fail('must not request'))
            self.assertFalse(summary['complete'])
            self.assertEqual(summary['not_checked'], 2)
            self.assertEqual(summary['checked'], 0)
            self.assertEqual(len((out / 'results.jsonl').read_text().splitlines()), 2)

    def test_cli_help_and_limit_validation(self):
        got = subprocess.run([sys.executable, str(SOURCE), '--help'], capture_output=True, text=True)
        self.assertEqual(got.returncode, 0)
        self.assertIn('--output', got.stdout)
        got = subprocess.run([sys.executable, str(SOURCE), '--output', '/unused', '--workers', '9'], capture_output=True)
        self.assertNotEqual(got.returncode, 0)


if __name__ == '__main__':
    unittest.main()
