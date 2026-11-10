import csv
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import analyze_balance
from analyze_balance import analyze


class BalanceTests(unittest.TestCase):
    def test_changed_counter_source_not_committed_as_final_result(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)
            source=root/'source.csv'
            header='time_ps,count_Si,count_C,inserted_Si,inserted_C,removed_Si,removed_C\n'
            source.write_text(header+'10,1,1,0,1,0,0\n',encoding='utf-8')
            original_identity=analyze_balance.identity
            calls=[]
            def observed_then_changed(path):
                observed=original_identity(path)
                if not calls:
                    source.write_text(header+'10,1,2,0,2,0,0\n',encoding='utf-8')
                calls.append(path)
                return observed
            with patch.object(analyze_balance,'identity',side_effect=observed_then_changed):
                with self.assertRaisesRegex(ValueError,'source changed'):
                    analyze(source,self.configuration(),root/'analysis')
            self.assertFalse((root/'analysis').exists())

    def test_many_samples_stream_to_complete_native_csv(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)
            source=root/'many.csv'
            with source.open('w',encoding='utf-8') as stream:
                stream.write('time_ps,count_Si,count_C,inserted_Si,inserted_C,removed_Si,removed_C\n')
                for index in range(5000):
                    stream.write(f'{index},1,{index},0,{index},0,0\n')
            report=analyze(source,self.configuration(),root/'analysis')
            self.assertEqual(report['species_samples'],10000)
            self.assertEqual(report['mismatching_species_samples'],0)
            with (root/'analysis/balance.csv').open(encoding='utf-8',newline='') as stream:
                self.assertEqual(sum(1 for _ in csv.DictReader(stream)),10000)

    def test_explicit_restart_origins_preserve_global_counter_identity(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)
            source=root/'restart.csv'
            source.write_text('time_ps,count_Si,count_C,inserted_Si,inserted_C,removed_Si,removed_C\n10,1,2,5,5,1,2\n',encoding='utf-8')
            config=self.configuration()
            config['counter_origins']={'inserted':{'Si':5,'C':2},'removed':{'Si':1,'C':1},
                                       'source':'Artificial explicit parent counter snapshot'}
            report=analyze(source,config,root/'analysis')
            self.assertEqual(report['status'],'COUNTER_BALANCE_MATCH')
            with (root/'analysis/balance.csv').open(encoding='utf-8',newline='') as stream:
                rows=list(csv.DictReader(stream))
            self.assertEqual(int(rows[-1]['inserted_since_origin']),3)
            self.assertEqual(int(rows[-1]['removed_since_origin']),1)
            self.assertAlmostEqual(float(rows[-1]['interval_inserted_atoms_per_A2_ps']),0.15)

    def test_reset_counter_or_time_requires_explicit_reconciliation(self):
        header='time_ps,count_Si,count_C,inserted_Si,inserted_C,removed_Si,removed_C\n'
        for rows in ('10,1,3,0,3,0,0\n20,1,1,0,1,0,0\n',
                     '10,1,3,0,3,0,0\n0,1,4,0,4,0,0\n'):
            with tempfile.TemporaryDirectory() as temporary:
                root=Path(temporary)
                source=root/'reset.csv'
                source.write_text(header+rows,encoding='utf-8')
                with self.assertRaisesRegex(ValueError,'reset|timeline'):
                    analyze(source,self.configuration(),root/'analysis')
                self.assertFalse((root/'analysis').exists())

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
