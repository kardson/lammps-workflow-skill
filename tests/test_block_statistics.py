from pathlib import Path
import math
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from block_statistics import analyze_samples


class TimeBlockStatistics(unittest.TestCase):
    def config(self):
        return {'window_start_ps': 0, 'window_end_ps': 8, 'block_duration_ps': 2,
                'sample_interval_ps': 1, 'time_tolerance_ps': 1e-9, 'maximum_blocks': 10,
                'minimum_blocks_for_interval': 4, 'confidence': 0.95,
                'window_basis': 'Artificial explicit fixture window', 'stationarity_basis': None,
                'correlation_basis': None, 'max_absolute_block_lag1': None}

    def test_correlated_frames_do_not_receive_iid_interval(self):
        blocks = []
        report = analyze_samples(((index, index // 2 + 1) for index in range(8)), self.config(), blocks.append)
        self.assertEqual(report['status'], 'DESCRIPTIVE_ONLY')
        self.assertEqual(report['complete_blocks'], 4)
        self.assertEqual(report['selected_samples'], 8)
        self.assertIsNone(report['block_mean_sem'])
        self.assertEqual([block['mean'] for block in blocks], [1, 2, 3, 4])

    def test_declared_lag_limit_blocks_interval_and_missing_block_is_retained(self):
        config = self.config()
        config.update(stationarity_basis='Artificial stationarity claim', correlation_basis='Artificial block claim',
                      max_absolute_block_lag1=0.5)
        samples = [(index, index // 2 + 1) for index in range(8)]
        report = analyze_samples(iter(samples), config)
        self.assertAlmostEqual(report['block_mean_lag1_correlation'], 1)
        self.assertIsNone(report['confidence_lower'])
        rows = []
        report = analyze_samples(iter(samples[:2] + samples[4:]), config, rows.append)
        self.assertEqual(report['incomplete_blocks'], 1)
        self.assertEqual(len(rows), 4)
        self.assertEqual(rows[1]['samples'], 0)
        self.assertIsNone(rows[1]['mean'])

    def test_bad_cadence_reset_or_nonfinite_data_not_discarded(self):
        for samples in ([(0, 1), (0, 2)], [(0, 1), (1.2, 2)], [(0, float('nan'))]):
            with self.subTest(samples=samples), self.assertRaises(ValueError):
                analyze_samples(iter(samples), self.config())

    def test_conditional_interval_uses_block_count_not_frame_count(self):
        config = self.config()
        config.update(window_end_ps=12, stationarity_basis='Artificial fixture declaration only',
                      correlation_basis='Artificial block declaration only', max_absolute_block_lag1=0.2)
        means = [0, 1, 0, -1, 0, 1]
        report = analyze_samples(((index, means[index // 2]) for index in range(12)), config)
        self.assertEqual(report['status'], 'CONDITIONAL_BLOCK_INTERVAL')
        self.assertEqual(report['complete_blocks'], 6)
        self.assertEqual(report['selected_samples'], 12)
        self.assertAlmostEqual(report['block_mean_sem'], math.sqrt(17 / 180))
        self.assertLess(report['confidence_lower'], report['complete_block_means']['mean'])
        self.assertGreater(report['confidence_upper'], report['complete_block_means']['mean'])
        self.assertEqual(report['scientific_acceptance'], 'UNVERIFIED')


if __name__ == '__main__':
    unittest.main()
