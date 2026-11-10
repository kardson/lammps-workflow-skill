"""Batch-import existing static LAMMPS outputs; preserve all sample failures."""
import argparse
import csv
import hashlib
import json
from pathlib import Path

from common import utc_now
from lammps_prediction import import_sample
from local_common import json_file, new_directory


def import_batch(manifest_file, output):
    path = Path(manifest_file).resolve(strict=True)
    if path.stat().st_size > 64 * 1024 * 1024:
        raise ValueError('Import manifest exceeds 64 MiB bound')
    raw = path.read_bytes()
    manifest = json.loads(raw.decode('utf-8-sig'))
    if not isinstance(manifest, dict) or manifest.get('schema_version') != 1 or manifest.get('record_type') != 'static_prediction_import':
        raise ValueError('Expected v1 static_prediction_import manifest')
    source_class = manifest.get('source_class')
    if source_class not in ('artificial_fixture', 'research_candidate', 'reviewed_reference'):
        raise ValueError('Explicit supported source_class required')
    backend = manifest.get('backend')
    if not isinstance(backend, dict) or backend.get('kind') not in ('empirical', 'pretrained_ml', 'artificial_fixture') or not isinstance(backend.get('identity'), str) or not backend['identity'].strip():
        raise ValueError('Explicit backend kind/identity required')
    samples = manifest.get('samples')
    if not isinstance(samples, list) or not 0 < len(samples) <= 10000 or any(not isinstance(sample, dict) for sample in samples):
        raise ValueError('Manifest requires 1..10000 sample objects')
    ids = [sample.get('id') for sample in samples]
    if any(not isinstance(key, str) or not key for key in ids) or len(set(ids)) != len(ids):
        raise ValueError('Explicit unique nonempty sample IDs required')
    records = [import_sample(sample, path.parent) for sample in samples]
    provenance = {str(path): {'path': str(path), 'sha256': hashlib.sha256(raw).hexdigest()}}
    for record in records:
        for observed in record['provenance']:
            previous = provenance.get(observed['path'])
            if previous and previous['sha256'] != observed['sha256']:
                raise ValueError('Shared artifact changed across samples')
            provenance[observed['path']] = observed
    dataset = {'schema_version': 1, 'record_type': 'prediction_dataset', 'source_class': source_class,
               'backend': backend, 'records': records, 'provenance': list(provenance.values()),
               'imported_utc': utc_now(), 'inference_performed': False,
               'scope': 'Existing static outputs only; backend identity declared, not independently authenticated'}
    successful = sum(record['status'] == 'SUCCEEDED' for record in records)
    receipt = {'status': 'IMPORTED' if successful == len(records) else 'IMPORT_PARTIAL',
               'requested_samples': len(records), 'successful_samples': successful,
               'failed_samples': len(records) - successful, 'inference_performed': False,
               'source_manifest': provenance[str(path)], 'scientific_acceptance': 'UNVERIFIED'}
    directory = new_directory(output)
    json_file(directory / 'predictions.json', dataset)
    json_file(directory / 'import.json', receipt)
    with (directory / 'samples.csv').open('x', encoding='utf-8', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=['id', 'status', 'reason'])
        writer.writeheader()
        for record in records:
            writer.writerow({key: record.get(key, '') for key in ('id', 'status', 'reason')})
    return receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', required=True)
    parser.add_argument('--output-directory', required=True)
    args = parser.parse_args()
    try:
        result = import_batch(args.manifest, args.output_directory)
    except (OSError, ValueError) as error:
        print(json.dumps({'status': 'ERROR', 'message': str(error), 'inference_performed': False}))
        return 2
    print(json.dumps(result))
    return 0 if result['status'] == 'IMPORTED' else 1


if __name__ == '__main__':
    raise SystemExit(main())
