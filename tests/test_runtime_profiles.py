from pathlib import Path
import sys
import unittest
import json
from jsonschema import Draft202012Validator

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from runtime_profiles import check_bindings


class RuntimeProfiles(unittest.TestCase):
    def test_templates_validate_without_claiming_ready(self):
        root = Path(__file__).resolve().parents[1]
        for name in ('engine-profile', 'site-binding'):
            validator = Draft202012Validator(json.loads((root / 'schemas' / (name + '.schema.json')).read_text()))
            record = json.loads((root / 'templates' / (name + '.json')).read_text())
            validator.validate(record)
            record['schema_version'] = 9
            self.assertTrue(list(validator.iter_errors(record)))

    def test_binding_match_is_not_live_readiness(self):
        report = check_bindings([{'id': 'cpu'}], {'engine_bindings': [
            {'engine_id': 'cpu', 'executable': '/not/locally/installed/lmp'}]})
        self.assertEqual(report['status'], 'DECLARATIONS_MATCH')
        self.assertEqual(report['live_readiness'], 'UNVERIFIED')

    def test_unknown_and_duplicate_bindings_rejected(self):
        report = check_bindings([{'id': 'cpu'}], {'engine_bindings': [
            {'engine_id': 'missing', 'executable': ''}, {'engine_id': 'missing', 'executable': 'lmp'}]})
        self.assertEqual(report['status'], 'INVALID')
        self.assertEqual(len(report['errors']), 4)


if __name__ == '__main__':
    unittest.main()
