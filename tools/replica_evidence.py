"""Bind replica-level scalars to declared run/window/seed and metric source evidence."""
import hashlib
import json
import math
from pathlib import Path


def finite(value):
    return type(value) in (int, float) and math.isfinite(value)


def bind(config, observed, base):
    supplied = config.get('replica_evidence')
    required = supplied is not None or config.get('source_class') == 'research_output'
    if supplied is None:
        supplied = []
    if not isinstance(supplied, list):
        raise ValueError('replica_evidence must be an explicit list')
    records = {}
    for item in supplied:
        if not isinstance(item, dict) or not isinstance(item.get('group'), dict) or set(item['group']) != set(config['group_columns']):
            raise ValueError('Replica evidence group must exactly name the configured comparison fields')
        if not isinstance(item.get('replica_id'), str) or any(not isinstance(item['group'][name], str) for name in config['group_columns']):
            raise ValueError('Replica/group evidence identities must be strings')
        key = (tuple(item['group'][name] for name in config['group_columns']), item['replica_id'])
        if key not in observed or key in records:
            raise ValueError('Unknown or duplicate replica evidence binding')
        issues = []
        if not isinstance(item.get('run_id'), str) or not item['run_id'].strip():
            issues.append('Actual run identity missing')
        seeds = item.get('seeds')
        if not isinstance(seeds, dict) or not seeds or any(value is None for value in seeds.values()) or not item.get('seed_basis'):
            issues.append('Seed roles/basis unresolved; explicit nonrandom roles need a justification')
        elif any(not isinstance(role,str) or not role or (type(value) is not int or value<0) and value!='not_applicable' for role,value in seeds.items()):
            issues.append('Seed values must be nonnegative integers or explicit not_applicable')
        window = item.get('window')
        if not isinstance(window, dict) or not finite(window.get('start_ps')) or not finite(window.get('end_ps')) or window['end_ps'] < window['start_ps'] or not window.get('source'):
            issues.append('Sampling window/source unresolved')
        elif window['end_ps'] == window['start_ps'] and window.get('kind') != 'snapshot':
            issues.append('Zero-duration window requires an explicit snapshot definition')
        if not isinstance(item.get('correlation_basis'), str) or not item['correlation_basis'].strip():
            issues.append('Within-run correlation treatment unresolved')
        if not isinstance(item.get('metric_definition'), str) or not item['metric_definition'].strip() or item.get('unit') != config['unit']:
            issues.append('Metric definition/unit unresolved or inconsistent')
        metric = item.get('metric_source')
        source_identity = None
        if not isinstance(metric, dict) or not isinstance(metric.get('path'), str) or not metric.get('sha256'):
            issues.append('Actual metric source identity missing')
        else:
            try:
                path = Path(metric['path'])
                path = path if path.is_absolute() else Path(base) / path
                if path.stat().st_size > 16 * 1024 * 1024:
                    raise ValueError('Scalar evidence JSON exceeds 16 MiB bound')
                raw = path.read_bytes()
                digest = hashlib.sha256(raw).hexdigest()
                source_identity = {'path': str(path.resolve()), 'sha256': digest, 'bytes': len(raw)}
                if digest != metric['sha256']:
                    raise ValueError('Metric source identity mismatch')
                selected = json.loads(raw.decode('utf-8-sig'))
                pointer = metric.get('pointer')
                if not isinstance(pointer, str) or pointer and not pointer.startswith('/'):
                    raise ValueError('Explicit metric JSON pointer required')
                for token in pointer[1:].split('/') if pointer else []:
                    token = token.replace('~1', '/').replace('~0', '~')
                    selected = selected[int(token)] if isinstance(selected, list) else selected[token]
                tolerance = metric.get('value_tolerance')
                if not finite(tolerance) or tolerance < 0 or not finite(selected) or abs(selected - observed[key]) > tolerance:
                    raise ValueError('Bound metric value/tolerance differs from the actual CSV scalar')
            except (OSError, ValueError, KeyError, IndexError, TypeError) as error:
                issues.append(str(error))
        records[key] = {'status': 'BOUND_DECLARATIONS_NOT_INDEPENDENCE_PROOF' if not issues else 'UNRESOLVED',
                        'issues': issues, 'metadata': item, 'metric_source_observed': source_identity}
    for key in observed:
        if key not in records:
            records[key] = {'status': 'UNRESOLVED' if required else 'LEGACY_DECLARED_ONLY',
                'issues': ['Replica evidence record missing'] if required else [], 'metadata': None,
                'metric_source_observed': None}
    return required, records
