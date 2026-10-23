"""Prepare a literal atomic-beam candidate package; never launch LAMMPS."""
import argparse
import copy
import json
from pathlib import Path
import shutil

from common import print_receipt, utc_now
from local_common import identity, integer, json_file, load_config, new_directory, number, require, resolve_file
from structure_io import geometry_summary, read_structure, validate_order, write_structure

REQUIRED = ['purpose', 'provenance', 'mechanism', 'structure_file', 'structure_format', 'type_order',
            'boundary', 'minimum_separation_angstrom', 'potential', 'fixed_z_bounds_angstrom',
            'bath_z_bounds_angstrom', 'injection_bounds_angstrom', 'initial_temperature_K',
            'velocity_seed', 'thermostat_seed', 'thermostat_damping_ps', 'temperature_extra_dof',
            'timestep_ps', 'equilibrate_steps', 'deposition_steps', 'post_steps', 'beams',
            'thermo_every', 'dump_every', 'restart_every']


def readiness(config):
    missing = [key for key in REQUIRED if config.get(key) is None]
    potential = config.get('potential')
    if isinstance(potential, dict):
        missing += ['potential.' + key for key in ['kind', 'interface', 'provenance', 'files', 'pair_style', 'pair_coeff', 'type_order']
                    if potential.get(key) is None]
    elif potential is not None:
        missing.append('potential (must be an object)')
    return {'ready_for_local_preparation': not missing, 'unresolved_fields': missing,
            'scientific_confirmation_verified': False, 'execution_authorized': False}


def tokens(value, name):
    if not isinstance(value, list) or not value or any(not isinstance(word, str) or not word or
            any(c.isspace() or c in '#;\"\'`$&' for c in word) for word in value):
        raise ValueError(name + ' must be literal single-line tokens; expressions/control characters are unsupported.')
    return value


def ordered_bounds(value, name, length=2):
    if not isinstance(value, list) or len(value) != length:
        raise ValueError(name + ' needs ' + str(length) + ' finite numbers.')
    result = [number(item, name) for item in value]
    if any(result[i] >= result[i + 1] for i in range(0, length, 2)):
        raise ValueError(name + ' lower bounds must be strictly below upper bounds.')
    return result


def seed(value, name):
    result = integer(value, name, 1)
    if result > 899999999:
        raise ValueError(name + ' exceeds the conservative supported seed range.')
    return result


def prepare(config, base, output):
    import numpy as np
    state = readiness(config)
    if not state['ready_for_local_preparation']:
        raise ValueError('Unresolved fields: ' + ', '.join(state['unresolved_fields']))
    if config['purpose'] not in {'engineering_fixture', 'research_candidate'} or not str(config['provenance']).strip():
        raise ValueError('An explicit purpose and source/parameter provenance are required.')
    if config['mechanism'] != 'atomic_beam' or config['boundary'] != ['p', 'p', 'f']:
        raise ValueError('This renderer supports atomic beams and z-normal p p f only; reactive/molecular deposition is unsupported.')
    order = validate_order(config['type_order'])
    source = resolve_file(config['structure_file'], base)
    atoms = read_structure(source, config['structure_format'], order, config['boundary'])
    audit = geometry_summary(atoms, order, config['boundary'], config['minimum_separation_angstrom'])
    if not audit['geometry_checks_passed']:
        raise ValueError('Input structure failed geometric checks: ' + repr(audit['issues']))
    lengths = atoms.cell.lengths()
    if not np.allclose(atoms.cell.array, np.diag(lengths), atol=1e-9):
        raise ValueError('Atomic-beam renderer currently requires an axis-aligned orthogonal cell.')
    fixed = ordered_bounds(config['fixed_z_bounds_angstrom'], 'fixed_z_bounds_angstrom')
    bath = ordered_bounds(config['bath_z_bounds_angstrom'], 'bath_z_bounds_angstrom')
    if fixed[0] < 0 or fixed[1] > bath[0] or bath[1] > lengths[2]:
        raise ValueError('Fixed and bath ranges must be ordered inside the cell without a shared volume.')
    z = atoms.positions[:, 2]
    fixed_mask = (z >= fixed[0]) & (z <= fixed[1])
    bath_mask = (z >= bath[0]) & (z <= bath[1])
    if np.any(fixed_mask & bath_mask) or not fixed_mask.any() or not bath_mask.any() or fixed_mask.all():
        raise ValueError('Fixed and bath groups must be nonempty and disjoint, with mobile atoms remaining.')
    injection = ordered_bounds(config['injection_bounds_angstrom'], 'injection_bounds_angstrom', 6)
    for axis in range(3):
        if injection[2 * axis] < 0 or injection[2 * axis + 1] >= lengths[axis]:
            raise ValueError('Injection region must be strictly inside the declared box.')
    if injection[4] <= z.max():
        raise ValueError('This adapter requires injection above the initial structure.')
    temperature = number(config['initial_temperature_K'], 'initial_temperature_K', positive=True)
    damping = number(config['thermostat_damping_ps'], 'thermostat_damping_ps', positive=True)
    dt = number(config['timestep_ps'], 'timestep_ps', positive=True)
    dof = integer(config['temperature_extra_dof'], 'temperature_extra_dof')
    velocity_seed = seed(config['velocity_seed'], 'velocity_seed')
    bath_seed = seed(config['thermostat_seed'], 'thermostat_seed')
    stages = {key: integer(config[key], key, 1 if key == 'deposition_steps' else 0)
              for key in ['equilibrate_steps', 'deposition_steps', 'post_steps']}
    cadence = {key: integer(config[key], key, 1) for key in ['thermo_every', 'dump_every', 'restart_every']}
    potential = config['potential']
    if potential['kind'] not in {'empirical', 'pretrained-ml'} or potential['type_order'] != order:
        raise ValueError('Keep an explicit empirical/pretrained-ml route and matching potential type_order.')
    if not str(potential['interface']).strip() or not str(potential['provenance']).strip():
        raise ValueError('Record potential interface and provenance.')
    if not isinstance(potential['files'], list) or potential['kind'] == 'pretrained-ml' and not potential['files']:
        raise ValueError('List potential files explicitly; pretrained ML requires existing weights.')
    potential_paths = [resolve_file(value, base) for value in potential['files']]
    header_checks = []
    if potential.get('format') == 'nep':
        from inspect_potential import inspect_file
        for path in potential_paths:
            check = inspect_file(path, 'nep', order)
            if not all(check['required_element_coverage'].values()):
                raise ValueError('Existing NEP header does not cover the full input type_order.')
            header_checks.append(check)
    style = tokens(potential['pair_style'], 'potential.pair_style')
    if not isinstance(potential['pair_coeff'], list) or not potential['pair_coeff']:
        raise ValueError('Supply the documented pair_coeff token lists.')
    coefficient_rows = [tokens(row, 'potential.pair_coeff') for row in potential['pair_coeff']]
    substitutions = {'@potential_file:' + str(i): 'models/potential-' + str(i) + '.txt' for i in range(len(potential_paths))}
    def expand(row):
        for word in row:
            if word.startswith('@') and word not in substitutions:
                raise ValueError('Unknown potential-file placeholder: ' + word)
        return ' '.join(substitutions.get(word, word) for word in row)
    pair_lines = ['pair_style ' + expand(style)] + ['pair_coeff ' + expand(row) for row in coefficient_rows]
    beams = config['beams']
    if not isinstance(beams, list) or not beams:
        raise ValueError('Supply at least one explicit atomic beam.')
    beam_lines, beam_ids, expected = [], [], {}
    for i, beam in enumerate(beams):
        require(beam, ['element', 'count', 'every_steps', 'seed', 'near_angstrom', 'velocity_bounds_angstrom_per_ps'])
        if beam['element'] not in order:
            raise ValueError('Beam element is absent from type_order.')
        count = integer(beam['count'], 'beam.count', 1)
        interval = integer(beam['every_steps'], 'beam.every_steps', 1)
        near = number(beam['near_angstrom'], 'beam.near_angstrom', positive=True)
        velocity = beam['velocity_bounds_angstrom_per_ps']
        if not isinstance(velocity, list) or len(velocity) != 3 or any(not isinstance(pair, list) or len(pair) != 2 for pair in velocity):
            raise ValueError('Supply vx/vy/vz lower and upper velocity bounds.')
        for pair in velocity:
            for value in pair:
                number(value, 'beam velocity')
            if pair[0] > pair[1]:
                raise ValueError('Beam velocity bounds are reversed.')
        if velocity[2][1] >= 0:
            raise ValueError('This z-normal adapter requires downward beam velocities.')
        beam_id = 'source' + str(i + 1)
        beam_ids.append(beam_id)
        line = f'fix {beam_id} mobile deposit {count} {order.index(beam["element"]) + 1} {interval} {seed(beam["seed"], "beam.seed")} region injection near {near}'
        for axis, pair in zip(['vx', 'vy', 'vz'], velocity):
            line += f' {axis} {pair[0]} {pair[1]}'
        beam_lines.append(line + ' units box')
        expected[beam['element']] = expected.get(beam['element'], 0) + count
    lines = ['# PREPARED CANDIDATE ONLY: not engine/numerical/scientific validation or execution permission.',
             'units metal', 'atom_style atomic', 'boundary p p f', 'read_data structure.data',
             *pair_lines, f'timestep {dt}',
             f'region frozen block INF INF INF INF {fixed[0]} {fixed[1]} units box',
             f'region bathRegion block INF INF INF INF {bath[0]} {bath[1]} units box',
             'group frozen region frozen', 'group bath region bathRegion', 'group mobile subtract all frozen',
             'velocity frozen set 0.0 0.0 0.0',
             f'velocity mobile create {temperature} {velocity_seed} mom yes rot no dist gaussian',
             'fix hold frozen setforce 0.0 0.0 0.0', 'fix integrate mobile nve',
             f'compute mobileTemp mobile temp', f'compute_modify mobileTemp dynamic/dof yes extra/dof {dof}',
             'compute bathTemp bath temp', f'compute_modify bathTemp extra/dof {dof}',
             f'fix bathHeat bath langevin {temperature} {temperature} {damping} {bath_seed}',
             'fix_modify bathHeat temp bathTemp',
             'thermo_style custom step time atoms temp c_bathTemp pe ke etotal', 'thermo_modify temp mobileTemp',
             f'thermo {cadence["thermo_every"]}',
             f'dump trajectory all custom {cadence["dump_every"]} trajectory.dump id type x y z ix iy iz vx vy vz',
             'dump_modify trajectory sort id', f'restart {cadence["restart_every"]} restart.*']
    if stages['equilibrate_steps']:
        lines += ['# Initial thermalization stage', f'run {stages["equilibrate_steps"]}']
    lines += ['region injection block ' + ' '.join(map(str, injection)) + ' units box', *beam_lines,
              'thermo_style custom step time atoms temp c_bathTemp pe ke etotal ' + ' '.join('f_' + beam_id for beam_id in beam_ids),
              'thermo_modify temp mobileTemp',
              '# Deposition stage; fix scalars record cumulative successful atomic insertions.', f'run {stages["deposition_steps"]}']
    lines += ['print "CUMULATIVE_INSERTED ' + beam_id + ' $(' + 'f_' + beam_id + ')"' for beam_id in beam_ids]
    lines += ['thermo_style custom step time atoms temp c_bathTemp pe ke etotal', 'thermo_modify temp mobileTemp']
    lines += ['unfix ' + beam_id for beam_id in beam_ids]
    if stages['post_steps']:
        lines += ['# Post-deposition relaxation stage', f'run {stages["post_steps"]}']
    lines += ['write_data final.data', 'write_restart final.restart']
    output = new_directory(output)
    write_structure(output, atoms, order)
    (output / 'in.growth').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    copied = []
    if potential_paths:
        (output / 'models').mkdir()
    for i, source_path in enumerate(potential_paths):
        target = output / substitutions['@potential_file:' + str(i)]
        before = identity(source_path)
        shutil.copy2(source_path, target)
        copied_identity = identity(target)
        if before['sha256'] != copied_identity['sha256']:
            raise ValueError('Potential copy identity mismatch.')
        copied.append({'source': before, 'package_file': str(target.relative_to(output)), 'identity': copied_identity})
    json_file(output / 'type-map.json', {str(i + 1): symbol for i, symbol in enumerate(order)})
    portable = copy.deepcopy(config)
    portable['structure_file'] = 'structure.extxyz'
    portable['structure_format'] = 'extxyz'
    portable['potential']['files'] = [item['package_file'] for item in copied]
    json_file(output / 'configuration.json', portable)
    selected = ['in.growth', 'structure.data', 'structure.extxyz', 'type-map.json', 'configuration.json'] + [item['package_file'] for item in copied]
    report = {'prepared_utc': utc_now(), 'status': 'PREPARED_CANDIDATE_NOT_ENGINE_VALIDATED',
              'purpose': config['purpose'], 'mechanism': config['mechanism'], 'structure_source': identity(source),
              'geometry_audit': audit, 'potential': potential, 'potential_copies': copied, 'potential_header_checks': header_checks,
              'initial_group_counts': {'fixed': int(fixed_mask.sum()), 'bath': int(bath_mask.sum()), 'mobile_including_bath': int((~fixed_mask).sum())},
              'planned_insertions': expected, 'stages_steps': stages, 'nominal_stage_duration_ps': {key: value * dt for key, value in stages.items()},
              'package_files': selected, 'file_identities': [{**identity(output / name), 'package_file': name} for name in selected],
              'scientific_confirmation_verified': False, 'execution_authorized': False, 'simulation_run': False,
              'limitations': ['Fresh orthogonal atomic-beam candidate only; no precursor chemistry or general restart renderer.',
                              'Pair commands are explicit user-supplied interface contracts, not independently verified syntax/physics.',
                              'Incoming atoms join mobile via fix deposit; dynamic insertion, MPI, thermostat and restart behavior need engine tests.',
                              'No full scientific audit, energy/force inference, numerical or performance validation.']}
    json_file(output / 'package-manifest.json', report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', required=True)
    parser.add_argument('--output-directory')
    parser.add_argument('--check-only', action='store_true')
    parser.add_argument('--readiness-report')
    args = parser.parse_args()
    config, base = load_config(args.config)
    if args.check_only:
        state = readiness(config)
        if args.readiness_report:
            from common import write_report
            write_report(args.readiness_report, state)
        print(json.dumps(state, indent=2))
        raise SystemExit(0 if state['ready_for_local_preparation'] else 2)
    if not args.output_directory:
        parser.error('--output-directory is required unless --check-only is used')
    report = prepare(config, base, args.output_directory)
    print_receipt(args.output_directory, status=report['status'], execution_authorized=False)


if __name__ == '__main__':
    main()
