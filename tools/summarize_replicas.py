"""Summarize explicitly independent replica-level scalars, not correlated frames."""
import argparse
import csv
import math
import statistics

from common import print_receipt, utc_now
from local_common import identity, json_file, load_config, new_directory, number, require, resolve_file


def summarize(source, config, output):
    from scipy.stats import t
    require(config, ['metric_column', 'unit', 'replica_id_column', 'group_columns', 'confidence', 'independence_basis', 'source_class'])
    if not isinstance(config['group_columns'], list) or not isinstance(config['independence_basis'], str) or not config['independence_basis'].strip():
        raise ValueError('List group columns explicitly and document the claimed replica independence basis.')
    confidence = number(config['confidence'], 'confidence')
    if not 0 < confidence < 1:
        raise ValueError('Confidence must be strictly between 0 and 1.')
    groups, seen = {}, set()
    with open(source, encoding='utf-8-sig', newline='') as stream:
        reader = csv.DictReader(stream)
        required = [config['metric_column'], config['replica_id_column'], *config['group_columns']]
        if any(column not in (reader.fieldnames or []) for column in required):
            raise ValueError('Missing required CSV column.')
        for row in reader:
            key = tuple(row[column] for column in config['group_columns'])
            replica = row[config['replica_id_column']]
            if not replica.strip() or (key, replica) in seen:
                raise ValueError('Replica IDs must be nonempty and unique within each comparison group.')
            seen.add((key, replica))
            value = float(row[config['metric_column']])
            if not math.isfinite(value):
                raise ValueError('Nonfinite replica metric; values are not silently discarded.')
            groups.setdefault(key, []).append((replica, value))
    if not groups:
        raise ValueError('No replica rows.')
    rows = []
    for key, items in groups.items():
        values = [value for _, value in items]
        n = len(values)
        mean = statistics.mean(values)
        sd = statistics.stdev(values) if n > 1 else None
        sem = sd / math.sqrt(n) if n > 1 else None
        half_width = float(t.ppf((1 + confidence) / 2, n - 1) * sem) if n > 1 else None
        rows.append({**dict(zip(config['group_columns'], key)), 'replicas': n, 'mean': mean,
                     'sample_sd': sd, 'sem': sem, 'confidence_lower': mean - half_width if n > 1 else None,
                     'confidence_upper': mean + half_width if n > 1 else None, 'unit': config['unit'],
                     'replica_ids': [replica for replica, _ in items]})
    output = new_directory(output)
    with (output / 'replica-summary.csv').open('x', encoding='utf-8', newline='') as stream:
        fields = [*config['group_columns'], 'replicas', 'mean', 'sample_sd', 'sem', 'confidence_lower', 'confidence_upper', 'unit']
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows({key: row[key] for key in fields} for row in rows)
    report = {'summarized_utc': utc_now(), 'source': identity(source), 'configuration': config, 'groups': rows,
              'assumptions': ['Rows are explicitly declared independent replica-level values, not adjacent trajectory frames.',
                              'Student-t mean interval assumes independent approximately normal replica metrics; independence was not verified by this tool.',
                              'Single replicas have no estimated SD, SEM or confidence interval. No automatic equilibration or within-run uncertainty estimate.'],
              'scientific_acceptance': 'UNVERIFIED', 'simulation_run': False}
    json_file(output / 'replica-summary.json', report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--csv', required=True)
    parser.add_argument('--config', required=True)
    parser.add_argument('--output-directory', required=True)
    args = parser.parse_args()
    config, _ = load_config(args.config)
    result = summarize(resolve_file(args.csv, '.'), config, args.output_directory)
    print_receipt(args.output_directory, groups=len(result['groups']), scientific_acceptance='UNVERIFIED')


if __name__ == '__main__':
    main()
