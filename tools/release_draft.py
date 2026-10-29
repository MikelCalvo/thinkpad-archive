"""Create one reviewed-asset DRAFT release for an existing matching version tag."""
from pathlib import Path
import argparse
import json
import re
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / 'tools') not in sys.path:
    sys.path.insert(0, str(ROOT / 'tools'))
from release_assets import assets_match, verified_assets


def _command(argv):
    return subprocess.run(argv, cwd=ROOT, check=True, capture_output=True, text=True, timeout=120).stdout.strip()


def prepare_draft(directory, *, repository, tag, sha, version=None):
    number = (ROOT / 'VERSION').read_text(encoding='ascii').strip() if version is None else version
    if (not isinstance(number, str) or re.fullmatch(r'(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)', number) is None or
            tag != 'v' + number or re.fullmatch(r'[a-f0-9]{40}', sha) is None or
            re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', repository) is None):
        raise ValueError('Invalid version/tag/repository identity')
    assets = verified_assets(directory, number)
    if _command(['git', 'rev-parse', 'HEAD']) != sha or _command(['git', 'rev-parse', tag + '^{commit}']) != sha:
        raise ValueError('Release tag and checkout must match the checked commit')
    # A successful complete listing distinguishes absence from auth/network errors.
    pages = json.loads(_command(['gh', 'api', 'repos/' + repository + '/releases?per_page=100', '--paginate', '--slurp']))
    releases = [row for page in pages for row in page] if pages and isinstance(pages[0], list) else pages
    existing = [row for row in releases if row.get('tag_name') == tag]
    if existing:
        if (len(existing) != 1 or existing[0].get('draft') is not True or
                existing[0].get('prerelease') is not number.startswith('0.') or
                not assets_match(existing[0], assets)):
            raise ValueError('Existing release differs; reconcile it manually')
        return {'status': 'draft-already-present', 'tag': tag, 'commit': sha}
    changelog = (ROOT / 'CHANGELOG.md').read_text(encoding='utf-8')
    heading = re.search(r'^## ' + re.escape(number) + r'(?: \([^\n]*\))?\s*$', changelog, re.M)
    if heading is None:
        raise ValueError('Release changelog section is missing')
    section = changelog[heading.end():].split('\n## ', 1)[0].strip()
    notes = section + '\n\nOffline catalogue: extract the ZIP and open index.html. External manuals and drivers are not bundled.\n'
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / 'release-notes.md'
        path.write_text(notes, encoding='utf-8')
        args = ['gh', 'release', 'create', tag, *[str(a['path']) for a in assets], '--repo', repository,
                '--draft', '--verify-tag', '--title', tag, '--notes-file', str(path), '--latest=false']
        if number.startswith('0.'):
            args.append('--prerelease')
        _command(args)
    # A failed or ambiguous create is not retried. Reruns only reconcile existing bytes.
    # Use the authenticated listing for drafts too; never interpret lookup errors as absence.
    pages = json.loads(_command(['gh', 'api', 'repos/' + repository + '/releases?per_page=100', '--paginate', '--slurp']))
    rows = [row for page in pages for row in page] if pages and isinstance(pages[0], list) else pages
    matches = [row for row in rows if row.get('tag_name') == tag]
    if len(matches) != 1:
        raise ValueError('Created draft requires manual reconciliation')
    release = matches[0]
    if (release.get('draft') is not True or release.get('prerelease') is not number.startswith('0.') or
            not assets_match(release, assets)):
        raise ValueError('Created draft requires manual reconciliation')
    return {'status': 'draft-created', 'tag': tag, 'commit': sha}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--assets', required=True)
    parser.add_argument('--repository', required=True)
    parser.add_argument('--tag', required=True)
    parser.add_argument('--sha', required=True)
    args = parser.parse_args(argv)
    try:
        result = prepare_draft(args.assets, repository=args.repository, tag=args.tag, sha=args.sha)
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError):
        print('error: draft release refused; inspect checks or reconcile any existing release', file=sys.stderr)
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
