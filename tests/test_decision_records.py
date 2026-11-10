from pathlib import Path
import sys
import unittest
import json
from jsonschema import Draft202012Validator

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from decision_records import stage_blockers


class DecisionRecords(unittest.TestCase):
    def test_valid_repaired_issue_retains_evidence(self):
        root = Path(__file__).resolve().parents[1]
        validator = Draft202012Validator(json.loads((root / 'schemas/decision-log.schema.json').read_text()))
        record = {'schema_version': 1, 'record_type': 'decision_log', 'plan': None,
                  'entries': [{'id': 'issue', 'kind': 'ISSUE', 'summary': 'fixture',
                     'status': 'RESOLVED', 'source': 'original-failure.json', 'related_fields': [],
                     'blocks': ['launch'], 'release_condition': 'Repair and verify',
                     'resolution': 'Repaired', 'evidence': ['regression.json'],
                     'selected_fix': 'Fixture fix', 'verification': 'Fixture regression',
                     'regression_scope': 'Fixture only'}]}
        validator.validate(record)
        self.assertEqual(stage_blockers(record, 'launch'), [])
        record['entries'][0]['evidence'] = []
        self.assertTrue(list(validator.iter_errors(record)))

    def test_blocking_question_requires_release_condition(self):
        root = Path(__file__).resolve().parents[1]
        validator = Draft202012Validator(json.loads((root / 'schemas/decision-log.schema.json').read_text()))
        record = {'schema_version': 1, 'record_type': 'decision_log', 'plan': None,
                  'entries': [{'id': 'q', 'kind': 'QUESTION', 'summary': 'Unknown',
                     'status': 'OPEN', 'source': 'user', 'related_fields': [],
                     'blocks': ['research_input'], 'release_condition': None}]}
        self.assertTrue(list(validator.iter_errors(record)))

    def test_repaired_issue_requires_verification(self):
        root = Path(__file__).resolve().parents[1]
        schema = json.loads((root / 'schemas/decision-log.schema.json').read_text())
        record = {'schema_version': 1, 'record_type': 'decision_log', 'plan': None,
                  'entries': [{'id': 'issue', 'kind': 'ISSUE', 'summary': 'fixture',
                     'status': 'RESOLVED', 'source': 'fixture', 'related_fields': [],
                     'blocks': [], 'release_condition': None, 'resolution': 'fixed', 'evidence': []}]}
        self.assertTrue(list(Draft202012Validator(schema).iter_errors(record)))

    def test_malformed_entry_is_not_silently_ready(self):
        with self.assertRaises(ValueError):
            stage_blockers({'entries': [None]}, 'launch')

    def test_missing_orientation_only_blocks_declared_stages(self):
        record = {'entries': [{'id': 'orientation', 'kind': 'QUESTION', 'status': 'OPEN',
                   'summary': 'Orientation unresolved', 'blocks': ['research_structure'],
                   'release_condition': 'Record the scientific choice and its source'}]}
        self.assertEqual(len(stage_blockers(record, 'research_structure')), 1)
        self.assertEqual(stage_blockers(record, 'environment'), [])
        self.assertEqual(stage_blockers(record, 'analysis'), [])
        record['entries'][0]['status'] = 'RESOLVED'
        self.assertEqual(stage_blockers(record, 'research_structure'), [])


if __name__ == '__main__':
    unittest.main()
