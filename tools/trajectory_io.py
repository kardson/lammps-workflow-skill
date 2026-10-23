"""Stream explicit orthogonal LAMMPS text dumps, one validated frame at a time."""
import hashlib
from pathlib import Path


class UnsupportedDump(ValueError):
    pass


def frames(path, max_atoms, observation):
    import numpy as np
    path = Path(path).resolve(strict=True)
    before = path.stat()
    digest, consumed, line_number, complete, at_eof = hashlib.sha256(), 0, 0, False, False
    with path.open('rb') as stream:
        def line(required=True):
            nonlocal consumed, line_number, at_eof
            raw = stream.readline()
            at_eof = not raw
            if not raw and required:
                raise ValueError('Truncated dump at line ' + str(line_number + 1))
            digest.update(raw)
            consumed += len(raw)
            line_number += bool(raw)
            return raw.decode('utf-8').strip()
        try:
            while True:
                header = line(False)
                if not header:
                    if at_eof:
                        complete = True
                        break
                    continue
                if header != 'ITEM: TIMESTEP':
                    raise ValueError('Expected TIMESTEP at line ' + str(line_number))
                step = int(line())
                if line() != 'ITEM: NUMBER OF ATOMS':
                    raise ValueError('Missing NUMBER OF ATOMS section.')
                count = int(line())
                if count < 0 or count > max_atoms:
                    raise ValueError('Frame atom count is negative or exceeds explicit local memory budget.')
                box_header = line().split()
                if box_header[:3] != ['ITEM:', 'BOX', 'BOUNDS']:
                    raise UnsupportedDump('Only orthogonal BOX BOUNDS dumps are supported.')
                if len(box_header) != 6 or any(token in box_header for token in ['xy', 'xz', 'yz', 'abc', 'origin']):
                    raise UnsupportedDump('Triclinic/general-cell dumps require another adapter.')
                boundary = box_header[3:]
                if any(len(token) != 2 or any(c not in 'pfsm' for c in token) or ('p' in token and token != 'pp') for token in boundary):
                    raise ValueError('Invalid dump boundary flags.')
                bounds = np.array([[float(value) for value in line().split()] for _ in range(3)])
                if bounds.shape != (3, 2) or not np.isfinite(bounds).all() or np.any(bounds[:, 1] <= bounds[:, 0]):
                    raise ValueError('Invalid orthogonal bounds.')
                columns_header = line().split()
                if columns_header[:2] != ['ITEM:', 'ATOMS']:
                    raise ValueError('Missing ATOMS header.')
                columns = columns_header[2:]
                if len(columns) != len(set(columns)) or 'id' not in columns or 'type' not in columns:
                    raise ValueError('Unique columns including id and type are required.')
                coordinates = None
                for names, convention in [(['x', 'y', 'z'], 'cartesian_wrapped'),
                                          (['xu', 'yu', 'zu'], 'cartesian_unwrapped'),
                                          (['xs', 'ys', 'zs'], 'scaled_wrapped')]:
                    if all(name in columns for name in names):
                        coordinates = [columns.index(name) for name in names]
                        break
                if coordinates is None:
                    raise UnsupportedDump('Need x/y/z, xu/yu/zu or xs/ys/zs coordinates.')
                ids, types, positions, labels = [], [], [], []
                for _ in range(count):
                    row = line().split()
                    if len(row) != len(columns):
                        raise ValueError('Atom row width does not match the header.')
                    ids.append(int(row[columns.index('id')]))
                    types.append(int(row[columns.index('type')]))
                    positions.append([float(row[index]) for index in coordinates])
                    if 'element' in columns:
                        labels.append(row[columns.index('element')])
                if any(value <= 0 for value in ids) or len(set(ids)) != count:
                    raise ValueError('Atom IDs must be positive and unique within a frame.')
                positions = np.array(positions, dtype=float).reshape((count, 3))
                if not np.isfinite(positions).all():
                    raise ValueError('Nonfinite trajectory coordinates.')
                if convention == 'scaled_wrapped':
                    positions = bounds[:, 0] + positions * (bounds[:, 1] - bounds[:, 0])
                yield {'step': step, 'count': count, 'ids': ids, 'types': types, 'positions': positions,
                       'element_labels': labels or None, 'bounds': bounds, 'boundary': boundary,
                       'coordinate_convention': convention, 'last_line': line_number}
        finally:
            after = path.stat()
            observation.update(path=str(path), source_bytes_before=before.st_size, source_bytes_after=after.st_size,
                               bytes_observed=consumed, observed_stream_sha256=digest.hexdigest(), complete_read=complete,
                               source_changed_during_read=(before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns))
