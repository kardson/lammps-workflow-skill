import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from prepare_static_prediction import prepare
from lammps_prediction import configuration_identity


class StaticPreparation(unittest.TestCase):
    def config(self, directory, kind='empirical'):
        profile = {'schema_version': 1, 'record_type': 'engine_profile', 'id': 'artificial-not-installed',
                   'lammps_version': None, 'interface': {'revision': None}, 'precision': None}
        (directory / 'engine.json').write_text(json.dumps(profile))
        configuration = {'species': ['Ga', 'As'], 'atom_ids': [7, 3], 'boundary': ['pp', 'pp', 'ff'],
                         'bounds_angstrom': [[0, 10], [0, 10], [-1, 10]],
                         'positions_angstrom': [[1.123456789012345, 1, 1], [2, 2, 2]]}
        return {'schema_version': 1, 'record_type': 'static_prediction_plan', 'id': 'artificial-static',
                'source_class': 'artificial_fixture',
                'provenance': 'Synthetic structure and pair syntax only; no physical model',
                'configuration': configuration, 'configuration_sha256': configuration_identity(configuration),
                'maximum_atoms': 2, 'masses_amu': {'Ga': 69.723, 'As': 74.921595}, 'engine_profile_file': 'engine.json',
                'potential': {'kind': kind, 'provenance': 'Artificial fixture only', 'type_order': ['Ga', 'As'],
                              'files': [], 'pair_style': ['lj/cut', '2.5'],
                              'pair_coeff': [['*', '*', '1', '1', '2.5']]}}

    def test_candidate_roundtrip_noncontiguous_ids_and_unresolved_profile(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            config = self.config(directory)
            report = prepare(config, directory, directory / 'candidate')
            self.assertFalse(report['execution_authorized'])
            self.assertFalse(report['inference_performed'])
            text = (directory / 'candidate/structure.data').read_text()
            self.assertIn('7 1 1.123456789012345', text)
            self.assertIn('3 2 2 2 2', text)
            commands = (directory / 'candidate/in.static').read_text().splitlines()
            self.assertIn('run 0', commands)
            self.assertFalse(any(row.startswith('fix ') for row in commands))
            before = (directory / 'candidate/structure.data').read_bytes()
            with self.assertRaises(FileExistsError):
                prepare(config, directory, directory / 'candidate')
            self.assertEqual((directory / 'candidate/structure.data').read_bytes(), before)

    def test_model_file_identity_and_reserved_destination(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = Path(tmp)
            config = self.config(directory, 'pretrained_ml')
            (directory / 'model.nep').write_bytes(b'Not a real NEP model; copy test only')
            digest = hashlib.sha256((directory / 'model.nep').read_bytes()).hexdigest()
            config['potential'].update(files=[{'source': 'model.nep', 'target': 'model.nep', 'sha256': digest}],
                                      pair_style=['nep'], pair_coeff=[['*', '*', 'model.nep', 'Ga', 'As']])
            prepare(config, directory, directory / 'candidate')
            self.assertEqual((directory / 'candidate/model.nep').read_bytes(), (directory / 'model.nep').read_bytes())
            config['potential']['files'][0]['target'] = 'final.dump'
            with self.assertRaises(ValueError):
                prepare(config, directory, directory / 'bad')
            self.assertFalse((directory / 'bad').exists())

    def test_changed_geometry_and_periodic_upper_face_not_repaired(self):
        for mode in ('hash', 'upper-face'):
            with tempfile.TemporaryDirectory() as tmp:
                directory = Path(tmp)
                config = self.config(directory)
                config['configuration']['positions_angstrom'][0][0] = 10 if mode == 'upper-face' else 1.2
                if mode == 'upper-face':
                    config['configuration_sha256'] = configuration_identity(config['configuration'])
                with self.assertRaisesRegex(ValueError, 'Configuration.*identity' if mode == 'hash' else 'periodic upper face'):
                    prepare(config, directory, directory / 'bad')
                self.assertFalse((directory / 'bad').exists())


if __name__ == '__main__':
    unittest.main()
