"""Technical SEO through actual rendered builds, without a search-engine account."""
from html.parser import HTMLParser
from pathlib import Path
import base64
import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from urllib.parse import urlsplit
import xml.etree.ElementTree as ET

import test_build as fixtures
from thinkpad_archive import build_site
from thinkpad_archive.offline_release import build_offline_release

ROOT = Path(__file__).resolve().parents[1]
ORIGIN = 'https://thinkpadarchive.com'
NS = {'s': 'http://www.sitemaps.org/schemas/sitemap/0.9'}


class Head(HTMLParser):
    def __init__(self, text):
        super().__init__(convert_charrefs=True)
        self.links, self.meta, self.json_texts, self.titles = [], {}, [], []
        self.in_head = False
        self.capture = None
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == 'head':self.in_head = True
        if not self.in_head:return
        if tag == 'link':self.links.append(a)
        if tag == 'meta':self.meta[a.get('name', a.get('http-equiv', a.get('property')))] = a.get('content')
        if tag == 'title':self.capture = 'title';self.titles.append('')
        if tag == 'script' and a.get('type') == 'application/ld+json':
            self.capture = 'json';self.json_texts.append('')

    def handle_data(self, data):
        if self.capture == 'title':self.titles[-1] += data
        if self.capture == 'json':self.json_texts[-1] += data

    def handle_endtag(self, tag):
        if tag in ('title', 'script'):self.capture = None
        if tag == 'head':self.in_head = False

    def canonical(self):
        return [a['href'] for a in self.links if a.get('rel') == 'canonical']

    def alternates(self):
        return {a['hreflang']: a['href'] for a in self.links if a.get('rel') == 'alternate'}


def tool(name):
    path = ROOT / 'tools' / (name + '.py')
    if not path.is_file():raise AssertionError('SEO verifier is missing')
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:raise AssertionError('Could not load verifier')
    module = importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module


class TechnicalSEO(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory(dir=os.environ.get('TMPDIR'))
        cls.addClassCleanup(cls.tmp.cleanup)
        cls.root = Path(cls.tmp.name)
        records = fixtures.fixture_data()
        records['models']['models'][0]['introduced'] = [{'year': 1992, 'variants': ['700C'], 'url': 'https://example.org/date'}]
        records['models']['models'][1]['introduced'] = [{'year': 1994, 'variants': ['X230t'], 'url': 'https://example.org/date'}]
        fixtures.write_fixture(cls.root / 'data', records)
        cls.site = build_site(cls.root / 'site', data_dir=cls.root / 'data')

    def head(self, path):return Head((self.site / path).read_text())

    def test_sitemap_is_deterministic_unique_canonical_and_excludes_thin_or_operational_routes(self):
        path = self.site / 'sitemap.xml'
        self.assertTrue(path.is_file(), 'Generated XML sitemap is missing')
        tree = ET.fromstring(path.read_bytes())
        urls = [n.text or '' for n in tree.findall('s:url/s:loc', NS)]
        expected = {ORIGIN + '/' + code + '/' + suffix for code in ('en', 'es') for suffix in (
            '', 'sources.html', 'models/700c.html', 'models/700cs.html', 'models/x230-tablet.html',
            'years/1992.html', 'years/1994.html')}
        self.assertEqual(set(urls), expected)
        self.assertEqual(urls, sorted(set(urls)))
        self.assertNotIn('lastmod', path.read_text())
        self.assertNotIn('priority', path.read_text())
        self.assertNotIn('changefreq', path.read_text())
        other = build_site(self.root / 'same-inputs', data_dir=self.root / 'data')
        self.assertEqual(path.read_bytes(), (other / 'sitemap.xml').read_bytes())

    def test_robots_announces_sitemap_and_does_not_hide_assets_or_noindex_pages(self):
        path = self.site / 'robots.txt'
        self.assertTrue(path.is_file(), 'Generated robots.txt is missing')
        text = path.read_text()
        self.assertIn('User-agent: *', text)
        self.assertIn('Sitemap: ' + ORIGIN + '/sitemap.xml', text)
        from urllib.robotparser import RobotFileParser
        robots = RobotFileParser();robots.parse(text.splitlines())
        for agent in ('Googlebot', 'bingbot', 'DuckDuckBot'):
            for route in ('/en/', '/es/models/700c.html', '/en/stats.html', '/assets/style.css', '/en/catalogue.html'):
                self.assertTrue(robots.can_fetch(agent, ORIGIN + route))
            for route in ('/api/stats/summary', '/_deploy/github', '/healthz'):
                self.assertFalse(robots.can_fetch(agent, ORIGIN + route))

    def test_absolute_reciprocal_alternates_and_same_language_canonicals(self):
        for suffix, canonical_suffix in [('index.html', ''), ('catalogue.html', ''), ('models/700c.html', 'models/700c.html'), ('sources.html', 'sources.html'), ('years/1992.html', 'years/1992.html')]:
            expected = {lang: ORIGIN + '/' + lang + '/' + canonical_suffix for lang in ('en', 'es')}
            expected['x-default'] = expected['en']
            for lang in ('en', 'es'):
                head = self.head(lang + '/' + suffix)
                self.assertEqual(head.canonical(), [expected[lang]])
                self.assertEqual(head.alternates(), expected)
                body = (self.site / (lang + '/' + suffix)).read_text().split('<body', 1)[1]
                self.assertNotIn('href="' + expected['en'] + '"', body)
        self.assertEqual(self.head('index.html').alternates()['x-default'], ORIGIN + '/en/')

    def test_stats_unknown_and_empty_years_noindex_but_catalogue_models_indexable(self):
        for lang in ('en', 'es'):
            for suffix in ('stats.html', 'years/unknown.html', 'years/1993.html'):
                self.assertEqual(self.head(lang + '/' + suffix).meta.get('robots'), 'noindex,follow')
            for suffix in ('index.html', 'catalogue.html', 'models/700c.html', 'years/1992.html'):
                self.assertNotIn('noindex', self.head(lang + '/' + suffix).meta.get('robots', ''))
            home, stats = self.head(lang + '/index.html'), self.head(lang + '/stats.html')
            self.assertNotEqual(home.meta['description'], stats.meta['description'])
            self.assertEqual(stats.titles, [stats.meta['og:title']])
            self.assertEqual(home.titles, [home.meta['og:title']])
            self.assertNotEqual(home.titles, ['Catalogue · ThinkPad Archive'])

    def test_structured_data_matches_page_and_exact_csp_hash_without_unsafe_inline(self):
        for name in ('index.html', 'en/index.html', 'es/models/700c.html', 'en/sources.html'):
            head = self.head(name)
            self.assertEqual(len(head.json_texts), 1, 'One inert JSON-LD graph is required')
            raw = head.json_texts[0];graph = json.loads(raw)
            self.assertEqual(graph['@context'], 'https://schema.org')
            nodes = graph['@graph']
            site = next(n for n in nodes if n['@type'] == 'WebSite')
            self.assertEqual(site['url'], ORIGIN + '/')
            self.assertEqual(site['name'], 'ThinkPad Archive')
            page = next(n for n in nodes if n['@type'] in ('WebPage', 'CollectionPage'))
            self.assertEqual(page['url'], head.canonical()[0])
            self.assertEqual(page['name'], head.meta['og:title'])
            self.assertEqual(page['inLanguage'], 'es' if name.startswith('es/') else 'en')
            self.assertFalse(any(n['@type'] in ('Product', 'Review', 'AggregateRating') for n in nodes))
            digest = base64.b64encode(hashlib.sha256(raw.encode()).digest()).decode()
            self.assertIn("'sha256-" + digest + "'", head.meta['Content-Security-Policy'])
            self.assertNotIn('unsafe-inline', head.meta['Content-Security-Policy'])
            self.assertNotIn('SearchAction', raw)

    def test_hostile_model_text_cannot_terminate_json_or_add_markup(self):
        from thinkpad_archive.render import Renderer
        from thinkpad_archive.validation import load_catalogue, load_locales
        renderer = Renderer(load_catalogue(self.root / 'data'), load_locales(ROOT / 'locales'))
        model = dict(renderer.data['models'][0], name='ThinkPad </script><script>alert(1)</script> & "quote"')
        text = renderer.model('en/models/700c.html', 'en', model)
        head = Head(text)
        self.assertEqual(len(head.json_texts), 1)
        self.assertNotIn('</script>', head.json_texts[0])
        page = next(n for n in json.loads(head.json_texts[0])['@graph'] if n['@type'] == 'WebPage')
        self.assertIn(model['name'], page['name'])
        self.assertNotIn('<script>alert(1)</script>', text)

    def test_spanish_default_has_correct_xdefault_without_changing_model_language(self):
        site = build_site(self.root / 'spanish-root', data_dir=self.root / 'data', default_language='es')
        for lang in ('en', 'es'):
            head = Head((site / lang / 'models/700c.html').read_text())
            self.assertEqual(head.alternates().get('x-default'), ORIGIN + '/es/models/700c.html')
            self.assertEqual(head.canonical(), [ORIGIN + '/' + lang + '/models/700c.html'])

    def test_offline_archive_includes_verified_public_crawler_files_without_collection(self):
        import zipfile
        out = build_offline_release(self.root / 'offline', data_dir=self.root / 'data')
        archive = next(out.glob('*.zip'));prefix = 'thinkpad-archive-' + (ROOT / 'VERSION').read_text().strip() + '/'
        with zipfile.ZipFile(archive) as z:
            for name in ('robots.txt', 'sitemap.xml'):
                self.assertIn(prefix + name, z.namelist())
                self.assertEqual(z.read(prefix + name), (self.site / name).read_bytes())
            self.assertNotIn(b'data-stats-enabled="true"', z.read(prefix + 'en/models/700c.html'))

    def test_real_generated_tree_seo_verifier_and_cli_fail_on_corrupt_alternate(self):
        checker = tool('check_seo')
        result = checker.check_seo(self.site)
        self.assertEqual(result['errors'], [])
        self.assertGreater(result['sitemap_urls'], 0)
        victim = self.site / 'en/models/700c.html';original = victim.read_text()
        try:
            victim.write_text(original.replace('hreflang="es" href="' + ORIGIN + '/es/models/700c.html"', 'hreflang="es" href="' + ORIGIN + '/es/models/missing.html"'))
            self.assertTrue(checker.check_seo(self.site)['errors'])
            run = subprocess.run([sys.executable, str(ROOT / 'tools/check_seo.py'), str(self.site)], capture_output=True, text=True, timeout=20)
            self.assertNotEqual(run.returncode, 0)
        finally:victim.write_text(original)

    def test_verifier_refuses_invalid_sitemap_robots_json_csp_and_duplicate_metadata(self):
        checker = tool('check_seo')
        cases = (
            ('sitemap.xml', ORIGIN + '/en/models/700c.html', 'https://example.org/en/models/700c.html'),
            ('robots.txt', 'Disallow: /api/', 'Disallow: /'),
            ('en/models/700c.html', 'application/ld+json', 'application/json'),
            ('en/models/700c.html', 'sha256-', 'sha384-'),
            ('en/models/700c.html', '<meta name="description"', '<meta name="description" content="duplicate"><meta name="description"'),
            ('en/stats.html', 'content="noindex,follow"', 'content="index,follow"'),
        )
        for name, old, new in cases:
            with self.subTest(member=name, replacement=new):
                path = self.site / name;original = path.read_text()
                self.assertIn(old, original)
                try:
                    path.write_text(original.replace(old, new, 1))
                    self.assertTrue(checker.check_seo(self.site)['errors'])
                finally:path.write_text(original)

    def test_language_bootstrap_prefers_relative_offline_targets_over_public_metadata(self):
        import shutil
        if not shutil.which('node'):self.skipTest('Node required for script verification')
        code = r'''const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const alternatives=['en','es'].map(code=>({getAttribute:k=>({'hreflang':code,'href':'https://thinkpadarchive.com/'+code+'/', 'data-language-target':code+'/index.html'}[k]||null)}));
const redirects=[];const document={documentElement:{getAttribute:k=>k==='lang'?'en':'true'},querySelectorAll:()=>alternatives,readyState:'loading',addEventListener(){}};
const location={search:'?year=1992',hash:'#main',replace:u=>redirects.push(u)};
vm.runInNewContext(fs.readFileSync(process.argv[1],'utf8'),{document,localStorage:{getItem:()=> 'es'},window:{location},location});
assert.deepEqual(redirects,['es/index.html?year=1992#main']);'''
        run = subprocess.run(['node', '-e', code, str(ROOT / 'assets/language.js')], capture_output=True, text=True, timeout=15)
        self.assertEqual(run.returncode, 0, run.stderr)

    def test_check_runner_calls_real_seo_verifier_after_each_build(self):
        runner = tool('check');calls = []
        with tempfile.TemporaryDirectory(dir=os.environ.get('TMPDIR')) as tmp:
            def run(argv, **kwargs):calls.append(argv);return subprocess.CompletedProcess(argv, 0)
            with patch.object(runner.subprocess, 'run', side_effect=run):runner.check_project(Path(tmp) / 'check')
        self.assertEqual(sum(any(str(x).endswith('check_seo.py') for x in a) for a in calls), 3)


if __name__ == '__main__':unittest.main()
