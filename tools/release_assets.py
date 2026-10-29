"""Validate offline release assets without network access or extraction."""
import hashlib
import json
from pathlib import Path
import re
import zipfile


def _digest(stream):
    value = hashlib.sha256()
    while chunk := stream.read(1024 * 1024):
        value.update(chunk)
    return value.hexdigest()


def verified_assets(directory, version):
    if not isinstance(version, str) or re.fullmatch(r'(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)', version) is None:
        raise ValueError('Invalid release version')
    root = Path(directory)
    name = 'thinkpad-archive-' + version + '-offline.zip'
    paths = [root / name, root / (name + '.sha256')]
    if {p.name for p in root.iterdir()} != {p.name for p in paths} or any(p.is_symlink() or not p.is_file() for p in paths):
        raise ValueError('Unexpected release assets')
    with paths[0].open('rb') as stream:
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    if paths[1].read_text(encoding='ascii') != digest + '  ' + name + '\n':
        raise ValueError('ZIP checksum mismatch')
    with zipfile.ZipFile(paths[0]) as archive:
        infos = archive.infolist()
        names = [i.filename for i in infos]
        prefix = 'thinkpad-archive-' + version + '/'
        if (len(infos) > 20000 or len(names) != len(set(names)) or
                sum(i.file_size for i in infos) > 512 * 1024 * 1024 or
                any(i.file_size > 16 * 1024 * 1024 or i.flag_bits & 1 or
                    not i.filename.startswith(prefix) or '..' in i.filename.split('/') or '\\' in i.filename
                    for i in infos)):
            raise ValueError('Invalid ZIP members')
        manifest = json.loads(archive.read(prefix + 'SHA256SUMS.json'))
        if manifest.get('version') != version or set(names) != {prefix + p for p in manifest['files']} | {prefix + 'SHA256SUMS.json'}:
            raise ValueError('ZIP manifest mismatch')
        for member, expected in manifest['files'].items():
            with archive.open(prefix + member) as stream:
                if _digest(stream) != expected:
                    raise ValueError('ZIP member checksum mismatch')
    result = []
    for path in paths:
        with path.open('rb') as stream:
            result.append({'path': path, 'name': path.name, 'size': path.stat().st_size,
                           'digest': 'sha256:' + hashlib.file_digest(stream, 'sha256').hexdigest()})
    return result


def assets_match(release, assets):
    """Require exact existing names, size, state and GitHub-reported SHA-256."""
    existing = release.get('assets', [])
    if len(existing) != len(assets):
        return False
    by_name = {row.get('name'): row for row in existing}
    if set(by_name) != {a['name'] for a in assets}:
        return False
    return all(by_name[a['name']].get('size') == a['size'] and
               by_name[a['name']].get('state') == 'uploaded' and
               by_name[a['name']].get('digest') == a['digest'] for a in assets)
