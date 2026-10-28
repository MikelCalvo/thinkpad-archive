"""0.4.3 navigation, local preference and favicon contracts."""
from html.parser import HTMLParser
from pathlib import Path
import json
import os
import re
import shutil
import subprocess
import tempfile
import unittest
import xml.etree.ElementTree as ET

import test_build as fixtures
import test_release_integration as profiles
from thinkpad_archive import build_site

ROOT = Path(__file__).resolve().parents[1]


class Tags(HTMLParser):
    def __init__(self, text):
        super().__init__(convert_charrefs=True)
        self.tags = []
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        self.tags.append((tag, dict(attrs)))


class NavigationRefresh(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=os.environ.get('TMPDIR'))
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        records = fixtures.fixture_data()
        records['models']['models'][0]['introduced'] = [
            {'year': 1992, 'variants': ['700C'], 'url': 'https://example.org/history'}]
        fixtures.write_fixture(self.root / 'data', records)
        (self.root / 'data/profiles.json').write_text(json.dumps(profiles.profiles_for(records)))
        self.site = build_site(self.root / 'site', data_dir=self.root / 'data')

    def test_favicon_is_local_and_declared_on_every_page(self):
        icon = self.site / 'favicon.svg'
        self.assertTrue(icon.is_file(), 'Original red TrackPoint favicon is missing')
        svg = ET.fromstring(icon.read_text())
        self.assertEqual(svg.attrib.get('viewBox'), '0 0 64 64')
        self.assertNotIn('https:', icon.read_text())
        for page in self.site.rglob('*.html'):
            with self.subTest(page=str(page.relative_to(self.site))):
                tags = Tags(page.read_text()).tags
                icons = [a for tag, a in tags if tag == 'link' and a.get('rel') == 'icon']
                self.assertEqual(len(icons), 1)
                self.assertEqual(icons[0].get('type'), 'image/svg+xml')
                self.assertEqual((page.parent / icons[0]['href']).resolve(), icon.resolve())
                csp = next(a['content'] for tag, a in tags if a.get('http-equiv') == 'Content-Security-Policy')
                self.assertIn("img-src 'self'", csp)

    def test_navigation_is_left_and_language_picker_precedes_theme(self):
        for page in self.site.rglob('*.html'):
            with self.subTest(page=str(page.relative_to(self.site))):
                text = page.read_text()
                header = text.split('<header', 1)[1].split('</header>', 1)[0]
                self.assertLess(header.index('class="main-nav"'), header.index('id="language-picker"'))
                self.assertLess(header.index('id="language-picker"'), header.index('id="theme-toggle"'))
                self.assertLess(header.index('id="theme-toggle"'), header.index('class="github-link'))
                picker = header.split('id="language-picker"', 1)[1].split('</details>', 1)[0]
                tags = Tags(picker).tags
                self.assertTrue(any(tag == 'summary' and a.get('aria-label') for tag, a in tags))
                self.assertIn('<svg', picker)
                self.assertIn('class="language-nav"', picker)
                self.assertEqual({a['data-language-choice'] for tag, a in tags if 'data-language-choice' in a}, {'en', 'es'})

    def test_subpage_home_icon_precedes_catalogue_without_a_brand_row(self):
        for lang in ('en', 'es'):
            for suffix in ('models/700c.html', 'sources.html', 'catalogue.html', 'years/1992.html'):
                with self.subTest(lang=lang, page=suffix):
                    page = self.site / lang / suffix
                    text = page.read_text()
                    header = text.split('<header', 1)[1].split('</header>', 1)[0]
                    nav = header.split('class="main-nav"', 1)[1].split('</nav>', 1)[0]
                    links = [a for tag, a in Tags(nav).tags if tag == 'a']
                    self.assertEqual(len(links), 3)
                    self.assertEqual(links[0].get('class'), 'home-link')
                    self.assertEqual((page.parent / links[0]['href']).resolve(), (self.site / lang / 'index.html').resolve())
                    self.assertEqual(links[0].get('aria-label'), 'Home' if lang == 'en' else 'Inicio')
                    icon = nav.split('</a>', 1)[0]
                    self.assertIn('<svg', icon)
                    self.assertIn('aria-hidden="true"', icon)
                    self.assertIn('<path', icon)
                    self.assertNotIn('ThinkPad', re.sub(r'<[^>]+>', '', header))
                    self.assertNotIn('brandbar', text)
                    self.assertNotIn('site-brand', text)
                    self.assertNotIn('class="design-location"', text)
                    self.assertNotIn('class="breadcrumb"', text)
                    self.assertNotIn('Back to catalogue', text.split('<main', 1)[1])
                    self.assertNotIn('Volver al catálogo', text.split('<main', 1)[1])
            home = (self.site / lang / 'index.html').read_text()
            self.assertNotIn('class="home-link"', home)
            self.assertNotIn('site-brand', home)
            self.assertIn('class="archive-title"', home)

    def test_language_bootstrap_and_same_page_fallback_targets(self):
        self.assertTrue((self.site / 'assets/language.js').is_file())
        root = (self.site / 'index.html').read_text()
        self.assertIn('<html lang="en" data-language-entry="true"', root)
        for relative in ('index.html', 'es/models/700c.html', 'en/years/1992.html', 'es/sources.html'):
            page = self.site / relative
            text = page.read_text()
            tags = Tags(text).tags
            script = next((a for tag, a in tags if tag == 'script' and a.get('src', '').endswith('/language.js')), None)
            self.assertIsNotNone(script)
            assert script is not None
            self.assertNotIn('defer', script)
            self.assertLess(text.index(script['src']), text.index('rel="stylesheet"'))
            alternates = [a for tag, a in tags if tag == 'link' and a.get('rel') == 'alternate']
            self.assertEqual({a['hreflang'] for a in alternates}, {'en', 'es'})
            for a in alternates:
                suffix = relative.split('/', 1)[1] if '/' in relative else 'index.html'
                self.assertEqual((page.parent / a['href']).resolve(), (self.site / a['hreflang'] / suffix).resolve())
        self.assertNotIn('data-language-entry="true"', (self.site / 'es/index.html').read_text())

    @unittest.skipUnless(shutil.which('node'), 'Node is optional verification tooling')
    def test_language_preference_entry_storage_refusal_and_explicit_deep_links(self):
        script = ROOT / 'assets/language.js'
        self.assertTrue(script.is_file(), 'Language preference bootstrap is missing')
        js = r'''
const assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs');
const source=fs.readFileSync(process.argv[1],'utf8');
function start(saved, {entry=false,lang='en',blocked=false}={}) {
 const events={},writes=[],redirects=[],choices=[];
 function link(code){const handlers={},attrs={'hreflang':code,'href':code+'/index.html','data-language-choice':code};const a={handlers,href:code+'/index.html',getAttribute:k=>attrs[k],setAttribute(k,v){attrs[k]=v;},addEventListener:(k,f)=>handlers[k]=f};return a;}
 const alternatives=[link('en'),link('es')],links=[link('en'),link('es')];
 const root={getAttribute:k=>({'lang':lang,'data-language-entry':entry?'true':null}[k])};
 const picker={open:false,contains:()=>false,querySelector:()=>({focus(){}})};
 const document={documentElement:root,readyState:'loading',querySelectorAll:s=>s.includes('alternate')?alternatives:links,getElementById:()=>picker,addEventListener:(k,f)=>events[k]=f};
 const location={search:'?q=1',hash:'#manuals',replace:u=>redirects.push(u)};
 const context={document,window:{location,addEventListener(){}},location,localStorage:{getItem(){if(blocked)throw Error('blocked');return saved;},setItem(k,v){if(blocked)throw Error('blocked');writes.push([k,v]);}}};
 vm.runInNewContext(source,context);if(events.DOMContentLoaded)events.DOMContentLoaded();
 return {events,writes,redirects,links,picker};
}
assert.deepEqual(start(null,{entry:true}).redirects,[]);
assert.deepEqual(start('es',{entry:true}).redirects,['es/index.html?q=1#manuals']);
assert.deepEqual(start('en',{entry:true}).redirects,[]);
assert.deepEqual(start('invalid',{entry:true}).redirects,[]);
assert.deepEqual(start('es',{entry:false,lang:'en'}).redirects,[]);
assert.deepEqual(start('en',{entry:false,lang:'es'}).redirects,[]);
assert.deepEqual(start('es',{entry:true,blocked:true}).redirects,[]);
const explicit=start(null);explicit.links[1].handlers.click({button:0});assert.deepEqual(explicit.writes,[['thinkpad-archive-language','es']]);
const denied=start(null,{blocked:true});denied.links[1].handlers.click({button:0});assert.equal(denied.writes.length,0);
console.log('language preferences and explicit deep links passed');
'''
        result = subprocess.run(['node', '-e', js, str(script)], text=True, capture_output=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('language preferences and explicit deep links passed', result.stdout)


if __name__ == '__main__':
    unittest.main()
