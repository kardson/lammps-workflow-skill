import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from stage_links import check


class StageLinks(unittest.TestCase):
    def contract(self, directory):
        def write(name, data):
            path = directory / name
            path.write_text(json.dumps(data))
            return hashlib.sha256(path.read_bytes()).hexdigest()
        plan_hash = write('plan.json', {'schema_version': 1, 'record_type': 'md_plan', 'id': 'fixture'})
        profile_hash = write('profile.json', {'schema_version': 1, 'record_type': 'engine_profile', 'id': 'fixture-engine'})
        (directory / 'raw.txt').write_text('Synthetic engine evidence fixture; no engine executed')
        evidence_hash = write('evidence.json', {'schema_version': 1, 'records': [{
            'model_sha256': 'a' * 64, 'engine_id': 'fixture-engine', 'scenario': 'fixture-insertion',
            'dimension': 'deposition', 'status': 'PASSED', 'evidence': ['raw.txt']}]})
        return {'plan_binding': {'id': 'fixture', 'file': 'plan.json', 'sha256': plan_hash},
                'stages': [{'id': 'growth', 'engine_support': {'profile_file': 'profile.json',
                'profile_sha256': profile_hash, 'engine_id': 'fixture-engine', 'model_sha256': 'a' * 64,
                'evidence_file': 'evidence.json', 'evidence_sha256': evidence_hash, 'scenario': 'fixture-insertion',
                'required_dimensions': ['deposition']}}]}

    def test_exact_scope_matches_and_absent_scenario_stays_unknown(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            contract = self.contract(directory)
            result = check(contract, directory)
            self.assertEqual(result['status'], 'LINKS_MATCH_RECORDED_EVIDENCE')
            self.assertEqual(result['stages'][0]['recorded_evidence']['dimensions']['physical_accuracy']['status'], 'UNVERIFIED')
            contract['stages'][0]['engine_support']['required_dimensions'] = ['restart']
            self.assertEqual(check(contract, directory)['status'], 'PARTIAL')
            contract['stages'][0]['engine_support']['required_dimensions'] = ['deposition']
            contract['stages'][0]['engine_support']['scenario'] = 'different-scenario'
            self.assertEqual(check(contract, directory)['status'], 'PARTIAL')

    def test_changed_source_missing_evidence_and_recorded_failure_not_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            contract = self.contract(directory)
            (directory / 'raw.txt').unlink()
            self.assertEqual(check(contract, directory)['status'], 'PARTIAL')
            (directory / 'raw.txt').write_text('fixture restored')
            evidence = json.loads((directory / 'evidence.json').read_text())
            evidence['records'][0]['status'] = 'FAILED'
            (directory / 'evidence.json').write_text(json.dumps(evidence))
            contract['stages'][0]['engine_support']['evidence_sha256'] = hashlib.sha256((directory / 'evidence.json').read_bytes()).hexdigest()
            self.assertEqual(check(contract, directory)['status'], 'INCONSISTENT')
            (directory / 'plan.json').write_text('{}')
            self.assertTrue(any('identity mismatch' in text for text in check(contract, directory)['errors']))


if __name__ == '__main__':
    unittest.main()
