import csv
from contextlib import closing
import json
from pathlib import Path
import sqlite3
import sys
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from deposition_events import EVENTS, analyze


class EventLedger(unittest.TestCase):
    def test_duplicate_event_rolls_back_and_cli_reports_partial(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            source = self.source(directory, [(0,'ATTEMPT','a1',''),(1,'INSERTED','a1',10),(2,'REFLECTED','a1',10)])
            with source.open('a',encoding='utf-8') as stream:
                stream.write('e2,3,REFLECTED,a1,10,Cd,Synthetic duplicate event\n')
            report = analyze(source, self.config(), directory / 'failed')
            self.assertEqual(report['status'], 'FAILED')
            self.assertEqual(report['events_processed'], 3)
            self.assertEqual(report['elements']['Cd']['reflection_events'], 1)
            config = directory / 'config.json'
            config.write_text(json.dumps(self.config()))
            child = subprocess.run([sys.executable,str(ROOT/'tools/analyze_events.py'),'--csv',str(source),
                '--config',str(config),'--output-directory',str(directory/'cli-failed')],capture_output=True,text=True)
            self.assertEqual(child.returncode,1,child.stderr)
            self.assertEqual(json.loads(child.stdout)['status'],'FAILED')
            self.assertTrue((directory/'cli-failed/events.json').is_file())

    def config(self):
        return {'source_class': 'engineering_fixture', 'scope_id': 'synthetic-cohort', 'elements': ['Cd'],
                'start_time_ps': 0, 'observation_time_ps': 10, 'counter_provenance': 'Artificial event fixture only',
                'cohort_definition': 'Artificial incident cohort; retained selection defined by supplied fixture events',
                'event_definitions': {event: 'Artificial ' + event + ' classification, not physics evidence' for event in EVENTS}}

    def source(self, directory, rows):
        path = directory / 'events.csv'
        with path.open('w', encoding='utf-8', newline='') as stream:
            writer = csv.writer(stream)
            writer.writerow(['event_id', 'time_ps', 'event', 'attempt_id', 'atom_id', 'element', 'source'])
            for index, (time, event, attempt, atom) in enumerate(rows):
                writer.writerow(['e' + str(index), time, event, attempt, atom, 'Cd', 'Synthetic row source'])
        return path

    def test_reflection_history_is_not_an_exclusive_fate(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            source = self.source(directory, [(0,'ATTEMPT','a1',''),(0,'ATTEMPT','a2',''),
                (1,'REJECTED','a1',''),(1,'INSERTED','a2',10),(2,'REFLECTED','a2',10),(3,'ESCAPED','a2',10),
                (4,'ATTEMPT','a3',''),(4,'INSERTED','a3',11),(10,'COHORT_RETAINED','a3',11)])
            original = source.read_bytes()
            report = analyze(source, self.config(), directory / 'output')
            values = report['elements']['Cd']
            self.assertEqual(report['status'], 'DECLARED_EVENT_LEDGER_SUMMARY')
            self.assertEqual(values['attempts'], 3)
            self.assertEqual(values['successfully_inserted'], 2)
            self.assertEqual(values['reflection_events'], 1)
            self.assertEqual(values['escaped'], 1)
            self.assertEqual(values['retained_at_observation'], 1)
            self.assertEqual(values['retained_per_successful_insertion'], 0.5)
            self.assertEqual(source.read_bytes(), original)
            with closing(sqlite3.connect(directory / 'output/events.sqlite')) as connection:
                self.assertEqual(connection.execute('SELECT count(*) FROM events').fetchone()[0], 9)

    def test_missing_outcomes_stay_unknown_and_ratio_is_not_zero(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            source = self.source(directory, [(0,'ATTEMPT','a1',''),(1,'INSERTED','a1',10),(2,'ATTEMPT','pending','')])
            report = analyze(source, self.config(), directory / 'output')
            self.assertEqual(report['status'], 'EVENT_LEDGER_PARTIAL')
            self.assertEqual(report['elements']['Cd']['unclassified_inserted'], 1)
            self.assertEqual(report['elements']['Cd']['pending_attempts'], 1)
            self.assertIsNone(report['elements']['Cd']['retained_per_successful_insertion'])

    def test_reused_atom_id_fails_without_committing_the_bad_event(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            source = self.source(directory, [(0,'ATTEMPT','a1',''),(1,'INSERTED','a1',10),
                (2,'ATTEMPT','a2',''),(3,'INSERTED','a2',10)])
            report = analyze(source, self.config(), directory / 'output')
            self.assertEqual(report['status'], 'FAILED')
            self.assertEqual(report['events_processed'], 3)
            self.assertEqual(report['elements']['Cd']['successfully_inserted'], 1)
            self.assertEqual(report['elements']['Cd']['pending_attempts'], 1)

    def test_unknown_removal_is_not_normal_escape(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            source = self.source(directory, [(0,'ATTEMPT','a1',''),(1,'INSERTED','a1',10),(2,'REMOVED_UNKNOWN','a1',10)])
            report = analyze(source, self.config(), directory / 'output')
            self.assertEqual(report['status'], 'EVENT_LEDGER_PARTIAL')
            self.assertEqual(report['elements']['Cd']['escaped'], 0)
            self.assertEqual(report['elements']['Cd']['removed_unknown'], 1)


if __name__ == '__main__':
    unittest.main()
