"""Module entry point: python3 -m thinkpad_archive build --output NEW_DIR."""
from __future__ import annotations

import argparse
import sys

from . import build_site


def main(argv=None):
    parser = argparse.ArgumentParser(description="Build an offline-readable ThinkPad manual and driver finder.")
    sub = parser.add_subparsers(dest="command", required=True)
    build = sub.add_parser("build", help="create a new static output directory")
    build.add_argument("--output", required=True, help="new output directory; parent must already exist")
    build.add_argument("--default-language", help="installed locale code (default: en)")
    build.add_argument("--data-dir", help="metadata directory (default: project data/)")
    build.add_argument("--locales-dir", help="translation directory (default: project locales/)")
    args = parser.parse_args(argv)
    try:
        build_site(args.output, data_dir=args.data_dir, locales_dir=args.locales_dir,
                   default_language=args.default_language)
    except (ValueError, TypeError, OverflowError):
        # Do not echo exception text, metadata values or host paths.
        print("error: build refused; check metadata, locales and a new output directory", file=sys.stderr)
        return 2
    print("Built static ThinkPad catalogue.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
