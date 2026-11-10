from pathlib import Path
import sys
import unittest
import tempfile
import json
import subprocess

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from compatibility_registry import query, load_evidence


class CompatibilityRegistry(unittest.TestCase):
    def test_cli_failure_and_malformed_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'raw').write_text('fixture')
            path = root / 'evidence.json'
            command = [sys.executable, str(Path(__file__).resolve().parents[1] / 'tools/validate_compatibility.py'),
                '--evidence', str(path), '--model-sha256', 'm', '--engine-id', 'e', '--scenario', 's']
            path.write_text(json.dumps({'schema_version': 1, 'records': [
                {'model_sha256': 'm', 'engine_id': 'e', 'scenario': 's', 'dimension': 'restart',
                 'status': 'FAILED', 'evidence': ['raw']}]}))
            result = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(result.returncode, 1)
            self.assertEqual(json.loads(result.stdout)['dimensions']['restart']['status'], 'FAILED')
            path.write_text('[]')
            result = subprocess.run(command, capture_output=True, text=True)
            self.assertEqual(result.returncode, 2)
            self.assertEqual(json.loads(result.stdout)['status'], 'ERROR')

    def test_positive_source_and_cli_query(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'raw.json').write_text('{}')
            path = root / 'evidence.json'
            path.write_text(json.dumps({'schema_version': 1, 'records': [
                {'model_sha256': 'm', 'engine_id': 'e', 'scenario': 's', 'dimension': 'numerical',
                 'status': 'PASSED', 'evidence': ['raw.json']}]}))
            result = subprocess.run([sys.executable, str(Path(__file__).resolve().parents[1] / 'tools/validate_compatibility.py'),
                '--evidence', str(path), '--model-sha256', 'm', '--engine-id', 'e', '--scenario', 's'],
                cwd=tmp, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0)
            report = json.loads(result.stdout)
            self.assertEqual(report['dimensions']['numerical']['status'], 'PASSED_RECORDED')
            self.assertEqual(report['dimensions']['physical_accuracy']['status'], 'UNVERIFIED')

    def test_missing_raw_evidence_is_unverified(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'evidence.json'
            path.write_text(json.dumps({'schema_version': 1, 'records': [
                {'model_sha256': 'm', 'engine_id': 'e', 'scenario': 's', 'dimension': 'numerical',
                 'status': 'PASSED', 'evidence': ['missing.log']}]}))
            self.assertEqual(load_evidence(path)[0]['status'], 'UNVERIFIED')

    def test_exact_identity_and_scenario_do_not_generalize(self):
        records = [{'model_sha256': 'model', 'engine_id': 'cpu', 'scenario': 'small_static',
                    'dimension': 'numerical', 'status': 'PASSED'}]
        self.assertEqual(query(records, 'model', 'cpu', 'small_static')['dimensions']['numerical']['status'], 'PASSED_RECORDED')
        self.assertEqual(query(records, 'model', 'gpu', 'small_static')['dimensions']['numerical']['status'], 'UNVERIFIED')
        self.assertEqual(query(records, 'model', 'cpu', 'growth')['dimensions']['physical_accuracy']['status'], 'UNVERIFIED')

    def test_failure_is_not_hidden_by_success(self):
        records = [{'model_sha256': 'm', 'engine_id': 'e', 'scenario': 's',
                    'dimension': 'restart', 'status': value} for value in ('PASSED', 'FAILED')]
        self.assertEqual(query(records, 'm', 'e', 's')['dimensions']['restart']['status'], 'CONFLICTING')


if __name__ == '__main__':
    unittest.main()
