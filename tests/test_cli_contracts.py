"""Detect argument inventory drift without invoking tools or engines."""
import ast
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class CLIContracts(unittest.TestCase):
    def test_inventory_matches_actual_argparse_declarations(self):
        observed = {}
        for path in sorted((ROOT / 'tools').glob('*.py')):
            arguments = []
            for node in ast.walk(ast.parse(path.read_text(encoding='utf-8-sig'))):
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == 'add_argument':
                    arguments.append({'names': [value.value for value in node.args
                        if isinstance(value, ast.Constant) and isinstance(value.value, str)],
                        'required': any(value.arg == 'required' and isinstance(value.value, ast.Constant)
                                        and value.value.value is True for value in node.keywords)})
            if arguments:
                observed['tools/' + path.name] = arguments
        inventory = json.loads((ROOT / 'cli-contracts.json').read_text())
        declared = {entry['entrypoint']: entry['arguments'] for entry in inventory['entries']}
        self.assertEqual(observed, declared)


if __name__ == '__main__':
    unittest.main()
