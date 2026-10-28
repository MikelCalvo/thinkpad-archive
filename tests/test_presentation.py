"""Presentation regressions: original synthetic metadata, no vendor files."""
from pathlib import Path
from html.parser import HTMLParser
import importlib.util
import json
import os
import shutil
import subprocess
import tempfile
import unittest

import test_build as fixtures

ROOT = Path(__file__).resolve().parents[1]


class Page(HTMLParser):
    def __init__(self, text):
        super().__init__(convert_charrefs=True)
        self.tags = []
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        self.tags.append((tag, dict(attrs)))


class Presentation(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=os.environ.get('TMPDIR'))
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.data = self.root / 'data'
        records = fixtures.fixture_data()
        records['drivers']['drivers'] += [
            dict(records['drivers']['drivers'][0], id='audio-second', title='A second audio package'),
            dict(records['drivers']['drivers'][0], id='ethernet', title='Ethernet package', category='Networking: LAN (Ethernet)'),
            dict(records['drivers']['drivers'][0], id='unknown', title='Unknown-category package', category='<Odd & source>'),
        ]
        records['models']['models'][0]['driver_ids'] += ['ethernet', 'audio-second', 'unknown']
        fixtures.write_fixture(self.data, records)
        import thinkpad_archive
        self.output = thinkpad_archive.build_site(self.root / 'site', data_dir=self.data)

    def text(self, relative):
        return (self.output / relative).read_text()

    def test_home_brand_replaces_tagline_and_intro_both_languages(self):
        for lang in ('en', 'es'):
            text = self.text(lang + '/index.html')
            self.assertIn('<h1 class="archive-title" aria-label="ThinkPad Archive">', text)
            self.assertIn('<span class="archive-word" aria-hidden="true">Archive</span>', text)
            self.assertNotIn('class="lede"', text)
            self.assertNotIn('from the earliest ThinkPads', text)
            self.assertNotIn('desde los primeros ThinkPad', text)
            self.assertNotIn('Los primeros equipos tienen prioridad', text)
        self.assertIn('class="archive-title"', self.text('index.html'))

    def test_title_leads_directly_to_timeline_without_stats_or_numbered_headings(self):
        for lang in ('en', 'es'):
            text = self.text(lang + '/index.html')
            self.assertNotIn('class="stats"', text)
            self.assertNotIn('class="section-number"', text)
            self.assertNotIn('class="section-heading"', text)
            self.assertNotIn('id="catalogue-heading"', text)
            self.assertNotIn('id="manuals-heading"', text)
            self.assertNotIn('id="utilities-heading"', text)
            self.assertIn('</h1></section><section aria-label=', text)
            self.assertIn('<h2 id="selected-year" class="visually-hidden">', text)
            self.assertNotIn('reference-library', text)
            self.assertNotIn('<article class="document">', text)
            self.assertNotIn('<article class="utility">', text)
        css = (self.output/'assets/style.css').read_text()
        hero = css.split('.hero{', 1)[1].split('}', 1)[0]
        self.assertNotIn('border-bottom:', hero)
        self.assertIn('padding-bottom:0', hero)

    def test_general_notice_is_absent_but_firmware_warning_remains(self):
        for path in self.output.rglob('*.html'):
            text = path.read_text()
            self.assertNotIn('dismissible-notice', text)
            self.assertNotIn('data-dismiss-notice', text)
            self.assertNotIn('Source metadata. Not a compatibility certification.', text)
            self.assertNotIn('Metadatos de fuentes. No certifica compatibilidad.', text)
            self.assertNotIn('A manufacturer listing is not a verified download', text)
            self.assertNotIn('Un listado del fabricante no acredita', text)
        for lang in ('en', 'es'):
            text = self.text(lang + '/models/700c.html')
            firmware = text.split('<section id="firmware"', 1)[1]
            self.assertIn('class="firmware-warning"', firmware)
            self.assertNotIn('data-dismiss-notice', firmware)
            self.assertIn('src="../../assets/ui.js"', text)

    def test_categories_have_icons_counts_navigation_and_all_exact_packages(self):
        for lang, audio, network in [('en', 'Audio', 'Networking'), ('es', 'Audio', 'Redes')]:
            text = self.text(lang + '/models/700c.html')
            parser = Page(text)
            groups = [a for tag, a in parser.tags if tag == 'details' and a.get('class') == 'driver-category']
            ids = {a['id'] for a in groups}
            self.assertEqual(ids, {'drivers-cat-audio', 'drivers-cat-network', 'drivers-cat-other', 'firmware-cat-bios'})
            self.assertTrue(all('open' not in a for a in groups))
            self.assertIn('data-category-target="drivers-cat-audio"', text)
            self.assertIn('data-category-target="drivers-cat-network"', text)
            self.assertIn('class="category-icon" aria-hidden="true"', text)
            self.assertIn(audio, text)
            self.assertIn(network, text)
            self.assertIn('class="category-count">2</span>', text)
            for title in ['Audio Features', 'A second audio package', 'Ethernet package', 'Unknown-category package', 'System Program']:
                self.assertEqual(text.count('<h3>' + title + '</h3>'), 1)
            self.assertIn('&lt;Odd &amp; source&gt;', text)
            self.assertGreater(text.index('System Program'), text.index('<section id="firmware"'))
            self.assertLess(text.index('A second audio package'), text.index('Audio Features'))

    @unittest.skipUnless(shutil.which('node'), 'Node is optional verification tooling')
    def test_real_ui_script_opens_category_without_general_notice(self):
        script = ROOT / 'assets/ui.js'
        self.assertTrue(script.is_file(), 'progressive presentation API is missing')
        js = r'''
const assert = require('node:assert/strict');
const events = {};
let focused=0, scrolled=0;
const group = {open:false,querySelector:()=>({focus(){focused++;}}),scrollIntoView(){scrolled++;}};
const jump = {getAttribute:()=> 'drivers-cat-audio',addEventListener:(k,f)=>events.jump=f};
global.document = {querySelectorAll:s=>s==='[data-category-target]'?[jump]:[],getElementById:id=>id==='drivers-cat-audio'?group:null};
require(process.argv[1]);
let prevented=0;events.jump({preventDefault(){prevented++;}});
assert.equal(group.open,true);assert.equal(focused,1);assert.equal(scrolled,1);assert.equal(prevented,1);
console.log('presentation interactions passed');
'''
        result = subprocess.run(['node', '-e', js, str(script)], text=True, capture_output=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('presentation interactions passed', result.stdout)


if __name__ == '__main__':
    unittest.main()
