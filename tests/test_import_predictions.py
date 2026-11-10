import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import test_lammps_prediction

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from import_predictions import import_batch
from evaluate_reference import load_artifact


class BatchPredictionImport(unittest.TestCase):
    def manifest(self, directory):
        sample = test_lammps_prediction.StaticPredictions().fixture(directory)
        failed = copy.deepcopy(sample)
        failed['id'] = 'intentionally-missing-dump'
        failed['artifacts']['dump']['path'] = 'absent.dump'
        data = {'schema_version': 1, 'record_type': 'static_prediction_import',
                'source_class': 'artificial_fixture', 'backend': {'kind': 'artificial_fixture',
                'identity': 'Synthetic two-atom static output'}, 'samples': [sample, failed]}
        path = directory / 'manifest.json'
        path.write_text(json.dumps(data))
        return path

    def test_cli_partial_preserves_both_samples_and_evaluation_format(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            manifest = self.manifest(directory)
            output = directory / 'imported'
            child = subprocess.run([sys.executable, str(ROOT / 'tools/import_predictions.py'),
                '--manifest', str(manifest), '--output-directory', str(output)], capture_output=True, text=True)
            self.assertEqual(child.returncode, 1, child.stderr)
            self.assertEqual(json.loads(child.stdout)['failed_samples'], 1)
            dataset, observed = load_artifact(output / 'predictions.json', 'prediction_dataset')
            self.assertEqual([record['status'] for record in dataset['records']], ['SUCCEEDED', 'FAILED'])
            self.assertEqual(len(dataset['records']), 2)
            self.assertTrue(observed['verified_provenance'])
            self.assertIn('intentionally-missing-dump', (output / 'samples.csv').read_text())

    def test_duplicate_ids_are_input_error_not_dropped(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            path = self.manifest(directory)
            data = json.loads(path.read_text())
            data['samples'][1]['id'] = data['samples'][0]['id']
            path.write_text(json.dumps(data))
            with self.assertRaisesRegex(ValueError, 'unique'):
                import_batch(path, directory / 'output')
            self.assertFalse((directory / 'output').exists())


if __name__ == '__main__':
    unittest.main()
