"""Summarize explicitly independent replica-level scalars, not correlated frames."""
import argparse
import csv
import math
import statistics
from pathlib import Path

from common import print_receipt, utc_now
from local_common import identity, json_file, load_config, new_directory, number, require, resolve_file
from replica_evidence import bind


def summarize(source, config, output):
    require(config, ['metric_column', 'unit', 'replica_id_column', 'group_columns', 'confidence', 'independence_basis', 'source_class'])
    if any(not isinstance(config[name],str) or not config[name].strip() for name in ('metric_column','unit','replica_id_column')) or config['source_class'] not in ('engineering_fixture','upstream_reference','research_output'):
        raise ValueError('Explicit metric/replica columns, unit and supported source_class required')
    if not isinstance(config['group_columns'], list) or any(not isinstance(name, str) or not name for name in config['group_columns']) or len(set(config['group_columns'])) != len(config['group_columns']) or not isinstance(config['independence_basis'], str) or not config['independence_basis'].strip():
        raise ValueError('List group columns explicitly and document the claimed replica independence basis.')
    if config.get('observation_kind', 'independent_replica_scalar') != 'independent_replica_scalar':
        raise ValueError('Trajectory frames are not independent replica-level scalars')
    reserved = {'replicas','mean','sample_sd','sem','confidence_lower','confidence_upper','unit','replica_ids','interval_status','evidence_status','replica_evidence','evidence_issues'}
    if set(config['group_columns']) & reserved:
        raise ValueError('Comparison group columns conflict with statistical output fields')
    confidence = number(config['confidence'], 'confidence')
    if not 0 < confidence < 1:
        raise ValueError('Confidence must be strictly between 0 and 1.')
    source_before = identity(source)
    groups, seen, observed = {}, set(), {}
    with open(source, encoding='utf-8-sig', newline='') as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames is not None and len(set(reader.fieldnames)) != len(reader.fieldnames):
            raise ValueError('Duplicate replica CSV columns are ambiguous')
        required = [config['metric_column'], config['replica_id_column'], *config['group_columns']]
        if any(column not in (reader.fieldnames or []) for column in required):
            raise ValueError('Missing required CSV column.')
        for row in reader:
            if None in row or any(not isinstance(row.get(column), str) for column in required):
                raise ValueError('Malformed replica CSV row')
            key = tuple(row[column] for column in config['group_columns'])
            replica = row[config['replica_id_column']]
            if not replica.strip() or (key, replica) in seen:
                raise ValueError('Replica IDs must be nonempty and unique within each comparison group.')
            seen.add((key, replica))
            value = float(row[config['metric_column']])
            if not math.isfinite(value):
                raise ValueError('Nonfinite replica metric; values are not silently discarded.')
            groups.setdefault(key, []).append((replica, value))
            observed[(key,replica)] = value
    if not groups:
        raise ValueError('No replica rows.')
    evidence_required, evidence = bind(config, observed, Path(source).resolve().parent)
    rows = []
    for key, items in groups.items():
        values = [value for _, value in items]
        n = len(values)
        mean = statistics.mean(values)
        sd = statistics.stdev(values) if n > 1 else None
        contexts = [evidence[(key,replica)] for replica,_ in items]
        evidence_issues = [issue for context in contexts for issue in context['issues']]
        if evidence_required and config.get('observation_kind') != 'independent_replica_scalar':
            evidence_issues.append('Independent replica scalar observation kind not explicitly declared')
        run_ids = [context['metadata'].get('run_id') for context in contexts if context['metadata'] and context['metadata'].get('run_id')]
        if len(run_ids) != len(set(run_ids)):
            evidence_issues.append('Multiple declared replicas share one actual run identity')
        allowed = n > 1 and not evidence_issues
        sem = sd / math.sqrt(n) if allowed else None
        if allowed:
            from scipy.stats import t
            half_width = float(t.ppf((1 + confidence) / 2, n - 1) * sem)
            lower = number(mean - half_width,'confidence lower')
            upper = number(mean + half_width,'confidence upper')
        else:
            half_width = lower = upper = None
        for name,value in [('mean',mean),('sample_sd',sd),('sem',sem),('half_width',half_width)]:
            if value is not None:
                number(value,name)
        rows.append({**dict(zip(config['group_columns'], key)), 'replicas': n, 'mean': mean,
                     'sample_sd': sd, 'sem': sem, 'confidence_lower': lower,
                     'confidence_upper': upper, 'unit': config['unit'],
                     'replica_ids': [replica for replica, _ in items], 'replica_evidence': contexts,
                     'evidence_status': 'UNRESOLVED' if evidence_issues else 'BOUND_DECLARATIONS' if evidence_required else 'LEGACY_DECLARED_ONLY',
                     'interval_status': 'CONDITIONAL_ON_DECLARED_INDEPENDENCE' if allowed else 'WITHHELD',
                     'evidence_issues': evidence_issues})
    source_after = identity(source)
    if source_before != source_after:
        raise ValueError('Replica scalar source changed during analysis')
    output = new_directory(output)
    with (output / 'replica-summary.csv').open('x', encoding='utf-8', newline='') as stream:
        fields = [*config['group_columns'], 'replicas', 'mean', 'sample_sd', 'sem', 'confidence_lower', 'confidence_upper', 'unit','interval_status','evidence_status']
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows({key: row[key] for key in fields} for row in rows)
    report = {'summarized_utc': utc_now(), 'source': source_after, 'configuration': config, 'groups': rows,
              'status': 'REPLICA_SUMMARY_PARTIAL' if any(row['evidence_issues'] for row in rows) else
                  'CONDITIONAL_REPLICA_SUMMARY' if any(row['sem'] is not None for row in rows) else 'DESCRIPTIVE_REPLICA_SUMMARY',
              'evidence_policy': 'REQUIRED' if evidence_required else 'LEGACY_DECLARATION_WITH_UNVERIFIED_ASSUMPTIONS',
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
    try:
        config, _ = load_config(args.config)
        result = summarize(resolve_file(args.csv, '.'), config, args.output_directory)
    except (OSError,ValueError,ImportError) as error:
        import json
        print(json.dumps({'status':'ERROR','message':str(error),'simulation_run':False}))
        return 2
    print_receipt(args.output_directory, groups=len(result['groups']), status=result['status'], scientific_acceptance='UNVERIFIED')
    return 1 if result['status']=='REPLICA_SUMMARY_PARTIAL' else 0


if __name__ == '__main__':
    raise SystemExit(main())
