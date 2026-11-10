import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import test_block_statistics

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from summarize_time_series import summarize


class TimeSeriesSummary(unittest.TestCase):
    def config(self):
        return {**test_block_statistics.TimeBlockStatistics().config(), 'time_column': 'time_ps',
                'metric_column': 'roughness', 'unit': 'angstrom', 'run_id': 'artificial-run',
                'seeds': {'velocity': None}, 'seed_basis': 'Artificial metadata; seed intentionally unknown',
                'source_class': 'engineering_fixture'}

    def test_cli_descriptive_with_native_blocks_and_seed_gap(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            source = directory / 'series.csv'
            source.write_text('time_ps,roughness\n' + ''.join(f'{index},{index // 2}\n' for index in range(8)))
            config = directory / 'config.json'
            config.write_text(json.dumps(self.config()))
            child = subprocess.run([sys.executable,str(ROOT/'tools/summarize_time_series.py'),'--csv',str(source),
                '--config',str(config),'--output-directory',str(directory/'output')],capture_output=True,text=True)
            self.assertEqual(child.returncode,1,child.stderr)
            report = json.loads((directory/'output/time-summary.json').read_text())
            self.assertEqual(report['status'],'DESCRIPTIVE_ONLY')
            self.assertEqual(report['seed_metadata_unresolved'],['velocity'])
            self.assertIsNone(report['statistics']['confidence_lower'])
            self.assertTrue((directory/'output/blocks.csv').is_file())

    def test_bad_value_keeps_failed_partial_artifacts(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            source = directory / 'series.csv'
            source.write_text('time_ps,roughness\n0,1\n1,1\n2,2\n3,nan\n')
            report = summarize(source,self.config(),directory/'output')
            self.assertEqual(report['status'],'FAILED')
            self.assertIsNone(report['statistics'])
            self.assertTrue((directory/'output/blocks.csv').is_file())


if __name__ == '__main__':
    unittest.main()
