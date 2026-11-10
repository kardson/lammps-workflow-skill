import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
from record_io import read_record, reference_path, copy_record


class RecordIO(unittest.TestCase):
    def test_copy_preserves_bytes_and_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            source, output = Path(tmp) / 'source.json', Path(tmp) / 'copy.json'
            data = b'\xef\xbb\xbf{ "schema_version": 1, "confirmation": null }\r\n'
            source.write_bytes(data)
            copy_record(source, output)
            self.assertEqual(source.read_bytes(), data)
            self.assertEqual(output.read_bytes(), data)
            self.assertIsNone(read_record(output)['confirmation'])
            with self.assertRaises(FileExistsError):
                copy_record(source, output)

    def test_future_version_is_not_silently_migrated(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / 'source.json'
            source.write_text(json.dumps({'schema_version': 2}))
            with self.assertRaises(ValueError):
                copy_record(source, Path(tmp) / 'output.json')
            self.assertFalse((Path(tmp) / 'output.json').exists())

    def test_reference_uses_record_directory_or_explicit_root(self):
        path = Path(tempfile.gettempdir()) / 'records' / 'plan.json'
        self.assertEqual(reference_path(path, 'model'), path.parent / 'model')
        self.assertEqual(reference_path(path, 'model', path.parent.parent), path.parent.parent / 'model')


if __name__ == '__main__':
    unittest.main()
