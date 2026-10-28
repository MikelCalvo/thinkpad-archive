"""Source-backed profile contract; all support identities remain independent."""
from pathlib import Path
import copy
import importlib
import json
import tempfile
import unittest

from thinkpad_archive.validation import load_catalogue, load_locales

ROOT = Path(__file__).resolve().parents[1]


def profile():
    return {
        'model_id':'t30',
        'summary':{'en':'Mobile Pentium 4-M business notebook.', 'es':'Portátil de trabajo con Pentium 4-M.'},
        'context':{'en':'Optional wireless and a removable optical drive.', 'es':'Conexión inalámbrica opcional y unidad óptica extraíble.'},
        'facts':[{'key':'processor','value':{'en':'Pentium 4-M','es':'Pentium 4-M'},'scope':{'en':'2366 configurations','es':'Configuraciones 2366'},'sources':['psref']}],
        'dates':[{'date':'2002-04-23','kind':'announcement','scope':{'en':'US models; available May 2002','es':'Modelos de EE. UU.; disponibles en mayo de 2002'},'sources':['psref']}],
        'prices':[{'amount':'4350','currency':'USD','kind':'catalogue','date':'1994-05','scope':{'en':'Synthetic schema fixture, not T30 historical data','es':'Fixture sintético de esquema, no dato histórico del T30'},'sources':['psref']}],
        'markets':[{'exclusive':None,'scope':{'en':'US configurations documented; exclusivity not established','es':'Configuraciones de EE. UU. documentadas; exclusividad no establecida'},'sources':['psref']}],
        'references':[{'id':'psref','url':'https://psrefstuff.lenovo.com/syspool/Sys/PDF/withdrawnbook/tawbook.pdf#page=41','title':'IBM PSREF T30','kind':'official','locator':'page 41'}],
    }


class Profiles(unittest.TestCase):
    def api(self):
        self.assertTrue((ROOT/'thinkpad_archive/profiles.py').is_file(), 'Profile validation API is missing')
        return importlib.import_module('thinkpad_archive.profiles')

    def validate(self, rows=None, ids=None):
        return self.api().validate_profiles({'schema_version':1,'profiles':rows if rows is not None else [profile()]}, ids or {'t30'})

    def test_sourced_profiles_are_indexed_by_exact_catalogue_identity(self):
        result = self.validate()
        self.assertEqual(result['t30']['facts'][0]['value']['en'], 'Pentium 4-M')

    def test_missing_duplicate_unknown_identities_and_unknown_fields_refused(self):
        for rows,ids in [([],{'t30'}),([profile(),profile()],{'t30'}),([dict(profile(),model_id='t30p')],{'t30'}),([dict(profile(),host_path='/home/private')],{'t30'})]:
            with self.subTest(rows=len(rows),ids=ids), self.assertRaises(ValueError):
                self.validate(rows,ids)

    def test_unknown_sources_unsafe_urls_and_invalid_provenance_refused(self):
        mutations = [lambda p:p['facts'][0].update(sources=['missing']),
                     lambda p:p['facts'][0].update(sources=[]),
                     lambda p:p['references'][0].update(url='file:///home/private/source.pdf'),
                     lambda p:p['references'][0].update(url='https://user:password@example.test/'),
                     lambda p:p['references'][0].update(kind='guessed'),
                     lambda p:p['summary'].pop('es'),
                     lambda p:p.update(references=[]),
                     lambda p:p['markets'][0].update(exclusive='yes')]
        for index,mutate in enumerate(mutations):
            p=profile(); mutate(p)
            with self.subTest(case=index), self.assertRaises(ValueError): self.validate([p])

    def test_date_meaning_precision_and_currency_are_validated(self):
        for field,value in [('date','2002-02-30'),('date','2002-13'),('date','May 2002'),('kind','driver_release')]:
            p=profile();p['dates'][0][field]=value
            with self.subTest(field=field,value=value),self.assertRaises(ValueError):self.validate([p])
        for date in ('2002','2002-05','2002-05-01'):
            p=profile();p['dates'][0]['date']=date;self.validate([p])
        for field,value in [('amount','NaN'),('amount','-4'),('currency','dollars'),('kind','used')]:
            p=profile();p['prices'][0][field]=value
            with self.subTest(field=field,value=value),self.assertRaises(ValueError):self.validate([p])

    def test_empty_researched_entry_is_not_fabricated(self):
        p={'model_id':'t30','summary':None,'context':None,'facts':[],'dates':[],'prices':[],'markets':[],'references':[]}
        self.assertIsNone(self.validate([p])['t30']['summary'])

    def test_reader_rejects_duplicate_json_keys(self):
        api=self.api()
        with tempfile.TemporaryDirectory()as directory:
            p=Path(directory)/'profiles.json';p.write_text('{"schema_version":1,"schema_version":1,"profiles":[]}')
            with self.assertRaises(ValueError):api.load_profiles(p,set())

    def test_period_prices_render_without_truncating_integer_zeroes(self):
        from thinkpad_archive.model_design import ModelDesignRenderer
        renderer=ModelDesignRenderer({'documents':[],'drivers':[],'sources':[]}, {})
        p=profile()
        for value,en,es in [('4350.00','4,350 USD','4.350 USD'),('100.50','100.5 USD','100,5 USD'),('1200','1,200 USD','1.200 USD')]:
            p['prices'][0]['amount']=value
            sample=renderer.profile_sample(p)
            self.assertEqual(sample['price']['value'],en)
            self.assertEqual(sample['price']['es_value'],es)

    def test_renderer_uses_profiles_and_keeps_citations_at_the_bottom(self):
        from thinkpad_archive.model_design import ModelDesignRenderer
        data=load_catalogue(ROOT/'data');locales=load_locales(ROOT/'locales')
        p=profile();p['prices']=[]
        renderer=ModelDesignRenderer(data,locales,profiles=self.validate([p]))
        model=next(m for m in data['models']if m['id']=='t30')
        for lang in ('en','es'):
            html=renderer.model(lang+'/models/t30.html',lang,model)
            self.assertIn(p['summary'][lang],html)
            self.assertIn(p['facts'][0]['scope'][lang],html)
            self.assertIn(p['markets'][0]['scope'][lang],html)
            self.assertIn('23 April 2002'if lang=='en'else'23 de abril de 2002',html)
            bottom=html.split('id="sources"')[1]
            self.assertIn('IBM PSREF T30',bottom)
            self.assertNotIn('model-deck',html)
            self.assertNotIn('category-nav',html)
            self.assertNotIn('model-jumps',html)
            self.assertIn(locales[lang]['firmware_warning_text'],html)

    def test_spec_table_contains_values_without_repeated_scope_disclaimers(self):
        from thinkpad_archive.model_design import ModelDesignRenderer
        data=load_catalogue(ROOT/'data');locales=load_locales(ROOT/'locales')
        p=profile()
        p['facts'][0]['value']={'en':'Pentium 4-M, up to 1.8 GHz','es':'Pentium 4-M, hasta 1,8 GHz'}
        p['facts'][0]['scope']={
            'en':'Selected US PSREF sheet. Only the listed configurations, not the worldwide range.',
            'es':'Ficha PSREF seleccionada de EE. UU. Solo las configuraciones indicadas, no toda la gama mundial.'}
        renderer=ModelDesignRenderer(data,locales,profiles=self.validate([p]))
        model=next(m for m in data['models']if m['id']=='t30')
        for lang in ('en','es'):
            html=renderer.model(lang+'/models/t30.html',lang,model)
            panel=html.split('<section id="specifications"',1)[1].split('</section>',1)[0]
            bottom=html.split('id="sources"',1)[1]
            self.assertIn(p['facts'][0]['value'][lang],panel)
            self.assertNotIn(p['facts'][0]['scope'][lang],panel)
            self.assertNotIn('class="spec-note"',panel)
            self.assertIn(p['facts'][0]['scope'][lang],bottom)

    def test_earlier_exact_sku_announcement_precedes_later_family_refresh(self):
        from thinkpad_archive.model_design import ModelDesignRenderer
        p=profile()
        p['dates'][0]['kind']='sku_announcement'
        later=copy.deepcopy(p['dates'][0]);later.update(date='2003-08-01',kind='announcement')
        p['dates'].append(later)
        renderer=ModelDesignRenderer({'documents':[],'drivers':[],'sources':[]},{})
        self.assertEqual(renderer.profile_sample(p)['release']['en'],'23 April 2002')

    def test_earlier_availability_is_not_hidden_by_later_sku_refresh(self):
        from thinkpad_archive.model_design import ModelDesignRenderer
        p=profile()
        p['dates'][0].update(date='2001-08-07',kind='sku_announcement')
        earlier=copy.deepcopy(p['dates'][0]);earlier.update(date='2001-04',kind='availability')
        p['dates'].append(earlier)
        renderer=ModelDesignRenderer({'documents':[],'drivers':[],'sources':[]},{})
        self.assertEqual(renderer.profile_sample(p)['release']['en'],'April 2001')
        self.assertTrue(renderer.profile_sample(p)['release_scope']['en'].startswith('Availability'))

    def test_profile_prose_references_are_not_lost_when_fact_rows_exist(self):
        from thinkpad_archive.model_design import ModelDesignRenderer
        p=profile()
        p['references'].append({'id':'prose-source','url':'https://example.org/model-history',
                                'title':'Source for historical narrative','kind':'press','locator':'Discontinuation'})
        renderer=ModelDesignRenderer({'documents':[],'drivers':[],'sources':[]},{})
        html=renderer.profile_references('en',p)
        self.assertIn('https://example.org/model-history',html)
        self.assertIn('Source for historical narrative',html)

    def test_profile_pages_describe_gaps_without_claiming_research_is_pending(self):
        from thinkpad_archive.model_design import ModelDesignRenderer
        data=load_catalogue(ROOT/'data');locales=load_locales(ROOT/'locales')
        p=profile();p.update(summary=None,context=None,facts=[],markets=[],prices=[])
        renderer=ModelDesignRenderer(data,locales,profiles=self.validate([p]))
        model=next(m for m in data['models']if m['id']=='t30')
        for lang in ('en','es'):
            html=renderer.model(lang+'/models/t30.html',lang,model)
            self.assertNotIn('catalogue-wide research pass is still pending',html)
            self.assertNotIn('investigación del catálogo completo queda pendiente',html)
            self.assertNotIn('after the design is approved',html)
            self.assertNotIn('tras aprobar el diseño',html)
            self.assertIn('No source confirmed' if lang=='en' else 'No se ha confirmado una fuente',html)

    def test_preview_builder_consumes_validated_profile_file_before_output(self):
        import importlib.util
        spec=importlib.util.spec_from_file_location('preview_model_design_under_test',ROOT/'tools/preview_model_design.py')
        assert spec is not None and spec.loader is not None
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        build_preview=module.build_preview
        data=load_catalogue(ROOT/'data')
        rows=[{'model_id':m['id'],'summary':None,'context':None,'facts':[],'dates':[],'prices':[],'markets':[],'references':[]} for m in data['models']]
        rows=[profile() if p['model_id']=='t30' else p for p in rows]
        with tempfile.TemporaryDirectory() as directory:
            source=Path(directory)/'profiles.json';source.write_text(json.dumps({'schema_version':1,'profiles':rows}))
            destination=Path(directory)/'site'
            output,generated=build_preview(destination,profiles_path=source)
            self.assertEqual(len(generated),len(data['models'])*2)
            self.assertIn('Portátil de trabajo con Pentium 4-M.',(output/'es/models/t30.html').read_text())
            source.write_text('{"schema_version":1,"profiles":[]}')
            rejected=Path(directory)/'rejected'
            with self.assertRaises(ValueError):build_preview(rejected,profiles_path=source)
            self.assertFalse(rejected.exists())

    def test_enriched_values_are_escaped(self):
        from thinkpad_archive.model_design import ModelDesignRenderer
        data=load_catalogue(ROOT/'data');locales=load_locales(ROOT/'locales');p=profile()
        p['summary']['es']='<script>not_markup()</script>'
        renderer=ModelDesignRenderer(data,locales,profiles=self.validate([p]))
        model=next(m for m in data['models']if m['id']=='t30')
        html=renderer.model('es/models/t30.html','es',model)
        self.assertIn('&lt;script&gt;not_markup()',html)
        self.assertNotIn('<script>not_markup()',html)


if __name__=='__main__':unittest.main()
