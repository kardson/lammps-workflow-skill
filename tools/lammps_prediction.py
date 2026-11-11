"""Import identified static LAMMPS metal-unit outputs; no process launch."""
import hashlib
import json
import math
from pathlib import Path
import shlex

from local_common import identity
from parse_log import parse_log
from restricted_cell import cell_values


def configuration_identity(configuration):
    canonical = {'species': configuration['species'], 'atom_ids': configuration['atom_ids'],
                 'boundary': configuration['boundary'],
                 'bounds_angstrom': [[float(x) for x in row] for row in configuration['bounds_angstrom']],
                 'positions_angstrom': [[float(x) for x in row] for row in configuration['positions_angstrom']]}
    if 'tilt_angstrom' in configuration:
        canonical['tilt_angstrom'] = cell_values(configuration)[1]
    raw = json.dumps(canonical, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()
    return hashlib.sha256(raw).hexdigest()


def static_dump(path, maximum_atoms):
    """One orthogonal/restricted-triclinic Cartesian force frame by atom ID."""
    if type(maximum_atoms) is not int or maximum_atoms < 1:
        raise ValueError('Positive integer atom budget required')
    with Path(path).open(encoding='utf-8') as stream:
        def line():
            text = stream.readline()
            if not text:
                raise ValueError('Truncated static prediction dump')
            return text.strip()
        if line() != 'ITEM: TIMESTEP':
            raise ValueError('Static dump timestep section missing')
        step = int(line())
        if line() != 'ITEM: NUMBER OF ATOMS':
            raise ValueError('Static dump atom count section missing')
        count = int(line())
        if not 0 < count <= maximum_atoms:
            raise ValueError('Static prediction atom count exceeds explicit bound or is empty')
        box = line().split()
        triclinic = len(box) == 9 and box[:6] == ['ITEM:', 'BOX', 'BOUNDS', 'xy', 'xz', 'yz']
        orthogonal = len(box) == 6 and box[:3] == ['ITEM:', 'BOX', 'BOUNDS']
        if not (orthogonal or triclinic):
            raise ValueError('Only orthogonal or restricted-triclinic static dump boxes supported')
        flags = box[6:] if triclinic else box[3:]
        if any(flag not in ('pp', 'ff', 'ss', 'mm', 'fs', 'sf', 'fm', 'mf', 'sm', 'ms') for flag in flags):
            raise ValueError('Invalid static boundary flags')
        bounds = [[float(x) for x in line().split()] for _ in range(3)]
        if any(len(row) != (3 if triclinic else 2) or not all(math.isfinite(x) for x in row) or row[0] >= row[1] for row in bounds):
            raise ValueError('Invalid static prediction box')
        tilt = [row[2] for row in bounds] if triclinic else [0.0, 0.0, 0.0]
        if triclinic:
            xy, xz, yz = tilt
            bounds = [[bounds[0][0] - min(0.0, xy, xz, xy + xz),
                       bounds[0][1] - max(0.0, xy, xz, xy + xz)],
                      [bounds[1][0] - min(0.0, yz), bounds[1][1] - max(0.0, yz)],
                      bounds[2][:2]]
        bounds, tilt = cell_values({'bounds_angstrom': bounds, 'tilt_angstrom': tilt})
        header = line().split()
        if header[:2] != ['ITEM:', 'ATOMS']:
            raise ValueError('Static dump atom section missing')
        columns = header[2:]
        required = ('id', 'type', 'x', 'y', 'z', 'fx', 'fy', 'fz')
        if len(columns) != len(set(columns)) or not all(name in columns for name in required):
            raise ValueError('Explicit unique ID/type/Cartesian position/force columns required')
        atoms = {}
        for _ in range(count):
            values = line().split()
            if len(values) != len(columns):
                raise ValueError('Malformed static dump row')
            row = dict(zip(columns, values))
            key, atom_type = int(row['id']), int(row['type'])
            position = [float(row[x]) for x in ('x', 'y', 'z')]
            force = [float(row[x]) for x in ('fx', 'fy', 'fz')]
            if key <= 0 or key in atoms or atom_type <= 0 or not all(math.isfinite(x) for x in position + force):
                raise ValueError('Invalid/duplicate atom identity or nonfinite prediction')
            atoms[key] = {'type': atom_type, 'position': position, 'force': force}
        if stream.read().strip():
            raise ValueError('Multiple frames/trailing data unsupported for static prediction')
    return {'step': step, 'bounds': bounds, 'tilt_angstrom': tilt, 'boundary': flags, 'atoms': atoms}


def import_sample(sample, base):
    output = {'id': sample.get('id'), 'status': 'FAILED'}
    provenance = []
    try:
        files = {}
        for role in ('input', 'log', 'dump', 'execution'):
            item = sample['artifacts'][role]
            path = Path(item['path'])
            path = path if path.is_absolute() else Path(base) / path
            if path.stat().st_size > 64 * 1024 * 1024:
                raise ValueError('Static artifact exceeds 64 MiB bound')
            observed = identity(path)
            if observed['sha256'] != item['sha256']:
                raise ValueError('Prediction artifact identity mismatch: ' + role)
            provenance.append(observed)
            files[role] = path
        text = files['input'].read_text(encoding='utf-8-sig')
        commands = [shlex.split(line, comments=True) for line in text.splitlines()]
        if [row for row in commands if row and row[0] == 'units'] != [['units', 'metal']]:
            raise ValueError('Exactly one literal units metal declaration required')
        if any(row and row[0] in ('include', 'jump', 'clear') for row in commands):
            raise ValueError('Dynamic input layout unsupported for static unit audit')
        execution = json.loads(files['execution'].read_text(encoding='utf-8-sig'))
        pointer = sample['artifacts']['execution'].get('pointer', '')
        if pointer and not pointer.startswith('/'):
            raise ValueError('Execution JSON pointer must start with slash')
        for token in pointer[1:].split('/') if pointer else []:
            token = token.replace('~1', '/').replace('~0', '~')
            execution = execution[int(token)] if isinstance(execution, list) else execution[token]
        if type(execution.get('exit_code')) is not int or execution['exit_code'] != 0:
            raise ValueError('Successful actual execution exit evidence required')
        configuration = sample['configuration']
        if configuration_identity(configuration) != sample['configuration_sha256']:
            raise ValueError('Requested configuration identity mismatch')
        expected_bounds, expected_tilt = cell_values(configuration)
        count = len(configuration['species'])
        ids = configuration['atom_ids']
        if len(ids) != count or len(set(ids)) != count or any(type(key) is not int or key <= 0 for key in ids):
            raise ValueError('Explicit unique positive atom IDs required')
        if len(configuration['positions_angstrom']) != count or len(configuration['bounds_angstrom']) != 3:
            raise ValueError('Requested configuration dimensions invalid')
        frame = static_dump(files['dump'], sample['maximum_atoms'])
        if type(sample['expected_step']) is not int or set(frame['atoms']) != set(ids) or frame['step'] != sample['expected_step']:
            raise ValueError('Dump atom IDs or step differ from static request')
        if frame['boundary'] != configuration['boundary']:
            raise ValueError('Prediction boundary differs from requested configuration')
        tolerance = sample['geometry_tolerance_angstrom']
        if type(tolerance) not in (int, float) or not math.isfinite(tolerance) or not 0 <= tolerance <= 1e-5:
            raise ValueError('Explicit bounded geometry tolerance required (0 through 1e-5 angstrom)')
        def close(observed, expected):
            return len(observed) == len(expected) and all(math.isfinite(float(x)) and abs(a - float(x)) <= tolerance for a, x in zip(observed, expected))
        if any(not close(row, expected) for row, expected in zip(frame['bounds'], expected_bounds)) or not close(frame['tilt_angstrom'], expected_tilt):
            raise ValueError('Prediction cell differs from requested structure')
        order = sample['type_order']
        if not isinstance(order, list) or not order or len(set(order)) != len(order):
            raise ValueError('Explicit unique type-to-element order required')
        forces = []
        for key, symbol, position in zip(ids, configuration['species'], configuration['positions_angstrom']):
            atom = frame['atoms'][key]
            if atom['type'] > len(order) or order[atom['type'] - 1] != symbol or not close(atom['position'], position):
                raise ValueError('Prediction species/order/geometry differs from requested structure')
            forces.append(atom['force'])
        log = parse_log(files['log'])
        if log['parse_scope'] != 'PARSED_SINGLE_LINE_THERMO' or log['error_count'] or log['nonfinite_values']:
            raise ValueError('Prediction thermo incomplete or invalid')
        block = log['thermo_blocks'][-1]
        final = block['last']['values']
        if block['following_loop_line'] is None or final.get('Step') != frame['step'] or final.get('Atoms') != count:
            raise ValueError('Prediction thermo step/atom count or loop marker mismatch')
        energy = final.get('PotEng')
        if type(energy) not in (int, float) or not math.isfinite(energy):
            raise ValueError('Explicit finite PotEng thermo column required')
        for role, path in files.items():
            if identity(path)['sha256'] != sample['artifacts'][role]['sha256']:
                raise ValueError('Prediction artifact changed during import: ' + role)
        output.update(status='SUCCEEDED', species=configuration['species'], configuration_sha256=sample['configuration_sha256'],
            energy_eV=energy, forces_eV_per_angstrom=forces,
            energy_reference=sample.get('energy_reference'), provenance=provenance)
    except (OSError, ValueError, KeyError, IndexError, TypeError) as error:
        output.update(reason=str(error), provenance=provenance)
    return output
