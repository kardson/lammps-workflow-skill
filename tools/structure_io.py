"""Explicit, atomic-only structure I/O and geometric checks using ASE."""
from collections import Counter
from pathlib import Path


def validate_order(order):
    from ase.data import atomic_numbers
    if not isinstance(order, list) or not order or len(set(order)) != len(order):
        raise ValueError('type_order must be a nonempty, unique list of element symbols.')
    if any(symbol not in atomic_numbers or symbol == 'X' for symbol in order):
        raise ValueError('Unknown chemical symbol in type_order.')
    return order


def read_structure(path, file_format, order, boundary):
    from ase.data import atomic_numbers
    from ase.io import read
    import numpy as np
    validate_order(order)
    if file_format not in {'extxyz', 'cif', 'lammps-data'}:
        raise ValueError('Supported formats: extxyz, cif and atomic LAMMPS data only.')
    if not isinstance(boundary, list) or len(boundary) != 3 or any(item not in {'p', 'f', 's', 'm'} for item in boundary):
        raise ValueError('Supply all three explicit LAMMPS boundary tokens.')
    if file_format == 'lammps-data':
        atoms = read(path, format=file_format, atom_style='atomic', units='metal',
                     Z_of_type={i + 1: atomic_numbers[symbol] for i, symbol in enumerate(order)})
    else:
        atoms = read(path, format=file_format, index=0)
    requested_pbc = np.array([token == 'p' for token in boundary])
    if file_format == 'extxyz' and not np.array_equal(atoms.pbc, requested_pbc):
        raise ValueError('Explicit boundary disagrees with extxyz periodic flags.')
    atoms.pbc = requested_pbc
    if set(atoms.get_chemical_symbols()) - set(order):
        raise ValueError('Structure species are missing from explicit type_order.')
    if 'lammps_type' in atoms.arrays:
        expected = np.array([order.index(symbol) + 1 for symbol in atoms.get_chemical_symbols()])
        if not np.array_equal(atoms.arrays['lammps_type'], expected):
            raise ValueError('Embedded lammps_type labels disagree with explicit element mapping.')
    if file_format == 'lammps-data':
        types = atoms.arrays.get('type')
        if types is not None and (np.any(types < 1) or np.any(types > len(order))):
            raise ValueError('LAMMPS atom type lies outside the supplied mapping.')
    return atoms


def geometry_summary(atoms, order, boundary, minimum_separation):
    import numpy as np
    from ase.neighborlist import neighbor_list
    from local_common import number
    validate_order(order)
    cutoff = number(minimum_separation, 'minimum_separation_angstrom', positive=True)
    issues = []
    positions = np.asarray(atoms.positions)
    cell = np.asarray(atoms.cell)
    valid = len(atoms) > 0 and np.isfinite(positions).all() and np.isfinite(cell).all() and np.linalg.det(cell) > 0
    if not valid:
        issues.append('Need nonempty finite coordinates and a right-handed full-rank cell.')
    missing = sorted(set(atoms.get_chemical_symbols()) - set(order))
    if missing:
        issues.append('Elements outside explicit type_order: ' + repr(missing))
    masses = atoms.get_masses()
    if not np.isfinite(masses).all() or np.any(masses <= 0):
        issues.append('Masses must be finite and positive.')
    close_count, examples = 0, []
    out_of_bounds = {}
    if valid:
        scaled = atoms.get_scaled_positions(wrap=False)
        for axis, token in enumerate(boundary):
            if token != 'p':
                selected = np.flatnonzero((scaled[:, axis] < -1e-9) | (scaled[:, axis] > 1 + 1e-9))
                if len(selected):
                    out_of_bounds[str(axis)] = {'count': len(selected), 'indices_first_20': selected[:20].tolist()}
        if out_of_bounds:
            issues.append('Atoms lie outside a declared nonperiodic cell direction.')
        # Reject a huge cutoff relative to the cell before allocating neighbor images.
        if cutoff > min(atoms.cell.lengths()):
            raise ValueError('Minimum-separation threshold exceeds a cell length; choose an appropriate explicit threshold.')
        i_values, j_values, shifts, distances = neighbor_list('ijSd', atoms, cutoff, self_interaction=False)
        for i, j, shift, distance in zip(i_values, j_values, shifts, distances):
            forward = (int(i), int(j), *map(int, shift))
            reverse = (int(j), int(i), *map(int, -shift))
            if forward > reverse:
                continue
            close_count += 1
            if len(examples) < 20:
                examples.append({'indices_zero_based': [int(i), int(j)], 'image_shift': shift.tolist(),
                                 'distance_angstrom': float(distance)})
        if close_count:
            issues.append('Pairs closer than the user-supplied minimum separation were found.')
    return {'atom_count': len(atoms), 'composition': dict(Counter(atoms.get_chemical_symbols())),
            'cell_angstrom': cell.tolist(), 'boundary': boundary, 'type_order': order,
            'minimum_separation_angstrom': cutoff, 'close_pair_count': close_count,
            'close_pairs_first_20': examples, 'nonperiodic_out_of_bounds': out_of_bounds,
            'geometry_checks_passed': not issues, 'issues': issues,
            'scope': 'Geometry and explicit mapping only; no energy, stability, surface chemistry or potential applicability validation.'}


def write_structure(output, atoms, order):
    from ase.io import write
    import numpy as np
    output = Path(output)
    cell = atoms.cell.array
    if not np.allclose(cell[np.triu_indices(3, 1)], 0, atol=1e-9) or np.any(np.diag(cell) <= 0):
        raise ValueError('Explicitly orient the cell in restricted lower-triangular LAMMPS form before export; no silent coordinate rotation is performed.')
    atoms.set_array('lammps_type', np.array([order.index(symbol) + 1 for symbol in atoms.get_chemical_symbols()], dtype=int))
    write(output / 'structure.extxyz', atoms, format='extxyz')
    write(output / 'structure.data', atoms, format='lammps-data', specorder=order,
          atom_style='atomic', masses=True, units='metal', write_image_flags=False)
