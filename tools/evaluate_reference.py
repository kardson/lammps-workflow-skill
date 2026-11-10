"""Evaluate existing reference/prediction artifacts locally; never performs inference."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import re

from common import utc_now
from local_common import identity, json_file, new_directory
from reference_metrics import evaluate


def load_artifact(path, record_type):
    path = Path(path).resolve(strict=True)
    if path.stat().st_size > 64 * 1024 * 1024:
        raise ValueError('Evaluation JSON exceeds 64 MiB bound; supply a bounded dataset')
    raw = path.read_bytes()
    data = json.loads(raw.decode('utf-8-sig'))
    if not isinstance(data, dict) or data.get('schema_version') != 1 or data.get('record_type') != record_type:
        raise ValueError('Expected v1 ' + record_type)
    if data.get('source_class') not in ('artificial_fixture', 'research_candidate', 'reviewed_reference'):
        raise ValueError('Explicit source_class required')
    records = data.get('records')
    if not isinstance(records, list) or any(not isinstance(record, dict) for record in records):
        raise ValueError('Dataset records must be objects')
    provenance = []
    for item in data.get('provenance', []):
        if not isinstance(item, dict) or not isinstance(item.get('path'), str):
            raise ValueError('Malformed dataset provenance')
        source = Path(item['path'])
        source = source if source.is_absolute() else path.parent / source
        observed = identity(source)
        if observed['sha256'] != item.get('sha256'):
            raise ValueError('Dataset provenance identity mismatch: ' + item['path'])
        provenance.append(observed)
    if data['source_class'] != 'artificial_fixture' and not provenance:
        raise ValueError('Research artifacts require explicit source provenance identities')
    if data['source_class'] != 'artificial_fixture':
        for record in records:
            if record_type == 'prediction_dataset' and record.get('status') != 'SUCCEEDED':
                continue
            if not re.fullmatch('[a-f0-9]{64}', str(record.get('configuration_sha256', ''))):
                raise ValueError('Research sample requires explicit configuration_sha256')
    return data, {'path': str(path), 'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest(),
                  'verified_provenance': provenance}


def plot_summary(report, output):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    figure, axes = plt.subplots(1, 2, figsize=(10, 4), layout='constrained')
    names = list(report['coverage'])
    valid = [report['coverage'][name]['valid'] for name in names]
    required = [report['coverage'][name]['required'] for name in names]
    axes[0].bar(names, required, color='#d9e1e8', label='Required samples')
    axes[0].bar(names, valid, color='#267ca5', label='Valid samples')
    axes[0].set_ylabel('Sample count')
    axes[0].legend()
    species = report['force_components_by_species_eV_per_angstrom']
    if species:
        axes[1].bar(list(species), [value['mae'] for value in species.values()], color='#267ca5')
        axes[1].set_ylabel('Force component MAE (eV/angstrom)')
    else:
        axes[1].text(0.5, 0.5, 'No valid force metrics', ha='center', va='center', transform=axes[1].transAxes)
    figure.suptitle(report['source_class'] + ' — ' + report['status'])
    figure.savefig(output, dpi=160)
    plt.close(figure)


def evaluate_files(reference_file, prediction_file, metrics, output, plot=False):
    references, ref_identity = load_artifact(reference_file, 'reference_dataset')
    predictions, pred_identity = load_artifact(prediction_file, 'prediction_dataset')
    backend = predictions.get('backend')
    if not isinstance(backend, dict) or backend.get('kind') not in ('empirical', 'pretrained_ml', 'artificial_fixture') or not backend.get('identity'):
        raise ValueError('Explicit empirical/pretrained ML/fixture backend identity required')
    report = evaluate(references['records'], predictions['records'], metrics)
    report.update(evaluated_utc=utc_now(), source_class=references['source_class'],
                  prediction_source_class=predictions['source_class'], backend=backend,
                  artifact_identities={'reference': ref_identity, 'prediction': pred_identity})
    directory = new_directory(output)
    json_file(directory / 'evaluation.json', report)
    with (directory / 'samples.csv').open('x', encoding='utf-8', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=['id', 'prediction_status', 'energy_signed_error_eV_per_atom',
                                   'force_component_mae_eV_per_angstrom', 'force_component_max_absolute_eV_per_angstrom', 'issues'])
        writer.writeheader()
        for sample in report['samples']:
            writer.writerow({'id': sample['id'], 'prediction_status': sample['prediction_status'],
                'energy_signed_error_eV_per_atom': sample['metrics'].get('energy', {}).get('signed_error_eV_per_atom'),
                'force_component_mae_eV_per_angstrom': sample['metrics'].get('forces', {}).get('mae'),
                'force_component_max_absolute_eV_per_angstrom': sample['metrics'].get('forces', {}).get('max_absolute'),
                'issues': ' | '.join(sample['issues'])})
    if plot:
        plot_summary(report, directory / 'evaluation.png')
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--references', required=True)
    parser.add_argument('--predictions', required=True)
    parser.add_argument('--metric', action='append', required=True, choices=['energy', 'forces', 'stress'])
    parser.add_argument('--output-directory', required=True)
    parser.add_argument('--plot', action='store_true')
    args = parser.parse_args()
    try:
        report = evaluate_files(args.references, args.predictions, args.metric, args.output_directory, args.plot)
    except (OSError, ValueError, ImportError) as error:
        print(json.dumps({'status': 'ERROR', 'message': str(error), 'inference_performed': False}))
        return 2
    print(json.dumps({'status': report['status'], 'coverage': report['coverage'], 'inference_performed': False}))
    return 0 if report['status'] == 'METRICS_REPORTED_NOT_ACCEPTED' else 1


if __name__ == '__main__':
    raise SystemExit(main())
