"""Exercise local tools on artificial fixtures, without inference or MD."""
import argparse
import importlib.metadata
from pathlib import Path
import sys

from common import print_receipt, SKILL_ROOT, utc_now
from local_common import json_file, new_directory


def run(output):
    # The full skill ships these explicitly labeled, artificial software fixtures.
    sys.path.insert(0, str(SKILL_ROOT / 'tests'))
    from local_fixtures import dump_frame, package_fixture, trajectory_config
    from analyze_trajectory import analyze
    from analyze_balance import analyze as analyze_balance
    from bundle_package import bundle
    from generate_report import generate
    from inspect_input import inspect_input
    from prepare_input_package import prepare as prepare_package
    from prepare_structure import prepare as prepare_structure
    from prepare_sweep import prepare_sweep
    from render_structure import render
    from summarize_replicas import summarize
    output = new_directory(output)
    record = {'started_utc': utc_now(), 'source_class': 'engineering_fixture', 'status': 'IN_PROGRESS',
              'simulation_run': False, 'model_inference_run': False, 'workstation_contacted': False,
              'note': 'Artificial geometry/parameters/trajectory/scalars; no semiconductor physics or production input acceptance.'}
    try:
        record['versions'] = {name: importlib.metadata.version(name) for name in
                              ['ase', 'numpy', 'scipy', 'pandas', 'matplotlib', 'ovito', 'jupyterlab', 'spglib']}
        bulk_config = {'operation': 'bulk_zincblende', 'purpose': 'engineering_fixture',
                       'provenance': 'Arbitrary serializer fixture; lattice is not a reference value.',
                       'type_order': ['Si', 'C'], 'boundary': ['p', 'p', 'p'], 'minimum_separation_angstrom': 0.2,
                       'elements': ['Si', 'C'], 'lattice_a_angstrom': 4.4, 'repeat': [1, 1, 1]}
        bulk = prepare_structure(bulk_config, output, output / 'bulk')
        slab_config = {**bulk_config, 'operation': 'slab', 'source_file': str(output / 'bulk/structure.extxyz'),
                       'source_format': 'extxyz', 'source_boundary': ['p', 'p', 'p'], 'boundary': ['p', 'p', 'f'],
                       'miller': [1, 0, 0], 'layers': 2, 'trim_bottom_planes': 0, 'trim_top_planes': 0,
                       'plane_tolerance_angstrom': 1e-5, 'bottom_buffer_angstrom': 1,
                       'vacuum_above_angstrom': 8, 'termination_label': 'Unrelaxed engineering cut, no physical selection'}
        slab = prepare_structure(slab_config, output, output / 'slab')
        interface_config = {**bulk_config, 'operation': 'interface', 'boundary': ['p', 'p', 'f'],
                            'substrate_file': str(output / 'slab/structure.extxyz'), 'film_file': str(output / 'slab/structure.extxyz'),
                            'source_format': 'extxyz', 'lateral_match': 'strain_film_to_substrate',
                            'gap_angstrom': 1.5, 'bottom_buffer_angstrom': 1, 'vacuum_above_angstrom': 8,
                            'film_xy_shift_angstrom': [0, 0]}
        interface = prepare_structure(interface_config, output, output / 'interface')
        config = package_fixture(output)
        json_file(output / 'fixture-input-config.json', config)
        package = prepare_package(config, output, output / 'input-package')
        plan = {'status': 'ENGINEERING_FIXTURE', 'confirmation': None, 'simulation':
                {'units': 'metal', 'atom_style': 'atomic', 'boundary': ['p', 'p', 'f'], 'timestep': config['timestep_ps']}}
        json_file(output / 'fixture-plan.json', plan)
        input_review = inspect_input(output / 'input-package/in.growth', output / 'fixture-plan.json')
        assert all(value['verdict'] == 'MATCH' for value in input_review['plan_checks'].values())
        json_file(output / 'input-review.json', input_review)
        archive = bundle(output / 'input-package', output / 'candidate-inputs.zip', output / 'archive.json')
        sweep_config = {'base_config_file': str(output / 'fixture-input-config.json'), 'purpose': 'engineering_fixture',
                        'variants': [{'id': 'seed1', 'changes': {'velocity_seed': 11111}},
                                     {'id': 'seed2', 'changes': {'velocity_seed': 22222}}]}
        sweep = prepare_sweep(sweep_config, output, output / 'sweep', 2)
        trajectory = output / 'artificial.dump'
        trajectory.write_text(dump_frame(0, [[1, 1, 0.25, 0.5, 1], [2, 2, 0.25, 0.5, 2], [3, 2, 1.25, 0.5, 4]]) +
                              dump_frame(10, [[1, 1, 0.25, 0.5, 1], [3, 2, 1.25, 0.5, 4], [4, 2, 0.25, 0.5, 6]]), encoding='utf-8')
        analysis = analyze(trajectory, trajectory_config(), output / 'analysis')
        counters = output / 'artificial-counters.csv'
        counters.write_text('time_ps,count_Si,count_C,inserted_Si,inserted_C,removed_Si,removed_C\n0,1,0,0,0,0,0\n10,1,2,0,3,0,1\n', encoding='utf-8')
        balance = analyze_balance(counters, {'source_class': 'engineering_fixture', 'elements': ['Si', 'C'],
                                  'initial_counts': {'Si': 1, 'C': 0}, 'area_angstrom2': 2, 'time_column': 'time_ps',
                                  'initial_time_ps': 0, 'observed_prefix': 'count_', 'inserted_prefix': 'inserted_',
                                  'removed_prefix': 'removed_', 'counter_provenance': 'Fabricated counters; no actual insertion run.'},
                                  output / 'balance')
        report = generate(output / 'analysis', output / 'report', 'Engineering fixture — no material result', 100)
        scalars = output / 'artificial-replicas.csv'
        scalars.write_text('case,replica,metric\nfixture,1,1\nfixture,2,2\nfixture,3,3\n', encoding='utf-8')
        statistics = summarize(scalars, {'metric_column': 'metric', 'unit': 'angstrom', 'replica_id_column': 'replica',
                                        'group_columns': ['case'], 'confidence': 0.95,
                                        'independence_basis': 'Artificial scalar fixture, not trajectory samples.',
                                        'source_class': 'engineering_fixture'}, output / 'replicas')
        image = render(output / 'interface/structure.data', 'lammps-data', ['Si', 'C'],
                       output / 'preview', 'ENGINEERING FIXTURE / UNRELAXED')
        record.update(status='LOCAL_SOFTWARE_CHECKS_PASSED', completed_utc=utc_now(),
                      atom_counts={'bulk': bulk['audit']['atom_count'], 'slab': slab['audit']['atom_count'],
                                   'interface': interface['audit']['atom_count']},
                      geometry_checks_passed=True, literal_plan_checks='MATCH', archive_crc_verified=archive['archive_crc_verified'],
                      candidate_variants=len(sweep['prepared_variants']), jobs_submitted=sweep['jobs_submitted'],
                      trajectory_frames=analysis['frames_selected'], replica_groups=len(statistics['groups']),
                      counter_balance=balance['status'],
                      renderer=image['renderer'], report_path=str(output / 'report/report.html'),
                      preview_path=str(output / 'preview/structure-preview.png'), scientific_acceptance='UNVERIFIED')
    except Exception as error:
        record.update(status='FAILED_PARTIAL_LOCAL_CHECK', failure={'type': type(error).__name__, 'message': str(error)})
        json_file(output / 'local-pipeline-verification.json', record)
        raise
    json_file(output / 'local-pipeline-verification.json', record)
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-directory', required=True)
    args = parser.parse_args()
    result = run(args.output_directory)
    print_receipt(args.output_directory, status=result['status'], simulation_run=False)


if __name__ == '__main__':
    main()
