"""One local/CI entry point for tests, syntax, fresh builds and packaging."""
from pathlib import Path
import argparse
import os
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def check_project(output, *, package=False):
    """Run real checked child commands; never reuse a populated build tree."""
    destination = Path(output).absolute()
    if destination.exists() or any(p.is_symlink() for p in (destination, *destination.parents)):
        raise ValueError('Checks need a new output directory without symlinks')
    if not destination.parent.is_dir():
        raise ValueError('Check output parent must exist')
    destination.mkdir()
    env = dict(os.environ)
    env['PYTHONDONTWRITEBYTECODE'] = '1'
    def run(argv, timeout=180):
        subprocess.run(argv, cwd=ROOT, env=env, check=True, timeout=timeout)
    run([sys.executable, '-m', 'unittest', 'discover', '-s', 'tests', '-v'], timeout=600)
    run([sys.executable, '-m', 'compileall', '-q', '-f', 'thinkpad_archive', 'tools', 'tests'])
    for path in sorted((ROOT / 'assets').glob('*.js')):
        run(['node', '--check', str(path)], timeout=30)
    for name, flags in (('english', []), ('spanish', ['--default-language', 'es']),
                        ('stats', ['--enable-stats'])):
        site = destination / name
        run([sys.executable, '-m', 'thinkpad_archive', 'build', '--output', str(site), *flags])
        run([sys.executable, 'tools/check_site.py', str(site), *(['--allow-stats-api'] if name == 'stats' else [])])
    if package:
        run([sys.executable, '-m', 'thinkpad_archive', 'offline-release', '--output', str(destination / 'offline')])
    return destination


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, help='new check-output directory; parent must exist')
    parser.add_argument('--package', action='store_true', help='also generate and verify the offline ZIP/checksum')
    args = parser.parse_args(argv)
    try:
        check_project(args.output, package=args.package)
    except (OSError, ValueError, subprocess.SubprocessError):
        print('error: verification failed; inspect the failing check above', file=sys.stderr)
        return 1
    print('Project verification passed.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
