"""Behavioral fixtures; no simulation or external connection."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from check_environment import parse_help
from common import evidence_path, write_report
from init_workspace import initialize, MARKER
from inspect_potential import inspect_file
from search_manual import search


class WorkflowToolsTests(unittest.TestCase):
    def test_help_sections_do_not_cross_match(self):
        help_text = '''Installed packages:

MANYBODY OPENMP

Lists of individual styles included in this LAMMPS executable
* Pair styles:
nep* tersoff
* Fix styles:
deposit nve
* Compute styles:
temp
'''
        parsed = parse_help(help_text)
        self.assertIn('nep', parsed['Pair styles'])
        self.assertNotIn('deposit', parsed['Pair styles'])
        self.assertIn('deposit', parsed['Fix styles'])
        self.assertEqual(parsed['packages'], ['MANYBODY', 'OPENMP'])
        self.assertIsNone(parse_help('unrecognized help')['packages'])

    def test_workspace_preserves_existing_work_and_rules(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            original = '# Existing rules\nPreserve source files.\n'
            (root / 'AGENTS.md').write_text(original, encoding='utf-8')
            initialize(root, connect_skill=False)
            self.assertEqual((root / 'AGENTS.md').read_text(encoding='utf-8'), original)
            plan = root / '01_plan/md-plan.json'
            self.assertIsNone(json.loads(plan.read_text(encoding='utf-8'))['confirmation'])
            plan.write_text('{"private": true}', encoding='utf-8')
            initialize(root, connect_skill=True)
            initialize(root, connect_skill=True)
            self.assertEqual(plan.read_text(encoding='utf-8'), '{"private": true}')
            rules = (root / 'AGENTS.md').read_text(encoding='utf-8')
            self.assertTrue(rules.startswith(original))
            self.assertEqual(rules.count(MARKER), 1)

    def test_evidence_cannot_overwrite_or_enter_skill(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'evidence.json'
            write_report(path, {'observed': True})
            before = path.read_bytes()
            with self.assertRaises(FileExistsError):
                write_report(path, {'observed': False})
            self.assertEqual(path.read_bytes(), before)
        with self.assertRaises(ValueError):
            evidence_path(ROOT / 'forbidden-evidence.json')
        with self.assertRaises(ValueError):
            initialize(ROOT / 'research')

    def test_nep_identity_coverage_does_not_imply_suitability(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'fixture.txt'
            content = b'nep4_zbl 2 Si C\nzbl 1 2\nartificial header fixture, not usable weights\n'
            path.write_bytes(content)
            result = inspect_file(path, 'nep', ['Si', 'O'])
            self.assertEqual(result['sha256'], hashlib.sha256(content).hexdigest())
            self.assertEqual(result['required_element_coverage'], {'Si': True, 'O': False})
            self.assertEqual(result['scientific_suitability'], 'UNVERIFIED')
            self.assertTrue(result['built_in_zbl_declared'])
            self.assertEqual(path.read_bytes(), content)
            path.write_text('nep4 2 Si Si\n', encoding='utf-8')
            with self.assertRaises(ValueError):
                inspect_file(path, 'nep', [])

    def test_empirical_route_does_not_invent_elements(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'empirical.params'
            path.write_text('artificial parameter identity fixture', encoding='utf-8')
            result = inspect_file(path, 'empirical', [])
            self.assertNotIn('elements', result)
            self.assertFalse(result['inference_run'])

    def test_explicit_offline_manual_and_limit(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            (folder / 'fix_deposit.rst').write_text('fix deposit\nexample fix deposit\n', encoding='utf-8')
            self.assertEqual(len(search(folder, 'fix deposit', 1)), 1)
            self.assertEqual(search(folder, 'missing literal', 1), [])
            with self.assertRaises(ValueError):
                search(folder, '', 1)

    def test_missing_executable_is_not_success(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / 'environment.json'
            result = subprocess.run([sys.executable, str(ROOT / 'tools/check_environment.py'),
                                     '--role', 'controller', '--lmp', str(Path(temporary) / 'missing-lmp'),
                                     '--output', str(output)], capture_output=True, text=True, timeout=15)
            self.assertEqual(result.returncode, 1, result.stderr)
            report = json.loads(output.read_text(encoding='utf-8'))
            self.assertEqual(report['engine']['status'], 'MISSING')
            self.assertFalse(report['simulation_run'])


if __name__ == '__main__':
    unittest.main()
