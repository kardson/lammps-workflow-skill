"""Restricted-triclinic geometry only; no rotation, wrapping or basis reduction."""
import math


def cell_values(configuration):
    bounds = configuration['bounds_angstrom']
    if len(bounds) != 3 or any(len(row) != 2 for row in bounds):
        raise ValueError('Three lower/upper cell bounds required')
    values = [x for row in bounds for x in row]
    tilt = configuration.get('tilt_angstrom', [0.0, 0.0, 0.0])
    if not isinstance(tilt, list) or len(tilt) != 3:
        raise ValueError('tilt_angstrom must contain xy, xz, yz')
    if any(type(x) not in (int, float) or not math.isfinite(x) for x in values + tilt):
        raise ValueError('Finite numeric cell bounds and tilt required')
    if any(row[0] >= row[1] for row in bounds):
        raise ValueError('Increasing cell bounds required')
    return [[float(x) for x in row] for row in bounds], [float(x) for x in tilt]


def fractional(position, bounds, tilt):
    """Cartesian position in restricted basis, relative to explicit box origin."""
    if len(position) != 3 or any(type(x) not in (int, float) or not math.isfinite(x) for x in position):
        raise ValueError('Three finite numeric Cartesian coordinates required')
    xy, xz, yz = tilt
    x, y, z = [x - row[0] for x, row in zip(position, bounds)]
    lx, ly, lz = [row[1] - row[0] for row in bounds]
    sz = z / lz
    sy = (y - yz * sz) / ly
    sx = (x - xy * sy - xz * sz) / lx
    return [sx, sy, sz]
