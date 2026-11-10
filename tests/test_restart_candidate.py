from pathlib import Path
import sys
import tempfile
import unittest
import hashlib
import json
from jsonschema import Draft202012Validator

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from restart_candidate import inspect


class RestartCandidate(unittest.TestCase):
    def test_research_variants_require_reason_and_plan(self):
        from prepare_sweep import prepare_sweep
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            config = {'base_config_file': 'base.json', 'purpose': 'research_candidate',
                      'variants': [{'id': 'v', 'changes': {'timestep_ps': 0.001}}]}
            with self.assertRaisesRegex(ValueError, 'change reason'):
                prepare_sweep(config, root, root / 'output', 1)
            config['variants'][0]['reason'] = 'Proposed sensitivity check'
            (root / 'base.json').write_text(json.dumps({'purpose': 'research_candidate'}))
            with self.assertRaisesRegex(ValueError, 'base plan'):
                prepare_sweep(config, root, root / 'output', 1)
            self.assertFalse((root / 'output').exists())

    def test_malformed_checkpoint_is_diagnostic(self):
        with self.assertRaises(ValueError):
            inspect({'checkpoint': {'file': 123, 'sha256': 'x'}}, Path.cwd())

    def test_template_schema_rejects_authorization_promotion(self):
        root = Path(__file__).resolve().parents[1]
        validator = Draft202012Validator(json.loads((root / 'schemas/restart-candidate.schema.json').read_text()))
        record = json.loads((root / 'templates/restart-candidate.json').read_text())
        validator.validate(record)
        record['execution_authorized'] = True
        self.assertTrue(list(validator.iter_errors(record)))

    def test_complete_declarations_and_cross_engine_limit(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'restart').write_bytes(b'fixture')
            (root / 'evidence').write_text('Artificial evidence only')
            record = {'parent_attempt': 'parent', 'source_engine_id': 'cpu', 'target_engine_id': 'cpu',
                      'potential_sha256': 'declared', 'phase': 'deposition', 'counter_origin': 'parent-step-3',
                      'fix_state_evidence': 'evidence', 'compatibility_evidence': 'evidence',
                      'completed_step': 3, 'target_step': 12,
                      'checkpoint': {'file': 'restart', 'sha256': hashlib.sha256(b'fixture').hexdigest()}}
            self.assertEqual(inspect(record, root)['status'], 'DECLARATIONS_COMPLETE')
            self.assertFalse(inspect(record, root)['engine_state_verified'])
            record['target_engine_id'] = 'gpu'
            self.assertEqual(inspect(record, root)['status'], 'PREPARATION_INCOMPLETE')

    def test_unknowns_remain_incomplete(self):
        result = inspect({}, Path.cwd())
        self.assertEqual(result['status'], 'PREPARATION_INCOMPLETE')
        self.assertFalse(result['execution_authorized'])

    def test_wrong_checkpoint_and_steps_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp) / 'restart').write_bytes(b'fixture')
            report = inspect({'checkpoint': {'file': 'restart', 'sha256': 'wrong'},
                              'completed_step': 20, 'target_step': 10}, tmp)
            self.assertEqual(len(report['errors']), 2)


if __name__ == '__main__':
    unittest.main()
