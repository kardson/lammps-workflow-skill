import copy
import json
from pathlib import Path
import unittest
import jsonschema


ROOT = Path(__file__).resolve().parents[1]


class ValidationCases(unittest.TestCase):
    def setUp(self):
        self.schema = json.loads((ROOT / 'schemas/validation-case.schema.json').read_text())
        self.case = json.loads((ROOT / 'validation/cases/local-receipt-fixture.json').read_text())

    def test_unbound_artificial_case_is_valid_but_not_permission(self):
        jsonschema.Draft202012Validator.check_schema(self.schema)
        jsonschema.validate(self.case, self.schema)
        self.assertIsNone(self.case['resources'])

    def test_missing_threshold_source_and_unknown_category_rejected(self):
        for change in ('source', 'category', 'identity'):
            case = copy.deepcopy(self.case)
            if change == 'source':
                del case['checks'][0]['source']
            elif change == 'category':
                case['category'] = 'all_authorized'
            else:
                case['inputs'] = [{'path': 'model', 'sha256': 'invalid'}]
            with self.subTest(change=change), self.assertRaises(jsonschema.ValidationError):
                jsonschema.validate(case, self.schema)


if __name__ == '__main__':
    unittest.main()
