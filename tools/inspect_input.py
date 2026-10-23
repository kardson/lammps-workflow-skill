"""Read one LAMMPS input without evaluating variables, includes or commands."""
import argparse
import hashlib
import json
from pathlib import Path
import shlex

from common import evidence_path, print_receipt, utc_now, write_report

CONTROL_FLOW = {'include', 'jump', 'if', 'next', 'clear', 'python', 'shell'}
SELECTED = {'units', 'atom_style', 'boundary', 'timestep', 'pair_style', 'pair_coeff',
            'read_data', 'read_restart', 'fix', 'compute_modify', 'group', 'dump',
            'dump_modify', 'restart', 'write_restart', 'thermo_style', 'run', 'minimize'}


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


def inspect_input(path, plan_path=None):
    path = Path(path).expanduser().resolve(strict=True)
    raw = path.read_bytes()
    text = raw.decode('utf-8-sig')
    commands, issues = index_commands(text)
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
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', required=True)
    parser.add_argument('--plan', help='Optional existing plan; only four literal fields are compared')
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    output = evidence_path(args.output)
    report = inspect_input(args.input, args.plan)
    write_report(output, report)
    mismatches = [field for field, check in report['plan_checks'].items() if check['verdict'] == 'MISMATCH']
    print_receipt(output, coverage=report['coverage'], literal_mismatches=mismatches,
                  preparation_audit_complete=False)
    if mismatches:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
