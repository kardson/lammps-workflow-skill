"""Structural contracts for existing v1 records; no execution or inference."""
import copy
import json
import unittest
import sys
import tempfile
from pathlib import Path

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))


class RecordSchemas(unittest.TestCase):
    def load(self, name):
        schema = json.loads((ROOT / 'schemas' / (name + '.schema.json')).read_text())
        Draft202012Validator.check_schema(schema)
        record = json.loads((ROOT / 'templates' / (name + '.json')).read_text())
        return Draft202012Validator(schema), record

    def test_existing_drafts_and_versions(self):
        for name in ('plan', 'model-card', 'attempt'):
            with self.subTest(name=name):
                validator, record = self.load(name)
                validator.validate(record)
                record['schema_version'] = 99
                self.assertTrue(list(validator.iter_errors(record)))

    def test_invalid_duration_and_required_sections(self):
        validator, record = self.load('plan')
        record['simulation']['physical_duration'] = -1
        self.assertTrue(list(validator.iter_errors(record)))
        record = copy.deepcopy(record)
        del record['materials']
        self.assertTrue(list(validator.iter_errors(record)))

    def test_model_identity_and_training_boundary(self):
        validator, record = self.load('model-card')
        record['identity']['sha256'] = 'invalid'
        self.assertTrue(list(validator.iter_errors(record)))
        record['identity']['sha256'] = None
        record['training_in_scope'] = True
        self.assertTrue(list(validator.iter_errors(record)))

    def test_exit_code_is_not_string(self):
        validator, record = self.load('attempt')
        record['termination']['exit_code'] = '0'
        self.assertTrue(list(validator.iter_errors(record)))

    def test_status_and_nullable_text(self):
        for name in ('plan', 'model-card', 'attempt'):
            validator, record = self.load(name)
            record['status'] = 'MAGIC_SUCCESS'
            self.assertTrue(list(validator.iter_errors(record)))
        validator, record = self.load('plan')
        record['id'] = 123
        self.assertTrue(list(validator.iter_errors(record)))

    def test_manifest_cannot_claim_execution(self):
        schema = json.loads((ROOT / 'schemas/package-manifest.schema.json').read_text())
        Draft202012Validator.check_schema(schema)
        validator = Draft202012Validator(schema)
        record = {key: ({} if value.get('type') == 'object' else [] if value.get('type') == 'array' else 'fixture')
                  for key, value in schema['properties'].items()}
        for key, value in schema['properties'].items():
            if 'const' in value:
                record[key] = value['const']
            elif 'enum' in value:
                record[key] = value['enum'][0]
        validator.validate(record)
        record['simulation_run'] = True
        self.assertTrue(list(validator.iter_errors(record)))

    def test_actual_generated_manifest(self):
        from local_fixtures import package_fixture
        from prepare_input_package import prepare
        schema = json.loads((ROOT / 'schemas/package-manifest.schema.json').read_text())
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            record = prepare(package_fixture(root), root, root / 'package')
            Draft202012Validator(schema).validate(record)


if __name__ == '__main__':
    unittest.main()
