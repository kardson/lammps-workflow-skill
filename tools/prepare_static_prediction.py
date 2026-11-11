"""Prepare an orthogonal/restricted-triclinic run-0 candidate; no inference."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil

from lammps_prediction import configuration_identity
from local_common import identity, json_file, load_config, new_directory, number, resolve_file
from prepare_input_package import tokens
from restricted_cell import cell_values, fractional


def validate_configuration(configuration, type_order, masses, maximum_atoms):
    species, ids = configuration['species'], configuration['atom_ids']
    if type(maximum_atoms) is not int or maximum_atoms < 1 or not isinstance(species, list) or not 0 < len(species) <= maximum_atoms:
        raise ValueError('Explicit positive atom bound and nonempty bounded configuration required')
    if not isinstance(type_order, list) or not type_order or any(not isinstance(symbol, str) or not re.fullmatch('[A-Z][a-z]?', symbol) for symbol in type_order) or len(set(type_order)) != len(type_order):
        raise ValueError('Explicit unique element type order required')
    if set(species) - set(type_order) or len(ids) != len(species) or len(set(ids)) != len(ids) or any(type(key) is not int or key <= 0 or key > 2147483647 for key in ids):
        raise ValueError('Species coverage/atom IDs invalid for this atomic adapter')
    if not isinstance(masses, dict) or set(masses) != set(type_order):
        raise ValueError('Explicit masses required for every declared type')
    for symbol in type_order:
        number(masses[symbol], 'mass ' + symbol, positive=True)
    bounds, tilt = cell_values(configuration)
    boundary = configuration['boundary']
    if not isinstance(boundary, list) or len(boundary) != 3 or any(flag not in ('pp', 'ff') for flag in boundary):
        raise ValueError('Static preparation supports fixed p/f boundaries only')
    positions = configuration['positions_angstrom']
    if len(positions) != len(species):
        raise ValueError('Position/species dimensions differ')
    for position in positions:
        if len(position) != 3:
            raise ValueError('Three Cartesian coordinates required')
        for value, flag in zip(fractional(position, bounds, tilt), boundary):
            if value < 0 or value > 1 or flag == 'pp' and value == 1:
                raise ValueError('Position outside box or on periodic upper face; no automatic wrapping')
    return configuration_identity(configuration)


def prepare(config, base, output):
    if config.get('schema_version') != 1 or config.get('record_type') != 'static_prediction_plan':
        raise ValueError('Expected v1 static_prediction_plan')
    if not isinstance(config.get('id'), str) or not config['id'] or not config.get('provenance'):
        raise ValueError('Explicit sample ID and provenance required')
    if config.get('source_class') not in ('artificial_fixture', 'research_candidate', 'reviewed_reference'):
        raise ValueError('Explicit structure source_class required')
    configuration = config['configuration']
    potential = config['potential']
    if potential.get('kind') not in ('empirical', 'pretrained_ml') or not potential.get('provenance'):
        raise ValueError('Existing empirical/pretrained potential provenance required')
    order = potential['type_order']
    digest = validate_configuration(configuration, order, config['masses_amu'], config['maximum_atoms'])
    if config.get('configuration_sha256') != digest:
        raise ValueError('Configuration does not match declared identity')
    pair_style = tokens(potential['pair_style'], 'pair_style')
    pair_coeff = [tokens(row, 'pair_coeff') for row in potential['pair_coeff']]
    if not pair_coeff:
        raise ValueError('Explicit pair coefficients required; no inferred mixing')
    profile_file = resolve_file(config['engine_profile_file'], base)
    profile_identity = identity(profile_file)
    profile = json.loads(profile_file.read_text(encoding='utf-8-sig'))
    if profile.get('schema_version') != 1 or profile.get('record_type') != 'engine_profile' or not profile.get('id'):
        raise ValueError('Explicit v1 engine profile snapshot required')
    sources, destinations = [], set()
    for item in potential['files']:
        target = item['target']
        if not isinstance(target, str) or not re.fullmatch('[A-Za-z0-9][A-Za-z0-9_.-]*', target) or target in destinations or target in ('in.static', 'structure.data', 'engine-profile.json', 'preparation.json', 'plan.json', 'log.lammps', 'final.dump', 'stdout.log', 'stderr.log', 'termination.json', 'startup.json', 'launch-request.json', 'request.json', 'case.json'):
            raise ValueError('Unique portable potential filename required')
        destinations.add(target)
        path = resolve_file(item['source'], base)
        observed = identity(path)
        if observed['bytes'] > 64 * 1024 * 1024 or observed['sha256'] != item['sha256']:
            raise ValueError('Potential identity mismatch or exceeds 64 MiB static adapter bound')
        sources.append((path, target, observed))
    directory = new_directory(output)
    for path, target, observed in sources:
        shutil.copyfile(path, directory / target)
        if identity(directory / target)['sha256'] != observed['sha256']:
            raise ValueError('Copied potential identity mismatch; partial package retained')
    shutil.copyfile(profile_file, directory / 'engine-profile.json')
    if identity(directory / 'engine-profile.json')['sha256'] != profile_identity['sha256']:
        raise ValueError('Engine profile changed while copying')
    data = ['Static prediction candidate; no execution authorization', '', f"{len(configuration['species'])} atoms",
            f'{len(order)} atom types', '']
    data += [f'{float(row[0]):.17g} {float(row[1]):.17g} {axis}lo {axis}hi' for row, axis in zip(configuration['bounds_angstrom'], 'xyz')]
    if 'tilt_angstrom' in configuration:
        data += [' '.join(f'{x:.17g}' for x in cell_values(configuration)[1]) + ' xy xz yz']
    data += ['', 'Masses', ''] + [f'{i + 1} {float(config["masses_amu"][symbol]):.17g}' for i, symbol in enumerate(order)]
    data += ['', 'Atoms # atomic', '']
    data += [' '.join([str(key), str(order.index(symbol) + 1), *(f'{float(x):.17g}' for x in position)])
             for key, symbol, position in zip(configuration['atom_ids'], configuration['species'], configuration['positions_angstrom'])]
    (directory / 'structure.data').write_text('\n'.join(data) + '\n', encoding='utf-8')
    # Verify serialized atom order/types/positions before calling the candidate prepared.
    atom_lines = (directory / 'structure.data').read_text().split('Atoms # atomic\n', 1)[1].split()
    recovered = [atom_lines[i:i + 5] for i in range(0, len(atom_lines), 5)]
    if len(recovered) != len(configuration['species']) or any(len(row) != 5 or int(row[0]) != key or int(row[1]) != order.index(symbol) + 1 or [float(x) for x in row[2:]] != [float(x) for x in position]
           for row, key, symbol, position in zip(recovered, configuration['atom_ids'], configuration['species'], configuration['positions_angstrom'])):
        raise ValueError('Static structure serialization mismatch')
    commands = ['units metal', 'atom_style atomic', 'boundary ' + ' '.join(flag[0] for flag in configuration['boundary']),
                'read_data structure.data', 'pair_style ' + ' '.join(pair_style)]
    commands += ['pair_coeff ' + ' '.join(row) for row in pair_coeff]
    commands += ['reset_timestep 0', 'thermo 1', 'thermo_style custom step atoms pe',
                 'thermo_modify format float %.17g', 'run 0',
                 'write_dump all custom final.dump id type x y z fx fy fz modify sort id format float %.17g']
    (directory / 'in.static').write_text('\n'.join(commands) + '\n', encoding='utf-8')
    json_file(directory / 'plan.json', config)
    unresolved_engine = [key for key, value in {'lammps_version': profile.get('lammps_version'),
        'interface_revision': profile.get('interface', {}).get('revision'), 'precision': profile.get('precision')}.items()
        if not isinstance(value, str) or not value]
    report = {'schema_version': 1, 'record_type': 'static_prediction_preparation', 'id': config['id'],
              'status': 'CANDIDATE_PREPARED_NOT_EXECUTED', 'configuration_sha256': digest,
              'source_class': config['source_class'],
              'configuration': configuration, 'type_order': order, 'engine_profile': profile_identity,
              'potential_kind': potential['kind'], 'potential_sources': [item[2] for item in sources],
              'files': [{'file': path.name, **identity(path)} for path in sorted(directory.iterdir())],
              'expected_outputs': ['log.lammps', 'final.dump', 'termination.json'], 'expected_step': 0,
              'unresolved_engine_identity_fields': unresolved_engine,
              'scientific_acceptance': 'UNVERIFIED', 'execution_authorized': False,
              'inference_performed': False, 'limits': ['Orthogonal/restricted-triclinic atomic fixed p/f boxes only; supplied Cartesian frame is preserved',
              'Pair syntax supplied explicitly, not proven compatible or physically valid',
              'No energy reference alignment or stress conversion', 'Execution uses a separately authorized engine attempt']}
    json_file(directory / 'preparation.json', report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', required=True)
    parser.add_argument('--output-directory', required=True)
    args = parser.parse_args()
    try:
        config, base = load_config(args.config)
        report = prepare(config, base, args.output_directory)
    except (OSError, ValueError, KeyError, TypeError) as error:
        print(json.dumps({'status': 'ERROR', 'message': str(error), 'inference_performed': False}))
        return 2
    print(json.dumps({'status': report['status'], 'configuration_sha256': report['configuration_sha256'], 'inference_performed': False}))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
