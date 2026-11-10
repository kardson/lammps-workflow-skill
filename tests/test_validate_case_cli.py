import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / 'tools/validate_case.py'


class ValidateCaseCLI(unittest.TestCase):
    def run_record(self, contents, *arguments):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'record.json'
            path.write_text(contents, encoding='utf-8')
            result = subprocess.run([sys.executable, str(TOOL), '--record', str(path), *arguments],
                                    cwd=tmp, capture_output=True, text=True)
            self.assertNotIn('Traceback', result.stderr)
            return result.returncode, json.loads(result.stdout)

    def test_bad_json_and_nonobject_return_error(self):
        for contents in ('{broken', '[]', 'null'):
            with self.subTest(contents=contents):
                code, report = self.run_record(contents)
                self.assertEqual(code, 2)
                self.assertEqual(report['status'], 'ERROR')

    def test_invalid_schema_is_not_success(self):
        code, report = self.run_record(json.dumps({'record_type': 'md_plan'}))
        self.assertEqual(code, 1)
        self.assertEqual(report['status'], 'INVALID')

    def test_unresolved_links_are_explicitly_partial(self):
        record = (ROOT / 'templates/attempt.json').read_text()
        code, report = self.run_record(record, '--check-links')
        self.assertEqual(code, 0)
        self.assertEqual(report['links']['status'], 'PARTIAL')
        self.assertTrue(report['links']['unknown'])
        self.assertFalse(report['execution_performed'])

    def test_malformed_binding_returns_diagnostic(self):
        record = json.loads((ROOT / 'templates/attempt.json').read_text())
        record['plan_binding'] = {'file': 123}
        code, report = self.run_record(json.dumps(record), '--check-links')
        self.assertEqual(code, 1)
        self.assertEqual(report['links']['status'], 'INCONSISTENT')


if __name__ == '__main__':
    unittest.main()
