"""Stream explicit sampling windows into time blocks; no IID-frame uncertainty."""
import argparse
import csv
import json

from block_statistics import analyze_samples
from common import utc_now
from local_common import identity, json_file, load_config, new_directory, resolve_file


def summarize(source, config, output):
    for key in ('time_column', 'metric_column', 'unit', 'run_id', 'seed_basis'):
        if not isinstance(config.get(key), str) or not config[key].strip():
            raise ValueError('Explicit ' + key + ' required')
    if config.get('source_class') not in ('engineering_fixture', 'upstream_reference', 'research_output'):
        raise ValueError('Explicit supported source_class required')
    if not isinstance(config.get('seeds'), dict):
        raise ValueError('Explicit seed metadata object required; unknown seed values may remain null')
    before = identity(source)
    directory = new_directory(output)
    partial, result, failure, after = 0, None, None, None
    fields = ['block', 'start_ps', 'end_ps', 'samples', 'mean', 'sample_sd', 'complete', 'reason']
    try:
        with (directory / 'blocks.csv').open('x', encoding='utf-8', newline='') as target:
            writer = csv.DictWriter(target, fieldnames=fields)
            writer.writeheader()
            def emit(row):
                nonlocal partial
                writer.writerow(row)
                partial += 1
            with open(source, encoding='utf-8-sig', newline='') as stream:
                reader = csv.DictReader(stream)
                if not reader.fieldnames or len(set(reader.fieldnames)) != len(reader.fieldnames) or any(config[key] not in reader.fieldnames for key in ('time_column', 'metric_column')):
                    raise ValueError('Unique explicit time/metric CSV columns required')
                def samples():
                    for row in reader:
                        if None in row or row[config['time_column']] is None or row[config['metric_column']] is None:
                            raise ValueError('Malformed time-series row')
                        yield float(row[config['time_column']]), float(row[config['metric_column']])
                result = analyze_samples(samples(), config, emit)
        after = identity(source)
        if before != after:
            raise ValueError('Time-series source changed during processing')
    except (OSError, ValueError, csv.Error, ImportError, OverflowError) as error:
        failure = {'type': type(error).__name__, 'message': str(error), 'blocks_written': partial}
    metadata_unknown = [key for key, value in config['seeds'].items() if value is None]
    if not config['seeds']:
        metadata_unknown.append('No seed roles recorded; see seed_basis')
    report = {'schema_version': 1, 'record_type': 'time_block_summary', 'summarized_utc': utc_now(),
        'status': 'FAILED' if failure else result['status'], 'configuration': config,
        'source_before': before, 'source_after': after,
        'statistics': result if not failure else None, 'partial_statistics': result if failure else None,
        'failure': failure, 'seed_metadata_unresolved': metadata_unknown,
        'output': identity(directory / 'blocks.csv'), 'scientific_acceptance': 'UNVERIFIED',
        'simulation_run': False, 'scope': 'Within-run statistical diagnostic; no equilibration or independence certification',
        'excluded_uncertainties': ['Model discrepancy', 'Finite size', 'Timestep/flux/geometry sensitivity']}
    json_file(directory / 'time-summary.json', report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--csv', required=True)
    parser.add_argument('--config', required=True)
    parser.add_argument('--output-directory', required=True)
    args = parser.parse_args()
    try:
        config, _ = load_config(args.config)
        result = summarize(resolve_file(args.csv, '.'), config, args.output_directory)
    except (OSError, ValueError) as error:
        print(json.dumps({'status': 'ERROR', 'message': str(error), 'simulation_run': False}))
        return 2
    print(json.dumps({'status': result['status'], 'scientific_acceptance': 'UNVERIFIED', 'simulation_run': False}))
    return 0 if result['status'] == 'CONDITIONAL_BLOCK_INTERVAL' else 1


if __name__ == '__main__':
    raise SystemExit(main())
