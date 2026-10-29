"""HTML request classification: real no-script requests and finite marginal data."""
from contextlib import closing
from datetime import datetime, timedelta, timezone
import http.client
import json
import os
import shutil
from pathlib import Path
import socket
import sqlite3
import subprocess
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

import test_stats_backend as inherited
import test_stats_frontend as frontend
from thinkpad_archive import stats_server, stats_store

KNOWN = ('Googlebot', 'Bingbot', 'DuckDuckBot', 'Baiduspider', 'YandexBot', 'Applebot', 'GPTBot', 'OAI-SearchBot', 'ClaudeBot', 'Bytespider', 'PetalBot', 'Amazonbot')
VALUES = {'browser', 'unknown', 'other-bot', *KNOWN}


class Classifier(unittest.TestCase):
    def classify(self, value):
        self.assertTrue(callable(getattr(stats_server, 'classify_traffic', None)), 'Transient UA classifier is missing')
        return stats_server.classify_traffic(value)

    def test_known_tokens_and_automation_precede_browser(self):
        for token in KNOWN:
            with self.subTest(token=token):
                self.assertEqual(self.classify('Mozilla/5.0 (compatible; ' + token.swapcase() + '/2.1; +https://example.invalid/) Chrome/120.0'), token)
        for ua in ('curl/8.0', 'Wget/1.2', 'python-requests/2.1', 'SomeCrawler/1.0', 'ExampleBot/2.0', 'HeadlessChrome/120.0', 'Mozilla/5.0 Chrome/120.0 Selenium/4.0'):
            with self.subTest(ua=ua):
                self.assertEqual(self.classify(ua), 'other-bot')

    def test_false_boundaries_and_unknowns_never_become_named_crawlers(self):
        for token in KNOWN:
            for ua in ('Not' + token + '/1', token + '-fake/1', token + '.evil/1', token + '_evil/1', token + 'x/1', 'https://' + token + '/1'):
                with self.subTest(token=token, kind=ua):
                    self.assertNotIn(self.classify(ua), KNOWN)
        for ua in ('Mozilla/5.0 Firefox/128.0', 'Mozilla/5.0 Chrome/128.0 Safari/537.36', 'Mozilla/5.0 Version/17.0 Safari/605.1', 'Mozilla/5.0 FxiOS/20.0'):
            self.assertEqual(self.classify(ua), 'browser')
        for ua in (None, '', 'Unrecognized client', 'NotFirefox/128', 'Chrome/1.evil', 3, 'a'*2049, 'Googlebot/1\r\n'):
            self.assertEqual(self.classify(ua), 'unknown')


class TrafficStore(unittest.TestCase):
    def test_original_schema_history_finite_dimension_and_reopen(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = Path(tmp) / 'counts.sqlite'
            now = datetime(2022, 1, 1, tzinfo=timezone.utc)
            with closing(sqlite3.connect(db)) as conn:
                conn.execute(stats_store.SCHEMA)
                conn.execute("INSERT INTO counts VALUES('2021-01-01','total','all',7)")
                conn.commit()
            db.chmod(0o600)
            store = stats_store.AnalyticsStore(db, pages={'/en/'}, clock=lambda: now)
            self.addCleanup(store.close)
            self.assertIn('documents', store.data('all'), 'Document population is missing')
            before = store.export()['counts']
            self.assertEqual(store.data('all')['documents']['total'], 0, 'Old JS history is not browser history')
            self.assertTrue(callable(getattr(store, 'record_document', None)), 'Daily document writer is missing')
            for value in VALUES:
                store.record_document(value)
            saved = store.export()
            for bad in ('Googlebot-fake', 'human', '/en/', '', None, 2):
                with self.assertRaises(ValueError):
                    store.record_document(bad)
                self.assertEqual(store.export(), saved)
            data = store.data('all')
            docs = data['documents']
            self.assertEqual(docs['total'], len(VALUES))
            self.assertEqual(docs['browser'], 1); self.assertEqual(docs['unknown'], 1)
            self.assertEqual(docs['bots'], len(VALUES)-2)
            self.assertEqual({r['value'] for r in docs['crawlers']}, VALUES-{'browser','unknown'})
            self.assertEqual(sum(r['total'] for r in docs['daily']), len(VALUES))
            self.assertEqual(data['total'], 7); self.assertEqual(data['downloads']['total'], 0)
            self.assertEqual([r for r in saved['counts'] if r['dimension'] != 'document-traffic'], before)
            with closing(sqlite3.connect(db)) as conn:
                self.assertEqual(conn.execute("SELECT sql FROM sqlite_master WHERE name='counts'").fetchone()[0], stats_store.SCHEMA)
                self.assertEqual({r[0] for r in conn.execute('SELECT DISTINCT value FROM counts WHERE dimension=?', ('document-traffic',))}, VALUES)
            store.close()
            now += timedelta(days=1200)
            reopened = stats_store.AnalyticsStore(db, pages={'/en/'}, clock=lambda: now)
            self.addCleanup(reopened.close)
            self.assertEqual(reopened.export(), saved)
            self.assertEqual(reopened.data('all')['documents']['total'], len(VALUES))
            self.assertEqual(reopened.data(365)['documents']['total'], 0)


class TrafficHTTP(unittest.TestCase):
    # Reuse helpers, not the TestCase: discovery must not duplicate old tests.
    setUp = inherited.HTTPTests.setUp
    start = inherited.HTTPTests.start
    data = inherited.HTTPTests.data
    post = inherited.HTTPTests.post

    def request(self, server, *args, **kwargs):
        try:
            return inherited.HTTPTests.request(self, server, *args, **kwargs)
        finally:
            # Body receipt may precede the post-send transaction. Observe real
            # worker completion; do not retry requests or weaken exact counts.
            until=time.monotonic()+3
            while server._workers._value != stats_server.MAX_WORKERS and time.monotonic()<until:
                time.sleep(.005)
            self.assertEqual(server._workers._value,stats_server.MAX_WORKERS)

    def docs(self, server):
        data = self.data(server)
        self.assertIn('documents', data, 'HTML document aggregate is absent')
        return data['documents']

    def test_actual_no_js_get_counts_named_crawler_not_view_or_download(self):
        server = self.start()
        for path in ('/', '/index.html', '/en/', '/en/index.html', '/en/catalogue.html', '/en/years/2012.html', '/es/models/x230.html', '/en/?search=private'):
            status, headers, raw = self.request(server, path=path, headers={'User-Agent': 'Googlebot/2.1'})
            self.assertEqual(status, 200, 'Generated HTML must be served without JavaScript')
            self.assertEqual(headers['Content-Type'], 'text/html; charset=utf-8')
            actual = 'en/index.html' if path.startswith('/en/?') or path == '/en/' else 'index.html' if path == '/' else path.lstrip('/')
            self.assertEqual(raw, (self.site / actual).read_bytes())
        docs = self.docs(server)
        self.assertEqual(docs['total'], 8); self.assertEqual(docs['bots'], 8)
        self.assertEqual(docs['crawlers'], [{'value':'Googlebot','count':8}])
        self.assertEqual(self.data(server)['total'], 0)
        self.assertEqual(self.data(server)['downloads']['total'], 0)
        exported = json.loads(self.request(server, path='/api/stats/export.json')[2])
        self.assertEqual(exported['counts'], [{'day':'2026-10-29','dimension':'document-traffic','value':'Googlebot','count':8}])

    def test_browser_unknown_duplicate_ua_optouts_and_exclusions(self):
        server = self.start()
        self.assertEqual(self.request(server, path='/en/', headers={'User-Agent':'Mozilla/5.0 Firefox/128.0'})[0], 200)
        self.assertEqual(self.request(server, path='/en/')[0], 200)
        self.assertEqual(self.docs(server)['browser'], 1); self.assertEqual(self.docs(server)['unknown'], 1)
        before = self.request(server, path='/api/stats/export.json')[2]
        for header in ({'DNT':'1'}, {'DNT':' \t1 \t'}, {'Sec-GPC':'1\t'}):
            self.assertEqual(self.request(server, path='/en/', headers={'User-Agent':'GPTBot/1.0',**header})[0], 200)
            self.assertEqual(self.request(server, path='/api/stats/export.json')[2], before)
        for path in ('/en/stats.html','/assets/stats.js','/missing.html','/en/../index.html','/en/%69ndex.html','/en/index.html/extra'):
            self.assertEqual(self.request(server, path=path)[0], 404)
        self.assertEqual(self.request(server, method='HEAD', path='/en/')[0], 200)
        self.assertEqual(self.request(server, method='POST', path='/en/')[0], 405)
        self.assertEqual(self.request(server, path='/en/', headers={'Range':'bytes=0-1'})[0],416)
        self.assertEqual(self.request(server, path='/api/stats/health')[0],200)
        self.assertEqual(self.request(server, path='/api/stats/export.json')[2], before)
        with closing(http.client.HTTPConnection(*server.server_address, timeout=3)) as conn:
            conn.putrequest('GET','/en/'); conn.putheader('User-Agent','GPTBot/1'); conn.putheader('User-Agent','Firefox/1'); conn.endheaders()
            response=conn.getresponse(); self.assertEqual(response.status,200); response.read()
        self.assertEqual(self.docs(server)['unknown'],2)
        for order in (('1 \t','0'), ('0',' \t1')):
            before=self.request(server,path='/api/stats/export.json')[2]
            with closing(http.client.HTTPConnection(*server.server_address,timeout=3)) as conn:
                conn.putrequest('GET','/en/'); conn.putheader('User-Agent','GPTBot/1')
                for v in order: conn.putheader('DNT',v)
                conn.endheaders();response=conn.getresponse();self.assertEqual(response.status,200);response.read()
            self.assertEqual(self.request(server,path='/api/stats/export.json')[2],before)

    def test_disabled_reads_html_without_database_or_collection(self):
        server = self.start(enabled=False)
        self.assertEqual(self.request(server, path='/en/', headers={'User-Agent':'GPTBot/1'})[0],200)
        self.assertFalse(self.db.exists()); self.assertEqual(self.docs(server)['total'],0)

    def test_document_replacement_symlink_hardlink_size_and_identity_refused(self):
        server = self.start()
        self.assertEqual(self.request(server,path='/en/')[0],200)
        before=self.request(server,path='/api/stats/export.json')[2]
        target=self.site/'en/index.html'
        target.write_text('<html>changed</html>')
        self.assertEqual(self.request(server,path='/en/')[0],503)
        target.unlink();target.symlink_to(self.site/'index.html')
        self.assertNotEqual(self.request(server,path='/en/')[0],200)
        target.unlink();os.link(self.site/'index.html',target)
        self.assertNotEqual(self.request(server,path='/en/')[0],200)
        self.assertEqual(self.request(server,path='/api/stats/export.json')[2],before)

    def test_generated_route_scope_excludes_unrelated_html(self):
        for name in ('en/private.html','en/assets/probe.html','en/arbitrary/deep.html'):
            path=self.site/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_text('<html></html>')
        server=self.start()
        for path in ('/en/private.html','/en/assets/probe.html','/en/arbitrary/deep.html'):
            self.assertEqual(self.request(server,path=path)[0],404)
            self.assertEqual(self.post(server,{**self.event,'path':path})[0],400)

    def test_root_hardlink_is_rejected_before_parser_reads(self):
        root=self.site/'index.html'
        os.link(root,self.site/'copy.txt')
        from thinkpad_archive.stats_server import _RootLanguage
        with patch.object(_RootLanguage,'feed',side_effect=AssertionError('parser must not read unsafe root')) as feed:
            with self.assertRaises(ValueError): self.start()
            self.assertEqual(feed.call_count,0)

    def test_startup_rejects_hardlinked_or_oversized_html(self):
        target=self.site/'en/index.html'
        target.unlink();os.link(self.site/'index.html',target)
        with self.assertRaises(ValueError): self.start()
        target.unlink();target.write_bytes(b'x'*(2*1024*1024+1))
        with self.assertRaises(ValueError): self.start()

    def test_full_write_failure_and_original_absolute_deadline(self):
        from thinkpad_archive.stats_server import _Handler
        server=self.start()
        self.assertEqual(self.request(server,path='/en/')[0],200)
        before=self.request(server,path='/api/stats/export.json')[2]
        with patch.object(_Handler,'end_headers',side_effect=BrokenPipeError):
            with self.assertRaises((OSError,http.client.HTTPException)): self.request(server,path='/en/')
        self.assertEqual(self.request(server,path='/api/stats/export.json')[2],before)
        self.assertEqual(server.read_timeout,2.0)
        # A body-send stall uses the existing absolute HTML deadline, not ZIP's.
        original=_Handler.end_headers
        def slow(handler):
            if handler.path=='/en/': time.sleep(2.15)
            return original(handler)
        start=time.monotonic()
        with patch.object(_Handler,'end_headers',slow):
            with self.assertRaises((OSError,http.client.HTTPException)): self.request(server,path='/en/')
        self.assertLess(time.monotonic()-start,2.7)
        self.assertEqual(self.request(server,path='/api/stats/export.json')[2],before)


class TrafficDashboard(unittest.TestCase):
    run_node = frontend.StatsDashboard.run_node

    def test_bilingual_visual_native_exact_counts_and_semantic_methodology(self):
        for lang in ('en','es'):
            text=frontend.stats_module().stats_body(lang)
            ids={a.get('id'):(tag,a) for tag,a in frontend.Tags(text).tags if 'id' in a}
            for name in ('traffic','traffic-chart','traffic-counts','traffic-crawlers','traffic-daily','traffic-status','document-total'):
                self.assertIn('stats-'+name,ids,'Document traffic UI is missing')
            self.assertEqual(ids['stats-traffic-counts'][0],'tbody')
            self.assertEqual(ids['stats-traffic-chart'][1]['role'],'img')
            self.assertNotIn('<p',text.split('<header class="stats-heading">')[1].split('</header>')[0])
    @unittest.skipUnless(shutil.which('node'), 'Node is required for JS behavioral verification')
    def test_actual_dashboard_script_finite_documents_and_legacy_compatibility(self):
        self.run_node(r'''
function addDocuments(p,total=6){p.documents={total,browser:total?2:0,bots:total?3:0,unknown:total?1:0,crawlers:total?[{value:'Googlebot',count:2},{value:'other-bot',count:1}]:[],daily:p.daily.map(r=>({day:r.day,total:r.day===p.window.to?total:0,browser:r.day===p.window.to&&total?2:0,bots:r.day===p.window.to&&total?3:0,unknown:r.day===p.window.to&&total?1:0}))};return p;}
for(const lang of ['en','es']){
 const app=boot({lang,payload:addDocuments(data())});positive(app);await flush();
 assert.equal(app.ids['stats-document-total'].textContent,'6');assert.equal(app.ids['stats-total'].textContent,'2');
 assert.equal(app.ids['stats-traffic-counts'].children.length,3);assert.equal(app.ids['stats-traffic-crawlers'].children.length,2);
 assert.equal(app.ids['stats-traffic-chart'].children.filter(n=>n.tagName==='rect').length,3);
 assert.equal(app.ids['stats-traffic-daily'].children.length,30);assert.equal(app.ids['stats-traffic-status'].textContent,'');
 assert.ok(app.ids['stats-traffic-counts'].textContent.includes(copies[lang].traffic_browser));
}
const old=boot();await flush();assert.equal(old.ids['stats-document-total'].textContent,'—');assert.equal(old.ids['stats-traffic-status'].textContent,copies.en.traffic_absent);
const zero=boot({payload:addDocuments(data(30,0),0)});await flush();assert.equal(zero.ids['stats-document-total'].textContent,'0');assert.equal(zero.ids['stats-traffic-counts'].children.length,3);assert.equal(zero.ids['stats-traffic-status'].textContent,'');
for(const mutate of [p=>p.documents.total=-1,p=>p.documents.total='6',p=>p.documents.browser=3,p=>p.documents.bots=4,p=>p.documents.unknown=Number.MAX_SAFE_INTEGER+1,p=>p.documents.crawlers[0].value='Googlebot.evil',p=>p.documents.crawlers.push({value:'Googlebot',count:1}),p=>p.documents.daily.pop(),p=>p.documents.daily.at(-1).total=5,p=>p.documents.daily[0].day='2026-02-30',p=>p.documents.crawlers[0].count=1,p=>p.documents.daily[0].browser=1,p=>p.documents.crawlers[0].value='constructor']){
 const payload=addDocuments(data());mutate(payload);const app=boot({payload});await flush();assert.equal(app.ids['stats-results'].hidden,true);assert.equal(app.ids['stats-document-total'].textContent,'—');
}
let payload=addDocuments(data());const app=boot({fetch:()=>Promise.resolve({ok:true,json:()=>Promise.resolve(payload)})});await flush();payload=data(7);addDocuments(payload);app.ids['stats-days'].value='7';app.ids['stats-days'].events.change();await flush();assert.equal(app.ids['stats-traffic-daily'].children.length,7);assert.equal(app.calls.length,2);
''')

    def test_generated_exact_proxy_matcher_tracks_allowlisted_files_only(self):
        self.assertTrue(callable(getattr(stats_server,'document_proxy_matcher',None)), 'Generated document matcher is missing')
        inherited.HTTPTests.setUp(self)
        text=stats_server.document_proxy_matcher(self.site)
        self.assertIn('path / /en/',text)
        for route in ('/index.html','/en/index.html','/en/catalogue.html','/es/models/x230.html','/en/years/2012.html'):
            self.assertIn(route,text.split())
        for route in ('/en/stats.html','/es/stats.html','/assets/stats.js','/downloads/'):
            self.assertNotIn(route,text.split())

    def test_all_stats_proxy_branches_strip_identity_including_webhook(self):
        text=(Path(__file__).resolve().parents[1]/'deploy/Caddyfile.stats').read_text()
        branches=text.split('reverse_proxy ')[1:]
        self.assertEqual(len(branches),4)
        for i,branch in enumerate(branches):
            with self.subTest(branch=i):
                for key in ('Cookie','Authorization','Referer','Forwarded','X-Forwarded-For','X-Forwarded-Host','X-Forwarded-Proto','X-Real-IP'):
                    self.assertIn('header_up -'+key,branch)
                if i != 1:
                    self.assertIn('header_up User-Agent ""',branch)
                    self.assertNotIn('header_up -User-Agent',branch)

    def test_proxy_has_document_only_ua_forwarding_and_static_default_is_unchanged(self):
        root=Path(__file__).resolve().parents[1]
        text=(root/'deploy/Caddyfile.stats').read_text()
        self.assertIn('handle @catalogueDocument',text,'Exact document proxy branch is missing')
        branch=text.split('handle @catalogueDocument',1)[1].split('handle /api/stats/*',1)[0]
        self.assertNotIn('header_up -User-Agent',branch)
        for key in ('Cookie','Authorization','Referer','Forwarded','X-Forwarded-For','X-Forwarded-Host','X-Forwarded-Proto','X-Real-IP'):
            self.assertIn('header_up -'+key,branch)
        self.assertIn('flush_interval -1',branch)
        self.assertNotIn('stats', (root/'deploy/Caddyfile').read_text())
