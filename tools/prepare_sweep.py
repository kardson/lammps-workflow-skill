"""Prepare a bounded explicit list of candidate variants; never submit jobs."""
import argparse
import copy
import re

from common import print_receipt, utc_now
from local_common import identity, integer, json_file, load_config, new_directory, require, resolve_file
from prepare_input_package import prepare

ALLOWED = {'initial_temperature_K', 'velocity_seed', 'thermostat_seed', 'thermostat_damping_ps',
           'temperature_extra_dof', 'timestep_ps', 'equilibrate_steps', 'deposition_steps', 'post_steps',
           'beams', 'thermo_every', 'dump_every', 'restart_every', 'structure_file', 'minimum_separation_angstrom'}


def prepare_sweep(config, base, output, maximum):
    require(config, ['base_config_file', 'variants', 'purpose'])
    integer(maximum, 'maximum_candidates', 1)
    variants = config['variants']
    if not isinstance(variants, list) or not variants or len(variants) > maximum:
        raise ValueError('Variant list is empty or exceeds the explicitly supplied candidate budget.')
    ids = [variant.get('id') for variant in variants]
    if len(set(ids)) != len(ids) or any(not isinstance(value, str) or not re.fullmatch(r'[a-zA-Z0-9][a-zA-Z0-9_-]{0,63}', value) for value in ids):
        raise ValueError('Variant IDs must be unique safe directory names.')
    for variant in variants:
        if not isinstance(variant.get('changes'), dict) or not variant['changes'] or set(variant['changes']) - ALLOWED:
            raise ValueError('Each variant needs explicit changes within the supported atomic-beam contract.')
    source = resolve_file(config['base_config_file'], base)
    template, template_base = load_config(source)
    if config['purpose'] != template.get('purpose'):
        raise ValueError('Sweep purpose must match the base configuration.')
    output = new_directory(output)
    records, failure = [], None
    try:
        for variant in variants:
            candidate = copy.deepcopy(template)
            candidate.update(variant['changes'])
            report = prepare(candidate, template_base, output / variant['id'])
            records.append({'id': variant['id'], 'changes': variant['changes'], 'status': report['status'],
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
    args = parser.parse_args()
    config, base = load_config(args.config)
    report = prepare_sweep(config, base, args.output_directory, args.maximum_candidates)
    print_receipt(args.output_directory, status=report['status'], jobs_submitted=0)


if __name__ == '__main__':
    main()
