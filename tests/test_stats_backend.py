"""Real loopback and durable-storage tests for aggregate-only analytics."""
from __future__ import annotations

import importlib.util
import concurrent.futures
from contextlib import closing, redirect_stderr, redirect_stdout
import http.client
import io
import socket
import threading
import time
from unittest.mock import patch
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest


class StorageTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        self.db = self.folder / "counters.sqlite3"
        self.now = datetime(2026, 10, 29, 12, tzinfo=timezone.utc)
        self.pages = ("/en/", "/es/", "/es/models/x230.html")

    def store(self):
        from thinkpad_archive.stats_store import AnalyticsStore
        store = AnalyticsStore(self.db, pages=self.pages, clock=lambda: self.now)
        self.addCleanup(store.close)
        return store

    def event(self, store, path="/es/models/x230.html"):
        store.record_pageview(path, "github", "desktop", "firefox", "linux")

    def test_empty_zero_schema_and_complete_public_export(self):
        store = self.store()
        data = store.data(7)
        self.assertEqual(data["total"], 0)
        self.assertEqual(data["daily"], [
            {"day": (self.now.date() - timedelta(days=i)).isoformat(), "count": 0}
            for i in reversed(range(7))])
        self.assertEqual(store.export()["counts"], [])
        self.event(store)
        export = store.export()
        with closing(sqlite3.connect(self.db)) as db:
            self.assertEqual(db.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall(), [("counts",)])
            self.assertEqual([r[1] for r in db.execute("PRAGMA table_info(counts)")], ["day", "dimension", "value", "count"])
            sql_rows = [dict(zip(("day", "dimension", "value", "count"), row)) for row in db.execute("SELECT day, dimension, value, count FROM counts ORDER BY day, dimension, value")]
        self.assertEqual(export["counts"], sql_rows)
        self.assertEqual(len(sql_rows), 7)
        self.assertEqual({row["dimension"] for row in sql_rows}, {"total", "page", "source", "device", "browser", "system", "language"})
        data = store.data(7)
        self.assertEqual(data["total"], 1)
        self.assertEqual(data["pages"], [{"value": "/es/models/x230.html", "count": 1}])
        self.assertEqual(data["languages"], [{"value": "es", "count": 1}])
        self.assertEqual(export["privacy"], data["privacy"])
        self.assertEqual(data["privacy"], {"storage": "daily_marginal_counters", "retention_days": None, "timezone": "UTC", "unique_visitors": False, "no_cookies": True, "no_identifiers": True, "geo": False})
        self.assertEqual(self.db.stat().st_mode & 0o777, 0o600)

    def test_atomic_parallel_increments_and_reopen(self):
        store = self.store()
        with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
            list(pool.map(lambda _: self.event(store), range(80)))
        store.close()
        reopened = self.store()
        self.assertEqual(reopened.data(30)["total"], 80)
        self.assertEqual({row["count"] for row in reopened.export()["counts"]}, {80})

    def test_indefinite_retention_at_startup_read_and_write(self):
        store = self.store()
        self.event(store)
        first_day = self.now.date().isoformat()
        self.now += timedelta(days=400)
        self.assertEqual(len(store.export()["counts"]), 7)
        self.assertEqual(store.data(365)["total"], 0)
        self.event(store, "/en/")
        self.assertEqual(len(store.export()["counts"]), 14)
        store.close()
        self.now += timedelta(days=800)
        reopened = self.store()
        self.assertEqual(len(reopened.export()["counts"]), 14)
        data = reopened.data('all')
        self.assertEqual(data['total'], 2)
        self.assertEqual(data['window'], {'days': 'all', 'from': first_day, 'to': self.now.date().isoformat()})
        self.assertEqual(len(data['daily']), 1201)
        self.assertEqual(sum(row['count'] for row in data['daily']), 2)
        self.assertEqual(reopened.data(7)["total"], 0)

    def test_all_time_empty_and_clock_rollback_preserve_history(self):
        store = self.store()
        empty = store.data('all')
        self.assertEqual(empty['window'], {'days': 'all', 'from': self.now.date().isoformat(), 'to': self.now.date().isoformat()})
        self.assertEqual(empty['daily'], [{'day': self.now.date().isoformat(), 'count': 0}])
        self.event(store)
        before = store.export()['counts']
        self.now -= timedelta(days=1)
        self.assertEqual(store.data('all')['total'], 0)
        self.assertEqual(store.export()['counts'], before)
        self.now += timedelta(days=10000)
        self.assertEqual(store.data('all')['total'], 1)
        self.assertEqual(store.export()['counts'], before)

    def test_utc_day_windows_sorting_and_atomic_refusal(self):
        store = self.store()
        self.now = datetime(2026, 10, 30, 0, 30, tzinfo=timezone(timedelta(hours=2)))
        self.event(store, "/en/")
        self.event(store, "/es/")
        self.event(store, "/es/")
        data = store.data(30)
        self.assertEqual(data["window"]["to"], "2026-10-29")
        self.assertEqual(data["pages"], [{"value": "/es/", "count": 2}, {"value": "/en/", "count": 1}])
        before = store.export()
        with self.assertRaises(ValueError):
            store.record_pageview("/en/", "unknown-domain", "desktop", "firefox", "linux")
        with self.assertRaises(ValueError):
            self.event(store, "/en/private.html")
        for days in (0, 1, 366, True, "30"):
            with self.assertRaises(ValueError):
                store.data(days)
        self.assertEqual(store.export(), before)

    def test_concurrent_store_handles_share_atomic_counts(self):
        first = self.store()
        second = self.store()
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
            list(pool.map(lambda n: self.event(first if n % 2 else second), range(40)))
        self.assertEqual(first.data(30)["total"], 40)
        self.assertEqual(second.data(30)["total"], 40)

    def test_each_refusal_is_atomic_and_all_marginals_balance(self):
        store = self.store()
        self.event(store)
        original = store.export()
        cases = (
            ("/en/unknown.html", "github", "desktop", "firefox", "linux"),
            ("/en/", "unknown", "desktop", "firefox", "linux"),
            ("/en/", "github", "unknown-device", "firefox", "linux"),
            ("/en/", "github", "desktop", "unknown-browser", "linux"),
            ("/en/", "github", "desktop", "firefox", "unknown-system"),
        )
        for index, fields in enumerate(cases):
            with self.subTest(case=index), self.assertRaises(ValueError):
                store.record_pageview(*fields)
            self.assertEqual(store.export(), original)
        with closing(sqlite3.connect(self.db)) as db:
            totals = db.execute("SELECT dimension,sum(count) FROM counts GROUP BY dimension").fetchall()
        self.assertEqual(len(totals), 7)
        self.assertEqual({total for _, total in totals}, {1})

    def test_no_hidden_tail_all_window_buckets_and_tie_order(self):
        from thinkpad_archive.stats_store import AnalyticsStore
        pages = ["/en/models/m" + str(i) + ".html" for i in range(40)]
        store = AnalyticsStore(self.db, pages=pages, clock=lambda: self.now)
        self.addCleanup(store.close)
        for page in reversed(pages):
            self.event(store, page)
        data = store.data(30)
        self.assertEqual(data['total'], 40)
        self.assertEqual(data['pages'], [{'value': page, 'count': 1} for page in sorted(pages)])
        self.assertEqual(len([row for row in store.export()['counts'] if row['dimension'] == 'page']), 40)

    def test_database_file_sidecar_hardlink_and_public_mode_refusal(self):
        from thinkpad_archive.stats_store import AnalyticsStore
        target = self.folder / 'target'
        target.write_bytes(b'')
        self.db.symlink_to(target)
        with self.assertRaises(ValueError):
            self.store()
        self.db.unlink()
        target.chmod(0o600)
        self.db.hardlink_to(target)
        with self.assertRaises(ValueError):
            self.store()
        self.db.unlink()
        self.db.write_bytes(b'')
        self.db.chmod(0o644)
        with self.assertRaises(ValueError):
            self.store()
        self.db.chmod(0o600)
        for suffix in ('-wal', '-shm', '-journal'):
            side = Path(str(self.db) + suffix)
            side.symlink_to(target)
            try:
                with self.assertRaises(ValueError):
                    self.store()
            finally:
                side.unlink()

    def test_partial_upsert_failure_rolls_back_every_marginal(self):
        store = self.store()
        self.event(store)
        with closing(sqlite3.connect(self.db)) as db:
            db.execute("UPDATE counts SET count=9223372036854775807 WHERE dimension='total'")
            db.commit()
        before = store.export()
        with self.assertRaises(sqlite3.IntegrityError):
            self.event(store)
        self.assertEqual(store.export(), before)

    def test_reopen_preserves_retained_public_routes_removed_from_build(self):
        store = self.store()
        self.event(store)
        before = store.export()
        store.close()
        from thinkpad_archive.stats_store import AnalyticsStore
        updated = AnalyticsStore(self.db, pages=("/en/", "/es/"), clock=lambda: self.now)
        self.addCleanup(updated.close)
        self.assertEqual(updated.export(), before)
        with self.assertRaises(ValueError):
            self.event(updated)

    def test_reopen_refuses_invalid_persisted_dimensions(self):
        store = self.store()
        self.event(store)
        store.close()
        with closing(sqlite3.connect(self.db)) as db:
            db.execute("INSERT INTO counts(day,dimension,value,count) VALUES('2026-10-29','private','unexpected',1)")
            db.commit()
        with self.assertRaises(ValueError):
            self.store()

    def test_symlinks_private_directory_and_unknown_schema_refused(self):
        from thinkpad_archive.stats_store import AnalyticsStore
        target = self.folder / "target"
        target.mkdir(mode=0o700)
        link = self.folder / "link"
        link.symlink_to(target, target_is_directory=True)
        with self.assertRaises(ValueError):
            AnalyticsStore(link / "db", pages=self.pages)
        self.db.symlink_to(target / "db")
        with self.assertRaises(ValueError):
            self.store()
        self.db.unlink()
        with closing(sqlite3.connect(self.db)) as db:
            db.execute("CREATE TABLE events(raw TEXT)")
        with self.assertRaises(ValueError):
            self.store()
        self.db.unlink()
        target.chmod(0o755)
        with self.assertRaises(ValueError):
            AnalyticsStore(target / "db", pages=self.pages)


class HTTPTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.folder = Path(self.temp.name)
        self.site = self.folder / "public"
        self.site.mkdir()
        self.private = self.folder / "private"
        self.private.mkdir(mode=0o700)
        self.db = self.private / "stats.sqlite3"
        self.origin = "https://archive.example"
        self.now = datetime(2026, 10, 29, 12, tzinfo=timezone.utc)
        self.event = {"path": "/es/models/x230.html", "source": "github", "device": "desktop", "browser": "firefox", "system": "linux"}
        for name in ("index.html", "en/index.html", "en/catalogue.html", "es/index.html", "es/catalogue.html", "en/stats.html", "es/stats.html", "es/models/x230.html", "en/sources/thinkwiki.html", "en/years/2012.html"):
            path = self.site / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('<!doctype html><html lang="en"></html>')

    def start(self, *, enabled=True, database=None, root=None):
        from thinkpad_archive.stats_server import create_server
        server = create_server(root or self.site, database or self.db, self.origin, enabled=enabled, clock=lambda: self.now)
        thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.01})
        thread.start()
        def cleanup():
            server.shutdown()
            thread.join(3)
            server.server_close()
        self.addCleanup(cleanup)
        return server

    def request(self, server, method="GET", path="/api/stats/data", body=None, headers=None):
        connection = http.client.HTTPConnection(*server.server_address, timeout=4)
        try:
            connection.request(method, path, body=body, headers=headers or {})
            response = connection.getresponse()
            result = (response.status, dict(response.getheaders()), response.read())
        finally:
            connection.close()
        self.assertEqual(result[1].get("Cache-Control"), "no-store")
        self.assertEqual(result[1].get("X-Content-Type-Options"), "nosniff")
        self.assertNotIn("Set-Cookie", result[1])
        self.assertNotIn("Access-Control-Allow-Origin", result[1])
        return result

    def post(self, server, payload=None, headers=None, path="/api/stats/pageview"):
        actual = {"Origin": self.origin, "Content-Type": "application/json"}
        actual.update(headers or {})
        return self.request(server, "POST", path, json.dumps(self.event if payload is None else payload), actual)

    def data(self, server, days=30):
        status, _, body = self.request(server, path="/api/stats/data?days=" + str(days))
        self.assertEqual(status, 200)
        return json.loads(body)

    def test_cli_help_and_real_child_http(self):
        args = [sys.executable, "-m", "thinkpad_archive.stats_server"]
        help_result = subprocess.run(args + ["--help"], capture_output=True, timeout=5)
        self.assertEqual(help_result.returncode, 0)
        self.assertIn(b"--site-root", help_result.stdout)
        with socket.socket() as reservation:
            reservation.bind(('127.0.0.1', 0))
            port = reservation.getsockname()[1]
        child = subprocess.Popen(args + ["--site-root", str(self.site), "--database", str(self.db), "--origin", self.origin, "--listen", "127.0.0.1", "--port", str(port), "--enabled"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        statuses = []
        try:
            until = time.monotonic() + 4
            while time.monotonic() < until:
                if child.poll() is not None:
                    break
                try:
                    with closing(http.client.HTTPConnection('127.0.0.1', port, timeout=0.5)) as connection:
                        connection.request('GET', '/api/stats/health')
                        response = connection.getresponse()
                        statuses.append(response.status)
                        response.read()
                    break
                except OSError:
                    time.sleep(0.03)
            self.assertEqual(statuses, [200], "CLI did not expose a real ready HTTP server")
            with closing(http.client.HTTPConnection('127.0.0.1', port, timeout=2)) as connection:
                connection.request('POST', '/api/stats/pageview', json.dumps(self.event), {'Origin': self.origin, 'Content-Type': 'application/json'})
                response = connection.getresponse()
                self.assertEqual(response.status, 204)
                response.read()
        finally:
            child.terminate()
            stdout, stderr = child.communicate(timeout=5)
        self.assertEqual(child.returncode, 0)
        self.assertEqual(stdout, b'')
        self.assertEqual(stderr, b'')
        with closing(sqlite3.connect(self.db)) as db:
            self.assertEqual(db.execute("SELECT count FROM counts WHERE dimension='total'").fetchone()[0], 1)

    def test_live_http_empty_accept_export_sql_and_health(self):
        server = self.start()
        self.assertEqual(self.data(server)["total"], 0)
        self.assertEqual(self.post(server)[0], 204)
        data = self.data(server, 7)
        self.assertTrue(data["enabled"])
        self.assertEqual(data["total"], 1)
        self.assertEqual(data["daily"][-1], {"day": "2026-10-29", "count": 1})
        for dimension in ("pages", "sources", "devices", "browsers", "systems", "languages"):
            self.assertEqual(len(data[dimension]), 1)
        status, _, raw = self.request(server, path="/api/stats/export.json")
        self.assertEqual(status, 200)
        exported = json.loads(raw)
        with closing(sqlite3.connect(self.db)) as db:
            actual = [dict(zip(("day", "dimension", "value", "count"), row)) for row in db.execute("SELECT day,dimension,value,count FROM counts ORDER BY day,dimension,value")]
        self.assertEqual(exported["counts"], actual)
        self.assertEqual(self.request(server, path="/api/stats/health")[0], 200)
        self.assertEqual(self.data(server)["total"], 1)

    def test_http_retention_zero_days_and_all_windows(self):
        server = self.start()
        self.assertEqual(self.post(server)[0], 204)
        self.now += timedelta(days=6)
        for days in (7, 30, 90, 365):
            data = self.data(server, days)
            self.assertEqual(len(data["daily"]), days)
            self.assertEqual(data["total"], 1)
            self.assertEqual(sum(row["count"] for row in data["daily"]), 1)
            self.assertEqual(data["daily"][-1]["count"], 0)
        self.now += timedelta(days=1)
        self.assertEqual(self.data(server, 7)["total"], 0)
        self.assertEqual(self.data(server, 30)["total"], 1)
        self.now += timedelta(days=358)
        status, _, raw = self.request(server, path='/api/stats/export.json')
        self.assertEqual(status, 200)
        self.assertEqual(len(json.loads(raw)["counts"]), 7)
        status, _, raw = self.request(server, path='/api/stats/data?days=all')
        self.assertEqual(status, 200)
        lifetime = json.loads(raw)
        self.assertEqual(lifetime['total'], 1)
        self.assertEqual(lifetime['window']['days'], 'all')
        self.assertEqual(len(lifetime['daily']), 366)
        self.assertIsNone(lifetime['privacy']['retention_days'])
        self.assertEqual(self.data(server,365)['total'], 0)
        with closing(sqlite3.connect(self.db)) as db:
            self.assertEqual(db.execute('SELECT count(*) FROM counts').fetchone()[0], 7)

    def test_optout_requires_live_positive_then_no_mutation(self):
        server = self.start()
        self.assertEqual(self.post(server)[0], 204)
        before = self.request(server, path='/api/stats/export.json')[2]
        for header in ({'DNT': '1'}, {'Sec-GPC': '1'}, {'DNT': '1 '}, {'Sec-GPC': '1\t'}, {'DNT': ' \t1 \t'}):
            with self.subTest(header=header):
                self.assertEqual(self.post(server, headers=header)[0], 204)
                self.assertEqual(self.request(server, path='/api/stats/export.json')[2], before)
        self.assertEqual(self.post(server, headers={'DNT': '0', 'Sec-GPC': '0'})[0], 204)
        self.assertEqual(self.data(server)["total"], 2)

    def test_supported_three_letter_and_regional_locale_routes(self):
        for language in ('ast', 'pt-br', 'zh-hant'):
            folder = self.site / language
            folder.mkdir()
            (folder / 'index.html').write_text('<html lang="' + language + '"></html>')
            (folder / 'stats.html').write_text('<html></html>')
        server = self.start()
        for language in ('ast', 'pt-br', 'zh-hant'):
            self.assertEqual(self.post(server, {**self.event, 'path': '/' + language + '/index.html'})[0], 204)
            self.assertEqual(self.post(server, {**self.event, 'path': '/' + language + '/stats.html'})[0], 400)
        self.assertEqual(self.data(server)['languages'], [{'value': language, 'count': 1} for language in ('ast', 'pt-br', 'zh-hant')])

    def test_generated_site_allows_real_source_page_and_multiple_locales(self):
        for name in ('en/sources.html', 'fr/index.html', 'fr/stats.html', 'fr/models/x230.html'):
            path = self.site / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('<html lang="fr"></html>')
        server = self.start()
        for path in ('/en/sources.html', '/fr/', '/fr/models/x230.html'):
            self.assertEqual(self.post(server, {**self.event, 'path': path})[0], 204)
        self.assertEqual(self.post(server, {**self.event, 'path': '/fr/stats.html'})[0], 400)
        self.assertEqual(self.data(server)["languages"], [{"value": "fr", "count": 2}, {"value": "en", "count": 1}])

    def test_route_aliases_and_generated_html_allowlist(self):
        server = self.start()
        for path in ("/", "/index.html", "/en/index.html", "/en/", "/en/catalogue.html", "/es/index.html", "/es/", "/es/catalogue.html", "/en/sources/thinkwiki.html", "/en/years/2012.html"):
            self.assertEqual(self.post(server, {**self.event, "path": path})[0], 204)
        counts = {row["value"]: row["count"] for row in self.data(server)["pages"]}
        self.assertEqual(counts, {"/en/": 5, "/es/": 3, "/en/sources/thinkwiki.html": 1, "/en/years/2012.html": 1})
        root = self.folder / "spanish"
        root.mkdir()
        (root / "index.html").write_text("<html lang='es'></html>")
        (root / "es").mkdir()
        (root / "es/index.html").write_text("<html lang='es'></html>")
        other = self.start(root=root, database=self.private / "es.sqlite3")
        self.assertEqual(self.post(other, {**self.event, "path": "/"})[0], 204)
        self.assertEqual(self.data(other)["pages"], [{"value": "/es/", "count": 1}])

    def test_invalid_payloads_have_fixed_refusals_and_no_mutation(self):
        server = self.start()
        self.assertEqual(self.post(server)[0], 204)
        bad_payloads = [[], None, {}, {**self.event, "extra": "not-allowed"}, {**self.event, "language": "es"}]
        for key in self.event:
            bad_payloads.extend(({**self.event, key: 1}, {k: v for k, v in self.event.items() if k != key}))
        for path in ("/es/stats.html", "/en/stats.html", "/en/unknown.html", "/es/models/x230.html?a=1", "/es/models/x230.html#fragment", "/es/models/%7830.html", "/es/../en/index.html", "https://archive.example/es/", "//es/", "/es/models/./x230.html", "/es/models/x230.html/", "/es/models/x230.html\\x00"):
            bad_payloads.append({**self.event, "path": path})
        for key in ("source", "device", "browser", "system"):
            bad_payloads.append({**self.event, key: "not-enumerated"})
        for index, payload in enumerate(bad_payloads):
            with self.subTest(case=index):
                status, _, body = self.post(server, payload if payload is not None else "null")
                self.assertEqual(status, 400)
                self.assertEqual(body, b"invalid request\n")
        for raw in (b"{", b"null", b'[{"path":"/en/"}]', b'\xff', b'{"path":"/en/","path":"/es/","source":"direct","device":"desktop","browser":"firefox","system":"linux"}'):
            self.assertEqual(self.request(server, "POST", "/api/stats/pageview", raw, {"Origin": self.origin, "Content-Type": "application/json"})[0], 400)
        self.assertEqual(self.data(server)["total"], 1)

    def test_optouts_origin_size_content_type_and_method_boundaries(self):
        server = self.start()
        self.assertEqual(self.post(server)[0], 204)
        for header in ({"DNT": "1"}, {"Sec-GPC": "1"}, {"DNT": "0", "Sec-GPC": "1"}):
            self.assertEqual(self.post(server, headers=header)[0], 204)
        for origin in ("", "null", "https://else.example", self.origin + ".attacker.example", self.origin + "/", "https://user@archive.example"):
            self.assertEqual(self.post(server, headers={"Origin": origin})[0], 403)
        self.assertEqual(self.request(server, "POST", "/api/stats/pageview", "{}", {"Content-Type": "application/json"})[0], 403)
        for mime in ("text/plain", "application/json; charset=latin1", ""):
            self.assertEqual(self.post(server, headers={"Content-Type": mime})[0], 400)
        raw = json.dumps(self.event).encode()
        self.assertEqual(self.request(server, "POST", "/api/stats/pageview", raw + b" " * (1024 - len(raw)), {"Origin": self.origin, "Content-Type": "application/json"})[0], 204)
        self.assertEqual(self.request(server, "POST", "/api/stats/pageview", b"x" * 1025, {"Origin": self.origin, "Content-Type": "application/json"})[0], 413)
        for method in ("HEAD", "OPTIONS", "GET", "PUT", "DELETE", "PATCH", "TRACE"):
            self.assertEqual(self.request(server, method, "/api/stats/pageview")[0], 405)
        for path in ("/api/stats/pageview?x=1", "/api/stats/data?days=8", "/api/stats/data?days=30&days=7", "/api/stats/data?other=1", "/api/stats/export.json?x=1"):
            self.assertIn(self.request(server, path=path)[0], (400, 404))
        self.assertEqual(self.data(server)["total"], 2)

    def test_disabled_no_database_and_database_location_refusal(self):
        server = self.start(enabled=False)
        self.assertFalse(self.db.exists())
        data = self.data(server)
        self.assertFalse(data["enabled"])
        self.assertEqual(data["total"], 0)
        self.assertEqual(self.post(server)[0], 503)
        self.assertFalse(self.db.exists())
        from thinkpad_archive.stats_server import create_server
        with self.assertRaises(ValueError):
            create_server(self.site, self.site / "secret.sqlite3", self.origin, enabled=True)
        link = self.folder / "private-link"
        link.symlink_to(self.private, target_is_directory=True)
        with self.assertRaises(ValueError):
            create_server(self.site, link / "bad.sqlite3", self.origin, enabled=True)
        for origin in ("file://archive.example", "https://user:pass@archive.example", "https://archive.example/path", "https://archive.example?key=value"):
            with self.assertRaises(ValueError):
                create_server(self.site, self.db, origin)

    def test_private_canary_not_in_storage_public_data_or_application_logs(self):
        import secrets
        canary = "private-" + secrets.token_hex(20)
        server = self.start()
        output = io.StringIO()
        with redirect_stdout(output), redirect_stderr(output):
            headers = {"User-Agent": canary, "Referer": "https://private.invalid/" + canary, "X-Forwarded-For": canary, "Forwarded": canary, "Cookie": canary}
            accepted = self.post(server, headers=headers)
            rejected = self.post(server, {**self.event, "path": "/" + canary})
            malformed = self.request(server, "GET", "/" + canary)
            public = self.request(server, path="/api/stats/export.json")
            with socket.create_connection(server.server_address, timeout=2) as sock:
                sock.sendall(("BROKEN " + canary + "\r\n\r\n").encode())
                raw_error = sock.recv(4096)
        self.assertEqual(accepted[0], 204)
        self.assertEqual(rejected[0], 400)
        self.assertEqual(malformed[0], 404)
        sinks = [output.getvalue().encode(), accepted[2], rejected[2], malformed[2], public[2], raw_error]
        sinks.extend(path.read_bytes() for path in self.private.iterdir() if path.is_file())
        self.assertFalse(any(canary.encode() in sink for sink in sinks), "private canary escaped")
        self.assertEqual(output.getvalue(), "")
        self.assertEqual(self.data(server)["total"], 1)

    def test_global_rate_has_no_forwarding_identity_and_recovers(self):
        with patch("thinkpad_archive.stats_server.RATE_CAPACITY", 2), patch("thinkpad_archive.stats_server.RATE_PER_SECOND", 0):
            server = self.start()
        self.assertEqual(self.post(server, headers={"X-Forwarded-For": "192.0.2.1"})[0], 204)
        self.assertEqual(self.post(server, headers={"X-Forwarded-For": "192.0.2.2"})[0], 204)
        status, _, body = self.post(server, headers={"X-Forwarded-For": "192.0.2.3"})
        self.assertEqual(status, 429)
        self.assertEqual(body, b"busy\n")
        with closing(sqlite3.connect(self.db)) as db:
            self.assertEqual(db.execute("SELECT count FROM counts WHERE dimension='total'").fetchone()[0], 2)
        with patch("thinkpad_archive.stats_server.RATE_CAPACITY", 1), patch("thinkpad_archive.stats_server.RATE_PER_SECOND", 20):
            other = self.start(database=self.private / "rate.sqlite3")
        self.assertEqual(self.post(other)[0], 204)
        time.sleep(0.08)
        self.assertEqual(self.post(other)[0], 204)

    def test_bounded_workers_socket_deadline_and_bad_framing(self):
        with patch("thinkpad_archive.stats_server.MAX_WORKERS", 2), patch("thinkpad_archive.stats_server.READ_TIMEOUT", 0.35):
            server = self.start()
        sockets = []
        try:
            for _ in range(2):
                sock = socket.create_connection(server.server_address, timeout=2)
                sock.sendall(b"POST /api/stats/pageview HTTP/1.1\r\n")
                sockets.append(sock)
            time.sleep(0.04)
            self.assertEqual(self.post(server)[0], 429)
            time.sleep(0.4)
            self.assertEqual(self.post(server)[0], 204)
        finally:
            for sock in sockets:
                sock.close()
        # Separate framing validation from the deliberately saturated server;
        # a response can arrive just before its worker releases its slot.
        server = self.start(database=self.private / 'framing.sqlite3')
        probes = (
            b"Content-Length: 0\r\nContent-Length: 2\r\n",
            b"Transfer-Encoding: chunked\r\n",
            b"Content-Length: -1\r\n",
            b"Content-Length: garbage\r\n",
            b"Content-Length: 2\r\nOrigin: https://archive.example\r\n",
        )
        for framing in probes:
            with socket.create_connection(server.server_address, timeout=2) as sock:
                request = b"POST /api/stats/pageview HTTP/1.1\r\nHost: archive.example\r\nOrigin: https://archive.example\r\nContent-Type: application/json\r\n" + framing + b"Connection: close\r\n\r\n{}"
                sock.sendall(request)
                response = sock.makefile("rb")
                status = response.readline()
                self.assertTrue(b" 400 " in status, "ambiguous framing was not refused")
                response.close()
        self.assertEqual(self.data(server)["total"], 0)

    def test_body_absolute_deadline_and_incomplete_body_never_write(self):
        with patch('thinkpad_archive.stats_server.READ_TIMEOUT', 0.25):
            server = self.start()
        raw = json.dumps(self.event).encode()
        head = ("POST /api/stats/pageview HTTP/1.1\r\nHost: archive.example\r\nOrigin: " + self.origin + "\r\nContent-Type: application/json\r\nContent-Length: " + str(len(raw)) + "\r\n\r\n").encode()
        started = time.monotonic()
        with socket.create_connection(server.server_address, timeout=2) as sock:
            sock.sendall(head + raw[:1])
            for _ in range(10):
                try:
                    sock.sendall(b' ')
                except OSError:
                    break
                time.sleep(0.04)
            received = b''
            try:
                received = sock.recv(4096)
            except OSError:
                pass
        self.assertLess(time.monotonic() - started, 1)
        self.assertNotIn(b' 204 ', received)
        self.assertEqual(self.data(server)['total'], 0)
        self.assertEqual(self.post(server)[0], 204)

    def test_hostname_listen_is_refused_without_outbound_resolution(self):
        from thinkpad_archive.stats_server import create_server
        created = None
        try:
            with self.assertRaises(ValueError):
                created = create_server(self.site, self.db, self.origin, host='localhost')
        finally:
            if created is not None:
                created.server_close()

    def test_server_creation_never_resolves_hostnames(self):
        lookups = []
        def blocked(*args, **kwargs):
            lookups.append(1)
            raise OSError('name lookup blocked')
        server = None
        with patch.object(socket, 'getfqdn', blocked):
            try:
                server = self.start()
            except OSError:
                pass
        self.assertEqual(len(lookups), 0, 'server construction attempted a hostname lookup')
        self.assertIsNotNone(server)
        self.assertEqual(self.request(server, path='/api/stats/health')[0], 200)

    def test_symlinked_root_document_rejected_before_reading_target(self):
        from thinkpad_archive.stats_server import create_server
        target = self.folder / 'root-target.html'
        target.write_text('<html lang="en"></html>')
        index = self.site / 'index.html'
        index.unlink()
        index.symlink_to(target)
        original = Path.open
        observed = []
        def tracked(path, *args, **kwargs):
            observed.append(path == index)
            return original(path, *args, **kwargs)
        with patch.object(Path, 'open', tracked), self.assertRaises(ValueError):
            create_server(self.site, self.db, self.origin, enabled=True)
        self.assertFalse(any(observed), 'symlinked root document was opened before refusal')

    def test_symlinked_site_pages_refused(self):
        from thinkpad_archive.stats_server import create_server
        target = self.folder / 'private.html'
        target.write_text('<html></html>')
        (self.site / 'en/private.html').symlink_to(target)
        with self.assertRaises(ValueError):
            create_server(self.site, self.db, self.origin, enabled=True)
        self.assertFalse(self.db.exists())

    def test_parallel_http_persistence_and_database_lock_unavailability(self):
        server = self.start()
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
            statuses = list(pool.map(lambda _: self.post(server)[0], range(24)))
        self.assertEqual(statuses, [204] * 24)
        self.assertEqual(self.data(server)["total"], 24)
        with closing(sqlite3.connect(self.db)) as db:
            db.execute("BEGIN IMMEDIATE")
            start = time.monotonic()
            status, _, body = self.post(server)
            self.assertEqual(status, 503)
            self.assertEqual(body, b"unavailable\n")
            self.assertLess(time.monotonic() - start, 2)
            db.rollback()
        self.assertEqual(self.data(server)["total"], 24)
        other = self.start(database=self.db)
        self.assertEqual(self.data(other)["total"], 24)


class BackendAPITests(unittest.TestCase):
    def test_import_has_no_database_or_network_side_effect(self):
        code = '''
import sys
calls = []
def guard(event, args):
    if event == "sqlite3.connect" or event in ("socket.connect", "socket.bind", "socket.getaddrinfo", "socket.gethostbyaddr"):
        calls.append(1)
        raise RuntimeError("forbidden import side effect")
sys.addaudithook(guard)
import thinkpad_archive.stats_store
import thinkpad_archive.stats_server
assert len(calls) == 0
print("import-side-effects=0")
'''
        result = subprocess.run([sys.executable, '-c', code], capture_output=True, timeout=5)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout, b'import-side-effects=0\n')
        self.assertEqual(result.stderr, b'')

    def test_explicit_backend_api_exists(self):
        for name in ("stats_store", "stats_server"):
            spec = importlib.util.find_spec("thinkpad_archive." + name)
            self.assertIsNotNone(spec, "analytics backend module is missing")
        from thinkpad_archive.stats_store import AnalyticsStore
        from thinkpad_archive.stats_server import create_server
        self.assertTrue(callable(AnalyticsStore))
        self.assertTrue(callable(create_server))


if __name__ == "__main__":
    unittest.main()
