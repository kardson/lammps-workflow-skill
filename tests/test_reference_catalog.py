from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from reference_catalog import select


class ReferenceCatalog(unittest.TestCase):
    def test_version_missing_is_gap_not_fallback(self):
        entries = [{'engine_ids': ['cpu-2026'], 'topics': ['fix_deposit'], 'path': 'manual'}]
        self.assertEqual(len(select(entries, 'cpu-2026', 'fix_deposit')), 1)
        self.assertEqual(select(entries, 'gpu-2025', 'fix_deposit'), [])


if __name__ == '__main__':
    unittest.main()
