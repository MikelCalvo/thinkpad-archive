#!/usr/bin/env python3
"""Opt-in, metadata-only availability audit; never a package/compatibility check.

Only explicit CLI execution performs IO. Network requests use disposable child
processes so DNS, TLS, headers and body reads share one hard wall-clock budget.
No proxies, cookies, authentication or automatic redirects are used. A successful
HEAD is only availability evidence; no file identity is inferred.
"""
import argparse
import collections
import concurrent.futures
import contextlib
import datetime
import hashlib
import http.client
import ipaddress
import json
import os
from pathlib import Path
import re
import socket
import ssl
import subprocess
import sys
import threading
import time
from urllib.parse import urljoin, urlsplit

REDIRECTS = {301, 302, 303, 307, 308}
ERRORS = {'timeout', 'dns_error', 'tls_error', 'transport_error', 'unsafe_url'}


def utcnow():
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec='milliseconds').replace('+00:00', 'Z')


def inventory(root, files):
    """Bind every HTTP(S) string to its exact RFC6901 pointer; strip only #."""
    root = Path(root).resolve()
    urls = {}
    hashes = {}
    count = 0

    def visit(value, filename, pointer=''):
        nonlocal count
        if isinstance(value, dict):
            for key, child in value.items():
                visit(child, filename, pointer + '/' + key.replace('~', '~0').replace('/', '~1'))
        elif isinstance(value, list):
            for index, child in enumerate(value):
                visit(child, filename, pointer + '/' + str(index))
        elif isinstance(value, str) and value.lower().startswith(('http://', 'https://')):
            # Refuse before writing anything: never archive credentials from inputs.
            parsed = urlsplit(value)
            if parsed.username is not None or parsed.password is not None:
                raise ValueError('credentials in input URL; inventory refused')
            key = value.split('#', 1)[0]
            urls.setdefault(key, []).append({'file': filename, 'pointer': pointer, 'url': value})
            count += 1

    for name in sorted(files):
        path = (root / name).resolve()
        if not path.is_relative_to(root):
            raise ValueError('input outside source directory')
        raw = path.read_bytes()
        hashes[name] = hashlib.sha256(raw).hexdigest()
        visit(json.loads(raw), name)
    return {'occurrences': count, 'input_sha256': hashes,
            'urls': [{'url': key, 'references': refs} for key, refs in urls.items()]}


def is_public_unicast(address):
    # is_global alone also accepts multicast, including link-local multicast.
    ip = ipaddress.ip_address(address)
    return ip.is_global and not ip.is_multicast


def validate_url(url):
    if not isinstance(url, str) or re.search(r'[\x00-\x20\x7f\\]', url):
        raise ValueError('unsafe URL characters')
    parsed = urlsplit(url)
    if parsed.scheme not in {'http', 'https'} or not parsed.hostname:
        raise ValueError('only public HTTP(S) URLs permitted')
    if parsed.username is not None or parsed.password is not None:
        raise ValueError('credentials forbidden')
    host = parsed.hostname.encode('idna').decode('ascii').lower().rstrip('.')
    port = parsed.port or (443 if parsed.scheme == 'https' else 80)
    if port not in {80, 443}:
        raise ValueError('nonstandard port forbidden')
    if host == 'localhost' or host.endswith(('.localhost', '.local', '.internal')) or '.' not in host and ':' not in host:
        raise ValueError('private host forbidden')
    try:
        addr = ipaddress.ip_address(host)
    except ValueError:
        if not re.fullmatch(r'[a-z0-9.-]+', host):
            raise ValueError('invalid public hostname') from None
    else:
        if not is_public_unicast(addr):
            raise ValueError('private address forbidden')
    return host, port


def resolve_public(host, port):
    addresses = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    if not addresses:
        raise socket.gaierror()
    for _, _, _, _, address in addresses:
        if not is_public_unicast(address[0]):
            raise ValueError('private DNS destination forbidden')
    return addresses[0][4][0]


def open_public_connection(url, timeout):
    """Resolve once, validate all addresses, connect to pinned IP; TLS uses host."""
    host, port = validate_url(url)
    ip = resolve_public(host, port)
    parsed = urlsplit(url)
    connection = (http.client.HTTPSConnection(host, port, timeout=timeout,
                    context=ssl.create_default_context()) if parsed.scheme == 'https'
                  else http.client.HTTPConnection(host, port, timeout=timeout))
    # HTTPConnection.connect uses this hook, while HTTPS still verifies the
    # certificate against the original hostname and sends its original SNI.
    connection._create_connection = lambda address, timeout, source_address=None: socket.create_connection((ip, port), timeout, source_address)
    return connection


def read_prefix(response, limit=1024):
    return response.read(min(1024, max(0, limit)))


def inspect_prefix(prefix, content_type):
    if 'html' not in content_type.lower():
        return False, False
    text = prefix.lower()
    challenge = any(marker in text for marker in [b'cf-chl-', b'captcha', b'just a moment',
                    b'verify you are human', b'access denied', b'incapsula', b'akamai bot'])
    missing = bool(re.search(br'<title[^>]*>\s*(?:404|410|page not found|not found)', text))
    return challenge, missing


def exchange(url, method, timeout):
    """One exchange only; parent bounds the entire child including DNS/body."""
    if method not in {'HEAD', 'GET'}:
        raise ValueError('method forbidden')
    connection = open_public_connection(url, timeout)
    parsed = urlsplit(url)
    target = parsed.path or '/'
    # Preserve an explicitly empty query as well as exact query bytes/case.
    if '?' in url.split('#', 1)[0]:
        target += '?' + parsed.query
    headers = {'User-Agent': 'ThinkPadArchive-LinkAudit/1.0 (availability only)',
               'Accept-Encoding': 'identity', 'Connection': 'close'}
    if method == 'GET':
        headers['Range'] = 'bytes=0-1023'
    try:
        connection.request(method, target, headers=headers)
        response = connection.getresponse()
        content_type = response.getheader('Content-Type', '').split(';', 1)[0].lower()
        if not re.fullmatch(r'[a-z0-9!#$&^_.+/-]{0,100}', content_type):
            content_type = 'unknown'
        prefix = read_prefix(response) if method == 'GET' and response.status not in REDIRECTS else b''
        challenge, missing = inspect_prefix(prefix, content_type)
        return {'status': response.status, 'content_type': content_type,
                'location': response.getheader('Location'), 'bytes_read': len(prefix),
                'challenge': challenge, 'soft_missing': missing}
    finally:
        connection.close()


def network_request(url, method, timeout):
    """Kill/reap a stuck resolver or slow-drip response, not just socket idle IO."""
    try:
        result = subprocess.run([sys.executable, str(Path(__file__).resolve()), '--_request'],
                   input=json.dumps({'url': url, 'method': method, 'timeout': timeout}),
                   text=True, capture_output=True, timeout=timeout,
                   env={'PATH': os.defpath, 'PYTHONIOENCODING': 'utf-8'})
        if result.returncode != 0:
            return {'error': 'transport_error'}
        return json.loads(result.stdout)
    except subprocess.TimeoutExpired:
        return {'error': 'timeout'}
    except (OSError, ValueError):
        return {'error': 'transport_error'}


class HostLimiter:
    def __init__(self, per_host=4, interval=0.075):
        self.per_host = per_host
        self.interval = interval
        self.lock = threading.Lock()
        self.hosts = {}

    @contextlib.contextmanager
    def slot(self, host, deadline):
        with self.lock:
            sem, start_lock, last = self.hosts.setdefault(host, (threading.BoundedSemaphore(self.per_host), threading.Lock(), [0.0]))
        remaining = deadline - time.monotonic()
        if remaining <= 0 or not sem.acquire(timeout=remaining):
            raise TimeoutError()
        try:
            with start_lock:
                delay = max(0, last[0] + self.interval - time.monotonic())
                if time.monotonic() + delay >= deadline:
                    raise TimeoutError()
                if delay:
                    time.sleep(delay)
                last[0] = time.monotonic()
            yield
        finally:
            sem.release()


def check_url(url, transport=None, deadline=None, timeout=12, limiter=None):
    started = time.monotonic()
    deadline = started + 2 * timeout * 6 + 1 if deadline is None else deadline
    transport = transport or network_request
    row = {'url': url, 'checked_at': utcnow(), 'final_url': url,
           'redirect_chain': [], 'attempts': [], 'method': None, 'status': None,
           'content_type': None, 'bytes_read': 0, 'category': 'not_checked',
           'reason': 'duration_cutoff', 'elapsed': 0.0}
    method = 'HEAD'
    current = url
    seen = set()
    first_missing = False
    redirects = 0
    while True:
        try:
            host, _ = validate_url(current)
        except ValueError:
            row.update(category='unsafe_url', reason='public_url_validation_refused')
            break
        if (method, current) in seen:
            row.update(category='redirect_loop', reason='repeated_redirect_destination')
            break
        seen.add((method, current))
        if time.monotonic() >= deadline:
            row.update(category='timeout' if row['attempts'] else 'not_checked', reason='duration_cutoff')
            break
        request_started = False
        attempt_start = time.monotonic()
        try:
            with limiter.slot(host, deadline) if limiter else contextlib.nullcontext():
                remaining = min(timeout, deadline - time.monotonic())
                if remaining <= 0:
                    raise TimeoutError()
                attempt_start = time.monotonic()
                request_started = True
                result = transport(current, method, remaining)
            error = result.get('error')
        except (TimeoutError, socket.timeout):
            if not request_started:
                row.update(category='timeout' if row['attempts'] else 'not_checked', reason='duration_cutoff')
                break
            result, error = {}, 'timeout'
        except socket.gaierror:
            result, error = {}, 'dns_error'
        except ssl.SSLError:
            result, error = {}, 'tls_error'
        except OSError:
            result, error = {}, 'transport_error'
        row.update(final_url=current, method=method, status=result.get('status'),
                   content_type=result.get('content_type'))
        row['bytes_read'] += result.get('bytes_read', 0)
        row['attempts'].append({'url': current, 'method': method, 'status': result.get('status'),
                               'content_type': result.get('content_type'),
                               'bytes_read': result.get('bytes_read', 0),
                               'error': error if error in ERRORS else None,
                               'elapsed': round(time.monotonic() - attempt_start, 4) if 'attempt_start' in locals() else 0})
        if error:
            row.update(category=error if error in ERRORS else 'transport_error', reason='bounded_request_failed')
            break
        status = result['status']
        if status in REDIRECTS:
            if redirects >= 5:
                row.update(category='redirect_limit', reason='five_redirect_limit')
                break
            location = result.get('location')
            if not location:
                row.update(category='redirect_error', reason='missing_location')
                break
            destination = urljoin(current, location).split('#', 1)[0]
            try:
                validate_url(destination)
            except ValueError:
                row.update(category='unsafe_url', reason='unsafe_redirect_refused')
                break
            row['redirect_chain'].append({'url': current, 'status': status, 'to': destination, 'method': method})
            current = destination
            redirects += 1
            continue
        if method == 'HEAD' and (status in {403, 404, 405, 410, 429} or status >= 500):
            first_missing = status in {404, 410}
            method = 'GET'
            continue
        if result.get('challenge'):
            category, reason = 'challenge', 'bounded_html_prefix_challenge_marker'
        elif result.get('soft_missing') and 200 <= status < 300:
            category, reason = 'suspected_soft_missing', 'bounded_html_title_missing_marker'
        elif 200 <= status < 300:
            category, reason = 'available', 'head_only_availability' if method == 'HEAD' else 'bounded_get_availability'
        elif status in {404, 410}:
            category, reason = ('confirmed_missing', 'head_and_get_missing') if first_missing else ('missing_candidate', 'get_missing_without_head_confirmation')
        elif status == 403:
            category, reason = 'blocked', 'http_403'
        elif status == 429:
            category, reason = 'rate_limited', 'http_429'
        elif status >= 500:
            category, reason = 'server_error', 'http_5xx'
        elif status == 401:
            category, reason = 'blocked', 'http_401_no_auth_attempted'
        else:
            category, reason = 'http_error', 'other_http_status'
        row.update(category=category, reason=reason)
        break
    row['elapsed'] = round(time.monotonic() - started, 4)
    return row


def write_json(path, value):
    temporary = path.with_suffix('.tmp')
    with temporary.open('w', encoding='utf-8') as stream:
        json.dump(value, stream, ensure_ascii=True, indent=2)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())
    temporary.replace(path)


def run_audit(items, output, workers=8, max_duration=2700, timeout=12, checker=None,
              source_root=None, argv=None):
    if not 1 <= workers <= 8 or not 0 <= max_duration <= 2700 or not 0 < timeout <= 30:
        raise ValueError('audit bounds exceeded')
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    start = time.monotonic()
    deadline = start + max_duration
    started_at = utcnow()
    write_json(output / 'inventory.json', items)
    write_json(output / 'manifest.json', {'schema': 1, 'started_at': started_at,
               'source_root': str(source_root) if source_root else None, 'argv': argv,
               'tool_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
               'input_sha256': items['input_sha256'], 'target': len(items['urls']),
               'occurrences': items['occurrences'], 'workers': workers, 'per_host': 4,
               'min_host_start_interval': 0.075, 'timeout': timeout, 'max_duration': max_duration,
               'redirect_limit': 5, 'get_read_cap': 1024,
               'limitations': ['HEAD 2xx is availability only; not identity or compatibility',
                   'No HTML soft-error detection unless GET fallback fetched a prefix',
                   'No bodies retained; bytes_read is prefix bytes delivered to this application',
                   'No circuit breaker; each target attempted unless duration cutoff']})
    limiter = HostLimiter()
    checker = checker or check_url
    # Round-robin hosts so one slow origin cannot monopolize the catalogue queue.
    hosts = collections.defaultdict(collections.deque)
    for entry in items['urls']:
        hosts[urlsplit(entry['url']).hostname].append(entry['url'])
    pending = collections.deque()
    while hosts:
        for host in list(hosts):
            pending.append(hosts[host].popleft())
            if not hosts[host]:
                del hosts[host]
    total = len(pending)
    categories = collections.Counter()
    rows_count = 0
    write_json(output / 'progress.json', {'started_at': started_at, 'rows': 0, 'target': total})

    with (output / 'results.jsonl').open('x', encoding='utf-8') as stream:
        def checkpoint(row):
            nonlocal rows_count
            stream.write(json.dumps(row, ensure_ascii=True) + '\n')
            stream.flush()
            os.fsync(stream.fileno())
            rows_count += 1
            categories[row['category']] += 1
            write_json(output / 'progress.json', {'started_at': started_at, 'updated_at': utcnow(),
                       'rows': rows_count, 'target': total, 'categories': dict(categories),
                       'elapsed': round(time.monotonic() - start, 3)})

        with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
            active = {}
            while pending or active:
                while pending and len(active) < workers and time.monotonic() < deadline:
                    url = pending.popleft()
                    future = executor.submit(checker, url, deadline=deadline, timeout=timeout, limiter=limiter)
                    active[future] = url
                if not active:
                    break
                completed, _ = concurrent.futures.wait(active, timeout=0.25, return_when=concurrent.futures.FIRST_COMPLETED)
                for future in completed:
                    url = active.pop(future)
                    # Programming defects intentionally propagate, not fake network outcomes.
                    checkpoint(future.result())
            while pending:
                checkpoint({'url': pending.popleft(), 'category': 'not_checked',
                            'reason': 'duration_cutoff', 'checked_at': None, 'attempts': [],
                            'redirect_chain': [], 'final_url': None, 'method': None, 'status': None,
                            'content_type': None, 'elapsed': 0, 'bytes_read': 0})
    # Re-read durable outcomes, independently checking exact inventory coverage.
    rows = [json.loads(line) for line in (output / 'results.jsonl').read_text().splitlines()]
    expected = {entry['url'] for entry in items['urls']}
    actual = {row['url'] for row in rows}
    if actual != expected or len(rows) != len(expected):
        raise RuntimeError('checkpoint inventory reconciliation failed')
    categories = collections.Counter(row['category'] for row in rows)
    unchecked = categories.get('not_checked', 0)
    summary = {'schema': 1, 'started_at': started_at, 'finished_at': utcnow(),
               'elapsed': round(time.monotonic() - start, 3), 'target': total,
               'occurrences': items['occurrences'], 'rows': len(rows), 'checked': total - unchecked,
               'not_checked': unchecked, 'complete': unchecked == 0,
               'categories': dict(sorted(categories.items())),
               'redirected_urls': sum(bool(row.get('redirect_chain')) for row in rows),
               'bytes_read': sum(row.get('bytes_read', 0) for row in rows),
               'attempts': sum(len(row.get('attempts', [])) for row in rows)}
    write_json(output / 'summary.json', summary)
    return summary


def child_request():
    try:
        arguments = json.loads(sys.stdin.read(16384))
        result = exchange(**arguments)
    except (TimeoutError, socket.timeout):
        result = {'error': 'timeout'}
    except socket.gaierror:
        result = {'error': 'dns_error'}
    except ssl.SSLError:
        result = {'error': 'tls_error'}
    except ValueError:
        result = {'error': 'unsafe_url'}
    except (OSError, http.client.HTTPException, UnicodeError):
        result = {'error': 'transport_error'}
    print(json.dumps(result))
    return 0


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if argv == ['--_request']:
        return child_request()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=Path(__file__).resolve().parents[1], help='source git worktree; only tracked data/*.json is inventoried')
    parser.add_argument('--output', type=Path, required=True, help='new metadata-only evidence directory; existing output refused')
    parser.add_argument('--workers', type=int, choices=range(1, 9), default=8)
    parser.add_argument('--timeout', type=float, default=12, help='whole exchange deadline, seconds (0 < value <= 30)')
    parser.add_argument('--max-duration', type=float, default=2700, help='aggregate network deadline in seconds, maximum 2700')
    args = parser.parse_args(argv)
    if not 0 < args.timeout <= 30 or not 0 <= args.max_duration <= 2700:
        parser.error('timeout must be (0,30], max-duration must be [0,2700]')
    if args.output.exists():
        parser.error('output exists; choose a new directory (resume not supported)')
    try:
        files = subprocess.check_output(['git', '-C', str(args.source), 'ls-files', '-z', '--', 'data/*.json']).decode().split('\0')
        files = [name for name in files if name]
        if not files:
            parser.error('no tracked data JSON inputs')
        items = inventory(args.source, files)
        summary = run_audit(items, args.output, workers=args.workers, timeout=args.timeout,
                            max_duration=args.max_duration, source_root=args.source, argv=argv)
    except (ValueError, FileExistsError):
        parser.error('input or output refused; inspect public URL safety and output location')
    print(json.dumps(summary, indent=2))
    return 0 if summary['complete'] else 2


if __name__ == '__main__':
    raise SystemExit(main())
