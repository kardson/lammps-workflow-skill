"""Stream snapshot counts, composition and explicitly defined film geometry."""
import argparse
import csv

from common import print_receipt, utc_now
from local_common import identity, integer, json_file, load_config, new_directory, number, require, resolve_file
from structure_io import validate_order
from trajectory_io import frames


def validate(config):
    import numpy as np
    require(config, ['source_class', 'units', 'type_order', 'film_elements', 'z_window_angstrom',
                     'reference_z_angstrom', 'height_quantile', 'height_grid', 'empty_cell_policy',
                     'composition_z_edges_angstrom', 'max_atoms_per_frame'])
    if config['source_class'] not in {'engineering_fixture', 'upstream_reference', 'research_output'} or config['units'] != 'metal':
        raise ValueError('Set source_class explicitly; this analysis adapter requires metal (angstrom) coordinates.')
    order = validate_order(config['type_order'])
    film = config['film_elements']
    if not isinstance(film, list) or not film or len(set(film)) != len(film) or set(film) - set(order):
        raise ValueError('Supply unique film elements from type_order.')
    window = config['z_window_angstrom']
    if not isinstance(window, list) or len(window) != 2 or number(window[0], 'z minimum') >= number(window[1], 'z maximum'):
        raise ValueError('Supply an ordered finite z selection window.')
    number(config['reference_z_angstrom'], 'reference_z_angstrom')
    quantile = number(config['height_quantile'], 'height_quantile')
    if not 0 <= quantile <= 1:
        raise ValueError('height_quantile must lie between zero and one.')
    grid = config['height_grid']
    if not isinstance(grid, list) or len(grid) != 2 or any(integer(value, 'height_grid', 1) > 10000 for value in grid):
        raise ValueError('Supply a bounded, positive [nx, ny] height grid.')
    if grid[0] * grid[1] > 1000000:
        raise ValueError('Height grid exceeds this adapter memory budget.')
    if config['empty_cell_policy'] != 'exclude':
        raise ValueError('This adapter explicitly excludes empty cells from roughness and reports their coverage.')
    edges = np.array(config['composition_z_edges_angstrom'], dtype=float)
    if edges.ndim != 1 or len(edges) < 2 or not np.isfinite(edges).all() or np.any(np.diff(edges) <= 0):
        raise ValueError('Composition z edges must be finite and strictly increasing.')
    integer(config['max_atoms_per_frame'], 'max_atoms_per_frame', 1)
    return order, edges


def metrics(frame, config, order):
    import numpy as np
    if frame['boundary'][:2] != ['pp', 'pp'] or frame['boundary'][2] == 'pp':
        raise ValueError('Film geometry adapter requires periodic x/y and nonperiodic z.')
    types = np.array(frame['types'], dtype=int)
    if np.any(types < 1) or np.any(types > len(order)):
        raise ValueError('Trajectory atom type is outside the supplied mapping.')
    elements = np.array([order[value - 1] for value in types])
    if frame['element_labels'] is not None and frame['element_labels'] != elements.tolist():
        raise ValueError('Dump element labels disagree with numeric type mapping.')
    positions = frame['positions']
    low, high = config['z_window_angstrom']
    selected = np.isin(elements, config['film_elements']) & (positions[:, 2] >= low) & (positions[:, 2] <= high)
    z_values = positions[selected, 2]
    nx, ny = config['height_grid']
    grid = np.full((nx, ny), -np.inf)
    bounds = frame['bounds']
    xy = (positions[selected, :2] - bounds[:2, 0]) % (bounds[:2, 1] - bounds[:2, 0])
    if len(z_values):
        indices = np.floor(xy / (bounds[:2, 1] - bounds[:2, 0]) * [nx, ny]).astype(int)
        indices = np.minimum(indices, [nx - 1, ny - 1])
        np.maximum.at(grid, (indices[:, 0], indices[:, 1]), z_values)
    heights = grid[np.isfinite(grid)] - config['reference_z_angstrom']
    quantile_height = float(np.quantile(z_values, config['height_quantile']) - config['reference_z_angstrom']) if len(z_values) else None
    counts = {symbol: int(np.count_nonzero(elements == symbol)) for symbol in order}
    return {'atoms': frame['count'], 'selected_film_atoms': int(selected.sum()),
            'quantile_height_angstrom': quantile_height,
            'mean_occupied_grid_height_angstrom': float(heights.mean()) if len(heights) else None,
            'rms_grid_roughness_angstrom': float(np.sqrt(np.mean((heights - heights.mean()) ** 2))) if len(heights) else None,
            'occupied_grid_fraction': float(len(heights) / (nx * ny)),
            'snapshot_counts': counts,
            'outside_z_window': int(frame['count'] - np.count_nonzero((positions[:, 2] >= low) & (positions[:, 2] <= high)))}, elements


def analyze(path, config, output, max_frames=None, stride=1):
    import numpy as np
    order, edges = validate(config)
    integer(stride, 'stride', 1)
    if max_frames is not None:
        integer(max_frames, 'max_frames', 1)
    output = new_directory(output)
    observation = {}
    generator = frames(path, config['max_atoms_per_frame'], observation)
    seen, selected, previous, previous_step, issues = 0, 0, None, None, []
    columns = ['frame', 'step', 'atoms', 'selected_film_atoms', 'quantile_height_angstrom',
               'mean_occupied_grid_height_angstrom', 'rms_grid_roughness_angstrom', 'occupied_grid_fraction',
               'outside_z_window', 'appeared_ids_since_previous_selected_frame', 'disappeared_ids_since_previous_selected_frame',
               'changed_species_same_id', *['count_' + symbol for symbol in order]]
    failure = None
    try:
        with (output / 'frame-metrics.csv').open('x', encoding='utf-8', newline='') as metrics_file, \
             (output / 'composition-profile.csv').open('x', encoding='utf-8', newline='') as composition_file:
            writer = csv.DictWriter(metrics_file, fieldnames=columns)
            writer.writeheader()
            profile = csv.writer(composition_file)
            profile.writerow(['frame', 'step', 'z_lower_angstrom', 'z_upper_angstrom', 'element', 'count', 'bin_atom_fraction'])
            for index, frame in enumerate(generator):
                seen += 1
                if index % stride:
                    continue
                selected += 1
                result, elements = metrics(frame, config, order)
                counts = result.pop('snapshot_counts')
                current = dict(zip(frame['ids'], elements.tolist()))
                appeared = len(current.keys() - previous.keys()) if previous is not None else None
                disappeared = len(previous.keys() - current.keys()) if previous is not None else None
                changed = sum(current[key] != previous[key] for key in current.keys() & previous.keys()) if previous is not None else 0
                if changed:
                    issues.append({'frame': index, 'reason': 'Same atom ID changed species; identity interpretation requires review.'})
                if previous_step is not None and frame['step'] <= previous_step:
                    issues.append({'frame': index, 'reason': 'Step reset/repetition observed; no cumulative time inferred.'})
                writer.writerow({'frame': index, 'step': frame['step'], **result,
                                 'appeared_ids_since_previous_selected_frame': appeared,
                                 'disappeared_ids_since_previous_selected_frame': disappeared,
                                 'changed_species_same_id': changed, **{'count_' + key: value for key, value in counts.items()}})
                histograms = {symbol: np.histogram(frame['positions'][elements == symbol, 2], bins=edges)[0] for symbol in order}
                totals = sum(histograms.values())
                for j in range(len(edges) - 1):
                    for symbol in order:
                        count = int(histograms[symbol][j])
                        profile.writerow([index, frame['step'], edges[j], edges[j + 1], symbol, count,
                                          float(count / totals[j]) if totals[j] else ''])
                previous, previous_step = current, frame['step']
                if max_frames is not None and selected >= max_frames:
                    break
    except Exception as error:
        failure = {'type': type(error).__name__, 'message': str(error)}
    finally:
        generator.close()
    if observation.get('source_changed_during_read'):
        issues.append({'reason': 'Source changed during read; this is not final immutable evidence.'})
    status = 'FAILED' if failure else ('PARTIAL_SNAPSHOT' if not observation.get('complete_read') or observation.get('source_changed_during_read') else 'LOCAL_GEOMETRY_SUMMARY')
    if selected == 0 and not failure:
        status = 'NO_FRAMES'
    report = {'analyzed_utc': utc_now(), 'status': status, 'configuration': config,
              'source': observation, 'frames_read': seen, 'frames_selected': selected,
              'stride': stride, 'maximum_selected_frames': max_frames, 'issues': issues, 'failure': failure,
              'method': {'height': 'Configured quantile of selected film z minus explicit reference z.',
                         'roughness': 'RMS of per-cell maximum selected film height over occupied grid cells only.',
                         'coverage': 'Fraction of lateral grid cells occupied by at least one selected film atom; not epitaxial coverage.',
                         'composition': 'All snapshot species counted in fixed z bins; final bin includes right edge.',
                         'ids': 'Snapshot differences only; not insertion/escape counters or cumulative flux.'},
              'outputs': [identity(output / name) for name in ['frame-metrics.csv', 'composition-profile.csv']],
              'scientific_acceptance': 'UNVERIFIED', 'simulation_run': False,
              'limitations': ['Orthogonal p/p/nonperiodic-z text dumps only; no automatic phase, interface or production-window selection.',
                              'Selected z window, reference, quantile and bin/grid choices are explicit analysis assumptions.',
                              'Adatoms/escape particles inside the selected window affect heights; snapshots can miss insertion/removal between frames.',
                              'No force evaluation, equilibrium, statistical independence or potential-accuracy validation.']}
    json_file(output / 'analysis.json', report)
    if failure:
        raise ValueError('Trajectory analysis failed; partial outputs labeled FAILED at ' + str(output / 'analysis.json') + ': ' + failure['message'])
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--trajectory', required=True)
    parser.add_argument('--config', required=True)
    parser.add_argument('--output-directory', required=True)
    parser.add_argument('--max-frames', type=int)
    parser.add_argument('--stride', type=int, default=1)
    args = parser.parse_args()
    config, _ = load_config(args.config)
    report = analyze(resolve_file(args.trajectory, '.'), config, args.output_directory, args.max_frames, args.stride)
    print_receipt(args.output_directory, status=report['status'], frames_selected=report['frames_selected'])
    if report['status'] in {'NO_FRAMES', 'FAILED'}:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
