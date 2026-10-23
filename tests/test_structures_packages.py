import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from prepare_structure import prepare as prepare_structure
from prepare_input_package import prepare as prepare_package, readiness
from structure_io import geometry_summary, read_structure, write_structure
from local_fixtures import package_fixture


class StructureAndPackageTests(unittest.TestCase):
    def test_export_does_not_silently_rotate_the_research_axes(self):
        from ase import Atoms
        atoms = Atoms('Si', positions=[[0, 0, 1]], cell=[[0, 5, 0], [-5, 0, 0], [0, 0, 5]], pbc=[True, True, False])
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaises(ValueError):
                write_structure(Path(temporary), atoms, ['Si'])
            self.assertFalse((Path(temporary) / 'structure.data').exists())

    def test_bulk_slab_interface_roundtrip_and_no_relaxation(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            base = {'operation': 'bulk_zincblende', 'purpose': 'engineering_fixture',
                    'provenance': 'Artificial lattice for serializer testing, not reference material data.',
                    'type_order': ['Si', 'C'], 'boundary': ['p', 'p', 'p'], 'minimum_separation_angstrom': 0.2,
                    'elements': ['Si', 'C'], 'lattice_a_angstrom': 4.4, 'repeat': [1, 1, 1]}
            bulk = prepare_structure(base, root, root / 'bulk')
            self.assertEqual(bulk['audit']['atom_count'], 8)
            self.assertFalse(bulk['calculator_used'])
            source = root / 'bulk/structure.extxyz'
            slab_config = {**base, 'operation': 'slab', 'source_file': str(source), 'source_format': 'extxyz',
                           'source_boundary': ['p', 'p', 'p'], 'boundary': ['p', 'p', 'f'],
                           'miller': [1, 0, 0], 'layers': 2, 'trim_bottom_planes': 0, 'trim_top_planes': 0,
                           'plane_tolerance_angstrom': 1e-5, 'bottom_buffer_angstrom': 1,
                           'vacuum_above_angstrom': 8, 'termination_label': 'explicit unrelaxed engineering cut'}
            slab = prepare_structure(slab_config, root, root / 'slab')
            self.assertIn('observed_top_plane', slab['construction'])
            interface_config = {**base, 'operation': 'interface', 'boundary': ['p', 'p', 'f'],
                                'substrate_file': str(root / 'slab/structure.extxyz'), 'film_file': str(root / 'slab/structure.extxyz'),
                                'source_format': 'extxyz', 'lateral_match': 'strain_film_to_substrate',
                                'gap_angstrom': 1.5, 'bottom_buffer_angstrom': 1, 'vacuum_above_angstrom': 8,
                                'film_xy_shift_angstrom': [0, 0]}
            interface = prepare_structure(interface_config, root, root / 'interface')
            self.assertEqual(interface['audit']['atom_count'], 2 * slab['audit']['atom_count'])
            reread = read_structure(root / 'interface/structure.data', 'lammps-data', ['Si', 'C'], ['p', 'p', 'f'])
            self.assertEqual(len(reread), interface['audit']['atom_count'])
            self.assertEqual(interface['scientific_acceptance'], 'UNVERIFIED')

    def test_periodic_overlap_and_nonperiodic_bounds_are_detected(self):
        from ase import Atoms
        atoms = Atoms('Si2', positions=[[0.1, 1, 1], [9.9, 1, 1]], cell=[10, 10, 10], pbc=[True, True, False])
        report = geometry_summary(atoms, ['Si'], ['p', 'p', 'f'], 0.3)
        self.assertEqual(report['close_pair_count'], 1)
        atoms.positions[1, 2] = 11
        report = geometry_summary(atoms, ['Si'], ['p', 'p', 'f'], 0.3)
        self.assertIn('2', report['nonperiodic_out_of_bounds'])

    def test_boundary_and_embedded_type_disagreement_rejected(self):
        import numpy as np
        from ase import Atoms
        from ase.io import write
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'inconsistent.extxyz'
            atoms = Atoms('SiC', positions=[[1, 1, 1], [2, 2, 2]], cell=[5, 5, 5], pbc=[True, True, False])
            atoms.set_array('lammps_type', np.array([2, 1]))
            write(path, atoms, format='extxyz')
            with self.assertRaises(ValueError):
                read_structure(path, 'extxyz', ['Si', 'C'], ['p', 'p', 'p'])
            with self.assertRaises(ValueError):
                read_structure(path, 'extxyz', ['Si', 'C'], ['p', 'p', 'f'])

    def test_candidate_has_one_mobile_integrator_and_preserves_source(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            config = package_fixture(root)
            source = Path(config['structure_file'])
            original = source.read_bytes()
            result = prepare_package(config, root, root / 'package')
            text = (root / 'package/in.growth').read_text(encoding='utf-8')
            self.assertEqual(text.count('fix integrate mobile nve'), 1)
            self.assertIn('fix source1 mobile deposit', text)
            self.assertIn('dynamic/dof yes', text)
            self.assertIn('f_source1', text)
            self.assertIn('CUMULATIVE_INSERTED source1', text)
            self.assertNotIn('f_source1', text.split('unfix source1', 1)[1])
            self.assertFalse(result['execution_authorized'])
            self.assertEqual(result['initial_group_counts'], {'fixed': 1, 'bath': 1, 'mobile_including_bath': 2})
            self.assertEqual(source.read_bytes(), original)
            with self.assertRaises(FileExistsError):
                prepare_package(config, root, root / 'package')

    def test_unsupported_mechanism_and_unresolved_science_not_guessed(self):
        self.assertFalse(readiness({'mechanism': None})['ready_for_local_preparation'])
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            config = package_fixture(root)
            config['mechanism'] = 'reactive_precursor'
            with self.assertRaises(ValueError):
                prepare_package(config, root, root / 'package')
            self.assertFalse((root / 'package').exists())

    def test_overlapping_groups_and_command_injection_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            config = package_fixture(root)
            config['bath_z_bounds_angstrom'] = [1, 2.5]
            with self.assertRaises(ValueError):
                prepare_package(config, root, root / 'overlap')
            config = package_fixture(root)
            config['potential']['pair_style'] = ['lj/cut\nshell', '2.5']
            with self.assertRaises(ValueError):
                prepare_package(config, root, root / 'injected')

    def test_existing_nep_file_is_copied_without_cropping_header(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            config = package_fixture(root)
            model = root / 'artificial-nep-header.txt'
            raw = b'nep4_zbl 3 Si C O\nzbl 1 2\nHeader-only software fixture, not usable weights.\n'
            model.write_bytes(raw)
            config['potential'].update(kind='pretrained-ml', format='nep', files=[str(model)],
                                       pair_style=['nep'], pair_coeff=[['*', '*', '@potential_file:0', 'Si', 'C']])
            result = prepare_package(config, root, root / 'package')
            self.assertEqual((root / 'package/models/potential-0.txt').read_bytes(), raw)
            self.assertEqual(result['potential_header_checks'][0]['element_count'], 3)
            self.assertEqual(result['potential_header_checks'][0]['scientific_suitability'], 'UNVERIFIED')
            self.assertFalse(result['simulation_run'])


if __name__ == '__main__':
    unittest.main()
