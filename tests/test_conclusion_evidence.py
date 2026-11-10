import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from conclusion_evidence import audit
from local_common import identity
from generate_report import generate


class ConclusionTests(unittest.TestCase):
    def test_report_keeps_native_index_and_reproduction_configuration(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            analysis = root / 'analysis'
            analysis.mkdir()
            (analysis / 'analysis.json').write_text(json.dumps({
                'status': 'PARTIAL_TIME_MAPPING', 'frames_selected': 2,
                'configuration': {'source_class': 'engineering_fixture'},
                'method': {'height': 'Artificial fixture'}, 'limitations': ['No science validation'],
                'issues': ['Unmapped time']}), encoding='utf-8')
            csv = analysis / 'frame-metrics.csv'
            csv.write_text('frame,quantile_height_angstrom,rms_grid_roughness_angstrom\n0,1,0\n1,2,0.2\n', encoding='utf-8')
            config = root / 'evidence.json'
            config.write_text(json.dumps({'report_class': 'engineering', 'claims': [
                {'id': 'draft', 'statement': '<unsafe>', 'result': 2,
                 'sources': [{'path': 'analysis/frame-metrics.csv', 'sha256': identity(csv)['sha256'],
                              'locator': 'row frame=1; column quantile_height_angstrom'}]}]}), encoding='utf-8')
            original = csv.read_bytes()
            result = generate(analysis, root / 'report', 'Fixture <title>', 2, config)
            self.assertEqual(result['conclusion_chain_status'], 'PARTIAL')
            self.assertEqual(csv.read_bytes(), original)
            text = (root / 'report/report.html').read_text(encoding='utf-8')
            self.assertIn('&lt;unsafe&gt;', text)
            self.assertIn('PARTIAL_TIME_MAPPING', text)
            self.assertEqual(len(result['outputs']), 4)
            reproduction = json.loads((root / 'report/report-configuration.json').read_text())
            self.assertEqual(reproduction['sources'][1]['sha256'], identity(csv)['sha256'])

    def test_identity_and_missing_fields_are_separate_from_acceptance(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / 'result.json'
            source.write_text('{"value": 0}', encoding='utf-8')
            claim = {'id': 'zero', 'statement': 'Artificial zero result', 'attempt': 'fixture',
                     'method_version': 'fixture-v1', 'time_window': 'static snapshot',
                     'atom_selection': 'all fixture atoms', 'formula': 'fixture constant',
                     'unit': 'eV', 'result': 0, 'uncertainty': 'not estimated',
                     'acceptance_conditions': 'engineering only', 'limitations': ['artificial'],
                     'sources': [{'path': 'result.json', 'sha256': identity(source)['sha256'],
                                  'locator': '/value'}]}
            config = {'report_class': 'engineering', 'claims': [claim]}
            report = audit(config, root)
            self.assertEqual(report['status'], 'DECLARED_CHAINS_PRESENT')
            self.assertEqual(report['scientific_acceptance'], 'UNVERIFIED')
            source.write_text('{"value": 1}', encoding='utf-8')
            self.assertEqual(audit(config, root)['status'], 'PARTIAL')
            source.unlink()
            self.assertEqual(audit(config, root)['claims'][0]['sources'][0]['status'], 'UNAVAILABLE')

    def test_no_claims_and_missing_metadata_remain_partial(self):
        self.assertEqual(audit({'report_class': 'diagnostic', 'claims': []}, '.')['status'], 'PARTIAL')
        result = audit({'report_class': 'research', 'claims': [{'id': 'draft'}]}, '.')
        self.assertIn('uncertainty', result['claims'][0]['missing_evidence'])
        self.assertEqual(result['scientific_acceptance'], 'UNVERIFIED')

    def test_duplicate_and_invalid_class_rejected(self):
        for config in [{'report_class': 'accepted', 'claims': []},
                       {'report_class': 'research', 'claims': [{'id': 'a'}, {'id': 'a'}]}]:
            with self.assertRaises(ValueError):
                audit(config, '.')


if __name__ == '__main__':
    unittest.main()
