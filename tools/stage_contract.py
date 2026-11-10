"""Audit declared MD stages and inspect supplied observations; no process control."""
import math
import json
from pathlib import Path
from compatibility_registry import DIMENSIONS

KINDS = ('preparation', 'thermalization', 'deposition', 'post_relaxation', 'sampling')
SUPPORT_FIELDS = ('profile_file', 'profile_sha256', 'engine_id', 'model_sha256', 'evidence_file', 'evidence_sha256', 'scenario')


def finite(value):
    return type(value) in (int, float) and math.isfinite(value)


def audit(contract):
    errors, unresolved = [], []
    import jsonschema
    schema = json.loads((Path(__file__).resolve().parents[1] / 'schemas/stage-contract.schema.json').read_text(encoding='utf-8'))
    structural = list(jsonschema.Draft202012Validator(schema).iter_errors(contract))
    if structural:
        return {'status': 'INVALID', 'errors': [('/' + '/'.join(map(str, error.absolute_path)) + ': ' + error.message) for error in structural],
                'unresolved': [], 'scope': 'Stage record structure invalid; no observation checks performed'}
    if contract.get('schema_version') != 1 or contract.get('record_type') != 'deposition_stage_contract':
        errors.append('Expected v1 deposition_stage_contract')
    if not isinstance(contract.get('plan_binding'), dict) or any(not contract['plan_binding'].get(name) for name in ('id', 'file', 'sha256')):
        unresolved.append('plan_binding')
    stages = contract.get('stages')
    if not isinstance(stages, list):
        return {'status': 'INVALID', 'errors': errors + ['stages must be a list'], 'unresolved': unresolved}
    if not stages:
        unresolved.append('stages')
    seen = set()
    previous_end = None
    for stage in stages:
        if not isinstance(stage, dict):
            errors.append('Stage must be an object')
            continue
        key = stage.get('id')
        if not isinstance(key, str) or not key or key in seen:
            errors.append('Missing/duplicate stage ID')
        else:
            seen.add(key)
        label = str(key)
        if stage.get('kind') not in KINDS:
            errors.append(label + ': unsupported stage kind')
        start, end = stage.get('start_step'), stage.get('end_step')
        if start is None or end is None:
            unresolved.append(label + ': step interval')
            previous_end = None
        elif type(start) is not int or type(end) is not int or start < 0 or end <= start:
            errors.append(label + ': require increasing nonnegative half-open step interval')
        else:
            if previous_end is not None and start < previous_end:
                errors.append(label + ': overlapping phase intervals')
            previous_end = end
        for name in ('timestep_ps', 'physical_time_origin_ps'):
            value = stage.get(name)
            if value is None:
                unresolved.append(label + ': ' + name)
            elif not finite(value) or name == 'timestep_ps' and value <= 0:
                errors.append(label + ': invalid ' + name)
        groups = stage.get('group_roles')
        if not isinstance(groups, dict) or any(groups.get(role) is None for role in ('fixed', 'bath', 'mobile', 'incoming')):
            unresolved.append(label + ': explicit group roles')
        integrators = stage.get('integrators')
        if not isinstance(integrators, list) or not integrators:
            unresolved.append(label + ': integrator declarations')
        else:
            integrated, fixes = set(), set()
            for item in integrators:
                if not isinstance(item, dict) or not item.get('fix_id') or item.get('fix_id') in fixes:
                    errors.append(label + ': invalid/duplicate integrator fix ID')
                    continue
                fixes.add(item['fix_id'])
                ids = item.get('atom_ids')
                if ids is None:
                    unresolved.append(label + ': dynamic integrator membership requires actual input/runtime evidence')
                elif not isinstance(ids, list) or any(type(value) is not int or value < 1 for value in ids) or len(set(ids)) != len(ids):
                    errors.append(label + ': invalid declared integrated atom IDs')
                else:
                    if integrated.intersection(ids):
                        errors.append(label + ': atom declared in multiple position integrators')
                    integrated.update(ids)
        temperature = stage.get('temperature_definition')
        required = ('compute_id', 'selection', 'streaming_velocity_treatment', 'dynamic_dof', 'extra_dof', 'definition')
        if not isinstance(temperature, dict) or any(temperature.get(name) is None for name in required):
            unresolved.append(label + ': temperature definition')
        elif not finite(temperature['extra_dof']):
            errors.append(label + ': extra_dof must be finite')
        if stage.get('open_system') is None:
            unresolved.append(label + ': open-system policy')
        elif type(stage.get('open_system')) is not bool:
            errors.append(label + ': open_system must be boolean or null')
        if stage.get('particle_count_varies') is None:
            unresolved.append(label + ': particle-count policy')
        elif stage.get('particle_count_varies') is True and isinstance(temperature, dict) and temperature.get('dynamic_dof') is not True and not temperature.get('alternative_dynamic_dof_evidence'):
            unresolved.append(label + ': changing N needs dynamic DOF or explicit alternative evidence')
        for field in ('heat_flow_definition', 'insertion_event_definition', 'engine_support'):
            if not stage.get(field):
                unresolved.append(label + ': ' + field)
        support = stage.get('engine_support')
        if isinstance(support, dict) and any(not isinstance(support.get(name), str) or not support[name] for name in SUPPORT_FIELDS):
            unresolved.append(label + ': engine/scenario source fields')
        if isinstance(support, dict):
            dimensions = support.get('required_dimensions')
            if not isinstance(dimensions, list) or not dimensions:
                unresolved.append(label + ': required engine evidence dimensions')
            elif any(not isinstance(name, str) or name not in DIMENSIONS for name in dimensions):
                errors.append(label + ': unsupported engine evidence dimension')
        checks = stage.get('stop_conditions')
        if checks is None:
            unresolved.append(label + ': stop conditions')
        elif not isinstance(checks, list):
            errors.append(label + ': stop_conditions must be a list or null')
        else:
            check_ids = set()
            for check in checks:
                if not isinstance(check, dict) or not check.get('id') or check['id'] in check_ids:
                    errors.append(label + ': missing/duplicate stop-condition ID')
                    continue
                check_ids.add(check['id'])
                if any(check.get(name) is None or check.get(name) == '' for name in ('quantity', 'operator', 'threshold', 'unit', 'reason', 'source')):
                    unresolved.append(label + ': incomplete stop condition ' + check['id'])
                    continue
                if check['operator'] not in ('gt', 'lt', 'abs_gt') or not finite(check['threshold']):
                    errors.append(label + ': invalid numerical stop condition')
                elif check['operator'] == 'abs_gt' and check['threshold'] < 0:
                    errors.append(label + ': absolute-value threshold must be nonnegative')
                if (stage.get('particle_count_varies') is True or stage.get('open_system') is True) and check['quantity'] == 'closed_system_total_energy_drift':
                    errors.append(label + ': closed-system energy conservation criterion invalid for changing N')
    return {'status': 'INVALID' if errors else 'PARTIAL' if unresolved else 'DECLARATIONS_COMPLETE_NOT_RUNTIME_VALIDATED',
            'errors': errors, 'unresolved': unresolved,
            'scope': 'Declared phases only; no actual input parsing, atom membership, equilibrium or scientific acceptance'}


def inspect_observation(contract, stage_id, observation):
    report = audit(contract)
    if report['status'] == 'INVALID':
        raise ValueError('Invalid stage contract: ' + '; '.join(report['errors']))
    matches = [stage for stage in contract['stages'] if stage.get('id') == stage_id]
    if len(matches) != 1:
        raise ValueError('Unknown stage ID')
    stage = matches[0]
    if not isinstance(observation, dict) or not isinstance(observation.get('quantities'), dict):
        raise ValueError('Observation object with quantities mapping required')
    results = []
    step = observation.get('step')
    start, end = stage.get('start_step'), stage.get('end_step')
    inside = type(step) is int and type(start) is int and type(end) is int and start <= step < end
    for check in stage.get('stop_conditions') or []:
        measurement = observation.get('quantities', {}).get(check.get('quantity'), {})
        if not isinstance(measurement, dict):
            measurement = {}
        actual, threshold = measurement.get('value'), check.get('threshold')
        complete_check = all(check.get(name) is not None and check.get(name) != '' for name in ('quantity', 'operator', 'threshold', 'unit', 'reason', 'source'))
        if not complete_check or check.get('operator') not in ('gt', 'lt', 'abs_gt') or not inside or not observation.get('source') or not finite(actual) or not finite(threshold) or measurement.get('unit') != check.get('unit'):
            state = 'UNVERIFIED'
        else:
            op = check.get('operator')
            triggered = actual > threshold if op == 'gt' else actual < threshold if op == 'lt' else abs(actual) > threshold
            state = 'TRIGGERED' if triggered else 'NOT_TRIGGERED'
        results.append({'id': check.get('id'), 'status': state, 'reason': check.get('reason'),
                        'value': actual if finite(actual) else None, 'threshold': threshold, 'unit': check.get('unit')})
    return {'stage_id': stage_id, 'contract_status': report['status'], 'checks': results,
            'status': 'CONDITION_TRIGGERED' if any(item['status'] == 'TRIGGERED' for item in results)
                else 'UNVERIFIED' if not inside or not results or any(item['status'] == 'UNVERIFIED' for item in results)
                else 'NO_DECLARED_CONDITION_TRIGGERED',
            'source': observation.get('source'), 'process_action_performed': False,
            'limitations': ['Caller-supplied observations are not authenticated by this checker',
                           'No equilibrium claim, parameter changes, engine signals, model switching or training']}
