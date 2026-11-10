import copy
import hashlib
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from lammps_prediction import import_sample, configuration_identity


class StaticPredictions(unittest.TestCase):
    def fixture(self, directory):
        content = {'input': 'units metal\natom_style atomic\nrun 0\n',
            'execution': '{"exit_code":0}',
            'log': 'Step Atoms PotEng\n0 2 -2\nLoop time of 0\n',
            'dump': 'ITEM: TIMESTEP\n0\nITEM: NUMBER OF ATOMS\n2\nITEM: BOX BOUNDS pp pp pp\n0 10\n0 10\n0 10\nITEM: ATOMS id type x y z fx fy fz\n2 2 2 2 2 0.2 0 0\n1 1 1 1 1 0.1 0 0\n'}
        artifacts = {}
        for role, text in content.items():
            path = directory / role
            path.write_text(text)
            artifacts[role] = {'path': role, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
        configuration = {'species': ['Ga', 'As'], 'atom_ids': [1, 2], 'positions_angstrom': [[1, 1, 1], [2, 2, 2]],
                         'bounds_angstrom': [[0, 10]] * 3, 'boundary': ['pp'] * 3}
        return {'id': 'artificial-static', 'configuration': configuration,
                'configuration_sha256': configuration_identity(configuration), 'type_order': ['Ga', 'As'],
                'expected_step': 0, 'maximum_atoms': 2, 'geometry_tolerance_angstrom': 1e-8, 'artifacts': artifacts}

    def test_unsorted_ids_are_mapped_to_requested_atom_order(self):
        with tempfile.TemporaryDirectory() as tmp:
            sample = self.fixture(Path(tmp))
            report = import_sample(sample, tmp)
            self.assertEqual(report['status'], 'SUCCEEDED', report)
            self.assertEqual(report['forces_eV_per_angstrom'], [[0.1, 0, 0], [0.2, 0, 0]])
            self.assertEqual(report['energy_eV'], -2)
            self.assertIsNone(report['energy_reference'])

    def test_changed_geometry_or_boundary_cannot_be_imported(self):
        for field in ('geometry', 'boundary'):
            with tempfile.TemporaryDirectory() as tmp:
                sample = self.fixture(Path(tmp))
                if field == 'geometry':
                    sample['configuration']['positions_angstrom'][0][0] = 1.1
                else:
                    sample['configuration']['boundary'][2] = 'ff'
                sample['configuration_sha256'] = configuration_identity(sample['configuration'])
                report = import_sample(sample, tmp)
                self.assertEqual(report['status'], 'FAILED')
                self.assertEqual(report['id'], sample['id'])

    def test_changed_source_and_missing_artifact_remain_failed_samples(self):
        with tempfile.TemporaryDirectory() as tmp:
            sample = self.fixture(Path(tmp))
            (Path(tmp) / 'dump').write_text('changed')
            self.assertIn('identity mismatch', import_sample(sample, tmp)['reason'])
            (Path(tmp) / 'dump').unlink()
            self.assertEqual(import_sample(sample, tmp)['status'], 'FAILED')

    def test_nonzero_exit_or_unknown_units_refused(self):
        for role, text in [('execution', '{"exit_code":1}'), ('input', 'units real\nrun 0\n')]:
            with tempfile.TemporaryDirectory() as tmp:
                sample = self.fixture(Path(tmp))
                path = Path(tmp) / role
                path.write_text(text)
                sample['artifacts'][role]['sha256'] = hashlib.sha256(path.read_bytes()).hexdigest()
                self.assertEqual(import_sample(sample, tmp)['status'], 'FAILED')


if __name__ == '__main__':
    unittest.main()
