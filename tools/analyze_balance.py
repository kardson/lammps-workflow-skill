"""Check atomic balance from explicit cumulative insertion/removal counters."""
import argparse
import csv
from decimal import Decimal, InvalidOperation
import shutil
import tempfile

from common import print_receipt, utc_now
from local_common import identity, json_file, load_config, new_directory, number, require, resolve_file
from structure_io import validate_order


def count(value):
    if isinstance(value, bool):
        raise ValueError('Counts cannot be boolean.')
    try:
        numeric = Decimal(str(value))
    except InvalidOperation as error:
        raise ValueError('Counts must be numeric integers.') from error
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
    origins = config.get('counter_origins')
    if origins is None:
        inserted_origin = removed_origin = {symbol: 0 for symbol in elements}
        origin_policy = 'ZERO_AS_ORIGINAL_COUNTER_CONTRACT; not restart reconciliation'
    else:
        if not isinstance(origins, dict) or not isinstance(origins.get('source'), str) or not origins['source'].strip():
            raise ValueError('Counter origins require an explicit source.')
        if any(not isinstance(origins.get(key), dict) or set(origins[key]) != set(elements) for key in ('inserted', 'removed')):
            raise ValueError('Supply every species inserted/removed origin explicitly.')
        inserted_origin = {symbol: count(origins['inserted'][symbol]) for symbol in elements}
        removed_origin = {symbol: count(origins['removed'][symbol]) for symbol in elements}
        origin_policy = 'EXPLICIT_SUPPLIED_COUNTER_ORIGINS'
    previous_inserted = dict(inserted_origin)
    previous_removed = dict(removed_origin)
    source_before = identity(source)
    species_samples = 0
    mismatch_count = 0
    with tempfile.TemporaryFile(mode='w+', encoding='utf-8', newline='') as spool:
        writer = None
        with open(source, encoding='utf-8-sig', newline='') as stream:
            reader = csv.DictReader(stream)
            if reader.fieldnames is not None and len(set(reader.fieldnames)) != len(reader.fieldnames):
                raise ValueError('Duplicate counter CSV columns are ambiguous.')
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
                    expected = initial[symbol] + inserted - inserted_origin[symbol] - removed + removed_origin[symbol]
                    residual = observed - expected
                    mismatch_count += residual != 0
                    inserted_rate = removed_rate = None
                    if delta_time > 0:
                        exposure = number(area * delta_time, 'area times interval', positive=True)
                        try:
                            inserted_rate = number((inserted - previous_inserted[symbol]) / exposure, 'insertion rate', nonnegative=True)
                            removed_rate = number((removed - previous_removed[symbol]) / exposure, 'removal rate', nonnegative=True)
                        except OverflowError as error:
                            raise ValueError('Counter rate exceeds finite numerical range') from error
                    result = {'sample': index, 'time_ps': time_ps, 'element': symbol, 'observed_atoms': observed,
                                 'initial_atoms': initial[symbol], 'cumulative_inserted': inserted, 'cumulative_removed': removed,
                                 'inserted_counter_origin': inserted_origin[symbol], 'removed_counter_origin': removed_origin[symbol],
                                 'inserted_since_origin': inserted - inserted_origin[symbol], 'removed_since_origin': removed - removed_origin[symbol],
                                 'expected_atoms': expected, 'balance_residual_atoms': residual,
                                 'interval_inserted_atoms_per_A2_ps': inserted_rate,
                                 'interval_removed_atoms_per_A2_ps': removed_rate}
                    if writer is None:
                        writer = csv.DictWriter(spool, fieldnames=list(result))
                        writer.writeheader()
                    writer.writerow(result)
                    species_samples += 1
                    previous_inserted[symbol], previous_removed[symbol] = inserted, removed
                previous_time = time_ps
        if not species_samples:
            raise ValueError('No counter samples.')
        source_after = identity(source)
        if source_before != source_after:
            raise ValueError('Counter source changed while analyzing; source and existing outputs preserved.')
        output = new_directory(output)
        spool.seek(0)
        with (output / 'balance.csv').open('x', encoding='utf-8', newline='') as stream:
            shutil.copyfileobj(spool, stream, length=1024 * 1024)
    report = {'analyzed_utc': utc_now(), 'source': source_after, 'configuration': config,
              'status': 'COUNTER_BALANCE_MATCH' if mismatch_count == 0 else 'COUNTER_BALANCE_MISMATCH',
              'counter_origin_policy': origin_policy,
              'processing': 'Streaming CSV to disk spool; memory does not retain the row history',
              'species_samples': species_samples, 'mismatching_species_samples': mismatch_count,
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
