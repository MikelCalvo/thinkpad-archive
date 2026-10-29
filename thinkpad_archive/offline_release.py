"""Build a bounded, reproducible wrapper around a fresh collection-free site."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import tempfile
import zipfile

from . import ROOT, build_site
from .validation import load_catalogue, load_locales, no_symlinks, read_bytes, require

MAX_MEMBERS = 20000
MAX_MEMBER = 16 * 1024 * 1024
MAX_TOTAL = 512 * 1024 * 1024
ASSETS = ('style.css', 'search.js', 'ui.js', 'theme.js', 'language.js', 'packages.js',
          'stats.css', 'stats.js', 'analytics.js', 'social-en.png', 'social-es.png')


def _expected_site(data_dir, locales_dir):
    data = load_catalogue(data_dir)
    locales = load_locales(locales_dir)
    years = [r['year'] for model in data['models'] for r in model.get('introduced', [])]
    calendar = list(range(min(years), max(years) + 1)) if years else []
    members = {'index.html', 'favicon.svg', *('assets/' + name for name in ASSETS)}
    for lang in locales:
        members.update(lang + '/' + page for page in ('index.html', 'catalogue.html', 'sources.html', 'stats.html'))
        members.update(lang + '/models/' + model['id'] + '.html' for model in data['models'])
        members.update(lang + '/years/' + str(year) + '.html' for year in [*calendar, 'unknown'])
    return members


def _instructions(version):
    return (f'ThinkPad Archive {version} — offline catalogue / catálogo offline\n\n'
            'English\n'
            'Extract the entire ZIP, then open index.html in your browser. No Python, server or installation is needed. '
            'Both English and Spanish are included. Keep all folders together.\n'
            'Model pages, specifications, search and navigation work locally. External sources, PDFs, driver links and '
            'GitHub correction drafts still need Internet access. No manufacturer PDFs or installers are included.\n'
            'Live statistics and their history are not included. This copy does not collect visits. The Stats page '
            'cannot show live counts from a local file. Theme and language preferences may be stored locally by your browser.\n'
            'SHA256SUMS.json records the contents of this snapshot; the sibling .zip.sha256 checks the whole ZIP. '
            'Checksums detect changes, not publisher identity.\n'
            'Original project material: MIT, see LICENSE. Third-party source and trademark rights remain separate; '
            'see docs/sources-and-rights.md. This is not an IBM or Lenovo publication.\n\n'
            'Español\n'
            'Descomprime el ZIP completo y abre index.html en el navegador. No necesitas Python, servidor ni instalación. '
            'Incluye español e inglés. Conserva todas las carpetas juntas.\n'
            'Las fichas, especificaciones, búsquedas y navegación funcionan localmente. Las fuentes externas, los PDF, '
            'los enlaces a drivers y los borradores de corrección de GitHub necesitan Internet. No se incluyen PDF ni instaladores del fabricante.\n'
            'No se incluyen las estadísticas en directo ni su historial. Esta copia no recoge visitas. Stats no puede '
            'mostrar contadores en directo desde un archivo local. El navegador puede guardar localmente tus preferencias de tema e idioma.\n'
            'SHA256SUMS.json registra el contenido de esta copia; el archivo .zip.sha256 adjunto comprueba el ZIP completo. '
            'Las sumas detectan cambios, no autentican al editor.\n'
            'Material original del proyecto: MIT, consulta LICENSE. Los derechos de fuentes y marcas de terceros son '
            'independientes; consulta docs/sources-and-rights.md. No es una publicación de IBM ni Lenovo.\n').encode('utf-8')


def _verify_archive(path, prefix, digests):
    with zipfile.ZipFile(path) as archive:
        require(archive.namelist() == [prefix + name for name in sorted(digests)], 'Archive membership mismatch')
        for info in archive.infolist():
            require(info.file_size <= MAX_MEMBER and not info.flag_bits & 1, 'Invalid archive member')
            with archive.open(info) as stream:
                digest = hashlib.sha256()
                while chunk := stream.read(1024 * 1024):
                    digest.update(chunk)
            require(digest.hexdigest() == digests[info.filename[len(prefix):]], 'Archive checksum mismatch')


def build_offline_release(output, *, data_dir=None, locales_dir=None, default_language=None):
    """Create a new directory containing the bilingual ZIP and its checksum.

    The website is freshly built from validated metadata, never copied from a
    caller-supplied site directory. No downloads, stats opt-in or network IO.
    """
    destination = None
    created = False
    try:
        destination = no_symlinks(output)
        data = no_symlinks(data_dir if data_dir is not None else ROOT / 'data')
        locales = no_symlinks(locales_dir if locales_dir is not None else ROOT / 'locales')
        require(not destination.exists(), 'Output must be a new directory')
        require(destination.parent.is_dir(), 'Output parent must exist')
        require(not any(destination == p or destination.is_relative_to(p)
                        for p in (data, locales, ROOT / 'assets', ROOT / 'thinkpad_archive')), 'Output overlaps inputs')
        version_text = read_bytes(ROOT / 'VERSION', limit=64).decode('ascii')
        require(re.fullmatch(r'(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\n?', version_text) is not None,
                'Invalid release version')
        version = version_text.strip()
        name = 'thinkpad-archive-' + version + '-offline.zip'
        prefix = 'thinkpad-archive-' + version + '/'
        expected = _expected_site(data, locales)
        require(len(expected) + 5 <= MAX_MEMBERS, 'Too many archive members')
        with tempfile.TemporaryDirectory(prefix='.thinkpad-offline-', dir=destination.parent) as temporary:
            staging = Path(temporary)
            site = build_site(staging / 'site', data_dir=data, locales_dir=locales,
                              default_language=default_language, stats_enabled=False)
            entries = list(site.rglob('*'))
            require(all(not p.is_symlink() and (p.is_dir() or p.is_file()) for p in entries), 'Invalid generated file type')
            require({p.relative_to(site).as_posix() for p in entries if p.is_file()} == expected,
                    'Unexpected generated site members')
            supports = {'LICENSE': read_bytes(ROOT / 'LICENSE'), 'VERSION': (version + '\n').encode(),
                        'READ-ME.txt': _instructions(version),
                        'docs/sources-and-rights.md': read_bytes(ROOT / 'docs/sources-and-rights.md')}
            paths = sorted(expected | set(supports))
            total = sum((site / rel).stat().st_size if rel in expected else len(supports[rel]) for rel in paths)
            require(total <= MAX_TOTAL, 'Archive exceeds size limit')
            digests = {}
            archive_path = staging / name
            with zipfile.ZipFile(archive_path, 'x', compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
                def add(rel, body):
                    require(len(body) <= MAX_MEMBER, 'Archive member exceeds size limit')
                    info = zipfile.ZipInfo(prefix + rel, date_time=(1980, 1, 1, 0, 0, 0))
                    info.create_system = 3
                    info.external_attr = 0o100644 << 16
                    info.compress_type = zipfile.ZIP_DEFLATED
                    archive.writestr(info, body, compress_type=zipfile.ZIP_DEFLATED, compresslevel=6)
                    digests[rel] = hashlib.sha256(body).hexdigest()
                # Hash the fresh site, then consume one bounded member at a time.
                # Recheck those exact bytes before packaging to detect changes.
                hashes = {rel: hashlib.sha256(supports[rel] if rel in supports else
                                              read_bytes(site / rel, limit=MAX_MEMBER)).hexdigest()
                          for rel in paths}
                supports['SHA256SUMS.json'] = (json.dumps({'version': version, 'files': hashes},
                                                        ensure_ascii=False, sort_keys=True, indent=2) + '\n').encode('utf-8')
                require(total + len(supports['SHA256SUMS.json']) <= MAX_TOTAL, 'Archive exceeds size limit')
                for rel in sorted([*paths, 'SHA256SUMS.json']):
                    body = supports[rel] if rel in supports else read_bytes(site / rel, limit=MAX_MEMBER)
                    if rel in hashes:
                        require(hashlib.sha256(body).hexdigest() == hashes[rel], 'Generated member changed')
                    add(rel, body)
            _verify_archive(archive_path, prefix, digests)
            with archive_path.open('rb') as stream:
                digest = hashlib.file_digest(stream, 'sha256').hexdigest()
            checksum = staging / (name + '.sha256')
            checksum.write_text(digest + '  ' + name + '\n', encoding='ascii')
            destination.mkdir(mode=0o755)
            created = True
            for source in (archive_path, checksum):
                with source.open('rb') as incoming, (destination / source.name).open('xb') as outgoing:
                    shutil.copyfileobj(incoming, outgoing, length=1024 * 1024)
            created = False
        return destination
    except (OSError, UnicodeError, zipfile.BadZipFile, ValueError, TypeError, OverflowError):
        if created and destination is not None:
            shutil.rmtree(destination)
        raise ValueError('Offline release could not be created') from None
