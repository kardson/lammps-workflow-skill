import copy
import csv
import json
from pathlib import Path
import sys
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from analyze_trajectory import analyze
from bundle_package import bundle
from generate_report import generate
from prepare_input_package import prepare
from prepare_sweep import prepare_sweep
from summarize_replicas import summarize
from local_fixtures import dump_frame, package_fixture, trajectory_config


class DeliveryTests(unittest.TestCase):
    def test_archive_exact_members_and_post_preparation_change_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            config = package_fixture(root)
            prepared = prepare(config, root, root / 'package')
            report = bundle(root / 'package', root / 'package.zip', root / 'archive.json')
            self.assertTrue(report['archive_crc_verified'])
            with zipfile.ZipFile(root / 'package.zip') as archive:
                self.assertEqual(set(archive.namelist()), set(prepared['package_files']) | {'package-manifest.json'})
                portable = json.loads(archive.read('configuration.json'))
                self.assertEqual(portable['structure_file'], 'structure.extxyz')
            with (root / 'package/in.growth').open('a', encoding='utf-8') as stream:
                stream.write('# changed after preparation\n')
            with self.assertRaises(ValueError):
                bundle(root / 'package', root / 'changed.zip', root / 'changed.json')
            self.assertFalse((root / 'changed.zip').exists())

    def test_archive_traversal_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            config = package_fixture(root)
            prepare(config, root, root / 'package')
            path = root / 'package/package-manifest.json'
            report = json.loads(path.read_text(encoding='utf-8'))
            report['package_files'][0] = '../outside.txt'
            report['file_identities'][0]['package_file'] = '../outside.txt'
            path.write_text(json.dumps(report), encoding='utf-8')
            with self.assertRaises(ValueError):
                bundle(root / 'package', root / 'bad.zip', root / 'bad.json')

    def test_explicit_replica_statistics_and_single_sample_unknown(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / 'replicas.csv'
            source.write_text('case,replica,roughness\na,1,1\na,2,2\na,3,3\nb,1,7\n', encoding='utf-8')
            config = {'metric_column': 'roughness', 'unit': 'angstrom', 'replica_id_column': 'replica',
                      'group_columns': ['case'], 'confidence': 0.95, 'independence_basis': 'Artificial independent scalar test fixture.', 'source_class': 'engineering_fixture'}
            result = summarize(source, config, root / 'summary')
            first, single = result['groups']
            self.assertEqual(first['mean'], 2)
            self.assertEqual(first['sample_sd'], 1)
            self.assertAlmostEqual(first['sem'], 1 / 3 ** 0.5)
            self.assertLess(first['confidence_lower'], first['mean'])
            self.assertIsNone(single['sem'])
            self.assertIsNone(single['confidence_upper'])
            source.write_text('case,replica,roughness\na,1,1\na,1,2\n', encoding='utf-8')
            with self.assertRaises(ValueError):
                summarize(source, config, root / 'duplicate')

    def test_bounded_sweep_proposes_candidates_without_jobs(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            base = package_fixture(root)
            source = root / 'base.json'
            source.write_text(json.dumps(base), encoding='utf-8')
            config = {'base_config_file': str(source), 'purpose': 'engineering_fixture',
                      'variants': [{'id': 'seed1', 'changes': {'velocity_seed': 11111}},
                                   {'id': 'seed2', 'changes': {'velocity_seed': 22222}}]}
            with self.assertRaises(ValueError):
                prepare_sweep(config, root, root / 'too-many', 1)
            result = prepare_sweep(config, root, root / 'sweep', 2)
            self.assertEqual(result['jobs_submitted'], 0)
            self.assertEqual(len(result['prepared_variants']), 2)
            self.assertNotEqual((root / 'sweep/seed1/in.growth').read_text(encoding='utf-8'),
                                (root / 'sweep/seed2/in.growth').read_text(encoding='utf-8'))

    def test_local_html_contains_declared_source_and_escaped_title(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / 'synthetic.dump'
            source.write_text(dump_frame(0, [[1, 2, 0.25, 0.5, 2], [2, 2, 1.25, 0.5, 4]]) +
                              dump_frame(1, [[1, 2, 0.25, 0.5, 3], [2, 2, 1.25, 0.5, 5]]), encoding='utf-8')
            analyze(source, trajectory_config(), root / 'analysis')
            result = generate(root / 'analysis', root / 'report', '<script>synthetic</script>', 2)
            text = (root / 'report/report.html').read_text(encoding='utf-8')
            self.assertIn('engineering_fixture', text)
            self.assertIn('&lt;script&gt;', text)
            self.assertNotIn('<script>', text)
            self.assertEqual(result['plotted_points'], 2)
            self.assertTrue((root / 'report/geometry-metrics.png').is_file())


if __name__ == '__main__':
    unittest.main()
