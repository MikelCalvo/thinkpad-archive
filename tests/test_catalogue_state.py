"""Execute the shipped catalogue script with DOM/History boundary doubles in Node.

No browser/layout claims: centering is checked through rail-only calls; history,
URL parsing, event ordering and timers use deterministic browser-shaped doubles.
"""
from pathlib import Path
import shutil
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
HARNESS = r'''
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const source = fs.readFileSync(process.argv[1], 'utf8');
function boot(options = {}) {
  const handlers = {}, timers = new Map(), writes = [], centers = [], forbidden = [];
  let timerId = 0, index = 0;
  const stack = [options.url || 'https://archive.test/en/index.html'];
  const location = {};
  function locate(url) {
    const u = new URL(url, stack[index]);
    for (const k of ['href','pathname','search','hash']) location[k] = u[k];
  }
  locate(stack[0]);
  function control(value = '', values) {
    return {value, hidden:false, textContent:'', attrs:{}, events:{},
      options: values && values.map(value=>({value})),
      getAttribute(k){return this.attrs[k] || null;},
      setAttribute(k,v){this.attrs[k]=String(v);},
      addEventListener(k,f){(this.events[k] ||= []).push(f);},
      fire(k,e={}){for (const f of this.events[k] || []) f(e);}};
  }
  const controls = {};
  controls.filters = control();
  controls['model-search'] = control();
  controls['family-filter'] = control('', ['', 'x', '700']);
  for (const id of ['driver-filter','manual-filter']) controls[id] = control('', ['', 'with','without']);
  for (const id of ['empty-results','selected-year','year-slider']) controls[id] = control();
  const attrs = {'data-selected-year':options.selected || 'all','data-default-year':options.defaultYear || 'all',
    'data-all-value':'1991','data-all-label':'ALL','data-unknown-label':'Unknown','data-year-label':'Introduced in'};
  controls.timeline = {getAttribute:k=>attrs[k],setAttribute:(k,v)=>attrs[k]=v};
  const records = options.rows || [
    ['early','ThinkPad 700C Café + &','700','with','with','1992',false],
    ['later','ThinkPad X230 Tablet X230t','x','with','without','2012 2013',true],
    ['unknown','ThinkPad 700CS','700','without','without','',false]
  ];
  const rows = records.map(([id,text,family,drivers,manuals,years,unknown])=>({hidden:false,
    getAttribute:k=>({'data-model-id':id,'data-search':text,'data-family':family,'data-drivers':drivers,
      'data-manuals':manuals,'data-years':years,'data-unknown-year':String(unknown)})[k]}));
  controls['model-rows'] = {getElementsByTagName:()=>rows};
  const rail = {scrollLeft:0,clientLeft:0,clientWidth:100,scrollWidth:1000,
    getBoundingClientRect:()=>({left:0}),scrollTo(o){this.scrollLeft=o.left;centers.push(o);}};
  const links = ['all','1992','2000','2012','2013'].map((year,i)=>{
    const link=control();link.attrs['data-year']=year;link.parentNode=rail;
    link.getBoundingClientRect=()=>({left:i*100-rail.scrollLeft,width:50});
    link.scrollIntoView=()=>forbidden.push('ancestor');return link;
  });
  const document = {getElementById:id=>controls[id],querySelectorAll:s=>s==='[data-year]'?links:[],
    addEventListener(k,f){(handlers['document:'+k] ||= []).push(f);}};
  const window = {location,URLSearchParams,matchMedia:()=>({matches:false}),
    setTimeout(f,ms){timers.set(++timerId,{f,ms});return timerId;},clearTimeout(id){timers.delete(id);},
    addEventListener(k,f){(handlers[k] ||= []).push(f);},scrollTo(){forbidden.push('window');}};
  const history = {};
  for (const method of ['replaceState','pushState']) history[method]=function(state,title,url){
    if(options.rejectHistory) throw new Error('History denied');
    writes.push({method,url});
    if(method==='pushState'){stack.splice(index+1);stack.push(new URL(url,location.href).href);index++;}
    else stack[index]=new URL(url,location.href).href;
    locate(stack[index]);
  };
  window.history = history;
  if(options.noHistory) delete window.history;
  if(options.noURL) delete window.URLSearchParams;
  if(options.noLocation) delete window.location;
  const context = {document,window};
  vm.runInNewContext(source,context,{filename:'assets/search.js'});
  function emit(k,event={}){for(const f of handlers[k] || []) f(event);}
  return {controls,links,attrs,rows,writes,centers,forbidden,timers,stack,location,
    visible:()=>rows.filter(r=>!r.hidden).map(r=>r.getAttribute('data-model-id')),
    params:()=>new URLSearchParams(location.search),
    input(value){controls['model-search'].value=value;controls['model-search'].fire('input');},
    filter(id,value){controls[id+'-filter'].value=value;controls[id+'-filter'].fire('change');},
    year(year,event={}){let prevented=false;links.find(l=>l.attrs['data-year']===year).fire('click',
      {...event,preventDefault(){prevented=true;}});return prevented;},
    slide(year){controls['year-slider'].value=year;controls['year-slider'].fire('input');},
    flush(){const pending=[...timers.values()];timers.clear();for(const t of pending)t.f();},
    reset(){controls.filters.fire('reset');for(const id of ['model-search','family-filter','driver-filter','manual-filter']) controls[id].value='';this.flush();},
    navigate(url){emit('document:click',{target:{closest:()=>({href:url})},button:0});emit('pagehide');},
    pop(url){stack[index]=new URL(url,location.href).href;locate(stack[index]);emit('popstate');},
    back(){if(index>0){index--;locate(stack[index]);emit('popstate');}},
    forward(){if(index<stack.length-1){index++;locate(stack[index]);emit('popstate');}}
  };
}
'''


@unittest.skipUnless(shutil.which('node'), 'Node required for catalogue interaction checks')
class CatalogueState(unittest.TestCase):
    def run_js(self, scenario):
        result = subprocess.run(['node', '-e', HARNESS + '\n' + scenario,
                                 str(ROOT / 'assets/search.js')], capture_output=True,
                                text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_initial_valid_filters_and_reload(self):
        self.run_js(r'''
const a=boot({url:'https://archive.test/en/index.html?q=X230t&family=x&drivers=with&manuals=without'});
assert.equal(a.controls['model-search'].value,'X230t');
assert.deepEqual(a.visible(),['later']);assert.equal(a.controls.filters.hidden,false);
for(const [id,value] of [['family','x'],['driver','with'],['manual','without']]) assert.equal(a.controls[id+'-filter'].value,value);
const b=boot({url:a.location.href});assert.deepEqual(b.visible(),a.visible());
''')

    def test_invalid_options_are_ignored_not_inferred_from_rows(self):
        self.run_js(r'''
const a=boot({url:'https://archive.test/en/index.html?family=__proto__&drivers=yes&manuals=WITH&year=9999'});
assert.deepEqual(a.visible(),['early','later','unknown']);
for(const key of ['family','drivers','manuals','year']) assert.equal(a.params().has(key),false);
const b=boot({url:'https://archive.test/en/index.html?family=X'});assert.equal(b.controls['family-filter'].value,'');
const c=boot({url:'https://archive.test/en/index.html?family=forged',rows:[['f','forged','forged','with','with','1992',false]]});
assert.equal(c.controls['family-filter'].value,'');assert.deepEqual(c.visible(),['f']);
''')

    def test_raw_unicode_query_roundtrip_and_normalized_matching(self):
        self.run_js(r'''
const raw='  CAFÉ + &  ';
const a=boot({url:'https://archive.test/en/index.html?q='+encodeURIComponent(raw)});
assert.equal(a.controls['model-search'].value,raw);assert.deepEqual(a.visible(),['early']);
a.input(' X230t ');a.flush();assert.equal(a.params().get('q'),' X230t ');
assert.equal(boot({url:a.location.href}).controls['model-search'].value,' X230t ');
''')

    def test_owned_canonicalization_preserves_unrelated_bytes_and_hash(self):
        self.run_js(r'''
const a=boot({url:'https://archive.test/en/index.html?utm=a%20b&tag=1&tag=2&q=&family=bad&drivers=&year=all#models'});
assert.equal(a.location.search,'?utm=a%20b&tag=1&tag=2');assert.equal(a.location.hash,'#models');
a.input('Café & +');a.flush();assert.equal(a.params().get('q'),'Café & +');
assert.ok(a.location.search.startsWith('?utm=a%20b&tag=1&tag=2&'));
a.reset();assert.equal(a.location.search,'?utm=a%20b&tag=1&tag=2');assert.equal(a.location.hash,'#models');
''')

    def test_static_year_fallback_invalid_year_and_explicit_all_override(self):
        self.run_js(r'''
for(const suffix of ['', '?year=garbage', '?year=02012']) {
 const a=boot({selected:'2012',url:'https://archive.test/en/years/2012.html'+suffix});
 assert.equal(a.attrs['data-selected-year'],'2012');assert.deepEqual(a.visible(),['later']);assert.equal(a.controls.filters.hidden,true);
}
const a=boot({selected:'2012',url:'https://archive.test/en/years/2012.html?year=all&q=700'});
assert.equal(a.attrs['data-selected-year'],'all');assert.deepEqual(a.visible(),['early','unknown']);assert.equal(a.params().get('year'),'all');
a.reset();assert.equal(a.attrs['data-selected-year'],'all');assert.equal(a.params().get('year'),'all');assert.equal(a.params().has('q'),false);
''')

    def test_year_override_discards_all_filters_and_unknown_without_rail_link(self):
        self.run_js(r'''
const a=boot({url:'https://archive.test/en/index.html?year=2013&q=700&family=700&drivers=without&manuals=with'});
assert.deepEqual(a.visible(),['later']);assert.equal(a.controls.filters.hidden,true);
for(const key of ['q','family','drivers','manuals']) assert.equal(a.params().has(key),false);
const b=boot({url:'https://archive.test/en/index.html?year=unknown'});
assert.deepEqual(b.visible(),['later','unknown']);assert.equal(b.attrs['data-selected-year'],'unknown');
const c=boot({selected:'unknown',url:'https://archive.test/en/years/unknown.html'});
assert.deepEqual(c.visible(),['later','unknown']);
''')

    def test_typing_debounces_replace_and_flushes_before_model_navigation(self):
        self.run_js(r'''
const a=boot();a.input('X');a.input('X230t');
assert.deepEqual(a.visible(),['later']);assert.equal(a.writes.length,0);assert.equal(a.timers.size,1);
assert.ok([...a.timers.values()][0].ms>=150);a.flush();
assert.equal(a.writes.length,1);assert.equal(a.writes[0].method,'replaceState');
a.input('700');a.navigate('models/700c.html');assert.equal(a.params().get('q'),'700');
assert.equal(a.writes.at(-1).method,'replaceState');assert.equal(a.stack.length,1);
''')

    def test_discrete_choices_push_once_and_duplicates_do_not_write(self):
        self.run_js(r'''
const a=boot();a.filter('family','x');assert.equal(a.writes.length,1);assert.equal(a.writes[0].method,'pushState');
a.filter('family','x');assert.equal(a.writes.length,1);
a.year('2012');assert.equal(a.writes.length,2);assert.equal(a.writes[1].method,'pushState');
a.year('2012');assert.equal(a.writes.length,2);assert.equal(a.params().has('family'),false);
a.year('all');assert.equal(a.writes.length,3);assert.equal(a.location.search,'');
''')

    def test_slider_replaces_and_modified_clicks_remain_native(self):
        self.run_js(r'''
const a=boot();a.slide('2012');a.slide('2013');assert.equal(a.stack.length,1);
assert.deepEqual(a.writes.map(w=>w.method),['replaceState','replaceState']);
for(const extra of [{ctrlKey:true},{metaKey:true},{shiftKey:true},{altKey:true},{button:1}]) assert.equal(a.year('1992',extra),false);
assert.equal(a.params().get('year'),'2013');assert.deepEqual(a.forbidden,[]);
''')

    def test_back_forward_popstate_restores_without_writing_or_stale_timer(self):
        self.run_js(r'''
const a=boot();a.input('X230t');a.flush();a.filter('family','x');a.year('1992');
const count=a.writes.length;a.back();assert.equal(a.attrs['data-selected-year'],'all');
assert.equal(a.controls['model-search'].value,'X230t');assert.equal(a.controls['family-filter'].value,'x');assert.deepEqual(a.visible(),['later']);
a.forward();assert.deepEqual(a.visible(),['early']);assert.equal(a.controls.filters.hidden,true);
assert.equal(a.writes.length,count);assert.ok(a.centers.length>0);assert.deepEqual(a.forbidden,[]);
a.year('all');a.input('stale');const before=a.writes.length;a.pop('?q=700#models');a.flush();
assert.deepEqual(a.visible(),['early','unknown']);assert.equal(a.controls['model-search'].value,'700');assert.equal(a.writes.length,before);
''')

    def test_pending_query_is_recorded_before_discrete_push(self):
        self.run_js(r'''
const a=boot();a.input('X230t');a.filter('family','x');
assert.deepEqual(a.writes.map(w=>w.method),['replaceState','pushState']);
a.back();assert.equal(a.controls['model-search'].value,'X230t');assert.equal(a.controls['family-filter'].value,'');
''')

    def test_reset_uses_current_default_year_and_removes_owned_values(self):
        self.run_js(r'''
const a=boot({url:'https://archive.test/en/index.html?tag=a#models'});
a.filter('family','x');a.attrs['data-default-year']='1992';a.reset();
assert.equal(a.attrs['data-selected-year'],'1992');assert.equal(a.params().get('year'),'1992');
assert.equal(a.params().has('family'),false);assert.equal(a.params().get('tag'),'a');assert.equal(a.location.hash,'#models');
assert.deepEqual(a.visible(),['early']);assert.equal(a.writes.at(-1).method,'pushState');
''')

    def test_malformed_unrelated_query_key_does_not_disable_updates(self):
        self.run_js(r'''
const a=boot({url:'https://archive.test/en/index.html?bad%zz=value&%71=X230t#models'});
assert.deepEqual(a.visible(),['later']);a.input('700');a.flush();
assert.equal(a.params().get('q'),'700');assert.ok(a.location.search.startsWith('?bad%zz=value&'));
assert.equal(a.location.hash,'#models');
''')

    def test_encoded_duplicate_owned_keys_are_canonicalized(self):
        self.run_js(r'''
const a=boot({url:'https://archive.test/en/index.html?%71=X230t&q=700&family=x&family=700'});
assert.deepEqual(a.visible(),['later']);assert.deepEqual(a.params().getAll('q'),['X230t']);
assert.deepEqual(a.params().getAll('family'),['x']);
a.input('   ');a.flush();assert.equal(a.params().has('q'),false);
''')

    def test_optional_or_rejected_browser_apis_do_not_break_filtering(self):
        self.run_js(r'''
for(const options of [{noHistory:true},{rejectHistory:true},{noURL:true},{noLocation:true}]) {
 const a=boot(options);a.input('X230t');a.flush();assert.deepEqual(a.visible(),['later']);
 a.year('1992');assert.deepEqual(a.visible(),['early']);a.reset();assert.equal(a.visible().length,3);
}
''')


if __name__ == '__main__':
    unittest.main()
