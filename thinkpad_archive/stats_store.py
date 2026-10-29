"""Permanent SQLite daily marginal counters, never events or visitor records.

A database's existing parent directory must be private (mode 0700), outside
any served tree. Callers supply a finite set of public canonical routes.
"""
from __future__ import annotations

from contextlib import contextmanager
from datetime import date, datetime, timedelta, timezone
import os
from pathlib import Path
import re
import sqlite3
import stat
import threading

from .validation import LANG

CATEGORIES = {
    "source": frozenset(("direct", "internal", "search", "github", "reddit", "hacker-news", "social", "other")),
    "device": frozenset(("desktop", "mobile", "tablet", "unknown")),
    "browser": frozenset(("firefox", "chrome", "safari", "edge", "opera", "other", "unknown")),
    "system": frozenset(("windows", "macos", "linux", "android", "ios", "other", "unknown")),
}
PRIVACY = {"storage": "daily_marginal_counters", "retention_days": None,
           "timezone": "UTC", "unique_visitors": False, "no_cookies": True,
           "no_identifiers": True, "geo": False}
VERSION = re.compile(r'(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\.(?:0|[1-9][0-9]*)\Z', re.ASCII)
LOCK_TIMEOUT = 0.5
SCHEMA = """CREATE TABLE counts(day TEXT NOT NULL, dimension TEXT NOT NULL,
value TEXT NOT NULL, count INTEGER NOT NULL CHECK(typeof(count)='integer' AND count>0),
PRIMARY KEY(day,dimension,value))"""
ROUTE = re.compile(r"/[a-z]{2,3}(?:-[a-z0-9]{2,8})*/(?:[a-zA-Z0-9_/-]+\.html)?\Z")


def no_symlinks(path):
    """Return an absolute path only if none of its components is a symlink."""
    path = Path(os.path.abspath(os.fspath(path)))
    if any(part.is_symlink() for part in (path, *path.parents)):
        raise ValueError("Unsafe analytics path")
    return path


def empty_data(days, today, *, enabled=True, first_day=None):
    start = (first_day or today) if days == 'all' else today - timedelta(days=days - 1)
    length = (today - start).days + 1
    return {"enabled": enabled, "privacy": dict(PRIVACY),
            "window": {"days": days, "from": start.isoformat(), "to": today.isoformat()},
            "total": 0, "daily": [{"day": (start + timedelta(days=i)).isoformat(), "count": 0} for i in range(length)],
            **{name: [] for name in ("pages", "sources", "devices", "browsers", "systems", "languages")},
            "downloads": {"total": 0, "daily": [{"day": (start + timedelta(days=i)).isoformat(), "count": 0} for i in range(length)], "versions": []},
            "export_url": "/api/stats/export.json"}


class AnalyticsStore:
    """Serialize bounded transactions; public export is every retained field.

    ``clock`` is a zero-argument callable returning an aware datetime. All
    counters are retained indefinitely; period filters never delete history.
    """

    def __init__(self, database, *, pages, clock=None):
        self.database = no_symlinks(database)
        self.pages = frozenset(pages)
        if not self.pages or any(type(p) is not str or not ROUTE.fullmatch(p) or p.endswith('/stats.html') for p in self.pages):
            raise ValueError("Invalid public routes")
        parent = self.database.parent
        if not parent.is_dir() or parent.stat().st_mode & 0o077 or parent.stat().st_uid != os.getuid():
            raise ValueError("Analytics directory must be private")
        self.clock = clock or (lambda: datetime.now(timezone.utc))
        self._lock = threading.Lock()
        self._db = None
        flags = os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW
        fd = os.open(self.database, flags, 0o600)
        try:
            meta = os.fstat(fd)
            if not stat.S_ISREG(meta.st_mode) or meta.st_nlink != 1 or meta.st_uid != os.getuid() or meta.st_mode & 0o077:
                raise ValueError("Unsafe analytics database")
        finally:
            os.close(fd)
        for suffix in ("-wal", "-shm", "-journal"):
            side = no_symlinks(str(self.database) + suffix)
            if side.exists() and (not side.is_file() or side.stat().st_nlink != 1):
                raise ValueError("Unsafe analytics database")
        db = sqlite3.connect(self.database, timeout=LOCK_TIMEOUT, check_same_thread=False, isolation_level=None)
        self._db = db
        try:
            db.execute("PRAGMA trusted_schema=OFF")
            objects = db.execute("SELECT type,name,sql FROM sqlite_master WHERE name NOT LIKE 'sqlite_%'").fetchall()
            if not objects:
                db.execute(SCHEMA)
            elif objects != [("table", "counts", SCHEMA)]:
                raise ValueError("Unexpected analytics schema")
            db.execute("PRAGMA journal_mode=WAL")
            db.execute("PRAGMA secure_delete=ON")
            with self._transaction() as (conn, today):
                allowed = {**CATEGORIES, 'total': {'all'}}
                for day, dimension, value, count in conn.execute('SELECT day,dimension,value,count FROM counts'):
                    if dimension == 'page':
                        valid = type(value) is str and bool(ROUTE.fullmatch(value)) and not value.endswith('/stats.html')
                    elif dimension == 'language':
                        valid = type(value) is str and bool(LANG.fullmatch(value))
                    elif dimension == 'download':
                        valid = type(value) is str and len(value) <= 64 and bool(VERSION.fullmatch(value))
                    else:
                        valid = dimension in allowed and value in allowed[dimension]
                    if (type(day) is not str or date.fromisoformat(day).isoformat() != day or
                            not valid or type(count) is not int or count <= 0):
                        raise ValueError('Invalid analytics counters')
        except Exception:
            self.close()
            raise

    def _today(self):
        now = self.clock()
        if not isinstance(now, datetime) or now.utcoffset() is None:
            raise ValueError("Invalid analytics clock")
        return now.astimezone(timezone.utc).date()

    @contextmanager
    def _transaction(self):
        if not self._lock.acquire(timeout=LOCK_TIMEOUT):
            raise sqlite3.OperationalError("Analytics busy")
        try:
            if self._db is None:
                raise sqlite3.OperationalError("Analytics unavailable")
            today = self._today()
            self._db.execute("BEGIN IMMEDIATE")
            try:
                yield self._db, today
                self._db.execute("COMMIT")
            except BaseException:
                self._db.execute("ROLLBACK")
                raise
        finally:
            self._lock.release()

    def record_pageview(self, path, source, device, browser, system):
        """Atomically increment seven marginal counters after finite validation."""
        fields = {"page": path, "source": source, "device": device,
                  "browser": browser, "system": system}
        if type(path) is not str or path not in self.pages:
            raise ValueError("Invalid pageview")
        if any(type(fields[key]) is not str or fields[key] not in values for key, values in CATEGORIES.items()):
            raise ValueError("Invalid pageview")
        fields.update(total="all", language=path.split('/')[1])
        with self._transaction() as (db, today):
            db.executemany("INSERT INTO counts(day,dimension,value,count) VALUES(?,?,?,1) "
                           "ON CONFLICT(day,dimension,value) DO UPDATE SET count=count+1",
                           [(today.isoformat(), dim, value) for dim, value in fields.items()])

    def record_download(self, version):
        """Increment only a public daily version aggregate, not pageview marginals."""
        if type(version) is not str or len(version) > 64 or not VERSION.fullmatch(version):
            raise ValueError('Invalid download version')
        with self._transaction() as (db, today):
            db.execute("INSERT INTO counts(day,dimension,value,count) VALUES(?,?,?,1) "
                       "ON CONFLICT(day,dimension,value) DO UPDATE SET count=count+1",
                       (today.isoformat(), 'download', version))

    def export(self):
        with self._transaction() as (db, today):
            rows = db.execute("SELECT day,dimension,value,count FROM counts ORDER BY day,dimension,value").fetchall()
        return {"privacy": dict(PRIVACY), "counts": [dict(zip(("day", "dimension", "value", "count"), row)) for row in rows]}

    def data(self, days: int | str = 30):
        if not ((type(days) is int and days in (7, 30, 90, 365)) or (type(days) is str and days == 'all')):
            raise ValueError("Invalid analytics window")
        with self._transaction() as (db, today):
            first_day = None
            if days == 'all':
                first = db.execute('SELECT min(day) FROM counts WHERE day <= ?', (today.isoformat(),)).fetchone()[0]
                first_day = date.fromisoformat(first) if first is not None else today
            result = empty_data(days, today, first_day=first_day)
            rows = db.execute("SELECT day,dimension,value,count FROM counts WHERE day >= ? AND day <= ? ORDER BY day,dimension,value",
                              (result['window']['from'], today.isoformat())).fetchall()
        daily = {row['day']: row for row in result['daily']}
        totals = {key: {} for key in ("page", "source", "device", "browser", "system", "language")}
        download_daily = {row['day']: row for row in result['downloads']['daily']}
        versions = {}
        for day, dimension, value, count in rows:
            if dimension == 'download':
                result['downloads']['total'] += count
                download_daily[day]['count'] += count
                versions[value] = versions.get(value, 0) + count
            elif dimension == 'total':
                daily[day]['count'] += count
                result['total'] += count
            else:
                bucket = totals[dimension]
                bucket[value] = bucket.get(value, 0) + count
        result['downloads']['versions'] = [{"value": value, "count": count} for value, count in sorted(versions.items(), key=lambda item: (-item[1], item[0]))]
        for dimension, values in totals.items():
            result[dimension + 's'] = [{"value": value, "count": count} for value, count in sorted(values.items(), key=lambda item: (-item[1], item[0]))]
        return result

    def close(self):
        with self._lock:
            if self._db is not None:
                self._db.close()
                self._db = None
