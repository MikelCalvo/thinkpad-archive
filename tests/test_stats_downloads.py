"""Download transfers are separate, public daily aggregates, never click events."""
from datetime import datetime, timedelta, timezone
import concurrent.futures
from contextlib import closing
import http.client
import json
from pathlib import Path
import socket
import sqlite3
import struct
import tempfile
import threading
import time
import unittest
import zipfile
from unittest.mock import patch

from thinkpad_archive.stats_store import AnalyticsStore, SCHEMA
from thinkpad_archive.stats_server import create_server


class DownloadCounters(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.now = datetime(2026, 10, 29, 12, tzinfo=timezone.utc)

    def store(self):
        store = AnalyticsStore(self.root / 'counts.sqlite', pages={'/en/'}, clock=lambda: self.now)
        self.addCleanup(store.close)
        return store

    def test_existing_schema_and_views_survive_separate_atomic_downloads_and_reopen(self):
        with closing(sqlite3.connect(self.root / 'counts.sqlite')) as db:
            db.execute(SCHEMA)
            db.execute('INSERT INTO counts VALUES(?,?,?,?)', ('2025-01-01', 'total', 'all', 7))
            db.commit()
        (self.root / 'counts.sqlite').chmod(0o600)
        store = self.store()
        self.assertTrue(callable(getattr(store, 'record_download', None)), 'Download counter API missing')
        old = store.export()['counts']
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
            list(pool.map(lambda _: store.record_download('0.5.6'), range(20)))
        data = store.data('all')
        self.assertEqual(data['total'], 7)
        self.assertEqual(data['downloads']['total'], 20)
        self.assertEqual(data['downloads']['versions'], [{'value': '0.5.6', 'count': 20}])
        self.assertEqual(sum(r['count'] for r in data['downloads']['daily']), 20)
        self.assertEqual([r for r in store.export()['counts'] if r['dimension'] != 'download'], old)
        before = store.export()
        for version in ('private/path', '01.5.6', '0.5.6?secret', '', None, 1):
            with self.subTest(kind=type(version).__name__), self.assertRaises(ValueError):
                store.record_download(version)
        self.assertEqual(store.export(), before)
        store.close(); store = self.store()
        self.now += timedelta(days=400)
        self.assertEqual(store.data(365)['downloads']['total'], 0)
        self.assertEqual(store.data('all')['downloads']['total'], 20)
        with closing(sqlite3.connect(self.root / 'counts.sqlite')) as db:
            self.assertEqual(db.execute("SELECT sql FROM sqlite_master WHERE name='counts'").fetchone()[0], SCHEMA)


class DownloadHTTP(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.site = self.root / 'site'; self.site.mkdir()
        (self.site / 'en').mkdir(); (self.site / 'en/index.html').write_text('<html lang="en">catalogue</html>')
        (self.site / 'index.html').write_text('<html lang="en">catalogue</html>')
        (self.site / 'downloads').mkdir()
        self.archive = self.site / 'downloads/thinkpad-archive-0.5.6-offline.zip'
        with zipfile.ZipFile(self.archive, 'w') as z:
            z.writestr('index.html', 'local archive')
        self.private = self.root / 'private'; self.private.mkdir(mode=0o700)
        self.path = '/downloads/' + self.archive.name

    def start(self, enabled=True):
        server = create_server(self.site, self.private / 'counts.sqlite', 'http://archive.example', enabled=enabled)
        thread = threading.Thread(target=server.serve_forever, kwargs={'poll_interval': .01}); thread.start()
        self.addCleanup(lambda: (server.shutdown(), server.server_close(), thread.join(3)))
        return server

    def request(self, server, path=None, method='GET', headers=()):
        with closing(http.client.HTTPConnection(*server.server_address, timeout=5)) as conn:
            conn.putrequest(method, path or self.path)
            for key, value in headers: conn.putheader(key, value)
            conn.endheaders(); response = conn.getresponse()
            return response.status, dict(response.getheaders()), response.read()

    def count(self, server):
        return json.loads(self.request(server, '/api/stats/data?days=all')[2])['downloads']['total']

    def test_real_zip_then_public_counts_without_pageview_pollution(self):
        server = self.start()
        status, headers, body = self.request(server)
        self.assertEqual(status, 200, 'Real ZIP route missing')
        self.assertEqual(body, self.archive.read_bytes())
        self.assertEqual(headers['Content-Type'], 'application/zip')
        self.assertEqual(int(headers['Content-Length']), len(body))
        until = time.monotonic() + 2
        while self.count(server) != 1 and time.monotonic() < until: time.sleep(.01)
        self.assertEqual(self.count(server), 1)
        data = json.loads(self.request(server, '/api/stats/data')[2])
        self.assertEqual(data['total'], 0)
        export = json.loads(self.request(server, '/api/stats/export.json')[2])
        self.assertEqual(len(export['counts']), 1)
        self.assertEqual({k: v for k, v in export['counts'][0].items() if k != 'day'}, {'dimension':'download','value':'0.5.6','count':1})

    def test_head_range_unknown_query_and_opt_out_never_increment(self):
        server = self.start()
        self.assertEqual(self.request(server, method='HEAD')[0], 200)
        self.assertEqual(self.request(server, headers=[('Range','bytes=0-7')])[0], 416)
        self.assertEqual(self.request(server, self.path+'?private=1')[0], 404)
        self.assertEqual(self.request(server, self.path+'.sha256')[0], 404)
        self.assertEqual(self.request(server, self.path, method='POST')[0], 405)
        for headers in [[('DNT','1')], [('DNT','0'),('DNT',' 1\t')], [('Sec-GPC','1 ')]]:
            self.assertEqual(self.request(server, headers=headers)[0], 200)
        self.assertEqual(self.count(server), 0)
        self.assertEqual(json.loads(self.request(server, '/api/stats/export.json')[2])['counts'], [])

    def test_disabled_serves_zip_without_creating_database(self):
        server = self.start(enabled=False)
        self.assertEqual(self.request(server)[0], 200)
        self.assertFalse((self.private/'counts.sqlite').exists())
        data = json.loads(self.request(server, '/api/stats/data')[2])
        self.assertFalse(data['enabled']); self.assertEqual(data['downloads']['total'], 0)

    def test_stats_proxy_routes_zip_to_counter_without_identity_headers(self):
        text = (Path(__file__).resolve().parents[1] / 'deploy/Caddyfile.stats').read_text()
        self.assertIn('@catalogueDownload', text)
        self.assertIn('path_regexp', text)
        self.assertIn('flush_interval -1', text)
        self.assertIn('header_up -Cookie', text)
        self.assertIn('header_up -User-Agent', text)

    def test_changed_or_symlinked_archive_cannot_be_read_or_counted(self):
        server = self.start()
        self.archive.unlink(); self.archive.symlink_to('/etc/passwd')
        self.assertNotEqual(self.request(server)[0], 200)
        self.assertEqual(self.count(server), 0)

    def large_archive(self):
        # A valid ZIP larger than the socket buffers makes early reset observable.
        with zipfile.ZipFile(self.archive, 'w', compression=zipfile.ZIP_STORED) as z:
            z.writestr('catalogue.html', b'x' * (16 * 1024 * 1024))

    def workers_released(self, server):
        until = time.monotonic() + 3
        while time.monotonic() < until:
            if not any(t.is_alive() for t in server._threads):
                return
            time.sleep(.01)
        self.fail('Download worker did not finish within the observation bound')

    def test_early_connection_reset_does_not_count_and_healthy_download_recovers(self):
        self.large_archive()
        server = self.start()
        with socket.create_connection((str(server.server_address[0]), int(server.server_address[1])), timeout=2) as conn:
            conn.sendall(('GET ' + self.path + ' HTTP/1.1\r\nHost: archive.example\r\n\r\n').encode())
            received = conn.recv(2048)
            self.assertIn(b'200', received.split(b'\r\n', 1)[0])
            conn.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER, struct.pack('ii', 1, 0))
        self.workers_released(server)
        self.assertEqual(self.count(server), 0)
        self.assertEqual(self.request(server)[2], self.archive.read_bytes())
        self.workers_released(server)
        self.assertEqual(self.count(server), 1)

    def test_admitted_send_has_finite_deadline_without_counting_stalled_reader(self):
        self.large_archive()
        server = self.start()
        with patch('thinkpad_archive.stats_server.DOWNLOAD_TIMEOUT', .2):
            with socket.socket() as conn:
                conn.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 1024)
                conn.settimeout(2)
                conn.connect(server.server_address)
                conn.sendall(('GET ' + self.path + ' HTTP/1.1\r\nHost: archive.example\r\n\r\n').encode())
                self.assertIn(b'200', conn.recv(512).split(b'\r\n', 1)[0])
                self.workers_released(server)
        self.assertEqual(self.count(server), 0)

    def test_persistence_failure_does_not_corrupt_already_served_zip_or_replay(self):
        server = self.start()
        with patch.object(server.store, 'record_download', side_effect=sqlite3.OperationalError('busy')) as record:
            self.assertEqual(self.request(server)[2], self.archive.read_bytes())
            until = time.monotonic()+1
            while not record.call_count and time.monotonic()<until: time.sleep(.01)
            self.assertEqual(record.call_count, 1)
        self.assertEqual(self.count(server), 0)

if __name__ == '__main__': unittest.main()
