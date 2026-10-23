"""Check atomic balance from explicit cumulative insertion/removal counters."""
import argparse
import csv
from decimal import Decimal

from common import print_receipt, utc_now
from local_common import identity, json_file, load_config, new_directory, number, require, resolve_file
from structure_io import validate_order


def count(value):
    numeric = Decimal(str(value))
    if not numeric.is_finite() or numeric < 0 or numeric != numeric.to_integral_value():
        raise ValueError('Counts must be finite, nonnegative integers.')
    return int(numeric)


def analyze(source, config, output):
    require(config, ['source_class', 'elements', 'initial_counts', 'area_angstrom2', 'time_column', 'initial_time_ps',
                     'observed_prefix', 'inserted_prefix', 'removed_prefix', 'counter_provenance'])
    elements = validate_order(config['elements'])
    area = number(config['area_angstrom2'], 'area_angstrom2', positive=True)
    previous_time = number(config['initial_time_ps'], 'initial_time_ps')
    if set(config['initial_counts']) != set(elements) or not str(config['counter_provenance']).strip():
        raise ValueError('Supply every initial species count and actual insertion/removal counter provenance.')
    initial = {symbol: count(config['initial_counts'][symbol]) for symbol in elements}
    previous_inserted = {symbol: 0 for symbol in elements}
    previous_removed = {symbol: 0 for symbol in elements}
    rows = []
    mismatch_count = 0
    with open(source, encoding='utf-8-sig', newline='') as stream:
        reader = csv.DictReader(stream)
        required_columns = [config['time_column']] + [config[prefix] + symbol for symbol in elements
                            for prefix in ['observed_prefix', 'inserted_prefix', 'removed_prefix']]
        if any(column not in (reader.fieldnames or []) for column in required_columns):
            raise ValueError('Observed counts and cumulative inserted/removed columns are all required; do not infer missing counters from snapshots.')
        for index, row in enumerate(reader):
            time_ps = number(float(row[config['time_column']]), 'time_ps')
            if time_ps < previous_time or index > 0 and time_ps == previous_time:
                raise ValueError('Supply an explicit strictly increasing physical timeline and cumulative counters without resets.')
            delta_time = time_ps - previous_time
            for symbol in elements:
                observed = count(row[config['observed_prefix'] + symbol])
                inserted = count(row[config['inserted_prefix'] + symbol])
                removed = count(row[config['removed_prefix'] + symbol])
                if inserted < previous_inserted[symbol] or removed < previous_removed[symbol]:
                    raise ValueError('Cumulative counters reset/decreased; explicitly reconcile phases before balance analysis.')
                expected = initial[symbol] + inserted - removed
                residual = observed - expected
                mismatch_count += residual != 0
                rows.append({'sample': index, 'time_ps': time_ps, 'element': symbol, 'observed_atoms': observed,
                             'initial_atoms': initial[symbol], 'cumulative_inserted': inserted, 'cumulative_removed': removed,
                             'expected_atoms': expected, 'balance_residual_atoms': residual,
                             'interval_inserted_atoms_per_A2_ps': (inserted - previous_inserted[symbol]) / (area * delta_time) if delta_time > 0 else None,
                             'interval_removed_atoms_per_A2_ps': (removed - previous_removed[symbol]) / (area * delta_time) if delta_time > 0 else None})
                previous_inserted[symbol], previous_removed[symbol] = inserted, removed
            previous_time = time_ps
    if not rows:
        raise ValueError('No counter samples.')
    output = new_directory(output)
    with (output / 'balance.csv').open('x', encoding='utf-8', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    report = {'analyzed_utc': utc_now(), 'source': identity(source), 'configuration': config,
              'status': 'COUNTER_BALANCE_MATCH' if mismatch_count == 0 else 'COUNTER_BALANCE_MISMATCH',
              'species_samples': len(rows), 'mismatching_species_samples': mismatch_count,
              'scientific_acceptance': 'UNVERIFIED', 'simulation_run': False,
              'limitations': ['Counter provenance is supplied, not authenticated by this tool. Initial counts and cumulative insertion/removal must share the same scope and origin.',
                              'Snapshot ID changes are not a replacement for actual cumulative insertion/removal counters.',
                              'Rates use supplied physical time and area; they do not establish experimental flux equivalence or film quality.']}
    json_file(output / 'balance.json', report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--csv', required=True)
    parser.add_argument('--config', required=True)
    parser.add_argument('--output-directory', required=True)
    args = parser.parse_args()
    config, _ = load_config(args.config)
    report = analyze(resolve_file(args.csv, '.'), config, args.output_directory)
    print_receipt(args.output_directory, status=report['status'])
    if report['mismatching_species_samples']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
