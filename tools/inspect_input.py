"""Statically inspect literal input text and optional bounded includes; never execute commands."""
import argparse
import hashlib
import json
from pathlib import Path
import shlex

from common import evidence_path, print_receipt, utc_now, write_report

CONTROL_FLOW = {'include', 'jump', 'if', 'next', 'clear', 'python', 'shell'}
SELECTED = {'units', 'atom_style', 'boundary', 'timestep', 'pair_style', 'pair_coeff',
            'read_data', 'read_restart', 'fix', 'compute_modify', 'group', 'dump',
            'dump_modify', 'restart', 'write_restart', 'thermo_style', 'run', 'minimize',
            'region', 'mass', 'velocity', 'thermo', 'unfix', 'reset_timestep'}


def index_commands(text):
    commands, issues = [], []
    pending, start = '', None
    for number, physical in enumerate(text.splitlines(), 1):
        if start is None:
            start = number
        # LAMMPS tests a trailing ampersand before removing comments.
        stripped = physical.rstrip()
        continued = stripped.endswith('&')
        pending += (stripped[:-1] + ' ') if continued else stripped
        if continued:
            continue
        if '\"\"\"' in pending or "'''" in pending:
            issues.append({'line': start, 'reason': 'Triple-quoted block unsupported; indexing stops here.'})
            break
        lexer = shlex.shlex(pending, posix=True)
        lexer.whitespace_split = True
        lexer.commenters = '#'
        lexer.escape = ''  # Preserve paths; this is not a shell escape evaluator.
        try:
            words = list(lexer)
        except ValueError as error:
            issues.append({'line': start, 'reason': 'Quoted argument could not be indexed: ' + str(error)})
            break
        if words:
            commands.append({'line': start, 'command': words[0], 'args': words[1:],
                             'dynamic_tokens': any('$' in word for word in words)})
            if '&' in words:
                issues.append({'line': start, 'reason': 'Unresolved ampersand; possible comment/continuation ambiguity.'})
        pending, start = '', None
    else:
        if pending:
            issues.append({'line': start, 'reason': 'Unfinished continuation at end of file.'})
    return commands, issues


def compare_literal(commands, field, expected, ambiguous):
    observed = [item for item in commands if item['command'] == field]
    result = {'expected': expected, 'observed': [item['args'] for item in observed]}
    if expected is None:
        return {**result, 'verdict': 'UNCONFIRMED', 'reason': 'Plan has no value for this field.'}
    if ambiguous or len(observed) != 1 or observed[0]['dynamic_tokens']:
        return {**result, 'verdict': 'UNVERIFIED', 'reason': 'Need one literal assignment without unresolved control flow.'}
    actual = observed[0]['args']
    wanted = expected.split() if isinstance(expected, str) else expected
    if field == 'timestep':
        try:
            equal = len(actual) == 1 and float(actual[0]) == float(expected)
        except (TypeError, ValueError):
            return {**result, 'verdict': 'UNVERIFIED', 'reason': 'Non-numeric timestep contract.'}
    else:
        if not isinstance(wanted, list):
            return {**result, 'verdict': 'UNVERIFIED', 'reason': 'Expected text or token list in plan.'}
        equal = actual == wanted
    return {**result, 'verdict': 'MATCH' if equal else 'MISMATCH',
            'reason': 'Literal comparison only; not an input-validity or scientific-acceptance result.'}


def expand_literal_includes(path, root, active=(), depth=0, budget=None):
    if budget is None:
        budget = {'files': 0, 'bytes': 0}
    path = Path(path).resolve(strict=True)
    if not path.is_relative_to(root) or path in active or depth > 8:
        raise ValueError('Include escapes root, cycles or exceeds depth limit')
    raw = path.read_bytes()
    budget['files'] += 1
    budget['bytes'] += len(raw)
    if budget['files'] > 64 or budget['bytes'] > 16 * 1024 * 1024:
        raise ValueError('Aggregate include budget exceeded')
    if len(raw) > 4 * 1024 * 1024:
        raise ValueError('Include file exceeds 4 MiB text limit')
    commands, issues = index_commands(raw.decode('utf-8-sig'))
    result, sources = [], [{'path': str(path), 'sha256': hashlib.sha256(raw).hexdigest()}]
    for command in commands:
        command['source'] = str(path)
        if command['command'] == 'include' and not command['dynamic_tokens'] and len(command['args']) == 1:
            # Explicit root models the intended LAMMPS working directory.
            nested, problems, observed = expand_literal_includes(root / command['args'][0], root, (*active, path), depth + 1, budget)
            result.extend(nested)
            issues.extend(problems)
            sources.extend(observed)
        else:
            result.append(command)
    return result, issues, sources


def inspect_input(path, plan_path=None, include_root=None):
    path = Path(path).expanduser().resolve(strict=True)
    raw = path.read_bytes()
    text = raw.decode('utf-8-sig')
    commands, issues = index_commands(text)
    include_sources = []
    if include_root is not None:
        commands, issues, include_sources = expand_literal_includes(path, Path(include_root).resolve())
    controls = [item for item in commands if item['command'] in CONTROL_FLOW or
                '$' in item['command'] or
                (item['command'] == 'run' and 'every' in item['args'])]
    dynamic = [item['line'] for item in commands if item['dynamic_tokens']]
    report = {'observed_utc': utc_now(), 'input': str(path), 'bytes': len(raw),
              'sha256': hashlib.sha256(raw).hexdigest(), 'indexed_command_count': len(commands),
              'selected_commands': [item for item in commands if item['command'] in SELECTED],
              'control_flow_not_evaluated': controls, 'dynamic_token_lines': dynamic,
              'indexing_issues': issues, 'plan_checks': {},
              'coverage': 'PARTIAL' if issues or controls or dynamic else 'LITERAL_COMMAND_INDEX_ONLY',
              'preparation_audit_complete': False, 'execution_authorized': False,
              'engine_started': False,
              'limitations': ['Single input only; include files, variables, branches and Python/shell commands are never evaluated.',
                              'No engine syntax validation, potential-interface/type mapping validation, geometry/overlap or numerical test.',
                              'No inference of command defaults, scientific confirmation, job state or execution permission.']}
    if include_root is not None:
        report['limitations'][0] = 'Literal includes expanded within explicit working-directory root only; variables, branches and Python/shell commands never evaluated.'
    report['literal_include_sources'] = include_sources
    if plan_path:
        plan_path = Path(plan_path).expanduser().resolve(strict=True)
        plan_raw = plan_path.read_bytes()
        plan = json.loads(plan_raw.decode('utf-8-sig'))
        simulation = plan.get('simulation', {})
        if not isinstance(simulation, dict):
            raise ValueError('Plan simulation must be a JSON object.')
        report['plan'] = {'path': str(plan_path), 'sha256': hashlib.sha256(plan_raw).hexdigest(),
                          'status': plan.get('status'), 'confirmation_present': plan.get('confirmation') is not None,
                          'note': 'Presence of a field is not approval verification.'}
        report['plan_checks'] = {field: compare_literal(commands, field, simulation.get(field), bool(issues or controls))
                                 for field in ['units', 'atom_style', 'boundary', 'timestep']}
        contracts = plan.get('input_contract', {})
        if not isinstance(contracts, dict):
            raise ValueError('input_contract must be an object')
        checks = {}
        for field, expected in contracts.items():
            if field not in SELECTED:
                checks[field] = {'verdict': 'UNVERIFIED', 'reason': 'Command outside selected audit scope'}
                continue
            observed = [item for item in commands if item['command'] == field]
            if issues or controls or any(item['dynamic_tokens'] for item in observed):
                checks[field] = {'verdict': 'UNVERIFIED', 'reason': 'Unresolved parsing/control flow or dynamic command'}
            elif not isinstance(expected, list) or not all(isinstance(row, list) and all(isinstance(token, str) for token in row) for row in expected):
                checks[field] = {'verdict': 'UNVERIFIED', 'reason': 'Expected ordered list of literal argument lists'}
            else:
                actual = [item['args'] for item in observed]
                checks[field] = {'verdict': 'MATCH' if actual == expected else 'MISMATCH',
                                 'expected': expected, 'observed': actual}
        report['command_contract_checks'] = checks
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', required=True)
    parser.add_argument('--plan', help='Optional plan: four simulation fields plus explicit selected-command input_contract comparisons')
    parser.add_argument('--output', required=True)
    parser.add_argument('--include-root', help='Explicit intended working directory for bounded literal include text expansion')
    args = parser.parse_args()
    output = evidence_path(args.output)
    report = inspect_input(args.input, args.plan, args.include_root)
    write_report(output, report)
    mismatches = [field for field, check in report['plan_checks'].items() if check['verdict'] == 'MISMATCH']
    mismatches += [field for field, check in report.get('command_contract_checks', {}).items() if check['verdict'] == 'MISMATCH']
    print_receipt(output, coverage=report['coverage'], literal_mismatches=mismatches,
                  preparation_audit_complete=False)
    if mismatches:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
