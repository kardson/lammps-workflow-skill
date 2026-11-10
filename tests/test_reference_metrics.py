import copy
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from reference_metrics import evaluate


class ReferenceMetrics(unittest.TestCase):
    def test_configuration_mismatch_and_repeated_metric_refused(self):
        self.reference['configuration_sha256'] = 'a' * 64
        self.prediction['configuration_sha256'] = 'b' * 64
        self.assertEqual(evaluate([self.reference], [self.prediction])['coverage']['forces']['valid'], 0)
        with self.assertRaises(ValueError):
            evaluate([self.reference], [self.prediction], ['forces', 'forces'])
    def setUp(self):
        self.reference = {'id': 'artificial', 'species': ['Ga', 'As'], 'energy_eV': -2,
            'energy_reference': 'explicit-fixture-zero', 'dft_group': 'fixture-only',
            'forces_eV_per_angstrom': [[0, 0, 0], [0, 0, 0]]}
        self.prediction = {**copy.deepcopy(self.reference), 'status': 'SUCCEEDED', 'energy_eV': -1.8,
            'forces_eV_per_angstrom': [[0.3, 0, 0], [0, 0, 0]]}

    def test_explicit_component_and_per_atom_errors(self):
        report = evaluate([self.reference], [self.prediction])
        self.assertEqual(report['status'], 'METRICS_REPORTED_NOT_ACCEPTED')
        self.assertAlmostEqual(report['energy_groups'][0]['errors_eV_per_atom']['mae'], 0.1)
        self.assertAlmostEqual(report['force_components_by_species_eV_per_angstrom']['Ga']['mae'], 0.1)
        self.assertEqual(report['scientific_acceptance'], 'UNVERIFIED')
        self.assertEqual(report['ranked_errors']['forces']['valid_samples'], 1)
        self.assertAlmostEqual(report['ranked_errors']['forces']['largest_first_100'][0]['absolute_error'], 0.3)

    def test_failure_missing_labels_and_unknown_energy_zero_counted(self):
        failed = {'id': 'failed', 'species': ['Ga'], 'status': 'FAILED', 'reason': 'fixture inference failure'}
        ref2 = {**self.reference, 'id': 'failed'}
        del self.reference['forces_eV_per_angstrom']
        self.prediction['energy_reference'] = 'different-zero'
        report = evaluate([self.reference, ref2], [self.prediction, failed])
        self.assertEqual(report['status'], 'METRICS_PARTIAL')
        self.assertEqual(report['coverage']['energy']['unavailable'], 2)
        self.assertEqual(report['coverage']['forces']['missing_label'], 1)
        self.assertEqual(report['coverage']['forces']['unavailable'], 1)
        self.assertEqual(report['coverage']['forces']['reference_labels_missing_or_invalid'], 1)
        self.assertEqual(report['prediction_accounting']['declared_failed'], 1)
        self.assertEqual(report['energy_groups'], [])

    def test_species_order_and_duplicate_ids_not_silently_repaired(self):
        self.prediction['species'].reverse()
        self.assertEqual(evaluate([self.reference], [self.prediction])['coverage']['forces']['valid'], 0)
        with self.assertRaises(ValueError):
            evaluate([self.reference, self.reference], [self.prediction])

    def test_stress_requires_exact_declared_units_and_convention(self):
        self.reference.update(stress=[[0, 0, 0]] * 3, stress_unit='kbar', stress_convention='VASP-raw-3x3')
        self.prediction.update(stress=[[0, 0, 0]] * 3, stress_unit='GPa', stress_convention='VASP-raw-3x3')
        self.assertEqual(evaluate([self.reference], [self.prediction], ['stress'])['coverage']['stress']['valid'], 0)

    def test_nonfinite_and_overflow_not_reported_as_valid_metrics(self):
        self.reference['energy_eV'] = -1e308
        self.prediction['energy_eV'] = 1e308
        self.prediction['forces_eV_per_angstrom'][0][0] = float('nan')
        report = evaluate([self.reference], [self.prediction])
        self.assertEqual(report['coverage']['energy']['valid'], 0)
        self.assertEqual(report['coverage']['forces']['valid'], 0)


if __name__ == '__main__':
    unittest.main()
