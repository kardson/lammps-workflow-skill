"""Local input/log edge cases; fixtures are fabricated and never executed."""
import json
from pathlib import Path
import sys
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from inspect_input import index_commands, inspect_input
from parse_log import parse_log


class LocalInspectionTests(unittest.TestCase):
    def test_literal_contract_and_mismatch_remain_unapproved(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / 'in.fixture'
            source.write_text('units metal\natom_style atomic\nboundary p p f\ntimestep 0.001\n', encoding='utf-8')
            plan = root / 'plan.json'
            plan.write_text(json.dumps({'status': 'DRAFT', 'confirmation': None, 'simulation':
                                        {'units': 'metal', 'atom_style': 'atomic', 'boundary': ['p', 'p', 'p'], 'timestep': 0.001}}), encoding='utf-8')
            before = source.read_bytes()
            result = inspect_input(source, plan)
            self.assertEqual(result['plan_checks']['units']['verdict'], 'MATCH')
            self.assertEqual(result['plan_checks']['boundary']['verdict'], 'MISMATCH')
            self.assertFalse(result['execution_authorized'])
            self.assertFalse(result['preparation_audit_complete'])
            self.assertFalse(result['plan']['confirmation_present'])
            self.assertEqual(source.read_bytes(), before)

    def test_control_flow_and_command_variables_are_not_executed(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            marker = root / 'MUST_NOT_EXIST'
            source = root / 'in.fixture'
            source.write_text('units metal\ninclude missing.inc\nshell echo unsafe > ' + str(marker) + '\n${command} 123\n', encoding='utf-8')
            plan = root / 'plan.json'
            plan.write_text('{"simulation":{"units":"metal"}}', encoding='utf-8')
            result = inspect_input(source, plan)
            self.assertEqual(result['coverage'], 'PARTIAL')
            self.assertEqual(result['plan_checks']['units']['verdict'], 'UNVERIFIED')
            self.assertEqual(len(result['control_flow_not_evaluated']), 3)
            self.assertFalse(marker.exists())

    def test_continuation_comments_and_quoted_hash(self):
        commands, issues = index_commands('fix src all deposit 1 1 &\n 10 12345 region beam\nprint "keep # inside"\n')
        self.assertFalse(issues)
        self.assertEqual(commands[0]['args'], ['src', 'all', 'deposit', '1', '1', '10', '12345', 'region', 'beam'])
        self.assertEqual(commands[1]['args'], ['keep # inside'])
        _, issues = index_commands('units metal & # comment prevents continuation\n')
        self.assertTrue(issues)
        commands, _ = index_commands('# entire continued comment &\nunits real\nunits metal\n')
        self.assertEqual(len(commands), 1)
        self.assertEqual(commands[0]['args'], ['metal'])

    def test_triple_quote_and_unfinished_input_are_partial(self):
        commands, issues = index_commands('units metal\npython source here """\nunits real\n"""\n')
        self.assertEqual(len(commands), 1)
        self.assertTrue(issues)
        _, issues = index_commands('units &\n')
        self.assertTrue(issues)

    def parse_fixture(self, text):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'synthetic.log'
            path.write_text(text, encoding='utf-8')
            before = path.read_bytes()
            result = parse_log(path)
            self.assertEqual(before, path.read_bytes())
            return result

    def test_multiple_blocks_keep_reset_steps_and_columns(self):
        result = self.parse_fixture('Step Temp PotEng\n0 300 -10\n10 301 -9\nLoop time of 1 on 1 procs for 10 steps with 4 atoms\nStep Atoms Temp\n0 4 302\n5 6 303\n')
        self.assertEqual(len(result['thermo_blocks']), 2)
        first, second = result['thermo_blocks']
        self.assertEqual(first['row_count'], 2)
        self.assertEqual(first['last']['values']['Step'], 10)
        self.assertEqual(second['first']['values']['Step'], 0)
        self.assertEqual(second['max']['Atoms'], 6)
        self.assertEqual(result['job_state'], 'UNVERIFIED')
        self.assertEqual(result['scientific_acceptance'], 'UNVERIFIED')
        self.assertIsNone(second['following_loop_line'])

    def test_warning_does_not_split_thermo_and_error_after_loop_is_retained(self):
        result = self.parse_fixture('Step Temp\n0 300\nWARNING: synthetic warning\n1 301\nLoop time of 1 on 1 procs for 1 steps with 4 atoms\nERROR: synthetic later failure\n')
        self.assertEqual(result['warning_count'], 1)
        self.assertEqual(result['error_count'], 1)
        self.assertEqual(result['thermo_blocks'][0]['row_count'], 2)
        self.assertEqual(result['job_state'], 'UNVERIFIED')

    def test_nonfinite_values_and_large_integer_steps(self):
        result = self.parse_fixture('Step Temp PotEng\n9007199254740993 NaN Inf\n9007199254740994 3.0D+02 -1.0\n')
        self.assertEqual(result['nonfinite_values'], 2)
        self.assertEqual(result['thermo_blocks'][0]['first']['values']['Step'], 9007199254740993)
        self.assertIsNone(result['thermo_blocks'][0]['first']['values']['Temp'])
        self.assertEqual(result['thermo_blocks'][0]['last']['values']['Temp'], 300)
        json.dumps(result, allow_nan=False)

    def test_malformed_and_truncated_rows_are_visible(self):
        for body in ['Step Temp\n0 300\n10 301 4\n', 'Step Temp\n0 300\n10 3broken\n', 'Step Temp\n']:
            with self.subTest(body=body):
                result = self.parse_fixture(body)
                self.assertGreater(result['issue_count'], 0)
                self.assertEqual(result['parse_scope'], 'PARTIAL')

    def test_yaml_is_not_misrepresented_as_supported_thermo(self):
        result = self.parse_fixture('---\nkeywords: [Step, Temp]\ndata:\n  - [0, 300]\n...\n')
        self.assertEqual(result['parse_scope'], 'PARTIAL')
        self.assertIn('YAML thermo', result['unsupported_formats'])
        self.assertFalse(result['thermo_blocks'])

    def test_empty_or_unrecognized_log_is_not_a_completed_run(self):
        result = self.parse_fixture('LAMMPS input echo only\nrun 100\n')
        self.assertEqual(result['parse_scope'], 'NO_SUPPORTED_THERMO')
        self.assertEqual(result['job_state'], 'UNVERIFIED')

    def test_cli_reports_unsupported_log_with_nonzero_exit(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / 'unsupported.log'
            source.write_text('keywords: [Step, Temp]\ndata:\n  - [0, 300]\n...\n', encoding='utf-8')
            output = root / 'summary.json'
            result = subprocess.run([sys.executable, str(ROOT / 'tools/parse_log.py'),
                                     '--log', str(source), '--output', str(output)],
                                    capture_output=True, text=True, timeout=15)
            self.assertEqual(result.returncode, 2, result.stderr)
            report = json.loads(output.read_text(encoding='utf-8'))
            self.assertEqual(report['parse_scope'], 'PARTIAL')
            self.assertEqual(report['job_state'], 'UNVERIFIED')


if __name__ == '__main__':
    unittest.main()
