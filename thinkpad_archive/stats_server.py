"""First-party aggregate-only HTTP API; intentionally not a static web server.

Run behind a same-origin reverse proxy. This application has no access/error
request logs. Infrastructure (proxy/hosting) logs are outside that promise.
Disabled mode creates no database and serves explicitly disabled zero data.
Limits are global to this process, never keyed by an IP, cookie or identifier.
"""
from __future__ import annotations

from datetime import datetime, timezone
from html.parser import HTMLParser
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import os
import re
import socket
import stat
from pathlib import Path
from socketserver import TCPServer, ThreadingMixIn
import sqlite3
import threading
import time
from typing import cast
from urllib.parse import urlsplit

from .stats_store import AnalyticsStore, CATEGORIES, LANG, PRIVACY, ROUTE, VERSION, empty_data, no_symlinks

MAX_WORKERS = 8
READ_TIMEOUT = 2.0
RATE_CAPACITY = 240
RATE_PER_SECOND = 60
MAX_BODY = 1024
DOWNLOAD_TIMEOUT = 30.0
MAX_DOWNLOAD = 512 * 1024 * 1024
ERRORS = {400: b"invalid request\n", 403: b"forbidden\n", 404: b"not found\n",
          405: b"method not allowed\n", 413: b"too large\n", 416: b"range not supported\n", 429: b"busy\n", 503: b"unavailable\n"}


class _RootLanguage(HTMLParser):
    language = None

    def handle_starttag(self, tag, attrs):
        if tag == 'html' and self.language is None:
            self.language = dict(attrs).get('lang')


def _routes(root):
    """Snapshot generated HTML routes; never turn user paths into file reads."""
    root = no_symlinks(root)
    if not root.is_dir():
        raise ValueError("Invalid site root")
    parser = _RootLanguage()
    with no_symlinks(root / 'index.html').open('r', encoding='utf-8') as stream:
        parser.feed(stream.read(65536))
    default = parser.language
    if not isinstance(default, str) or not LANG.fullmatch(default):
        raise ValueError("Invalid default language")
    routes = {}
    for folder, dirs, files in os.walk(root, followlinks=False):
        for name in (*dirs, *files):
            if (no_symlinks(folder) / name).is_symlink():
                raise ValueError("Unsafe site root")
        for name in files:
            if not name.endswith('.html'):
                continue
            path = '/' + (no_symlinks(folder) / name).relative_to(root).as_posix()
            if not ROUTE.fullmatch(path) or path.endswith('/stats.html'):
                continue
            routes[path] = path
    for path in tuple(routes):
        parts = path.strip('/').split('/')
        if len(parts) == 2 and parts[1] in ('index.html', 'catalogue.html'):
            canonical = '/' + parts[0] + '/'
            routes[path] = canonical
            routes[canonical] = canonical
    if '/' + default + '/' not in routes:
        raise ValueError("Missing default catalogue")
    routes['/'] = routes['/index.html'] = '/' + default + '/'
    return root, routes


def _download_files(root):
    """Snapshot only versioned generated ZIPs, never client-selected paths."""
    folder = no_symlinks(root / 'downloads')
    if not folder.exists():
        return {}
    if not folder.is_dir():
        raise ValueError('Invalid downloads folder')
    result = {}
    for path in folder.iterdir():
        match = re.fullmatch(r'thinkpad-archive-(.+)-offline\.zip', path.name)
        if not match or len(match[1]) > 64 or not VERSION.fullmatch(match[1]):
            continue
        path = no_symlinks(path)
        meta = path.stat()
        if not stat.S_ISREG(meta.st_mode) or meta.st_nlink != 1 or not 0 < meta.st_size <= MAX_DOWNLOAD:
            raise ValueError('Invalid download file')
        result['/downloads/' + path.name] = (path, match[1], (meta.st_dev, meta.st_ino, meta.st_size, meta.st_mtime_ns, meta.st_ctime_ns))
    return result


def _origin(value):
    try:
        parts = urlsplit(value)
        port = parts.port
        if (parts.scheme not in ('https', 'http') or not parts.hostname or
                parts.username is not None or parts.password is not None or
                parts.path or parts.query or parts.fragment or
                value != parts.scheme + '://' + parts.netloc or
                any(ord(c) < 33 or ord(c) > 126 for c in value)):
            raise ValueError
        if port is not None and not 0 < port < 65536:
            raise ValueError
    except (ValueError, TypeError):
        raise ValueError("Invalid public origin") from None
    return value


class _Server(ThreadingMixIn, HTTPServer):
    daemon_threads = False
    block_on_close = True
    allow_reuse_address = True
    request_queue_size = 16

    def __init__(self, address, *, store, routes, downloads, origin, clock):
        self.downloads = downloads
        self.store = store
        self.routes = routes
        self.origin = origin
        self.clock = clock
        self.read_timeout = READ_TIMEOUT
        self._workers = threading.BoundedSemaphore(MAX_WORKERS)
        self._rate_lock = threading.Lock()
        self._capacity = RATE_CAPACITY
        self._refill = RATE_PER_SECOND
        self._tokens = float(self._capacity)
        self._last = time.monotonic()
        super().__init__(address, _Handler)

    def server_bind(self):
        # HTTPServer.server_bind calls getfqdn; no reverse DNS is needed here.
        TCPServer.server_bind(self)
        self.server_name = 'analytics'
        self.server_port = self.server_address[1]

    def allowed(self):
        with self._rate_lock:
            now = time.monotonic()
            self._tokens = min(self._capacity, self._tokens + (now - self._last) * self._refill)
            self._last = now
            if self._tokens < 1:
                return False
            self._tokens -= 1
            return True

    def process_request(self, request, client_address):
        request = cast(socket.socket, request)
        if not self._workers.acquire(blocking=False):
            try:
                request.settimeout(0.1)
                request.sendall(b"HTTP/1.1 429 Too Many Requests\r\nCache-Control: no-store\r\nX-Content-Type-Options: nosniff\r\nContent-Type: text/plain; charset=utf-8\r\nContent-Length: 5\r\nConnection: close\r\n\r\nbusy\n")
                request.shutdown(socket.SHUT_WR)
                # Avoid resetting a client still sending its bounded body.
                # No parsing or retention; both bytes and elapsed time are capped.
                until = time.monotonic() + 0.05
                remaining = 8192
                while remaining and time.monotonic() < until:
                    request.settimeout(max(0.001, until - time.monotonic()))
                    chunk = request.recv(min(remaining, 4096))
                    if not chunk:
                        break
                    remaining -= len(chunk)
            except OSError:
                pass
            self.shutdown_request(request)
            return
        try:
            super().process_request(request, client_address)
        except BaseException:
            self._workers.release()
            raise

    def process_request_thread(self, request, client_address):
        try:
            super().process_request_thread(request, client_address)
        finally:
            self._workers.release()

    def handle_error(self, request, client_address):
        # Never print tracebacks, request headers, paths or peer addresses.
        pass

    def server_close(self):
        super().server_close()
        if self.store is not None:
            self.store.close()


class _Handler(BaseHTTPRequestHandler):
    # The stdlib request handler stores BaseServer; this class is constructed
    # exclusively by _Server, which supplies the narrower service state.
    server: _Server  # type: ignore[assignment]
    protocol_version = 'HTTP/1.1'

    def setup(self):
        self.request.settimeout(self.server.read_timeout)
        # An absolute connection deadline also bounds slow trickle reads.
        self._deadline = threading.Timer(self.server.read_timeout, self._expire)
        self._deadline.daemon = True
        self._deadline.start()
        super().setup()

    def _expire(self):
        try:
            self.request.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass

    def finish(self):
        self._deadline.cancel()
        super().finish()

    def log_message(self, format, *args):
        pass

    def send_error(self, code, message=None, explain=None):
        self._reply(code if code in ERRORS else 400)

    def _reply(self, code, body=None):
        self.close_connection = True
        if body is None:
            body = ERRORS.get(code, b'')
        kind = 'text/plain; charset=utf-8'
        if isinstance(body, dict):
            body = json.dumps(body, ensure_ascii=True, separators=(',', ':')).encode('ascii')
            kind = 'application/json; charset=utf-8'
        self.send_response_only(code)
        self.send_header('Content-Type', kind)
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Connection', 'close')
        self.end_headers()
        if self.command != 'HEAD':
            self.wfile.write(body)

    def _dispatch(self):
        if not self.server.allowed():
            return self._reply(429)
        try:
            return self._route()
        except (OSError, sqlite3.Error):
            return self._reply(503)
        except (ValueError, TypeError, RecursionError):
            return self._reply(400)
        except Exception:
            # Refuse without leaking internal exception text.
            return self._reply(503)

    def _route(self):
        if self.path.startswith('/downloads/'):
            if self.path not in self.server.downloads:
                return self._reply(404)
            if self.command not in ('GET', 'HEAD'):
                return self._reply(405)
            return self._download()
        if self.path == '/api/stats/pageview':
            if self.command != 'POST':
                return self._reply(405)
            return self._pageview()
        if self.command != 'GET':
            return self._reply(405)
        if self.path == '/api/stats/health':
            if self.server.store is None:
                return self._reply(503)
            self.server.store.data(7)
            return self._reply(200, {'ready': True})
        if self.path == '/api/stats/export.json':
            if self.server.store is None:
                return self._reply(200, {'privacy': dict(PRIVACY), 'counts': []})
            return self._reply(200, self.server.store.export())
        if self.path == '/api/stats/data' or self.path.startswith('/api/stats/data?'):
            match = re.fullmatch(r'/api/stats/data(?:\?days=(7|30|90|365|all))?', self.path)
            if not match:
                return self._reply(400)
            days = 'all' if match.group(1) == 'all' else int(match.group(1) or 30)
            if self.server.store is None:
                today = self.server.clock().astimezone(timezone.utc).date()
                return self._reply(200, empty_data(days, today, enabled=False))
            return self._reply(200, self.server.store.data(days))
        return self._reply(404)

    def _download(self):
        if self.headers.get_all('Range'):
            return self._reply(416)
        path, version, expected = self.server.downloads[self.path]
        no_symlinks(path)
        with os.fdopen(os.open(path, os.O_RDONLY | os.O_NOFOLLOW), 'rb') as stream:
            meta = os.fstat(stream.fileno())
            identity = (meta.st_dev, meta.st_ino, meta.st_size, meta.st_mtime_ns, meta.st_ctime_ns)
            if not stat.S_ISREG(meta.st_mode) or meta.st_nlink != 1 or identity != expected:
                return self._reply(503)
            self.close_connection = True
            # Retain API/slow-header deadlines; only an admitted ZIP transfer
            # receives this separate, finite absolute body-send allowance.
            self._deadline.cancel()
            self._deadline = threading.Timer(DOWNLOAD_TIMEOUT, self._expire)
            self._deadline.daemon = True
            self._deadline.start()
            try:
                self.send_response_only(200)
                self.send_header('Content-Type', 'application/zip')
                self.send_header('Content-Length', str(meta.st_size))
                self.send_header('Content-Disposition', 'attachment; filename="' + path.name + '"')
                self.send_header('Cache-Control', 'no-store')
                self.send_header('X-Content-Type-Options', 'nosniff')
                self.send_header('Connection', 'close')
                self.end_headers()
                if self.command == 'HEAD':
                    return
                remaining = meta.st_size
                while remaining:
                    chunk = stream.read(min(65536, remaining))
                    if not chunk:
                        return
                    self.wfile.write(chunk)
                    remaining -= len(chunk)
                self.wfile.flush()
            except OSError:
                # Headers may already be sent. Never emit a second HTTP reply.
                return
            finally:
                self._deadline.cancel()
        opted_out = any(value.strip(' \t') == '1' for name in ('DNT', 'Sec-GPC')
                        for value in self.headers.get_all(name, []))
        if self.server.store is not None and not opted_out:
            try:
                self.server.store.record_download(version)
            except (OSError, sqlite3.Error):
                # Download already delivered: no retries or deceptive failure.
                pass

    def _pageview(self):
        if self.server.store is None:
            return self._reply(503)
        origins = self.headers.get_all('Origin', [])
        if origins != [self.server.origin]:
            return self._reply(403 if len(origins) < 2 else 400)
        lengths = self.headers.get_all('Content-Length', [])
        if (self.headers.get_all('Transfer-Encoding') or len(lengths) != 1 or
                not re.fullmatch(r'[0-9]{1,10}', lengths[0])):
            return self._reply(400)
        length = int(lengths[0])
        if length > MAX_BODY:
            return self._reply(413)
        types = self.headers.get_all('Content-Type', [])
        if len(types) != 1 or types[0].lower() not in ('application/json', 'application/json; charset=utf-8'):
            return self._reply(400)
        if any(value.strip(' \t') == '1' for name in ('DNT', 'Sec-GPC')
               for value in self.headers.get_all(name, [])):
            return self._reply(204)
        raw = self.rfile.read(length)
        if len(raw) != length:
            return self._reply(400)

        def unique(pairs):
            obj = {}
            for key, value in pairs:
                if key in obj:
                    raise ValueError('Invalid pageview')
                obj[key] = value
            return obj

        event = json.loads(raw.decode('utf-8'), object_pairs_hook=unique)
        fields = {'path', 'source', 'device', 'browser', 'system'}
        if type(event) is not dict or set(event) != fields or any(type(v) is not str for v in event.values()):
            return self._reply(400)
        path = event['path']
        if path not in self.server.routes or any(event[key] not in values for key, values in CATEGORIES.items()):
            return self._reply(400)
        self.server.store.record_pageview(self.server.routes[path], event['source'], event['device'], event['browser'], event['system'])
        return self._reply(204)

    do_GET = do_POST = do_HEAD = do_OPTIONS = do_PUT = do_DELETE = do_PATCH = do_TRACE = _dispatch


def create_server(site_root, database, origin, *, host='127.0.0.1', port=0,
                  enabled=False, clock=None):
    """Return a bounded server; no IO occurs merely by importing this module.

    The database parent must already exist with mode 0700, owned by the
    service user. Neither the DB nor its path components may be symlinks.
    """
    try:
        socket.inet_pton(socket.AF_INET, host)
    except (OSError, TypeError):
        raise ValueError('Listen address must be numeric IPv4') from None
    origin = _origin(origin)
    root, routes = _routes(site_root)
    downloads = _download_files(root)
    database = no_symlinks(database)
    if database == root or database.is_relative_to(root):
        raise ValueError('Database must be outside public root')
    clock = clock or (lambda: datetime.now(timezone.utc))
    store = AnalyticsStore(database, pages=set(routes.values()), clock=clock) if enabled else None
    try:
        return _Server((host, port), store=store, routes=routes, downloads=downloads, origin=origin, clock=clock)
    except BaseException:
        if store is not None:
            store.close()
        raise


def main(argv=None):
    """Explicit opt-in CLI with fixed diagnostics and graceful shutdown."""
    import argparse
    import signal
    import sys

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--site-root', required=True)
    parser.add_argument('--database', required=True)
    parser.add_argument('--origin', required=True)
    parser.add_argument('--listen', default='127.0.0.1')
    parser.add_argument('--port', type=int, default=8080)
    parser.add_argument('--enabled', action='store_true')
    args = parser.parse_args(argv)
    try:
        server = create_server(args.site_root, args.database, args.origin,
                               host=args.listen, port=args.port, enabled=args.enabled)
    except (OSError, ValueError, sqlite3.Error):
        print('Analytics service unavailable', file=sys.stderr)
        return 1
    stopped = threading.Event()

    def stop(signum, frame):
        if not stopped.is_set():
            stopped.set()
            threading.Thread(target=server.shutdown, daemon=True).start()

    previous = {sig: signal.signal(sig, stop) for sig in (signal.SIGTERM, signal.SIGINT)}
    try:
        server.serve_forever(poll_interval=0.1)
    finally:
        server.server_close()
        for sig, handler in previous.items():
            signal.signal(sig, handler)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
