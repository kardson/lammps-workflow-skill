import json
from pathlib import Path
import sys
import tempfile
import unittest
import subprocess

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from inspect_input import inspect_input


class InputContracts(unittest.TestCase):
    def test_dynamic_and_cli_mismatch(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'input').write_text('pair_style ${style}\n')
            (root / 'plan').write_text(json.dumps({'input_contract': {'pair_style': [['nep']]}}))
            report = inspect_input(root / 'input', root / 'plan')
            self.assertEqual(report['command_contract_checks']['pair_style']['verdict'], 'UNVERIFIED')
            (root / 'input').write_text('pair_style wrong\n')
            tool = Path(__file__).resolve().parents[1] / 'tools/inspect_input.py'
            result = subprocess.run([sys.executable, str(tool), '--input', str(root / 'input'),
                '--plan', str(root / 'plan'), '--output', str(root / 'report.json')],
                capture_output=True, text=True)
            self.assertEqual(result.returncode, 1)
            self.assertEqual(json.loads((root / 'report.json').read_text())['command_contract_checks']['pair_style']['verdict'], 'MISMATCH')

    def test_include_budget_and_outside_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'main').write_text('include settings\n' * 65)
            (root / 'settings').write_text('units metal\n')
            with self.assertRaisesRegex(ValueError, 'budget exceeded'):
                inspect_input(root / 'main', include_root=root)
            (root / 'main').write_text('include ../outside\n')
            (root.parent / 'outside').exists()  # No outside file is created.
            with self.assertRaises((ValueError, FileNotFoundError)):
                inspect_input(root / 'main', include_root=root)

    def test_literal_include_is_bounded_and_cycles_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'main').write_text('include settings\n')
            (root / 'settings').write_text('pair_style nep\n')
            (root / 'plan').write_text(json.dumps({'input_contract': {'pair_style': [['nep']]}}))
            report = inspect_input(root / 'main', root / 'plan', root)
            self.assertEqual(report['command_contract_checks']['pair_style']['verdict'], 'MATCH')
            self.assertEqual(len(report['literal_include_sources']), 2)
            (root / 'settings').write_text('include main\n')
            with self.assertRaises(ValueError):
                inspect_input(root / 'main', root / 'plan', root)

    def test_actual_fix_and_pair_tokens_checked_without_execution(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'input').write_text('pair_style nep\nfix integrate mobile nve\n')
            (root / 'plan').write_text(json.dumps({'input_contract': {
                'pair_style': [['nep']], 'fix': [['integrate', 'all', 'nve']]}}))
            report = inspect_input(root / 'input', root / 'plan')
            self.assertEqual(report['command_contract_checks']['pair_style']['verdict'], 'MATCH')
            self.assertEqual(report['command_contract_checks']['fix']['verdict'], 'MISMATCH')
            self.assertFalse(report['engine_started'])
            (root / 'input').write_text('include other.in\npair_style nep\n')
            self.assertEqual(inspect_input(root / 'input', root / 'plan')['command_contract_checks']['pair_style']['verdict'], 'UNVERIFIED')


if __name__ == '__main__':
    unittest.main()
