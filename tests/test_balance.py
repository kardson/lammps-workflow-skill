import csv
from pathlib import Path
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from analyze_balance import analyze


class BalanceTests(unittest.TestCase):
    def configuration(self):
        return {'source_class':'engineering_fixture','elements':['Si','C'],'initial_counts':{'Si':1,'C':0},
                'area_angstrom2':2,'time_column':'time_ps','initial_time_ps':0,
                'observed_prefix':'count_','inserted_prefix':'inserted_','removed_prefix':'removed_',
                'counter_provenance':'Fabricated counters for arithmetic verification only.'}

    def test_exact_counter_balance_and_rate(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)
            source=root/'counters.csv'
            source.write_text('time_ps,count_Si,count_C,inserted_Si,inserted_C,removed_Si,removed_C\n0,1,0,0,0,0,0\n10,1,2,0,3,0,1\n',encoding='utf-8')
            report=analyze(source,self.configuration(),root/'analysis')
            self.assertEqual(report['status'],'COUNTER_BALANCE_MATCH')
            with (root/'analysis/balance.csv').open(encoding='utf-8',newline='') as stream:
                rows=list(csv.DictReader(stream))
            self.assertEqual(float(rows[-1]['interval_inserted_atoms_per_A2_ps']),0.15)
            self.assertEqual(float(rows[-1]['interval_removed_atoms_per_A2_ps']),0.05)

    def test_mismatch_is_reported_without_repairing_counts(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)
            source=root/'counters.csv'
            source.write_text('time_ps,count_Si,count_C,inserted_Si,inserted_C,removed_Si,removed_C\n10,1,3,0,3,0,1\n',encoding='utf-8')
            report=analyze(source,self.configuration(),root/'analysis')
            self.assertEqual(report['status'],'COUNTER_BALANCE_MISMATCH')
            self.assertEqual(report['mismatching_species_samples'],1)

    def test_missing_actual_counter_is_not_inferred(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)
            source=root/'snapshots-only.csv'
            source.write_text('time_ps,count_Si,count_C\n10,1,3\n',encoding='utf-8')
            with self.assertRaises(ValueError):
                analyze(source,self.configuration(),root/'analysis')
            self.assertFalse((root/'analysis').exists())
