import hashlib
from pathlib import Path
import sys
import tempfile
import unittest
import json

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from validate_case import validate_links


class RecordLinks(unittest.TestCase):
    def test_matching_compatibility_evidence_remains_bounded(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'raw.log').write_text('Artificial evidence; no numerical validation claim.')
            evidence = {'executable': 'engine', 'interface_revision': 'rev', 'precision': 'double',
                        'potential_sha256': 'hash', 'scenario': 'static', 'status': 'PASSED',
                        'raw_evidence': ['raw.log']}
            (root / 'evidence.json').write_text(json.dumps(evidence))
            result = validate_links({'record_type': 'execution_attempt', 'executable': 'engine',
                'interface_revision': 'rev', 'precision': 'double',
                'potential_identity': {'sha256': 'hash'}, 'validation_scenario': 'static',
                'compatibility_evidence': 'evidence.json'}, root)
            self.assertEqual(result['errors'], [])
            self.assertEqual(result['status'], 'PARTIAL')

    def test_malformed_hash_and_mapping_are_diagnostics(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'model').write_bytes(b'fixture')
            result = validate_links({'record_type': 'potential_model_card',
                'identity': {'file': 'model', 'sha256': 123},
                'elements': ['Si'], 'type_to_element': [{}]}, root)
            self.assertEqual(len(result['errors']), 2)

    def test_wrong_scenario_evidence_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            evidence = {'executable': 'engine', 'interface_revision': 'rev', 'precision': 'double',
                        'potential_sha256': 'hash', 'scenario': 'static', 'status': 'PASSED',
                        'raw_evidence': ['missing.log']}
            (root / 'evidence.json').write_text(json.dumps(evidence))
            result = validate_links({'record_type': 'execution_attempt', 'executable': 'engine',
                'interface_revision': 'rev', 'precision': 'double',
                'potential_identity': {'sha256': 'hash'}, 'validation_scenario': 'deposition_restart',
                'compatibility_evidence': 'evidence.json'}, root)
            self.assertIn('Compatibility evidence scenario mismatch', result['errors'])
            self.assertIn('Missing raw compatibility evidence: missing.log', result['errors'])

    def test_plan_input_declaration_mismatch(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data = json.dumps({'record_type': 'md_plan', 'id': 'p', 'schema_version': 1,
                               'simulation': {'units': 'metal'}}).encode()
            (root / 'plan.json').write_bytes(data)
            result = validate_links({'record_type': 'execution_attempt',
                'plan_binding': {'file': 'plan.json', 'id': 'p', 'schema_version': 1,
                                 'sha256': hashlib.sha256(data).hexdigest()},
                'input_declarations': {'units': 'real'}}, root)
            self.assertIn('Plan/input declaration mismatch: units', result['errors'])

    def test_attempt_model_and_restart_mismatches(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'model.json').write_text(json.dumps({
                'record_type': 'potential_model_card', 'identity': {'sha256': 'a', 'bytes': 3},
                'interface': {'revision': 'r1', 'precision': 'double'}}))
            record = {'record_type': 'execution_attempt', 'model_card': 'model.json',
                      'potential_identity': {'sha256': 'b', 'bytes': 4},
                      'interface_revision': 'r2', 'precision': 'single',
                      'parent_attempt': 'previous', 'parent_restart_identity': {'file': 'missing.restart'}}
            result = validate_links(record, root)
            self.assertEqual(len(result['errors']), 5)
            self.assertTrue(result['unknown'])

    def test_plan_binding_detects_wrong_version_and_id(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            data = json.dumps({'record_type': 'md_plan', 'id': 'actual', 'schema_version': 1}).encode()
            (root / 'plan.json').write_bytes(data)
            record = {'record_type': 'execution_attempt', 'plan_binding': {
                'file': 'plan.json', 'id': 'wrong', 'schema_version': 2,
                'sha256': hashlib.sha256(data).hexdigest()}}
            result = validate_links(record, root)
            self.assertIn('Plan binding mismatch: id', result['errors'])
            self.assertIn('Plan binding mismatch: schema_version', result['errors'])

    def test_model_changed_identity_and_mapping(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'model').write_bytes(b'fixture')
            record = {'record_type': 'potential_model_card', 'elements': ['Si'],
                      'type_to_element': ['Si'], 'identity': {'file': 'model', 'bytes': 7,
                      'sha256': hashlib.sha256(b'fixture').hexdigest()}}
            self.assertEqual(validate_links(record, root)['status'], 'CHECKED')
            (root / 'model').write_bytes(b'changed')
            record['type_to_element'] = ['Cd']
            self.assertEqual(len(validate_links(record, root)['errors']), 2)

    def test_inventory_and_path_escape(self):
        with tempfile.TemporaryDirectory() as tmp:
            record = {'package_files': ['a'], 'file_identities': [{'package_file': '../outside'}]}
            self.assertEqual(len(validate_links(record, Path(tmp))['errors']), 2)

    def test_missing_reference_and_unresolved_semantics(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = validate_links({'record_type': 'execution_attempt', 'plan': 'missing.json'}, Path(tmp))
            self.assertEqual(result['status'], 'INCONSISTENT')
            self.assertTrue(result['unknown'])


if __name__ == '__main__':
    unittest.main()
