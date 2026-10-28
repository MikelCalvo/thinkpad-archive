"""Catalogue-wide factual backfill regressions; no live network required."""
from pathlib import Path
import unittest

from thinkpad_archive.profiles import load_profiles
from thinkpad_archive.validation import load_catalogue

ROOT=Path(__file__).resolve().parents[1]


class ProfileBackfill(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalogue=load_catalogue(ROOT/'data')

    def profiles(self):
        source=ROOT/'data/profiles.json'
        self.assertTrue(source.is_file(),'Integrated profile backfill is missing')
        return load_profiles(source,{model['id']for model in self.catalogue['models']})

    def test_every_existing_model_has_an_explicit_profile_entry(self):
        profiles=self.profiles()
        self.assertEqual(len(profiles),666)
        self.assertEqual(set(profiles),{m['id']for m in self.catalogue['models']})
        self.assertIsNone(profiles['x201si']['summary'])
        self.assertEqual(profiles['x201si']['facts'],[])

    def test_catalogue_price_is_not_promoted_to_launch_price(self):
        prices=self.profiles()['700c']['prices']
        source=next(row for row in prices if row['amount']=='4350')
        self.assertEqual((source['kind'],source['date'],source['currency']),('catalogue','1994-05','USD'))

    def test_restricted_variant_and_panel_relationships_survive(self):
        profiles=self.profiles()
        fact=lambda mid,key:next(f for f in profiles[mid]['facts']if f['key']==key)
        self.assertEqual(fact('a22m-2628','graphics')['value']['en'],'2628-Sxx: ATI Rage Mobility M3 / AGP 2X / 8MB SDRAM')
        self.assertEqual(fact('t60p','display')['value']['en'],'14.1-inch SXGA+ (1400×1050), or 15.0-inch UXGA (1600×1200) FlexView/IPS.')
        self.assertNotIn('USB 3.0',fact('x220i','ports')['value']['en'])
        self.assertNotIn('eSATA',fact('t520i','ports')['value']['en'])

    def test_mixed_footer_is_not_an_exact_sku_announcement(self):
        profiles=self.profiles()
        mixed=[row for profile in profiles.values()for row in profile['dates']if 'Mixed announcement footer:'in row['scope']['en']]
        self.assertEqual(len(mixed),6)
        self.assertTrue(all(row['kind']=='documented_by'for row in mixed))

    def test_spanish_technical_values_are_not_mixed_english_templates(self):
        profiles=self.profiles()
        fact=lambda mid,key:next(f['value']['es'] for f in profiles[mid]['facts'] if f['key']==key)
        self.assertEqual(fact('x230','positioning'),'Portátil profesional')
        self.assertIn('6 filas',fact('x230','features'))
        self.assertNotIn('grey cover',fact('t14-gen-5-amd','weight'))
        self.assertNotIn('AC adapter',fact('t14-gen-5-amd','battery'))
        self.assertNotIn('Táctilpad',fact('x1-carbon-gen-12','weight'))
        self.assertNotIn('transfer speeds',fact('p1-gen-7','memory'))
        self.assertIn('auriculares/micrófono',fact('x1-carbon-gen-12','ports'))
        self.assertIn('hasta 80%',fact('t14-gen-5-amd','battery'))

    def test_known_conditional_memory_and_source_typo_are_corrected(self):
        profiles=self.profiles()
        self.assertIn('Lunar Lake',profiles['t14-gen-6-intel']['context']['en'])
        self.assertIn('Arrow Lake',profiles['t14-gen-6-intel']['context']['en'])
        self.assertTrue(any('LPCAMM2'in f['value']['en']for f in profiles['p1-gen-7']['facts']if f['key']=='memory'))
        display=next(f for f in profiles['yoga-12']['facts']if f['key']=='display')
        self.assertNotIn('1920x1081',display['value']['en'])
        self.assertIn('1920x1080',display['value']['en'])


if __name__=='__main__':unittest.main()
