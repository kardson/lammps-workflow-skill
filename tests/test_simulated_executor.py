from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from simulated_executor import SimulatedExecutor


class SimulatedExecution(unittest.TestCase):
    def test_competing_requests_do_not_duplicate_launch(self):
        with tempfile.TemporaryDirectory() as tmp:
            executor = SimulatedExecutor(tmp)
            executor.prepare('fixture')
            executor.stage()
            barrier = Barrier(2)
            def request():
                barrier.wait(timeout=5)
                try:
                    return SimulatedExecutor(tmp).launch()['launch_requests']
                except RuntimeError:
                    return 'LOCKED'
            with ThreadPoolExecutor(max_workers=2) as pool:
                results = list(pool.map(lambda _: request(), range(2)))
            self.assertIn(1, results)
            self.assertEqual(executor.status()['launch_requests'], 1)

    def test_failed_atomic_replace_preserves_previous_state(self):
        with tempfile.TemporaryDirectory() as tmp:
            executor = SimulatedExecutor(tmp)
            executor.prepare('fixture')
            with patch('simulated_executor.os.replace', side_effect=OSError('fixture interrupted write')):
                with self.assertRaises(OSError):
                    executor.stage()
            self.assertEqual(executor.status()['execution_state'], 'PREPARED')
            self.assertTrue(list(Path(tmp).glob('state-*.tmp')))

    def test_mutation_lock_and_invalid_transition(self):
        with tempfile.TemporaryDirectory() as tmp:
            executor = SimulatedExecutor(tmp)
            executor.prepare('fixture')
            with self.assertRaises(ValueError):
                executor.launch()
            executor.stage()
            (Path(tmp) / '.mutation-lock').mkdir()
            with self.assertRaises(RuntimeError):
                SimulatedExecutor(tmp).launch()
            self.assertEqual(executor.status()['launch_requests'], 0)
            self.assertTrue((Path(tmp) / '.mutation-lock').is_dir())

    def test_unknown_and_partial_collection_are_separate_from_execution(self):
        with tempfile.TemporaryDirectory() as tmp:
            executor = SimulatedExecutor(tmp)
            executor.prepare('fixture')
            executor.stage()
            executor.launch()
            executor.observe(False)
            with self.assertRaises(ValueError):
                executor.launch()
            self.assertEqual(executor.status()['execution_state'], 'RUNNING')
            executor.observe(True)
            executor.finish(0)
            result = executor.collect(['log', 'dump'], ['log'])
            self.assertEqual(result['execution_state'], 'SUCCEEDED')
            self.assertEqual(result['collection']['status'], 'PARTIAL')

    def test_persistent_sequential_retry_and_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            executor = SimulatedExecutor(tmp)
            executor.prepare('fixture-attempt')
            executor.stage()
            executor.launch()
            recovered = SimulatedExecutor(tmp)
            self.assertEqual(recovered.launch()['launch_requests'], 1)
            recovered.finish(1)
            self.assertEqual(executor.status()['execution_state'], 'FAILED')
            with self.assertRaises(FileExistsError):
                executor.prepare('replacement')


if __name__ == '__main__':
    unittest.main()
