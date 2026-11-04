import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

TOOL = Path(__file__).resolve().parents[1] / 'tools/preflight_nep_model.py'


class ModelPreflightTests(unittest.TestCase):
    def invoke(self, path, digest, elements):
        result = subprocess.run([sys.executable, str(TOOL), '--model', str(path),
                                 '--expected-sha256', digest, '--elements', *elements],
                                capture_output=True, text=True)
        return result.returncode, json.loads(result.stdout)

    def test_valid_identity_and_coverage(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'fixture.txt'
            path.write_bytes(b'nep4_zbl 2 Si C\nartificial parser fixture\n')
            code, report = self.invoke(path, hashlib.sha256(path.read_bytes()).hexdigest(), ['Si', 'C'])
            self.assertEqual(code, 0)
            self.assertEqual(report['status'], 'PASS')
            self.assertFalse(report['inference_run'])

    def test_changed_weights_rejected_with_same_header(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'fixture.txt'
            original = b'nep4 1 Si\noriginal fixture bytes\n'
            path.write_bytes(original.replace(b'original', b'changed'))
            code, report = self.invoke(path, hashlib.sha256(original).hexdigest(), ['Si'])
            self.assertEqual(code, 2)
            self.assertIn('SHA-256', report['problems'][0])

    def test_species_not_covered(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'fixture.txt'; path.write_bytes(b'nep4 1 Si\n')
            code, report = self.invoke(path, hashlib.sha256(path.read_bytes()).hexdigest(), ['C'])
            self.assertEqual(code, 2)
            self.assertIn('C', report['problems'][0])

    def test_missing_empty_directory_and_bad_header(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            for name, content in [('empty', b''), ('bad', b'nep4 2 Si\n')]:
                (root / name).write_bytes(content)
            for path in [root / 'missing', root, root / 'empty', root / 'bad']:
                with self.subTest(path=path):
                    code, report = self.invoke(path, '0' * 64, ['Si'])
                    self.assertEqual(code, 2)
                    self.assertTrue(report['problems'])


if __name__ == '__main__':
    unittest.main()
