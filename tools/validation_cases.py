"""Validation planning and bounded receipt parsing; never launches a process."""
import hashlib
import json
import math
from pathlib import Path


def expected_terminal(case):
    state = case.get('expected_terminal_state', 'SUCCEEDED')
    if state not in ('SUCCEEDED', 'FAILED'):
        raise ValueError('Expected terminal state must be SUCCEEDED or FAILED')
    if state == 'FAILED':
        if case['parser'] not in ('termination_v1', 'lammps_single_line_v1'):
            raise ValueError('Expected process failure requires a terminal parser')
        checks = [check for check in case['checks'] if check['metric'] == 'exit_code']
        if len(checks) != 1 or checks[0]['operator'] != 'eq' or type(checks[0]['value']) is not int or checks[0]['value'] == 0:
            raise ValueError('Expected process failure requires one exact nonzero integer exit_code check')
    return state


def load_case(path):
    import jsonschema
    case = json.loads(Path(path).read_text(encoding='utf-8-sig'))
    schema = json.loads((Path(__file__).resolve().parents[1] /
                         'schemas/validation-case.schema.json').read_text(encoding='utf-8'))
    jsonschema.validate(case, schema)
    expected_terminal(case)
    for item in case['inputs'] + case['expected_outputs']:
        safe_path(Path('.').resolve(), item['path'])
    if case['category'] in ('inference', 'md', 'performance', 'scientific') and case['execution_kind'] != 'engine':
        raise ValueError('Computational case category requires engine execution kind')
    if case['parser'] == 'historical_record_v1':
        source = case.get('historical_source')
        if not source or not any(item['path'] == source['path'] for item in case['inputs']):
            raise ValueError('Historical source must have a declared input identity')
        safe_path(Path('.').resolve(), source['path'])
    return case


def safe_path(root, relative):
    if not isinstance(relative, str) or not relative or '\\' in relative or ':' in relative:
        raise ValueError('Portable relative evidence path required')
    path = Path(relative)
    if path.is_absolute() or '..' in path.parts:
        raise ValueError('Evidence path escapes case directory')
    root = Path(root).resolve()
    result = (root / path).resolve()
    if not result.is_relative_to(root):
        raise ValueError('Evidence path escapes case directory')
    return result


def plan(cases, categories=None):
    selected = set(categories or [])
    ids = [case['case_id'] for case in cases]
    if len(ids) != len(set(ids)):
        raise ValueError('Duplicate validation case identity')
    return {'operation': 'plan', 'execution_performed': False,
            'scope': 'Selection only; no authorization or current host readiness established',
            'cases': [{'case_id': case['case_id'], 'category': case['category'],
                       'execution_kind': case['execution_kind'],
                       'state': 'SELECTED_NOT_RUN' if case['category'] in selected else 'NOT_SELECTED',
                       'unresolved': (['combination'] if case['execution_kind'] == 'engine' and case['combination'] is None else [])
                           + (['resources'] if case['execution_kind'] != 'static' and case['resources'] is None else []),
                       'preconditions': case['preconditions']} for case in cases]}


def parse_termination(case, directory):
    """Only interprets terminal protocol and requested metrics, not engine physics."""
    expected_state = expected_terminal(case)
    root = Path(directory).resolve(strict=True)
    result = {'case_id': case['case_id'], 'status': 'UNVERIFIED', 'checks': [],
              'missing_outputs': [], 'evidence': [], 'errors': [],
              'scope': 'Parsed existing receipt only; no execution, freshness or scientific acceptance claim'}
    for item in case['inputs']:
        path = safe_path(root, item['path'])
        if not path.is_file():
            result['errors'].append('Required case input missing: ' + item['path'])
            continue
        digest = hashlib.sha256()
        with path.open('rb') as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b''):
                digest.update(block)
        if digest.hexdigest() != item['sha256']:
            result['errors'].append('Case input identity mismatch: ' + item['path'])
    for item in case['expected_outputs']:
        path = safe_path(root, item['path'])
        if item['required'] and not path.is_file():
            result['missing_outputs'].append(item['path'])
    if case['parser'] == 'historical_record_v1':
        return parse_historical(case, root, result)
    if case['parser'] not in ('termination_v1', 'lammps_single_line_v1'):
        result['errors'].append('Unsupported parser: ' + case['parser'])
        return result
    path = safe_path(root, 'termination.json')
    if not path.is_file():
        result['status'] = 'PARTIAL'
        result['errors'].append('Terminal receipt missing')
        return result
    if path.stat().st_size > 1024 * 1024:
        result['errors'].append('Receipt exceeds 1 MiB parsing bound')
        return result
    raw = path.read_bytes()
    result['evidence'].append({'path': 'termination.json', 'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw)})
    try:
        receipt = json.loads(raw.decode('utf-8-sig'))
        if not isinstance(receipt, dict):
            raise ValueError('Receipt must be an object')
    except (ValueError, UnicodeError) as error:
        result['errors'].append(str(error))
        result['status'] = 'PARTIAL'
        return result
    code, state = receipt.get('exit_code'), receipt.get('state')
    result['process_terminal_state'] = state
    result['expected_terminal_state'] = expected_state
    if type(code) is not int or state not in ('SUCCEEDED', 'FAILED', 'STOPPED'):
        result['errors'].append('Missing/invalid exit code or terminal state')
    elif (state == 'SUCCEEDED') != (code == 0):
        result['errors'].append('Inconsistent terminal state and exit code')
    metrics = {'exit_code': code}
    if case['parser'] == 'lammps_single_line_v1':
        from parse_log import parse_log
        log_path = safe_path(root, 'log.lammps')
        if not log_path.is_file():
            result['errors'].append('LAMMPS log missing')
        else:
            summary = parse_log(log_path)
            result['log_parse_scope'] = summary['parse_scope']
            result['evidence'].append({'path': 'log.lammps',
                'sha256': summary['observed_stream_sha256'], 'bytes': summary['source_bytes_after']})
            blocks = summary['thermo_blocks']
            metrics.update({'error_count': summary['error_count'],
                            'nonfinite_values': summary['nonfinite_values'],
                            'thermo_block_count': len(blocks)})
            if summary['parse_scope'] != 'PARSED_SINGLE_LINE_THERMO':
                result['errors'].append('Incomplete or unsupported thermo parsing')
            if blocks:
                metrics['last_step'] = blocks[-1]['last']['values'].get('Step')
                metrics['last_block_completed'] = int(blocks[-1]['following_loop_line'] is not None)
            # Fundamental evidence failures cannot be hidden by selecting easier checks.
            if summary['error_count'] or summary['nonfinite_values']:
                result['errors'].append('Log contains engine errors or nonfinite thermo values')
            if not blocks or blocks[-1]['following_loop_line'] is None:
                result['errors'].append('Final thermo block lacks a following loop marker')
    for check in case['checks']:
        metric, op, expected = check['metric'], check['operator'], check['value']
        value = metrics.get(metric)
        supported = metric in metrics and type(value) in (int, float) and math.isfinite(value)
        if not supported:
            outcome = 'UNVERIFIED'
        elif op == 'finite':
            outcome = 'PASSED'
        elif op == 'eq':
            outcome = 'PASSED' if type(value) == type(expected) and value == expected else 'FAILED'
        elif op in ('le', 'ge') and type(expected) in (int, float) and math.isfinite(expected):
            outcome = 'PASSED' if (value <= expected if op == 'le' else value >= expected) else 'FAILED'
        else:
            outcome = 'UNVERIFIED'
        result['checks'].append({'metric': metric, 'value': value, 'expected': expected,
                                 'operator': op, 'unit': check['unit'], 'status': outcome})
    if (state in ('SUCCEEDED', 'FAILED', 'STOPPED') and state != expected_state) or any(c['status'] == 'FAILED' for c in result['checks']):
        result['status'] = 'FAILED'
    elif result['errors'] or result['missing_outputs']:
        result['status'] = 'PARTIAL'
    elif any(c['status'] == 'UNVERIFIED' for c in result['checks']):
        result['status'] = 'UNVERIFIED'
    else:
        result['status'] = 'PASSED'
    return result


def parse_historical(case, root, result):
    """Compare declared metrics in an identified old receipt; never fabricate an exit."""
    source = case.get('historical_source')
    result.update(execution_relation='HISTORICAL_NOT_RERUN', observed_date=source.get('observed_date') if source else None,
                  scope='Checks on preserved historical receipt fields only; no raw-force recomputation or current readiness')
    if result['errors'] or result['missing_outputs'] or not source:
        result['status'] = 'PARTIAL'
        return result
    path = safe_path(root, source['path'])
    if path.stat().st_size > 16 * 1024 * 1024:
        result['errors'].append('Historical receipt exceeds 16 MiB bound')
        result['status'] = 'PARTIAL'
        return result
    try:
        raw = path.read_bytes()
        expected_hash = next(item['sha256'] for item in case['inputs'] if item['path'] == source['path'])
        if hashlib.sha256(raw).hexdigest() != expected_hash:
            raise ValueError('Historical source changed after identity check')
        value = json.loads(raw.decode('utf-8-sig'))
        pointer = source['pointer']
        if pointer and not pointer.startswith('/'):
            raise ValueError('JSON pointer must start with slash')
        for key in pointer[1:].split('/') if pointer else []:
            key = key.replace('~1', '/').replace('~0', '~')
            value = value[int(key)] if isinstance(value, list) else value[key]
        if not isinstance(value, dict):
            raise ValueError('Historical selected record must be an object')
    except (ValueError, KeyError, IndexError, TypeError, UnicodeError) as error:
        result['errors'].append('Historical pointer/record invalid: ' + str(error))
        result['status'] = 'PARTIAL'
        return result
    result['evidence'].append({'path': source['path'], 'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw), 'pointer': pointer})
    for check in case['checks']:
        metric, expected, op = check['metric'], check['value'], check['operator']
        actual = value.get(metric)
        numeric = type(actual) in (int, float) and math.isfinite(actual)
        if metric not in value or actual is None:
            outcome = 'UNVERIFIED'
        elif op == 'eq' and type(actual) in (str, bool, int, float):
            outcome = 'PASSED' if type(actual) == type(expected) and actual == expected and (type(actual) not in (int, float) or numeric) else 'FAILED'
        elif op == 'finite' and numeric:
            outcome = 'PASSED'
        elif op in ('le', 'ge') and numeric and type(expected) in (int, float) and math.isfinite(expected):
            outcome = 'PASSED' if (actual <= expected if op == 'le' else actual >= expected) else 'FAILED'
        else:
            outcome = 'UNVERIFIED'
        result['checks'].append({'metric': metric, 'value': actual, 'expected': expected,
                                 'operator': op, 'unit': check['unit'], 'status': outcome})
    outcomes = {item['status'] for item in result['checks']}
    result['status'] = 'FAILED' if 'FAILED' in outcomes else 'UNVERIFIED' if 'UNVERIFIED' in outcomes or not outcomes else 'PASSED'
    return result
