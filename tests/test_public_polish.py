"""Public navigation, external-link and local-only theme regressions."""
from html.parser import HTMLParser
from pathlib import Path
import os
import shutil
import subprocess
import tempfile
import unittest

import test_build as fixtures

ROOT = Path(__file__).resolve().parents[1]
REPO = 'https://github.com/MikelCalvo/thinkpad-archive'


class Tags(HTMLParser):
    def __init__(self, text):
        super().__init__(convert_charrefs=True)
        self.tags = []
        self.feed(text)

    def handle_starttag(self, tag, attrs):
        self.tags.append((tag, dict(attrs)))


class PublicPolish(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=os.environ.get('TMPDIR'))
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        fixtures.write_fixture(self.root / 'data')
        import thinkpad_archive
        self.output = thinkpad_archive.build_site(self.root / 'site', data_dir=self.root / 'data')

    def test_all_external_links_open_safely_in_new_tabs_but_internal_stay(self):
        external = internal = pdfs = 0
        for path in self.output.rglob('*.html'):
            for tag, attrs in Tags(path.read_text()).tags:
                if tag != 'a':
                    continue
                href = attrs.get('href', '')
                if href.startswith('https://'):
                    external += 1
                    pdfs += '.pdf' in href
                    self.assertEqual(attrs.get('target'), '_blank', href)
                    self.assertTrue({'noopener', 'noreferrer'} <= set(attrs.get('rel', '').split()), href)
                else:
                    internal += 1
                    self.assertNotIn('target', attrs, href)
        self.assertGreater(external, 0)
        self.assertGreater(internal, 0)
        self.assertGreater(pdfs, 0)

    def test_header_controls_order_and_localized_accessibility_on_all_pages(self):
        for path in self.output.rglob('*.html'):
            text = path.read_text()
            header = text.split('<header', 1)[1].split('</header>', 1)[0]
            tags = Tags(header).tags
            buttons = [a for tag, a in tags if tag == 'button' and a.get('id') == 'theme-toggle']
            self.assertEqual(len(buttons), 1)
            button = buttons[0]
            self.assertIn('hidden', button)  # no inert control without JavaScript
            self.assertTrue(button.get('data-light-label'))
            self.assertTrue(button.get('data-dark-label'))
            github = [a for tag, a in tags if tag == 'a' and a.get('href') == REPO]
            self.assertEqual(len(github), 1)
            self.assertTrue(github[0].get('aria-label'))
            self.assertLess(header.index('class="main-nav"'), header.index('class="language-nav"'))
            self.assertLess(header.index('id="language-picker"'), header.index('id="theme-toggle"'))
            self.assertLess(header.index('class="main-nav"'), header.index('id="theme-toggle"'))
            self.assertLess(header.index('id="theme-toggle"'), header.index('class="github-link'))
            self.assertIn('class="theme-moon"', header)
            self.assertIn('class="theme-sun"', header)

    def test_theme_bootstrap_is_local_early_and_nojs_css_defaults_dark(self):
        for relative in ('index.html', 'en/models/700c.html', 'es/sources.html'):
            text = (self.output / relative).read_text()
            theme = [a for tag, a in Tags(text).tags if tag == 'script' and a.get('src', '').endswith('/theme.js')]
            self.assertEqual(len(theme), 1)
            self.assertNotIn('defer', theme[0])
            self.assertLess(text.index(theme[0]['src']), text.index('rel="stylesheet"'))
        self.assertTrue((self.output / 'assets/theme.js').is_file())
        css = (self.output / 'assets/style.css').read_text()
        self.assertNotIn('prefers-color-scheme', css)
        self.assertIn('[data-theme="dark"]', css)
        self.assertIn('var(--firmware)', css)

    def test_dark_theme_accents_remain_red_not_pink(self):
        import re
        css = (self.output/'assets/style.css').read_text()
        for selector in (':root[data-theme="dark"]', ':root:not([data-theme])'):
            declarations = css.split(selector + '{', 1)[1].split('}', 1)[0]
            for token in ('red', 'red-dark'):
                color = re.search(r'--' + token + r':#([0-9a-fA-F]{6});', declarations)
                self.assertIsNotNone(color)
                red, green, blue = [int(color[1][i:i+2], 16) for i in (0, 2, 4)]
                self.assertGreaterEqual(red, 200)
                self.assertLess(green, 100, (selector, token))
                self.assertLess(blue, 100, (selector, token))

    def test_dark_red_has_normal_text_contrast_on_every_accent_surface(self):
        import re
        def luminance(color):
            rgb = [int(color[i:i+2], 16)/255 for i in (0, 2, 4)]
            linear = [v/12.92 if v <= .04045 else ((v+.055)/1.055)**2.4 for v in rgb]
            return sum(a*b for a,b in zip(linear, (.2126, .7152, .0722)))
        css = (self.output/'assets/style.css').read_text()
        for selector in (':root[data-theme="dark"]', ':root:not([data-theme])'):
            declarations = css.split(selector+'{', 1)[1].split('}', 1)[0]
            colors = dict(re.findall(r'--([a-z-]+):#([0-9a-fA-F]{6});', declarations))
            foreground = luminance(colors['red'])
            for surface in ('paper', 'card', 'tint', 'row-hover', 'firmware'):
                background = luminance(colors[surface])
                contrast = (max(foreground, background)+.05)/(min(foreground, background)+.05)
                self.assertGreaterEqual(contrast, 4.5, (selector, surface, contrast))

    @unittest.skipUnless(shutil.which('node'), 'Node is optional theme verification tooling')
    def test_theme_preference_persists_and_storage_refusal_does_not_break_control(self):
        script = self.output / 'assets/theme.js'
        self.assertTrue(script.is_file(), 'local theme bootstrap is required')
        js = r'''
const assert = require('node:assert/strict');
const vm = require('node:vm');
const fs = require('node:fs');
const source = fs.readFileSync(process.argv[1], 'utf8');
function start(stored, systemDark, blocked=false) {
  const attrs = {}, handlers = {}, media = {}, win = {}, writes = [];
  const button = {hidden:true,attrs:{'data-light-label':'Switch to light','data-dark-label':'Switch to dark'},
    getAttribute(k){return this.attrs[k];},setAttribute(k,v){this.attrs[k]=v;},
    addEventListener(k,f){handlers[k]=f;}};
  const root = {setAttribute(k,v){attrs[k]=v;},getAttribute(k){return attrs[k];}};
  const document = {documentElement:root,readyState:'loading',getElementById:()=>button,
    addEventListener(k,f){handlers[k]=f;}};
  const context = {document, window:{matchMedia(){return {matches:systemDark,addEventListener(k,f){media[k]=f;}};},
    addEventListener(k,f){win[k]=f;}},localStorage:{getItem(){if(blocked)throw Error('blocked');return stored;},
    setItem(k,v){if(blocked)throw Error('blocked');writes.push([k,v]);stored=v;}}};
  vm.runInNewContext(source, context);
  handlers.DOMContentLoaded();
  return {attrs,handlers,button,writes,media,win};
}
const first=start(null,false);assert.equal(first.attrs['data-theme'],'dark');
assert.equal(first.button.hidden,false);assert.equal(first.button.attrs['aria-label'],'Switch to light');
first.handlers.click();assert.equal(first.attrs['data-theme'],'light');
assert.equal(first.button.attrs['aria-label'],'Switch to dark');
assert.equal(first.writes.length,1);assert.equal(first.writes[0][1],'light');
assert.equal(start('dark',false).attrs['data-theme'],'dark');
assert.equal(start('light',true).attrs['data-theme'],'light');
assert.equal(start('invalid',false).attrs['data-theme'],'dark');
assert.equal(start(null,true).attrs['data-theme'],'dark');
const denied=start(null,false,true);assert.equal(denied.attrs['data-theme'],'dark');denied.handlers.click();assert.equal(denied.attrs['data-theme'],'light');
const system=start(null,false);if(system.media.change)system.media.change({matches:false});assert.equal(system.attrs['data-theme'],'dark');
system.handlers.click();if(system.media.change)system.media.change({matches:true});assert.equal(system.attrs['data-theme'],'light');
system.win.storage({key:'thinkpad-archive-theme',newValue:'dark'});assert.equal(system.attrs['data-theme'],'dark');
system.win.storage({key:'thinkpad-archive-theme',newValue:'light'});assert.equal(system.attrs['data-theme'],'light');
system.win.storage({key:'thinkpad-archive-theme',newValue:null});assert.equal(system.attrs['data-theme'],'dark');
system.win.storage({key:'thinkpad-archive-theme',newValue:'invalid'});assert.equal(system.attrs['data-theme'],'dark');
system.win.storage({key:'unrelated',newValue:'light'});assert.equal(system.attrs['data-theme'],'dark');
console.log('theme preference and failure paths passed');
'''
        result = subprocess.run(['node', '-e', js, str(script)], capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('theme preference and failure paths passed', result.stdout)


if __name__ == '__main__':
    unittest.main()
