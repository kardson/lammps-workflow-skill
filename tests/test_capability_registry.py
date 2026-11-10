import json
from pathlib import Path
import unittest
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from capability_registry import lookup


class CapabilityRegistry(unittest.TestCase):
    def test_lookup_resolves_contract_and_rejects_invented_tool(self):
        entries = lookup(category='analysis')
        self.assertTrue(entries)
        self.assertTrue(all(item['category'] == 'analysis' for item in entries))
        entry = lookup('analyze_trajectory')[0]
        self.assertEqual(entry['contract']['entrypoint'], entry['entrypoint'])
        with self.assertRaises(ValueError):
            lookup('automatic_potential_training')

    def test_tools_contracts_and_references_match(self):
        registry = json.loads((ROOT / 'capabilities.json').read_text())
        contracts = {e['entrypoint']: e for e in json.loads((ROOT / 'cli-contracts.json').read_text())['entries']}
        self.assertEqual({e['entrypoint'] for e in registry['entries']}, set(contracts))
        self.assertEqual(len({e['id'] for e in registry['entries']}), len(registry['entries']))
        for entry in registry['entries']:
            self.assertTrue((ROOT / entry['entrypoint']).is_file())
            self.assertTrue((ROOT / entry['limits_reference']).is_file())
            for key in ('inputs', 'outputs', 'side_effects'):
                self.assertEqual(entry[key], contracts[entry['entrypoint']][key])
            self.assertFalse(entry['runs_md'])
            self.assertFalse(entry['evaluates_potential'])
            self.assertFalse(entry['launches_remote'])
            self.assertTrue(entry['supported_scope'])
            self.assertIsInstance(entry['dependencies']['optional_imports'], list)


if __name__ == '__main__':
    unittest.main()
