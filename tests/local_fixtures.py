"""Artificial values for software tests only, never physical reference data."""
from pathlib import Path


def package_fixture(root):
    from ase import Atoms
    from ase.io import write
    root = Path(root)
    source = root / 'artificial.extxyz'
    atoms = Atoms(['Si', 'Si', 'C'], positions=[[1, 1, 1], [4, 1, 2], [7, 7, 3]], cell=[10, 10, 12], pbc=[True, True, False])
    write(source, atoms, format='extxyz')
    return {'purpose': 'engineering_fixture', 'provenance': 'Artificial fixture; no material claim.',
            'mechanism': 'atomic_beam', 'structure_file': str(source), 'structure_format': 'extxyz',
            'type_order': ['Si', 'C'], 'boundary': ['p', 'p', 'f'], 'minimum_separation_angstrom': 0.2,
            'potential': {'kind': 'empirical', 'interface': 'artificial LJ contract', 'provenance': 'Synthetic tokens, not semiconductor parameters.',
                          'files': [], 'pair_style': ['lj/cut', '2.5'], 'pair_coeff': [['*', '*', '1.0', '1.0']], 'type_order': ['Si', 'C']},
            'fixed_z_bounds_angstrom': [0, 1.5], 'bath_z_bounds_angstrom': [1.5, 2.5],
            'injection_bounds_angstrom': [1, 9, 1, 9, 8, 10], 'initial_temperature_K': 300,
            'velocity_seed': 12457, 'thermostat_seed': 34567, 'thermostat_damping_ps': 0.1,
            'temperature_extra_dof': 0, 'timestep_ps': 0.001, 'equilibrate_steps': 10, 'deposition_steps': 20,
            'post_steps': 10, 'beams': [{'element': 'C', 'count': 2, 'every_steps': 5, 'seed': 12345,
                                     'near_angstrom': 0.5, 'velocity_bounds_angstrom_per_ps': [[0, 0], [0, 0], [-1, -1]]}],
            'thermo_every': 5, 'dump_every': 5, 'restart_every': 10}


def trajectory_config():
    return {'source_class': 'engineering_fixture', 'units': 'metal', 'type_order': ['Si', 'C'],
            'film_elements': ['C'], 'z_window_angstrom': [1, 9], 'reference_z_angstrom': 1,
            'height_quantile': 1.0, 'height_grid': [2, 1], 'empty_cell_policy': 'exclude',
            'composition_z_edges_angstrom': [0, 2, 4, 8, 10], 'max_atoms_per_frame': 100}


def dump_frame(step, rows, scaled=False):
    header = ['ITEM: TIMESTEP', str(step), 'ITEM: NUMBER OF ATOMS', str(len(rows)),
              'ITEM: BOX BOUNDS pp pp ff', '0 2', '0 1', '0 10',
              'ITEM: ATOMS id type ' + ('xs ys zs' if scaled else 'x y z')]
    return '\n'.join(header + [' '.join(map(str, row)) for row in rows]) + '\n'
