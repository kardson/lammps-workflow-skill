from pathlib import Path
import sys
import unittest
import json
from jsonschema import Draft202012Validator

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from potential_registry import search, load_index


class PotentialRegistry(unittest.TestCase):
    def test_load_actual_fixture_and_reject_malformed_context(self):
        root = Path(__file__).resolve().parents[1]
        record = load_index(root / 'tests/potential-index-fixture.json')
        self.assertEqual(len(search(record['entries'])), 2)
        with self.assertRaises(ValueError):
            search([{'id': 'bad', 'metrics': { }, 'metric_context': []}],
                   maximum_energy_mae=1, dataset='d', scenario='s')

    def test_explicit_fixture_schema_and_negative_metric(self):
        root = Path(__file__).resolve().parents[1]
        validator = Draft202012Validator(json.loads((root / 'schemas/potential-index.schema.json').read_text()))
        record = json.loads((root / 'tests/potential-index-fixture.json').read_text())
        validator.validate(record)
        record['entries'][0]['metrics']['energy_mae_ev_per_atom'] = -1
        self.assertTrue(list(validator.iter_errors(record)))

    def test_empirical_and_pretrained_share_discovery(self):
        entries = [{'id': 'empirical', 'kind': 'empirical', 'elements': ['Si']},
                   {'id': 'pretrained', 'kind': 'pretrained_ml', 'elements': ['Si', 'C']}]
        self.assertEqual(len(search(entries, ['Si'])), 2)
        self.assertEqual(search(entries, ['C'])[0]['id'], 'pretrained')

    def test_unknown_accuracy_is_not_qualified(self):
        entries = [{'id': 'unknown'}, {'id': 'known', 'metrics': {'energy_mae_ev_per_atom': 0.02},
                   'metric_context': {'dataset': 'fixture', 'scenario': 'bulk', 'evidence': 'fixture.json'}}]
        self.assertEqual([x['id'] for x in search(entries, maximum_energy_mae=0.03, dataset='fixture', scenario='bulk')], ['known'])
        self.assertEqual(search(entries, maximum_energy_mae=0.01, dataset='fixture', scenario='bulk'), [])
        self.assertEqual(search(entries, maximum_energy_mae=0.03, dataset='fixture', scenario='surface'), [])
        with self.assertRaises(ValueError):
            search(entries, maximum_energy_mae=0.03)

    def test_duplicate_ids_and_negative_metric_are_rejected(self):
        with self.assertRaises(ValueError):
            search([{'id': 'duplicate'}, {'id': 'duplicate'}])
        with self.assertRaises(ValueError):
            search([{'id': 'bad', 'metrics': {'energy_mae_ev_per_atom': -1},
                     'metric_context': {'dataset': 'd', 'scenario': 's', 'evidence': 'e'}}],
                   maximum_energy_mae=1, dataset='d', scenario='s')


if __name__ == '__main__':
    unittest.main()
