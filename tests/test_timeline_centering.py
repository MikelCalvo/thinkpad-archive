"""Only the horizontal timeline moves when a year is activated."""
from pathlib import Path
import shutil
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(shutil.which('node'), 'Node is optional interaction verification')
class TimelineCentering(unittest.TestCase):
    def test_click_centers_year_in_rail_and_preserves_navigation_contract(self):
        script = r'''
const assert = require('node:assert/strict');
function run(reduced, nativeScroll = true) {
  const calls = [], forbidden = [];
  function control(value = '') {
    return {value, hidden:true, textContent:'', setAttribute(k,v){this[k]=v;},
            addEventListener(k,f){this[k]=f;}};
  }
  const controls = {};
  for (const id of ['filters','model-search','family-filter','driver-filter','manual-filter',
                    'result-count','empty-results','year-slider','selected-year']) controls[id]=control();
  const attrs = {'data-selected-year':'all','data-default-year':'all','data-all-value':'1991',
                 'data-all-label':'ALL','data-unknown-label':'Unknown','data-year-label':'Introduced in'};
  controls.timeline = {getAttribute:k=>attrs[k], setAttribute:(k,v)=>attrs[k]=v};
  const rail = {scrollLeft:500, clientWidth:400, clientLeft:2, scrollWidth:1800,
                getBoundingClientRect(){return {left:100,width:404};}};
  if (nativeScroll) rail.scrollTo = options => {calls.push(options);rail.scrollLeft=options.left;};
  const positions = {all:0, '1992':80, '2002':800, '2003':880, '2026':1720};
  const links = Object.keys(positions).map(year => ({
    year, parentNode:rail, getAttribute:k=>k==='data-year'?year:null,
    setAttribute(k,v){this[k]=v;}, addEventListener(k,f){this[k]=f;},
    getBoundingClientRect(){return {left:102+positions[year]-rail.scrollLeft,width:80};},
    scrollIntoView(){forbidden.push('page-scrolling API');}
  }));
  const rows = [['old','1992'],['target','2002'],['next','2003'],['last','2026']].map(([id,years]) => ({
    hidden:false, getAttribute:k=>({'data-model-id':id,'data-years':years,'data-search':id,
      'data-family':'x','data-drivers':'with','data-manuals':'with'})[k]
  }));
  controls['model-rows'] = {getElementsByTagName:()=>rows};
  global.document = {getElementById:id=>controls[id], querySelectorAll:s=>s==='[data-year]'?links:[]};
  global.window = {setTimeout:f=>f(),matchMedia:()=>({matches:reduced}),scrollTo(){forbidden.push('window scroll');}};
  delete require.cache[require.resolve(process.argv[1])];
  require(process.argv[1]);
  const activate = (year, extra={}) => {
    let prevented=false;
    links.find(a=>a.year===year).click({...extra,preventDefault(){prevented=true;}});
    return prevented;
  };
  assert.equal(activate('2002'),true);
  assert.equal(rail.scrollLeft,640,'clicked year must be centered inside its own rail');
  if (nativeScroll) assert.deepEqual(calls.at(-1),{left:640,behavior:reduced?'auto':'smooth'});
  assert.equal(controls.timeline.getAttribute('data-selected-year'),'2002');
  assert.deepEqual(rows.filter(r=>!r.hidden).map(r=>r.getAttribute('data-model-id')),['target']);
  assert.equal(controls.filters.hidden,true);
  activate('2003');
  assert.equal(rail.scrollLeft,720,'successive clicks reveal the next years');
  activate('2026');
  assert.equal(rail.scrollLeft,1400,'last year clamps to rail end');
  activate('all');
  assert.equal(rail.scrollLeft,0,'ALL returns to the start');
  assert.equal(controls.filters.hidden,false);
  for (const modifiers of [{ctrlKey:true},{metaKey:true},{shiftKey:true},{altKey:true},{button:1}]) {
    const before=calls.length;
    assert.equal(activate('2002',modifiers),false);
    assert.equal(calls.length,before,'modified clicks keep native link behavior');
    assert.equal(rail.scrollLeft,0);
  }
  controls['year-slider'].value='2002';
  controls['year-slider'].input();
  assert.equal(rail.scrollLeft,640);
  if (nativeScroll) assert.equal(calls.at(-1).behavior,'auto','slider scrubbing must not queue smooth animations');
  assert.deepEqual(forbidden,[],'centering must not scroll page ancestors');
}
run(false);
run(true);
run(false,false);
console.log('timeline click centering passed');
'''
        result = subprocess.run(['node', '-e', script, str(ROOT / 'assets/search.js')],
                                text=True, capture_output=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('timeline click centering passed', result.stdout)


if __name__ == '__main__':
    unittest.main()
