"""Real UI handler with controlled clipboard/timers; browser gate is separate."""
from pathlib import Path
import shutil
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]

@unittest.skipUnless(shutil.which('node'), 'Node is optional interaction verification')
class OfflineCopy(unittest.TestCase):
    def test_copy_success_failure_fallback_and_feedback_reset(self):
        script = r'''
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const source = fs.readFileSync(process.argv[1], 'utf8');
const hash = 'ab'.repeat(32);
function setup(clipboard, legacyResult=true) {
  const handlers={}, attrs={'data-copy-label':'Copy SHA-256','data-copied-label':'Copied','data-copy-failed':'Copy failed'}, classes=new Set();
  let active;
  const button={hidden:true,disabled:false,getAttribute:k=>attrs[k],setAttribute:(k,v)=>attrs[k]=v,
    classList:{add:k=>classes.add(k),remove:k=>classes.delete(k),contains:k=>classes.has(k)},
    addEventListener:(k,f)=>handlers[k]=f,focus(){active=button;}};
  const field={value:hash,selected:0,focus(){active=field;},select(){field.selected++;}};
  const status={textContent:''}, calls=[], timers=new Map();let seq=0;
  const document={querySelectorAll:()=>[],getElementById:id=>({'offline-copy':button,'offline-hash':field,'offline-copy-status':status}[id]||null),
    execCommand(cmd){calls.push(cmd);if(legacyResult==='throw')throw Error('denied');return legacyResult;},get activeElement(){return active;}};
  const window={setTimeout(f,ms){const id=++seq;timers.set(id,{f,ms});return id;},clearTimeout(id){timers.delete(id);},isSecureContext:true};
  vm.runInNewContext(source,{document,window,navigator:clipboard===null?{}:{clipboard},Promise});
  return {button,field,status,attrs,classes,calls,timers,click:()=>handlers.click&&handlers.click(),active:()=>active};
}
const flush=()=>new Promise(r=>setImmediate(r));
(async()=>{
  let resolve, sent=[];
  const f=setup({writeText(value){sent.push(value);return new Promise(r=>resolve=r);}});
  assert.equal(f.button.hidden,false,'Copy enhancement must become available');
  f.click();assert.deepEqual(sent,[hash]);assert.equal(f.classes.has('is-copied'),false,'No check while copy is pending');
  assert.equal(f.button.disabled,true);resolve();await flush();
  assert.equal(f.button.disabled,false);assert.equal(f.classes.has('is-copied'),true);assert.equal(f.attrs['aria-label'],'Copied');
  assert.equal(f.status.textContent,'Copied');assert.deepEqual(f.calls,[],'Modern success must not invoke legacy copying');
  assert.equal(f.timers.size,1);let timer=[...f.timers.values()][0];assert.equal(timer.ms,2000);timer.f();
  assert.equal(f.classes.has('is-copied'),false);assert.equal(f.attrs['aria-label'],'Copy SHA-256');assert.equal(f.status.textContent,'');
  const repeat=setup({writeText:()=>Promise.resolve()});repeat.click();await flush();repeat.click();await flush();
  assert.equal(repeat.timers.size,1,'Repeated copies must replace the feedback timer');
  for(const result of [false,'throw']) {
    const fail=setup({writeText:()=>Promise.reject(Error('blocked'))},result);fail.click();await flush();
    assert.equal(fail.classes.has('is-copied'),false);assert.equal(fail.status.textContent,'Copy failed');assert.equal(fail.button.disabled,false);
    assert.equal(fail.field.selected,1);assert.deepEqual(fail.calls,['copy']);assert.equal(fail.timers.size,0);
  }
  const fallback=setup(null,true);fallback.click();await flush();
  assert.deepEqual(fallback.calls,['copy']);assert.equal(fallback.classes.has('is-copied'),true);assert.equal(fallback.active(),fallback.button);
  assert.equal(fallback.field.selected,1);assert.equal(fallback.button.disabled,false);
  console.log('copy feedback, denial, fallback and timer assertions passed');
})().catch(e=>{console.error(e);process.exitCode=1;});
'''
        result = subprocess.run(['node', '-e', script, str(ROOT / 'assets/ui.js')], capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('assertions passed', result.stdout)

if __name__ == '__main__':
    unittest.main()
