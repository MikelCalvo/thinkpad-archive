"""Adaptive model pages: known header facts and progressively disclosed specs."""
from pathlib import Path
from html.parser import HTMLParser
import copy
import re
import unittest

from thinkpad_archive.model_design import ModelDesignRenderer
from thinkpad_archive.profiles import load_profiles
from thinkpad_archive.validation import load_catalogue, load_locales

ROOT=Path(__file__).resolve().parents[1]


class FactsParser(HTMLParser):
    def __init__(self, html):
        super().__init__(convert_charrefs=True)
        self.groups=[]
        self.feed(html)
    def handle_starttag(self, tag, attrs):
        attrs=dict(attrs)
        if tag=='details' and 'spec-group' in (attrs.get('class') or '').split():
            self.groups.append(attrs)


class DetailRefresh(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data=load_catalogue(ROOT/'data')
        cls.models={m['id']:m for m in cls.data['models']}
        cls.locales=load_locales(ROOT/'locales')
        cls.profiles=load_profiles(ROOT/'data/profiles.json',set(cls.models))

    def render(self, mid, lang='es', profile=None):
        profiles=self.profiles if profile is None else {mid:profile}
        renderer=ModelDesignRenderer(self.data,self.locales,profiles=profiles)
        return renderer.model(lang+'/models/'+mid+'.html',lang,self.models[mid])

    def overview(self, html):
        return html.split('<section id="overview"',1)[1].split('</section>',1)[0]

    def test_unknown_price_and_nonexclusive_market_do_not_take_header_space(self):
        for mid in ('a30p','x201si'):
            for lang in ('en','es'):
                with self.subTest(mid=mid,lang=lang):
                    overview=self.overview(self.render(mid,lang))
                    self.assertNotIn('data-header-fact="price"',overview)
                    self.assertNotIn('data-header-fact="market"',overview)
                    self.assertNotIn('pending-fact',overview)
                    self.assertNotIn('launch-facts',overview)
                    self.assertIn('class="model-meta"',overview)

    def test_documented_distribution_does_not_imply_exclusivity(self):
        p=copy.deepcopy(self.profiles['x230'])
        p['markets']=[{'exclusive':None,'scope':{'en':'US listing only, not exclusivity','es':'Listado estadounidense, no exclusividad'},'sources':[p['references'][0]['id']]}]
        for exclusive in (None,False):
            p['markets'][0]['exclusive']=exclusive
            html=self.render('x230',profile=p)
            self.assertNotIn('data-header-fact="market"',self.overview(html))
            self.assertIn('Listado estadounidense, no exclusividad',html.split('id="sources"',1)[1])

    def test_only_explicit_exclusivity_has_a_short_market_label(self):
        for lang,label in [('en','Japan exclusive'),('es','Exclusivo de Japón')]:
            html=self.render('220',lang)
            overview=self.overview(html)
            self.assertIn('data-header-fact="market"',overview)
            self.assertIn(label,overview)
            for row in self.profiles['220']['markets']:
                self.assertNotIn(row['scope'][lang],overview)
                self.assertIn(row['scope'][lang],html.split('id="sources"',1)[1])

    def test_known_price_keeps_catalogue_meaning_and_full_scope_at_end(self):
        html=self.render('700c')
        overview=self.overview(html)
        self.assertIn('data-header-fact="price"',overview)
        self.assertIn('4.350 USD',overview)
        self.assertIn('Precio de catálogo',overview)
        self.assertIn('mayo de 1994',overview)
        self.assertNotIn('<p>',overview.split('class="model-meta"',1)[1].split('</dl>',1)[0])
        for price in self.profiles['700c']['prices']:
            self.assertIn(price['scope']['es'],html.split('id="sources"',1)[1])

    def test_launch_price_does_not_repeat_the_same_announcement_date(self):
        html=self.render('x230')
        meta=self.overview(html).split('class="model-meta"',1)[1].split('</dl>',1)[0]
        self.assertEqual(meta.count('15 de mayo de 2012'),1)
        self.assertIn('1.179 USD',meta)

    def test_date_header_has_concise_kind_not_a_source_paragraph(self):
        html=self.render('x230')
        meta=self.overview(html).split('class="model-meta"',1)[1].split('</dl>',1)[0]
        self.assertIn('Anuncio',meta)
        self.assertIn('15 de mayo de 2012',meta)
        self.assertNotIn(self.profiles['x230']['dates'][0]['scope']['es'],meta)
        self.assertIn(self.profiles['x230']['dates'][0]['scope']['es'],html.split('id="sources"',1)[1])

    def test_specs_are_grouped_closed_and_preserve_every_value(self):
        for mid in ('x230','a30p','t14-gen-5-amd','p1-gen-7'):
            for lang in ('en','es'):
                with self.subTest(mid=mid,lang=lang):
                    html=self.render(mid,lang)
                    spec=html.split('<section id="specifications"',1)[1].split('</section>',1)[0]
                    groups=FactsParser(spec).groups
                    self.assertTrue(1<=len(groups)<=4)
                    self.assertTrue(all('open'not in g for g in groups))
                    keys=re.findall(r'data-fact-key="([a-z_]+)"',spec)
                    self.assertCountEqual(keys,[f['key']for f in self.profiles[mid]['facts']])
                    for f in self.profiles[mid]['facts']:
                        self.assertIn(f['value'][lang].replace('&','&amp;').replace('"','&quot;').replace('>','&gt;').replace('<','&lt;'),spec)
                    self.assertNotIn('spec-note',spec)
                    self.assertNotIn('spec-panel',self.overview(html))
                    self.assertLess(html.index('id="specifications"'),html.index('id="manuals"'))

    def test_sparse_identity_does_not_repeat_empty_context_and_specs(self):
        overview=self.overview(self.render('x201si'))
        self.assertNotIn('era-story',overview)
        self.assertNotIn('Perspectiva histórica',overview)
        self.assertNotIn('Sin fuente suficiente para el precio',overview)
        self.assertEqual(overview.count('No se ha confirmado una fuente'),1)
        self.assertNotIn('id="specifications"',self.render('x201si'))

    def test_layout_is_full_width_specs_with_left_aligned_values(self):
        css=(ROOT/'assets/model-design.css').read_text()
        self.assertIn('.spec-groups{',css)
        self.assertIn('.spec-group>summary',css)
        self.assertIn('.model-meta{',css)
        value_rule=css.split('.key-specs dd{',1)[1].split('}',1)[0]
        self.assertIn('text-align:left',value_rule)
        self.assertNotIn('font-weight:600',value_rule)


if __name__=='__main__':unittest.main()
