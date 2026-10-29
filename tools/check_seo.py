"""Check static search metadata against the generated tree without network IO."""
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit
from urllib.robotparser import RobotFileParser
import argparse
import base64
import hashlib
import json
import re
import xml.etree.ElementTree as ET

ORIGIN = 'https://thinkpadarchive.com'
NS = {'s': 'http://www.sitemaps.org/schemas/sitemap/0.9'}


class Head(HTMLParser):
    def __init__(self, text):
        super().__init__(convert_charrefs=True)
        self.links, self.metadata, self.titles, self.schema, self.model_rows = [], [], [], [], []
        self.language = ''
        self.inside = False
        self.capture = None
        self.feed(text)
        self.close()

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == 'html':self.language = a.get('lang', '')
        if tag == 'head':self.inside = True
        if tag == 'tr' and 'data-model-id' in a:self.model_rows.append(a)
        if not self.inside:return
        if tag == 'link':self.links.append(a)
        if tag == 'meta':self.metadata.append(a)
        if tag == 'title':self.titles.append('');self.capture = self.titles
        if tag == 'script' and a.get('type') == 'application/ld+json':
            self.schema.append('');self.capture = self.schema

    def handle_data(self, data):
        if self.capture is not None:self.capture[-1] += data

    def handle_endtag(self, tag):
        if tag in ('title', 'script'):self.capture = None
        if tag == 'head':self.inside = False

    def values(self, key):
        return [a.get('content', '') for a in self.metadata if key in (a.get('name'), a.get('property'), a.get('http-equiv'))]


def check_seo(root):
    root = Path(root).resolve(strict=True)
    errors, pages, canonicals, alternate_maps = [], {}, {}, {}

    def fail(page, reason):
        errors.append({'page': page, 'reason': reason})

    def local_url(value):
        if not isinstance(value, str):return None
        try:
            parts = urlsplit(value)
        except ValueError:
            return None
        if (parts.scheme != 'https' or parts.netloc != 'thinkpadarchive.com' or parts.query or parts.fragment or
                not parts.path.startswith('/') or '\\' in parts.path or '..' in unquote(parts.path).split('/')):
            return None
        relative = unquote(parts.path.lstrip('/'))
        path = (root / relative / 'index.html') if parts.path.endswith('/') else root / relative
        path = path.resolve()
        return path if path.is_relative_to(root) and path.is_file() else None

    languages = {p.name for p in root.iterdir() if p.is_dir() and (p / 'index.html').is_file()}
    for path in sorted(root.rglob('*.html')):
        relative = path.relative_to(root).as_posix()
        head = Head(path.read_text(encoding='utf-8'));pages[relative] = head
        canonical = [a.get('href', '') for a in head.links if a.get('rel') == 'canonical']
        if len(canonical) != 1 or local_url(canonical[0]) is None:
            fail(relative, 'invalid-canonical');continue
        canonicals[relative] = canonical[0]
        aliases = relative == 'index.html' or relative.endswith(('/index.html', '/catalogue.html'))
        expected = ORIGIN + ('/' + head.language + '/' if aliases else '/' + relative)
        if canonical[0] != expected:fail(relative, 'wrong-canonical-route')
        alternates = [a for a in head.links if a.get('rel') == 'alternate']
        codes = [a.get('hreflang', '') for a in alternates]
        if len(codes) != len(set(codes)) or set(codes) != languages | {'x-default'}:
            fail(relative, 'invalid-alternate-languages')
        mapping = {a.get('hreflang'): a.get('href', '') for a in alternates}
        alternate_maps[relative] = mapping
        for code, value in mapping.items():
            target = local_url(value)
            if target is None:fail(relative, 'missing-or-unsafe-alternate');continue
            suffix = '' if aliases else relative.split('/', 1)[-1]
            if code != 'x-default' and value != ORIGIN + '/' + code + '/' + suffix:
                fail(relative, 'wrong-alternate-route')
        if mapping.get(head.language) != canonical[0]:fail(relative, 'alternate-missing-self')
        if mapping.get('x-default') not in {mapping.get(code) for code in languages}:
            fail(relative, 'invalid-xdefault')
        for key in ('description', 'og:title', 'og:description', 'og:url', 'Content-Security-Policy'):
            values = head.values(key)
            if len(values) != 1 or not values[0].strip():fail(relative, 'missing-or-repeated-' + key)
        if len(head.titles) != 1 or head.titles != head.values('og:title'):fail(relative, 'title-mismatch')
        if head.values('description') != head.values('og:description'):fail(relative, 'description-mismatch')
        if head.values('og:url') != canonical:fail(relative, 'social-canonical-mismatch')
        robots = head.values('robots')
        year_match = re.search(r'/years/([^/]+)\.html$', relative)
        empty_year = bool(year_match and (year_match[1] == 'unknown' or not any('hidden' not in row for row in head.model_rows)))
        should_noindex = relative.endswith('/stats.html') or empty_year
        if should_noindex and robots != ['noindex,follow']:fail(relative, 'missing-noindex')
        if not should_noindex and any('noindex' in value for value in robots):fail(relative, 'unexpected-noindex')
        try:
            if len(head.schema) != 1:raise ValueError('one graph required')
            raw = head.schema[0]
            schema = json.loads(raw);nodes = schema['@graph']
            sites = [n for n in nodes if n.get('@type') == 'WebSite']
            web = [n for n in nodes if n.get('@type') in ('WebPage', 'CollectionPage')]
            if (schema.get('@context') != 'https://schema.org' or len(sites) != 1 or len(web) != 1 or
                    sites[0].get('url') != ORIGIN + '/' or sites[0].get('name') != 'ThinkPad Archive' or
                    web[0].get('url') != canonical[0] or web[0].get('inLanguage') != head.language or
                    [web[0].get('name')] != head.values('og:title') or '<' in raw):
                raise ValueError('wrong graph')
            digest = base64.b64encode(hashlib.sha256(raw.encode()).digest()).decode()
            csp = head.values('Content-Security-Policy')[0]
            script = next(rule for rule in csp.split(';') if rule.strip().startswith('script-src '))
            if "'sha256-" + digest + "'" not in script or 'unsafe-inline' in csp:
                raise ValueError('CSP does not bind JSON')
        except (ValueError, KeyError, TypeError, IndexError, StopIteration):
            fail(relative, 'invalid-schema-or-csp')

    for relative, mapping in alternate_maps.items():
        for value in mapping.values():
            target = local_url(value)
            if target is None:continue
            target_name = target.relative_to(root).as_posix()
            if alternate_maps.get(target_name) != mapping:fail(relative, 'nonreciprocal-alternates')
            if canonicals.get(target_name) != value:fail(relative, 'noncanonical-alternate')

    expected_urls = {value for relative, value in canonicals.items()
                     if not any('noindex' in rule for rule in pages[relative].values('robots'))}
    sitemap_urls = []
    try:
        tree = ET.parse(root / 'sitemap.xml').getroot()
        if tree.tag != '{' + NS['s'] + '}urlset':raise ValueError('wrong namespace')
        sitemap_urls = [n.text for n in tree.findall('s:url/s:loc', NS)]
        if (not sitemap_urls or len(sitemap_urls) != len(set(sitemap_urls)) or
                set(sitemap_urls) != expected_urls or any(local_url(value) is None for value in sitemap_urls)):
            fail('sitemap.xml', 'invalid-sitemap-membership')
        if any(n.tag.rsplit('}', 1)[-1] in ('lastmod', 'changefreq', 'priority') for n in tree.iter()):
            fail('sitemap.xml', 'unsupported-sitemap-hints')
    except (OSError, ET.ParseError, ValueError, TypeError):
        fail('sitemap.xml', 'missing-or-invalid-sitemap')
    try:
        text = (root / 'robots.txt').read_text(encoding='utf-8')
        robot = RobotFileParser();robot.parse(text.splitlines())
        if robot.site_maps() != [ORIGIN + '/sitemap.xml']:fail('robots.txt', 'missing-sitemap-announcement')
        for agent in ('Googlebot', 'bingbot'):
            if any(not robot.can_fetch(agent, url) for url in expected_urls | {ORIGIN + '/assets/style.css', ORIGIN + '/en/stats.html'}):
                fail('robots.txt', 'catalogue-or-assets-blocked')
            if any(robot.can_fetch(agent, ORIGIN + route) for route in ('/api/stats/summary', '/_deploy/github', '/healthz')):
                fail('robots.txt', 'operational-route-allowed')
    except (OSError, UnicodeError):fail('robots.txt', 'missing-or-invalid-robots')
    if not pages:fail('.', 'no-pages')
    return {'html_pages': len(pages), 'sitemap_urls': len(sitemap_urls), 'errors': errors}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('site', type=Path)
    args = parser.parse_args(argv)
    try:
        result = check_seo(args.site)
    except (OSError, ValueError, UnicodeError):
        print('error: SEO check could not inspect the generated site')
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return int(bool(result['errors']))


if __name__ == '__main__':raise SystemExit(main())
