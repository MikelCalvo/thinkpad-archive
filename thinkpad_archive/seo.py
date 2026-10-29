"""Technical search metadata derived only from the validated public catalogue."""
import base64
import hashlib
import json
import xml.etree.ElementTree as ET

from .social import SITE_ORIGIN, page_metadata


def canonical_url(current, lang, kind):
    return SITE_ORIGIN + ('/' + lang + '/' if kind in ('home', 'all') else '/' + current)


def structured_page(current, lang, title, kind, selection, translations):
    """Return inert escaped JSON-LD plus its exact CSP source hash."""
    heading, _, canonical = page_metadata(current, lang, title, kind, selection, translations)
    website = {'@type': 'WebSite', '@id': SITE_ORIGIN + '/#website',
               'name': translations['site_name'], 'url': SITE_ORIGIN + '/'}
    page = {'@type': 'CollectionPage' if kind in ('home', 'all', 'year') else 'WebPage',
            '@id': canonical + '#webpage', 'url': canonical, 'name': heading,
            'inLanguage': lang, 'isPartOf': {'@id': website['@id']}}
    if kind == 'model':
        page['about'] = {'@type': 'Thing', 'name': title}
    value = json.dumps({'@context': 'https://schema.org', '@graph': [website, page]},
                       ensure_ascii=False, sort_keys=True, separators=(',', ':'))
    # HTML script raw text does not decode entities. Escape potential end tags.
    value = value.replace('&', '\\u0026').replace('<', '\\u003c').replace('>', '\\u003e')
    digest = base64.b64encode(hashlib.sha256(value.encode('utf-8')).digest()).decode('ascii')
    return '<script type="application/ld+json">' + value + '</script>\n', "'sha256-" + digest + "'"


def crawler_files(data, locales):
    """Emit one canonical URL per useful translated page, without false dates."""
    years = sorted({r['year'] for model in data['models'] for r in model.get('introduced', [])})
    routes = set()
    for code in locales:
        routes.update(SITE_ORIGIN + '/' + code + '/' + suffix for suffix in ('', 'sources.html'))
        routes.update(SITE_ORIGIN + '/' + code + '/models/' + model['id'] + '.html' for model in data['models'])
        routes.update(SITE_ORIGIN + '/' + code + '/years/' + str(year) + '.html' for year in years)
    namespace = 'http://www.sitemaps.org/schemas/sitemap/0.9'
    ET.register_namespace('', namespace)
    tree = ET.Element('{' + namespace + '}urlset')
    for route in sorted(routes):
        row = ET.SubElement(tree, '{' + namespace + '}url')
        ET.SubElement(row, '{' + namespace + '}loc').text = route
    ET.indent(tree, space='  ')
    sitemap = ET.tostring(tree, encoding='unicode', xml_declaration=True) + '\n'
    robots = ('User-agent: *\nDisallow: /api/\nDisallow: /_deploy/\nDisallow: /healthz\n\n'
              'Sitemap: ' + SITE_ORIGIN + '/sitemap.xml\n')
    return {'robots.txt': robots, 'sitemap.xml': sitemap}
