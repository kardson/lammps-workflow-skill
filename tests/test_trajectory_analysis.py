import csv
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from analyze_trajectory import analyze
from local_fixtures import dump_frame, trajectory_config


class TrajectoryAnalysisTests(unittest.TestCase):
    def test_exact_grid_geometry_composition_and_snapshot_ids(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / 'synthetic.dump'
            source.write_text(dump_frame(0, [[1, 1, 0.25, 0.5, 1], [2, 2, 0.25, 0.5, 2], [3, 2, 1.25, 0.5, 4]]) +
                              dump_frame(10, [[1, 1, 0.25, 0.5, 1], [3, 2, 1.25, 0.5, 4], [4, 2, 0.25, 0.5, 6]]), encoding='utf-8')
            before = source.read_bytes()
            report = analyze(source, trajectory_config(), root / 'analysis')
            self.assertTrue(report['source']['complete_read'])
            self.assertEqual(report['frames_selected'], 2)
            with (root / 'analysis/frame-metrics.csv').open(encoding='utf-8', newline='') as stream:
                rows = list(csv.DictReader(stream))
            self.assertEqual(float(rows[0]['quantile_height_angstrom']), 3)
            self.assertEqual(float(rows[0]['rms_grid_roughness_angstrom']), 1)
            self.assertEqual(float(rows[0]['occupied_grid_fraction']), 1)
            self.assertEqual(int(rows[1]['appeared_ids_since_previous_selected_frame']), 1)
            self.assertEqual(int(rows[1]['disappeared_ids_since_previous_selected_frame']), 1)
            self.assertEqual(report['scientific_acceptance'], 'UNVERIFIED')
            self.assertEqual(source.read_bytes(), before)

    def test_scaled_coordinates_match_cartesian_metrics(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / 'scaled.dump'
            source.write_text(dump_frame(0, [[2, 2, 0.125, 0.5, 0.2], [3, 2, 0.625, 0.5, 0.4]], scaled=True), encoding='utf-8')
            report = analyze(source, trajectory_config(), root / 'analysis')
            with (root / 'analysis/frame-metrics.csv').open(encoding='utf-8', newline='') as stream:
                row = next(csv.DictReader(stream))
            self.assertEqual(float(row['rms_grid_roughness_angstrom']), 1)
            self.assertEqual(report['frames_read'], 1)

    def test_sampling_is_partial_and_empty_film_is_not_zero_thickness(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / 'empty-film.dump'
            source.write_text(dump_frame(0, [[1, 1, 0.25, 0.5, 1]]) + dump_frame(1, []), encoding='utf-8')
            result = analyze(source, trajectory_config(), root / 'analysis', max_frames=1)
            self.assertEqual(result['status'], 'PARTIAL_SNAPSHOT')
            with (root / 'analysis/frame-metrics.csv').open(encoding='utf-8', newline='') as stream:
                row = next(csv.DictReader(stream))
            self.assertEqual(row['quantile_height_angstrom'], '')
            self.assertEqual(float(row['occupied_grid_fraction']), 0)

    def test_duplicate_ids_truncation_and_triclinic_dump_are_failed(self):
        for body in [dump_frame(0, [[1, 1, 0, 0, 1], [1, 2, 1, 0, 2]]),
                     dump_frame(0, [[1, 1, 0, 0, 1]]).rsplit('\n', 2)[0] + '\n',
                     dump_frame(0, []).replace('BOUNDS pp pp ff', 'BOUNDS xy xz yz pp pp ff')]:
            with self.subTest(body=body), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                source = root / 'bad.dump'
                source.write_text(body, encoding='utf-8')
                with self.assertRaises(ValueError):
                    analyze(source, trajectory_config(), root / 'analysis')
                failure = json.loads((root / 'analysis/analysis.json').read_text(encoding='utf-8'))
                self.assertEqual(failure['status'], 'FAILED')
                self.assertIsNotNone(failure['failure'])


if __name__ == '__main__':
    unittest.main()
