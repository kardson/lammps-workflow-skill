import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from stage_package import stage
from local_common import identity


class StagePackage(unittest.TestCase):
    def test_competing_staging_has_single_destination(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / 'source'
            source.mkdir()
            (source / 'input').write_text('fixture')
            (source / 'package-manifest.json').write_text(json.dumps({'package_files': ['input'],
                'file_identities': [{**identity(source / 'input'), 'package_file': 'input'}]}))
            barrier = Barrier(2)
            def request():
                barrier.wait(timeout=5)
                try:
                    stage(source, root / 'received')
                    return 'DONE'
                except (RuntimeError, FileExistsError):
                    return 'EXISTS_OR_LOCKED'
            with ThreadPoolExecutor(max_workers=2) as pool:
                results = list(pool.map(lambda _: request(), range(2)))
            self.assertEqual(results.count('DONE'), 1)
            self.assertTrue((root / 'received/stage-receipt.json').is_file())

    def test_actual_link_member_rejected_when_platform_permits(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / 'source'
            source.mkdir()
            (source / 'original').write_text('fixture')
            try:
                (source / 'link').symlink_to(source / 'original')
            except OSError as error:
                self.skipTest('Platform link creation unavailable: ' + str(error))
            (source / 'package-manifest.json').write_text(json.dumps({'package_files': ['link'],
                'file_identities': [{**identity(source / 'original'), 'package_file': 'link'}]}))
            with self.assertRaisesRegex(ValueError, 'Linked package'):
                stage(source, root / 'received')

    def test_reserved_destination_and_traversal_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / 'source'
            source.mkdir()
            (root / 'target.stage-lock').mkdir()
            with self.assertRaises(RuntimeError):
                stage(source, root / 'target')
            manifest = {'package_files': ['../outside'], 'file_identities': [
                {'package_file': '../outside', 'sha256': 'unused', 'bytes': 1}]}
            (source / 'package-manifest.json').write_text(json.dumps(manifest))
            with self.assertRaises(ValueError):
                stage(source, root / 'escape')
            self.assertFalse((root / 'escape').exists())

    def test_interrupted_copy_and_duplicate_identity(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / 'source'
            source.mkdir()
            (source / 'input').write_text('fixture')
            item = {**identity(source / 'input'), 'package_file': 'input'}
            manifest = {'package_files': ['input'], 'file_identities': [item]}
            path = source / 'package-manifest.json'
            path.write_text(json.dumps(manifest))
            with patch('stage_package.shutil.copyfile', side_effect=OSError('fixture interrupted')):
                with self.assertRaises(OSError):
                    stage(source, root / 'failed')
            self.assertFalse((root / 'failed').exists())
            self.assertFalse(any(p.name == 'stage-receipt.json' for p in root.rglob('*')))
            manifest['file_identities'].append(item)
            path.write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ValueError, 'inventory mismatch'):
                stage(source, root / 'duplicate')

    def test_verified_and_corrupt_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / 'source'
            source.mkdir()
            (source / 'in.growth').write_text('Artificial input')
            manifest = {'package_files': ['in.growth'], 'file_identities': [
                {**identity(source / 'in.growth'), 'package_file': 'in.growth'}]}
            (source / 'package-manifest.json').write_text(json.dumps(manifest))
            stage(source, root / 'good')
            self.assertTrue((root / 'good/stage-receipt.json').is_file())
            (source / 'in.growth').write_text('changed')
            with self.assertRaises(ValueError):
                stage(source, root / 'bad')
            self.assertFalse((root / 'bad').exists())
            self.assertTrue(list(root.glob('bad.partial-*')))


if __name__ == '__main__':
    unittest.main()
