"""Software filters use explicit source OS labels, never compatibility inference."""
from html.parser import HTMLParser
from pathlib import Path
import importlib.util
import json
import os
import shutil
import subprocess
import tempfile
import unittest

import test_build as fixtures
import test_release_integration as profiles
from thinkpad_archive import build_site

ROOT = Path(__file__).resolve().parents[1]


class Tags(HTMLParser):
    def __init__(self, html):
        super().__init__(convert_charrefs=True)
        self.tags = []
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        self.tags.append((tag, dict(attrs)))


class PackageFilters(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=os.environ.get('TMPDIR'))
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.records = fixtures.fixture_data()
        drivers = self.records['drivers']['drivers']
        drivers[0]['operating_systems'] = ['Windows 8 32-bit', 'Microsoft Windows XP Professional x64 Edition, SP2', 'Windows 8.1 64-bit']
        drivers[0]['title'] = 'Audio <legacy> & network'
        drivers.append(dict(drivers[0], id='unknown-system', title='Unknown system package', operating_systems=[]))
        self.records['models']['models'][0]['driver_ids'].append('unknown-system')
        fixtures.write_fixture(self.root / 'data', self.records)

    def build(self, enriched=False):
        if enriched:
            (self.root / 'data/profiles.json').write_text(json.dumps(profiles.profiles_for(self.records)))
        return build_site(self.root / ('profile-site' if enriched else 'site'), data_dir=self.root / 'data')

    def test_source_os_grouping_is_exact_and_keeps_unknown_labels(self):
        self.assertIsNotNone(importlib.util.find_spec('thinkpad_archive.package_filters'), 'OS presentation grouping is missing')
        from thinkpad_archive.package_filters import operating_system_groups
        self.assertEqual(operating_system_groups(['Microsoft Windows 8.1 32-bit, 64-bit', 'Windows 8 (32-bit)', 'Windows XP x64', 'Windows Server2003', 'Linux', 'Mystery <OS>']),
                         ['Linux', 'Mystery <OS>', 'Windows 8', 'Windows 8.1', 'Windows Server 2003', 'Windows XP'])
        self.assertEqual(operating_system_groups(['Windows 8.1 64-bit']), ['Windows 8.1'])
        self.assertEqual(operating_system_groups(['OS Independent', 'All operating systems listed']), ['All operating systems listed', 'OS Independent'])
        self.assertEqual(operating_system_groups([]), [])
        self.assertEqual(operating_system_groups(['Windows 8.2', 'Windows 8.10', 'Windows Server2003R2']), ['Windows 8.10', 'Windows 8.2', 'Windows Server2003R2'])

    def test_software_controls_and_search_metadata_exist_in_both_renderers(self):
        for enriched in (False, True):
            site = self.build(enriched)
            for lang in ('en', 'es'):
                with self.subTest(enriched=enriched, lang=lang):
                    html = (site / lang / 'models/700c.html').read_text()
                    software = html.split('<section id="drivers"', 1)[1].split('</section>', 1)[0]
                    tags = Tags(software).tags
                    control = next((a for tag, a in tags if a.get('id') == 'package-filters'), None)
                    self.assertIsNotNone(control, 'Progressive package filter form is missing')
                    self.assertIn('hidden', control)
                    for identity in ('package-search', 'package-os', 'package-filter-status', 'package-empty'):
                        self.assertTrue(any(a.get('id') == identity for _, a in tags), identity)
                    rows = [a for tag, a in tags if tag == 'article' and 'data-package-id' in a]
                    self.assertEqual({a['data-package-id'] for a in rows}, {'audio', 'unknown-system'})
                    audio = next(a for a in rows if a['data-package-id'] == 'audio')
                    self.assertIn('Audio <legacy> & network', audio['data-package-search'])
                    self.assertEqual(json.loads(audio['data-package-os']), ['Windows 8', 'Windows 8.1', 'Windows XP'])
                    options = [a['value'] for tag, a in tags if tag == 'option']
                    self.assertEqual(options, ['', 'Windows 8', 'Windows 8.1', 'Windows XP', '__unrecorded__'])
                    self.assertIn('assets/packages.js', html)
                    self.assertNotIn('data-package-search', html.split('<section id="firmware"', 1)[1])
                    self.assertIn('firmware-warning', html)
                    self.assertIn('Windows 8 32-bit', software)  # Original advertised wording is retained.
                    sparse = (site / lang / 'models/700cs.html').read_text()
                    self.assertNotIn('id="package-filters"', sparse)

    @unittest.skipUnless(shutil.which('node'), 'Node is optional interaction verification')
    def test_search_os_combination_categories_reset_and_firmware_are_independent(self):
        script = ROOT / 'assets/packages.js'
        self.assertTrue(script.is_file(), 'Package filtering enhancement is missing')
        js = r'''
const assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs');
const events={}, documentEvents={};
function control(value=''){return {value,hidden:true,textContent:'',addEventListener(k,f){this[k]=f;},setAttribute(k,v){this[k]=v;}};}
function row(id,query,systems){return {hidden:false,getAttribute:k=>({'data-package-id':id,'data-package-search':query,'data-package-os':JSON.stringify(systems)})[k]};}
const audio=row('audio','Áudio legacy 1.23',['Windows XP','Windows 8.1']);
const network=row('network','Network 2.0',['Windows 8']);
const unknown=row('unknown','Unlisted system',[]),firmware=row('bios','BIOS update',['Windows XP']);
function group(rows){const count=control();count.textContent=''+rows.length;return {hidden:false,open:false,rows,count,querySelector:s=>s==='.category-count'?count:null,querySelectorAll:()=>rows};}
const groups=[group([audio]),group([network,unknown])];
const ids={'package-filters':control(),'package-search':control(),'package-os':control(),'package-empty':control(),'package-filter-status':control()};
ids['package-filter-status'].getAttribute=k=>({'data-pattern':'{shown} / {total} packages'})[k];
const section={querySelectorAll:s=>s==='.driver-category'?groups:[audio,network,unknown]};
ids.drivers=section;
const document={getElementById:id=>ids[id]||null,addEventListener:(k,f)=>documentEvents[k]=f};
vm.runInNewContext(fs.readFileSync(process.argv[1],'utf8'),{document,window:{setTimeout:f=>f()},JSON});
const visible=()=>[audio,network,unknown].filter(r=>!r.hidden).map(r=>r.getAttribute('data-package-id'));
assert.equal(ids['package-filters'].hidden,false);
assert.deepEqual(visible(),['audio','network','unknown']);
ids['package-search'].value='audio 1.23';ids['package-search'].input();
assert.deepEqual(visible(),['audio']);assert.equal(groups[0].open,true);assert.equal(groups[1].hidden,true);
ids['package-os'].value='Windows 8';ids['package-os'].change();assert.deepEqual(visible(),[]);assert.equal(ids['package-empty'].hidden,false);
assert.equal(firmware.hidden,false,'software filtering must never affect firmware');
ids['package-search'].value='';ids['package-search'].input();assert.deepEqual(visible(),['network']);
assert.equal(groups[1].count.textContent,'1 / 2');
ids['package-os'].value='Windows 8.1';ids['package-os'].change();assert.deepEqual(visible(),['audio']);
ids['package-os'].value='__unrecorded__';ids['package-os'].change();assert.deepEqual(visible(),['unknown']);
ids['package-search'].value='';ids['package-os'].value='';ids['package-filters'].reset();
assert.deepEqual(visible(),['audio','network','unknown']);assert.equal(ids['package-empty'].hidden,true);
assert.equal(groups[0].open,false,'reset restores the original native category state');
assert.equal(groups[1].count.textContent,'2');assert.equal(firmware.hidden,false);
console.log('software search, OS, reset and firmware isolation passed');
'''
        result = subprocess.run(['node', '-e', js, str(script)], capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('firmware isolation passed', result.stdout)


if __name__ == '__main__':
    unittest.main()
