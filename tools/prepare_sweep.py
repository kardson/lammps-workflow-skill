"""Prepare a bounded explicit list of candidate variants; never submit jobs."""
import argparse
import copy
import re
import json

from common import print_receipt, utc_now
from local_common import identity, integer, json_file, load_config, new_directory, require, resolve_file
from prepare_input_package import prepare, readiness

ALLOWED = {'initial_temperature_K', 'velocity_seed', 'thermostat_seed', 'thermostat_damping_ps',
           'temperature_extra_dof', 'timestep_ps', 'equilibrate_steps', 'deposition_steps', 'post_steps',
           'beams', 'thermo_every', 'dump_every', 'restart_every', 'structure_file', 'minimum_separation_angstrom'}


def load_sweep(config, base, maximum):
    if not isinstance(config,dict):
        raise ValueError('Sweep configuration must be an object')
    json.dumps(config,allow_nan=False)
    require(config, ['base_config_file', 'variants', 'purpose'])
    integer(maximum, 'maximum_candidates', 1)
    variants = config['variants']
    if config['purpose'] not in ('engineering_fixture','research_candidate'):
        raise ValueError('Explicit engineering_fixture or research_candidate purpose required')
    if not isinstance(variants, list) or not variants or len(variants) > maximum or any(not isinstance(variant,dict) for variant in variants):
        raise ValueError('Variant list is empty or exceeds the explicitly supplied candidate budget.')
    ids = [variant.get('id') for variant in variants]
    if any(not isinstance(value, str) or not re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9_-]{0,63}', value) for value in ids) or len(set(ids)) != len(ids):
        raise ValueError('Variant IDs must be unique safe directory names.')
    for variant in variants:
        if not isinstance(variant.get('changes'), dict) or not variant['changes'] or set(variant['changes']) - ALLOWED:
            raise ValueError('Each variant needs explicit changes within the supported atomic-beam contract.')
        if config['purpose'] == 'research_candidate' and (not isinstance(variant.get('reason'), str) or not variant['reason'].strip()):
            raise ValueError('Research parameter variants require an explicit change reason.')
    source = resolve_file(config['base_config_file'], base)
    template, template_base = load_config(source)
    if config['purpose'] != template.get('purpose'):
        raise ValueError('Sweep purpose must match the base configuration.')
    if config['purpose'] == 'research_candidate' and not template.get('plan_file'):
        raise ValueError('Research variants require a base plan reference.')
    return variants, source, template, template_base


def plan_sweep(config, base, output, maximum):
    variants,source,template,template_base = load_sweep(config,base,maximum)
    plan_identity = None
    if template.get('plan_file'):
        plan_file = resolve_file(template['plan_file'],template_base)
        plan, _ = load_config(plan_file)
        if plan.get('schema_version') != 1 or plan.get('record_type') != 'md_plan' or not plan.get('id'):
            raise ValueError('Explicit v1 MD plan identity required for bound proposals')
        plan_identity = {'id':plan['id'],**identity(plan_file)}
    records=[]
    for variant in variants:
        unresolved=[]
        for key in ('comparison_basis','sampling_window','replica_strategy'):
            if not variant.get(key):
                unresolved.append(key)
        if any(value is None for value in variant['changes'].values()):
            unresolved.append('parameter values')
        records.append({'id':variant['id'],'changes':variant['changes'],'reason':variant.get('reason'),
            'comparison_basis':variant.get('comparison_basis'),'sampling_window':variant.get('sampling_window'),
            'replica_strategy':variant.get('replica_strategy'),'unresolved':unresolved})
    report={'prepared_utc':utc_now(),'status':'NONEXECUTABLE_SENSITIVITY_PROPOSALS',
        'purpose':config['purpose'],'base_configuration':identity(source),'plan_binding':plan_identity,
        'base_preparation_readiness':readiness(template),'maximum_candidates':maximum,'proposed_variants':records,
        'input_files_prepared':False,'execution_authorized':False,'jobs_submitted':0,
        'scope':'Explicit bounded proposals only; no parameter defaults, automatic grid, geometry/model generation or run',
        'limitations':['Changing timestep without stage counts may change physical duration; comparison basis must address this',
            'Size/flux/seed effects and model discrepancy are separate from statistical confidence intervals',
            'Missing scientific choices remain unresolved; no proposal is an accepted calculation plan']}
    output=new_directory(output)
    json_file(output/'sensitivity-plan.json',report)
    return report


def prepare_sweep(config, base, output, maximum):
    variants,source,template,template_base = load_sweep(config,base,maximum)
    output = new_directory(output)
    records, failure = [], None
    try:
        for variant in variants:
            candidate = copy.deepcopy(template)
            candidate.update(variant['changes'])
            report = prepare(candidate, template_base, output / variant['id'])
            records.append({'id': variant['id'], 'changes': variant['changes'], 'status': report['status'],
                            'reason': variant.get('reason'), 'research_bindings': report.get('research_bindings', {}),
                            'manifest': str(output / variant['id'] / 'package-manifest.json')})
    except Exception as error:
        failure = {'type': type(error).__name__, 'message': str(error)}
    report = {'prepared_utc': utc_now(), 'status': 'FAILED_PARTIAL_PREPARATION' if failure else 'CANDIDATES_PREPARED',
              'base_configuration': identity(source), 'purpose': config['purpose'], 'maximum_candidates': maximum,
              'requested_variants': variants, 'prepared_variants': records, 'failure': failure,
              'scientific_changes_proposed': True, 'execution_authorized': False, 'jobs_submitted': 0,
              'scope': 'Explicit local parameter candidates only; no automatic grid expansion, resource scheduler, MD or acceptance.'}
    json_file(output / 'sweep-manifest.json', report)
    if failure:
        raise ValueError('Sweep preparation failed; partial candidates preserved: ' + failure['message'])
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', required=True)
    parser.add_argument('--maximum-candidates', type=int, required=True)
    parser.add_argument('--output-directory', required=True)
    parser.add_argument('--plan-only', action='store_true')
    args = parser.parse_args()
    config, base = load_config(args.config)
    report = plan_sweep(config, base, args.output_directory, args.maximum_candidates) if args.plan_only else prepare_sweep(config, base, args.output_directory, args.maximum_candidates)
    print_receipt(args.output_directory, status=report['status'], jobs_submitted=0)


if __name__ == '__main__':
    main()
