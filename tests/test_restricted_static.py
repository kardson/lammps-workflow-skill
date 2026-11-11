"""Artificial geometry/file tests only; no engine or potential inference."""
import hashlib
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from lammps_prediction import configuration_identity, import_sample, static_dump
from prepare_static_prediction import prepare
from restricted_cell import fractional
import test_lammps_prediction as old_import
import test_prepare_static_prediction as old_prepare


class RestrictedStatic(unittest.TestCase):
    def test_mixed_sign_dump_bounds_inverted_before_identity_check(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)
            sample = old_import.StaticPredictions().fixture(p)
            sample['configuration']['tilt_angstrom'] = [-3, 2, -4]
            sample['configuration_sha256'] = configuration_identity(sample['configuration'])
            dump = p / 'dump'
            text = dump.read_text().replace('BOX BOUNDS pp pp pp\n0 10\n0 10\n0 10',
                'BOX BOUNDS xy xz yz pp pp pp\n-3 12 -3\n-4 10 2\n0 10 -4')
            dump.write_text(text)
            sample['artifacts']['dump']['sha256'] = hashlib.sha256(dump.read_bytes()).hexdigest()
            frame = static_dump(dump, 2)
            self.assertEqual(frame['bounds'], [[0, 10]] * 3)
            self.assertEqual(frame['tilt_angstrom'], [-3, 2, -4])
            result = import_sample(sample, p)
            self.assertEqual(result['status'], 'SUCCEEDED', result)
            self.assertEqual(result['forces_eV_per_angstrom'], [[0.1, 0, 0], [0.2, 0, 0]])
            sample['configuration']['tilt_angstrom'][0] = -2.9
            sample['configuration_sha256'] = configuration_identity(sample['configuration'])
            self.assertIn('cell differs', import_sample(sample, p)['reason'])

    def test_skew_contains_cartesian_point_outside_axis_limits(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)
            config = old_prepare.StaticPreparation().config(p)
            config['configuration'].update(tilt_angstrom=[4, 0, 0],
                bounds_angstrom=[[0, 10]] * 3,
                positions_angstrom=[[10.5, 9, 9], [2, 2, 2]])
            config['configuration_sha256'] = configuration_identity(config['configuration'])
            result = prepare(config, p, p / 'candidate')
            self.assertFalse(result['inference_performed'])
            text = (p / 'candidate/structure.data').read_text()
            self.assertIn('4 0 0 xy xz yz', text)
            self.assertIn('7 1 10.5 9 9', text)
            config['configuration']['positions_angstrom'][0] = [0.1, 9, 1]
            config['configuration_sha256'] = configuration_identity(config['configuration'])
            with self.assertRaisesRegex(ValueError, 'outside box'):
                prepare(config, p, p / 'bad')
            self.assertFalse((p / 'bad').exists())

    def test_fractional_solver_uses_origin_and_all_three_tilts(self):
        # Origin=(1,-2,3), lengths=(4,5,6), tilt=(-2,1,-3), s=(.25,.5,.75)
        self.assertEqual(fractional([1.75, -1.75, 7.5],
            [[1, 5], [-2, 3], [3, 9]], [-2, 1, -3]), [.25, .5, .75])

    def test_tilt_is_part_of_identity_and_invalid_values_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)
            config = old_prepare.StaticPreparation().config(p)
            original = configuration_identity(config['configuration'])
            config['configuration']['tilt_angstrom'] = [0, 0, 0]
            self.assertNotEqual(original, configuration_identity(config['configuration']))
            for bad in ([0, 0], [0, float('nan'), 0], [True, 0, 0]):
                config['configuration']['tilt_angstrom'] = bad
                with self.assertRaises(ValueError):
                    configuration_identity(config['configuration'])

    def test_general_triclinic_and_invalid_recovered_lengths_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)
            old_import.StaticPredictions().fixture(p)
            dump = p / 'dump'
            original = dump.read_text()
            dump.write_text(original.replace('BOX BOUNDS pp pp pp', 'BOX BOUNDS abc origin pp pp pp'))
            with self.assertRaisesRegex(ValueError, 'restricted-triclinic'):
                static_dump(dump, 2)
            dump.write_text(original.replace('BOX BOUNDS pp pp pp\n0 10\n0 10\n0 10',
                'BOX BOUNDS xy xz yz pp pp pp\n0 1 5\n0 10 0\n0 10 0'))
            with self.assertRaisesRegex(ValueError, 'Increasing'):
                static_dump(dump, 2)


if __name__ == '__main__':
    unittest.main()
