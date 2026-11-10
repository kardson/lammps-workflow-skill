import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
import subprocess
import hashlib

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from validation_cases import load_case, plan, parse_termination


class ValidationBehavior(unittest.TestCase):
    def test_expected_negative_exit_is_separate_from_validation_failure(self):
        self.case['checks'][0].update(value=1)
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            terminal = {'state': 'FAILED', 'exit_code': 1}
            self.assertEqual(self.parse(directory, terminal)['status'], 'FAILED')
            self.case['expected_terminal_state'] = 'FAILED'
            result = self.parse(directory, terminal)
            self.assertEqual(result['status'], 'PASSED')
            self.assertEqual(result['process_terminal_state'], 'FAILED')
            path = directory / 'negative-case.json'
            path.write_text(json.dumps(self.case))
            child = subprocess.run([sys.executable, str(ROOT / 'tools/run_validation.py'),
                '--operation', 'parse', '--case', str(path), '--result-directory', str(directory)],
                capture_output=True, text=True)
            self.assertEqual(child.returncode, 0, child.stderr)
            self.assertEqual(json.loads(child.stdout)['process_terminal_state'], 'FAILED')
            self.assertEqual(self.parse(directory, {'state': 'SUCCEEDED', 'exit_code': 0})['status'], 'FAILED')
            self.assertEqual(self.parse(directory, {'state': 'FAILED', 'exit_code': 2})['status'], 'FAILED')
            self.case['expected_outputs'].append({'path': 'missing', 'required': True})
            self.assertEqual(self.parse(directory, terminal)['status'], 'PARTIAL')

    def test_expected_failure_requires_exact_nonzero_exit(self):
        self.case['expected_terminal_state'] = 'FAILED'
        with tempfile.TemporaryDirectory() as tmp:
            for value in (0, True, None, 1.0):
                self.case['checks'][0]['value'] = value
                with self.assertRaises(ValueError):
                    parse_termination(self.case, tmp)

    def test_historical_threshold_and_identity_never_imply_new_execution(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            source = directory / 'old.json'
            source.write_text(json.dumps({'checks': [{'status': 'PASS', 'error': 0.2}]}))
            self.case.update(parser='historical_record_v1',
                historical_source={'path': 'old.json', 'pointer': '/checks/0', 'observed_date': 'fixture-date'},
                inputs=[{'path': 'old.json', 'sha256': hashlib.sha256(source.read_bytes()).hexdigest()}],
                expected_outputs=[], checks=[{'metric': 'error', 'operator': 'le', 'value': 0.1,
                'unit': 'fixture-unit', 'source': 'Artificial declared threshold'}])
            report = parse_termination(self.case, directory)
            self.assertEqual(report['status'], 'FAILED')
            self.assertEqual(report['execution_relation'], 'HISTORICAL_NOT_RERUN')
            self.case['checks'][0]['value'] = 0.3
            self.assertEqual(parse_termination(self.case, directory)['status'], 'PASSED')
            source.write_text('{}')
            self.assertEqual(parse_termination(self.case, directory)['status'], 'PARTIAL')

    def test_input_identity_required_even_with_successful_terminal(self):
        self.case = load_case(ROOT / 'validation/cases/local-receipt-fixture.json')
        self.case['inputs'] = [{'path': 'in.lammps', 'sha256': hashlib.sha256(b'original').hexdigest()}]
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            self.assertEqual(self.parse(directory, {'state': 'SUCCEEDED', 'exit_code': 0})['status'], 'PARTIAL')
            (directory / 'in.lammps').write_bytes(b'changed')
            self.assertEqual(self.parse(directory, {'state': 'SUCCEEDED', 'exit_code': 0})['status'], 'PARTIAL')
            (directory / 'in.lammps').write_bytes(b'original')
            self.assertEqual(self.parse(directory, {'state': 'SUCCEEDED', 'exit_code': 0})['status'], 'PASSED')

    def test_cli_plan_and_partial_parse_exit_codes(self):
        command = [sys.executable, str(ROOT / 'tools/run_validation.py'), '--case',
                   str(ROOT / 'validation/cases/local-receipt-fixture.json')]
        result = subprocess.run(command + ['--operation', 'plan', '--category', 'local_logic'],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(json.loads(result.stdout)['execution_performed'])
        with tempfile.TemporaryDirectory() as tmp:
            result = subprocess.run(command + ['--operation', 'parse', '--result-directory', tmp],
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 1, result.stderr)
            self.assertEqual(json.loads(result.stdout)['status'], 'PARTIAL')

    def setUp(self):
        self.case = load_case(ROOT / 'validation/cases/local-receipt-fixture.json')

    def test_plan_does_not_select_all_by_default_or_authorize(self):
        self.assertEqual(plan([self.case])['cases'][0]['state'], 'NOT_SELECTED')
        report = plan([self.case], ['local_logic'])
        self.assertFalse(report['execution_performed'])
        self.assertEqual(report['cases'][0]['state'], 'SELECTED_NOT_RUN')
        with self.assertRaisesRegex(ValueError, 'Duplicate'):
            plan([self.case, self.case])

    def parse(self, directory, data):
        (directory / 'termination.json').write_text(json.dumps(data), encoding='utf-8')
        return parse_termination(self.case, directory)

    def test_success_failure_and_inconsistent_receipts(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            self.assertEqual(self.parse(directory, {'state': 'SUCCEEDED', 'exit_code': 0})['status'], 'PASSED')
            self.assertEqual(self.parse(directory, {'state': 'FAILED', 'exit_code': 1})['status'], 'FAILED')
            self.assertEqual(self.parse(directory, {'state': 'SUCCEEDED', 'exit_code': 2})['status'], 'FAILED')
            self.assertEqual(self.parse(directory, {'state': 'FAILED', 'exit_code': 0})['status'], 'FAILED')

    def test_missing_corrupt_and_boolean_code_not_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            self.assertEqual(parse_termination(self.case, directory)['status'], 'PARTIAL')
            (directory / 'termination.json').write_text('{')
            self.assertEqual(parse_termination(self.case, directory)['status'], 'PARTIAL')
            self.assertNotEqual(self.parse(directory, {'state': 'SUCCEEDED', 'exit_code': False})['status'], 'PASSED')

    def test_unknown_metric_or_missing_output_not_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            self.case['checks'][0]['metric'] = 'energy'
            self.assertEqual(self.parse(directory, {'state': 'SUCCEEDED', 'exit_code': 0})['status'], 'UNVERIFIED')
            self.case['expected_outputs'].append({'path': 'missing.dump', 'required': True})
            report = self.parse(directory, {'state': 'SUCCEEDED', 'exit_code': 0})
            self.assertEqual(report['status'], 'PARTIAL')
            self.assertIn('missing.dump', report['missing_outputs'])

    def test_unsupported_parser_and_escape_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.case['parser'] = 'unknown'
            self.assertEqual(parse_termination(self.case, tmp)['status'], 'UNVERIFIED')
            self.case['expected_outputs'][0]['path'] = '../outside'
            with self.assertRaises(ValueError):
                parse_termination(self.case, tmp)

    def test_lammps_complete_truncated_nonfinite_and_reset(self):
        self.case['parser'] = 'lammps_single_line_v1'
        self.case['checks'].append({'metric': 'last_step', 'operator': 'eq', 'value': 9,
                                   'unit': 'step', 'source': 'Synthetic two-stage contract'})
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            log = directory / 'log.lammps'
            prefix = 'Step Temp\n0 300\n20 301\nLoop time of 1\nStep Temp\n0 300\n9 301\n'
            log.write_text(prefix + 'Loop time of 1\n')
            report = self.parse(directory, {'state': 'SUCCEEDED', 'exit_code': 0})
            self.assertEqual(report['status'], 'PASSED')
            self.assertEqual(report['checks'][-1]['value'], 9)
            log.write_text(prefix)
            self.assertEqual(self.parse(directory, {'state': 'SUCCEEDED', 'exit_code': 0})['status'], 'PARTIAL')
            log.write_text(prefix.replace('9 301', '9 nan') + 'Loop time of 1\n')
            self.assertNotEqual(self.parse(directory, {'state': 'SUCCEEDED', 'exit_code': 0})['status'], 'PASSED')
            log.write_text(prefix + 'Loop time of 1\nERROR: synthetic failure\n')
            self.assertNotEqual(self.parse(directory, {'state': 'SUCCEEDED', 'exit_code': 0})['status'], 'PASSED')


if __name__ == '__main__':
    unittest.main()
