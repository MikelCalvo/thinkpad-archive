"""Public statistics: semantic HTML and offline, privacy-bounded JS contracts."""
from html.parser import HTMLParser
from pathlib import Path
import importlib
import importlib.util
import json
import shutil
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]


class Tags(HTMLParser):
    def __init__(self, html):
        super().__init__(convert_charrefs=True)
        self.tags = []
        self.text = []
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        self.tags.append((tag, dict(attrs)))

    def handle_data(self, data):
        self.text.append(data)


def stats_module():
    if importlib.util.find_spec('thinkpad_archive.stats_page') is None:
        raise AssertionError('Public statistics body API is missing')
    return importlib.import_module('thinkpad_archive.stats_page')


class StatsMarkup(unittest.TestCase):
    def test_bilingual_native_controls_complete_tables_without_download(self):
        module = stats_module()
        for lang, title in [('en', 'Stats'), ('es', 'Estadísticas')]:
            with self.subTest(lang=lang):
                html = module.stats_body(lang)
                tags = Tags(html).tags
                ids = {a['id']: (tag, a) for tag, a in tags if 'id' in a}
                heading = html.split('<h1>', 1)[1].split('</h1>', 1)[0]
                self.assertEqual(''.join(Tags(heading).text), title)
                self.assertEqual(ids['stats-days'][0], 'select')
                self.assertEqual([a['value'] for tag, a in tags if tag == 'option'], ['7', '30', '90', '365', 'all'])
                self.assertTrue(any(tag == 'label' and a.get('for') == 'stats-days' for tag, a in tags))
                self.assertEqual(ids['stats-refresh'][1]['type'], 'button')
                self.assertEqual(ids['stats-status'][1]['role'], 'status')
                self.assertEqual(ids['stats-status'][1]['aria-live'], 'polite')
                self.assertIn('hidden', ids['stats-results'][1])
                self.assertIn('hidden', ids['stats-controls'][1])
                for name in ('daily', 'pages', 'sources', 'devices', 'browsers', 'systems', 'languages'):
                    self.assertEqual(ids['stats-' + name][0], 'tbody')
                self.assertTrue(all(a.get('scope') in ('col', 'row') for tag, a in tags if tag == 'th'))
                self.assertTrue(any(tag == 'noscript' for tag, _ in tags))
                self.assertNotIn('stats-export', ids)
                self.assertFalse(any('download' in a for _, a in tags))
                self.assertNotIn('/api/stats/export.json', html)
                copy = json.loads(ids['stats-dashboard'][1]['data-stats-copy'])
                self.assertEqual(copy, module.STATS_COPY[lang])
                for key in ('loading', 'ready', 'unavailable', 'file', 'disabled'):
                    self.assertTrue(copy[key])
                self.assertNotIn('<script', html)
                self.assertNotIn(' style=', html)
                self.assertIn('<details', html)

    def test_refresh_is_an_icon_with_localized_accessible_name(self):
        module = stats_module()
        for lang, label in [('en', 'Refresh'), ('es', 'Actualizar')]:
            with self.subTest(lang=lang):
                html = module.stats_body(lang)
                button = html.split('<button id="stats-refresh"', 1)[1].split('</button>', 1)[0]
                tags = Tags('<button' + button + '</button>')
                attrs = next(attrs for tag, attrs in tags.tags if tag == 'button')
                self.assertEqual(attrs.get('aria-label'), label)
                self.assertEqual(attrs.get('title'), label)
                self.assertEqual(''.join(tags.text).strip(), '')
                svg = next((attrs for tag, attrs in tags.tags if tag == 'svg'), None)
                self.assertIsNotNone(svg)
                assert svg is not None
                self.assertEqual(svg.get('aria-hidden'), 'true')
                self.assertEqual(svg.get('focusable'), 'false')

    def test_heading_has_no_subtitle_and_retains_plain_text(self):
        module = stats_module()
        for lang in ('en', 'es'):
            with self.subTest(lang=lang):
                html = module.stats_body(lang)
                header = html.split('<header class="stats-heading">', 1)[1].split('</header>', 1)[0]
                self.assertFalse(any(tag == 'p' for tag, _ in Tags(header).tags))
                self.assertNotIn('intro', module.STATS_COPY[lang])
                self.assertNotIn('zero', module.STATS_COPY[lang])

    def test_spanish_heading_reuses_native_i_red_dot_without_replacing_accent(self):
        html = stats_module().stats_body('es')
        heading = html.split('<h1>', 1)[1].split('</h1>', 1)[0]
        self.assertIn('Estadíst<span class="title-i">i</span>cas', heading)
        self.assertEqual(''.join(Tags(heading).text), 'Estadísticas')
        self.assertNotIn('ı', heading)
        self.assertNotIn('class="title-i"', stats_module().stats_body('en'))

    def test_transparent_methodology_and_future_locale_fallback(self):
        module = stats_module()
        self.assertEqual(module.stats_body('future'), module.stats_body('en'))
        self.assertEqual(set(module.STATS_COPY['en']), set(module.STATS_COPY['es']))
        en = ' '.join(Tags(module.stats_body('en')).text)
        es = ' '.join(Tags(module.stats_body('es')).text)
        for value in ('indefinitely', 'All time', 'UTC', 'DNT', 'GPC', 'counts(day, dimension, value, count)', 'bots', 'unique visitors', 'Infrastructure', 'country', 'marginal'):
            self.assertIn(value, en)
        for value in ('indefinida', 'Todo el tiempo', 'UTC', 'DNT', 'GPC', 'bots', 'visitantes únicos', 'infraestructura', 'país', 'marginales'):
            self.assertIn(value, es)
        for lang in ('en', 'es'):
            html = module.stats_body(lang)
            self.assertNotIn('Google Analytics', html)
            self.assertNotIn('https://', html)
            self.assertNotIn('onclick=', html)

    def test_dashboard_styles_reuse_theme_tokens_and_scope_responsive_rules(self):
        path = ROOT / 'assets/stats.css'
        self.assertTrue(path.is_file(), 'Scoped dashboard stylesheet is missing')
        css = path.read_text()
        for value in ('var(--paper)', 'var(--card)', 'var(--ink)', 'var(--muted)', 'var(--red)', 'var(--line)', '@media', '.stats-dashboard', 'minmax(0,1fr)', 'overflow-wrap:anywhere', ':focus-visible', '[hidden]'):
            self.assertIn(value, css)
        self.assertNotIn('@import', css)
        self.assertNotIn('url(', css)


COLLECTOR_HARNESS = r'''
const assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs');
const script=fs.existsSync(process.argv[1])?fs.readFileSync(process.argv[1],'utf8'):'';
function collect(config={}) {
  const calls=[];
  const location={protocol:'https:',origin:'https://archive.example',pathname:'/es/models/x230.html'};
  Object.assign(location,config.location||{});
  for(const key of ['search','hash','href']) Object.defineProperty(location,key,{get(){throw Error('forbidden location read')}});
  const navigator={userAgent:'Mozilla/5.0 (X11; Linux x86_64; rv:128.0) Gecko/20100101 Firefox/128.0',doNotTrack:'0',globalPrivacyControl:false};
  Object.assign(navigator,config.navigator||{});
  for(const key of ['cookie','language','languages','platform','hardwareConcurrency','deviceMemory','userAgentData']) Object.defineProperty(navigator,key,{get(){throw Error('forbidden navigator read')}});
  const document={referrer:config.referrer||'',documentElement:{getAttribute:k=>k==='data-stats-enabled'?(config.enabled===undefined?'true':config.enabled):null},addEventListener(){throw Error('no event tracking')}};
  Object.defineProperty(document,'cookie',{get(){throw Error('cookie read')},set(){throw Error('cookie write')}});
  const context={document,location,navigator,URL,fetch:(url,options)=>{calls.push({url,options});return config.reject?Promise.reject(Error('unavailable')):Promise.resolve({ok:true});}};
  context.window={location,navigator,doNotTrack:config.windowDnt,addEventListener(){throw Error('no lifecycle tracking')}};
  for(const key of ['localStorage','sessionStorage','indexedDB','crypto','screen','history']) Object.defineProperty(context,key,{get(){throw Error('forbidden API')}});
  vm.runInNewContext(script,context);
  return calls;
}
function positive(){assert.equal(collect().length,1,'ordinary document load must submit one view')}
'''


@unittest.skipUnless(shutil.which('node'), 'Node is required for JS behavioral verification')
class StatsCollector(unittest.TestCase):
    def run_node(self, code):
        result = subprocess.run(['node', '--unhandled-rejections=strict', '-e', COLLECTOR_HARNESS + code, str(ROOT / 'assets/analytics.js')], capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_one_document_view_uses_only_five_fields_and_private_transport(self):
        self.run_node(r'''
positive();
const call=collect()[0],body=JSON.parse(call.options.body);
assert.equal(call.url,'/api/stats/pageview');
assert.deepEqual(body,{path:'/es/models/x230.html',source:'direct',device:'desktop',browser:'firefox',system:'linux'});
assert.equal(call.options.method,'POST');assert.equal(call.options.mode,'same-origin');
assert.equal(call.options.credentials,'omit');assert.equal(call.options.referrerPolicy,'no-referrer');
assert.equal(call.options.headers['Content-Type'],'application/json');
assert.equal(collect({reject:true}).length,1,'a failed request is never retried');
''')

    def test_privacy_preferences_disabled_stats_file_and_unsafe_routes_never_submit(self):
        self.run_node(r'''
positive();
for(const navigator of [{doNotTrack:'1'},{doNotTrack:1},{doNotTrack:'yes'},{msDoNotTrack:'1'},{globalPrivacyControl:true}]) assert.equal(collect({navigator}).length,0);
assert.equal(collect({windowDnt:'1'}).length,0);
for(const enabled of [null,'false','',true]) assert.equal(collect({enabled}).length,0);
for(const protocol of ['file:','data:','httpx:']) assert.equal(collect({location:{protocol}}).length,0);
for(const pathname of ['/en/stats.html','/es/stats.html','/stats.html','/en/models/a.html?x=1','/en/models/a.html#x','/en/models/%78.html','/en/../secret.html','//en/index.html','/en/models/<x>.html','/api/stats/data']) assert.equal(collect({location:{pathname}}).length,0,'unsafe/non-document route admitted');
for(const pathname of ['/','/index.html','/en/','/es/catalogue.html','/en/sources.html','/en/years/1992.html']) assert.equal(collect({location:{pathname}}).length,1);
''')

    def test_referrer_domains_reduce_to_finite_buckets_with_boundaries(self):
        self.run_node(r'''
positive();
const examples=[['','direct'],['https://archive.example/en/?private=discard#discard','internal'],['https://github.com/person/repo?private=discard','github'],['https://gist.github.com/a','github'],['https://reddit.com/a','reddit'],['https://old.reddit.com/a','reddit'],['https://news.ycombinator.com/item?id=123','hacker-news'],['https://google.com/search?q=discard','search'],['https://www.google.es/search?q=discard','search'],['https://bing.com/search?q=discard','search'],['https://duckduckgo.com/?q=discard','search'],['https://search.yahoo.com/?p=discard','search'],['https://search.brave.com/search?q=discard','search'],['https://x.com/a','social'],['https://t.co/a','social'],['https://m.facebook.com/a','social'],['https://www.linkedin.com/a','social'],['https://github.com.evil.example/a','other'],['https://evilgithub.com/a','other'],['https://google.com.evil.example/a','other'],['https://news.ycombinator.com.evil.example/a','other'],['http://192.0.2.7/private','other'],['not a URL','other'],['file:///private','other']];
for(const [referrer,expected] of examples){const body=JSON.parse(collect({referrer})[0].options.body);assert.equal(body.source,expected);assert.equal(Object.keys(body).length,5)}
''')

    def test_user_agent_is_reduced_in_memory_not_sent_or_fingerprinted(self):
        self.run_node(r'''
positive();
const examples=[
['Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/126.0 Safari/537.36','desktop','chrome','windows'],
['Mozilla/5.0 (Macintosh; Intel Mac OS X 14_1) AppleWebKit/605.1.15 Version/17.0 Safari/605.1.15','desktop','safari','macos'],
['Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 CriOS/127.0 Mobile/15E148 Safari/604.1','mobile','chrome','ios'],
['Mozilla/5.0 (iPad; CPU OS 17_0 like Mac OS X) AppleWebKit/605.1.15 FxiOS/127.0 Mobile/15E148 Safari/605.1.15','tablet','firefox','ios'],
['Mozilla/5.0 (Linux; Android 14; Pixel) AppleWebKit/537.36 Chrome/126.0 Mobile Safari/537.36','mobile','chrome','android'],
['Mozilla/5.0 (Linux; Android 13; Tablet) AppleWebKit/537.36 Chrome/126.0 Safari/537.36','tablet','chrome','android'],
['Mozilla/5.0 (Windows NT 10.0) Chrome/126.0 Safari/537.36 Edg/126.0','desktop','edge','windows'],
['Mozilla/5.0 (Windows NT 10.0) Chrome/126.0 Safari/537.36 OPR/100.0','desktop','opera','windows'],
['','unknown','unknown','unknown'],['Unrecognized client','unknown','other','other']];
for(const [userAgent,device,browser,system] of examples){const body=JSON.parse(collect({navigator:{userAgent}})[0].options.body);assert.deepEqual([body.device,body.browser,body.system],[device,browser,system]);assert.equal(Object.keys(body).length,5)}
''')


DASHBOARD_HARNESS = r'''
const assert=require('node:assert/strict'),vm=require('node:vm'),fs=require('node:fs');
const script=fs.existsSync(process.argv[1])?fs.readFileSync(process.argv[1],'utf8'):'';
const copies=JSON.parse(process.argv[2]);
class Element {
  constructor(tag='div'){this.tagName=tag;this.attrs={};this.children=[];this.hidden=false;this.disabled=false;this.value='30';this._text='';this.events={};}
  set textContent(value){this._text=String(value);this.children=[];}
  get textContent(){return this._text+this.children.map(c=>c.textContent).join('');}
  set innerHTML(value){throw Error('HTML sink is forbidden')}
  setAttribute(k,v){this.attrs[k]=String(v)}
  getAttribute(k){return Object.hasOwn(this.attrs,k)?this.attrs[k]:null}
  removeAttribute(k){delete this.attrs[k]}
  appendChild(child){this.children.push(child);return child}
  append(...children){this.children.push(...children)}
  replaceChildren(...children){this._text='';this.children=[...children]}
  addEventListener(type,fn){this.events[type]=fn}
}
const flush=()=>new Promise(resolve=>setImmediate(resolve));
function data(days=30,total=2){
  const to=new Date('2026-10-29T00:00:00Z'),from=new Date(to.getTime()-(days-1)*86400000);
  const daily=Array.from({length:days},(_,i)=>({day:new Date(from.getTime()+i*86400000).toISOString().slice(0,10),count:i===days-1?total:0}));
  const bucket=value=>total?[{value,count:total}]:[];
  return {enabled:true,privacy:{storage:'daily_marginal_counters',retention_days:null,timezone:'UTC',unique_visitors:false,no_cookies:true,no_identifiers:true,geo:false},window:{days,from:daily[0].day,to:daily.at(-1).day},total,daily,pages:bucket('/en/'),sources:bucket('github'),devices:bucket('desktop'),browsers:bucket('firefox'),systems:bucket('linux'),languages:bucket('en'),export_url:'/api/stats/export.json'};
}
function boot(config={}){
  const ids={},events={},calls=[],intervals=[],timers=new Map();let timerID=0;
  for(const id of ['dashboard','controls','days','refresh','status','results','total','download-total','window','chart','daily','pages','sources','devices','browsers','systems','languages','traffic','traffic-chart','traffic-counts','traffic-crawlers','traffic-daily','traffic-status','document-total']) ids['stats-'+id]=new Element();
  ids['stats-chart'].clientWidth=config.chartWidth||1000;
  ids['stats-results'].hidden=true;ids['stats-controls'].hidden=true;
  ids['stats-dashboard'].attrs['data-stats-copy']=JSON.stringify(copies[config.lang||'en']);
  const document={visibilityState:config.hidden?'hidden':'visible',hidden:!!config.hidden,getElementById:id=>ids[id]||null,createElement:tag=>new Element(tag),createElementNS:(ns,tag)=>new Element(tag),addEventListener:(k,f)=>events[k]=f};
  const window={addEventListener:(k,fn)=>events['window:'+k]=fn,setInterval:(fn,delay)=>{intervals.push({fn,delay});return intervals.length},clearInterval(){},setTimeout:(fn,delay)=>{timers.set(++timerID,{fn,delay});return timerID},clearTimeout:id=>timers.delete(id)};
  const context={document,window,location:{protocol:config.protocol||'https:'},AbortController,URL,fetch:(url,options)=>{
    calls.push({url,options});
    if(config.fetch) return config.fetch(url,options);
    if(config.fail) return Promise.reject(Error('unavailable'));
    return Promise.resolve({ok:config.ok!==false,json:()=>config.jsonReject?Promise.reject(Error('bad json')):Promise.resolve(config.payload===undefined?data():config.payload)});
  }};
  for(const key of ['navigator','localStorage','sessionStorage','indexedDB','crypto']) Object.defineProperty(context,key,{get(){throw Error('dashboard must not collect')}});
  vm.runInNewContext(script,context);
  return {ids,document,events,calls,intervals,timers};
}
function positive(app){assert.equal(app.calls.length,1,'dashboard must request public data')}
(async()=>{
'''


@unittest.skipUnless(shutil.which('node'), 'Node is required for JS behavioral verification')
class StatsDashboard(unittest.TestCase):
    def run_node(self, code):
        module = stats_module()
        program = DASHBOARD_HARNESS + code + '\n})().catch(error=>{console.error(error);process.exitCode=1});'
        result = subprocess.run(['node', '--unhandled-rejections=strict', '-e', program, str(ROOT / 'assets/stats.js'), json.dumps(module.STATS_COPY)], capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_download_total_is_separate_localized_and_validated(self):
        module = stats_module()
        for lang, label in [('en', 'Catalogue downloads'), ('es', 'Descargas del catálogo')]:
            self.assertIn('id="stats-download-total"', module.stats_body(lang))
            self.assertIn(label, module.stats_body(lang))
        self.run_node(r'''
const payload=data();payload.downloads={total:4,versions:[{value:'0.5.6',count:4}],daily:payload.daily.map(r=>({day:r.day,count:r.day===payload.window.to?4:0}))};
const app=boot({payload});positive(app);await flush();
assert.equal(app.ids['stats-download-total'].textContent,'4');assert.equal(app.ids['stats-total'].textContent,'2');
for(const mutate of [p=>p.downloads.total=-1,p=>p.downloads.total='4',p=>p.downloads.daily.at(-1).count=3,p=>p.downloads.versions[0].value='arbitrary/path',p=>p.downloads.versions[0].count=3]){
 const bad=structuredClone(payload);mutate(bad);const failed=boot({payload:bad});await flush();assert.equal(failed.ids['stats-results'].hidden,true);
}
const old=boot();await flush();assert.equal(old.ids['stats-download-total'].textContent,'—','An older API must not invent download zeroes');
''')

    def test_real_api_contract_all_buckets_chart_and_text_only_rendering(self):
        self.run_node(r'''
const payload=data();payload.total=3;payload.daily.at(-1).count=3;
for(const name of ['pages','sources','devices','browsers','systems','languages']) payload[name][0].count=3;
payload.pages=[{value:'/en/',count:2},{value:'/es/models/x230.html',count:1}];
const app=boot({payload});positive(app);await flush();
assert.equal(app.calls[0].url,'/api/stats/data?days=30');
for(const [key,value] of Object.entries({method:'GET',mode:'same-origin',credentials:'omit',referrerPolicy:'no-referrer',cache:'no-store'})) assert.equal(app.calls[0].options[key],value);
assert.equal(app.ids['stats-total'].textContent,'3');assert.equal(app.ids['stats-results'].hidden,false);
assert.equal(app.ids['stats-status'].textContent,copies.en.ready);assert.equal(app.ids['stats-controls'].hidden,false);
assert.equal(app.ids['stats-window'].textContent,'2026-09-30 – 2026-10-29');
assert.equal(app.ids['stats-daily'].children.length,30);assert.equal(app.ids['stats-pages'].children.length,2);
const link=app.ids['stats-pages'].children[1].children[0].children[0];
assert.equal(link.tagName,'a');assert.equal(link.getAttribute('href'),'/es/models/x230.html');assert.equal(link.textContent,'/es/models/x230.html');
for(const name of ['sources','devices','browsers','systems','languages']) assert.equal(app.ids['stats-'+name].children.length,1);
assert.equal(app.ids['stats-sources'].children[0].children[0].textContent,'GitHub');
assert.equal(app.ids['stats-chart'].children.filter(c=>c.tagName==='rect').length,30);
assert.equal(app.ids['stats-export'],undefined);
assert.equal(app.timers.size,0,'completed requests must clear their timeout');
''')

    def test_loading_zero_unavailable_disabled_file_are_distinct(self):
        self.run_node(r'''
const loading=boot({fetch:()=>new Promise(()=>{})});positive(loading);
assert.equal(loading.ids['stats-status'].textContent,copies.en.loading);assert.equal(loading.ids['stats-results'].hidden,true);
const zero=boot({payload:data(30,0),lang:'es'});await flush();
assert.equal(zero.ids['stats-total'].textContent,'0');assert.equal(zero.ids['stats-status'].textContent,'');assert.equal(zero.ids['stats-results'].hidden,false);
for(const config of [{fail:true},{ok:false},{jsonReject:true}]){const failed=boot(config);await flush();assert.equal(failed.ids['stats-status'].textContent,copies.en.unavailable);assert.equal(failed.ids['stats-results'].hidden,true);assert.equal(failed.calls.length,1)}
const disabled=boot({payload:{enabled:false}});await flush();assert.equal(disabled.ids['stats-status'].textContent,copies.en.disabled);assert.equal(disabled.ids['stats-results'].hidden,true);
const file=boot({protocol:'file:'});await flush();assert.equal(file.calls.length,0);assert.equal(file.ids['stats-status'].textContent,copies.en.file);assert.equal(file.ids['stats-controls'].hidden,true);assert.equal(file.intervals.length,0);assert.equal(file.ids['stats-export'],undefined);
''')

    def test_zero_results_clear_old_status_and_keep_refresh_functional(self):
        self.run_node(r'''
for(const lang of ['en','es']){
  let payload=data(30,3);const app=boot({lang,fetch:()=>Promise.resolve({ok:true,json:()=>Promise.resolve(payload)})});
  positive(app);await flush();assert.equal(app.ids['stats-status'].textContent,copies[lang].ready);
  payload=data(30,0);app.ids['stats-refresh'].events.click();
  assert.equal(app.ids['stats-status'].textContent,copies[lang].loading);
  await flush();assert.equal(app.ids['stats-total'].textContent,'0');
  assert.equal(app.ids['stats-status'].textContent,'','zero counts need no redundant message');
  assert.equal(app.ids['stats-results'].hidden,false);
  assert.equal(app.ids['stats-dashboard'].getAttribute('aria-busy'),'false');
  assert.equal(app.calls.length,2);assert.equal(app.timers.size,0);
}
''')

    def test_every_bucket_is_visible_without_truncating_the_public_tail(self):
        self.run_node(r'''
const payload=data(),pages=Array.from({length:250},(_,n)=>({value:'/en/models/m'+String(n).padStart(3,'0')+'.html',count:1}));
payload.total=250;payload.pages=pages;payload.daily.at(-1).count=250;
for(const name of ['sources','devices','browsers','systems','languages']) payload[name][0].count=250;
const app=boot({payload});positive(app);await flush();
assert.equal(app.ids['stats-pages'].children.length,250);assert.equal(app.ids['stats-total'].textContent,'250');
''')

    def test_untrusted_invalid_inconsistent_api_values_never_become_results(self):
        self.run_node(r'''
const control=boot();positive(control);await flush();assert.equal(control.ids['stats-results'].hidden,false);
const mutations=[
p=>p.total=-1,p=>p.total='2',p=>p.total=Number.MAX_SAFE_INTEGER+1,p=>p.pages[0].value='javascript:alert(1)',p=>p.pages[0].value='//evil.example/en/',p=>p.pages[0].value='/en/models/<script>.html',p=>p.pages[0].value='/en/models/a.html?private=1',p=>p.pages[0].value='/en/models/%2e.html',p=>p.pages[0].value='/en/../x.html',p=>p.pages[0].value='/en/stats.html',
p=>p.sources[0].value='arbitrary-domain.example',p=>p.devices[0].value='fingerprint',p=>p.browsers[0].count=1.5,p=>p.systems[0].count=0,p=>p.languages[0].value='<img>',p=>p.languages.push({value:'en',count:1}),p=>p.daily.pop(),p=>p.daily[0].day='2026-02-30',p=>p.daily[0].count=2,p=>p.daily.reverse(),p=>p.window.days=90,p=>p.window.from='2026-09-29',p=>p.privacy.unique_visitors=true,p=>p.privacy.geo=true,p=>p.export_url='https://evil.example/export',p=>delete p.pages,
];
for(const mutate of mutations){const payload=data();mutate(payload);const app=boot({payload});await flush();assert.equal(app.ids['stats-status'].textContent,copies.en.unavailable,'invalid public response was displayed');assert.equal(app.ids['stats-results'].hidden,true)}
''')

    def test_period_refresh_visibility_cadence_and_latest_response_wins(self):
        self.run_node(r'''
const pending=[];const app=boot({fetch:()=>new Promise(resolve=>pending.push(resolve))});positive(app);
assert.equal(app.intervals.length,1);assert.equal(app.intervals[0].delay,60000);
app.ids['stats-days'].value='7';app.ids['stats-days'].events.change();assert.equal(app.calls.at(-1).url,'/api/stats/data?days=7');
pending[1]({ok:true,json:()=>Promise.resolve(data(7,1))});await flush();
pending[0]({ok:true,json:()=>Promise.resolve(data(30,99))});await flush();assert.equal(app.ids['stats-total'].textContent,'1','obsolete request must not overwrite the selected period');
app.document.visibilityState='hidden';app.document.hidden=true;app.intervals[0].fn();assert.equal(app.calls.length,2);
app.document.visibilityState='visible';app.document.hidden=false;app.events.visibilitychange();assert.equal(app.calls.length,3);
pending[2]({ok:true,json:()=>Promise.resolve(data(7,4))});await flush();app.intervals[0].fn();assert.equal(app.calls.length,4);
pending[3]({ok:true,json:()=>Promise.resolve(data(7,5))});await flush();app.ids['stats-refresh'].events.click();assert.equal(app.calls.length,5);
pending[4]({ok:true,json:()=>Promise.resolve(data(7,6))});await flush();
app.ids['stats-days'].value='999';app.ids['stats-days'].events.change();assert.equal(app.calls.length,5,'only declared windows may be requested');
const hidden=boot({hidden:true});await flush();assert.equal(hidden.calls.length,0);hidden.document.hidden=false;hidden.document.visibilityState='visible';hidden.events.visibilitychange();assert.equal(hidden.calls.length,1);
''')

    def test_all_time_period_requests_lifetime_and_checks_full_date_span(self):
        self.run_node(r'''
const payload=data(800,3);payload.window.days='all';
const app=boot({fetch:(url)=>Promise.resolve({ok:true,json:()=>Promise.resolve(url.endsWith('=all')?payload:data())})});
positive(app);await flush();
app.ids['stats-days'].value='all';app.ids['stats-days'].events.change();await flush();
assert.equal(app.calls.at(-1).url,'/api/stats/data?days=all');
assert.equal(app.ids['stats-results'].hidden,false,'all-time counters must render');
assert.equal(app.ids['stats-total'].textContent,'3');
assert.equal(app.ids['stats-daily'].children.length,800);
assert.equal(app.ids['stats-window'].textContent,payload.window.from+' – '+payload.window.to);
for(const mutate of [p=>p.daily.pop(),p=>p.window.to='2026-10-30',p=>p.window.from='2024-01-01',p=>p.privacy.retention_days=365]){
const bad=structuredClone(payload);mutate(bad);
const other=boot({fetch:()=>Promise.resolve({ok:true,json:()=>Promise.resolve(bad)})});
other.ids['stats-days'].value='all';other.ids['stats-days'].events.change();await flush();
assert.equal(other.ids['stats-results'].hidden,true,'invalid lifetime shape must fail closed');
}
''')

    def test_future_region_language_pages_remain_readable(self):
        self.run_node(r'''
for(const language of ['ast','pt-br','zh-hant','en-us']){
const route='/'+language+'/models/x230.html';
const payload=data();payload.pages=[{value:route,count:2}];payload.languages=[{value:language,count:2}];
const app=boot({payload});positive(app);await flush();
assert.equal(app.ids['stats-results'].hidden,false,'a generated language route must remain visible');
assert.equal(app.ids['stats-pages'].children[0].children[0].textContent,route);
assert.equal(app.ids['stats-languages'].children[0].children[0].textContent,language);
}
''')

    def test_unknown_route_prototype_names_do_not_become_inherited_labels(self):
        self.run_node(r'''
const payload=data();payload.languages=[{value:'to',count:2}];
const app=boot({payload});positive(app);await flush();
assert.equal(app.ids['stats-results'].hidden,false);assert.equal(app.ids['stats-languages'].children[0].children[0].textContent,'to');
''')

    def test_chart_viewport_preserves_readable_axis_labels_on_mobile(self):
        self.run_node(r'''
const app=boot({chartWidth:286});positive(app);await flush();
assert.equal(app.ids['stats-chart'].getAttribute('viewBox'),'0 0 286 180');
const labels=app.ids['stats-chart'].children.filter(c=>c.tagName==='text');
assert.equal(labels.at(-1).getAttribute('x'),'276');
const rects=app.ids['stats-chart'].children.filter(c=>c.tagName==='rect');assert.equal(rects.length,30);
assert.ok(Number(rects.at(-1).getAttribute('x'))<276);
app.ids['stats-chart'].clientWidth=720;app.events['window:resize']();
assert.equal(app.ids['stats-chart'].getAttribute('viewBox'),'0 0 720 180');assert.equal(app.calls.length,1,'resize must not collect or refetch');
''')

    def test_failed_refresh_removes_previously_displayed_counts(self):
        self.run_node(r'''
let fail=false;const app=boot({fetch:()=>fail?Promise.reject(Error('unavailable')):Promise.resolve({ok:true,json:()=>Promise.resolve(data())})});
positive(app);await flush();assert.equal(app.ids['stats-results'].hidden,false);assert.equal(app.ids['stats-total'].textContent,'2');
fail=true;app.ids['stats-refresh'].events.click();await flush();assert.equal(app.ids['stats-results'].hidden,true);assert.equal(app.ids['stats-total'].textContent,'—');assert.equal(app.ids['stats-status'].textContent,copies.en.unavailable);assert.equal(app.timers.size,0);
''')

    def test_request_timeout_clears_counts_and_does_not_retry(self):
        self.run_node(r'''
const app=boot({fetch:()=>new Promise(()=>{})});positive(app);
const timer=[...app.timers.values()][0];assert.ok(timer);assert.equal(timer.delay,10000);timer.fn();await flush();
assert.equal(app.ids['stats-status'].textContent,copies.en.unavailable);assert.equal(app.ids['stats-results'].hidden,true);assert.equal(app.calls.length,1);assert.equal(app.calls[0].options.signal.aborted,true);
''')


if __name__ == '__main__':
    unittest.main()
