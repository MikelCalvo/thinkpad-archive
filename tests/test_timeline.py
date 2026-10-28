"""Year-based navigation must not infer release years or hide catalogue coverage."""
from pathlib import Path
from html.parser import HTMLParser
import copy
import json
import os
import shutil
import subprocess
import tempfile
import unittest
import test_build as fixtures

ROOT = Path(__file__).resolve().parents[1]


class Tags(HTMLParser):
    def __init__(self, text):
        super().__init__(convert_charrefs=True)
        self.tags = []
        self.feed(text)
    def handle_starttag(self, tag, attrs):
        self.tags.append((tag, dict(attrs)))


def records():
    data = fixtures.fixture_data()
    data['models']['models'][0]['introduced'] = [{'year':1992,'variants':['700C'],'url':'https://example.org/history'}]
    data['models']['models'][1]['introduced'] = [
        {'year':2012,'variants':['X230 Tablet'],'url':'https://example.org/x230'},
        {'year':2013,'variants':['Synthetic later variant'],'url':'https://example.org/x230'},
    ]
    data['models']['models'][2]['introduced'] = []
    return data


class Timeline(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=os.environ.get('TMPDIR'))
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.data = self.root / 'data'
        fixtures.write_fixture(self.data, records())
    def build(self):
        import thinkpad_archive
        return thinkpad_archive.build_site(self.root / 'site', data_dir=self.data)

    def test_year_navigation_has_static_fallback_and_complete_secondary_catalogue(self):
        site = self.build()
        for lang in ('en', 'es'):
            for path, expected in [('index.html',['700c','700cs','x230-tablet']),('years/2012.html',['x230-tablet']),('years/2013.html',['x230-tablet']),('years/2000.html',[]),('years/unknown.html',['700cs']),('catalogue.html',['700c','700cs','x230-tablet'])]:
                page = site / lang / path
                self.assertTrue(page.is_file(), path)
                text = page.read_text()
                rows = [a for t,a in Tags(text).tags if t=='tr' and 'data-model-id' in a and 'hidden' not in a]
                self.assertEqual([a['data-model-id'] for a in rows], expected, path)
            home = (site/lang/'index.html').read_text()
            self.assertIn('class="timeline-track"', home)
            rail = home.split('class="timeline-track"', 1)[1].split('</nav>', 1)[0]
            self.assertLess(rail.index('data-year="all"'), rail.index('data-year="1992"'))
            self.assertIn('data-selected-year="all"', home)
            self.assertIn('data-year="1992"', home)
            self.assertIn('type="range"', home)
            self.assertIn('years/2012.html', home)
            self.assertIn('catalogue.html', home)
            self.assertIn('<details class="reference-library"', home)
            css = (site/'assets/style.css').read_text()
            self.assertNotIn('border-top:5px solid var(--red)', css)
            empty = (site/lang/'years/2000.html').read_text()
            empty_tags = [a for t,a in Tags(empty).tags if a.get('id') == 'empty-results']
            self.assertNotIn('hidden', empty_tags[0])
            year = (site/lang/'years/2012.html').read_text()
            other = 'es' if lang=='en' else 'en'
            self.assertIn('../../'+other+'/years/2012.html', year)
            model = (site/lang/'models/x230-tablet.html').read_text()
            self.assertIn('2012', model)
            self.assertIn('2013', model)
            self.assertIn('https://example.org/x230', model)

    def test_year_rail_has_only_all_and_years_with_no_duplicate_scrollbar(self):
        site = self.build()
        for lang in ('en', 'es'):
            home = (site/lang/'index.html').read_text()
            years = [a['data-year'] for t,a in Tags(home).tags if 'data-year' in a]
            self.assertEqual(years, ['all'] + [str(y) for y in range(1992, 2014)])
            self.assertNotIn('class="timeline-secondary"', home)
            self.assertIn('id="year-slider"', home)
            all_page = (site/lang/'catalogue.html').read_text()
            visible = [a['data-model-id'] for t,a in Tags(all_page).tags if 'data-model-id' in a and 'hidden' not in a]
            self.assertIn('700cs', visible)  # Removing the link must not remove undated models.
        css = (site/'assets/style.css').read_text()
        rail_css = css.split('.timeline-track{', 1)[1].split('}', 1)[0]
        self.assertIn('overflow-x:auto', rail_css)
        self.assertIn('scrollbar-width:none', rail_css)
        self.assertIn('.timeline-track::-webkit-scrollbar{display:none}', css)

    def test_year_slider_keeps_accessible_name_without_visible_hint(self):
        site = self.build()
        for lang, hint in [('es', 'Desliza hasta un año'), ('en', 'Slide to a year')]:
            home = (site/lang/'index.html').read_text()
            tags = Tags(home).tags
            slider = next(a for t,a in tags if a.get('id') == 'year-slider')
            self.assertEqual(slider.get('aria-label'), hint)
            self.assertNotIn('>' + hint + '<', home)
            self.assertFalse(any(t == 'label' and a.get('for') == 'year-slider' for t,a in tags))

    def test_timeline_omits_redundant_range_and_variant_explanation(self):
        site = self.build()
        notes = (
            'Los años documentados corresponden a las variantes citadas, no a toda una entrada agrupada.',
            'Source-documented years apply to the cited variants, not every member of a grouped entry.',
        )
        for lang in ('en', 'es'):
            for relative in ('index.html', 'catalogue.html', 'years/1992.html', 'years/2012.html'):
                text = (site/lang/relative).read_text()
                self.assertNotIn('class="timeline-range"', text)
                self.assertNotIn('1992—2013', text)
                for note in notes:
                    self.assertNotIn(note, text)
                self.assertIn('class="timeline-track"', text)
                self.assertIn('id="selected-year"', text)
                self.assertIn('id="year-slider"', text)
            model = (site/lang/'models/x230-tablet.html').read_text()
            self.assertIn('https://example.org/x230', model)
            self.assertIn('2012', model)
            self.assertIn('2013', model)

    def test_selected_year_is_not_visually_repeated_below_the_rail(self):
        site = self.build()
        for lang in ('en', 'es'):
            for relative in ('index.html', 'years/2012.html'):
                text = (site/lang/relative).read_text()
                attrs = next(a for t,a in Tags(text).tags if a.get('id') == 'selected-year')
                self.assertEqual(attrs.get('class'), 'visually-hidden')
                self.assertNotIn('class="timeline-caption"', text)
                self.assertIn('aria-labelledby="selected-year"', text)
        css = (site/'assets/style.css').read_text()
        self.assertIn('.visually-hidden{', css)
        self.assertIn('clip-path:inset(50%)', css)

    def test_introduction_schema_rejects_bad_dates_urls_and_duplicates_before_output(self):
        invalid = [None, [1992], [{'year':True,'variants':['700C'],'url':'https://example.org'}],
                   [{'year':1991,'variants':['700C'],'url':'https://example.org'}],
                   [{'year':1992,'variants':[],'url':'https://example.org'}],
                   [{'year':1992,'variants':['700C'],'url':'javascript:alert(1)'}],
                   [{'year':1992,'variants':['700C'],'url':'https://example.org','extra':'x'}],
                   [{'year':1992,'variants':['700C'],'url':'https://example.org'}]*2]
        import thinkpad_archive
        for index, value in enumerate(invalid):
            with self.subTest(index=index):
                data = records();data['models']['models'][0]['introduced']=value
                source=self.root/('bad-'+str(index));fixtures.write_fixture(source,data)
                output=self.root/('site-'+str(index))
                with self.assertRaises(ValueError):
                    thinkpad_archive.build_site(output,data_dir=source)
                self.assertFalse(output.exists())

    def test_partially_dated_groups_preserve_unknown_variants(self):
        data = records()
        data['models']['models'][1]['introduced_unknown'] = ['Undated grouped variant']
        fixtures.write_fixture(self.data, data)
        site = self.build()
        for lang in ('en', 'es'):
            unknown = (site/lang/'years/unknown.html').read_text()
            rows = [a['data-model-id'] for t,a in Tags(unknown).tags if t == 'tr' and 'data-model-id' in a and 'hidden' not in a]
            self.assertEqual(set(rows), {'700cs', 'x230-tablet'})
            model = (site/lang/'models/x230-tablet.html').read_text()
            self.assertIn('Undated grouped variant', model)
            self.assertIn('data-unknown-year="true"', unknown)

    def test_unknown_variant_schema_rejects_empty_text_and_duplicate_names(self):
        import thinkpad_archive
        for index, value in enumerate([None, '', [''], ['same', 'same']]):
            data = records(); data['models']['models'][1]['introduced_unknown'] = value
            source = self.root/('unknown-bad-' + str(index)); fixtures.write_fixture(source, data)
            with self.assertRaises(ValueError):
                thinkpad_archive.build_site(self.root/('unknown-site-' + str(index)), data_dir=source)

    def test_machine_type_groups_do_not_inherit_generic_launch_years(self):
        models = {m['id']: m for m in json.loads((ROOT/'data/models.json').read_text())['models']}
        expected = {'r52-1846': {'1846', '1847', '1848', '1849'},
                    'r52-1858': {'1858', '1859', '1860', '1861', '1958'}}
        for identity, types in expected.items():
            references = models[identity]['introduced']
            self.assertEqual({v for r in references for v in r['variants']},
                             {'ThinkPad R52 (Type ' + t + ')' for t in types})
            self.assertTrue(all(r['year'] == 2005 and '#page=' in r['url'] and 'ltwbook_2013.pdf' in r['url'] for r in references))
            self.assertTrue(models[identity]['introduced_unknown'])

    def test_plain_legacy_models_remain_accessible_as_unknown(self):
        fixtures.write_fixture(self.data)
        site=self.build()
        home=(site/'index.html').read_text()
        self.assertIn('data-selected-year="all"',home)
        rows=[a for t,a in Tags(home).tags if t=='tr' and 'data-search' in a]
        self.assertEqual(len(rows),3)
        self.assertTrue(all('hidden' not in r for r in rows))

    @unittest.skipUnless(shutil.which('node'),'Node is optional interaction verification')
    def test_year_selection_range_global_search_reset_and_unknown(self):
        script=ROOT/'assets/search.js'
        js=r'''
const assert=require('node:assert/strict');
let events={},prevented=0;
function control(value=''){return {value,hidden:true,textContent:'',setAttribute(k,v){this[k]=v;},addEventListener(k,f){this[k]=f;}};}
let form=control(),query=control(),family=control(),drivers=control(),manuals=control(),count=control(),empty=control();
let slider=control('1992'),label=control();
let attrs={'data-selected-year':'all','data-default-year':'all','data-all-value':'1991','data-all-label':'All years','data-unknown-label':'Unknown','data-year-label':'Introduced in'};
let timeline={getAttribute:k=>attrs[k],setAttribute:(k,v)=>attrs[k]=v};
let rows=[['early','1992'],['later','2012 2013'],['unknown','']].map(([id,years])=>({hidden:false,getAttribute:k=>({'data-model-id':id,'data-years':years,'data-search':id,'data-family':'x','data-drivers':'with','data-manuals':'with'})[k]}));
function anchor(year){return {attrs:{'data-year':year},getAttribute(k){return this.attrs[k];},setAttribute(k,v){this.attrs[k]=v;},removeAttribute(k){delete this.attrs[k];},addEventListener(k,f){this[k]=f;},scrollIntoView(){}};}
let anchors=['1992','2000','2012','2013','unknown','all'].map(anchor);
let body={getElementsByTagName:()=>rows};let controls={'filters':form,'model-search':query,'family-filter':family,'driver-filter':drivers,'manual-filter':manuals,'result-count':count,'empty-results':empty,'model-rows':body,'timeline':timeline,'year-slider':slider,'selected-year':label};
global.document={getElementById:id=>controls[id]||null,querySelectorAll:s=>s==='[data-year]'?anchors:[]};
global.window={setTimeout:f=>f(),location:{hash:''},addEventListener(k,f){events[k]=f;}};
require(process.argv[1]);
const visible=()=>rows.filter(r=>!r.hidden).map(r=>r.getAttribute('data-model-id'));
assert.equal(visible().length,3);assert.equal(slider.hidden,false);assert.equal(form.hidden,false);
query.value='later';query.input();assert.deepEqual(visible(),['later']);
family.value='does-not-match';family.change();assert.equal(visible().length,0);
slider.value='2012';slider.input();assert.deepEqual(visible(),['later']);assert.equal(form.hidden,true);assert.equal(family.value,'');
anchors.find(a=>a.attrs['data-year']==='2013').click({preventDefault(){prevented++;}});assert.deepEqual(visible(),['later']);assert.equal(form.hidden,true);
anchors.find(a=>a.attrs['data-year']==='all').click({preventDefault(){}});assert.equal(form.hidden,false);
query.value='early';query.input();assert.deepEqual(visible(),['early']);
query.value='';query.input();assert.equal(visible().length,3);
anchors.find(a=>a.attrs['data-year']==='unknown').click({preventDefault(){}});assert.deepEqual(visible(),['unknown']);assert.equal(form.hidden,true);
anchors.find(a=>a.attrs['data-year']==='all').click({preventDefault(){}});assert.equal(visible().length,3);assert.equal(form.hidden,false);
slider.value='2000';slider.input();assert.deepEqual(visible(),[]);assert.equal(empty.hidden,false);assert.equal(form.hidden,true);
form.reset();assert.equal(visible().length,3);assert.equal(count.textContent,'3');assert.equal(form.hidden,false);
console.log('timeline interaction passed');
'''
        result=subprocess.run(['node','-e',js,str(script)],capture_output=True,text=True,timeout=10)
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertIn('timeline interaction passed',result.stdout)


if __name__=='__main__':
    unittest.main()
