"""Check generated local links and fragments without fetching external URLs."""
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit
import argparse
import json


class Links(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.ids = []
        self.links = []

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if 'id' in values:
            self.ids.append(values['id'])
        for attribute in ('href', 'src'):
            if attribute in values:
                self.links.append((tag, attribute, values[attribute], values.get('rel', '')))


def check_site(root):
    root = Path(root).resolve(strict=True)
    pages = {}
    errors = []
    external = 0
    internal = 0

    def error(path, value, reason):
        errors.append({'page': str(path.relative_to(root)), 'link': value, 'reason': reason})

    for path in sorted(root.rglob('*.html')):
        parser = Links()
        parser.feed(path.read_text(encoding='utf-8'))
        parser.close()
        pages[path.resolve()] = parser
        for identity, count in Counter(parser.ids).items():
            if count > 1:
                error(path, identity, 'duplicate-id')

    for path, parser in pages.items():
        for tag, attribute, value, rel in parser.links:
            try:
                url = urlsplit(value)
            except ValueError:
                error(path, value, 'unsafe-scheme')
                continue
            if url.scheme or url.netloc:
                if url.scheme not in ('http', 'https') or not url.hostname or url.username or url.password:
                    error(path, value, 'unsafe-scheme')
                elif not ((tag == 'a' and attribute == 'href') or
                          (tag == 'link' and attribute == 'href' and rel == 'canonical' and url.scheme == 'https')):
                    error(path, value, 'remote-asset')
                else:
                    external += 1
                continue
            target = (path.parent / unquote(url.path)).resolve() if url.path else path
            if not target.is_relative_to(root):
                error(path, value, 'path-escape')
                continue
            if target.is_dir():
                target = target / 'index.html'
            internal += 1
            if not target.is_file():
                error(path, value, 'missing-file')
            elif url.fragment:
                destination = pages.get(target)
                if destination is not None and unquote(url.fragment) not in destination.ids:
                    error(path, value, 'missing-fragment')

    return {'html_pages': len(pages), 'internal_links': internal, 'external_links': external, 'errors': errors}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('site', type=Path)
    args = parser.parse_args()
    result = check_site(args.site)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 1 if result['errors'] or not result['html_pages'] else 0


if __name__ == '__main__':
    raise SystemExit(main())
