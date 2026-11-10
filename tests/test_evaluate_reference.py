import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from evaluate_reference import evaluate_files, load_artifact


class EvaluationArtifacts(unittest.TestCase):
    def test_pseudo_atom_cli_keeps_sample_and_returns_partial(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            refs, preds = self.artifacts(directory)
            data = json.loads(refs.read_text())
            data['records'][0]['species_representation'] = 'pseudo_atoms'
            refs.write_text(json.dumps(data))
            output = directory / 'partial'
            child = subprocess.run([sys.executable, str(ROOT / 'tools/evaluate_reference.py'),
                '--references', str(refs), '--predictions', str(preds), '--metric', 'forces',
                '--output-directory', str(output)], capture_output=True, text=True)
            self.assertEqual(child.returncode, 1, child.stderr)
            report = json.loads((output / 'evaluation.json').read_text())
            self.assertEqual(report['coverage']['forces']['valid'], 0)
            self.assertEqual(report['total_reference_samples'], 1)
            self.assertIn('PSEUDO_ATOM_ADAPTER_UNSUPPORTED', (output / 'samples.csv').read_text())

    def artifacts(self, directory):
        record = {'id': 'artificial', 'species': ['Ga'], 'energy_eV': -1,
                  'energy_reference': 'fixture-zero', 'dft_group': 'fixture-only',
                  'forces_eV_per_angstrom': [[0, 0, 0]]}
        reference = {'schema_version': 1, 'record_type': 'reference_dataset',
                     'source_class': 'artificial_fixture', 'records': [record]}
        prediction = {'schema_version': 1, 'record_type': 'prediction_dataset',
                      'source_class': 'artificial_fixture', 'backend': {'kind': 'artificial_fixture', 'identity': 'no-engine'},
                      'records': [{**record, 'status': 'SUCCEEDED', 'energy_eV': -0.9,
                                   'forces_eV_per_angstrom': [[0.3, 0, 0]]}]}
        paths = directory / 'references.json', directory / 'predictions.json'
        for path, data in zip(paths, (reference, prediction)):
            path.write_text(json.dumps(data))
        return paths

    def test_cli_writes_native_values_and_preserves_existing_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            refs, preds = self.artifacts(directory)
            output = directory / 'results'
            command = [sys.executable, str(ROOT / 'tools/evaluate_reference.py'), '--references', str(refs),
                       '--predictions', str(preds), '--metric', 'energy', '--metric', 'forces', '--output-directory', str(output)]
            child = subprocess.run(command, capture_output=True, text=True, cwd=directory)
            self.assertEqual(child.returncode, 0, child.stderr)
            report = json.loads((output / 'evaluation.json').read_text())
            self.assertFalse(report['inference_performed'])
            self.assertEqual(report['source_class'], 'artificial_fixture')
            self.assertIn('artificial', (output / 'samples.csv').read_text())
            original = (output / 'evaluation.json').read_bytes()
            self.assertEqual(subprocess.run(command, capture_output=True).returncode, 2)
            self.assertEqual((output / 'evaluation.json').read_bytes(), original)

    def test_research_provenance_missing_or_changed_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            refs, _ = self.artifacts(directory)
            data = json.loads(refs.read_text())
            data['source_class'] = 'research_candidate'
            data['records'][0]['configuration_sha256'] = 'a' * 64
            refs.write_text(json.dumps(data))
            with self.assertRaisesRegex(ValueError, 'provenance'):
                load_artifact(refs, 'reference_dataset')
            (directory / 'source.txt').write_bytes(b'original')
            data['provenance'] = [{'path': 'source.txt', 'sha256': hashlib.sha256(b'original').hexdigest()}]
            refs.write_text(json.dumps(data))
            self.assertTrue(load_artifact(refs, 'reference_dataset')[1]['verified_provenance'])
            (directory / 'source.txt').write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError, 'identity mismatch'):
                load_artifact(refs, 'reference_dataset')

    def test_partial_prediction_produces_partial_artifacts(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            refs, preds = self.artifacts(directory)
            data = json.loads(preds.read_text())
            data['records'][0] = {'id': 'artificial', 'status': 'FAILED', 'reason': 'Synthetic backend error'}
            preds.write_text(json.dumps(data))
            report = evaluate_files(refs, preds, ['energy', 'forces'], directory / 'partial')
            self.assertEqual(report['status'], 'METRICS_PARTIAL')
            self.assertEqual(report['coverage']['energy']['valid'], 0)
            self.assertTrue((directory / 'partial/samples.csv').is_file())


if __name__ == '__main__':
    unittest.main()
