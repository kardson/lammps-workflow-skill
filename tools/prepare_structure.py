"""Generate explicit bulk/slab/interface candidates with ASE; no relaxation."""
import argparse
from collections import Counter

from common import print_receipt, utc_now
from local_common import identity, integer, json_file, load_config, new_directory, number, require, resolve_file
from structure_io import geometry_summary, read_structure, validate_order, write_structure


def repeat_vector(value):
    if not isinstance(value, list) or len(value) != 3:
        raise ValueError('repeat must contain three positive integers.')
    return [integer(item, 'repeat', 1) for item in value]


def plane_groups(z_values, tolerance):
    import numpy as np
    groups = []
    for i in np.argsort(z_values):
        if not groups or z_values[i] - z_values[groups[-1][0]] > tolerance:
            groups.append([int(i)])
        else:
            groups[-1].append(int(i))
    return groups


def build(config, base):
    import numpy as np
    from ase.build import bulk, surface
    require(config, ['operation', 'purpose', 'provenance', 'type_order', 'boundary', 'minimum_separation_angstrom'])
    if config['purpose'] not in {'engineering_fixture', 'research_candidate'}:
        raise ValueError('Set purpose explicitly to engineering_fixture or research_candidate.')
    if not isinstance(config['provenance'], str) or not config['provenance'].strip():
        raise ValueError('Record source/parameter provenance explicitly.')
    order = validate_order(config['type_order'])
    boundary = config['boundary']
    if boundary not in [['p', 'p', 'p'], ['p', 'p', 'f']]:
        raise ValueError('Generated candidates support explicit p p p bulk or p p f z-normal surfaces only.')
    operation = config['operation']
    sources, construction = [], {}
    if operation == 'bulk_zincblende':
        require(config, ['elements', 'lattice_a_angstrom', 'repeat'])
        elements = validate_order(config['elements'])
        if len(elements) != 2 or boundary != ['p', 'p', 'p']:
            raise ValueError('Zincblende requires two explicitly ordered elements and p p p.')
        lattice_a = number(config['lattice_a_angstrom'], 'lattice_a_angstrom', positive=True)
        atoms = bulk(''.join(elements), crystalstructure='zincblende', a=lattice_a, cubic=True)
        atoms = atoms.repeat(repeat_vector(config['repeat']))
        construction = {'basis': 'ASE cubic zincblende, ordered elements as supplied', 'lattice_a_angstrom': lattice_a}
    elif operation in {'import', 'slab'}:
        require(config, ['source_file', 'source_format', 'source_boundary'])
        source = resolve_file(config['source_file'], base)
        atoms = read_structure(source, config['source_format'], order, config['source_boundary'])
        sources.append(identity(source))
        if operation == 'slab':
            require(config, ['miller', 'layers', 'repeat', 'trim_bottom_planes', 'trim_top_planes',
                             'plane_tolerance_angstrom', 'bottom_buffer_angstrom', 'vacuum_above_angstrom', 'termination_label'])
            miller = config['miller']
            if not isinstance(miller, list) or len(miller) != 3 or any(isinstance(x, bool) or not isinstance(x, int) for x in miller) or not any(miller):
                raise ValueError('Supply three integer Miller indices, not all zero.')
            if boundary != ['p', 'p', 'f'] or config['source_boundary'] != ['p', 'p', 'p']:
                raise ValueError('Slab source must be a conventional periodic bulk; output is p p f.')
            repeat = repeat_vector(config['repeat'])
            if repeat[2] != 1:
                raise ValueError('Use layers for slab thickness; repeat[2] must be 1.')
            atoms = surface(atoms, miller, integer(config['layers'], 'layers', 1), vacuum=None, periodic=False).repeat(repeat)
            tolerance = number(config['plane_tolerance_angstrom'], 'plane_tolerance_angstrom', positive=True)
            groups = plane_groups(atoms.positions[:, 2], tolerance)
            bottom = integer(config['trim_bottom_planes'], 'trim_bottom_planes')
            top = integer(config['trim_top_planes'], 'trim_top_planes')
            if bottom + top >= len(groups):
                raise ValueError('Plane trimming would remove the complete slab.')
            keep = [i for group in groups[bottom:len(groups) - top if top else None] for i in group]
            atoms = atoms[sorted(keep)]
            height = float(np.ptp(atoms.positions[:, 2]))
            buffer = number(config['bottom_buffer_angstrom'], 'bottom_buffer_angstrom', nonnegative=True)
            vacuum = number(config['vacuum_above_angstrom'], 'vacuum_above_angstrom', positive=True)
            atoms.positions[:, 2] += buffer - atoms.positions[:, 2].min()
            cell = atoms.cell.array.copy()
            cell[2] = [0, 0, height + buffer + vacuum]
            atoms.set_cell(cell)
            observed = plane_groups(atoms.positions[:, 2], tolerance)
            construction = {'miller': miller, 'layers': config['layers'], 'termination_label': config['termination_label'],
                            'observed_bottom_plane': dict(Counter(atoms[i].symbol for i in observed[0])),
                            'observed_top_plane': dict(Counter(atoms[i].symbol for i in observed[-1])),
                            'note': 'Unrelaxed cut/trim; no reconstruction, passivation or surface-energy selection.'}
            target = config.get('expected_top_elements')
            if target is not None and sorted(target) != sorted(construction['observed_top_plane']):
                raise ValueError('Observed top-plane species do not match the explicitly requested termination.')
        elif [token == 'p' for token in boundary] != list(atoms.pbc):
            raise ValueError('Import boundary must agree with the explicitly read structure.')
    elif operation == 'interface':
        require(config, ['substrate_file', 'film_file', 'source_format', 'lateral_match', 'gap_angstrom',
                         'bottom_buffer_angstrom', 'vacuum_above_angstrom', 'film_xy_shift_angstrom'])
        if boundary != ['p', 'p', 'f'] or config['lateral_match'] != 'strain_film_to_substrate':
            raise ValueError('This adapter requires z-normal p p f and explicit strain_film_to_substrate.')
        paths = [resolve_file(config[key], base) for key in ['substrate_file', 'film_file']]
        substrate, film = [read_structure(path, config['source_format'], order, boundary) for path in paths]
        sources = [identity(path) for path in paths]
        for item in [substrate, film]:
            if not np.allclose(item.cell.array, np.diag(item.cell.lengths()), atol=1e-9):
                raise ValueError('Interface adapter currently supports axis-aligned orthogonal slabs only.')
        old_xy = film.cell.lengths()[:2].copy()
        cell = film.cell.array.copy()
        cell[:2] = substrate.cell.array[:2]
        film.set_cell(cell, scale_atoms=True)
        shift = config['film_xy_shift_angstrom']
        if not isinstance(shift, list) or len(shift) != 2:
            raise ValueError('Supply two explicit lateral shift values.')
        for value in shift:
            number(value, 'film_xy_shift_angstrom')
        film.positions[:, :2] += shift
        buffer = number(config['bottom_buffer_angstrom'], 'bottom_buffer_angstrom', nonnegative=True)
        gap = number(config['gap_angstrom'], 'gap_angstrom', positive=True)
        vacuum = number(config['vacuum_above_angstrom'], 'vacuum_above_angstrom', positive=True)
        substrate.positions[:, 2] += buffer - substrate.positions[:, 2].min()
        film.positions[:, 2] += substrate.positions[:, 2].max() + gap - film.positions[:, 2].min()
        atoms = substrate + film
        cell = substrate.cell.array.copy()
        cell[2] = [0, 0, float(atoms.positions[:, 2].max()) + vacuum]
        atoms.set_cell(cell)
        construction = {'film_lateral_strain': (substrate.cell.lengths()[:2] / old_xy - 1).tolist(),
                        'lateral_match': config['lateral_match'], 'substrate_atom_count': len(substrate),
                        'film_atom_count': len(film), 'gap_angstrom': gap,
                        'note': 'Unrelaxed stacked candidate; strain/registry and chemistry require scientific review.'}
    else:
        raise ValueError('Supported operations: bulk_zincblende, import, slab, interface.')
    atoms.pbc = [token == 'p' for token in boundary]
    atoms.wrap()
    atoms.info.update(purpose=config['purpose'], provenance=config['provenance'])
    audit = geometry_summary(atoms, order, boundary, config['minimum_separation_angstrom'])
    if not audit['geometry_checks_passed']:
        raise ValueError('Generated structure failed geometric checks: ' + repr(audit['issues']))
    return atoms, {'construction': construction, 'sources': sources, 'audit': audit}


def prepare(config, base, output):
    atoms, details = build(config, base)
    output = new_directory(output)
    write_structure(output, atoms, config['type_order'])
    report = {'prepared_utc': utc_now(), 'status': 'UNRELAXED_CANDIDATE', 'purpose': config['purpose'],
              'configuration': config, **details, 'calculator_used': False,
              'scientific_acceptance': 'UNVERIFIED', 'execution_authorized': False,
              'outputs': [identity(output / name) for name in ['structure.extxyz', 'structure.data']]}
    json_file(output / 'structure-manifest.json', report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', required=True)
    parser.add_argument('--output-directory', required=True)
    args = parser.parse_args()
    config, base = load_config(args.config)
    report = prepare(config, base, args.output_directory)
    print_receipt(args.output_directory, atom_count=report['audit']['atom_count'], status=report['status'])


if __name__ == '__main__':
    main()
